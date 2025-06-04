# NQ Options Expected Value Trading System

## Overview
This system analyzes NQ (E-mini Nasdaq-100) futures options data to identify optimal trading opportunities with the highest Expected Value (EV). **Successfully discovered API endpoint providing Volume and Open Interest data sufficient for EV analysis.**

## ✅ Current Status
- **Working API Endpoint Discovered**: Captures Volume (51.9% coverage) and Open Interest (62.7% coverage)
- **Sufficient Data Quality**: Volume and OI data meets requirements for EV calculations
- **Streamlined Pipeline**: Removed experimental code, focused on working solution
- **NEW: Tradovate Integration**: Added support for Tradovate API to access full options chain data

## Installation

1. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install required packages:
```bash
pip install requests beautifulsoup4 lxml websocket-client
```

## Usage

### Run the EV Report Generator
```bash
python scripts/run_saved_data_report.py
```

### Run Tests
```bash
python tests/test_saved_data_report.py
```

### Tradovate API Integration (NEW)
```bash
# Explore Tradovate API structure
python scripts/tradovate_api_explorer.py

# Get NQ options chain data
python scripts/tradovate_options_client.py
```

See [Tradovate Integration Guide](docs/tradovate_integration.md) for detailed setup instructions.

## Project Structure (Organized & Tested)

```
EOD/
├── README.md                           # This file
├── CLAUDE.md                           # Project-specific Claude instructions
├── .gitignore                          # Git ignore configuration
├── analysis/                           # Analysis tools and exploratory scripts
│   ├── capture_api_requests.py         # **BREAKTHROUGH**: API discovery script
│   └── hunt_live_api.py                # Data quality verification
├── data/                               # Data storage
│   └── api_responses/                  # Saved API responses
│       └── options_data_20250602_141553.json  # **WORKING DATA**: Volume & OI source
├── docs/                               # Documentation
│   ├── nq_options_ev_system.md         # Detailed system specifications
│   └── tradovate_integration.md        # Tradovate API integration guide
├── logs/                               # Session-based logging
│   └── YYYY-MM-DD_HH-MM-SS/            # Timestamped log directories
│       ├── calculations.log            # EV calculation details
│       ├── data.log                    # Data operations
│       ├── errors.log                  # Error tracking
│       └── main.log                    # Main execution log
├── reports/                            # Generated trading reports
│   └── nq_saved_data_ev_report_*.txt   # EV analysis reports
├── scripts/                            # Executable scripts
│   ├── run_api_report.py               # Generate report from API data
│   ├── run_saved_data_report.py        # **MAIN SCRIPT**: Generate report from saved data
│   ├── tradovate_api_explorer.py       # Explore Tradovate API endpoints
│   └── tradovate_options_client.py     # Retrieve NQ options chain from Tradovate
├── tests/                              # Unit tests
│   └── test_saved_data_report.py       # Tests for report generation
└── utils/                              # Utility modules
    └── logging_config.py               # Logging configuration
```

## Key Components

### 🎯 Working Solution
- `scripts/run_saved_data_report.py` - **MAIN SCRIPT** that generates EV trading recommendations
- `data/api_responses/options_data_20250602_141553.json` - **WORKING DATA SOURCE** with Volume & OI
- `analysis/capture_api_requests.py` - **THE BREAKTHROUGH SCRIPT** that discovered the working API endpoint

### Core Infrastructure
- `utils/logging_config.py` - Specialized logging configuration with data/calculations filters
- `tests/test_saved_data_report.py` - Comprehensive unit tests
- `docs/nq_options_ev_system.md` - Complete system specifications

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