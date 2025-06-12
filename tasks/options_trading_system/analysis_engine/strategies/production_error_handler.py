#!/usr/bin/env python3
"""
Production Error Handling and Recovery System for IFD v3.0

This module provides comprehensive error handling, stream recovery,
data quality monitoring, and automatic failover capabilities for
production deployment.

Features:
- Stream disconnection recovery protocols
- Data quality monitoring and alerts
- Automatic fallback to v1.0 on v3.0 failures
- Circuit breaker pattern implementation
- Health check monitoring
"""

import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict
import logging


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ComponentStatus(Enum):
    """Component operational status"""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    OFFLINE = "OFFLINE"


class RecoveryAction(Enum):
    """Available recovery actions"""
    RETRY = "RETRY"
    RECONNECT = "RECONNECT"
    FALLBACK = "FALLBACK"
    RESTART = "RESTART"
    ALERT_ONLY = "ALERT_ONLY"


@dataclass
class ErrorEvent:
    """Error event record"""
    error_id: str
    timestamp: datetime
    component: str
    error_type: str
    severity: ErrorSeverity
    message: str
    context: Dict[str, Any]

    # Recovery tracking
    recovery_attempted: bool = False
    recovery_action: Optional[RecoveryAction] = None
    recovery_success: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class ComponentHealth:
    """Component health status"""
    component_name: str
    status: ComponentStatus
    last_healthy: datetime
    last_check: datetime

    # Error tracking
    error_count_1h: int = 0
    error_count_24h: int = 0
    consecutive_failures: int = 0

    # Performance metrics
    response_time_ms: float = 0.0
    success_rate_1h: float = 1.0

    # Recovery status
    recovery_in_progress: bool = False
    fallback_active: bool = False


@dataclass
class StreamHealth:
    """Stream connection health status"""
    stream_name: str
    connected: bool
    last_data_received: datetime
    connection_uptime: timedelta

    # Connection quality
    messages_per_minute: float = 0.0
    data_quality_score: float = 1.0
    latency_ms: float = 0.0

    # Recovery tracking
    reconnection_attempts: int = 0
    max_reconnection_attempts: int = 5
    reconnection_backoff_seconds: float = 1.0


class StreamRecoveryManager:
    """Manages stream disconnection recovery protocols"""

    def __init__(self):
        self.streams: Dict[str, StreamHealth] = {}
        self.recovery_callbacks: Dict[str, Callable] = {}
        self.monitoring_active = False
        self._lock = threading.Lock()

    def register_stream(self, stream_name: str, recovery_callback: Callable):
        """Register a stream for monitoring"""
        with self._lock:
            self.streams[stream_name] = StreamHealth(
                stream_name=stream_name,
                connected=False,
                last_data_received=datetime.now(),
                connection_uptime=timedelta(0)
            )
            self.recovery_callbacks[stream_name] = recovery_callback

    def update_stream_health(self, stream_name: str, connected: bool, data_received: bool = False):
        """Update stream health status"""
        if stream_name not in self.streams:
            return

        with self._lock:
            stream = self.streams[stream_name]
            was_connected = stream.connected
            stream.connected = connected
            stream.last_data_received = datetime.now() if data_received else stream.last_data_received

            # Detect disconnection
            if was_connected and not connected:
                print(f"🔴 Stream disconnected: {stream_name}")
                self._initiate_recovery(stream_name)

            # Reset recovery state on successful connection
            if connected and not was_connected:
                print(f"✅ Stream reconnected: {stream_name}")
                stream.reconnection_attempts = 0
                stream.reconnection_backoff_seconds = 1.0

    def _initiate_recovery(self, stream_name: str):
        """Initiate recovery for disconnected stream"""
        stream = self.streams[stream_name]

        if stream.reconnection_attempts >= stream.max_reconnection_attempts:
            print(f"🚨 Stream {stream_name} max reconnection attempts exceeded")
            return

        # Exponential backoff
        backoff_time = stream.reconnection_backoff_seconds * (2 ** stream.reconnection_attempts)
        stream.reconnection_attempts += 1
        stream.reconnection_backoff_seconds = min(backoff_time, 60.0)  # Cap at 60 seconds

        print(f"🔄 Attempting stream recovery: {stream_name} (attempt {stream.reconnection_attempts})")

        # Schedule recovery attempt
        recovery_thread = threading.Thread(
            target=self._execute_recovery,
            args=(stream_name, backoff_time),
            daemon=True
        )
        recovery_thread.start()

    def _execute_recovery(self, stream_name: str, delay: float):
        """Execute recovery after delay"""
        time.sleep(delay)

        try:
            recovery_callback = self.recovery_callbacks[stream_name]
            success = recovery_callback()

            if success:
                print(f"✅ Stream recovery successful: {stream_name}")
                self.update_stream_health(stream_name, True)
            else:
                print(f"❌ Stream recovery failed: {stream_name}")
                self._initiate_recovery(stream_name)  # Retry

        except Exception as e:
            print(f"🚨 Stream recovery error for {stream_name}: {e}")
            self._initiate_recovery(stream_name)  # Retry


