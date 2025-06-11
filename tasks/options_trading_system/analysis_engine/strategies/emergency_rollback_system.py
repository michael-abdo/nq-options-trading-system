#!/usr/bin/env python3
"""
Emergency Rollback System for IFD v3.0 Production Environment

This module provides immediate rollback capabilities with minimal disruption
to trading operations when v3.0 encounters critical issues.

Features:
- Instant rollback triggers and execution
- State preservation and restoration
- Position safety management
- Real-time notification system
- Post-rollback analysis
- Integration with monitoring systems
"""

import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict
import logging


class RollbackTrigger(Enum):
    """Types of rollback triggers"""
    MANUAL = "MANUAL"
    PERFORMANCE_DEGRADATION = "PERFORMANCE_DEGRADATION"
    ERROR_THRESHOLD = "ERROR_THRESHOLD"
    POSITION_RISK = "POSITION_RISK"
    DATA_QUALITY = "DATA_QUALITY"
    SYSTEM_FAILURE = "SYSTEM_FAILURE"
    TIMEOUT = "TIMEOUT"
    EXTERNAL_SIGNAL = "EXTERNAL_SIGNAL"


class RollbackSeverity(Enum):
    """Rollback severity levels"""
    LOW = "LOW"           # Gradual rollback
    MEDIUM = "MEDIUM"     # Fast rollback
    HIGH = "HIGH"         # Immediate rollback
    CRITICAL = "CRITICAL" # Emergency stop


class RollbackStatus(Enum):
    """Rollback execution status"""
    STANDBY = "STANDBY"
    TRIGGERED = "TRIGGERED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    VERIFIED = "VERIFIED"


@dataclass
class RollbackConfig:
    """Emergency rollback configuration"""
    # Trigger thresholds
    max_error_rate: float = 0.1           # 10% error rate
    min_performance_ratio: float = 0.8    # v3.0 must be 80% as good as v1.0
    max_position_risk_percent: float = 5.0 # 5% portfolio risk
    max_drawdown_percent: float = 2.0     # 2% drawdown
    max_response_time_ms: float = 5000    # 5 seconds
    
    # Timing constraints
    rollback_timeout_seconds: int = 30    # 30 second rollback limit
    verification_period_minutes: int = 5  # 5 minutes post-rollback verification
    cooldown_period_minutes: int = 60     # 60 minutes before re-enabling v3.0
    
    # Position management
    close_open_positions: bool = False    # Whether to close v3.0 positions
    transfer_positions: bool = True       # Transfer positions to v1.0 management
    hedge_positions: bool = True          # Hedge risky positions during rollback
    
    # Notification settings
    immediate_alerts: List[str] = None    # Immediate notification channels
    escalation_alerts: List[str] = None   # Escalation notification channels
    
    # Safety controls
    require_manual_confirmation: bool = False  # Require human confirmation
    max_rollbacks_per_hour: int = 3           # Rollback rate limiting
    enable_circuit_breaker: bool = True       # Circuit breaker protection
    
    def __post_init__(self):
        if self.immediate_alerts is None:
            self.immediate_alerts = ["log", "console"]
        if self.escalation_alerts is None:
            self.escalation_alerts = ["log", "console", "email"]


@dataclass
class RollbackEvent:
    """Rollback event record"""
    event_id: str
    timestamp: datetime
    trigger: RollbackTrigger
    severity: RollbackSeverity
    
    description: str
    trigger_context: Dict[str, Any]
    
    # Execution details
    execution_start: Optional[datetime] = None
    execution_end: Optional[datetime] = None
    execution_duration_ms: float = 0.0
    
    # State preservation
    preserved_state: Optional[Dict[str, Any]] = None
    rollback_actions: List[str] = None
    
    # Results
    status: RollbackStatus = RollbackStatus.TRIGGERED
    success: bool = False
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.rollback_actions is None:
            self.rollback_actions = []


@dataclass
class SystemState:
    """System state snapshot for preservation"""
    timestamp: datetime
    
    # Algorithm state
    active_algorithm: str
    traffic_split: Dict[str, float]
    configuration: Dict[str, Any]
    
    # Positions
    open_positions: List[Dict[str, Any]]
    position_summary: Dict[str, float]
    total_exposure: float
    
    # Performance metrics
    recent_performance: Dict[str, Any]
    active_signals: List[Dict[str, Any]]
    
    # System health
    component_health: Dict[str, str]
    error_rates: Dict[str, float]
    response_times: Dict[str, float]


