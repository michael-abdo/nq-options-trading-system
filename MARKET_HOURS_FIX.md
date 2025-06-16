# Futures Market Hours Fix

## Problem
The live dashboard showed "no data" during market hours on Monday morning because:
- Original code treated Monday's "yesterday" (Sunday) as weekend
- Didn't account for futures markets opening Sunday 6 PM ET
- Result: No data even though markets were open for 6+ hours

## Root Cause
In `databento_5m_provider.py`, the `get_latest_bars` method had:
```python
if now.weekday() >= 5:  # Saturday or Sunday
    # Go back to Friday
else:
    # Use yesterday's data
    end = now - timedelta(days=1)  # ❌ Monday → Sunday → "weekend"!
```

## Solution
Created `nq_5m_dash_app_markets_fixed.py` that:
1. Patches `get_latest_bars` with proper futures hours logic
2. Correctly identifies when markets are open:
   - Sunday 6 PM ET through Friday 5 PM ET
   - Handles Monday morning correctly
3. Fetches real-time data when markets are open

## Usage
```bash
# Use the market-aware dashboard
python scripts/nq_5m_dash_app_markets_fixed.py

# Or update your start script
bash scripts/start_live_ifd_dashboard.sh
```

## Verification
The logs now show:
- "Market OPEN - fetching data" (correct!)
- "Aggregated 359 1-min bars to 73 5-min bars" (real data!)

## Futures Market Hours Reference
- **Open**: Sunday 6:00 PM ET
- **Close**: Friday 5:00 PM ET
- **Trading**: Nearly 24/5 with brief daily maintenance break

The dashboard now correctly shows live data during all market hours!