class DataQualityMonitor:
    """Monitors data quality and generates alerts"""

    def __init__(self):
        self.quality_thresholds = {
            "min_data_points_per_minute": 10,
            "max_null_percentage": 0.05,  # 5%
            "max_latency_ms": 1000,
            "min_accuracy_score": 0.95
        }

        self.quality_history: deque = deque(maxlen=1000)
        self.alert_callbacks: List[Callable] = []

    def register_alert_callback(self, callback: Callable):
        """Register callback for quality alerts"""
        self.alert_callbacks.append(callback)

    def check_data_quality(self, data: Dict[str, Any], source: str) -> float:
        """Check data quality and return score (0-1)"""
        quality_score = 1.0
        issues = []

        # Check data completeness
        if not data or len(data) == 0:
            quality_score -= 0.5
            issues.append("Empty data")

        # Check for null values
        null_count = sum(1 for v in data.values() if v is None)
        null_percentage = null_count / len(data) if data else 1.0

        if null_percentage > self.quality_thresholds["max_null_percentage"]:
            quality_score -= 0.3
            issues.append(f"High null percentage: {null_percentage:.1%}")

        # Check timestamp freshness
        if "timestamp" in data:
            try:
                timestamp = datetime.fromisoformat(str(data["timestamp"]))
                age_ms = (datetime.now() - timestamp).total_seconds() * 1000

                if age_ms > self.quality_thresholds["max_latency_ms"]:
                    quality_score -= 0.2
                    issues.append(f"High latency: {age_ms:.0f}ms")
            except:
                quality_score -= 0.1
                issues.append("Invalid timestamp")

        # Check for required fields
        required_fields = ["symbol", "strike", "volume", "open_interest"]
        missing_fields = [f for f in required_fields if f not in data or data[f] is None]

        if missing_fields:
            quality_score -= 0.2 * len(missing_fields) / len(required_fields)
            issues.append(f"Missing fields: {missing_fields}")

        # Record quality check
        quality_record = {
            "timestamp": datetime.now(),
            "source": source,
            "score": quality_score,
            "issues": issues
        }
        self.quality_history.append(quality_record)

        # Generate alerts for low quality
        if quality_score < self.quality_thresholds["min_accuracy_score"]:
            self._generate_quality_alert(source, quality_score, issues)

        return quality_score

    def _generate_quality_alert(self, source: str, score: float, issues: List[str]):
        """Generate data quality alert"""
        alert = {
            "type": "DATA_QUALITY_ALERT",
            "timestamp": datetime.now(),
            "source": source,
            "quality_score": score,
            "issues": issues,
            "severity": "HIGH" if score < 0.7 else "MEDIUM"
        }

        print(f"🚨 Data Quality Alert: {source} score={score:.2f} issues={issues}")

        # Notify registered callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Alert callback error: {e}")


