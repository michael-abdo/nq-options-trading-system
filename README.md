# NQ Options Trading System - Hierarchical Pipeline Framework

## Quick Start

**Single Entry Point with Flexible Usage**:

```bash
# Run monthly options pipeline (recommended)
python3 daily_options_pipeline.py --option-type monthly

# Run weekly options pipeline  
python3 daily_options_pipeline.py --option-type weekly

# Use global command for monthly options
nq-monthly

# Show help with all examples
python3 daily_options_pipeline.py --help
```

This runs the complete Hierarchical Pipeline Analysis Framework with your actual NQ Options EV algorithm using **live market data** when available.

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

- **Entry Point**: `daily_options_pipeline.py` - Modern options data pipeline with metrics
- **Pipeline System**: `tasks/options_trading_system/` - Modular analysis framework
- **Configuration**: `tasks/options_trading_system/analysis_engine/pipeline_config.json`
- **Documentation**: `docs/hierarchical_pipeline_framework.md`

## Project Structure

```
/Users/Mike/trading/algos/EOD/
├── CLAUDE.md                           # Project instructions
├── README.md                           # This file
├── daily_options_pipeline.py           # 🚀 MAIN ENTRY POINT
├── nq-monthly                          # Global command for monthly options
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
    │   └── barchart_web_scraper/       # Barchart API integration
    │       └── outputs/YYYYMMDD/       # Date-organized scraper outputs
    │           ├── api_data/           # Live API responses
    │           ├── web_data/           # Web scraped data
    │           ├── comparisons/        # Data comparison results
    │           ├── logs/               # Scraper logs
    │           ├── screenshots/        # Debug screenshots
    │           └── html_snapshots/     # Debug HTML captures
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