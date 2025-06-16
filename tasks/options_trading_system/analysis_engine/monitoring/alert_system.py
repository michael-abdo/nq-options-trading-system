#!/usr/bin/env python3
"""
Multi-Channel Alert System for IFD v3.0 Trading System

Provides comprehensive alerting capabilities including:
- Email notifications for critical issues
- Slack webhook integration for team alerts
- SMS alerting for emergency situations
- Alert escalation chains and routing
- Rate limiting and deduplication
- Alert history and tracking
"""

import json
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import os
import hashlib
from collections import defaultdict, deque

# Optional email support
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

# Import timezone utilities
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
from utils.timezone_utils import get_eastern_time

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    severity: str  # INFO, WARNING, CRITICAL, EMERGENCY
    title: str
    message: str
    component: str
    timestamp: str
    source: str
    tags: List[str]
    metadata: Dict[str, Any]
    resolved: bool = False
    acknowledged: bool = False
    escalated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class AlertChannel:
    """Alert notification channel configuration"""
    name: str
    type: str  # email, slack, sms, webhook
    enabled: bool
    config: Dict[str, Any]
    severity_filter: List[str]  # Which severities to send
    rate_limit: Optional[int] = None  # Max alerts per hour

class AlertSystem:
    """Multi-channel alert system with rate limiting and escalation"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/alerting.json"
        self.alerts_file = "outputs/monitoring/alerts.json"
        self.alert_history_file = "outputs/monitoring/alert_history.json"

        # Ensure directories exist
        os.makedirs("outputs/monitoring", exist_ok=True)

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Load configuration
        self.config = self._load_config()

        # Alert tracking
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.rate_limiters: Dict[str, deque] = defaultdict(deque)
        self.deduplication_cache: Set[str] = set()

        # Alert channels
        self.channels: Dict[str, AlertChannel] = self._setup_channels()

        # Load existing alerts
        self._load_existing_alerts()

    def _load_config(self) -> Dict[str, Any]:
        """Load alerting configuration"""
        default_config = {
            "channels": {
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "from_email": "",
                    "to_emails": [],
                    "severity_filter": ["WARNING", "CRITICAL", "EMERGENCY"]
                },
                "slack": {
                    "enabled": False,
                    "webhook_url": "",
                    "channel": "#alerts",
                    "username": "IFD-Bot",
                    "severity_filter": ["CRITICAL", "EMERGENCY"]
                },
                "sms": {
                    "enabled": False,
                    "service": "twilio",  # twilio, aws_sns
                    "account_sid": "",
                    "auth_token": "",
                    "from_number": "",
                    "to_numbers": [],
                    "severity_filter": ["EMERGENCY"]
                }
            },
            "escalation": {
                "enabled": True,
                "escalation_time_minutes": 30,
                "escalation_chain": [
                    {"level": 1, "channels": ["slack"]},
                    {"level": 2, "channels": ["email"]},
                    {"level": 3, "channels": ["sms"]}
                ]
            },
            "rate_limiting": {
                "enabled": True,
                "max_alerts_per_hour": {
                    "INFO": 60,
                    "WARNING": 30,
                    "CRITICAL": 12,
                    "EMERGENCY": 6
                }
            },
            "deduplication": {
                "enabled": True,
                "time_window_minutes": 10
            }
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    return {**default_config, **config}
            except Exception as e:
                self.logger.warning(f"Error loading config: {e}. Using defaults.")

        return default_config

    def _setup_channels(self) -> Dict[str, AlertChannel]:
        """Setup alert notification channels"""
        channels = {}

        for name, config in self.config.get("channels", {}).items():
            if config.get("enabled", False):
                channels[name] = AlertChannel(
                    name=name,
                    type=name,
                    enabled=True,
                    config=config,
                    severity_filter=config.get("severity_filter", ["CRITICAL", "EMERGENCY"]),
                    rate_limit=self.config.get("rate_limiting", {}).get("max_alerts_per_hour", {}).get("CRITICAL", 12)
                )

        return channels

    def _load_existing_alerts(self):
        """Load existing alerts from storage"""
        if os.path.exists(self.alerts_file):
            try:
                with open(self.alerts_file, 'r') as f:
                    alerts_data = json.load(f)
                    for alert_data in alerts_data:
                        alert = Alert(**alert_data)
                        if not alert.resolved:
                            self.active_alerts[alert.id] = alert
            except Exception as e:
                self.logger.warning(f"Error loading existing alerts: {e}")

    def create_alert(self,
                    severity: str,
                    title: str,
                    message: str,
                    component: str,
                    source: str = "system",
                    tags: Optional[List[str]] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> Optional[Alert]:
        """Create and process a new alert"""

        # Generate alert ID
        alert_id = self._generate_alert_id(severity, title, component)

        # Check for deduplication
        if self._is_duplicate_alert(alert_id):
            self.logger.debug(f"Skipping duplicate alert: {alert_id}")
            return None

        # Create alert
        alert = Alert(
            id=alert_id,
            severity=severity,
            title=title,
            message=message,
            component=component,
            timestamp=get_eastern_time().isoformat(),
            source=source,
            tags=tags or [],
            metadata=metadata or {},
            resolved=False,
            acknowledged=False,
            escalated=False
        )

        # Check rate limiting
        if not self._check_rate_limit(severity):
            self.logger.warning(f"Rate limit exceeded for severity {severity}")
            return None

        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        # Send notifications
        self._send_alert_notifications(alert)

        # Save to storage
        self._save_alerts()

        self.logger.info(f"Alert created: {alert_id} - {title}")
        return alert

    def _generate_alert_id(self, severity: str, title: str, component: str) -> str:
        """Generate unique alert ID"""
        content = f"{severity}:{title}:{component}:{int(time.time() // 60)}"  # 1-minute precision
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _is_duplicate_alert(self, alert_id: str) -> bool:
        """Check if alert is duplicate within deduplication window"""
        if not self.config.get("deduplication", {}).get("enabled", True):
            return False

        window_minutes = self.config.get("deduplication", {}).get("time_window_minutes", 10)
        cutoff_time = get_eastern_time() - timedelta(minutes=window_minutes)

        # Clean old entries from deduplication cache
        current_alerts = set()
        for alert in self.alert_history[-100:]:  # Check last 100 alerts
            alert_time = datetime.fromisoformat(alert.timestamp.replace('Z', '+00:00'))
            if alert_time > cutoff_time:
                current_alerts.add(alert.id)

        self.deduplication_cache = current_alerts
        return alert_id in self.deduplication_cache

    def _check_rate_limit(self, severity: str) -> bool:
        """Check if alert exceeds rate limit"""
        if not self.config.get("rate_limiting", {}).get("enabled", True):
            return True

        max_per_hour = self.config.get("rate_limiting", {}).get("max_alerts_per_hour", {}).get(severity, 60)
        current_time = time.time()
        hour_ago = current_time - 3600

        # Clean old entries
        rate_limiter = self.rate_limiters[severity]
        while rate_limiter and rate_limiter[0] < hour_ago:
            rate_limiter.popleft()

        # Check limit
        if len(rate_limiter) >= max_per_hour:
            return False

        # Add current time
        rate_limiter.append(current_time)
        return True

    def _send_alert_notifications(self, alert: Alert):
        """Send alert through configured channels"""
        for channel_name, channel in self.channels.items():
            if alert.severity in channel.severity_filter:
                try:
                    if channel.type == "email":
                        self._send_email_alert(alert, channel)
                    elif channel.type == "slack":
                        self._send_slack_alert(alert, channel)
                    elif channel.type == "sms":
                        self._send_sms_alert(alert, channel)
                    elif channel.type == "webhook":
                        self._send_webhook_alert(alert, channel)
                except Exception as e:
                    self.logger.error(f"Failed to send alert via {channel_name}: {e}")

    def _send_email_alert(self, alert: Alert, channel: AlertChannel):
        """Send email alert"""
        if not EMAIL_AVAILABLE:
            self.logger.warning("Email support not available - skipping email alert")
            return

        if not channel.config.get("username") or not channel.config.get("to_emails"):
            return

        try:
            msg = MimeMultipart()
            msg['From'] = channel.config.get("from_email", channel.config.get("username"))
            msg['To'] = ", ".join(channel.config.get("to_emails", []))
            msg['Subject'] = f"[{alert.severity}] IFD Alert: {alert.title}"

            body = f"""
