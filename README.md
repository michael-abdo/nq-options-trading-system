# NQ Options Trading System - Hierarchical Pipeline Framework

## Quick Start

**Single Entry Point with Flexible Usage**:

```bash
# Run with today's auto-calculated EOD contract  
python3 run_pipeline.py

# Run with specific contract (multiple syntax options)
python3 run_pipeline.py MC7M25                    # Friday's EOD contract
python3 run_pipeline.py MC1M25                    # Monday's EOD contract  
python3 run_pipeline.py --contract MC2M25         # Tuesday's EOD contract
python3 run_pipeline.py MC6M25                    # Monthly options

# Show help with all examples
python3 run_pipeline.py --help
```

This runs the complete Hierarchical Pipeline Analysis Framework with your actual NQ Options EV algorithm using **live market data** when available.

## ⚡ 0DTE (Zero Days to Expiration) Pipeline

**NEW: Enhanced 0DTE validation system for same-day expiring options**:

```bash
# Run 0DTE pipeline with automatic symbol validation
python3 -c "
from tasks.options_trading_system.daily_options_pipeline import run_daily_0dte_pipeline
result = run_daily_0dte_pipeline()
print(f'Status: {result[\"status\"]}')
"

# Test symbol validation only (no data fetching)
python3 -c "
from tasks.options_trading_system.daily_options_pipeline import validate_0dte_symbol_only
result = validate_0dte_symbol_only()
print(f'Symbol: {result.get(\"symbol\", \"None\")}')
"

# Force specific symbol with validation
python3 -c "
from tasks.options_trading_system.daily_options_pipeline import run_with_forced_symbol
result = run_with_forced_symbol('MC4N25')
print(f'Status: {result[\"status\"]}')
"
```

### Key 0DTE Features:
- **Smart Symbol Generation**: Tries MC, MM, MQ prefixes until finding valid 0DTE contract
- **Expiration Validation**: Confirms symbols actually expire today using live web scraping
- **Automatic Fallbacks**: Falls back to alternative contract types if primary fails
- **Pipeline Abort**: Stops execution if no valid 0DTE symbol found
- **Weekend Handling**: Automatically shifts weekend requests to Monday contracts

## System Overview

The system uses a **hierarchical pipeline architecture** where each analysis acts as a filter, enricher, and sorter of trading opportunities:

```
Raw Data (1000 strikes) 
    ↓
Risk Analysis: Filter significant exposure → Sort by risk
    ↓ (100 opportunities)
EV Analysis: Filter positive EV → Sort by expected value  
    ↓ (50 opportunities)
Final Results: Top-ranked trading opportunities
```

## Core Components

- **Entry Point**: `run_pipeline.py` - Single command to run everything
- **0DTE Pipeline**: `tasks/options_trading_system/daily_options_pipeline.py` - 0DTE-specific processing
- **Pipeline System**: `tasks/options_trading_system/` - Modular analysis framework
- **Configuration**: `tasks/options_trading_system/analysis_engine/pipeline_config.json`
- **Documentation**: `docs/hierarchical_pipeline_framework.md`

### 0DTE System Components

- **Symbol Generator**: `tasks/options_trading_system/data_ingestion/barchart_web_scraper/symbol_generator.py`
  - Generates contract symbols with multiple prefix support (MC, MM, MQ)
  - Handles weekend/holiday date adjustments
  - Provides legacy compatibility with existing EOD logic

- **Expiration Validator**: `tasks/options_trading_system/data_ingestion/barchart_web_scraper/expiration_validator.py`
  - Selenium-based validation of actual expiration dates
  - Scrapes live data from Barchart to confirm 0DTE status
  - Supports headless browser operation for production

- **Daily Pipeline**: `tasks/options_trading_system/daily_options_pipeline.py`
  - Orchestrates complete 0DTE workflow
  - Integrates symbol generation, validation, and main pipeline
  - Provides abort mechanisms for invalid symbols

- **Test Suite**: `tasks/options_trading_system/test_0dte_pipeline.py`
  - Comprehensive test coverage for all 0DTE components
  - Integration tests and validation scenarios
  - Performance and error handling tests

## Project Structure

```
/Users/Mike/trading/algos/EOD/
├── CLAUDE.md                           # Project instructions
├── README.md                           # This file
├── run_pipeline.py                     # 🚀 MAIN ENTRY POINT
├── archive/                            # Legacy files (archived)
├── data/                               # Market data
├── docs/                               # Documentation
├── outputs/                            # 📁 ORGANIZED OUTPUT STRUCTURE
│   └── YYYYMMDD/                       # Date-based organization
│       ├── analysis_exports/           # JSON analysis outputs
│       ├── reports/                    # Trading reports
│       ├── logs/                       # System logs
│       └── samples/                    # Sample data files
├── tests/                              # Test scripts
└── tasks/options_trading_system/       # Active pipeline framework
    ├── analysis_engine/                # Analysis modules
    ├── data_ingestion/                 # Data loading modules
    │   ├── barchart_web_scraper/       # Barchart API integration
    │   ├── polygon_api/                # Polygon.io Nasdaq-100 options
    │   ├── interactive_brokers_api/    # Interactive Brokers integration
    │   ├── tradovate_api_data/         # Tradovate integration
    │   └── outputs/YYYYMMDD/           # Date-organized data outputs
    │       ├── api_data/               # Live API responses
    │       ├── web_data/               # Web scraped data
    │       ├── comparisons/            # Data comparison results
    │       ├── logs/                   # Data ingestion logs
    │       ├── screenshots/            # Debug screenshots
    │       └── html_snapshots/         # Debug HTML captures
    └── output_generation/              # Results output modules
```

## Configuration Strategies

The system supports multiple analysis strategies via configuration:

- **Conservative**: Risk-first filtering with strict thresholds
- **Aggressive**: EV-first filtering with broader criteria  
- **Technical**: Pattern-first filtering for technical traders
- **Scalping**: Fast execution for intraday trading

Edit `tasks/options_trading_system/analysis_engine/pipeline_config.json` to switch strategies.

## File Organization

**Automated Output Management**: All generated files are automatically organized by date and type:

- **Analysis Results**: `outputs/YYYYMMDD/analysis_exports/` - JSON exports with trade recommendations  
- **Trading Reports**: `outputs/YYYYMMDD/reports/` - Human-readable trading reports
- **System Logs**: `outputs/YYYYMMDD/logs/` - Pipeline execution logs
- **API Data**: `tasks/.../barchart_web_scraper/outputs/YYYYMMDD/api_data/` - Live market data
- **Debug Data**: Screenshots, HTML snapshots, and comparison results organized by date

**No manual file management required** - the system automatically creates organized directories and routes all outputs appropriately.

## Algorithm

Uses your actual NQ Options Expected Value algorithm with:
- **Risk Analysis** (35% OI, 25% Volume, 25% PCR, 15% Distance weighting)
- **Institutional Positioning** ("Who has more skin in the game?")
- **Quality Filtering** (Min EV: 15 points, Min Probability: 60%)

## Development

- **Add Analysis**: Implement `PipelineAnalysis` interface in new module
- **Reorder Pipeline**: Change order in configuration file
- **ML Optimization**: Tune weights and thresholds via config

## Historical Context

This system replaces the previous task-based implementation. All legacy files are preserved in the `archive/` directory for reference.

**Ready to trade with: `python3 run_pipeline.py`** 🚀