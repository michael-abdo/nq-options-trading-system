# Rollback Procedures for Failed Phases

## Overview
This document outlines the procedures for rolling back changes when a phase deployment fails or causes critical issues in production.

## Rollback Decision Matrix

### Severity Levels
| Level | Description | Action Required | Timeline |
|-------|-------------|----------------|----------|
| **CRITICAL** | System down, data loss, security breach | Immediate rollback | < 15 minutes |
| **HIGH** | Major functionality broken, >30% performance degradation | Rollback after assessment | < 1 hour |
| **MEDIUM** | Some features broken, 10-30% performance degradation | Fix forward or rollback | < 4 hours |
| **LOW** | Minor issues, <10% performance impact | Fix in next deployment | Next release |

### Rollback Triggers
1. **System Failure**: Complete system outage or crash loops
2. **Data Corruption**: Any data integrity issues detected
3. **Performance Crisis**: Latency >500ms or accuracy <50%
4. **Security Issue**: Any security vulnerability exploited
5. **Cost Explosion**: Costs exceed 200% of budget
6. **Cascade Failures**: Errors affecting downstream systems

## Pre-Deployment Preparation

### Rollback Requirements
- [ ] Previous version tagged in git
- [ ] Database backup completed
- [ ] Configuration snapshot saved
- [ ] Rollback scripts tested
- [ ] Team contact list updated
- [ ] Rollback decision tree documented

### Rollback Testing
```bash
# Test rollback in staging environment
./scripts/test_rollback.sh --phase 4 --simulate

# Verify rollback time
./scripts/measure_rollback_time.sh
```

## Rollback Procedures by Phase

### Phase 1: Databento Client Rollback

#### Immediate Actions (0-15 minutes)
1. **Stop Data Ingestion**
   ```bash
   # Disable Databento streaming
   python scripts/emergency_stop.py --service databento
   ```

2. **Switch to Backup Data Source**
   ```bash
   # Enable fallback to Barchart
   python scripts/enable_fallback.py --source barchart
   ```

3. **Clear Corrupted Cache**
   ```bash
   # Remove potentially corrupted data
   rm -rf outputs/databento_cache/*
   sqlite3 outputs/market_data.db "DELETE FROM mbo_events WHERE timestamp > datetime('now', '-1 hour');"
   ```

#### Recovery Steps (15-60 minutes)
1. **Restore Previous Version**
   ```bash
   git checkout tags/pre-phase1-stable
   cd tasks/options_trading_system/data_ingestion/databento_api/
   cp solution_backup.py solution.py
   ```

2. **Verify System Health**
   ```python
   python scripts/health_check.py --comprehensive
   ```

3. **Resume Operations**
   ```bash
   python scripts/resume_trading.py --validate
   ```

### Phase 2: Analysis Engine Rollback

#### Immediate Actions (0-15 minutes)
1. **Disable v3.0 Algorithm**
   ```python
   # Switch to v1.0 algorithm
   from config_manager import ConfigManager
   config = ConfigManager()
   config.update_profile('production', algorithm_version='v1.0')
   ```

2. **Clear Signal Cache**
   ```bash
   redis-cli FLUSHDB  # If using Redis
   rm -rf outputs/signal_cache/*
   ```

#### Recovery Steps (15-60 minutes)
1. **Restore Algorithm**
   ```bash
   cd tasks/options_trading_system/analysis_engine/
   git checkout tags/phase2-rollback institutional_flow_v3/
   ```

2. **Rebuild Baselines**
   ```python
   python scripts/rebuild_baselines.py --quick
   ```

### Phase 3: Integration Rollback

#### Immediate Actions (0-15 minutes)
1. **Disable A/B Testing**
   ```python
   # Force all traffic to v1.0
   config.update_profile('production', testing_mode='production', algorithm_version='v1.0')
   ```

2. **Reset Configuration**
   ```bash
   cp config/backup/pipeline_config.json config/pipeline_config.json
   ```

#### Recovery Steps (15-60 minutes)
1. **Restore Integration Layer**
   ```bash
   git checkout tags/pre-phase3 integration.py config_manager.py
   ```

2. **Validate Pipeline**
   ```python
   python tests/test_integration.py --production-safe
   ```

### Phase 4: Production Deployment Rollback

#### Immediate Actions (0-15 minutes)
1. **Execute Emergency Rollback**
   ```python
   from strategies.emergency_rollback_system import EmergencyRollback
   rollback = EmergencyRollback()
   rollback.execute_immediate()
   ```

2. **Disable New Features**
   ```bash
   # Disable all Phase 4 components
   for component in success_metrics websocket_backfill budget_dashboard; do
     python scripts/disable_component.py --name $component
   done
   ```

#### Recovery Steps (15-60 minutes)
1. **Restore Monitoring**
   ```bash
   # Switch to basic monitoring
   systemctl stop advanced-monitoring
   systemctl start basic-monitoring
   ```

2. **Clear State**
   ```bash
   # Reset all Phase 4 state
   rm -rf outputs/phase4_state/*
   sqlite3 outputs/metrics.db < scripts/reset_metrics.sql
   ```