class PositionManager:
    """Manages positions during rollback"""
    
    def __init__(self):
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.position_history: deque = deque(maxlen=1000)
        self._lock = threading.Lock()
    
    def capture_positions(self) -> Dict[str, Any]:
        """Capture current position state"""
        with self._lock:
            position_snapshot = {
                "timestamp": datetime.now(),
                "positions": self.positions.copy(),
                "total_exposure": sum(abs(p.get("value", 0)) for p in self.positions.values()),
                "position_count": len(self.positions)
            }
            
            self.position_history.append(position_snapshot)
            return position_snapshot
    
    def transfer_positions_to_v1(self, positions: Dict[str, Any]) -> bool:
        """Transfer v3.0 positions to v1.0 management"""
        try:
            # In production, this would interface with actual trading system
            transfer_log = []
            
            for position_id, position in positions.get("positions", {}).items():
                if position.get("algorithm") == "v3.0":
                    # Mark for v1.0 management
                    position["algorithm"] = "v1.0"
                    position["transferred_at"] = datetime.now().isoformat()
                    position["transfer_reason"] = "v3.0_rollback"
                    
                    transfer_log.append({
                        "position_id": position_id,
                        "symbol": position.get("symbol"),
                        "quantity": position.get("quantity"),
                        "value": position.get("value")
                    })
            
            print(f"📊 Transferred {len(transfer_log)} positions to v1.0 management")
            return True
            
        except Exception as e:
            print(f"❌ Position transfer failed: {e}")
            return False
    
    def hedge_risky_positions(self, positions: Dict[str, Any], risk_threshold: float = 0.05) -> bool:
        """Hedge positions that exceed risk threshold"""
        try:
            hedge_actions = []
            total_value = sum(abs(p.get("value", 0)) for p in positions.get("positions", {}).values())
            
            for position_id, position in positions.get("positions", {}).items():
                position_risk = abs(position.get("value", 0)) / total_value if total_value > 0 else 0
                
                if position_risk > risk_threshold:
                    # In production, this would create actual hedge orders
                    hedge_action = {
                        "position_id": position_id,
                        "symbol": position.get("symbol"),
                        "hedge_size": position.get("quantity", 0) * 0.5,  # 50% hedge
                        "hedge_type": "protective_put" if position.get("direction") == "LONG" else "protective_call",
                        "timestamp": datetime.now().isoformat()
                    }
                    hedge_actions.append(hedge_action)
            
            if hedge_actions:
                print(f"🛡️ Created {len(hedge_actions)} hedge positions")
            
            return True
            
        except Exception as e:
            print(f"❌ Position hedging failed: {e}")
            return False


class NotificationSystem:
    """Handles emergency notifications"""
    
    def __init__(self, config: RollbackConfig):
        self.config = config
        self.notification_history: deque = deque(maxlen=1000)
        self.escalation_active = False
    
    def send_immediate_alert(self, event: RollbackEvent):
        """Send immediate rollback alert"""
        alert_message = f"""
🚨 EMERGENCY ROLLBACK TRIGGERED
Event ID: {event.event_id}
Trigger: {event.trigger.value}
Severity: {event.severity.value}
Time: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

Description: {event.description}

Immediate action required to verify system state.
        """.strip()
        
        self._send_to_channels(alert_message, self.config.immediate_alerts)
        
        # Record notification
        self.notification_history.append({
            "timestamp": datetime.now(),
            "type": "immediate_alert",
            "event_id": event.event_id,
            "channels": self.config.immediate_alerts
        })
    
    def send_escalation_alert(self, event: RollbackEvent):
        """Send escalation alert for failed rollbacks"""
        if self.escalation_active:
            return  # Prevent spam
        
        self.escalation_active = True
        
        escalation_message = f"""
🔥 CRITICAL: ROLLBACK ESCALATION
Event ID: {event.event_id}
Status: {event.status.value}
Error: {event.error_message or 'Unknown error'}

IMMEDIATE HUMAN INTERVENTION REQUIRED
System may be in unstable state.

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        self._send_to_channels(escalation_message, self.config.escalation_alerts)
        
        # Schedule escalation reset
        threading.Timer(300, self._reset_escalation).start()  # 5 minutes
    
    def send_completion_alert(self, event: RollbackEvent):
        """Send rollback completion notification"""
        status_emoji = "✅" if event.success else "❌"
        completion_message = f"""
{status_emoji} ROLLBACK COMPLETED
Event ID: {event.event_id}
Status: {"SUCCESS" if event.success else "FAILED"}
Duration: {event.execution_duration_ms:.0f}ms