class AutomaticFailoverManager:
    """Manages automatic fallback to v1.0 on v3.0 failures"""

    def __init__(self):
        self.failover_thresholds = {
            "max_consecutive_failures": 3,
            "max_error_rate_1h": 0.1,  # 10%
            "min_success_rate": 0.8,   # 80%
            "max_response_time_ms": 5000
        }

        self.component_states = {}
        self.failover_callbacks = {}
        self.fallback_active = False
        self._lock = threading.Lock()

    def register_component(self, component_name: str, failover_callback: Callable):
        """Register component for failover monitoring"""
        with self._lock:
            self.component_states[component_name] = ComponentHealth(
                component_name=component_name,
                status=ComponentStatus.HEALTHY,
                last_healthy=datetime.now(),
                last_check=datetime.now()
            )
            self.failover_callbacks[component_name] = failover_callback

    def record_component_result(self, component_name: str, success: bool,
                               response_time_ms: float = 0):
        """Record component operation result"""
        if component_name not in self.component_states:
            return

        with self._lock:
            component = self.component_states[component_name]
            component.last_check = datetime.now()

            if success:
                component.consecutive_failures = 0
                component.last_healthy = datetime.now()
                component.response_time_ms = response_time_ms

                # Check if we can recover from degraded state
                if component.status != ComponentStatus.HEALTHY:
                    self._check_recovery(component_name)
            else:
                component.consecutive_failures += 1
                component.error_count_1h += 1

                # Check if failover is needed
                self._check_failover_conditions(component_name)

    def _check_failover_conditions(self, component_name: str):
        """Check if component should be failed over"""
        component = self.component_states[component_name]

        # Check consecutive failures
        if component.consecutive_failures >= self.failover_thresholds["max_consecutive_failures"]:
            self._initiate_failover(component_name, "consecutive_failures")
            return

        # Check response time
        if component.response_time_ms > self.failover_thresholds["max_response_time_ms"]:
            self._initiate_failover(component_name, "high_response_time")
            return

        # Check success rate
        if component.success_rate_1h < self.failover_thresholds["min_success_rate"]:
            self._initiate_failover(component_name, "low_success_rate")
            return

    def _initiate_failover(self, component_name: str, reason: str):
        """Initiate failover for component"""
        component = self.component_states[component_name]

        if component.fallback_active:
            return  # Already in fallback mode

        print(f"🔄 Initiating failover for {component_name}: {reason}")

        component.status = ComponentStatus.UNHEALTHY
        component.fallback_active = True

        # Execute failover callback
        try:
            failover_callback = self.failover_callbacks[component_name]
            success = failover_callback()

            if success:
                print(f"✅ Failover successful for {component_name}")
                component.status = ComponentStatus.DEGRADED
            else:
                print(f"❌ Failover failed for {component_name}")
                component.status = ComponentStatus.OFFLINE

        except Exception as e:
            print(f"🚨 Failover error for {component_name}: {e}")
            component.status = ComponentStatus.OFFLINE

    def _check_recovery(self, component_name: str):
        """Check if component can recover from failover"""
        component = self.component_states[component_name]

        # Require stable performance before recovery
        if (component.consecutive_failures == 0 and
            component.success_rate_1h > 0.95 and
            component.response_time_ms < 1000):

            print(f"🔄 Attempting recovery for {component_name}")
            component.fallback_active = False
            component.status = ComponentStatus.HEALTHY
            print(f"✅ Component recovered: {component_name}")


