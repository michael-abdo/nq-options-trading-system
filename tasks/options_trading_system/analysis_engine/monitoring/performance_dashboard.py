#!/usr/bin/env python3
"""
Production Performance Monitoring Dashboard for IFD v3.0

This module provides real-time performance monitoring including:
- Signal accuracy tracking dashboard
- Cost consumption monitoring
- System performance metrics
- Real-time alerts and notifications

Features:
- Live signal accuracy visualization
- Cost tracking and budget alerts
- System health monitoring
- Performance comparison dashboards
- Alert management system
"""

import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from collections import deque, defaultdict
from enum import Enum
import statistics


class MetricType(Enum):
    """Types of metrics tracked"""
    SIGNAL_ACCURACY = "SIGNAL_ACCURACY"
    COST_CONSUMPTION = "COST_CONSUMPTION"
    SYSTEM_PERFORMANCE = "SYSTEM_PERFORMANCE"
    ALGORITHM_COMPARISON = "ALGORITHM_COMPARISON"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class SignalMetric:
    """Signal accuracy metric"""
    timestamp: datetime
    algorithm_version: str
    symbol: str

    # Signal details
    signal_id: str
    confidence: float
    predicted_direction: str
    actual_direction: Optional[str] = None

    # Accuracy tracking
    prediction_correct: Optional[bool] = None
    response_time_ms: float = 0.0

    # Trading results
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None


@dataclass
class CostMetric:
    """Cost consumption metric"""
    timestamp: datetime
    provider: str
    algorithm_version: str

    # Cost details
    api_calls: int = 0
    streaming_minutes: float = 0.0
    data_points: int = 0

    # Cost breakdown
    base_cost: float = 0.0
    overage_cost: float = 0.0
    total_cost: float = 0.0

    # Budget tracking
    daily_budget_used: float = 0.0
    monthly_budget_used: float = 0.0


@dataclass
class SystemMetric:
    """System performance metric"""
    timestamp: datetime
    component: str

    # Performance metrics
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    response_time_ms: float = 0.0

    # Throughput metrics
    requests_per_second: float = 0.0
    success_rate: float = 1.0
    error_rate: float = 0.0

    # Health indicators
    uptime_seconds: float = 0.0
    health_score: float = 1.0


@dataclass
class DashboardAlert:
    """Dashboard alert"""
    alert_id: str
    timestamp: datetime
    level: AlertLevel
    metric_type: MetricType

    title: str
    message: str
    context: Dict[str, Any]

    # Alert state
    acknowledged: bool = False
    resolved: bool = False
    resolution_time: Optional[datetime] = None


