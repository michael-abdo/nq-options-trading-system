# NQ Options Trading System - Hierarchical Pipeline Framework

## Quick Start

**Single Entry Point with Flexible Usage**:

```bash
# Run with Databento (Standard E-mini NQ Options - $20 per point)
python3 run_pipeline.py

# Note: Contract arguments are deprecated. Databento automatically fetches
# current Standard E-mini NQ options data. For configuration options:
python3 run_pipeline.py --help
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

- **Entry Point**: `run_pipeline.py` - Single command to run everything
- **Pipeline System**: `tasks/options_trading_system/` - Modular analysis framework
- **Configuration**: `tasks/options_trading_system/analysis_engine/pipeline_config.json`
- **Documentation**: `docs/hierarchical_pipeline_framework.md`

## Project Structure

```
/Users/Mike/trading/algos/EOD/
├── CLAUDE.md                           # Project instructions
├── README.md                           # This file
├── run_pipeline.py                     # 🚀 MAIN ENTRY POINT
├── .env                                # Environment variables (API keys)
├── .gitignore                          # Git ignore patterns
├── config/                             # 📋 CONFIGURATION PROFILES
│   ├── databento_only.json            # Databento-only configuration (default)
│   ├── barchart_only.json             # Barchart-only configuration  
│   ├── all_sources.json               # All data sources enabled
│   └── testing.json                   # Testing configuration
├── scripts/                            # 🔧 UTILITY SCRIPTS
│   ├── compare_barchart_databento.py  # Data source comparison
│   ├── requirements_databento.txt     # Databento dependencies
│   └── setup_databento.sh             # Databento setup script
├── tests/                              # 🧪 TEST SUITE
│   ├── test_config_system.py          # Configuration system tests
│   ├── test_pipeline_config.py        # Pipeline configuration tests
│   ├── test_pipeline_with_config.py   # Full pipeline tests
│   ├── test_databento_integration.py  # Databento integration tests
│   ├── test_barchart_api_only.py      # Barchart API tests
│   ├── test_databento_api.py          # Databento API tests
│   ├── test_databento_nq_options.py   # NQ options specific tests
│   └── test_web_scrape_simple.py      # Web scraping tests
├── archive/                            # Legacy files (archived)
├── docs/                               # 📚 DOCUMENTATION
│   ├── analysis/                       # Strategy documentation
│   ├── data_sources/                   # Data source guides
│   └── *.md                           # System documentation
├── outputs/                            # 📁 ORGANIZED OUTPUT STRUCTURE
│   ├── YYYYMMDD/                       # Date-based organization
│   │   ├── analysis_exports/           # JSON analysis outputs
│   │   ├── api_data/                   # API responses
│   │   ├── reports/                    # Trading reports
│   │   └── polygon_api_results/        # Polygon.io results
│   ├── config_tests/                   # Configuration test results
│   └── databento_cache/                # Databento cache
├── tasks/options_trading_system/       # 🏗️ ACTIVE PIPELINE FRAMEWORK
│   ├── config_manager.py               # Configuration management
│   ├── analysis_engine/                # Analysis modules
│   ├── data_ingestion/                 # Data loading modules
│   │   ├── sources_registry.py        # Data source registry
│   │   ├── integration.py             # Pipeline integration
│   │   ├── barchart_web_scraper/      # Barchart API integration
│   │   ├── databento_api/             # Databento CME Globex live data
│   │   ├── polygon_api/               # Polygon.io Nasdaq-100 options
│   │   ├── interactive_brokers_api/   # Interactive Brokers integration
│   │   └── tradovate_api_data/        # Tradovate integration
│   └── output_generation/              # Results output modules
├── venv/                               # Python virtual environment
└── worktrees/                          # Git worktrees for branch work
```

## Configurable Data Sources

The system now supports **easy configuration switching** between data sources:

### Available Configurations
- **`databento_only.json`** - Standard E-mini NQ options (default, $20 per point)
- **`barchart_only.json`** - Micro E-mini NQ options ($2 per point)  
- **`all_sources.json`** - All data sources enabled
- **`testing.json`** - Test configuration with saved data

### Switching Data Sources
```bash
# Use different configuration profile
# Edit config/databento_only.json to enable/disable sources
# Or load different profile in run_pipeline.py

# Example: Switch from Databento to Barchart
# In config/databento_only.json, change:
# "databento": {"enabled": false}
# "barchart": {"enabled": true}
```

### Analysis Strategies
The system supports multiple analysis strategies via configuration:

- **Conservative**: Risk-first filtering with strict thresholds
- **Aggressive**: EV-first filtering with broader criteria  
- **Technical**: Pattern-first filtering for technical traders
- **Scalping**: Fast execution for intraday trading

Edit configuration files in `config/` directory to switch strategies and data sources.

## File Organization

**Automated Output Management**: All generated files are automatically organized by date and type:

- **Analysis Results**: `outputs/YYYYMMDD/analysis_exports/` - JSON exports with trade recommendations  
- **Trading Reports**: `outputs/YYYYMMDD/reports/` - Human-readable trading reports
- **System Logs**: `outputs/YYYYMMDD/logs/` - Pipeline execution logs
- **API Data**: `tasks/.../barchart_web_scraper/outputs/YYYYMMDD/api_data/` - Live market data
- **Debug Data**: Screenshots, HTML snapshots, and comparison results organized by date

**No manual file management required** - the system automatically creates organized directories and routes all outputs appropriately.

## Data Sources

The system supports multiple data sources for comprehensive market coverage:

### Live Data Sources
- **Databento** - CME Globex live futures and options data ($179/month subscription)
- **Barchart** - Web API for options chains and pricing
- **Polygon.io** - Nasdaq-100 options and market data
- **Interactive Brokers** - Real-time trading data
- **Tradovate** - Futures trading platform integration

### Setup Instructions
```bash
# Install Databento dependencies
pip install -r scripts/requirements_databento.txt

# Configure API keys (see docs/data_sources/databento.md)
export DATABENTO_API_KEY=your-key-here

# Test integration
python tests/test_databento_integration.py

# Test configuration system
python tests/test_config_system.py
```

See [Data Sources Documentation](docs/data_sources/) for detailed setup guides.

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