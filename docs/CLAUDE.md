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

### Databento Live Status - VERIFIED WITH CLOSED-LOOP CONFIRMATION
**✅ AUTHENTICATION ALWAYS WORKS!**
**✅ LIVE DATA VERIFIED WITH TRADOVATE REFERENCE!**

**CRITICAL**: Use VERIFIED live data system with closed-loop confirmation!
- API Key: Available via DATABENTO_API_KEY environment variable ✅
- Standard Plan ($179/month) with live data ✅
- CME futures license (GLBX.MDP3) ✅
- Closed-loop verification against Tradovate ✅

VERIFIED Working configuration:
```python
# Start verification server (Terminal 1)
python3 tests/chrome/live_data_verification.py

# Start closed-loop verification (Terminal 2)
python3 scripts/closed_loop_verification.py

# Criteria: <5 second time difference AND <$10 price difference = VERIFIED LIVE
```

**ALWAYS USE CLOSED-LOOP VERIFICATION FOR LIVE DATA CONFIDENCE!**

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

### Key Files - VERIFIED LIVE DATA SYSTEM
- **PRIMARY LIVE STREAM**: `scripts/databento_nq_live_final.py`
- **CLOSED-LOOP VERIFICATION**: `scripts/closed_loop_verification.py`
- **VERIFICATION SERVER**: `tests/chrome/live_data_verification.py`
- **TRADOVATE AUTOMATION**: `scripts/tradovate_auto_capture.py`
- **Live dashboard**: `scripts/monitoring_dashboard.py`
- **Main engine**: `src/analysis/ifd_analyzer_v3.py`
