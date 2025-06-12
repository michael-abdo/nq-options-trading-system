# IFD v3.0 Deployment Guide

## Pre-Deployment Checklist

### System Requirements
- [ ] Python 3.8 or higher installed
- [ ] Network access to Databento API
- [ ] Barchart API credentials configured
- [ ] Sufficient disk space for SQLite databases (>1GB)
- [ ] System time synchronized (NTP)

### Configuration
- [ ] API credentials in `.env` file
- [ ] Configuration profile selected (ifd_v3_production)
- [ ] Budget limits configured ($150-200/month)
- [ ] Data sources verified

## Deployment Steps

### 1. Initial Setup
```bash
# Clone repository
git clone https://github.com/your-org/nq-options-trading-system.git
cd nq-options-trading-system

# Checkout production branch
git checkout phase-4-production-deployment

# Verify system works without dependencies
python3 run_pipeline.py --dry-run
```

### 2. Optional Dependency Installation
```bash
# For enhanced features (optional)
pip install -r tasks/options_trading_system/analysis_engine/requirements/phase4.txt

# Verify dependencies
python3 tasks/options_trading_system/analysis_engine/scripts/check_dependencies.py
```

### 3. Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# DATABENTO_API_KEY=your_key_here
# BARCHART_API_KEY=your_key_here
```

### 4. Staged Deployment

#### Stage 1: Shadow Mode (Recommended First Step)
```python
# In pipeline configuration
config = {
    "algorithm_version": "both",  # Run v1.0 and v3.0
    "testing_mode": "shadow",     # No actual trading
    "data_mode": "real_time"
}
```

#### Stage 2: Canary Deployment (10% Traffic)
```python
config = {
    "staged_rollout": {
        "stage": "canary",
        "v3_percentage": 10,
        "fallback_enabled": true
    }
}
```

#### Stage 3: Limited Production (50% Traffic)
```python
config = {
    "staged_rollout": {
        "stage": "limited",
        "v3_percentage": 50,
        "monitor_performance": true
    }
}
```

#### Stage 4: Full Production
```python
config = {
    "algorithm_version": "v3.0",
    "testing_mode": "production",
    "fallback_to_v1": true
}
```

## Monitoring

### Real-time Metrics
```bash
# View performance dashboard
python3 tasks/options_trading_system/analysis_engine/phase4/monthly_budget_dashboard.py

# Check system health
python3 tasks/options_trading_system/analysis_engine/phase4/uptime_monitor.py

# Monitor latency
python3 tasks/options_trading_system/analysis_engine/phase4/latency_monitor.py
```

### Log Locations
- **Production logs**: `outputs/production_logs/`
- **Performance metrics**: `outputs/performance_tracking/`
- **Rollout events**: `outputs/rollout/`
- **Error logs**: `outputs/errors/`

## Rollback Procedures

### Emergency Rollback
```bash
# Immediate rollback to v1.0
python3 tasks/options_trading_system/analysis_engine/strategies/emergency_rollback_system.py --execute

# Verify rollback
tail -f outputs/rollback/rollback_$(date +%Y%m%d).log
```

### Gradual Rollback
```python
# Reduce v3.0 traffic gradually
rollout_manager.adjust_traffic_split(v3_percentage=25)
rollout_manager.adjust_traffic_split(v3_percentage=10)
rollout_manager.adjust_traffic_split(v3_percentage=0)
```

## Performance Validation

### Success Criteria
- Accuracy: >75% (monitor daily)
- Latency: <100ms (95th percentile)
- Uptime: >99.9% (monthly)
- Cost: <$200/month
- Win/Loss: >1.8

### Monitoring Commands
```bash
# Check success metrics
python3 -c "
from phase4.success_metrics_tracker import SuccessMetricsTracker
tracker = SuccessMetricsTracker()
print(tracker.get_current_metrics())
"

# Verify cost tracking
python3 -c "
from phase4.monthly_budget_dashboard import MonthlyBudgetDashboard
dashboard = MonthlyBudgetDashboard()
print(dashboard.get_monthly_summary())
"
```

## Troubleshooting

### Common Issues

1. **WebSocket Disconnection**
   - Auto-reconnect should handle this
   - Check: `outputs/reconnection_log.json`
   - Manual restart if needed

2. **High Latency**
   - Check network connectivity
   - Verify data source performance
   - Review: `outputs/performance_tracking/latency_*.json`

3. **Budget Overrun**
   - System auto-throttles at 80%
   - Emergency stop at 100%
   - Adjust in `phase4/monthly_budget_dashboard.py`

4. **Accuracy Drop**
   - A/B testing will detect this
   - Auto-fallback to v1.0 if <65%
   - Review: `outputs/ab_testing/comparison_*.json`

## Support

### Logs to Collect for Support
1. `outputs/production_logs/production_$(date +%Y%m%d).log`
2. `outputs/errors/error_$(date +%Y%m%d).log`
3. `outputs/performance_tracking/daily_summary_$(date +%Y%m%d).json`
4. System configuration export

### Health Check Script
```bash
#!/bin/bash
echo "=== IFD v3.0 Health Check ==="
echo "1. Checking dependencies..."
python3 scripts/check_dependencies.py | grep "SYSTEM STATUS" -A 3

echo "2. Checking imports..."
python3 -c "from integration import AnalysisEngine; print('✅ Core imports OK')"

echo "3. Checking database..."
ls -la outputs/*.db

echo "4. Checking recent logs..."
tail -5 outputs/production_logs/production_$(date +%Y%m%d).log

echo "=== Health Check Complete ==="
```

## Best Practices

1. **Always start with Shadow Mode** for new deployments
2. **Monitor metrics closely** during first week
3. **Keep v1.0 fallback enabled** until confidence established
4. **Review logs daily** during initial deployment
5. **Set up alerts** for critical metrics
6. **Document any customizations** for future reference

## Next Steps

After successful deployment:
1. Monitor performance for 2 weeks
2. Optimize thresholds based on results
3. Consider expanding to other symbols
4. Plan for Phase 5 enhancements

**Support Contact**: Create issue at repository for assistance
