# NQ Options Trading System - Hierarchical Pipeline Framework

## Quick Start

**Production Trading System with Shadow Trading Mode**:

```bash
# Run standard analysis pipeline
python3 run_pipeline.py

# Run Shadow Trading Mode (1-week live validation without real positions)
python3 run_shadow_trading.py

# Run Limited Live Trading (small position sizes with strict risk controls)
python3 -c "from tasks.options_trading_system.analysis_engine.strategies.limited_live_trading_orchestrator import *; print('Limited Live Trading Ready')"

# Test system readiness
python3 tests/shadow_trading/test_real_performance_metrics.py
python3 tests/limited_live_trading/test_limited_live_trading_integration.py
```

> **System Status**: Production-ready with **Shadow Trading Mode** for live market validation. Real algorithms, real data, real performance tracking - no real positions.

> **Shadow Trading**: Comprehensive 1-week validation system with IFD v1.0/v3.0 algorithms, real-time performance metrics, signal validation, and false positive detection.

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

- **Analysis Pipeline**: `run_pipeline.py` - Traditional analysis execution
- **Shadow Trading**: `run_shadow_trading.py` - Live market validation system
- **Limited Live Trading**: `limited_live_trading_orchestrator.py` - Risk-controlled live position testing
- **Pipeline System**: `tasks/options_trading_system/` - Modular analysis framework
- **Trading Engine**: `tasks/options_trading_system/analysis_engine/strategies/` - Live validation and trading components
- **Configuration**: Multiple profile-based configurations for different trading modes
- **Documentation**: `docs/` - Comprehensive system and strategy documentation

## Project Structure

```
/Users/Mike/trading/algos/EOD/
├── CLAUDE.md                           # Project instructions
├── README.md                           # This file
├── run_pipeline.py                     # 🚀 ANALYSIS PIPELINE ENTRY POINT
├── run_shadow_trading.py               # 🎯 SHADOW TRADING ENTRY POINT
├── .env                                # Environment variables (API keys)
├── .gitignore                          # Git ignore patterns
├── config/                             # 📋 CONFIGURATION PROFILES
│   ├── databento_only.json            # Databento-only configuration
│   ├── barchart_only.json             # Barchart-only configuration (default)
│   ├── all_sources.json               # All data sources enabled
│   ├── shadow_trading.json            # Shadow trading configuration
│   ├── testing.json                   # Testing configuration
│   └── profiles/                       # Algorithm-specific profiles
├── scripts/                            # 🔧 UTILITY SCRIPTS
│   ├── compare_barchart_databento.py  # Data source comparison
│   ├── production_monitor.py          # Production monitoring system
│   ├── monitoring_dashboard.py        # Web monitoring dashboard
│   ├── validate_phase.py              # Phase validation script
│   ├── requirements_databento.txt     # Databento dependencies
│   └── setup_databento.sh             # Databento setup script
├── tests/                              # 🧪 TEST SUITE (40+ test files)
│   ├── shadow_trading/                 # Shadow trading system tests
│   │   ├── test_real_performance_metrics.py     # Performance metrics tests
│   │   ├── test_algorithm_integration.py        # Algorithm integration tests
│   │   ├── test_signal_validation.py            # Signal validation tests
│   │   └── test_shadow_trading_integration.py   # Complete system tests
│   ├── test_config_system.py          # Configuration system tests
│   ├── test_pipeline_config.py        # Pipeline configuration tests
│   ├── test_databento_integration.py  # Databento integration tests
│   ├── test_live_trading_readiness.py # Live trading readiness tests
│   ├── test_api_authentication.py     # API authentication tests
│   └── ... (30+ more test files)      # Complete test coverage
├── archive/                            # Legacy files (archived)
├── docs/                               # 📚 DOCUMENTATION
│   ├── SHADOW_TRADING_IMPLEMENTATION_SUMMARY.md # Complete implementation guide
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
│   ├── shadow_trading/                 # Shadow trading validation outputs
│   │   └── YYYY-MM-DD/                # Shadow trading session results
│   │       ├── ab_testing/            # A/B testing comparison results
│   │       ├── paper_trading/         # Paper trading execution logs
│   │       └── performance_tracking/  # Real-time performance metrics
│   ├── config_tests/                   # Configuration test results
│   ├── databento_cache/                # Databento cache
│   └── monitoring/                     # Production monitoring data
│       ├── production_metrics.json    # Real-time system metrics
│       ├── dashboard.html             # Web monitoring dashboard
│       └── monitor.log                # Monitoring system logs
├── tasks/options_trading_system/       # 🏗️ ACTIVE PIPELINE FRAMEWORK
│   ├── config_manager.py               # Configuration management
│   ├── analysis_engine/                # Analysis modules and strategies
│   │   ├── strategies/                 # Trading strategy implementations
│   │   │   ├── shadow_trading_orchestrator.py    # Shadow trading main engine
│   │   │   ├── real_performance_metrics.py       # Real-time performance tracking
│   │   │   ├── signal_validation_engine.py       # Signal validation & false positive detection
│   │   │   ├── market_relevance_tracker.py       # Market timing and relevance analysis
│   │   │   └── ...                    # Additional strategy modules
│   │   └── integration.py             # Analysis pipeline integration
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

## Shadow Trading Mode

**Shadow Trading Mode provides comprehensive live market validation without taking real positions**:

### Features
- **Real Market Data**: Live feeds from Barchart, Databento, Polygon, and Tradovate
- **Real Algorithms**: IFD v1.0 (Dead Simple Volume Spike) and IFD v3.0 (Enhanced MBO Streaming)
- **Signal Validation**: Advanced validation engine with false positive detection
- **Performance Tracking**: Real-time latency, cost, and data quality monitoring
- **Paper Trading**: Complete execution simulation with P&L tracking
- **Daily Reports**: Comprehensive validation analysis with recommendations

### Quick Start
```bash
# Run 1-week shadow trading validation
python3 run_shadow_trading.py

