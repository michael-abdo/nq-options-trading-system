# Troubleshooting Guide for IFD v3.0 Trading System

## Overview
This guide provides comprehensive troubleshooting solutions for common issues encountered in the IFD v3.0 Live Streaming Trading System. Follow the structured approach: **Identify → Diagnose → Resolve → Verify**.

## Quick Reference

### Emergency Procedures
```bash
# Stop all services immediately
pkill -f "python.*nq_realtime"
pkill -f "python.*run_pipeline"
pkill -f "python.*dashboard"

# Check system status
python3 scripts/production_monitor.py --health-check

# Emergency restart
./start_live_dashboard.sh --safe-mode
```

### Common Issues Summary
| Issue | Quick Fix | Section |
|-------|-----------|---------|
| Dashboard not loading | Check WebSocket port 8765 | [Dashboard Issues](#dashboard-connectivity-issues) |
| No live data | Verify API keys in .env | [Data Source Issues](#data-source-connection-problems) |
| High latency | Check network/CPU usage | [Performance Issues](#performance-and-streaming-issues) |
| Authentication failed | Regenerate API keys | [Authentication Issues](#api-authentication-problems) |
| Memory leak | Restart services, check config | [System Issues](#system-resource-problems) |

## Setup and Configuration Issues

### 1. Environment Setup Problems

#### Issue: Python Dependencies Missing
**Symptoms:**
- `ModuleNotFoundError` for required packages
- Import errors during startup

**Solution:**
```bash
# Check Python version (requires 3.8+)
python3 --version

# Install missing dependencies
pip install -r requirements.txt
pip install plotly jsonschema websockets asyncio

# Verify installation
python3 -c "import plotly, jsonschema, websockets; print('All dependencies OK')"
```

#### Issue: Environment Variables Not Loaded
**Symptoms:**
- "API key not found" errors
- Configuration defaults being used

**Solution:**
```bash
# Check .env file exists
ls -la .env

# If missing, create from template
cp .env.example .env

# Edit with your actual keys
nano .env

# Verify environment loading
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('DATABENTO_API_KEY:', os.getenv('DATABENTO_API_KEY', 'NOT_FOUND')[:10] + '...')
"
```

#### Issue: Configuration File Validation Errors
**Symptoms:**
- JSON parsing errors
- Configuration validation failures

**Solution:**
```bash
# Validate JSON syntax
python3 -c "
import json
with open('config/production.json') as f:
    config = json.load(f)
print('Configuration valid')
"

# Use configuration validator
python3 scripts/validate_config.py --config config/production.json

# Reset to default if corrupted
cp config/development.json config/production.json.backup
```

### 2. File Permission Issues

#### Issue: Cannot Write to Output Directories
**Symptoms:**
- Permission denied errors
- Missing output files

**Solution:**
```bash
# Fix output directory permissions
chmod -R 755 outputs/
mkdir -p outputs/$(date +%Y%m%d)/{analysis_exports,api_data,reports}

# Check disk space
df -h .

# Verify write permissions
touch outputs/test_write.tmp && rm outputs/test_write.tmp && echo "Write permissions OK"
```

## Data Source Connection Problems

### 1. Databento API Issues

#### Issue: Authentication Failures
**Symptoms:**
- "Unauthorized" API responses
- Connection refused errors

**Diagnosis:**
```bash
# Test API key directly
curl -H "Authorization: Bearer db-your-key-here" \
  "https://hist.databento.com/v1/metadata.list_datasets"

# Check key format (should start with 'db-')
echo $DATABENTO_API_KEY | grep -E '^db-[A-Za-z0-9]{32}$'
```

**Solution:**
```bash
# Regenerate API key from Databento dashboard
# Update .env file with new key
export DATABENTO_API_KEY="db-your-new-key-here"

# Test connection
python3 tests/test_databento_integration.py
```

#### Issue: WebSocket Connection Drops
**Symptoms:**
- Frequent reconnections
- Data stream interruptions

**Solution:**
```bash
# Check network stability
ping -c 10 hist.databento.com

# Increase connection timeout in config
# Edit config/production.json:
{
  "data_sources": {
    "databento": {
      "websocket_timeout": 60,
      "max_reconnect_attempts": 10,
      "reconnect_delay": 5
    }
  }
}

# Monitor connection health
python3 scripts/databento_connection_monitor.py
```

#### Issue: Rate Limiting
**Symptoms:**
- HTTP 429 responses
- API quota exceeded errors

**Solution:**
```bash
# Check current usage
python3 -c "
from tasks.options_trading_system.data_ingestion.databento_api.client import DatabentoClient
client = DatabentoClient()
print(client.get_usage_stats())
"

# Reduce request frequency in config
# Edit config/production.json:
{
  "data_sources": {
    "databento": {
      "rate_limit": 500,  # Reduce from 1000
      "batch_size": 50    # Reduce batch sizes
    }
  }
}
```

### 2. Barchart Fallback Issues

#### Issue: Web Scraping Blocked
**Symptoms:**
- HTTP 403/404 responses
- Empty data responses

**Solution:**
```bash
# Test direct access
curl -A "Mozilla/5.0" "https://www.barchart.com/futures/quotes/NQM25/options"

# Clear cache and retry
rm -rf outputs/cache/barchart/
python3 scripts/clear_cache.py --source barchart

# Enable fallback mode
# Edit config/production.json:
{
  "data_sources": {
    "barchart": {
      "fallback_enabled": true,
      "cache_ttl": 300,
      "retry_attempts": 5
    }
  }
}
```

### 3. Data Quality Issues

#### Issue: Missing or Invalid Data
**Symptoms:**
- Empty datasets
- Validation errors in processing

**Diagnosis:**
```bash
# Run data quality check
python3 scripts/data_quality_check.py --source all --date today

# Check data completeness
python3 -c "
from tasks.options_trading_system.data_ingestion.integration import DataIngestionPipeline
pipeline = DataIngestionPipeline()
stats = pipeline.get_data_quality_stats()
print(f'Data completeness: {stats[\"completeness\"]*100:.1f}%')
"
```

**Solution:**
```bash
# Force data refresh
python3 scripts/refresh_data.py --force --source databento

# Enable data validation
# Edit config/production.json:
{
  "processing": {
    "data_validation": true,
    "min_data_completeness": 0.95,
    "quality_checks": ["timestamp", "price", "volume"]
  }
}
```

## Performance and Streaming Issues

### 1. High Latency Problems

#### Issue: Slow Signal Generation
**Symptoms:**
- Processing times >100ms
- Dashboard updates delayed

**Diagnosis:**
```bash
# Run performance profiler
python3 tests/phase4/performance/test_performance_optimization.py

# Check system resources
top -p $(pgrep -f "python.*pipeline")
iostat -x 1 5
```

**Solution:**
```bash
# Optimize processing configuration
# Edit config/production.json:
{
  "processing": {
    "max_workers": 8,
    "buffer_size": 10000,
    "batch_size": 1000,
    "enable_profiling": false,
    "priority_queue": true
  }
}

# Enable performance optimizations
# Edit config/production.json:
{
  "ifd_v3": {
    "performance_optimized": true,
    "cache_optimization": true,
    "simplified_calculations": true
  }
}
```

#### Issue: Memory Usage Growing
**Symptoms:**
- Increasing RAM usage over time
- System becoming unresponsive

**Solution:**
```bash
# Monitor memory usage
python3 scripts/memory_monitor.py --interval 10

# Configure memory limits
# Edit config/production.json:
{
  "processing": {
    "max_memory_mb": 2048,
    "gc_threshold": 1000,
    "buffer_cleanup_interval": 300
  }
}

# Restart services periodically
# Add to cron:
# 0 */6 * * * /path/to/restart_services.sh
```

### 2. WebSocket Performance Issues

#### Issue: Dashboard Connection Drops
**Symptoms:**
- Frequent WebSocket disconnections
- "Connection lost" messages

**Solution:**
```bash
# Check WebSocket server health
netstat -an | grep :8765
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Host: localhost:8765" \
  -H "Origin: http://localhost:8765" \
  http://localhost:8765/

# Increase connection stability
# Edit config/production.json:
{
  "websocket": {
    "heartbeat_interval": 15,
    "max_clients": 50,
    "connection_timeout": 30,
    "compression": true
  }
}
```

#### Issue: Slow Chart Updates
**Symptoms:**
- Chart rendering delays
- UI becomes unresponsive

**Solution:**
```bash
# Optimize chart configuration
# Edit config/production.json:
{
  "dashboard": {
    "update_interval": 1000,
    "max_data_points": 100,
    "chart_optimization": true,
    "lazy_loading": true
  }
}

# Reduce browser memory usage
# Close unused browser tabs
# Clear browser cache
# Use Chrome with --max_old_space_size=4096
```

## API Authentication Problems

### 1. Key Management Issues

#### Issue: API Keys Expired or Invalid
**Symptoms:**
- 401 Unauthorized responses
- Authentication failures

**Solution:**
```bash
# Test all API keys
python3 scripts/test_api_keys.py

# Update expired keys
# For Databento:
# 1. Login to portal.databento.com
# 2. Generate new API key
# 3. Update .env file

# For Polygon:
# 1. Login to polygon.io dashboard
# 2. Regenerate API key
# 3. Update .env file

# Verify new keys
python3 tests/test_api_authentication.py
```

#### Issue: Environment Variable Conflicts
**Symptoms:**
- Wrong API keys being used
- Inconsistent authentication

**Solution:**
```bash
# Check environment precedence
env | grep -E "(DATABENTO|POLYGON|TRADOVATE)"

# Clear conflicting variables
unset DATABENTO_API_KEY
unset POLYGON_API_KEY

# Reload from .env
source .env
python3 -c "import os; print([k for k in os.environ.keys() if 'API' in k])"
```

### 2. Quota and Billing Issues

#### Issue: API Quota Exceeded
**Symptoms:**
- HTTP 429 rate limit errors
- Service degradation

**Solution:**
```bash
# Check usage limits
python3 scripts/check_api_usage.py --all-sources

# Implement usage tracking
# Edit config/production.json:
{
  "monitoring": {
    "api_usage_tracking": true,
    "quota_alerts": true,
    "cost_tracking": true
  }
}

# Set up usage alerts
python3 scripts/setup_usage_alerts.py --threshold 80
```

## Dashboard Connectivity Issues

### 1. WebSocket Server Issues

#### Issue: Server Won't Start
**Symptoms:**
- "Address already in use" errors
- WebSocket server startup failures

**Solution:**
```bash
# Find process using port 8765
lsof -i :8765

# Kill conflicting process
kill -9 $(lsof -t -i:8765)

# Start server with different port
python3 scripts/nq_realtime_ifd_dashboard.py --port 8766

# Update client configuration
# Edit dashboard HTML to use new port
```

#### Issue: CORS Errors
**Symptoms:**
- Browser console CORS errors
- Dashboard fails to load data

**Solution:**
```bash
# Enable CORS in WebSocket server
# Edit scripts/nq_realtime_ifd_dashboard.py:
import websockets
from websockets.exceptions import ConnectionClosed

# Add CORS headers
async def websocket_handler(websocket, path):
    websocket.response_headers['Access-Control-Allow-Origin'] = '*'
    # ... rest of handler
```

### 2. Browser Compatibility Issues

#### Issue: Dashboard Not Loading in Browser
**Symptoms:**
- Blank dashboard page
- JavaScript errors in console

**Solution:**
```bash
# Check browser compatibility
# Supported: Chrome 70+, Firefox 65+, Safari 12+

# Enable JavaScript debugging
# Open DevTools (F12)
# Check Console for errors

# Try different browser
# Clear browser cache and cookies
# Disable browser extensions

# Test with simple HTML
echo '<html><body>Test</body></html>' > outputs/test.html
open outputs/test.html
```

## System Resource Problems

### 1. CPU and Memory Issues

#### Issue: High CPU Usage
**Symptoms:**
- System sluggish
- High load averages

**Diagnosis:**
```bash
# Monitor CPU usage by component
top -p $(pgrep -f python)
htop
vmstat 1 10

# Profile application
python3 -m cProfile -o profile.out scripts/run_pipeline.py
python3 -c "
import pstats
p = pstats.Stats('profile.out')
p.sort_stats('cumulative').print_stats(10)
"
```

**Solution:**
```bash
# Optimize CPU usage
# Edit config/production.json:
{
  "processing": {
    "max_workers": 4,  # Reduce from 8
    "cpu_affinity": false,
    "process_priority": "normal"
  }
}

# Enable CPU throttling
# Add to system config:
echo 'performance' > /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

#### Issue: Memory Leaks
**Symptoms:**
- Continuously growing memory usage
- System running out of RAM

**Solution:**
```bash
# Monitor memory patterns
python3 scripts/memory_profiler.py --duration 3600

# Enable garbage collection optimization
# Edit config/production.json:
{
  "processing": {
    "gc_threshold": [700, 10, 10],
    "memory_limit_mb": 1024,
    "cleanup_interval": 300
  }
}

# Implement memory monitoring
python3 scripts/setup_memory_alerts.py --threshold 85
```

### 2. Disk Space Issues

#### Issue: Disk Full
**Symptoms:**
- Write errors
- Log files not being created

**Solution:**
```bash
# Check disk usage
df -h
du -sh outputs/

# Clean old files
find outputs/ -name "*.log" -mtime +7 -delete
find outputs/ -name "*.json" -mtime +30 -delete

# Configure log rotation
# Edit config/production.json:
{
  "logging": {
    "max_file_size": "50MB",
    "retention_days": 7,
    "rotation_enabled": true
  }
}
```

## Network Connectivity Issues

### 1. Firewall and Proxy Issues

#### Issue: Outbound Connections Blocked
**Symptoms:**
- Connection timeout errors
- API requests failing

**Solution:**
```bash
# Test external connectivity
curl -v https://hist.databento.com/v1/metadata.list_datasets
telnet hist.databento.com 443

# Configure proxy if needed
export https_proxy=http://proxy.company.com:8080
export http_proxy=http://proxy.company.com:8080

# Add to .env file:
HTTPS_PROXY=http://proxy.company.com:8080
HTTP_PROXY=http://proxy.company.com:8080
```

#### Issue: Port Conflicts
**Symptoms:**
- WebSocket server can't bind to port
- Dashboard inaccessible

**Solution:**
```bash
# Find available ports
netstat -tuln | grep -E ':(8765|8080)'

# Use alternative ports
python3 scripts/nq_realtime_ifd_dashboard.py --port 9000
python3 scripts/monitoring_dashboard.py --port 9001

# Update firewall rules if needed
sudo ufw allow 9000
sudo ufw allow 9001
```

## Recovery Procedures

### 1. Service Recovery

#### Complete System Recovery
```bash
#!/bin/bash
# Emergency system recovery script

echo "Starting emergency recovery..."

# Stop all services
pkill -f "python.*nq_realtime"
pkill -f "python.*run_pipeline"
pkill -f "python.*dashboard"

# Wait for processes to stop
sleep 5

# Clean temporary files
rm -rf /tmp/ifd_*
rm -rf outputs/temp/

# Verify configuration
python3 scripts/validate_config.py --config config/production.json

# Restart in safe mode
export SAFE_MODE=true
python3 scripts/run_pipeline.py --config config/production.json &
sleep 10

# Start dashboard
python3 scripts/nq_realtime_ifd_dashboard.py --safe-mode &
sleep 5

# Verify services
python3 scripts/health_check.py --all-services

echo "Recovery complete. Check outputs/recovery.log for details."
```

#### Data Recovery
```bash
# Restore from backup
cp -r outputs/backups/latest/* outputs/

# Rebuild cache
python3 scripts/rebuild_cache.py --all-sources

# Verify data integrity
python3 scripts/data_integrity_check.py --repair
```

### 2. Configuration Reset

#### Reset to Default Configuration
```bash
# Backup current config
cp config/production.json config/production.json.backup

# Reset to defaults
cp config/development.json config/production.json

# Update with production settings
python3 scripts/config_updater.py --profile production

# Validate new configuration
python3 scripts/validate_config.py --config config/production.json
```

## Monitoring and Alerting

### 1. Health Monitoring Setup

```bash
# Set up comprehensive monitoring
python3 scripts/setup_monitoring.py --enable-all

# Configure alerts
python3 scripts/setup_alerts.py \
  --email admin@company.com \
  --slack-webhook $SLACK_WEBHOOK_URL \
  --thresholds config/alert_thresholds.json

# Test alert system
python3 scripts/test_alerts.py --all-channels
```

### 2. Log Analysis

```bash
# Real-time log monitoring
tail -f outputs/$(date +%Y%m%d)/logs/system.log | grep -E "(ERROR|CRITICAL)"

# Log analysis
python3 scripts/log_analyzer.py \
  --log-file outputs/$(date +%Y%m%d)/logs/system.log \
  --time-range "last 1 hour" \
  --pattern "ERROR|CRITICAL"

# Generate log report
python3 scripts/log_report.py --date today --format html
```

## Prevention Best Practices

### 1. Regular Maintenance

```bash
# Daily maintenance script
#!/bin/bash
# Add to cron: 0 2 * * * /path/to/daily_maintenance.sh

# Check system health
python3 scripts/health_check.py --comprehensive

# Clean old files
find outputs/ -mtime +30 -delete

# Update data cache
python3 scripts/refresh_cache.py --selective

# Generate daily report
python3 scripts/daily_report.py --email admin@company.com
```

### 2. Configuration Validation

```bash
# Weekly configuration check
python3 scripts/config_audit.py --detailed

# Performance baseline check
python3 tests/phase4/performance/test_performance_optimization.py --baseline

# Security audit
python3 scripts/security_audit.py --api-keys --permissions
```

## Getting Help

### 1. Diagnostic Information Collection

```bash
# Generate diagnostic report
python3 scripts/diagnostic_report.py --comprehensive --output diagnostic_$(date +%Y%m%d).json

# System information
python3 -c "
import sys, platform, psutil
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print(f'CPU: {psutil.cpu_count()} cores')
print(f'RAM: {psutil.virtual_memory().total // (1024**3)} GB')
"
```

### 2. Support Resources

- **System Logs**: Check `outputs/YYYYMMDD/logs/` for detailed error information
- **Configuration Validation**: Use `python3 scripts/validate_config.py --help`
- **Performance Testing**: Run `python3 tests/phase4/run_all_tests.py --demo`
- **Health Checks**: Execute `python3 scripts/health_check.py --all-services`

### 3. Emergency Contacts

For critical system failures:
1. Run emergency recovery script
2. Check monitoring dashboard at http://localhost:8080
3. Review system logs for error patterns
4. Contact system administrator with diagnostic report

---

**Remember**: Always test solutions in development environment before applying to production. Keep regular backups and maintain system documentation up to date.