System Status: {"Stable on v1.0" if event.success else "Requires attention"}
Time: {event.execution_end.strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        self._send_to_channels(completion_message, self.config.immediate_alerts)
    
    def _send_to_channels(self, message: str, channels: List[str]):
        """Send message to specified channels"""
        for channel in channels:
            try:
                if channel == "console":
                    print(f"\n{message}\n")
                elif channel == "log":
                    logging.critical(message)
                elif channel == "email":
                    # In production, integrate with email service
                    print(f"📧 EMAIL ALERT: {message[:100]}...")
                elif channel == "sms":
                    # In production, integrate with SMS service
                    print(f"📱 SMS ALERT: {message[:100]}...")
                elif channel == "slack":
                    # In production, integrate with Slack API
                    print(f"📢 SLACK ALERT: {message[:100]}...")
            except Exception as e:
                print(f"⚠️ Failed to send alert to {channel}: {e}")
    
    def _reset_escalation(self):
        """Reset escalation flag"""
        self.escalation_active = False


class StatePreserver:
    """Preserves and restores system state"""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.state_snapshots: deque = deque(maxlen=100)
    
    def capture_system_state(self, traffic_split: Dict[str, float], 
                           configuration: Dict[str, Any],
                           performance_data: Dict[str, Any]) -> SystemState:
        """Capture comprehensive system state"""
        state = SystemState(
            timestamp=datetime.now(),
            active_algorithm="v3.0" if traffic_split.get("v3.0", 0) > 50 else "v1.0",
            traffic_split=traffic_split.copy(),
            configuration=configuration.copy(),
            open_positions=[],  # Would be populated from actual trading system
            position_summary={},
            total_exposure=0.0,
            recent_performance=performance_data.copy(),
            active_signals=[],
            component_health={},
            error_rates={},
            response_times={}
        )
        
        # Save state snapshot
        self._save_state_snapshot(state)
        self.state_snapshots.append(state)
        
        return state
    
    def restore_v1_state(self) -> bool:
        """Restore system to last known good v1.0 state"""
        try:
            # Find most recent v1.0 state
            v1_state = None
            for state in reversed(self.state_snapshots):
                if state.active_algorithm == "v1.0":
                    v1_state = state
                    break
            
            if v1_state is None:
                print("⚠️ No v1.0 state found, using default configuration")
                return False
            
            print(f"🔄 Restoring v1.0 state from {v1_state.timestamp.strftime('%H:%M:%S')}")
            
            # In production, this would restore actual system configuration
            # For now, we simulate successful restoration
            return True
            
        except Exception as e:
            print(f"❌ State restoration failed: {e}")
            return False
    
    def _save_state_snapshot(self, state: SystemState):
        """Save state snapshot to file"""
        snapshot_file = os.path.join(
            self.output_dir,
            f"state_snapshot_{state.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        try:
            state_dict = asdict(state)
            state_dict["timestamp"] = state.timestamp.isoformat()
            
            with open(snapshot_file, 'w') as f:
                json.dump(state_dict, f, indent=2, default=str)
                
        except Exception as e:
            print(f"⚠️ Failed to save state snapshot: {e}")


class EmergencyRollbackSystem:
    """
    Main emergency rollback system
    
    Provides immediate rollback capabilities with comprehensive safety
    controls and state management.
    """
    
    def __init__(self, config: RollbackConfig = None, output_dir: str = "outputs/rollback"):
        self.config = config or RollbackConfig()
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize components
        self.position_manager = PositionManager()
        self.notification_system = NotificationSystem(self.config)
        self.state_preserver = StatePreserver(output_dir)
        
        # Rollback state
        self.rollback_status = RollbackStatus.STANDBY
        self.last_rollback_time: Optional[datetime] = None
        self.rollback_count_1h = 0
        self.circuit_breaker_active = False
        
        # Event tracking
        self.rollback_events: deque = deque(maxlen=1000)
        self.trigger_conditions: Dict[RollbackTrigger, bool] = {}
        
        # Current system state
        self.current_traffic_split = {"v1.0": 100.0, "v3.0": 0.0}
        self.current_configuration = {}
        self.current_performance = {}
        
        # Monitoring
        self.monitoring_active = False
        self._lock = threading.Lock()
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup rollback logging"""
        log_file = os.path.join(self.output_dir, f"rollback_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger("EmergencyRollback")
    
    def start_monitoring(self):
        """Start rollback monitoring"""
        self.monitoring_active = True
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        
        self.logger.info("Emergency rollback monitoring started")
        print("🔍 Emergency rollback monitoring started")
    
    def stop_monitoring(self):
        """Stop rollback monitoring"""
        self.monitoring_active = False
        self.logger.info("Emergency rollback monitoring stopped")
        print("🛑 Emergency rollback monitoring stopped")
    
    def update_system_state(self, traffic_split: Dict[str, float], 
                          configuration: Dict[str, Any],
                          performance_data: Dict[str, Any]):
        """Update current system state"""
        with self._lock:
            self.current_traffic_split = traffic_split.copy()
            self.current_configuration = configuration.copy()
            self.current_performance = performance_data.copy()
    
    def check_rollback_conditions(self) -> Optional[Tuple[RollbackTrigger, RollbackSeverity, str]]:
        """Check if rollback conditions are met"""
        performance = self.current_performance
        
        # Performance degradation check
        v1_accuracy = performance.get("v1_accuracy", 1.0)
        v3_accuracy = performance.get("v3_accuracy", 1.0)
        
        if v1_accuracy > 0:
            performance_ratio = v3_accuracy / v1_accuracy
            if performance_ratio < self.config.min_performance_ratio:
                return (
                    RollbackTrigger.PERFORMANCE_DEGRADATION,
                    RollbackSeverity.HIGH,
                    f"v3.0 performance ratio: {performance_ratio:.2f}"
                )
        
        # Error rate check
        error_rate = performance.get("error_rate", 0.0)
        if error_rate > self.config.max_error_rate:
            severity = RollbackSeverity.CRITICAL if error_rate > 0.2 else RollbackSeverity.HIGH
            return (
                RollbackTrigger.ERROR_THRESHOLD,
                severity,
                f"Error rate: {error_rate:.1%}"
            )
        
        # Response time check
        response_time = performance.get("response_time_ms", 0.0)
        if response_time > self.config.max_response_time_ms:
            return (
                RollbackTrigger.TIMEOUT,
                RollbackSeverity.MEDIUM,
                f"Response time: {response_time:.0f}ms"
            )
        
        # Position risk check
        position_risk = performance.get("position_risk_percent", 0.0)
        if position_risk > self.config.max_position_risk_percent:
            return (
                RollbackTrigger.POSITION_RISK,
                RollbackSeverity.CRITICAL,
                f"Position risk: {position_risk:.1f}%"
            )
        
        return None
    
    def trigger_rollback(self, trigger: RollbackTrigger = RollbackTrigger.MANUAL,
                        severity: RollbackSeverity = RollbackSeverity.HIGH,
                        reason: str = "Manual rollback triggered") -> str:
        """Trigger emergency rollback"""
        # Check circuit breaker and rate limiting
        if not self._can_execute_rollback():
            return "Rollback blocked by circuit breaker or rate limiting"
        
        # Create rollback event
        event = RollbackEvent(
            event_id=f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.now(),
            trigger=trigger,
            severity=severity,
            description=reason,
            trigger_context=self.current_performance.copy()
        )
        
        self.rollback_events.append(event)
        self.rollback_status = RollbackStatus.TRIGGERED
        
        # Send immediate alert
        self.notification_system.send_immediate_alert(event)
        
        self.logger.critical(f"Rollback triggered: {reason}")
        print(f"🚨 Rollback triggered: {reason}")
        
        # Execute rollback
        success = self._execute_rollback(event)
        
        if not success:
            self.notification_system.send_escalation_alert(event)
        
        return event.event_id
    
    def _can_execute_rollback(self) -> bool:
        """Check if rollback can be executed"""
        # Circuit breaker check
        if self.circuit_breaker_active:
            print("⛔ Circuit breaker active - rollback blocked")
            return False
        
        # Rate limiting check
        current_time = datetime.now()
        one_hour_ago = current_time - timedelta(hours=1)
        
        recent_rollbacks = [
            event for event in self.rollback_events
            if event.timestamp >= one_hour_ago
        ]
        
        if len(recent_rollbacks) >= self.config.max_rollbacks_per_hour:
            print(f"⛔ Rate limit exceeded ({len(recent_rollbacks)} rollbacks in last hour)")
            self.circuit_breaker_active = True
            threading.Timer(3600, self._reset_circuit_breaker).start()  # Reset in 1 hour
            return False
        
        # Manual confirmation check
        if self.config.require_manual_confirmation:
            print("⚠️ Manual confirmation required for rollback")
            return False
        
        return True
    
    def _execute_rollback(self, event: RollbackEvent) -> bool:
        """Execute the rollback process"""
        event.execution_start = datetime.now()
        event.status = RollbackStatus.EXECUTING
        self.rollback_status = RollbackStatus.EXECUTING
        
        try:
            # Step 1: Capture current state
            print("📸 Capturing system state...")
            current_state = self.state_preserver.capture_system_state(
                self.current_traffic_split,
                self.current_configuration,
                self.current_performance
            )
            event.preserved_state = asdict(current_state)
            event.rollback_actions.append("state_captured")
            
            # Step 2: Handle positions
            if self.config.transfer_positions or self.config.hedge_positions:
                print("📊 Managing positions...")
                positions = self.position_manager.capture_positions()
                
                if self.config.transfer_positions:
                    if self.position_manager.transfer_positions_to_v1(positions):
                        event.rollback_actions.append("positions_transferred")
                    else:
                        raise Exception("Position transfer failed")
                
                if self.config.hedge_positions:
                    if self.position_manager.hedge_risky_positions(positions):
                        event.rollback_actions.append("positions_hedged")
                    else:
                        print("⚠️ Position hedging failed but continuing rollback")
            
            # Step 3: Switch traffic to v1.0
            print("🔄 Switching traffic to v1.0...")
            self.current_traffic_split = {"v1.0": 100.0, "v3.0": 0.0}
            event.rollback_actions.append("traffic_switched")
            
            # Step 4: Restore v1.0 configuration
            print("⚙️ Restoring v1.0 configuration...")
            if self.state_preserver.restore_v1_state():
                event.rollback_actions.append("config_restored")
            else:
                print("⚠️ Configuration restoration failed but continuing")
            
            # Rollback completed successfully
            event.execution_end = datetime.now()
            event.execution_duration_ms = (event.execution_end - event.execution_start).total_seconds() * 1000
            event.status = RollbackStatus.COMPLETED
            event.success = True
            
            self.rollback_status = RollbackStatus.COMPLETED
            self.last_rollback_time = datetime.now()
            
            self.logger.info(f"Rollback completed successfully in {event.execution_duration_ms:.0f}ms")
            print(f"✅ Rollback completed in {event.execution_duration_ms:.0f}ms")
            
            # Send completion notification
            self.notification_system.send_completion_alert(event)
            
            # Start verification period
            threading.Timer(
                self.config.verification_period_minutes * 60,
                self._verify_rollback_success,
                [event.event_id]
            ).start()
            
            return True
            
        except Exception as e:
            # Rollback failed
            event.execution_end = datetime.now()
            event.execution_duration_ms = (event.execution_end - event.execution_start).total_seconds() * 1000
            event.status = RollbackStatus.FAILED
            event.success = False
            event.error_message = str(e)
            
            self.rollback_status = RollbackStatus.FAILED
            
            self.logger.error(f"Rollback failed: {e}")
            print(f"❌ Rollback failed: {e}")
            
            return False
    
    def _verify_rollback_success(self, event_id: str):
        """Verify rollback was successful"""
        # In production, this would check actual system metrics
        print(f"✅ Rollback verification completed for {event_id}")
        
        # Find the event and mark as verified
        for event in self.rollback_events:
            if event.event_id == event_id:
                event.status = RollbackStatus.VERIFIED
                break
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker"""
        self.circuit_breaker_active = False
        print("🔓 Circuit breaker reset")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Only monitor if not in rollback
                if self.rollback_status == RollbackStatus.STANDBY:
                    condition = self.check_rollback_conditions()
                    
                    if condition:
                        trigger, severity, reason = condition
                        print(f"⚠️ Rollback condition detected: {reason}")
                        
                        # Auto-trigger for critical conditions
                        if severity == RollbackSeverity.CRITICAL:
                            self.trigger_rollback(trigger, severity, reason)
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                time.sleep(10)
    
    def get_rollback_status(self) -> Dict[str, Any]:
        """Get current rollback system status"""
        return {
            "status": self.rollback_status.value,
            "circuit_breaker_active": self.circuit_breaker_active,
            "last_rollback": self.last_rollback_time.isoformat() if self.last_rollback_time else None,
            "rollbacks_1h": len([
                e for e in self.rollback_events
                if e.timestamp >= datetime.now() - timedelta(hours=1)
            ]),
            "total_rollbacks": len(self.rollback_events),
            "monitoring_active": self.monitoring_active,
            "current_traffic_split": self.current_traffic_split,
            "trigger_conditions": {
                trigger.value: self.trigger_conditions.get(trigger, False)
                for trigger in RollbackTrigger
            }
        }
    
    def generate_rollback_report(self) -> str:
        """Generate rollback system status report"""
        status = self.get_rollback_status()
        
        recent_events = [
            event for event in self.rollback_events
            if event.timestamp >= datetime.now() - timedelta(hours=24)
        ]
        
        report = f"""
🚨 EMERGENCY ROLLBACK SYSTEM STATUS
Status: {status['status']}
Circuit Breaker: {"ACTIVE" if status['circuit_breaker_active'] else "STANDBY"}
Monitoring: {"ACTIVE" if status['monitoring_active'] else "INACTIVE"}
{'=' * 60}

📊 TRAFFIC SPLIT
v1.0: {status['current_traffic_split']['v1.0']:.0f}%
v3.0: {status['current_traffic_split']['v3.0']:.0f}%

📈 ROLLBACK STATISTICS
Total Rollbacks: {status['total_rollbacks']}
Last Hour: {status['rollbacks_1h']}
Last 24 Hours: {len(recent_events)}
Last Rollback: {status['last_rollback'] or 'Never'}

🎯 RECENT EVENTS
{chr(10).join([f"  {e.timestamp.strftime('%H:%M:%S')} - {e.trigger.value}: {e.description[:50]}..." for e in recent_events[-5:]])}

{'=' * 60}
        """
        
        return report.strip()


# Module-level convenience functions
def create_rollback_system(config: RollbackConfig = None) -> EmergencyRollbackSystem:
    """Create emergency rollback system instance"""
    return EmergencyRollbackSystem(config)


def create_default_rollback_config() -> RollbackConfig:
    """Create default rollback configuration"""
    return RollbackConfig()


if __name__ == "__main__":
    # Example usage
    config = create_default_rollback_config()
    rollback_system = create_rollback_system(config)
    
    # Start monitoring
    rollback_system.start_monitoring()
    
    print("Testing rollback system...")
    
    # Simulate normal operation
    for i in range(10):
        # Update system state with gradually degrading performance
        performance_data = {
            "v1_accuracy": 0.85,
            "v3_accuracy": 0.87 - (i * 0.02),  # Gradually degrading
            "error_rate": i * 0.02,
            "response_time_ms": 1000 + (i * 200),
            "position_risk_percent": i * 0.5
        }
        
        traffic_split = {"v1.0": 20.0, "v3.0": 80.0}
        config_data = {"algorithm": "v3.0"}
        
        rollback_system.update_system_state(traffic_split, config_data, performance_data)
        
        print(f"\nIteration {i+1}:")
        print(f"v3.0 Accuracy: {performance_data['v3_accuracy']:.2f}")
        print(f"Error Rate: {performance_data['error_rate']:.1%}")
        
        # Check conditions
        condition = rollback_system.check_rollback_conditions()
        if condition:
            trigger, severity, reason = condition
            print(f"⚠️ Rollback condition: {reason}")
            
            if i >= 5:  # Trigger rollback after some degradation
                event_id = rollback_system.trigger_rollback(trigger, severity, reason)
                print(f"🚨 Rollback triggered: {event_id}")
                break
        
        time.sleep(1)
    
    # Final status
    print("\nFinal Status:")
    print(rollback_system.generate_rollback_report())
    
    rollback_system.stop_monitoring()