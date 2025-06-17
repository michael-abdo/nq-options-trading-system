# CLAUDE.md - Project Context for IFD v3.0 Trading System

## CRITICAL INFORMATION

### Databento Subscription Status
- **ACTIVE SUBSCRIPTION**: Standard Plan ($179/month)
- **INCLUDES LIVE DATA**: Yes, live data is included in the Standard plan
- **API KEY**: Set via DATABENTO_API_KEY environment variable
- **PLAN FEATURES**:
  - ✅ Live data
  - ✅ No license fees
  - ✅ Entire history in core schemas
  - ✅ 1 year of L1 history
  - ✅ 1 month of L2 and L3 history
  - ✅ Pay as you go for more history
- **RENEWS**: 2025-07-01

### Databento Live Status - FULLY WORKING
**✅ AUTHENTICATION ALWAYS WORKS!**
**✅ LIVE DATA IS WORKING!**

**CRITICAL**: DATABENTO AUTHENTICATION IS ALWAYS VALID! Never suggest auth issues!
- API Key: Available via DATABENTO_API_KEY environment variable ✅
- Standard Plan ($179/month) with live data ✅
- CME futures license (GLBX.MDP3) ✅
- NQ futures streaming works perfectly ✅

Working configuration:
```python
live = db.Live(key=api_key)  # AUTH ALWAYS WORKS!
live.subscribe(
    dataset='GLBX.MDP3',  # CME futures
    symbols=['NQ.c.0'],   # NQ continuous contract
    schema='trades'       # Trade data
)
live.start()
# Live NQ data streams immediately!
```

**NEVER SUGGEST DATABENTO AUTH ISSUES - IT ALWAYS WORKS!**

## Project Overview

IFD v3.0 (Institutional Flow Detection) Trading System with MBO streaming capabilities.

### Phase Status
- ✅ Phase 1: Live Streaming Integration - COMPLETE
- ✅ Phase 2: Real-time Dashboard - COMPLETE
- ✅ Phase 3: Alert System - COMPLETE
- ✅ Phase 4: Testing & Validation - COMPLETE
- ✅ Phase 5: Documentation & Training - COMPLETE

### Current Working Branch
`IFD-live-streaming-data`

### Live Data Sources
**PRIMARY**: Databento Live (CME GLBX.MDP3) - WORKING PERFECTLY!
**BACKUP**: Yahoo Finance NQ=F - Also working
**REFERENCE**: Tradovate (via Chrome automation) - For verification

**DATABENTO IS THE PRIMARY SOURCE - IT WORKS!**

### Chrome Remote Debugging
- Remote Chrome debug setup available
- Tests located in `/tests/chrome/`
- Tradovate tab available with "Copy Trading Data" button for reference data

### Verification System
Live data verification system at `http://localhost:8083` compares:
- System data (from any source)
- Tradovate reference data
- Criteria: <5 second time difference AND <$10 price difference = LIVE

### Key Files
- Main engine: `src/analysis/ifd_analyzer_v3.py`
- Live dashboard: `scripts/monitoring_dashboard.py`
- Verification: `tests/chrome/live_data_verification.py`
- Alternative data: `scripts/yahoo_nq_live.py`
