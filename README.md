# NQ Options Expected Value Trading System

## Overview
This system analyzes NQ (E-mini Nasdaq-100) futures options end-of-day data from Barchart.com to identify optimal Target Price (TP) and Stop Loss (SL) combinations with the highest Expected Value (EV).

## Installation

1. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install required packages:
```bash
pip install requests beautifulsoup4 lxml
```

## Usage

### Basic Usage (with sample data)
```bash
python nq_options_ev_simple.py
```

### Advanced Usage (with actual Barchart scraping)
```bash
python nq_options_ev_algo.py
```

## Files

- `nq_options_ev_simple.py` - Main algorithm using sample data (works out of the box)
- `nq_options_ev_algo.py` - Full version with Barchart scraping capability
- `nq_options_scraper.py` - Enhanced scraping utilities
- `nq_options_ev_system.md` - Detailed system documentation

## How It Works

1. **URL Generation**: Automatically generates the correct Barchart URL for the current NQ options contract
   - Example: `https://www.barchart.com/futures/quotes/NQM25/options/MC6M25?futuresOptionsView=merged`

2. **Data Collection**: Scrapes options data including:
   - Strike prices
   - Call/Put volumes
   - Open interest
   - Premium prices

3. **EV Calculation**: Uses weighted factors to calculate probability and expected value:
   - Open Interest Factor (35% weight)
   - Volume Factor (25% weight)
   - Put/Call Ratio Factor (25% weight)
   - Distance Factor (15% weight)

4. **Output**: Generates a report with:
   - Top 5 trading opportunities ranked by EV
   - Execution recommendations
   - Position sizing guidance

## Example Output
```
================================================================================
NQ OPTIONS EV TRADING SYSTEM - 2025-06-02 06:34:44
================================================================================

Current NQ Price: 21,376.75

Top 5 Trading Opportunities:
--------------------------------------------------------------------------------
Rank  Direction  TP         SL         Prob     RR       EV        
--------------------------------------------------------------------------------
1     long       21500      21350      82.4%    4.6           +96.8
2     long       21500      21300      82.4%    1.6           +88.0
3     long       21450      21350      82.4%    2.7           +55.6

================================================================================
EXECUTION RECOMMENDATION:
Recommended Trade: LONG NQ
Entry: Current price (21,376.75)
Target: 21,500 (+123 points)
Stop: 21,350 (-27 points)
Position Size: LARGE (15-20%)
Expected Value: +96.8 points per trade
================================================================================
```

## Configuration

Edit the configuration section in the script to adjust:
- Factor weights
- Quality thresholds (MIN_EV, MIN_PROBABILITY, etc.)
- Distance weighting brackets

## Notes

- The simplified version (`nq_options_ev_simple.py`) uses sample data and works immediately
- For live data scraping, Barchart may require additional authentication or have rate limits
- Consider using a proxy or headers rotation for production use
- The algorithm assumes proper risk management and is for educational purposes