class SignalAccuracyTracker:
    """Tracks and analyzes signal accuracy in real-time"""

    def __init__(self, history_size: int = 10000):
        self.signals: deque = deque(maxlen=history_size)
        self.accuracy_cache = {}
        self._lock = threading.Lock()

    def record_signal(self, signal: SignalMetric):
        """Record a new signal"""
        with self._lock:
            self.signals.append(signal)
            self._update_accuracy_cache()

    def update_signal_outcome(self, signal_id: str, actual_direction: str,
                             exit_price: float = None, pnl: float = None):
        """Update signal with actual outcome"""
        with self._lock:
            for signal in self.signals:
                if signal.signal_id == signal_id:
                    signal.actual_direction = actual_direction
                    signal.prediction_correct = (signal.predicted_direction == actual_direction)
                    signal.exit_price = exit_price
                    signal.pnl = pnl
                    break

            self._update_accuracy_cache()

    def get_accuracy_metrics(self, algorithm_version: str = None,
                           timeframe_hours: int = 24) -> Dict[str, Any]:
        """Get accuracy metrics for time period"""
        cutoff_time = datetime.now() - timedelta(hours=timeframe_hours)

        # Filter signals
        relevant_signals = [
            s for s in self.signals
            if s.timestamp >= cutoff_time and
            (algorithm_version is None or s.algorithm_version == algorithm_version) and
            s.prediction_correct is not None
        ]

        if not relevant_signals:
            return {
                "total_signals": 0,
                "accuracy": 0.0,
                "confidence_avg": 0.0,
                "response_time_avg": 0.0
            }

        # Calculate metrics
        correct_predictions = sum(1 for s in relevant_signals if s.prediction_correct)
        accuracy = correct_predictions / len(relevant_signals)

        confidence_avg = statistics.mean(s.confidence for s in relevant_signals)
        response_time_avg = statistics.mean(s.response_time_ms for s in relevant_signals)

        # P&L metrics
        signals_with_pnl = [s for s in relevant_signals if s.pnl is not None]
        total_pnl = sum(s.pnl for s in signals_with_pnl) if signals_with_pnl else 0
        avg_pnl = total_pnl / len(signals_with_pnl) if signals_with_pnl else 0

        return {
            "total_signals": len(relevant_signals),
            "accuracy": accuracy,
            "confidence_avg": confidence_avg,
            "response_time_avg": response_time_avg,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "win_rate": len([s for s in signals_with_pnl if s.pnl > 0]) / len(signals_with_pnl) if signals_with_pnl else 0
        }

    def get_hourly_accuracy_trend(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly accuracy trend"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        hourly_data = []

        for hour in range(hours):
            hour_start = start_time + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1)

            hour_signals = [
                s for s in self.signals
                if hour_start <= s.timestamp < hour_end and
                s.prediction_correct is not None
            ]

            if hour_signals:
                correct = sum(1 for s in hour_signals if s.prediction_correct)
                accuracy = correct / len(hour_signals)
            else:
                accuracy = 0.0

            hourly_data.append({
                "hour": hour_start.strftime("%H:00"),
                "timestamp": hour_start,
                "accuracy": accuracy,
                "signal_count": len(hour_signals)
            })

        return hourly_data

    def _update_accuracy_cache(self):
        """Update cached accuracy metrics"""
        # Cache common queries
        for algo in ["v1.0", "v3.0"]:
            for hours in [1, 6, 24]:
                cache_key = f"{algo}_{hours}h"
                self.accuracy_cache[cache_key] = self.get_accuracy_metrics(algo, hours)