# Test shadow trading components
python3 tests/shadow_trading/test_real_performance_metrics.py
python3 tests/shadow_trading/test_algorithm_integration.py
python3 tests/shadow_trading/test_signal_validation.py
```

### Configuration
Shadow trading configuration is managed in `config/shadow_trading.json`:
- **Duration**: 1-7 days validation period
- **Trading Hours**: Market hours and optimal trading windows
- **Confidence Thresholds**: Signal quality requirements
- **Risk Limits**: Maximum daily loss and position size limits
- **Validation Criteria**: Signal validation and false positive detection settings

### Validation Engine

## Limited Live Trading Mode

**Limited Live Trading provides risk-controlled position testing with real money but strict limits**:

### Features
- **1-Contract Maximum**: Strict position size limits for initial testing
- **Real Order Placement**: Actual broker integration with live order execution
- **P&L Tracking**: Real profits and losses vs algorithm predictions
- **Budget Enforcement**: Automatic shutoffs at $8 daily and $200 monthly limits
- **Execution Quality**: Slippage and fill quality monitoring
- **Risk Management**: Stop-loss and profit target automation

### Configuration
Limited live trading uses strict risk controls:
- **Max Position Size**: 1 contract maximum per position
- **Daily Cost Limit**: $8 maximum data costs per day
- **Monthly Budget**: $200 maximum operational budget
- **Cost Per Signal**: <$5 target for signal generation costs
- **Risk Limits**: $50 max daily loss, $200 max total risk exposure

### Example Usage
```python
from tasks.options_trading_system.analysis_engine.strategies.limited_live_trading_orchestrator import (
    LimitedLiveTradingConfig, LimitedLiveTradingOrchestrator
)

# Configure limited live trading
config = LimitedLiveTradingConfig(
    start_date='2025-06-12',
    duration_days=1,
    max_position_size=1,
    daily_cost_limit=8.0,
    monthly_budget_limit=200.0,
    auto_shutoff_enabled=True
)

# Start live trading
orchestrator = LimitedLiveTradingOrchestrator(config)
orchestrator.start_live_trading()

# Process signals with strict risk controls
signal = {'id': 'test', 'confidence': 0.75, 'expected_value': 25.0}
success = orchestrator.process_signal_for_live_trading(signal)

# Monitor trading status
status = orchestrator.get_trading_status()
print(f"Positions: {status['open_positions']}, Risk: ${status['total_risk']:.2f}")
```

### Testing Suite
Comprehensive integration tests validate all limited live trading features:
```bash
python3 tests/limited_live_trading/test_limited_live_trading_integration.py
```

## Error Handling and Recovery System

**Comprehensive error handling with production-grade robustness testing**:

### Error Handling Features
- **Production Error Handler**: 5-level severity system with automatic alerts
- **Stream Recovery Manager**: Exponential backoff reconnection protocols
- **Data Quality Monitor**: Real-time validation with configurable thresholds
- **Automatic Failover Manager**: Circuit breaker patterns for API failures
- **Budget Enforcement**: Strict limits maintained during extreme conditions
- **Emergency Procedures**: Manual intervention and trading suspension

### Test Coverage
Complete error scenario validation with 4 specialized test suites:
```bash
# Run comprehensive error handling tests
python3 tests/error_handling/run_all_error_tests.py

# Individual test suites
python3 tests/error_handling/test_error_handling_and_recovery.py      # Core (17 tests)
python3 tests/error_handling/test_market_data_validation.py           # Data quality (7 tests)
python3 tests/error_handling/test_broker_connection_failures.py       # Connectivity (11 tests)
python3 tests/error_handling/test_system_resilience.py                # Stress testing (8 tests)
```

### Validated Error Scenarios
- **Market Volatility**: Position limits during extreme price movements
- **Data Feed Issues**: Interruption recovery with exponential backoff
- **Network Problems**: Connectivity recovery and timeout handling
- **API Failures**: Graceful degradation and automatic failover
- **Broker Issues**: Connection failures and retry mechanisms
- **System Stress**: High-frequency errors and resource exhaustion
- **Manual Recovery**: Emergency procedures and health monitoring
- **Cascading Failures**: Multi-component failure resilience

### Validation Engine
The signal validation engine provides comprehensive signal quality assessment:
- **Historical Pattern Matching**: Correlates signals with historical success patterns
- **Market Context Analysis**: Validates timing and market conditions
- **Technical Criteria**: Confidence, expected value, and risk/reward validation
- **False Positive Detection**: Multi-factor analysis to identify unreliable signals

### Performance Metrics
Real-time performance tracking includes:
- **Latency Monitoring**: Data load and algorithm execution times
- **Cost Tracking**: API usage and provider-specific cost monitoring
- **Data Quality**: Completeness, error rates, and source reliability
- **System Resources**: CPU, memory, and network utilization

See [Shadow Trading Implementation Guide](docs/SHADOW_TRADING_IMPLEMENTATION_SUMMARY.md) for complete details.

## Configurable Data Sources

The system now supports **easy configuration switching** between data sources:

### Available Configurations
- **`barchart_only.json`** - Micro E-mini NQ options (default, $2 per point)
- **`databento_only.json`** - Standard E-mini NQ options ($20 per point)
- **`all_sources.json`** - All data sources enabled
- **`shadow_trading.json`** - Shadow trading validation configuration
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
