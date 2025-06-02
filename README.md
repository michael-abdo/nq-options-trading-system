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

## Project Structure

```
EOD/
├── README.md                           # This file
├── CLAUDE.md                           # Project-specific Claude instructions  
├── requirements.txt                    # Python dependencies
├── package.json                        # Node.js dependencies
├── nq_options_ev_algo.py              # Main algorithm with live data scraping
├── nq_options_ev_algo_puppeteer.py    # Puppeteer-based scraping version
├── nq_options_ev_system.md            # Updated system specifications
├── analysis_tools/                    # Data analysis and investigation tools
│   ├── analyze_barchart_page.py       # Page structure analysis
│   ├── capture_api_requests.py        # Network monitoring
│   ├── hunt_live_api.py              # Live API endpoint discovery
│   ├── extract_complete_options_table.py  # Complete table extraction
│   └── investigate_professional_table.py  # Authentication analysis
├── data/                              # Data storage and captures
│   ├── api_responses/                 # Captured API responses
│   ├── debug/                         # Debug files and screenshots
│   ├── live_api/                      # Live API hunt results
│   ├── screenshots/                   # Visual captures
│   └── html_snapshots/               # Saved HTML pages
├── docs/                              # Documentation
│   ├── nq_options_ev_system.md       # System documentation
│   ├── feedback_loop_system.md       # Feedback loop documentation
│   └── logging_system.md             # Logging system docs
├── logs/                              # Application logs
│   └── YYYY-MM-DD_HH-MM-SS/          # Timestamped log directories
├── reports/                           # Generated trading reports
│   └── nq_ev_report_*.txt            # EV analysis reports
├── scripts/                           # Test and demo scripts
│   ├── test_*.py                      # Various testing scripts
│   └── demo_feedback_loop.py          # Demonstration scripts
├── tests/                             # Unit tests
│   ├── test_barchart_scrape.py       # Scraping tests
│   └── test_data_validation.py       # Data validation tests
├── utils/                             # Core utility modules
│   ├── nq_options_scraper.py         # Main scraping utilities
│   ├── feedback_loop_scraper.py      # Closed-loop scraping system
│   ├── puppeteer_scraper.py          # Puppeteer-based scraper
│   ├── logging_config.py             # Logging configuration
│   └── chrome_connection_manager.py  # Browser management
└── venv/                              # Python virtual environment
```

## Key Files

### Core Algorithms
- `nq_options_ev_algo.py` - Main Expected Value trading algorithm with live data
- `nq_options_ev_algo_puppeteer.py` - Puppeteer-based version with advanced scraping
- `nq_options_ev_system.md` - Complete system specifications and success criteria

### Scraping & Data Collection  
- `utils/nq_options_scraper.py` - Primary scraping utilities
- `utils/feedback_loop_scraper.py` - Self-improving closed-loop scraper
- `analysis_tools/hunt_live_api.py` - Live API endpoint discovery system
- `analysis_tools/capture_api_requests.py` - Network request monitoring

### Analysis & Investigation
- `analysis_tools/analyze_barchart_page.py` - Page structure analysis
- `analysis_tools/investigate_professional_table.py` - Authentication analysis
- `data/api_responses/options_data_*.json` - Captured live options data

### Documentation
- `docs/nq_options_ev_system.md` - System documentation  
- `docs/feedback_loop_system.md` - Closed feedback loop documentation
- `CLAUDE.md` - Project-specific instructions for Claude

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