class CostMonitor:
    """Monitors cost consumption and budget utilization"""

    def __init__(self):
        self.cost_records: deque = deque(maxlen=50000)
        self.budget_limits = {
            "daily": 100.0,
            "weekly": 500.0,
            "monthly": 2000.0
        }
        self.alert_thresholds = {
            "daily": 0.8,    # 80%
            "weekly": 0.85,  # 85%
            "monthly": 0.9   # 90%
        }
        self._lock = threading.Lock()

    def record_cost(self, cost_metric: CostMetric):
        """Record cost consumption"""
        with self._lock:
            self.cost_records.append(cost_metric)

    def get_cost_summary(self, timeframe_hours: int = 24) -> Dict[str, Any]:
        """Get cost summary for timeframe"""
        cutoff_time = datetime.now() - timedelta(hours=timeframe_hours)

        relevant_costs = [
            c for c in self.cost_records
            if c.timestamp >= cutoff_time
        ]

        # Group by provider and algorithm
        by_provider = defaultdict(float)
        by_algorithm = defaultdict(float)

        total_cost = 0.0
        total_api_calls = 0

        for cost in relevant_costs:
            by_provider[cost.provider] += cost.total_cost
            by_algorithm[cost.algorithm_version] += cost.total_cost
            total_cost += cost.total_cost
            total_api_calls += cost.api_calls

        return {
            "total_cost": total_cost,
            "total_api_calls": total_api_calls,
            "cost_per_call": total_cost / total_api_calls if total_api_calls > 0 else 0,
            "by_provider": dict(by_provider),
            "by_algorithm": dict(by_algorithm),
            "period_hours": timeframe_hours
        }

    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget utilization"""
        now = datetime.now()

        # Daily budget
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        daily_costs = [c for c in self.cost_records if c.timestamp >= day_start]
        daily_spent = sum(c.total_cost for c in daily_costs)

        # Monthly budget
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_costs = [c for c in self.cost_records if c.timestamp >= month_start]
        monthly_spent = sum(c.total_cost for c in monthly_costs)

        return {
            "daily": {
                "spent": daily_spent,
                "limit": self.budget_limits["daily"],
                "percentage": daily_spent / self.budget_limits["daily"],
                "remaining": self.budget_limits["daily"] - daily_spent
            },
            "monthly": {
                "spent": monthly_spent,
                "limit": self.budget_limits["monthly"],
                "percentage": monthly_spent / self.budget_limits["monthly"],
                "remaining": self.budget_limits["monthly"] - monthly_spent
            }
        }

    def check_budget_alerts(self) -> List[DashboardAlert]:
        """Check for budget threshold alerts"""
        alerts = []
        budget_status = self.get_budget_status()

        for period, status in budget_status.items():
            threshold = self.alert_thresholds[period]

            if status["percentage"] >= threshold:
                level = AlertLevel.CRITICAL if status["percentage"] >= 0.95 else AlertLevel.WARNING

                alert = DashboardAlert(
                    alert_id=f"budget_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    timestamp=datetime.now(),
                    level=level,
                    metric_type=MetricType.COST_CONSUMPTION,
                    title=f"{period.title()} Budget Alert",
                    message=f"{period.title()} budget {status['percentage']:.1%} used (${status['spent']:.2f} of ${status['limit']:.2f})",
                    context={"period": period, "status": status}
                )
                alerts.append(alert)

        return alerts


class SystemHealthMonitor:
    """Monitors system performance metrics"""

    def __init__(self):
        self.metrics: deque = deque(maxlen=10000)
        self.components = set()
        self._lock = threading.Lock()

    def record_metric(self, metric: SystemMetric):
        """Record system metric"""
        with self._lock:
            self.metrics.append(metric)
            self.components.add(metric.component)

    def get_component_health(self, component: str, minutes: int = 30) -> Dict[str, Any]:
        """Get health metrics for component"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        component_metrics = [
            m for m in self.metrics
            if m.component == component and m.timestamp >= cutoff_time
        ]

        if not component_metrics:
            return {
                "status": "NO_DATA",
                "avg_response_time": 0,
                "success_rate": 0,
                "health_score": 0
            }

        # Calculate averages
        avg_cpu = statistics.mean(m.cpu_usage_percent for m in component_metrics)
        avg_memory = statistics.mean(m.memory_usage_mb for m in component_metrics)
        avg_response_time = statistics.mean(m.response_time_ms for m in component_metrics)
        avg_success_rate = statistics.mean(m.success_rate for m in component_metrics)
        avg_health_score = statistics.mean(m.health_score for m in component_metrics)

        # Determine status
        if avg_health_score > 0.9 and avg_success_rate > 0.95:
            status = "HEALTHY"
        elif avg_health_score > 0.7 and avg_success_rate > 0.8:
            status = "DEGRADED"
        else:
            status = "UNHEALTHY"

        return {
            "status": status,
            "avg_cpu": avg_cpu,
            "avg_memory": avg_memory,
            "avg_response_time": avg_response_time,
            "success_rate": avg_success_rate,
            "health_score": avg_health_score,
            "sample_count": len(component_metrics)
        }

    def get_system_overview(self) -> Dict[str, Any]:
        """Get overall system health overview"""
        overview = {
            "timestamp": datetime.now(),
            "components": {},
            "overall_status": "HEALTHY",
            "alerts": []
        }

        unhealthy_count = 0

        for component in self.components:
            health = self.get_component_health(component)
            overview["components"][component] = health

            if health["status"] == "UNHEALTHY":
                unhealthy_count += 1

                # Generate alert for unhealthy components
                alert = DashboardAlert(
                    alert_id=f"health_{component}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    timestamp=datetime.now(),
                    level=AlertLevel.CRITICAL,
                    metric_type=MetricType.SYSTEM_PERFORMANCE,
                    title=f"Component Health Alert: {component}",
                    message=f"Component {component} is unhealthy (health score: {health['health_score']:.2f})",
                    context={"component": component, "health": health}
                )
                overview["alerts"].append(alert)

            elif health["status"] == "DEGRADED":
                # Generate warning for degraded components
                alert = DashboardAlert(
                    alert_id=f"degraded_{component}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    timestamp=datetime.now(),
                    level=AlertLevel.WARNING,
                    metric_type=MetricType.SYSTEM_PERFORMANCE,
                    title=f"Component Performance Warning: {component}",
                    message=f"Component {component} performance degraded (success rate: {health['success_rate']:.1%})",
                    context={"component": component, "health": health}
                )
                overview["alerts"].append(alert)

        # Set overall status
        if unhealthy_count > 0:
            overview["overall_status"] = "DEGRADED" if unhealthy_count == 1 else "UNHEALTHY"

        return overview