IFD v3.0 Trading System Alert

Severity: {alert.severity}
Component: {alert.component}
Time: {alert.timestamp}
Source: {alert.source}

Message:
{alert.message}

Tags: {', '.join(alert.tags)}

Alert ID: {alert.id}
            """

            msg.attach(MimeText(body, 'plain'))

            server = smtplib.SMTP(channel.config.get("smtp_server"), channel.config.get("smtp_port", 587))
            server.starttls()
            server.login(channel.config.get("username"), channel.config.get("password"))
            server.send_message(msg)
            server.quit()

            self.logger.info(f"Email alert sent: {alert.id}")

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")

    def _send_slack_alert(self, alert: Alert, channel: AlertChannel):
        """Send Slack webhook alert"""
        webhook_url = channel.config.get("webhook_url")
        if not webhook_url:
            return

        # Map severity to colors
        color_map = {
            "INFO": "#36a64f",      # Green
            "WARNING": "#ff9900",    # Orange
            "CRITICAL": "#ff0000",   # Red
            "EMERGENCY": "#8B0000"   # Dark Red
        }

        payload = {
            "channel": channel.config.get("channel", "#alerts"),
            "username": channel.config.get("username", "IFD-Bot"),
            "attachments": [{
                "color": color_map.get(alert.severity, "#cccccc"),
                "title": f"[{alert.severity}] {alert.title}",
                "text": alert.message,
                "fields": [
                    {"title": "Component", "value": alert.component, "short": True},
                    {"title": "Source", "value": alert.source, "short": True},
                    {"title": "Time", "value": alert.timestamp, "short": False},
                    {"title": "Alert ID", "value": alert.id, "short": True}
                ],
                "footer": "IFD v3.0 Trading System",
                "ts": int(time.time())
            }]
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            self.logger.info(f"Slack alert sent: {alert.id}")
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")

    def _send_sms_alert(self, alert: Alert, channel: AlertChannel):
        """Send SMS alert (Twilio implementation)"""
        if channel.config.get("service") == "twilio":
            try:
                # This would require twilio library: pip install twilio
                # from twilio.rest import Client

                # client = Client(
                #     channel.config.get("account_sid"),
                #     channel.config.get("auth_token")
                # )

                message_body = f"[{alert.severity}] IFD Alert: {alert.title}\n{alert.message[:100]}..."

                # for to_number in channel.config.get("to_numbers", []):
                #     client.messages.create(
                #         body=message_body,
                #         from_=channel.config.get("from_number"),
                #         to=to_number
                #     )

                self.logger.info(f"SMS alert would be sent: {alert.id} (Twilio not configured)")

            except Exception as e:
                self.logger.error(f"Failed to send SMS: {e}")

    def _send_webhook_alert(self, alert: Alert, channel: AlertChannel):
        """Send generic webhook alert"""
        webhook_url = channel.config.get("url")
        if not webhook_url:
            return

        payload = {
            "alert": alert.to_dict(),
            "timestamp": get_eastern_time().isoformat(),
            "system": "ifd_v3"
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            self.logger.info(f"Webhook alert sent: {alert.id}")
        except Exception as e:
            self.logger.error(f"Failed to send webhook: {e}")

    def acknowledge_alert(self, alert_id: str, acknowledger: str = "system") -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            self.active_alerts[alert_id].metadata["acknowledged_by"] = acknowledger
            self.active_alerts[alert_id].metadata["acknowledged_at"] = get_eastern_time().isoformat()
            self._save_alerts()
            self.logger.info(f"Alert acknowledged: {alert_id} by {acknowledger}")
            return True
        return False

    def resolve_alert(self, alert_id: str, resolver: str = "system") -> bool:
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            self.active_alerts[alert_id].metadata["resolved_by"] = resolver
            self.active_alerts[alert_id].metadata["resolved_at"] = get_eastern_time().isoformat()

            # Remove from active alerts
            resolved_alert = self.active_alerts.pop(alert_id)

            self._save_alerts()
            self.logger.info(f"Alert resolved: {alert_id} by {resolver}")
            return True
        return False

    def get_active_alerts(self, severity_filter: Optional[List[str]] = None) -> List[Alert]:
        """Get currently active alerts"""
        alerts = list(self.active_alerts.values())

        if severity_filter:
            alerts = [alert for alert in alerts if alert.severity in severity_filter]

        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)

    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert system statistics"""
        now = get_eastern_time()
        last_24h = now - timedelta(hours=24)

        recent_alerts = [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert.timestamp.replace('Z', '+00:00')) > last_24h
        ]

        stats = {
            "active_alerts": len(self.active_alerts),
            "total_alerts_24h": len(recent_alerts),
            "alerts_by_severity_24h": {},
            "alerts_by_component_24h": {},
            "average_resolution_time_minutes": self._calculate_avg_resolution_time(),
            "channels_configured": len(self.channels),
            "channels_enabled": [name for name, channel in self.channels.items() if channel.enabled]
        }

        # Count by severity
        for alert in recent_alerts:
            stats["alerts_by_severity_24h"][alert.severity] = \
                stats["alerts_by_severity_24h"].get(alert.severity, 0) + 1

        # Count by component
        for alert in recent_alerts:
            stats["alerts_by_component_24h"][alert.component] = \
                stats["alerts_by_component_24h"].get(alert.component, 0) + 1

        return stats

    def _calculate_avg_resolution_time(self) -> float:
        """Calculate average alert resolution time in minutes"""
        resolved_alerts = [
            alert for alert in self.alert_history[-100:]
            if alert.resolved and "resolved_at" in alert.metadata
        ]

        if not resolved_alerts:
            return 0.0

        total_time = 0
        for alert in resolved_alerts:
            created_time = datetime.fromisoformat(alert.timestamp.replace('Z', '+00:00'))
            resolved_time = datetime.fromisoformat(alert.metadata["resolved_at"].replace('Z', '+00:00'))
            total_time += (resolved_time - created_time).total_seconds()

        return total_time / len(resolved_alerts) / 60  # Convert to minutes

    def _save_alerts(self):
        """Save alerts to storage"""
        try:
            # Save active alerts
            active_alerts_data = [alert.to_dict() for alert in self.active_alerts.values()]
            with open(self.alerts_file, 'w') as f:
                json.dump(active_alerts_data, f, indent=2)

            # Save alert history (last 1000 alerts)
            history_data = [alert.to_dict() for alert in self.alert_history[-1000:]]
            with open(self.alert_history_file, 'w') as f:
                json.dump(history_data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save alerts: {e}")

# Convenience functions for common alert types
def create_trading_alert(alert_system: AlertSystem,
                        signal_accuracy: float,
                        expected_accuracy: float = 0.75):
    """Create trading performance alert"""
    if signal_accuracy < expected_accuracy * 0.8:  # Below 80% of target
        severity = "CRITICAL" if signal_accuracy < expected_accuracy * 0.6 else "WARNING"
        alert_system.create_alert(
            severity=severity,
            title="Trading Signal Accuracy Below Target",
            message=f"Signal accuracy is {signal_accuracy:.1%}, below target of {expected_accuracy:.1%}",
            component="trading_engine",
            source="performance_monitor",
            tags=["trading", "performance", "accuracy"],
            metadata={"current_accuracy": signal_accuracy, "target_accuracy": expected_accuracy}
        )

def create_system_alert(alert_system: AlertSystem,
                       component: str,
                       error_message: str,
                       severity: str = "WARNING"):
    """Create system error alert"""
    alert_system.create_alert(
        severity=severity,
        title=f"System Error in {component}",
        message=error_message,
        component=component,
        source="system_monitor",
        tags=["system", "error"],
        metadata={"error_details": error_message}
    )

def create_cost_alert(alert_system: AlertSystem,
                     current_cost: float,
                     budget_limit: float,
                     period: str = "daily"):
    """Create cost overrun alert"""
    usage_percent = (current_cost / budget_limit) * 100

    if usage_percent > 90:
        severity = "CRITICAL"
    elif usage_percent > 80:
        severity = "WARNING"
    else:
        return  # No alert needed

    alert_system.create_alert(
        severity=severity,
        title=f"Budget Alert: {period.title()} Cost Approaching Limit",
        message=f"Current {period} cost is ${current_cost:.2f} ({usage_percent:.1f}% of ${budget_limit:.2f} limit)",
        component="cost_monitor",
        source="budget_tracker",
        tags=["cost", "budget", period],
        metadata={
            "current_cost": current_cost,
            "budget_limit": budget_limit,
            "usage_percent": usage_percent,
            "period": period
        }
    )

# Example usage and testing
if __name__ == "__main__":
    # Create alert system
    alert_system = AlertSystem()

    # Test different alert types
    print("Testing Alert System...")

    # Test trading alert
    create_trading_alert(alert_system, 0.65, 0.75)

    # Test system alert
    create_system_alert(alert_system, "websocket_server", "Connection timeout after 30 seconds", "CRITICAL")

    # Test cost alert
    create_cost_alert(alert_system, 8.5, 10.0, "daily")

    # Test direct alert creation
    alert_system.create_alert(
        severity="WARNING",
        title="High Memory Usage",
        message="System memory usage is at 85%",
        component="system_monitor",
        source="health_check",
        tags=["memory", "performance"],
        metadata={"memory_usage": 0.85}
    )

    # Print statistics
    stats = alert_system.get_alert_stats()
    print(f"\nAlert Statistics:")
    print(f"Active alerts: {stats['active_alerts']}")
    print(f"Alerts in last 24h: {stats['total_alerts_24h']}")
    print(f"Channels configured: {stats['channels_configured']}")
    print(f"Enabled channels: {', '.join(stats['channels_enabled'])}")

    # Print active alerts
    active_alerts = alert_system.get_active_alerts()
    print(f"\nActive Alerts ({len(active_alerts)}):")
    for alert in active_alerts:
        print(f"  [{alert.severity}] {alert.title} - {alert.component}")
