# Databento Migration Guide

## Overview
This guide provides step-by-step instructions for re-enabling Databento as the primary data source once GLBX.MDP3 access is obtained.

## Current Status
- **Status**: Databento disabled due to lack of GLBX.MDP3 dataset access
- **Primary Data Source**: Barchart (web scraping with API)
- **Error**: `403 auth_no_dataset_entitlement: No entitlement for dataset GLBX.MDP3`

## Prerequisites for Migration
1. Databento API key with GLBX.MDP3 dataset access
2. Sufficient API quota for NQ options data
3. Testing environment for validation

## Migration Steps

### Step 1: Verify Databento Access
```bash
# Test Databento access
python3 test_mbo_streaming.py

# Expected output should show successful connection to GLBX.MDP3
```

### Step 2: Update Configuration Files

#### 2.1 Update databento_only.json
```json
{
  "profile_name": "databento_only",
  "description": "Databento as primary source for NQ options data",
  "data_sources": {
    "databento": {
      "enabled": true,  // Change from false to true
      "_comment": "Re-enabled with GLBX.MDP3 access",
      "config": {
        "api_key": "${DATABENTO_API_KEY}",
        "symbols": ["NQ"],
        "use_cache": true,
        "cache_dir": "outputs/databento_cache"
      }
    },
    "barchart": {
      "enabled": false,  // Change from true to false
      "_comment": "Disabled - using Databento as primary",
      "config": {
        "use_live_api": true,
        "futures_symbol": "NQM25",
        "headless": true
      }
    }
  }
}
```

#### 2.2 Update all_sources.json
```json
{
  "_comment": "Data source priority: 1=Databento (primary), 2=Barchart (backup), 3=Polygon, 4=Tradovate",
  "data_source_priority": ["databento", "barchart", "polygon", "tradovate"],
  // ... rest of config
}
```

### Step 3: Update Source Registry Priority
In `tasks/options_trading_system/data_ingestion/sources_registry.py`:

```python
self._source_priorities = {
    "databento": 1,      # Primary - real-time MBO data
    "barchart": 2,       # Secondary - free web scraping
    "barchart_live": 2,  # Same as barchart
    "polygon": 3,        # Tertiary - free tier with limits
    "tradovate": 4,      # Quaternary - demo mode
    "barchart_saved": 5  # Fallback - offline data
}
```

### Step 4: Remove Databento Access Check Override
In `tasks/options_trading_system/data_ingestion/databento_api/solution.py`:

Remove or comment out the forced access check:
```python
# Remove this block:
# if not self._check_dataset_access():
#     raise DatabentoAccessError("No access to required GLBX.MDP3 dataset")
```

### Step 5: Test Migration

#### 5.1 Run Integration Tests
```bash
# Test data source availability
python3 tests/test_source_availability.py

# Test pipeline with Databento
python3 tests/test_pipeline_with_config.py

# Test full pipeline
python3 run_pipeline.py
```

#### 5.2 Validate Data Quality
```bash
# Compare Databento vs Barchart data
python3 scripts/compare_barchart_databento.py
```

### Step 6: Monitor Performance

#### 6.1 Check API Usage
Monitor Databento API usage to ensure it stays within budget:
```bash
# Run cost monitoring
python3 outputs/live_trading_tests/api_costs_test.py
```

#### 6.2 Setup Alerts
Configure alerts for:
- API quota usage > 80%
- Failed API calls
- Data quality degradation

### Step 7: Update Documentation

#### 7.1 Update README.md
Change data source status table to reflect Databento as primary.

#### 7.2 Update CLAUDE.md
Add note about Databento being the primary data source.

## Rollback Plan

If issues occur during migration:

1. **Immediate Rollback**:
   ```bash
   # Copy backup configs
   cp config/databento_only.json.backup config/databento_only.json
   cp config/all_sources.json.backup config/all_sources.json
   ```

2. **Restart Pipeline**:
   ```bash
   python3 run_pipeline.py
   ```

3. **Verify Barchart is Active**:
   Check logs for "Loading data from barchart"

## Cost Considerations

### Current (Barchart)
- Cost: $0 (free web scraping)
- Limitations: Rate limits, potential blocking
- Data Quality: Good for EOD contracts

### Future (Databento)
- Estimated Cost: $50-100/month for NQ options
- Benefits: Real-time MBO data, higher reliability
- Data Quality: Excellent, institutional-grade

## Optimization Opportunities

Once Databento is re-enabled:

1. **Implement Smart Caching**:
   - Cache frequently accessed strikes
   - Implement TTL based on market hours

2. **Optimize API Calls**:
   - Batch requests where possible
   - Use WebSocket for real-time updates

3. **Hybrid Approach**:
   - Use Databento for active trading hours
   - Use Barchart for after-hours analysis

## Support Contacts

- Databento Support: support@databento.com
- Internal Team: [Your Team Contact]

## Revision History
- 2025-06-12: Initial migration guide created
- [Future Date]: Migration completed