class PerformanceDashboard:
    """
    Main performance monitoring dashboard

    Provides unified interface for all monitoring components
    """

    def __init__(self, output_dir: str = "outputs/dashboard"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Initialize monitoring components
        self.signal_tracker = SignalAccuracyTracker()
        self.cost_monitor = CostMonitor()
        self.system_monitor = SystemHealthMonitor()

        # Alert management
        self.active_alerts: Dict[str, DashboardAlert] = {}
        self.alert_history: deque = deque(maxlen=1000)

        # Dashboard state
        self.dashboard_active = False
        self.update_interval = 30  # seconds

        # Setup logging
        self._setup_dashboard_logging()

    def _setup_dashboard_logging(self):
        """Setup dashboard logging"""
        import logging

        log_file = os.path.join(self.output_dir, f"dashboard_{datetime.now().strftime('%Y%m%d')}.log")

        self.logger = logging.getLogger("PerformanceDashboard")
        if not self.logger.handlers:
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def start_dashboard(self):
        """Start dashboard monitoring"""
        self.dashboard_active = True

        # Start update thread
        update_thread = threading.Thread(target=self._dashboard_update_loop, daemon=True)
        update_thread.start()

        self.logger.info("Performance dashboard started")
        print("📊 Performance dashboard started")

    def stop_dashboard(self):
        """Stop dashboard monitoring"""
        self.dashboard_active = False
        self.logger.info("Performance dashboard stopped")
        print("🛑 Performance dashboard stopped")

    def record_signal(self, algorithm_version: str, signal_data: Dict[str, Any],
                     response_time_ms: float = 0):
        """Record signal for accuracy tracking"""
        signal = SignalMetric(
            timestamp=datetime.now(),
            algorithm_version=algorithm_version,
            symbol=signal_data.get("symbol", ""),
            signal_id=signal_data.get("signal_id", f"sig_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"),
            confidence=signal_data.get("confidence", 0.0),
            predicted_direction=signal_data.get("direction", ""),
            response_time_ms=response_time_ms,
            entry_price=signal_data.get("entry_price")
        )

        self.signal_tracker.record_signal(signal)

    def update_signal_outcome(self, signal_id: str, actual_direction: str,
                             exit_price: float = None, pnl: float = None):
        """Update signal with trading outcome"""
        self.signal_tracker.update_signal_outcome(signal_id, actual_direction, exit_price, pnl)

    def record_cost(self, provider: str, algorithm_version: str, api_calls: int = 0,
                   streaming_minutes: float = 0, total_cost: float = 0):
        """Record cost consumption"""
        cost_metric = CostMetric(
            timestamp=datetime.now(),
            provider=provider,
            algorithm_version=algorithm_version,
            api_calls=api_calls,
            streaming_minutes=streaming_minutes,
            total_cost=total_cost
        )

        self.cost_monitor.record_cost(cost_metric)

    def record_system_metric(self, component: str, cpu_usage: float = 0,
                           memory_usage_mb: float = 0, response_time_ms: float = 0,
                           success_rate: float = 1.0):
        """Record system performance metric"""
        metric = SystemMetric(
            timestamp=datetime.now(),
            component=component,
            cpu_usage_percent=cpu_usage,
            memory_usage_mb=memory_usage_mb,
            response_time_ms=response_time_ms,
            success_rate=success_rate,
            health_score=min(success_rate, 1.0 - (response_time_ms / 10000))  # Simple health score
        )

        self.system_monitor.record_metric(metric)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        dashboard_data = {
            "timestamp": datetime.now(),
            "signal_accuracy": {
                "v1.0": self.signal_tracker.get_accuracy_metrics("v1.0", 24),
                "v3.0": self.signal_tracker.get_accuracy_metrics("v3.0", 24),
                "hourly_trend": self.signal_tracker.get_hourly_accuracy_trend(24)
            },
            "cost_monitoring": {
                "summary_24h": self.cost_monitor.get_cost_summary(24),
                "budget_status": self.cost_monitor.get_budget_status()
            },
            "system_health": self.system_monitor.get_system_overview(),
            "active_alerts": len(self.active_alerts),
            "alert_summary": {
                "critical": len([a for a in self.active_alerts.values() if a.level == AlertLevel.CRITICAL]),
                "warning": len([a for a in self.active_alerts.values() if a.level == AlertLevel.WARNING]),
                "info": len([a for a in self.active_alerts.values() if a.level == AlertLevel.INFO])
            }
        }

        return dashboard_data

    def get_algorithm_comparison(self) -> Dict[str, Any]:
        """Get v1.0 vs v3.0 performance comparison"""
        v1_metrics = self.signal_tracker.get_accuracy_metrics("v1.0", 24)
        v3_metrics = self.signal_tracker.get_accuracy_metrics("v3.0", 24)

        v1_cost = self.cost_monitor.get_cost_summary(24)
        # Convert deque to list to avoid slice issues
        cost_records_list = list(self.cost_monitor.cost_records)
        v3_cost_data = [c for c in cost_records_list
                       if c.algorithm_version == "v3.0" and
                       c.timestamp >= datetime.now() - timedelta(hours=24)]
        v3_cost_total = sum(c.total_cost for c in v3_cost_data)

        comparison = {
            "accuracy_comparison": {
                "v1.0": v1_metrics["accuracy"],
                "v3.0": v3_metrics["accuracy"],
                "winner": "v3.0" if v3_metrics["accuracy"] > v1_metrics["accuracy"] else "v1.0"
            },
            "signal_volume_comparison": {
                "v1.0": v1_metrics["total_signals"],
                "v3.0": v3_metrics["total_signals"],
                "winner": "v3.0" if v3_metrics["total_signals"] > v1_metrics["total_signals"] else "v1.0"
            },
            "cost_efficiency": {
                "v1.0_cost_per_signal": (v1_cost["total_cost"] / v1_metrics["total_signals"]) if v1_metrics["total_signals"] > 0 else 0,
                "v3.0_cost_per_signal": (v3_cost_total / v3_metrics["total_signals"]) if v3_metrics["total_signals"] > 0 else 0
            },
            "pnl_comparison": {
                "v1.0": v1_metrics.get("total_pnl", 0),
                "v3.0": v3_metrics.get("total_pnl", 0),
                "winner": "v3.0" if v3_metrics.get("total_pnl", 0) > v1_metrics.get("total_pnl", 0) else "v1.0"
            }
        }

        return comparison

    def _dashboard_update_loop(self):
        """Main dashboard update loop"""
        while self.dashboard_active:
            try:
                self._check_alerts()
                self._save_dashboard_snapshot()
                time.sleep(self.update_interval)
            except Exception as e:
                self.logger.error(f"Dashboard update error: {e}")
                time.sleep(5)

    def _check_alerts(self):
        """Check for new alerts"""
        new_alerts = []

        # Check budget alerts
        budget_alerts = self.cost_monitor.check_budget_alerts()
        new_alerts.extend(budget_alerts)

        # Check system health alerts
        system_overview = self.system_monitor.get_system_overview()
        new_alerts.extend(system_overview.get("alerts", []))

        # Add new alerts
        for alert in new_alerts:
            if alert.alert_id not in self.active_alerts:
                self.active_alerts[alert.alert_id] = alert
                self.alert_history.append(alert)
                self.logger.warning(f"New alert: {alert.title} - {alert.message}")
                print(f"🚨 {alert.level.value}: {alert.title}")

    def _save_dashboard_snapshot(self):
        """Save dashboard snapshot to file"""
        snapshot = self.get_dashboard_data()

        snapshot_file = os.path.join(
            self.output_dir,
            f"dashboard_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        # Convert datetime objects to strings
        def datetime_converter(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        snapshot_json = json.dumps(snapshot, indent=2, default=datetime_converter)

        with open(snapshot_file, 'w') as f:
            f.write(snapshot_json)

        # Keep only last 100 snapshots
        snapshot_files = [f for f in os.listdir(self.output_dir) if f.startswith("dashboard_snapshot_")]
        if len(snapshot_files) > 100:
            snapshot_files.sort()
            for old_file in snapshot_files[:-100]:
                os.remove(os.path.join(self.output_dir, old_file))

    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            self.logger.info(f"Alert acknowledged: {alert_id}")

    def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolution_time = datetime.now()
            del self.active_alerts[alert_id]
            self.logger.info(f"Alert resolved: {alert_id}")

    def generate_dashboard_report(self) -> str:
        """Generate formatted dashboard report"""
        data = self.get_dashboard_data()
        comparison = self.get_algorithm_comparison()

        report = f"""
📊 PERFORMANCE DASHBOARD REPORT
Generated: {data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 60}

🎯 SIGNAL ACCURACY (24h)
v1.0: {data['signal_accuracy']['v1.0']['accuracy']:.1%} ({data['signal_accuracy']['v1.0']['total_signals']} signals)
v3.0: {data['signal_accuracy']['v3.0']['accuracy']:.1%} ({data['signal_accuracy']['v3.0']['total_signals']} signals)
Winner: {comparison['accuracy_comparison']['winner']}

💰 COST MONITORING (24h)
Total Cost: ${data['cost_monitoring']['summary_24h']['total_cost']:.2f}
API Calls: {data['cost_monitoring']['summary_24h']['total_api_calls']:,}
Daily Budget: {data['cost_monitoring']['budget_status']['daily']['percentage']:.1%} used
Monthly Budget: {data['cost_monitoring']['budget_status']['monthly']['percentage']:.1%} used

🖥️ SYSTEM HEALTH
Overall Status: {data['system_health']['overall_status']}
Components Monitored: {len(data['system_health']['components'])}

🚨 ACTIVE ALERTS
Critical: {data['alert_summary']['critical']}
Warning: {data['alert_summary']['warning']}
Info: {data['alert_summary']['info']}

📈 ALGORITHM COMPARISON (24h)
Accuracy Winner: {comparison['accuracy_comparison']['winner']}
Signal Volume Winner: {comparison['signal_volume_comparison']['winner']}
P&L Winner: {comparison['pnl_comparison']['winner']}

{'=' * 60}
        """

        return report.strip()


# Module-level convenience functions
def create_dashboard() -> PerformanceDashboard:
    """Create performance dashboard instance"""
    return PerformanceDashboard()


if __name__ == "__main__":
    # Example usage
    dashboard = create_dashboard()

    # Start dashboard
    dashboard.start_dashboard()

    print("Testing dashboard components...")

    # Test signal recording
    signal_data = {
        "signal_id": "test_001",
        "symbol": "NQM25",
        "confidence": 0.85,
        "direction": "LONG",
        "entry_price": 21350
    }

    dashboard.record_signal("v3.0", signal_data, response_time_ms=150)
    dashboard.update_signal_outcome("test_001", "LONG", exit_price=21375, pnl=25.0)

    # Test cost recording
    dashboard.record_cost("DATABENTO", "v3.0", api_calls=100, total_cost=1.50)

    # Test system metrics
    dashboard.record_system_metric("ifd_v3", cpu_usage=45.0, memory_usage_mb=1024,
                                  response_time_ms=200, success_rate=0.98)

    # Get dashboard data
    time.sleep(2)
    data = dashboard.get_dashboard_data()

    print("\n" + dashboard.generate_dashboard_report())

    dashboard.stop_dashboard()
