#!/usr/bin/env python3
"""
Production Monitoring System for IFD v3.0 Trading System

This script provides comprehensive monitoring for production metrics including:
- System performance and health
- Trading signal accuracy and timing
- Cost management and budget tracking
- Error rates and system reliability
- Business metrics and ROI tracking
"""

import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys
import os

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import timezone utilities
from utils.timezone_utils import get_eastern_time

class ProductionMonitor:
    """Production monitoring system for IFD v3.0"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/monitoring.json"
        self.metrics_file = "outputs/monitoring/production_metrics.json"
        self.alerts_file = "outputs/monitoring/alerts.json"
        self.dashboard_file = "outputs/monitoring/dashboard.json"

        # Ensure monitoring directory exists
        os.makedirs("outputs/monitoring", exist_ok=True)

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('outputs/monitoring/monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Load configuration
        self.config = self._load_config()

        # Initialize metrics storage
        self.metrics = {
            "timestamp": get_eastern_time().isoformat(),
            "system_health": {},
            "trading_metrics": {},
            "cost_metrics": {},
            "error_metrics": {},
            "business_metrics": {}
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load monitoring configuration"""
        default_config = {
            "monitoring_interval": 60,  # seconds
            "alert_thresholds": {
                "signal_accuracy": 0.70,  # Alert if below 70%
                "system_latency": 150,    # Alert if above 150ms
                "error_rate": 0.05,       # Alert if above 5%
                "daily_cost": 10.0,       # Alert if above $10/day
                "uptime": 0.995           # Alert if below 99.5%
            },
            "metrics_retention_days": 30,
            "dashboard_refresh_interval": 300  # 5 minutes
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                self.logger.warning(f"Error loading config: {e}. Using defaults.")

        return default_config

    def collect_system_health(self) -> Dict[str, Any]:
        """Collect system health metrics"""
        health_metrics = {
            "timestamp": get_eastern_time().isoformat(),
            "cpu_usage": self._get_cpu_usage(),
            "memory_usage": self._get_memory_usage(),
            "disk_usage": self._get_disk_usage(),
            "network_status": self._check_network_connectivity(),
            "service_status": self._check_service_status()
        }

        self.metrics["system_health"] = health_metrics
        return health_metrics

    def collect_trading_metrics(self) -> Dict[str, Any]:
        """Collect trading performance metrics"""
        trading_metrics = {
            "timestamp": get_eastern_time().isoformat(),
            "signals_generated": self._count_signals_today(),
            "signal_accuracy": self._calculate_signal_accuracy(),
            "average_latency": self._calculate_average_latency(),
            "win_loss_ratio": self._calculate_win_loss_ratio(),
            "successful_trades": self._count_successful_trades(),
            "failed_trades": self._count_failed_trades()
        }

        self.metrics["trading_metrics"] = trading_metrics
        return trading_metrics

    def collect_cost_metrics(self) -> Dict[str, Any]:
        """Collect cost and budget metrics"""
        cost_metrics = {
            "timestamp": get_eastern_time().isoformat(),
            "daily_cost": self._calculate_daily_cost(),
            "monthly_budget_used": self._calculate_monthly_budget_usage(),
            "cost_per_signal": self._calculate_cost_per_signal(),
            "data_usage_cost": self._calculate_data_usage_cost(),
            "api_call_costs": self._calculate_api_costs()
        }

        self.metrics["cost_metrics"] = cost_metrics
        return cost_metrics

    def collect_error_metrics(self) -> Dict[str, Any]:
        """Collect error and reliability metrics"""
        error_metrics = {
            "timestamp": get_eastern_time().isoformat(),
            "error_rate": self._calculate_error_rate(),
            "critical_errors": self._count_critical_errors(),
            "warnings": self._count_warnings(),
            "connection_failures": self._count_connection_failures(),
            "data_quality_issues": self._count_data_quality_issues(),
            "uptime_percentage": self._calculate_uptime()
        }

        self.metrics["error_metrics"] = error_metrics
        return error_metrics

    def collect_business_metrics(self) -> Dict[str, Any]:
        """Collect business performance metrics"""
        business_metrics = {
            "timestamp": get_eastern_time().isoformat(),
            "roi_today": self._calculate_roi_today(),
            "roi_this_month": self._calculate_roi_month(),
            "profit_loss": self._calculate_profit_loss(),
            "performance_vs_baseline": self._compare_to_baseline(),
            "market_conditions": self._assess_market_conditions()
        }

        self.metrics["business_metrics"] = business_metrics
        return business_metrics

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check all metrics against alert thresholds"""
        alerts = []
        thresholds = self.config["alert_thresholds"]

        # Check signal accuracy
        accuracy = self.metrics["trading_metrics"].get("signal_accuracy", 1.0)
        if accuracy < thresholds["signal_accuracy"]:
            alerts.append({
                "level": "WARNING",
                "metric": "signal_accuracy",
                "value": accuracy,
                "threshold": thresholds["signal_accuracy"],
                "message": f"Signal accuracy {accuracy:.2%} below threshold {thresholds['signal_accuracy']:.2%}"
            })

        # Check system latency
        latency = self.metrics["trading_metrics"].get("average_latency", 0)
        if latency > thresholds["system_latency"]:
            alerts.append({
                "level": "WARNING",
                "metric": "system_latency",
                "value": latency,
                "threshold": thresholds["system_latency"],
                "message": f"System latency {latency}ms above threshold {thresholds['system_latency']}ms"
            })

        # Check error rate
        error_rate = self.metrics["error_metrics"].get("error_rate", 0)
        if error_rate > thresholds["error_rate"]:
            alerts.append({
                "level": "CRITICAL",
                "metric": "error_rate",
                "value": error_rate,
                "threshold": thresholds["error_rate"],
                "message": f"Error rate {error_rate:.2%} above threshold {thresholds['error_rate']:.2%}"
            })

        # Check daily cost
        daily_cost = self.metrics["cost_metrics"].get("daily_cost", 0)
        if daily_cost > thresholds["daily_cost"]:
            alerts.append({
                "level": "WARNING",
                "metric": "daily_cost",
                "value": daily_cost,
                "threshold": thresholds["daily_cost"],
                "message": f"Daily cost ${daily_cost:.2f} above threshold ${thresholds['daily_cost']:.2f}"
            })

        # Check uptime
        uptime = self.metrics["error_metrics"].get("uptime_percentage", 1.0)
        if uptime < thresholds["uptime"]:
            alerts.append({
                "level": "CRITICAL",
                "metric": "uptime",
                "value": uptime,
                "threshold": thresholds["uptime"],
                "message": f"Uptime {uptime:.3%} below threshold {thresholds['uptime']:.3%}"
            })

        # Save alerts
        if alerts:
            self._save_alerts(alerts)

        return alerts

    def generate_dashboard(self) -> Dict[str, Any]:
        """Generate monitoring dashboard data"""
        dashboard = {
            "generated_at": get_eastern_time().isoformat(),
            "summary": {
                "status": self._get_overall_status(),
                "active_alerts": len(self.check_alerts()),
                "uptime": self.metrics["error_metrics"].get("uptime_percentage", 0),
                "daily_signals": self.metrics["trading_metrics"].get("signals_generated", 0),
                "daily_cost": self.metrics["cost_metrics"].get("daily_cost", 0)
            },
            "charts": {
                "signal_accuracy_trend": self._get_accuracy_trend(),
                "latency_trend": self._get_latency_trend(),
                "cost_trend": self._get_cost_trend(),
                "error_rate_trend": self._get_error_trend()
            },
            "metrics": self.metrics
        }

        # Save dashboard
        with open(self.dashboard_file, 'w') as f:
            json.dump(dashboard, f, indent=2)

        return dashboard

    def run_monitoring_cycle(self):
        """Run a complete monitoring cycle"""
        self.logger.info("Starting monitoring cycle")

        try:
            # Collect all metrics
            self.collect_system_health()
            self.collect_trading_metrics()
            self.collect_cost_metrics()
            self.collect_error_metrics()
            self.collect_business_metrics()

            # Check for alerts
            alerts = self.check_alerts()
            if alerts:
                self.logger.warning(f"Generated {len(alerts)} alerts")
                for alert in alerts:
                    self.logger.warning(f"{alert['level']}: {alert['message']}")

            # Generate dashboard
            dashboard = self.generate_dashboard()

            # Save metrics
            self._save_metrics()

            self.logger.info("Monitoring cycle completed successfully")

        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")

    def start_continuous_monitoring(self):
        """Start continuous monitoring loop"""
        self.logger.info("Starting continuous monitoring")
        interval = self.config["monitoring_interval"]

        try:
            while True:
                self.run_monitoring_cycle()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Fatal error in monitoring: {e}")

    # Helper methods for metric collection
    def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage (placeholder)"""
        # In production, use psutil or similar
        return 0.0

    def _get_memory_usage(self) -> float:
        """Get memory usage percentage (placeholder)"""
        return 0.0

    def _get_disk_usage(self) -> float:
        """Get disk usage percentage (placeholder)"""
        return 0.0

    def _check_network_connectivity(self) -> bool:
        """Check network connectivity (placeholder)"""
        return True

    def _check_service_status(self) -> Dict[str, bool]:
        """Check status of critical services (placeholder)"""
        return {
            "databento_connection": True,
            "trading_engine": True,
            "data_pipeline": True
        }

    def _count_signals_today(self) -> int:
        """Count signals generated today (placeholder)"""
        return 0

    def _calculate_signal_accuracy(self) -> float:
        """Calculate signal accuracy (placeholder)"""
        return 0.75

    def _calculate_average_latency(self) -> float:
        """Calculate average system latency in ms (placeholder)"""
        return 85.0

    def _calculate_win_loss_ratio(self) -> float:
        """Calculate win/loss ratio (placeholder)"""
        return 1.8

    def _count_successful_trades(self) -> int:
        """Count successful trades today (placeholder)"""
        return 0

    def _count_failed_trades(self) -> int:
        """Count failed trades today (placeholder)"""
        return 0

    def _calculate_daily_cost(self) -> float:
        """Calculate daily cost (placeholder)"""
        return 5.50

    def _calculate_monthly_budget_usage(self) -> float:
        """Calculate monthly budget usage percentage (placeholder)"""
        return 0.25

    def _calculate_cost_per_signal(self) -> float:
        """Calculate cost per signal (placeholder)"""
        return 2.75

    def _calculate_data_usage_cost(self) -> float:
        """Calculate data usage cost (placeholder)"""
        return 3.50

    def _calculate_api_costs(self) -> float:
        """Calculate API call costs (placeholder)"""
        return 2.00

    def _calculate_error_rate(self) -> float:
        """Calculate system error rate (placeholder)"""
        return 0.02

    def _count_critical_errors(self) -> int:
        """Count critical errors today (placeholder)"""
        return 0

    def _count_warnings(self) -> int:
        """Count warnings today (placeholder)"""
        return 2

    def _count_connection_failures(self) -> int:
        """Count connection failures today (placeholder)"""
        return 0

    def _count_data_quality_issues(self) -> int:
        """Count data quality issues (placeholder)"""
        return 1

    def _calculate_uptime(self) -> float:
        """Calculate system uptime percentage (placeholder)"""
        return 0.999

    def _calculate_roi_today(self) -> float:
        """Calculate ROI for today (placeholder)"""
        return 0.15

    def _calculate_roi_month(self) -> float:
        """Calculate ROI for this month (placeholder)"""
        return 0.28

    def _calculate_profit_loss(self) -> float:
        """Calculate profit/loss (placeholder)"""
        return 150.75

    def _compare_to_baseline(self) -> float:
        """Compare performance to baseline (placeholder)"""
        return 1.25  # 25% improvement

    def _assess_market_conditions(self) -> str:
        """Assess current market conditions (placeholder)"""
        return "normal"

    def _get_overall_status(self) -> str:
        """Get overall system status"""
        alerts = self.check_alerts()
        critical_alerts = [a for a in alerts if a.get("level") == "CRITICAL"]

        if critical_alerts:
            return "CRITICAL"
        elif alerts:
            return "WARNING"
        else:
            return "HEALTHY"

    def _get_accuracy_trend(self) -> List[Dict[str, Any]]:
        """Get signal accuracy trend data (placeholder)"""
        return []

    def _get_latency_trend(self) -> List[Dict[str, Any]]:
        """Get latency trend data (placeholder)"""
        return []

    def _get_cost_trend(self) -> List[Dict[str, Any]]:
        """Get cost trend data (placeholder)"""
        return []

    def _get_error_trend(self) -> List[Dict[str, Any]]:
        """Get error rate trend data (placeholder)"""
        return []

    def _save_metrics(self):
        """Save metrics to file"""
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def _save_alerts(self, alerts: List[Dict[str, Any]]):
        """Save alerts to file"""
        alert_data = {
            "timestamp": get_eastern_time().isoformat(),
            "alerts": alerts
        }
        with open(self.alerts_file, 'w') as f:
            json.dump(alert_data, f, indent=2)


def main():
    """Main monitoring entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Production Monitoring for IFD v3.0")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--once", action="store_true", help="Run once instead of continuous")
    parser.add_argument("--dashboard", action="store_true", help="Generate dashboard only")

    args = parser.parse_args()

    monitor = ProductionMonitor(args.config)

    if args.dashboard:
        dashboard = monitor.generate_dashboard()
        print(f"Dashboard generated: {monitor.dashboard_file}")
    elif args.once:
        monitor.run_monitoring_cycle()
    else:
        monitor.start_continuous_monitoring()


if __name__ == "__main__":
    main()
