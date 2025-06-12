# Production Monitoring Guide

## Overview
This guide describes the production monitoring system for the IFD v3.0 trading system, including real-time metrics collection, alerting, and dashboard visualization.

## Monitoring Architecture

### Core Components
```
Production Monitoring System
├── scripts/production_monitor.py     # Core monitoring engine
├── scripts/monitoring_dashboard.py   # Web dashboard
├── config/monitoring.json           # Configuration
└── outputs/monitoring/              # Metrics and logs
    ├── production_metrics.json      # Latest metrics
    ├── alerts.json                  # Active alerts
    ├── dashboard.json               # Dashboard data
    ├── dashboard.html               # Web interface
    └── monitor.log                  # Monitoring logs
```

### Monitored Metrics

#### System Health
- **CPU Usage**: Processor utilization percentage
- **Memory Usage**: RAM utilization percentage  
- **Disk Usage**: Storage utilization percentage
- **Network Status**: Connectivity to external services
- **Service Status**: Health of critical components

#### Trading Performance
- **Signal Accuracy**: Percentage of successful predictions
- **Average Latency**: System response time in milliseconds
- **Win/Loss Ratio**: Trading performance metric
- **Signals Generated**: Daily count of trading signals
- **Trade Success Rate**: Percentage of successful trades

#### Cost Management
- **Daily Cost**: Current day's operational costs
- **Monthly Budget Usage**: Percentage of monthly budget consumed
- **Cost per Signal**: Average cost to generate one signal
- **Data Usage Cost**: Costs from data providers
- **API Call Costs**: Costs from external API usage

#### Error Tracking
- **Error Rate**: Percentage of operations resulting in errors
- **Critical Errors**: Count of critical system errors
- **Warnings**: Count of system warnings
- **Connection Failures**: Network/API connection issues
- **Data Quality Issues**: Problems with incoming data
- **Uptime Percentage**: System availability metric

#### Business Metrics
- **ROI (Return on Investment)**: Daily and monthly ROI
- **Profit/Loss**: Financial performance
- **Performance vs Baseline**: Comparison to v1.0 baseline
- **Market Conditions**: Assessment of current market state

## Setup and Configuration

### Quick Start
```bash
# Start monitoring (continuous)
python scripts/production_monitor.py

# Run single monitoring cycle
python scripts/production_monitor.py --once

# Generate dashboard only
python scripts/production_monitor.py --dashboard

# Start web dashboard server
python scripts/monitoring_dashboard.py

# Generate dashboard HTML file only
python scripts/monitoring_dashboard.py --generate-only
```

### Configuration
Edit `config/monitoring.json` to customize:

```json
{
  "monitoring_interval": 60,          // Monitoring frequency (seconds)
  "alert_thresholds": {
    "signal_accuracy": 0.70,          // Alert if accuracy < 70%
    "system_latency": 150,            // Alert if latency > 150ms
    "error_rate": 0.05,               // Alert if error rate > 5%
    "daily_cost": 10.0,               // Alert if daily cost > $10
    "uptime": 0.995                   // Alert if uptime < 99.5%
  },
  "metrics_retention_days": 30,       // How long to keep metrics
  "dashboard_refresh_interval": 300   // Dashboard refresh (seconds)
}
```

### Alert Thresholds
The system monitors against these default thresholds:

| Metric | Warning | Critical | Target |
|--------|---------|----------|--------|
| Signal Accuracy | <75% | <70% | >75% |
| System Latency | >100ms | >150ms | <100ms |
| Error Rate | >3% | >5% | <2% |
| Daily Cost | >$8 | >$10 | <$8 |
| Uptime | <99.9% | <99.5% | >99.9% |
| Memory Usage | >80% | >90% | <80% |
| CPU Usage | >75% | >85% | <75% |

## Monitoring Operations

### Starting Monitoring
```bash
# Background monitoring
nohup python scripts/production_monitor.py > monitor.log 2>&1 &

# Monitoring with custom config
python scripts/production_monitor.py --config custom_monitoring.json

# Run monitoring once for testing
python scripts/production_monitor.py --once
```

### Dashboard Access
```bash
# Start web dashboard on default port 8080
python scripts/monitoring_dashboard.py

# Use custom port
python scripts/monitoring_dashboard.py --port 9000

# Generate static HTML dashboard
python scripts/monitoring_dashboard.py --generate-only
```

Access the dashboard at: `http://localhost:8080/dashboard.html`

### Metrics Files
- **production_metrics.json**: Latest complete metrics snapshot
- **alerts.json**: Current active alerts
- **dashboard.json**: Formatted data for dashboard
- **monitor.log**: Monitoring system logs

