# System Maintenance & Monitoring Procedures

## Overview
This guide provides comprehensive maintenance and monitoring procedures for the IFD v3.0 Live Streaming Trading System. Regular maintenance ensures optimal performance, data integrity, and system reliability in production environments.

## Table of Contents
- [Daily Maintenance](#daily-maintenance)
- [Weekly Maintenance](#weekly-maintenance)
- [Monthly Maintenance](#monthly-maintenance)
- [Monitoring Setup](#monitoring-setup)
- [Performance Optimization](#performance-optimization)
- [Backup & Recovery](#backup--recovery)
- [Security Maintenance](#security-maintenance)
- [Log Management](#log-management)
- [Service Management](#service-management)
- [Emergency Procedures](#emergency-procedures)

## Daily Maintenance

### 1. System Health Check
**Schedule**: Every day at 6:00 AM ET (before market open)

```bash
#!/bin/bash
# daily_health_check.sh - Add to cron: 0 6 * * * /path/to/daily_health_check.sh

LOG_FILE="outputs/$(date +%Y%m%d)/logs/daily_health_check.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting daily health check..." >> $LOG_FILE

# 1. System resource check
echo "[$DATE] Checking system resources..." >> $LOG_FILE
df -h >> $LOG_FILE
free -h >> $LOG_FILE
uptime >> $LOG_FILE

# 2. Service status check
echo "[$DATE] Checking service status..." >> $LOG_FILE
python3 scripts/health_check.py --all-services >> $LOG_FILE 2>&1

# 3. API connectivity test
echo "[$DATE] Testing API connectivity..." >> $LOG_FILE
python3 tests/test_api_authentication.py >> $LOG_FILE 2>&1

# 4. Data quality check
echo "[$DATE] Checking data quality..." >> $LOG_FILE
python3 scripts/data_quality_check.py --source all --date today >> $LOG_FILE 2>&1

# 5. Performance metrics
echo "[$DATE] Collecting performance metrics..." >> $LOG_FILE
python3 scripts/performance_metrics.py --timeframe 24h >> $LOG_FILE 2>&1

# 6. Alert threshold check
echo "[$DATE] Checking alert thresholds..." >> $LOG_FILE
python3 scripts/check_alert_thresholds.py >> $LOG_FILE 2>&1

echo "[$DATE] Daily health check completed." >> $LOG_FILE

# Send summary email if configured
if [ "$ENABLE_EMAIL_REPORTS" = "true" ]; then
    python3 scripts/send_daily_report.py --log-file $LOG_FILE
fi
```

### 2. Data Source Validation
**Schedule**: Every day at 6:30 AM ET

```bash
#!/bin/bash
# daily_data_validation.sh

# Test all data sources
python3 tests/test_source_availability.py --verbose

# Validate historical data integrity
python3 scripts/validate_historical_data.py --date yesterday

# Check data completeness
python3 scripts/data_completeness_check.py --timeframe 24h

# Test live streaming connections
python3 tests/test_databento_live.py
python3 tests/test_mbo_live_streaming.py
```

### 3. Performance Monitoring
**Schedule**: Continuous monitoring with daily reports

```bash
#!/bin/bash
# daily_performance_monitoring.sh

# Run performance test suite
python3 tests/phase4/performance/test_performance_optimization.py --baseline

# Check latency trends
python3 scripts/latency_analysis.py --timeframe 24h

# Memory usage analysis
python3 scripts/memory_analysis.py --detect-leaks

# Generate performance report
python3 scripts/generate_performance_report.py --date today --format html
```

### 4. Log Analysis
**Schedule**: Every day at 8:00 PM ET (after market close)

```bash
#!/bin/bash
# daily_log_analysis.sh

TODAY=$(date +%Y%m%d)
LOG_DIR="outputs/$TODAY/logs"

# Analyze error patterns
python3 scripts/log_analyzer.py \
    --log-dir $LOG_DIR \
    --pattern "ERROR|CRITICAL|FATAL" \
    --timeframe 24h \
    --output "outputs/$TODAY/reports/error_analysis.html"

# Check for security events
python3 scripts/security_log_check.py --date today

# Generate log summary
python3 scripts/log_summary.py --date today --email admin@company.com
```

## Weekly Maintenance

### 1. Comprehensive System Review
**Schedule**: Every Sunday at 2:00 AM ET

```bash
#!/bin/bash
# weekly_maintenance.sh - Add to cron: 0 2 * * 0 /path/to/weekly_maintenance.sh

WEEK_START=$(date -d "7 days ago" +%Y-%m-%d)
WEEK_END=$(date +%Y-%m-%d)

echo "Starting weekly maintenance for period: $WEEK_START to $WEEK_END"

# 1. Comprehensive performance analysis
python3 scripts/weekly_performance_analysis.py \
    --start-date $WEEK_START \
    --end-date $WEEK_END

# 2. Data integrity verification
python3 scripts/data_integrity_check.py \
    --start-date $WEEK_START \
    --end-date $WEEK_END \
    --repair-mode

# 3. Configuration audit
python3 scripts/config_audit.py --comprehensive

# 4. Security audit
python3 scripts/security_audit.py --full-scan

# 5. API usage analysis
python3 scripts/api_usage_analysis.py --timeframe 7d

# 6. Cost analysis
python3 scripts/cost_analysis.py --period weekly

echo "Weekly maintenance completed"
```

### 2. Database Maintenance
**Schedule**: Every Sunday at 3:00 AM ET

```bash
#!/bin/bash
# weekly_database_maintenance.sh

# Clean old temporary files
find outputs/ -name "*.tmp" -mtime +7 -delete

# Compress old log files
find outputs/*/logs/ -name "*.log" -mtime +7 -exec gzip {} \;

# Archive old analysis results
python3 scripts/archive_old_data.py --days 30

# Optimize database indexes (if using database)
python3 scripts/database_maintenance.py --optimize-indexes

# Vacuum and analyze database
python3 scripts/database_maintenance.py --vacuum --analyze
```

### 3. Performance Optimization Review
**Schedule**: Every Sunday at 4:00 AM ET

```bash
#!/bin/bash
# weekly_optimization_review.sh

# Analyze performance trends
python3 scripts/performance_trend_analysis.py --period weekly

# Generate optimization recommendations
python3 scripts/optimization_recommender.py --timeframe 7d

# Test configuration changes
python3 scripts/test_config_optimizations.py --safe-mode

# Update performance baselines
python3 scripts/update_baselines.py --period weekly
```

## Monthly Maintenance

### 1. Comprehensive System Audit
**Schedule**: First Sunday of each month at 1:00 AM ET

```bash
#!/bin/bash
# monthly_audit.sh - Add to cron: 0 1 1-7 * 0 /path/to/monthly_audit.sh

MONTH=$(date +%Y-%m)
echo "Starting monthly audit for: $MONTH"

# 1. Complete system health audit
python3 scripts/comprehensive_audit.py --month $MONTH

# 2. Security compliance check
python3 scripts/security_compliance_check.py --full-audit

# 3. API key rotation check
python3 scripts/check_api_key_expiration.py --warn-days 30

# 4. Performance benchmark comparison
python3 scripts/monthly_benchmark.py --compare-baseline

# 5. Cost optimization analysis
python3 scripts/cost_optimization_analysis.py --period monthly

# 6. Capacity planning analysis
python3 scripts/capacity_planning.py --forecast-months 3

echo "Monthly audit completed"
```

### 2. Backup Verification
**Schedule**: First Sunday of each month at 2:00 AM ET

```bash
#!/bin/bash
# monthly_backup_verification.sh

# Test backup integrity
python3 scripts/backup_verification.py --test-restore

# Verify backup completeness
python3 scripts/backup_completeness_check.py --month $(date +%Y-%m)

# Test disaster recovery procedures
python3 scripts/test_disaster_recovery.py --simulation-mode

# Update backup retention policies
python3 scripts/backup_retention_management.py --cleanup-old
```

### 3. Documentation Updates
**Schedule**: First Sunday of each month at 3:00 AM ET

```bash
#!/bin/bash
# monthly_documentation_update.sh

# Update system documentation
python3 scripts/auto_update_docs.py --generate-metrics

# Update configuration documentation
python3 scripts/config_doc_generator.py --output docs/operations/

# Generate API documentation
python3 scripts/api_doc_generator.py --output docs/technical/

# Update troubleshooting guides
python3 scripts/update_troubleshooting_guide.py --add-recent-issues
```

## Monitoring Setup

### 1. Real-Time Monitoring Dashboard

```bash
#!/bin/bash
# setup_monitoring.sh - Run once to set up monitoring

# Install monitoring dependencies
pip install prometheus_client grafana-api influxdb-client

# Start monitoring services
python3 scripts/monitoring_dashboard.py --port 8080 &
python3 scripts/metrics_collector.py --interval 10 &
python3 scripts/alert_manager.py &

# Configure system metrics
python3 scripts/setup_system_monitoring.py \
    --cpu-threshold 80 \
    --memory-threshold 85 \
    --disk-threshold 90

# Configure application metrics
python3 scripts/setup_app_monitoring.py \
    --latency-threshold 100 \
    --error-rate-threshold 0.01 \
    --throughput-threshold 1000

echo "Monitoring setup completed. Dashboard available at http://localhost:8080"
```

### 2. Alert Configuration

```python
# scripts/setup_alerts.py
import json
from pathlib import Path

def setup_alert_system():
    """Configure comprehensive alert system"""

    alert_config = {
        "channels": {
            "email": {
                "enabled": True,
                "smtp_server": "smtp.company.com",
                "port": 587,
                "username": "alerts@company.com",
                "recipients": ["admin@company.com", "trading@company.com"]
            },
            "slack": {
                "enabled": True,
                "webhook_url": "${SLACK_WEBHOOK_URL}",
                "channel": "#trading-alerts"
            },
            "sms": {
                "enabled": True,
                "provider": "twilio",
                "account_sid": "${TWILIO_ACCOUNT_SID}",
                "auth_token": "${TWILIO_AUTH_TOKEN}",
                "numbers": ["+1234567890"]
            }
        },
        "alert_rules": {
            "critical_system_failure": {
                "conditions": ["cpu > 95", "memory > 98", "disk > 95"],
                "channels": ["email", "slack", "sms"],
                "escalation": True,
                "auto_resolve": False
            },
            "high_error_rate": {
                "conditions": ["error_rate > 0.05"],
                "channels": ["email", "slack"],
                "escalation": True,
                "auto_resolve": True
            },
            "performance_degradation": {
                "conditions": ["latency_p99 > 200", "throughput < 500"],
                "channels": ["slack"],
                "escalation": False,
                "auto_resolve": True
            },
            "data_quality_issues": {
                "conditions": ["data_completeness < 0.95"],
                "channels": ["email", "slack"],
                "escalation": True,
                "auto_resolve": False
            },
            "api_quota_warning": {
                "conditions": ["api_usage > 80"],
                "channels": ["email"],
                "escalation": False,
                "auto_resolve": True
            }
        },
        "escalation_policies": {
            "levels": [
                {"timeout_minutes": 5, "channels": ["slack"]},
                {"timeout_minutes": 15, "channels": ["email", "slack"]},
                {"timeout_minutes": 30, "channels": ["email", "slack", "sms"]}
            ]
        }
    }

    # Save configuration
    config_path = Path("config/alerting.json")
    with open(config_path, "w") as f:
        json.dump(alert_config, f, indent=2)

    print(f"Alert configuration saved to {config_path}")

if __name__ == "__main__":
    setup_alert_system()
```

### 3. Metrics Collection

```python
# scripts/metrics_collector.py
import time
import json
import psutil
import logging
from datetime import datetime
from pathlib import Path

class MetricsCollector:
    def __init__(self, interval=10):
        self.interval = interval
        self.logger = logging.getLogger(__name__)
        self.metrics_file = Path(f"outputs/monitoring/metrics_{datetime.now().strftime('%Y%m%d')}.json")
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

    def collect_system_metrics(self):
        """Collect system-level metrics"""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "usage_percent": psutil.cpu_percent(interval=1),
                "load_average": psutil.getloadavg(),
                "core_count": psutil.cpu_count()
            },
            "memory": {
                "total_gb": psutil.virtual_memory().total / (1024**3),
                "used_gb": psutil.virtual_memory().used / (1024**3),
                "usage_percent": psutil.virtual_memory().percent,
                "available_gb": psutil.virtual_memory().available / (1024**3)
            },
            "disk": {
                "total_gb": psutil.disk_usage('/').total / (1024**3),
                "used_gb": psutil.disk_usage('/').used / (1024**3),
                "usage_percent": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
                "free_gb": psutil.disk_usage('/').free / (1024**3)
            },
            "network": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv,
                "packets_sent": psutil.net_io_counters().packets_sent,
                "packets_recv": psutil.net_io_counters().packets_recv
            }
        }

    def collect_application_metrics(self):
        """Collect application-specific metrics"""
        try:
            # Import your application modules
            from tasks.options_trading_system.analysis_engine.integration import get_performance_metrics
            from tasks.options_trading_system.data_ingestion.integration import get_data_quality_metrics

            return {
                "timestamp": datetime.now().isoformat(),
                "performance": get_performance_metrics(),
                "data_quality": get_data_quality_metrics(),
                "signal_generation": self.get_signal_metrics(),
                "websocket": self.get_websocket_metrics()
            }
        except Exception as e:
            self.logger.error(f"Error collecting application metrics: {e}")
            return {"error": str(e)}

    def get_signal_metrics(self):
        """Get signal generation metrics"""
        try:
            # Read recent signals file
            today = datetime.now().strftime('%Y%m%d')
            signals_file = Path(f"outputs/{today}/analysis_exports/signals.json")

            if signals_file.exists():
                with open(signals_file) as f:
                    data = json.load(f)

                return {
                    "total_signals": len(data.get("signals", [])),
                    "avg_confidence": sum(s.get("confidence", 0) for s in data.get("signals", [])) / max(len(data.get("signals", [])), 1),
                    "last_signal_time": data.get("signals", [{}])[-1].get("timestamp", "N/A") if data.get("signals") else "N/A"
                }
            else:
                return {"total_signals": 0, "avg_confidence": 0, "last_signal_time": "N/A"}
        except Exception as e:
            return {"error": str(e)}

    def get_websocket_metrics(self):
        """Get WebSocket connection metrics"""
        # This would interface with your WebSocket server
        return {
            "active_connections": 0,  # Implement based on your WebSocket server
            "messages_sent": 0,
            "messages_received": 0,
            "connection_errors": 0
        }

    def save_metrics(self, metrics):
        """Save metrics to file"""
        try:
            # Read existing metrics
            if self.metrics_file.exists():
                with open(self.metrics_file) as f:
                    all_metrics = json.load(f)
            else:
                all_metrics = []

            # Append new metrics
            all_metrics.append(metrics)

            # Keep only last 1000 entries (about 2.7 hours at 10s intervals)
            if len(all_metrics) > 1000:
                all_metrics = all_metrics[-1000:]

            # Save back to file
            with open(self.metrics_file, 'w') as f:
                json.dump(all_metrics, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving metrics: {e}")

    def run(self):
        """Main metrics collection loop"""
        self.logger.info(f"Starting metrics collection (interval: {self.interval}s)")

        while True:
            try:
                # Collect all metrics
                system_metrics = self.collect_system_metrics()
                app_metrics = self.collect_application_metrics()

                combined_metrics = {
                    "system": system_metrics,
                    "application": app_metrics
                }

                # Save metrics
                self.save_metrics(combined_metrics)

                # Log summary
                cpu_usage = system_metrics["cpu"]["usage_percent"]
                memory_usage = system_metrics["memory"]["usage_percent"]
                self.logger.debug(f"Metrics collected - CPU: {cpu_usage:.1f}%, Memory: {memory_usage:.1f}%")

                time.sleep(self.interval)

            except KeyboardInterrupt:
                self.logger.info("Metrics collection stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")
                time.sleep(self.interval)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = MetricsCollector(interval=10)
    collector.run()
```

## Performance Optimization

### 1. Performance Analysis Scripts

```bash
#!/bin/bash
# performance_optimization.sh

# Run performance profiling
python3 -m cProfile -o profile.out scripts/run_pipeline.py --duration 300

# Analyze profile results
python3 scripts/analyze_profile.py --profile profile.out --top 20

# Memory profiling
python3 -m memory_profiler scripts/run_pipeline.py

# CPU profiling with py-spy
py-spy record -o cpu_profile.svg -- python3 scripts/run_pipeline.py --duration 60

# Generate optimization report
python3 scripts/optimization_report.py \
    --cpu-profile cpu_profile.svg \
    --memory-profile memory_profile.dat \
    --performance-profile profile.out
```

### 2. Configuration Optimization

```python
# scripts/optimize_configuration.py
import json
from pathlib import Path

def optimize_production_config():
    """Optimize configuration for production performance"""

    config_path = Path("config/production.json")
    with open(config_path) as f:
        config = json.load(f)

    # CPU optimization
    import multiprocessing
    optimal_workers = min(multiprocessing.cpu_count(), 8)
    config["processing"]["max_workers"] = optimal_workers

    # Memory optimization
    config["processing"]["buffer_size"] = 10000
    config["processing"]["batch_size"] = 1000
    config["processing"]["gc_threshold"] = [700, 10, 10]

    # Network optimization
    config["websocket"]["compression"] = True
    config["websocket"]["heartbeat_interval"] = 15

    # Cache optimization
    config["data_sources"]["barchart"]["cache_ttl"] = 300
    config["ifd_v3"]["cache_optimization"] = True

    # Save optimized configuration
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print("Configuration optimized for production")

if __name__ == "__main__":
    optimize_production_config()
```

## Backup & Recovery

### 1. Automated Backup System

```bash
#!/bin/bash
# backup_system.sh - Add to cron: 0 1 * * * /path/to/backup_system.sh

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/ifd_system/$BACKUP_DATE"
S3_BUCKET="ifd-system-backups"

echo "Starting backup: $BACKUP_DATE"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup configuration files
cp -r config/ $BACKUP_DIR/config/

# Backup critical scripts
cp -r scripts/ $BACKUP_DIR/scripts/

# Backup recent outputs (last 7 days)
find outputs/ -mtime -7 -type f | tar -czf $BACKUP_DIR/recent_outputs.tar.gz -T -

# Backup system logs
cp -r outputs/*/logs/ $BACKUP_DIR/logs/ 2>/dev/null || true

# Backup monitoring data
cp -r outputs/monitoring/ $BACKUP_DIR/monitoring/ 2>/dev/null || true

# Create backup manifest
cat > $BACKUP_DIR/backup_manifest.txt << EOF
Backup Date: $BACKUP_DATE
System Version: $(python3 -c "print('3.0.1')")
Configuration Files: $(find $BACKUP_DIR/config -type f | wc -l)
Script Files: $(find $BACKUP_DIR/scripts -type f | wc -l)
Data Size: $(du -sh $BACKUP_DIR | cut -f1)
EOF

# Compress entire backup
tar -czf /backup/ifd_system_backup_$BACKUP_DATE.tar.gz -C /backup/ifd_system $BACKUP_DATE

# Upload to S3 (if configured)
if [ "$ENABLE_S3_BACKUP" = "true" ]; then
    aws s3 cp /backup/ifd_system_backup_$BACKUP_DATE.tar.gz s3://$S3_BUCKET/
fi

# Clean up old backups (keep last 30 days)
find /backup/ifd_system/ -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: /backup/ifd_system_backup_$BACKUP_DATE.tar.gz"
```

### 2. Disaster Recovery Procedure

```bash
#!/bin/bash
# disaster_recovery.sh

RESTORE_DATE=${1:-"latest"}
BACKUP_DIR="/backup/ifd_system"

echo "Starting disaster recovery from backup: $RESTORE_DATE"

# Stop all services
echo "Stopping services..."
pkill -f "python.*nq_realtime"
pkill -f "python.*run_pipeline"
pkill -f "python.*dashboard"

# Create recovery point
echo "Creating recovery point..."
cp -r . /tmp/recovery_point_$(date +%Y%m%d_%H%M%S)

# Find backup file
if [ "$RESTORE_DATE" = "latest" ]; then
    BACKUP_FILE=$(ls -t $BACKUP_DIR/ifd_system_backup_*.tar.gz | head -1)
else
    BACKUP_FILE="$BACKUP_DIR/ifd_system_backup_$RESTORE_DATE.tar.gz"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Restoring from: $BACKUP_FILE"

# Extract backup
tar -xzf $BACKUP_FILE -C /tmp/

# Restore configuration files
echo "Restoring configuration..."
cp -r /tmp/*/config/* config/

# Restore critical scripts
echo "Restoring scripts..."
cp -r /tmp/*/scripts/* scripts/

# Verify configuration
echo "Verifying configuration..."
python3 scripts/validate_config.py --config config/production.json

# Test system connectivity
echo "Testing system connectivity..."
python3 tests/test_api_authentication.py

# Restart services
echo "Restarting services..."
python3 scripts/run_pipeline.py --config config/production.json &
sleep 10
python3 scripts/nq_realtime_ifd_dashboard.py &

# Verify recovery
echo "Verifying recovery..."
sleep 30
python3 scripts/health_check.py --all-services

echo "Disaster recovery completed"
```

## Security Maintenance

### 1. Security Audit Script

```bash
#!/bin/bash
# security_audit.sh

echo "Starting security audit..."

# Check for exposed API keys
echo "Checking for exposed API keys..."
grep -r "db-[A-Za-z0-9]" --exclude-dir=.git --exclude-dir=outputs . || echo "No API keys found in code"

# Check file permissions
echo "Checking file permissions..."
find . -type f -name "*.py" -perm /o+w -exec echo "World-writable file: {}" \;
find config/ -type f -perm /o+r -exec echo "World-readable config file: {}" \;

# Check for security updates
echo "Checking for security updates..."
pip list --outdated | grep -E "(cryptography|requests|urllib3|ssl)"

# Audit dependencies
echo "Auditing dependencies..."
pip-audit --output json --output-file outputs/security_audit_$(date +%Y%m%d).json

# Check SSL certificates
echo "Checking SSL certificates..."
python3 scripts/check_ssl_certificates.py

# Validate environment security
echo "Validating environment security..."
python3 scripts/security_validation.py --comprehensive

echo "Security audit completed"
```

### 2. API Key Rotation

```python
# scripts/rotate_api_keys.py
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

def check_api_key_expiration():
    """Check if API keys are approaching expiration"""

    keys_to_check = [
        ("DATABENTO_API_KEY", 90),  # Check 90 days before expiration
        ("POLYGON_API_KEY", 30),    # Check 30 days before expiration
    ]

    warnings = []

    for key_name, warn_days in keys_to_check:
        key_value = os.getenv(key_name)
        if not key_value:
            warnings.append(f"{key_name} not found in environment")
            continue

        # Check key expiration (implementation depends on API provider)
        expiry_date = check_key_expiry(key_name, key_value)
        if expiry_date:
            days_until_expiry = (expiry_date - datetime.now()).days
            if days_until_expiry <= warn_days:
                warnings.append(f"{key_name} expires in {days_until_expiry} days")

    return warnings

def rotate_api_key(key_name, new_key):
    """Rotate an API key"""

    # Update .env file
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            lines = f.readlines()

        # Update the key
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key_name}="):
                lines[i] = f"{key_name}={new_key}\n"
                updated = True
                break

        if not updated:
            lines.append(f"{key_name}={new_key}\n")

        with open(env_file, 'w') as f:
            f.writelines(lines)

    # Test new key
    os.environ[key_name] = new_key
    test_result = test_api_key(key_name, new_key)

    if test_result:
        print(f"Successfully rotated {key_name}")

        # Log rotation
        log_key_rotation(key_name)
    else:
        print(f"Failed to rotate {key_name} - key validation failed")

def log_key_rotation(key_name):
    """Log API key rotation"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": "api_key_rotation",
        "key_name": key_name,
        "rotated_by": "automated_script"
    }

    log_file = Path("outputs/security/key_rotation_log.json")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    if log_file.exists():
        with open(log_file) as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(log_entry)

    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)
```

## Log Management

### 1. Log Rotation and Cleanup

```bash
#!/bin/bash
# log_management.sh - Add to cron: 0 0 * * * /path/to/log_management.sh

LOG_RETENTION_DAYS=30
ARCHIVE_RETENTION_DAYS=90

echo "Starting log management..."

# Compress logs older than 7 days
find outputs/*/logs/ -name "*.log" -mtime +7 ! -name "*.gz" -exec gzip {} \;

# Move old compressed logs to archive
find outputs/*/logs/ -name "*.log.gz" -mtime +$LOG_RETENTION_DAYS -exec mv {} outputs/archive/logs/ \;

# Delete archived logs older than retention period
find outputs/archive/logs/ -name "*.log.gz" -mtime +$ARCHIVE_RETENTION_DAYS -delete

# Clean temporary files
find outputs/ -name "*.tmp" -mtime +1 -delete
find /tmp/ -name "ifd_*" -mtime +1 -delete

# Generate log statistics
python3 scripts/log_statistics.py --timeframe 24h > outputs/logs/log_stats_$(date +%Y%m%d).txt

echo "Log management completed"
```

### 2. Log Analysis Automation

```python
# scripts/automated_log_analysis.py
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

class LogAnalyzer:
    def __init__(self, log_directory):
        self.log_directory = Path(log_directory)
        self.patterns = {
            "error": re.compile(r"ERROR|CRITICAL|FATAL", re.IGNORECASE),
            "warning": re.compile(r"WARNING|WARN", re.IGNORECASE),
            "performance": re.compile(r"latency|performance|slow", re.IGNORECASE),
            "memory": re.compile(r"memory|oom|out of memory", re.IGNORECASE),
            "network": re.compile(r"connection|timeout|network", re.IGNORECASE)
        }

    def analyze_logs(self, hours=24):
        """Analyze logs for the last N hours"""

        cutoff_time = datetime.now() - timedelta(hours=hours)
        results = defaultdict(list)

        for log_file in self.log_directory.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_time.timestamp():
                continue

            with open(log_file) as f:
                for line_num, line in enumerate(f, 1):
                    for category, pattern in self.patterns.items():
                        if pattern.search(line):
                            results[category].append({
                                "file": str(log_file),
                                "line": line_num,
                                "message": line.strip(),
                                "timestamp": self.extract_timestamp(line)
                            })

        return dict(results)

    def extract_timestamp(self, line):
        """Extract timestamp from log line"""
        timestamp_pattern = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
        match = timestamp_pattern.search(line)
        return match.group() if match else None

    def generate_report(self, analysis_results):
        """Generate log analysis report"""

        report = {
            "analysis_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_issues": sum(len(issues) for issues in analysis_results.values()),
                "categories": {cat: len(issues) for cat, issues in analysis_results.items()}
            },
            "details": analysis_results
        }

        # Save report
        report_file = Path(f"outputs/logs/analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        return report

if __name__ == "__main__":
    analyzer = LogAnalyzer("outputs/$(date +%Y%m%d)/logs")
    results = analyzer.analyze_logs(hours=24)
    report = analyzer.generate_report(results)

    # Print summary
    print(f"Log Analysis Summary:")
    print(f"Total Issues: {report['summary']['total_issues']}")
    for category, count in report['summary']['categories'].items():
        print(f"  {category.title()}: {count}")
```

## Service Management

### 1. Service Control Scripts

```bash
#!/bin/bash
# service_manager.sh

SERVICE_ACTION=${1:-"status"}
CONFIG_FILE=${2:-"config/production.json"}

case $SERVICE_ACTION in
    "start")
        echo "Starting IFD v3.0 services..."

        # Start main pipeline
        python3 scripts/run_pipeline.py --config $CONFIG_FILE --daemon &
        echo $! > /tmp/ifd_pipeline.pid

        # Start dashboard
        python3 scripts/nq_realtime_ifd_dashboard.py --daemon &
        echo $! > /tmp/ifd_dashboard.pid

        # Start monitoring
        python3 scripts/monitoring_dashboard.py --daemon &
        echo $! > /tmp/ifd_monitoring.pid

        echo "Services started"
        ;;

    "stop")
        echo "Stopping IFD v3.0 services..."

        # Stop services gracefully
        if [ -f /tmp/ifd_pipeline.pid ]; then
            kill $(cat /tmp/ifd_pipeline.pid) 2>/dev/null
            rm /tmp/ifd_pipeline.pid
        fi

        if [ -f /tmp/ifd_dashboard.pid ]; then
            kill $(cat /tmp/ifd_dashboard.pid) 2>/dev/null
            rm /tmp/ifd_dashboard.pid
        fi

        if [ -f /tmp/ifd_monitoring.pid ]; then
            kill $(cat /tmp/ifd_monitoring.pid) 2>/dev/null
            rm /tmp/ifd_monitoring.pid
        fi

        # Force kill if necessary
        pkill -f "python.*run_pipeline"
        pkill -f "python.*dashboard"

        echo "Services stopped"
        ;;

    "restart")
        $0 stop
        sleep 5
        $0 start $CONFIG_FILE
        ;;

    "status")
        echo "IFD v3.0 Service Status:"

        if pgrep -f "python.*run_pipeline" > /dev/null; then
            echo "  Pipeline: RUNNING"
        else
            echo "  Pipeline: STOPPED"
        fi

        if pgrep -f "python.*dashboard" > /dev/null; then
            echo "  Dashboard: RUNNING"
        else
            echo "  Dashboard: STOPPED"
        fi

        if pgrep -f "python.*monitoring" > /dev/null; then
            echo "  Monitoring: RUNNING"
        else
            echo "  Monitoring: STOPPED"
        fi
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status} [config_file]"
        exit 1
        ;;
esac
```

### 2. Health Check Automation

```python
# scripts/health_check_automation.py
import time
import logging
import subprocess
from datetime import datetime

class HealthChecker:
    def __init__(self, check_interval=300):  # 5 minutes
        self.check_interval = check_interval
        self.logger = logging.getLogger(__name__)
        self.consecutive_failures = 0
        self.max_failures = 3

    def check_services(self):
        """Check all critical services"""
        services = {
            "pipeline": self.check_pipeline(),
            "dashboard": self.check_dashboard(),
            "monitoring": self.check_monitoring(),
            "api_connectivity": self.check_api_connectivity(),
            "disk_space": self.check_disk_space(),
            "memory_usage": self.check_memory_usage()
        }

        failures = [name for name, status in services.items() if not status]

        if failures:
            self.consecutive_failures += 1
            self.logger.warning(f"Health check failures: {failures}")

            if self.consecutive_failures >= self.max_failures:
                self.handle_critical_failure(failures)
        else:
            self.consecutive_failures = 0
            self.logger.info("All health checks passed")

        return services

    def check_pipeline(self):
        """Check if main pipeline is running"""
        try:
            result = subprocess.run(["pgrep", "-f", "python.*run_pipeline"],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def check_dashboard(self):
        """Check if dashboard is accessible"""
        try:
            import requests
            response = requests.get("http://localhost:8765/health", timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def check_api_connectivity(self):
        """Check API connectivity"""
        try:
            result = subprocess.run(["python3", "tests/test_api_authentication.py"],
                                  capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except Exception:
            return False

    def check_disk_space(self):
        """Check available disk space"""
        try:
            import shutil
            free_bytes = shutil.disk_usage('.').free
            free_gb = free_bytes / (1024**3)
            return free_gb > 5.0  # Require at least 5GB free
        except Exception:
            return False

    def check_memory_usage(self):
        """Check memory usage"""
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent
            return memory_percent < 90  # Alert if over 90% usage
        except Exception:
            return False

    def handle_critical_failure(self, failures):
        """Handle critical system failure"""
        self.logger.critical(f"Critical failure detected: {failures}")

        # Send alert
        self.send_critical_alert(failures)

        # Attempt automatic recovery
        if "pipeline" in failures:
            self.restart_pipeline()

        if "dashboard" in failures:
            self.restart_dashboard()

    def restart_pipeline(self):
        """Restart the main pipeline"""
        try:
            subprocess.run(["./service_manager.sh", "restart"], timeout=60)
            self.logger.info("Pipeline restart attempted")
        except Exception as e:
            self.logger.error(f"Failed to restart pipeline: {e}")

    def send_critical_alert(self, failures):
        """Send critical failure alert"""
        try:
            subprocess.run(["python3", "scripts/send_alert.py",
                          "--level", "critical",
                          "--message", f"Critical system failure: {', '.join(failures)}"])
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")

    def run(self):
        """Main health checking loop"""
        self.logger.info("Starting health checker")

        while True:
            try:
                self.check_services()
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                self.logger.info("Health checker stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Health checker error: {e}")
                time.sleep(self.check_interval)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    checker = HealthChecker(check_interval=300)  # Check every 5 minutes
    checker.run()
```

## Emergency Procedures

### 1. Emergency Shutdown

```bash
#!/bin/bash
# emergency_shutdown.sh

echo "EMERGENCY SHUTDOWN INITIATED"
echo "Timestamp: $(date)"

# Stop all trading activities immediately
echo "Stopping all trading services..."
pkill -f "python.*run_pipeline"
pkill -f "python.*trading"
pkill -f "python.*dashboard"

# Close any open positions (if live trading)
echo "Checking for open positions..."
python3 scripts/emergency_position_close.py --force

# Save current state
echo "Saving current state..."
python3 scripts/save_emergency_state.py

# Send emergency notifications
echo "Sending emergency notifications..."
python3 scripts/send_emergency_alert.py --message "Emergency shutdown executed"

# Create emergency log
echo "Creating emergency log..."
cat > outputs/emergency_shutdown_$(date +%Y%m%d_%H%M%S).log << EOF
Emergency Shutdown Report
========================
Timestamp: $(date)
Initiated by: Emergency shutdown script
Reason: Manual emergency shutdown

System Status Before Shutdown:
$(python3 scripts/health_check.py --all-services 2>&1)

Active Processes Terminated:
$(ps aux | grep python | grep -E "(pipeline|trading|dashboard)")

Next Steps:
1. Investigate cause of emergency
2. Verify system state
3. Test system before restart
4. Document incident
EOF

echo "Emergency shutdown completed"
echo "Check outputs/emergency_shutdown_*.log for details"
```

### 2. Incident Response Procedure

```python
# scripts/incident_response.py
from datetime import datetime
from pathlib import Path
import json
import subprocess

class IncidentResponse:
    def __init__(self, incident_type, severity="medium"):
        self.incident_id = f"INC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.incident_type = incident_type
        self.severity = severity
        self.start_time = datetime.now()

    def initiate_response(self):
        """Initiate incident response procedure"""

        # Create incident directory
        incident_dir = Path(f"outputs/incidents/{self.incident_id}")
        incident_dir.mkdir(parents=True, exist_ok=True)

        # Collect system information
        self.collect_system_info(incident_dir)

        # Send initial alert
        self.send_incident_alert()

        # Execute severity-specific procedures
        if self.severity == "critical":
            self.handle_critical_incident()
        elif self.severity == "high":
            self.handle_high_incident()

        # Create incident report
        self.create_incident_report(incident_dir)

    def collect_system_info(self, incident_dir):
        """Collect comprehensive system information"""

        # System status
        with open(incident_dir / "system_status.txt", "w") as f:
            subprocess.run(["python3", "scripts/health_check.py", "--comprehensive"],
                         stdout=f, stderr=subprocess.STDOUT)

        # Process list
        with open(incident_dir / "processes.txt", "w") as f:
            subprocess.run(["ps", "aux"], stdout=f)

        # System resources
        with open(incident_dir / "resources.txt", "w") as f:
            subprocess.run(["top", "-b", "-n", "1"], stdout=f)

        # Network status
        with open(incident_dir / "network.txt", "w") as f:
            subprocess.run(["netstat", "-tulpn"], stdout=f)

        # Recent logs
        subprocess.run(["cp", "-r", f"outputs/{datetime.now().strftime('%Y%m%d')}/logs",
                       str(incident_dir / "logs")])

    def handle_critical_incident(self):
        """Handle critical severity incident"""

        # Immediate actions for critical incidents
        actions = [
            "Emergency shutdown of non-essential services",
            "Isolation of affected components",
            "Escalation to senior management",
            "External vendor notification if required"
        ]

        for action in actions:
            print(f"CRITICAL ACTION: {action}")
            # Implement specific action logic here

    def send_incident_alert(self):
        """Send incident alert to relevant teams"""

        alert_message = f"""
INCIDENT ALERT - {self.severity.upper()}

Incident ID: {self.incident_id}
Type: {self.incident_type}
Severity: {self.severity}
Start Time: {self.start_time}

Immediate attention required.
Incident response procedures initiated.
        """

        subprocess.run(["python3", "scripts/send_alert.py",
                       "--level", self.severity,
                       "--message", alert_message])

    def create_incident_report(self, incident_dir):
        """Create comprehensive incident report"""

        report = {
            "incident_id": self.incident_id,
            "type": self.incident_type,
            "severity": self.severity,
            "start_time": self.start_time.isoformat(),
            "detection_method": "automated_monitoring",
            "affected_systems": ["trading_pipeline", "dashboard"],
            "impact_assessment": {
                "service_disruption": True,
                "data_loss": False,
                "financial_impact": "minimal"
            },
            "response_actions": [
                "System information collected",
                "Incident alert sent",
                "Containment procedures executed"
            ],
            "status": "active"
        }

        with open(incident_dir / "incident_report.json", "w") as f:
            json.dump(report, f, indent=2)

# Usage examples
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 incident_response.py <incident_type> [severity]")
        sys.exit(1)

    incident_type = sys.argv[1]
    severity = sys.argv[2] if len(sys.argv) > 2 else "medium"

    incident = IncidentResponse(incident_type, severity)
    incident.initiate_response()
```

## Maintenance Schedule Summary

### Automated Tasks (Cron Schedule)

```bash
# Add to crontab: crontab -e

# Daily health check (6:00 AM ET)
0 6 * * * /path/to/daily_health_check.sh

# Daily log analysis (8:00 PM ET)
0 20 * * * /path/to/daily_log_analysis.sh

# Daily backup (1:00 AM ET)
0 1 * * * /path/to/backup_system.sh

# Weekly maintenance (Sunday 2:00 AM ET)
0 2 * * 0 /path/to/weekly_maintenance.sh

# Monthly audit (First Sunday 1:00 AM ET)
0 1 1-7 * 0 /path/to/monthly_audit.sh

# Log management (Daily midnight)
0 0 * * * /path/to/log_management.sh

# Health monitoring (Every 5 minutes)
*/5 * * * * /path/to/health_check_automation.py
```

This comprehensive maintenance guide ensures optimal system performance, reliability, and security for the IFD v3.0 Trading System in production environments.
