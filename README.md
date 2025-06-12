# NQ Options Trading System - Hierarchical Pipeline Framework

## Quick Start

**Single Entry Point with Flexible Usage**:

```bash
# Run with automatic data source selection (currently Barchart primary)
python3 run_pipeline.py

# Note: The system automatically selects the best available data source
# Priority: 1) Barchart (free), 2) Polygon (free tier), 3) Tradovate (demo), 4) Databento (CME)
python3 run_pipeline.py --help
```

This runs the complete Hierarchical Pipeline Analysis Framework with your actual NQ Options EV algorithm using **live market data** when available.

> **System Status**: Production-ready with comprehensive security, live trading infrastructure, and automated monitoring. Full test coverage with 96% success rate.

> **Data Source Status**: Multi-source system with intelligent failover. Barchart provides primary coverage, Databento available for premium CME Globex data.

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
│   ├── production_monitor.py          # Production monitoring system
│   ├── monitoring_dashboard.py        # Web monitoring dashboard
│   ├── validate_phase.py              # Phase validation script
│   ├── requirements_databento.txt     # Databento dependencies
│   └── setup_databento.sh             # Databento setup script
├── tests/                              # 🧪 TEST SUITE (32 test files)
│   ├── test_config_system.py          # Configuration system tests
│   ├── test_pipeline_config.py        # Pipeline configuration tests
│   ├── test_pipeline_with_config.py   # Full pipeline tests
│   ├── test_databento_integration.py  # Databento integration tests
│   ├── test_barchart_api_only.py      # Barchart API tests
│   ├── test_databento_api.py          # Databento API tests
│   ├── test_databento_nq_options.py   # NQ options specific tests
│   ├── test_live_trading_readiness.py # Live trading readiness tests
│   ├── test_api_authentication.py     # API authentication tests
│   ├── test_edge_cases.py             # Edge case handling tests
│   └── ... (22 more test files)       # Complete test coverage
├── archive/                            # Legacy files (archived)
├── docs/                               # 📚 DOCUMENTATION
│   ├── analysis/                       # Strategy documentation
│   ├── data_sources/                   # Data source guides
│   ├── live_trading_test_plan.txt     # Comprehensive test plan
│   └── *.md                           # System documentation
├── outputs/                            # 📁 ORGANIZED OUTPUT STRUCTURE
│   ├── YYYYMMDD/                       # Date-based organization
│   │   ├── analysis_exports/           # JSON analysis outputs
│   │   ├── api_data/                   # API responses
│   │   ├── reports/                    # Trading reports
│   │   └── polygon_api_results/        # Polygon.io results
│   ├── config_tests/                   # Configuration test results
│   ├── databento_cache/                # Databento cache
│   └── monitoring/                     # Production monitoring data
│       ├── production_metrics.json    # Real-time system metrics
│       ├── dashboard.html             # Web monitoring dashboard
│       └── monitor.log                # Monitoring system logs
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
├── templates/                          # 📋 DOCUMENTATION TEMPLATES
│   ├── phase_template.md               # Template for future phases
│   └── implementation_notes_template.md # Technical documentation template
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

### Clean Root Directory
The root directory contains only essential files:
- **`run_pipeline.py`** - Main entry point for the trading system
- **`README.md`** - This documentation file
- **`.env`** - Configuration file (API keys)
- **`.gitignore`** - Git configuration

All test files have been organized into the `tests/` directory for better structure.

### Directory Structure
```
├── tasks/                     # Core implementation modules
│   └── options_trading_system/
│       ├── analysis_engine/   # Analysis algorithms and strategies
│       ├── data_ingestion/    # Data source integrations
│       └── output_generation/ # Report generators
├── config/                    # Configuration profiles
├── docs/                      # Documentation and guides
├── outputs/                   # Generated outputs (auto-organized)
├── scripts/                   # Utility scripts
├── tests/                     # Test files
└── archive/                   # Legacy code for reference
```

### Automated Output Management
All generated files are automatically organized by date and type:

- **Analysis Results**: `outputs/YYYYMMDD/analysis_exports/` - JSON exports with trade recommendations
- **Trading Reports**: `outputs/YYYYMMDD/reports/` - Human-readable trading reports
- **System Logs**: `outputs/YYYYMMDD/logs/` - Pipeline execution logs
- **API Data**: `outputs/YYYYMMDD/api_data/` - Live market data snapshots
- **Performance Data**: `outputs/performance_tracking/` - System metrics

**No manual file management required** - the system automatically creates organized directories and routes all outputs appropriately.

## Data Sources

The system supports multiple data sources with automatic priority-based selection:

### Current Data Source Status

| Source | Status | Priority | Notes |
|--------|---------|----------|-------|
| **Barchart** | ✅ READY | 1 (Primary) | Free web scraping, no API key required |
| **Polygon.io** | ⚠️ Config Required | 2 | Free tier available, add API key to .env |
| **Tradovate** | ⚠️ Config Required | 3 | Demo mode, add credentials to .env |
| **Databento** | ✅ READY | 4 | CME Globex MDP3 subscription active ($179/mo) |

### Why Barchart is Primary
- **Free**: No API costs, uses web scraping with smart caching
- **Reliable**: Automatic fallback to saved data
- **Complete**: Full options chain data for NQ
- **Fast**: 5-minute cache reduces API calls significantly

### Databento Integration
Premium CME Globex data source with full integration:
- **Live Streaming**: Real-time trades schema available
- **Market Hours**: Automatic trading hours detection
- **Symbol Format**: Uses `NQ.OPT` with parent symbology
- **Cost Monitoring**: Built-in budget tracking ($179/month)
- **Reconnection**: Automatic backfill and error recovery
- **Note**: MBO schema requires premium subscription upgrade

### Configuration
```bash
# All API keys go in .env file
DATABENTO_API_KEY=your-key-here  # CME Globex MDP3 subscription active
POLYGON_API_KEY=your-key-here    # Optional - free tier
TRADOVATE_CID=your-cid           # Optional - demo mode
TRADOVATE_SECRET=your-secret     # Optional - demo mode

# Test data source availability
python3 tests/test_source_availability.py
python3 tests/test_databento_integration.py
python3 tests/test_mbo_live_streaming.py

# Test configuration system
python3 tests/test_config_system.py
python3 tests/test_barchart_caching.py
```

See [Data Sources Documentation](docs/data_sources/) for detailed setup guides.

## Production Monitoring

The system includes comprehensive production monitoring capabilities:

### Monitoring Features
- **Real-time Metrics**: System health, trading performance, cost tracking
- **Web Dashboard**: Visual monitoring interface with auto-refresh
- **Alert System**: Configurable thresholds with multiple alert levels
- **Historical Tracking**: 30-day retention of all metrics

### Quick Start Monitoring
```bash
# Start production monitoring
python3 scripts/production_monitor.py

# Launch web dashboard
python3 scripts/monitoring_dashboard.py

# View dashboard at: http://localhost:8080/dashboard.html
```

### Monitored Metrics
- **Trading Performance**: Signal accuracy, latency, win/loss ratios
- **System Health**: CPU, memory, disk usage, uptime
- **Cost Management**: Daily costs, budget tracking, API usage
- **Business Metrics**: ROI tracking, profit/loss analysis

See [Production Monitoring Guide](docs/PRODUCTION_MONITORING.md) for detailed setup and configuration.

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