## Alert Management

### Alert Levels
- **INFO**: Informational messages
- **WARNING**: Issues requiring attention
- **CRITICAL**: Severe issues requiring immediate action

### Alert Responses

#### Signal Accuracy Alerts
```bash
# Check recent trading performance
grep "signal_accuracy" outputs/monitoring/production_metrics.json

# Review recent signals
ls -la outputs/*/analysis_exports/

# Check for market condition changes
python scripts/market_condition_check.py
```

#### System Performance Alerts
```bash
# Check system resources
python scripts/system_health_check.py

# Review error logs
tail -f outputs/monitoring/monitor.log

# Restart services if needed
python scripts/restart_services.py
```

#### Cost Management Alerts
```bash
# Review daily costs
python scripts/cost_breakdown.py --today

# Check API usage
python scripts/api_usage_report.py

# Adjust data collection if needed
python scripts/reduce_data_collection.py
```

## Integration with Production

### Automated Monitoring
Add to crontab for automatic startup:
```bash
# Start monitoring at system boot
@reboot cd /path/to/project && python scripts/production_monitor.py > monitor.log 2>&1 &

# Generate daily dashboard report
0 9 * * * cd /path/to/project && python scripts/monitoring_dashboard.py --generate-only
```

### Integration with Trading System
The monitor integrates with the trading system by:
- Reading performance data from `outputs/*/analysis_exports/`
- Monitoring cost data from `outputs/*/api_data/`
- Tracking errors from system logs
- Connecting to live trading feeds for real-time metrics

### CI/CD Integration
Add monitoring checks to deployment pipeline:
```yaml
# .github/workflows/deploy.yml
- name: Verify monitoring system
  run: |
    python scripts/production_monitor.py --once
    python scripts/monitoring_dashboard.py --generate-only
```

## Dashboard Features

### Real-time Metrics
- System status overview
- Key performance indicators
- Cost tracking
- Error monitoring
- Business metrics

### Visual Elements
- Color-coded status indicators (Green/Yellow/Red)
- Metric cards with trend information
- Alert notifications
- Automatic refresh every 5 minutes

### Historical Data
- 24-hour metric trends
- 7-day alert history
- 30-day performance tracking
- Monthly cost analysis

## Troubleshooting

### Common Issues

#### Monitoring Not Starting
```bash
# Check for port conflicts
netstat -tlnp | grep :8080

# Verify permissions
ls -la outputs/monitoring/

# Check dependencies
python -c "import json, time, logging"
```

#### Missing Metrics
```bash
# Check data sources
ls -la outputs/*/
ls -la outputs/monitoring/

# Verify file permissions
chmod 755 scripts/production_monitor.py

# Check log for errors
tail -f outputs/monitoring/monitor.log
```

#### Dashboard Not Loading
```bash
# Generate fresh dashboard
python scripts/monitoring_dashboard.py --generate-only

# Check HTML file
ls -la outputs/monitoring/dashboard.html

# Verify web server
python -m http.server 8080
```

### Performance Optimization
- Adjust monitoring interval based on needs
- Configure retention period for metrics
- Use dashboard generation instead of live server for production
- Archive old metrics to reduce disk usage

## Advanced Configuration

### Custom Metrics
Extend the monitoring system by modifying `ProductionMonitor` class:

```python
def collect_custom_metrics(self) -> Dict[str, Any]:
    """Add your custom metrics here"""
    return {
        "custom_metric": self._calculate_custom_value(),
        "business_kpi": self._get_business_kpi()
    }
```

### External Integrations
- **Slack**: Add webhook URL for alert notifications
- **Email**: Configure SMTP for email alerts  
- **External Monitoring**: Export metrics to Prometheus/Grafana
- **Cloud Services**: Push metrics to AWS CloudWatch or similar

### Scaling Considerations
- Use database for metric storage (SQLite/PostgreSQL)
- Implement metric aggregation for long-term storage
- Consider distributed monitoring for multiple instances
- Set up log rotation for long-running systems

## Security

### Access Control
- Run monitoring with restricted user permissions
- Use firewall rules to limit dashboard access
- Implement authentication for web dashboard if needed
- Secure API endpoints and credentials

### Data Privacy
- Avoid logging sensitive trading data
- Implement data retention policies
- Use encrypted connections for external integrations
- Regular security audits of monitoring components

---

**Monitoring System Version**: 1.0  
**Last Updated**: June 11, 2025  
**Supports**: IFD v3.0 Production Environment