class ProductionErrorHandler:
    """
    Main production error handler coordinating all error management components
    """

    def __init__(self, output_dir: str = "outputs/production_logs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Initialize components
        self.stream_recovery = StreamRecoveryManager()
        self.data_quality = DataQualityMonitor()
        self.failover_manager = AutomaticFailoverManager()

        # Error tracking
        self.error_history: deque = deque(maxlen=10000)
        self.active_alerts: Dict[str, Dict[str, Any]] = {}

        # Setup logging
        self._setup_logging()

        # Health monitoring
        self.health_check_interval = 30  # seconds
        self.health_monitor_active = False

    def _setup_logging(self):
        """Setup production logging"""
        log_file = os.path.join(self.output_dir, f"production_{datetime.now().strftime('%Y%m%d')}.log")

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger("ProductionErrorHandler")

    def start_monitoring(self):
        """Start production monitoring"""
        self.health_monitor_active = True

        # Start health check thread
        health_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
        health_thread.start()

        # Register data quality alert callback
        self.data_quality.register_alert_callback(self._handle_data_quality_alert)

        self.logger.info("Production error handling started")
        print("🔍 Production monitoring started")

    def stop_monitoring(self):
        """Stop production monitoring"""
        self.health_monitor_active = False
        self.logger.info("Production error handling stopped")
        print("🛑 Production monitoring stopped")

    def register_stream(self, stream_name: str, recovery_callback: Callable):
        """Register stream for monitoring"""
        self.stream_recovery.register_stream(stream_name, recovery_callback)
        self.logger.info(f"Registered stream for monitoring: {stream_name}")

    def register_component(self, component_name: str, failover_callback: Callable):
        """Register component for failover monitoring"""
        self.failover_manager.register_component(component_name, failover_callback)
        self.logger.info(f"Registered component for failover: {component_name}")

    def record_error(self, component: str, error_type: str, message: str,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Dict[str, Any] = None):
        """Record an error event"""
        error_event = ErrorEvent(
            error_id=f"err_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.now(),
            component=component,
            error_type=error_type,
            severity=severity,
            message=message,
            context=context or {}
        )

        self.error_history.append(error_event)
        self.logger.error(f"{component} - {error_type}: {message}")

        # Handle critical errors immediately
        if severity == ErrorSeverity.CRITICAL:
            self._handle_critical_error(error_event)

        return error_event.error_id

    def record_component_operation(self, component_name: str, success: bool,
                                  response_time_ms: float = 0):
        """Record component operation result"""
        self.failover_manager.record_component_result(component_name, success, response_time_ms)

        if not success:
            self.record_error(
                component_name,
                "OPERATION_FAILURE",
                f"Component operation failed (response_time: {response_time_ms}ms)",
                ErrorSeverity.HIGH
            )

    def check_data_quality(self, data: Dict[str, Any], source: str) -> float:
        """Check data quality"""
        return self.data_quality.check_data_quality(data, source)

    def update_stream_health(self, stream_name: str, connected: bool, data_received: bool = False):
        """Update stream health"""
        self.stream_recovery.update_stream_health(stream_name, connected, data_received)

    def _handle_critical_error(self, error_event: ErrorEvent):
        """Handle critical errors immediately"""
        print(f"🚨 CRITICAL ERROR: {error_event.component} - {error_event.message}")

        # Generate immediate alert
        alert = {
            "type": "CRITICAL_ERROR",
            "timestamp": error_event.timestamp,
            "component": error_event.component,
            "error_type": error_event.error_type,
            "message": error_event.message,
            "context": error_event.context
        }

        # Store active alert
        alert_key = f"{error_event.component}_{error_event.error_type}"
        self.active_alerts[alert_key] = alert

        # Save to file
        self._save_alert(alert)

    def _handle_data_quality_alert(self, alert: Dict[str, Any]):
        """Handle data quality alerts"""
        alert_key = f"data_quality_{alert['source']}"
        self.active_alerts[alert_key] = alert

        self.logger.warning(f"Data quality alert: {alert['source']} score={alert['quality_score']}")
        self._save_alert(alert)

    def _health_monitor_loop(self):
        """Main health monitoring loop"""
        while self.health_monitor_active:
            try:
                self._perform_health_check()
                time.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")
                time.sleep(5)

    def _perform_health_check(self):
        """Perform periodic health check"""
        # Check component health
        for component_name, component in self.failover_manager.component_states.items():
            age_minutes = (datetime.now() - component.last_check).total_seconds() / 60

            if age_minutes > 5:  # No activity for 5 minutes
                self.logger.warning(f"Component {component_name} inactive for {age_minutes:.1f} minutes")

        # Check stream health
        for stream_name, stream in self.stream_recovery.streams.items():
            if stream.connected:
                age_minutes = (datetime.now() - stream.last_data_received).total_seconds() / 60

                if age_minutes > 2:  # No data for 2 minutes
                    self.logger.warning(f"Stream {stream_name} no data for {age_minutes:.1f} minutes")
                    self.stream_recovery.update_stream_health(stream_name, False)

    def _save_alert(self, alert: Dict[str, Any]):
        """Save alert to file"""
        alert_file = os.path.join(
            self.output_dir,
            f"alerts_{datetime.now().strftime('%Y%m%d')}.json"
        )

        # Load existing alerts
        alerts = []
        if os.path.exists(alert_file):
            try:
                with open(alert_file, 'r') as f:
                    alerts = json.load(f)
            except:
                pass

        # Add new alert
        alerts.append({**alert, "timestamp": alert["timestamp"].isoformat()})

        # Save alerts
        with open(alert_file, 'w') as f:
            json.dump(alerts, f, indent=2, default=str)

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        health_report = {
            "timestamp": datetime.now(),
            "overall_status": "HEALTHY",
            "components": {},
            "streams": {},
            "recent_errors": len([e for e in self.error_history if
                                (datetime.now() - e.timestamp).total_seconds() < 3600]),
            "active_alerts": len(self.active_alerts)
        }

        # Component health
        unhealthy_components = 0
        for name, component in self.failover_manager.component_states.items():
            health_report["components"][name] = {
                "status": component.status.value,
                "fallback_active": component.fallback_active,
                "consecutive_failures": component.consecutive_failures,
                "success_rate": component.success_rate_1h
            }

            if component.status != ComponentStatus.HEALTHY:
                unhealthy_components += 1

        # Stream health
        disconnected_streams = 0
        for name, stream in self.stream_recovery.streams.items():
            health_report["streams"][name] = {
                "connected": stream.connected,
                "reconnection_attempts": stream.reconnection_attempts,
                "last_data_age_minutes": (datetime.now() - stream.last_data_received).total_seconds() / 60
            }

            if not stream.connected:
                disconnected_streams += 1

        # Determine overall status
        if health_report["active_alerts"] > 0 or unhealthy_components > 0:
            health_report["overall_status"] = "DEGRADED"

        if disconnected_streams > 0 or unhealthy_components > len(self.failover_manager.component_states) / 2:
            health_report["overall_status"] = "UNHEALTHY"

        return health_report


# Module-level convenience functions
def create_error_handler() -> ProductionErrorHandler:
    """Create production error handler instance"""
    return ProductionErrorHandler()


# Example recovery callbacks
def reconnect_mbo_stream() -> bool:
    """Example MBO stream reconnection"""
    try:
        # In production, implement actual reconnection logic
        print("🔄 Reconnecting MBO stream...")
        time.sleep(1)  # Simulate reconnection time
        return True
    except Exception as e:
        print(f"Reconnection failed: {e}")
        return False


def fallback_to_v1() -> bool:
    """Example fallback to v1.0"""
    try:
        # In production, implement actual fallback logic
        print("🔄 Falling back to v1.0 algorithm...")
        return True
    except Exception as e:
        print(f"Fallback failed: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    error_handler = create_error_handler()

    # Start monitoring
    error_handler.start_monitoring()

    # Register components
    error_handler.register_stream("mbo_stream", reconnect_mbo_stream)
    error_handler.register_component("ifd_v3", fallback_to_v1)

    # Simulate some operations
    print("Testing error handling...")

    # Test successful operation
    error_handler.record_component_operation("ifd_v3", True, 150)

    # Test data quality
    good_data = {"symbol": "NQM25", "strike": 21350, "volume": 1000, "open_interest": 5000}
    bad_data = {"symbol": None, "strike": 21350}

    score1 = error_handler.check_data_quality(good_data, "test_source")
    score2 = error_handler.check_data_quality(bad_data, "test_source")

    print(f"Data quality scores: {score1:.2f}, {score2:.2f}")

    # Test stream health
    error_handler.update_stream_health("mbo_stream", True, True)
    error_handler.update_stream_health("mbo_stream", False)  # Trigger recovery

    # Get health report
    health = error_handler.get_system_health()
    print(f"System health: {health['overall_status']}")

    time.sleep(2)
    error_handler.stop_monitoring()
