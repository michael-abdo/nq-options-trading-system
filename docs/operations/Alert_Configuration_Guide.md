# Alert Configuration & Customization Guide

## Overview
The IFD v3.0 Trading System provides a comprehensive multi-channel alert system for real-time monitoring of trading signals, system health, and performance metrics. This guide covers alert configuration, customization options, and best practices for different use cases.

## Table of Contents
- [Alert System Architecture](#alert-system-architecture)
- [Alert Channels](#alert-channels)
- [Alert Types & Categories](#alert-types--categories)
- [Configuration Files](#configuration-files)
- [Channel-Specific Setup](#channel-specific-setup)
- [Alert Rules & Conditions](#alert-rules--conditions)
- [Escalation Policies](#escalation-policies)
- [Customization Options](#customization-options)
- [Testing & Validation](#testing--validation)
- [Performance Considerations](#performance-considerations)
- [Troubleshooting Alerts](#troubleshooting-alerts)

## Alert System Architecture

### Core Components
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Signal        │───▶│   Alert Engine   │───▶│   Channel       │
│   Generator     │    │   & Rule Engine  │    │   Dispatcher    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Monitoring    │    │   Alert          │    │   Email/Slack/  │
│   System        │    │   Manager        │    │   SMS/Webhook   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Data Flow
1. **Event Detection**: System components generate events (signals, errors, performance metrics)
2. **Rule Evaluation**: Alert engine evaluates events against configured rules
3. **Alert Generation**: Matching events trigger alert creation
4. **Channel Routing**: Alerts are routed to appropriate notification channels
5. **Delivery Tracking**: System tracks delivery status and handles failures
6. **Escalation Processing**: Unacknowledged critical alerts trigger escalation

## Alert Channels

### Supported Channels

#### 1. Email Alerts
**Best For**: Detailed reports, non-urgent notifications, documentation
- **Delivery Time**: 1-5 minutes
- **Format**: HTML with charts and detailed information
- **Reliability**: High (99.9% delivery rate)
- **Cost**: Low

#### 2. Slack Integration
**Best For**: Team notifications, real-time collaboration
- **Delivery Time**: < 30 seconds
- **Format**: Rich messages with buttons and quick actions
- **Reliability**: High (99.5% delivery rate)
- **Cost**: Free with Slack workspace

#### 3. SMS Notifications
**Best For**: Critical alerts, immediate attention required
- **Delivery Time**: < 10 seconds
- **Format**: Plain text, concise messages
- **Reliability**: Very High (99.95% delivery rate)
- **Cost**: $0.02-0.05 per message

#### 4. Webhook Integration
**Best For**: Custom integrations, external systems
- **Delivery Time**: < 5 seconds
- **Format**: JSON payload with full alert data
- **Reliability**: Depends on target system
- **Cost**: None from our system

#### 5. WebSocket Real-time
**Best For**: Dashboard updates, live monitoring
- **Delivery Time**: < 1 second
- **Format**: JSON with real-time updates
- **Reliability**: High (requires active connection)
- **Cost**: None

#### 6. Discord Integration
**Best For**: Trading communities, informal notifications
- **Delivery Time**: < 30 seconds
- **Format**: Rich embeds with custom formatting
- **Reliability**: High (99% delivery rate)
- **Cost**: Free

## Alert Types & Categories

### 1. Trading Signal Alerts

#### Signal Quality Alerts
```json
{
    "category": "trading_signal",
    "type": "high_confidence_signal",
    "conditions": [
        "signal.confidence >= 0.85",
        "signal.strength == 'strong'",
        "signal.risk_score <= 0.3"
    ],
    "channels": ["slack", "email", "websocket"],
    "priority": "high"
}
```

#### Signal Performance Alerts
```json
{
    "category": "trading_signal",
    "type": "signal_accuracy_drop",
    "conditions": [
        "accuracy_rate_24h < 0.65",
        "total_signals_24h >= 10"
    ],
    "channels": ["email", "slack"],
    "priority": "medium"
}
```

### 2. System Health Alerts

#### Resource Monitoring
```json
{
    "category": "system_health",
    "type": "high_resource_usage",
    "conditions": [
        "cpu_usage > 85",
        "memory_usage > 90",
        "disk_usage > 95"
    ],
    "channels": ["slack", "sms"],
    "priority": "critical"
}
```

#### Service Status
```json
{
    "category": "system_health",
    "type": "service_failure",
    "conditions": [
        "service_status != 'running'",
        "service_downtime > 300"
    ],
    "channels": ["email", "slack", "sms"],
    "priority": "critical",
    "escalation": true
}
```

### 3. Data Quality Alerts

#### Feed Quality
```json
{
    "category": "data_quality",
    "type": "data_feed_degradation",
    "conditions": [
        "data_completeness < 0.95",
        "error_rate > 0.05",
        "latency_p99 > 200"
    ],
    "channels": ["slack", "email"],
    "priority": "high"
}
```

### 4. Performance Alerts

#### Latency Monitoring
```json
{
    "category": "performance",
    "type": "high_latency",
    "conditions": [
        "signal_generation_latency > 100",
        "api_response_time > 500"
    ],
    "channels": ["slack"],
    "priority": "medium"
}
```

### 5. Security Alerts

#### Authentication Issues
```json
{
    "category": "security",
    "type": "authentication_failure",
    "conditions": [
        "failed_auth_attempts > 5",
        "unauthorized_access_detected == true"
    ],
    "channels": ["email", "sms"],
    "priority": "critical",
    "escalation": true
}
```

## Configuration Files

### Main Alert Configuration

**File**: `config/alerting.json`

```json
{
    "alert_system": {
        "enabled": true,
        "default_timezone": "America/New_York",
        "rate_limiting": {
            "enabled": true,
            "max_alerts_per_hour": 100,
            "burst_limit": 20
        },
        "retry_policy": {
            "max_retries": 3,
            "retry_delay_seconds": [30, 120, 300],
            "backoff_multiplier": 2
        }
    },
    "channels": {
        "email": {
            "enabled": true,
            "smtp_server": "smtp.company.com",
            "smtp_port": 587,
            "username": "${EMAIL_USERNAME}",
            "password": "${EMAIL_PASSWORD}",
            "from_address": "alerts@tradingsystem.com",
            "recipients": {
                "default": ["admin@company.com"],
                "critical": ["admin@company.com", "cto@company.com"],
                "trading": ["trader1@company.com", "trader2@company.com"]
            },
            "templates": {
                "signal_alert": "templates/signal_alert.html",
                "system_alert": "templates/system_alert.html"
            }
        },
        "slack": {
            "enabled": true,
            "webhook_url": "${SLACK_WEBHOOK_URL}",
            "channels": {
                "general": "#trading-alerts",
                "critical": "#critical-alerts",
                "signals": "#trading-signals"
            },
            "mention_users": {
                "critical": ["@channel"],
                "high": ["@here"],
                "medium": []
            }
        },
        "sms": {
            "enabled": true,
            "provider": "twilio",
            "account_sid": "${TWILIO_ACCOUNT_SID}",
            "auth_token": "${TWILIO_AUTH_TOKEN}",
            "from_number": "+1234567890",
            "recipients": {
                "critical": ["+1987654321", "+1555123456"],
                "emergency": ["+1911911911"]
            }
        },
        "webhook": {
            "enabled": true,
            "endpoints": [
                {
                    "name": "external_monitoring",
                    "url": "https://monitoring.company.com/webhooks/trading",
                    "headers": {
                        "Authorization": "Bearer ${MONITORING_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    "retry_policy": {
                        "max_retries": 5,
                        "timeout_seconds": 30
                    }
                }
            ]
        },
        "websocket": {
            "enabled": true,
            "port": 8766,
            "path": "/alerts",
            "max_clients": 50
        },
        "discord": {
            "enabled": false,
            "webhook_url": "${DISCORD_WEBHOOK_URL}",
            "username": "Trading Bot",
            "avatar_url": "https://example.com/bot-avatar.png"
        }
    },
    "alert_rules": {
        "trading_signals": {
            "high_confidence_signal": {
                "enabled": true,
                "conditions": [
                    "confidence >= 0.85",
                    "strength == 'strong'",
                    "risk_score <= 0.3"
                ],
                "channels": ["slack", "websocket"],
                "priority": "high",
                "rate_limit": "1_per_minute",
                "template": "high_confidence_signal"
            },
            "signal_cluster": {
                "enabled": true,
                "conditions": [
                    "signals_in_30min >= 3",
                    "same_direction == true",
                    "avg_confidence >= 0.75"
                ],
                "channels": ["slack", "email"],
                "priority": "high",
                "template": "signal_cluster"
            }
        },
        "system_health": {
            "critical_system_failure": {
                "enabled": true,
                "conditions": [
                    "cpu_usage > 95 OR memory_usage > 98 OR disk_usage > 98",
                    "service_status == 'failed'"
                ],
                "channels": ["email", "slack", "sms"],
                "priority": "critical",
                "escalation": true,
                "template": "critical_failure"
            },
            "performance_degradation": {
                "enabled": true,
                "conditions": [
                    "latency_p99 > 200",
                    "error_rate > 0.05"
                ],
                "channels": ["slack"],
                "priority": "medium",
                "rate_limit": "1_per_15min",
                "template": "performance_issue"
            }
        },
        "data_quality": {
            "feed_interruption": {
                "enabled": true,
                "conditions": [
                    "data_feed_status == 'disconnected'",
                    "duration > 300"
                ],
                "channels": ["slack", "email"],
                "priority": "high",
                "escalation": false,
                "template": "feed_interruption"
            }
        }
    },
    "escalation_policies": {
        "default": {
            "levels": [
                {
                    "timeout_minutes": 5,
                    "channels": ["slack"]
                },
                {
                    "timeout_minutes": 15,
                    "channels": ["email", "slack"]
                },
                {
                    "timeout_minutes": 30,
                    "channels": ["email", "slack", "sms"]
                }
            ]
        },
        "critical": {
            "levels": [
                {
                    "timeout_minutes": 2,
                    "channels": ["slack", "sms"]
                },
                {
                    "timeout_minutes": 10,
                    "channels": ["email", "slack", "sms"]
                },
                {
                    "timeout_minutes": 30,
                    "channels": ["email", "slack", "sms"],
                    "escalate_to": "emergency_contact"
                }
            ]
        }
    },
    "templates": {
        "high_confidence_signal": {
            "subject": "🚀 High Confidence Signal: ${signal.symbol} ${signal.direction}",
            "slack_format": "blocks",
            "include_charts": true,
            "include_metrics": true
        },
        "critical_failure": {
            "subject": "🚨 CRITICAL: System Failure Detected",
            "slack_format": "blocks",
            "sms_format": "brief",
            "include_system_info": true
        }
    }
}
```

## Channel-Specific Setup

### Email Configuration

#### SMTP Setup
```bash
# Environment variables for email
export EMAIL_USERNAME="alerts@company.com"
export EMAIL_PASSWORD="secure_app_password"
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
```

#### Email Templates
Create HTML templates in `templates/` directory:

**File**: `templates/signal_alert.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>Trading Signal Alert</title>
    <style>
        .signal-box {
            border: 2px solid #4CAF50;
            padding: 20px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .bullish { border-color: #4CAF50; background: #E8F5E8; }
        .bearish { border-color: #F44336; background: #FFEBEE; }
        .metrics { background: #F5F5F5; padding: 10px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="signal-box ${signal.direction}">
        <h2>🎯 ${signal.symbol} Signal - ${signal.direction.upper()}</h2>

        <div class="metrics">
            <strong>Confidence:</strong> ${signal.confidence * 100:.1f}%<br>
            <strong>Strength:</strong> ${signal.strength}<br>
            <strong>Expected Value:</strong> ${signal.expected_value} points<br>
            <strong>Risk Score:</strong> ${signal.risk_score:.2f}<br>
            <strong>Time:</strong> ${signal.timestamp}
        </div>

        <h3>Pressure Metrics</h3>
        <ul>
            <li>Imbalance Ratio: ${signal.pressure_metrics.imbalance_ratio:.2f}</li>
            <li>Volume Concentration: ${signal.pressure_metrics.volume_concentration:.2f}</li>
            <li>Order Flow Delta: ${signal.pressure_metrics.order_flow_delta}</li>
        </ul>

        <h3>Market Context</h3>
        <ul>
            <li>Price: ${signal.market_context.price}</li>
            <li>Volume: ${signal.market_context.volume:,}</li>
            <li>Session: ${signal.market_context.session}</li>
        </ul>

        <p><em>Generated by IFD v3.0 Trading System</em></p>
    </div>
</body>
</html>
```

### Slack Configuration

#### Webhook Setup
```bash
# Get webhook URL from Slack App settings
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
```

#### Custom Slack Blocks
```python
# Custom Slack message formatting
def create_signal_slack_message(signal):
    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🎯 {signal['symbol']} Signal - {signal['direction'].upper()}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Confidence:* {signal['confidence']*100:.1f}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Strength:* {signal['strength']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Expected Value:* {signal['expected_value']} pts"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Risk Score:* {signal['risk_score']:.2f}"
                    }
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Dashboard"
                        },
                        "url": "http://localhost:8765",
                        "action_id": "view_dashboard"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Acknowledge"
                        },
                        "action_id": "acknowledge_signal"
                    }
                ]
            }
        ]
    }
```

### SMS Configuration

#### Twilio Setup
```bash
# Twilio credentials
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token_here"
export TWILIO_FROM_NUMBER="+1234567890"
```

#### SMS Message Templates
```python
def format_sms_message(alert):
    """Format alert for SMS delivery (160 char limit)"""
    if alert['category'] == 'trading_signal':
        return f"🎯{alert['symbol']} {alert['direction']} {alert['confidence']*100:.0f}% conf, {alert['expected_value']:.0f}pts EV"
    elif alert['category'] == 'system_health':
        return f"🚨System Alert: {alert['message'][:100]}"
    else:
        return f"Alert: {alert['message'][:140]}"
```

### Webhook Configuration

#### Custom Webhook Handler
```python
# scripts/webhook_handler.py
import requests
import json
from typing import Dict, Any

class WebhookHandler:
    def __init__(self, config):
        self.endpoints = config['webhook']['endpoints']
        self.default_timeout = 30
        self.max_retries = 3

    def send_alert(self, alert: Dict[str, Any], endpoint_name: str = None):
        """Send alert to configured webhooks"""

        endpoints = [ep for ep in self.endpoints if ep['name'] == endpoint_name] if endpoint_name else self.endpoints

        for endpoint in endpoints:
            try:
                payload = self.format_payload(alert, endpoint)
                response = requests.post(
                    endpoint['url'],
                    json=payload,
                    headers=endpoint.get('headers', {}),
                    timeout=endpoint.get('timeout', self.default_timeout)
                )

                if response.status_code == 200:
                    print(f"Webhook sent successfully to {endpoint['name']}")
                else:
                    print(f"Webhook failed: {response.status_code} - {response.text}")

            except Exception as e:
                print(f"Webhook error for {endpoint['name']}: {e}")

    def format_payload(self, alert: Dict[str, Any], endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """Format alert payload for webhook"""
        return {
            "timestamp": alert['timestamp'],
            "alert_id": alert['alert_id'],
            "category": alert['category'],
            "type": alert['type'],
            "priority": alert['priority'],
            "message": alert['message'],
            "data": alert.get('data', {}),
            "source": "ifd_trading_system"
        }
```

## Alert Rules & Conditions

### Condition Syntax

#### Basic Operators
```
Comparison: >, <, >=, <=, ==, !=
Logical: AND, OR, NOT
Membership: IN, NOT IN
Pattern: LIKE, REGEX
```

#### Signal-Based Conditions
```python
# Signal quality conditions
"confidence >= 0.85"
"strength IN ['strong', 'moderate']"
"risk_score <= 0.4"
"expected_value > 50"

# Time-based conditions
"time_of_day BETWEEN '09:30' AND '16:00'"
"day_of_week NOT IN ['Saturday', 'Sunday']"
"signals_in_last_hour >= 3"

# Market context conditions
"market_context.session == 'regular'"
"market_context.volatility > 0.02"
"market_context.volume > average_volume * 1.5"
```

#### System Health Conditions
```python
# Resource conditions
"cpu_usage > 85"
"memory_usage > 90"
"disk_usage > 95"
"network_latency > 100"

# Service conditions
"service_status == 'failed'"
"uptime_seconds < 3600"
"error_rate > 0.05"
"response_time_p99 > 200"
```

### Complex Rule Examples

#### Multi-Condition Signal Alert
```json
{
    "name": "premium_signal_cluster",
    "enabled": true,
    "conditions": [
        "confidence >= 0.80",
        "strength == 'strong'",
        "signals_same_direction_30min >= 2",
        "market_context.session == 'regular'",
        "risk_score <= 0.35"
    ],
    "channels": ["slack", "email"],
    "priority": "high",
    "rate_limit": "1_per_30min",
    "custom_actions": [
        "increase_position_sizing_recommendation",
        "notify_portfolio_manager"
    ]
}
```

#### Cascading System Alert
```json
{
    "name": "system_degradation_cascade",
    "enabled": true,
    "conditions": [
        "cpu_usage > 80 AND memory_usage > 75",
        "error_rate > 0.02",
        "latency_increase_rate > 1.5"
    ],
    "channels": ["slack"],
    "priority": "medium",
    "escalation_conditions": [
        "cpu_usage > 90 OR memory_usage > 90",
        "error_rate > 0.05"
    ],
    "escalation_channels": ["email", "sms"],
    "escalation_priority": "critical"
}
```

## Escalation Policies

### Escalation Configuration

#### Time-Based Escalation
```json
{
    "escalation_policy": "time_based",
    "levels": [
        {
            "level": 1,
            "timeout_minutes": 5,
            "channels": ["slack"],
            "recipients": ["trading_team"]
        },
        {
            "level": 2,
            "timeout_minutes": 15,
            "channels": ["email", "slack"],
            "recipients": ["trading_team", "system_admin"]
        },
        {
            "level": 3,
            "timeout_minutes": 30,
            "channels": ["email", "slack", "sms"],
            "recipients": ["trading_team", "system_admin", "manager"]
        }
    ],
    "max_escalations": 3,
    "acknowledgment_required": true
}
```

#### Severity-Based Escalation
```json
{
    "escalation_policy": "severity_based",
    "rules": {
        "low": {
            "channels": ["slack"],
            "escalation": false
        },
        "medium": {
            "channels": ["slack", "email"],
            "escalation": true,
            "timeout_minutes": 30
        },
        "high": {
            "channels": ["slack", "email"],
            "escalation": true,
            "timeout_minutes": 15
        },
        "critical": {
            "channels": ["slack", "email", "sms"],
            "escalation": true,
            "timeout_minutes": 5,
            "immediate_escalation": true
        }
    }
}
```

### Escalation Implementation

```python
# scripts/escalation_manager.py
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List

class EscalationManager:
    def __init__(self, config):
        self.config = config
        self.active_escalations = {}
        self.acknowledged_alerts = set()

    def create_escalation(self, alert_id: str, alert_data: Dict):
        """Create new escalation for alert"""

        if alert_id in self.acknowledged_alerts:
            return

        escalation_policy = self.get_escalation_policy(alert_data)

        self.active_escalations[alert_id] = {
            "alert_data": alert_data,
            "policy": escalation_policy,
            "current_level": 0,
            "created_at": datetime.now(),
            "last_escalated": None
        }

        # Start escalation timer
        threading.Thread(
            target=self._escalation_timer,
            args=(alert_id,),
            daemon=True
        ).start()

    def acknowledge_alert(self, alert_id: str, user: str):
        """Acknowledge alert and stop escalation"""

        self.acknowledged_alerts.add(alert_id)

        if alert_id in self.active_escalations:
            escalation = self.active_escalations[alert_id]
            escalation['acknowledged_at'] = datetime.now()
            escalation['acknowledged_by'] = user

            # Log acknowledgment
            print(f"Alert {alert_id} acknowledged by {user}")

            # Remove from active escalations
            del self.active_escalations[alert_id]

    def _escalation_timer(self, alert_id: str):
        """Handle escalation timing"""

        while alert_id in self.active_escalations and alert_id not in self.acknowledged_alerts:
            escalation = self.active_escalations[alert_id]
            policy = escalation['policy']
            current_level = escalation['current_level']

            if current_level >= len(policy['levels']):
                break

            level_config = policy['levels'][current_level]
            timeout_seconds = level_config['timeout_minutes'] * 60

            # Wait for timeout
            time.sleep(timeout_seconds)

            # Check if still active and not acknowledged
            if alert_id in self.active_escalations and alert_id not in self.acknowledged_alerts:
                self._escalate_alert(alert_id, current_level + 1)
                escalation['current_level'] += 1
                escalation['last_escalated'] = datetime.now()

    def _escalate_alert(self, alert_id: str, level: int):
        """Escalate alert to next level"""

        escalation = self.active_escalations[alert_id]
        policy = escalation['policy']

        if level > len(policy['levels']):
            return

        level_config = policy['levels'][level - 1]
        alert_data = escalation['alert_data']

        # Send escalated alert
        escalated_alert = {
            **alert_data,
            "escalation_level": level,
            "escalated_at": datetime.now().isoformat(),
            "message": f"ESCALATED (Level {level}): {alert_data['message']}"
        }

        # Send to escalation channels
        for channel in level_config['channels']:
            self.send_to_channel(escalated_alert, channel, level_config['recipients'])

    def get_escalation_policy(self, alert_data: Dict) -> Dict:
        """Get appropriate escalation policy for alert"""

        priority = alert_data.get('priority', 'medium')
        alert_type = alert_data.get('type', 'general')

        # Use specific policy if exists, otherwise default
        policy_name = f"{alert_type}_escalation"
        if policy_name in self.config['escalation_policies']:
            return self.config['escalation_policies'][policy_name]
        else:
            return self.config['escalation_policies']['default']
```

## Customization Options

### Alert Templates

#### Dynamic Template Variables
```python
# Available template variables
template_vars = {
    # Signal data
    "signal.symbol": "NQM5",
    "signal.confidence": 0.85,
    "signal.direction": "bullish",
    "signal.expected_value": 95.25,

    # System data
    "system.cpu_usage": 75.2,
    "system.memory_usage": 68.5,
    "system.uptime": "2d 14h 32m",

    # Time data
    "time.now": "2025-06-16 14:30:22",
    "time.market_open": "09:30:00",
    "time.market_close": "16:00:00",

    # Custom functions
    "format_currency(value)": "$1,234.56",
    "format_percentage(value)": "85.3%",
    "time_ago(timestamp)": "5 minutes ago"
}
```

#### Custom Template Engine
```python
# scripts/template_engine.py
import re
from datetime import datetime
from typing import Dict, Any

class AlertTemplateEngine:
    def __init__(self):
        self.custom_functions = {
            'format_currency': self._format_currency,
            'format_percentage': self._format_percentage,
            'time_ago': self._time_ago,
            'upper': str.upper,
            'lower': str.lower,
            'round': round
        }

    def render_template(self, template: str, data: Dict[str, Any]) -> str:
        """Render template with data"""

        # Replace simple variables
        pattern = r'\$\{([^}]+)\}'

        def replace_var(match):
            var_expr = match.group(1).strip()
            return str(self._evaluate_expression(var_expr, data))

        return re.sub(pattern, replace_var, template)

    def _evaluate_expression(self, expr: str, data: Dict[str, Any]):
        """Evaluate template expression"""

        # Handle function calls
        func_pattern = r'(\w+)\(([^)]*)\)'
        func_match = re.match(func_pattern, expr)

        if func_match:
            func_name = func_match.group(1)
            args_str = func_match.group(2)

            if func_name in self.custom_functions:
                # Parse arguments
                args = [self._get_value(arg.strip(), data) for arg in args_str.split(',') if arg.strip()]
                return self.custom_functions[func_name](*args)

        # Handle simple variable access
        return self._get_value(expr, data)

    def _get_value(self, path: str, data: Dict[str, Any]):
        """Get value from nested dictionary using dot notation"""

        keys = path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return f"${{{path}}}"  # Return original if not found

        return value

    def _format_currency(self, value):
        """Format value as currency"""
        try:
            return f"${float(value):,.2f}"
        except:
            return str(value)

    def _format_percentage(self, value):
        """Format value as percentage"""
        try:
            return f"{float(value)*100:.1f}%"
        except:
            return str(value)

    def _time_ago(self, timestamp):
        """Format timestamp as time ago"""
        try:
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            diff = datetime.now() - timestamp

            if diff.days > 0:
                return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                return "just now"
        except:
            return str(timestamp)
```

### Channel-Specific Customizations

#### Slack Customization
```python
def create_custom_slack_message(alert_data):
    """Create custom Slack message based on alert type"""

    if alert_data['category'] == 'trading_signal':
        return create_signal_slack_blocks(alert_data)
    elif alert_data['category'] == 'system_health':
        return create_system_health_blocks(alert_data)
    else:
        return create_generic_alert_blocks(alert_data)

def create_signal_slack_blocks(signal):
    direction_emoji = "🟢" if signal['direction'] == 'bullish' else "🔴"
    confidence_bar = "█" * int(signal['confidence'] * 10) + "░" * (10 - int(signal['confidence'] * 10))

    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{direction_emoji} {signal['symbol']} Signal"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Direction:* {signal['direction'].title()}\n*Confidence:* {confidence_bar} {signal['confidence']*100:.1f}%"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Details"
                    },
                    "url": f"http://localhost:8765/signal/{signal['signal_id']}"
                }
            }
        ]
    }
```

#### Email Customization
```html
<!-- Custom email template with conditional formatting -->
<div class="alert-container ${alert.priority}">
    {% if alert.category == 'trading_signal' %}
        <div class="signal-header ${alert.data.direction}">
            <h2>{{ alert.data.direction.upper() }} Signal: {{ alert.data.symbol }}</h2>
            <div class="confidence-meter">
                <div class="confidence-bar" style="width: {{ alert.data.confidence * 100 }}%"></div>
                <span>{{ (alert.data.confidence * 100)|round(1) }}% Confidence</span>
            </div>
        </div>

        <div class="signal-metrics">
            <div class="metric">
                <label>Expected Value:</label>
                <span class="value">{{ alert.data.expected_value }} points</span>
            </div>
            <div class="metric">
                <label>Risk Score:</label>
                <span class="value risk-{{ 'high' if alert.data.risk_score > 0.6 else 'medium' if alert.data.risk_score > 0.3 else 'low' }}">
                    {{ (alert.data.risk_score * 100)|round(1) }}%
                </span>
            </div>
        </div>
    {% endif %}

    {% if alert.priority == 'critical' %}
        <div class="critical-banner">
            ⚠️ IMMEDIATE ATTENTION REQUIRED ⚠️
        </div>
    {% endif %}
</div>
```

## Testing & Validation

### Alert Testing Framework

```python
# scripts/test_alerts.py
import asyncio
import json
from typing import Dict, List

class AlertTester:
    def __init__(self, config_file="config/alerting.json"):
        with open(config_file) as f:
            self.config = json.load(f)

    async def test_all_channels(self):
        """Test all configured alert channels"""

        test_alert = {
            "alert_id": "test_001",
            "timestamp": "2025-06-16T14:30:00Z",
            "category": "test",
            "type": "channel_test",
            "priority": "medium",
            "message": "This is a test alert to verify channel configuration"
        }

        results = {}

        for channel_name, channel_config in self.config['channels'].items():
            if channel_config.get('enabled', False):
                try:
                    result = await self._test_channel(channel_name, test_alert)
                    results[channel_name] = {"status": "success", "details": result}
                except Exception as e:
                    results[channel_name] = {"status": "error", "error": str(e)}

        return results

    async def _test_channel(self, channel_name: str, alert: Dict):
        """Test specific channel"""

        if channel_name == "email":
            return await self._test_email(alert)
        elif channel_name == "slack":
            return await self._test_slack(alert)
        elif channel_name == "sms":
            return await self._test_sms(alert)
        elif channel_name == "webhook":
            return await self._test_webhook(alert)
        else:
            raise Exception(f"Unknown channel: {channel_name}")

    async def _test_email(self, alert: Dict):
        """Test email delivery"""
        import smtplib
        from email.mime.text import MIMEText

        config = self.config['channels']['email']

        msg = MIMEText("Test alert email")
        msg['Subject'] = "Alert System Test"
        msg['From'] = config['from_address']
        msg['To'] = config['recipients']['default'][0]

        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['username'], config['password'])
            server.send_message(msg)

        return "Email sent successfully"

    def test_alert_rules(self):
        """Test alert rule evaluation"""

        test_data = {
            "confidence": 0.87,
            "strength": "strong",
            "risk_score": 0.25,
            "cpu_usage": 45,
            "memory_usage": 67,
            "error_rate": 0.02
        }

        results = {}

        for rule_category, rules in self.config['alert_rules'].items():
            results[rule_category] = {}

            for rule_name, rule_config in rules.items():
                if rule_config.get('enabled', True):
                    try:
                        matches = self._evaluate_conditions(rule_config['conditions'], test_data)
                        results[rule_category][rule_name] = {
                            "matches": matches,
                            "conditions": rule_config['conditions']
                        }
                    except Exception as e:
                        results[rule_category][rule_name] = {
                            "error": str(e)
                        }

        return results

    def _evaluate_conditions(self, conditions: List[str], data: Dict) -> bool:
        """Evaluate alert conditions against test data"""

        for condition in conditions:
            # Simple condition evaluator (expand as needed)
            for key, value in data.items():
                condition = condition.replace(key, str(value))

            # Evaluate the condition (simplified)
            try:
                result = eval(condition)
                if not result:
                    return False
            except:
                return False

        return True

# Usage
async def main():
    tester = AlertTester()

    # Test all channels
    channel_results = await tester.test_all_channels()
    print("Channel Tests:")
    for channel, result in channel_results.items():
        print(f"  {channel}: {result['status']}")

    # Test alert rules
    rule_results = tester.test_alert_rules()
    print("\nRule Tests:")
    for category, rules in rule_results.items():
        print(f"  {category}:")
        for rule, result in rules.items():
            if 'matches' in result:
                print(f"    {rule}: {'✓' if result['matches'] else '✗'}")
            else:
                print(f"    {rule}: ERROR - {result.get('error', 'Unknown')}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Validation Scripts

```bash
#!/bin/bash
# validate_alert_config.sh

echo "Validating alert configuration..."

# Check configuration file syntax
python3 -c "
import json
try:
    with open('config/alerting.json') as f:
        config = json.load(f)
    print('✓ JSON syntax valid')
except Exception as e:
    print(f'✗ JSON syntax error: {e}')
    exit(1)
"

# Test environment variables
echo "Checking environment variables..."
python3 -c "
import os
required_vars = [
    'SLACK_WEBHOOK_URL',
    'EMAIL_USERNAME',
    'EMAIL_PASSWORD',
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN'
]

missing = []
for var in required_vars:
    if not os.getenv(var):
        missing.append(var)

if missing:
    print(f'✗ Missing environment variables: {missing}')
else:
    print('✓ All environment variables present')
"

# Test alert delivery
echo "Testing alert delivery..."
python3 scripts/test_alerts.py --quick-test

echo "Alert configuration validation complete"
```

## Performance Considerations

### Rate Limiting

```python
# scripts/rate_limiter.py
import time
from collections import defaultdict
from typing import Dict

class AlertRateLimiter:
    def __init__(self, config):
        self.limits = config['alert_system']['rate_limiting']
        self.counters = defaultdict(list)
        self.enabled = self.limits.get('enabled', True)

    def can_send_alert(self, alert_type: str, channel: str) -> bool:
        """Check if alert can be sent based on rate limits"""

        if not self.enabled:
            return True

        key = f"{alert_type}:{channel}"
        now = time.time()

        # Clean old entries
        self.counters[key] = [t for t in self.counters[key] if now - t < 3600]  # 1 hour window

        # Check hourly limit
        if len(self.counters[key]) >= self.limits['max_alerts_per_hour']:
            return False

        # Check burst limit (last 5 minutes)
        recent = [t for t in self.counters[key] if now - t < 300]  # 5 minutes
        if len(recent) >= self.limits['burst_limit']:
            return False

        return True

    def record_alert(self, alert_type: str, channel: str):
        """Record that an alert was sent"""

        key = f"{alert_type}:{channel}"
        self.counters[key].append(time.time())
```

### Batch Processing

```python
# scripts/alert_batcher.py
import asyncio
from collections import defaultdict
from typing import List, Dict

class AlertBatcher:
    def __init__(self, batch_size=10, batch_timeout=30):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.batches = defaultdict(list)

    async def add_alert(self, alert: Dict, channel: str):
        """Add alert to batch for processing"""

        batch_key = f"{channel}:{alert['category']}"
        self.batches[batch_key].append(alert)

        # Process if batch is full
        if len(self.batches[batch_key]) >= self.batch_size:
            await self._process_batch(batch_key)

    async def _process_batch(self, batch_key: str):
        """Process accumulated alerts in batch"""

        alerts = self.batches[batch_key]
        self.batches[batch_key] = []

        if not alerts:
            return

        channel, category = batch_key.split(':', 1)

        # Group similar alerts
        grouped = self._group_similar_alerts(alerts)

        for group in grouped:
            if len(group) == 1:
                await self._send_single_alert(group[0], channel)
            else:
                await self._send_grouped_alert(group, channel, category)

    def _group_similar_alerts(self, alerts: List[Dict]) -> List[List[Dict]]:
        """Group similar alerts together"""

        groups = defaultdict(list)

        for alert in alerts:
            # Group by type and symbol (for trading signals)
            if alert['category'] == 'trading_signal':
                key = f"{alert['type']}:{alert['data'].get('symbol', 'unknown')}"
            else:
                key = alert['type']

            groups[key].append(alert)

        return list(groups.values())
```

This comprehensive alert configuration guide provides all the necessary information to set up, customize, and maintain a robust alerting system for the IFD v3.0 Trading System. The multi-channel approach ensures critical information reaches the right people through their preferred communication methods while maintaining system performance and reliability.