## Automated Rollback Scripts

### Master Rollback Script
```bash
#!/bin/bash
# scripts/rollback_phase.sh

PHASE=$1
SEVERITY=$2

case $PHASE in
  1)
    echo "Rolling back Phase 1: Databento Client"
    ./rollback/phase1_rollback.sh
    ;;
  2)
    echo "Rolling back Phase 2: Analysis Engine"
    ./rollback/phase2_rollback.sh
    ;;
  3)
    echo "Rolling back Phase 3: Integration"
    ./rollback/phase3_rollback.sh
    ;;
  4)
    echo "Rolling back Phase 4: Production"
    ./rollback/phase4_rollback.sh
    ;;
  *)
    echo "Unknown phase: $PHASE"
    exit 1
    ;;
esac

# Verify rollback success
python scripts/verify_rollback.py --phase $PHASE
```

### Health Check Script
```python
# scripts/health_check.py
import sys
from datetime import datetime

def check_system_health():
    checks = {
        'data_ingestion': check_data_flow(),
        'analysis_engine': check_analysis(),
        'performance': check_performance(),
        'errors': check_error_rate()
    }

    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"❌ Health check failed: {failed}")
        return False

    print("✅ System healthy")
    return True

def check_data_flow():
    # Verify data is flowing
    pass

def check_analysis():
    # Verify analysis engine working
    pass

def check_performance():
    # Check latency and throughput
    pass

def check_error_rate():
    # Check error logs
    pass
```

## Communication Procedures

### Incident Response Team
1. **Technical Lead**: Make rollback decision
2. **Operations**: Execute rollback procedures
3. **QA**: Verify system health post-rollback
4. **Communications**: Update stakeholders
5. **Support**: Handle user inquiries

### Communication Templates

#### Initial Alert
```
SUBJECT: [SEVERITY] Production Issue - Phase X Deployment

Issue detected at: [timestamp]
Affected systems: [list]
Impact: [description]
Action: Initiating rollback procedures

ETA for resolution: [time]
```

#### Rollback Complete
```
SUBJECT: [RESOLVED] Phase X Rollback Complete

Rollback completed at: [timestamp]
Systems restored to: [version]
Current status: [operational/degraded]
Next steps: [root cause analysis]

Full incident report to follow.
```

## Post-Rollback Procedures

### Immediate (0-4 hours)
1. **Verify System Stability**
   - Run comprehensive health checks
   - Monitor error rates
   - Check performance metrics
   - Validate data integrity

2. **Document Incident**
   - Timeline of events
   - Decisions made
   - Actions taken
   - Current system state

### Short-term (4-24 hours)
1. **Root Cause Analysis**
   - Identify failure trigger
   - Analyze logs and metrics
   - Review deployment process
   - Interview team members

2. **Interim Report**
   - Executive summary
   - Technical details
   - Business impact
   - Preliminary recommendations

### Long-term (1-7 days)
1. **Comprehensive Post-Mortem**
   - Detailed timeline
   - Root cause identification
   - Contributing factors
   - Process improvements
   - Prevention measures

2. **Corrective Actions**
   - Fix identified issues
   - Update procedures
   - Enhance monitoring
   - Improve testing
   - Team training

## Rollback Metrics

### Success Criteria
- **Rollback Time**: < 15 minutes for critical
- **Data Loss**: Zero tolerance
- **Service Recovery**: 100% functionality restored
- **Performance**: Return to baseline metrics

### Tracking Metrics
```json
{
  "rollback_id": "uuid",
  "phase": 4,
  "trigger": "performance_degradation",
  "start_time": "2025-06-11T10:00:00Z",
  "completion_time": "2025-06-11T10:12:00Z",
  "duration_minutes": 12,
  "data_loss": false,
  "service_impact_minutes": 15,
  "root_cause": "memory_leak",
  "prevention_measures": ["added_memory_monitoring", "updated_tests"]
}
```

## Prevention Strategies

### Pre-deployment
1. **Canary Deployments**: Test with small traffic percentage
2. **Shadow Mode**: Run new code without affecting production
3. **Load Testing**: Verify performance under stress
4. **Chaos Engineering**: Test failure scenarios

### During Deployment
1. **Gradual Rollout**: Incremental traffic shifting
2. **Real-time Monitoring**: Watch key metrics
3. **Circuit Breakers**: Automatic failure isolation
4. **Feature Flags**: Quick feature disable

### Post-deployment
1. **Continuous Monitoring**: 24/7 metric tracking
2. **Anomaly Detection**: ML-based issue detection
3. **Regular Drills**: Practice rollback procedures
4. **Lessons Learned**: Continuous improvement

## Emergency Contacts

### Escalation Path
1. **L1 - Operations Team**: [contact]
2. **L2 - Technical Lead**: [contact]
3. **L3 - Engineering Manager**: [contact]
4. **L4 - CTO**: [contact]

### External Dependencies
- **Databento Support**: [contact]
- **Cloud Provider**: [contact]
- **Database Admin**: [contact]

---

**Document Version**: 1.0
**Last Updated**: 2025-06-11
**Next Review**: After first production rollback or in 3 months
