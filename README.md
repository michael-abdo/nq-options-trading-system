# NQ Options Expected Value Trading System

## Overview
This system analyzes NQ (E-mini Nasdaq-100) futures options data to identify optimal trading opportunities with the highest Expected Value (EV). **Successfully discovered API endpoint providing Volume and Open Interest data sufficient for EV analysis.**

## ✅ Current Status
- **Working API Endpoint Discovered**: Captures Volume (51.9% coverage) and Open Interest (62.7% coverage)
- **Sufficient Data Quality**: Volume and OI data meets requirements for EV calculations
- **Streamlined Pipeline**: Removed experimental code, focused on working solution

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

### Run the EV Algorithm
```bash
python nq_options_ev_algo.py
```

## Project Structure (Streamlined)

```
EOD/
├── README.md                           # This file
├── CLAUDE.md                           # Project-specific Claude instructions  
├── requirements.txt                    # Python dependencies
├── nq_options_ev_algo.py               # Main EV algorithm
├── nq_options_ev_system.md             # System specifications
├── analysis_tools/                     # Essential breakthrough tools
│   ├── capture_api_requests.py         # **BREAKTHROUGH**: API discovery script
│   └── hunt_live_api.py                # Data quality verification
├── data/                               # Data storage
│   ├── api_responses/                  # **WORKING DATA**: Captured API responses
│   │   └── options_data_20250602_141553.json  # Volume & OI data source
│   ├── debug/                          # Debug output (cleaned)
│   ├── live_api/                       # API hunt results (cleaned)
│   ├── screenshots/                    # Screenshots (cleaned)
│   └── html_snapshots/                 # HTML captures (cleaned)
├── docs/                               # Core documentation
│   ├── logging_system.md              # Logging configuration docs
│   └── nq_ev_pseudocode.txt           # Algorithm pseudocode
├── logs/                               # Application logs
├── reports/                            # Generated trading reports
├── scripts/                            # Additional scripts (cleaned)
├── tests/                              # Unit tests
│   ├── test_barchart_scrape.py         # Scraping validation
│   └── test_data_validation.py         # Data quality tests
├── utils/                              # Core utilities
│   ├── logging_config.py              # Logging setup
│   └── nq_options_scraper.py          # Scraping utilities
└── venv/                               # Python virtual environment
```

## Key Breakthrough Files

### 🎯 Working Solution
- `analysis_tools/capture_api_requests.py` - **THE BREAKTHROUGH SCRIPT** that discovered the working API endpoint
- `data/api_responses/options_data_20250602_141553.json` - **WORKING DATA SOURCE** with Volume & OI
- `analysis_tools/hunt_live_api.py` - Confirmed data quality meets our needs

### Core Algorithm
- `nq_options_ev_algo.py` - Main Expected Value trading algorithm
- `nq_options_ev_system.md` - Complete system specifications

### Supporting Infrastructure
- `utils/nq_options_scraper.py` - API integration utilities
- `utils/logging_config.py` - Logging configuration
- `tests/` - Data validation and quality tests

## How It Works

1. **API Data Source**: Uses discovered Barchart API endpoint:
   ```
   https://www.barchart.com/proxies/core-api/v1/quotes/get?symbol=MC6M25&list=futures.options...
   ```

2. **Data Collection**: Extracts options data including:
   - Strike prices
   - Call/Put volumes (51.9% coverage)
   - Open interest (62.7% coverage)
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

- **Working Data Source**: Uses discovered API with Volume/OI data sufficient for analysis
- **Educational Purpose**: Algorithm assumes proper risk management
- **Production Ready**: Streamlined to essential components only