# HIERARCHICAL PIPELINE TRADING SYSTEM

## Core Architecture
**HIERARCHICAL INTEGRATION PIPELINE**: Build on the established task-based directory structure using integration modules and comprehensive testing.

## System Structure

### **CURRENT ARCHITECTURE**:
```
project_root/
├── tasks/options_trading_system/
│   ├── analysis_engine/
│   │   ├── integration.py          # IFD v3.0 integration hub
│   │   ├── pipeline_config.json    # Pipeline configuration
│   │   ├── institutional_flow_v3/  # Core IFD v3.0 implementation
│   │   │   ├── solution.py         # Main algorithm
│   │   │   └── optimizations.py    # Performance enhancements
│   │   ├── strategies/             # Trading strategies
│   │   ├── monitoring/             # Performance tracking
│   │   └── tests/                  # Integration tests
│   ├── data_ingestion/
│   │   ├── integration.py          # Data pipeline coordinator
│   │   ├── databento_api/          # Market data feed
│   │   └── barchart_web_scraper/   # Backup data source
│   └── output_generation/
│       ├── integration.py          # Output system
│       └── report_generator/       # Trading reports
├── scripts/                        # Execution scripts
│   ├── run_pipeline.py            # Main pipeline runner
│   ├── run_shadow_trading.py      # Shadow trading mode
│   └── validate_phase.py          # Phase validation
└── tests/                         # System-wide tests
    └── shadow_trading/            # Shadow trading tests
```

## Development Guidelines

### **1. INTEGRATION-FIRST APPROACH**
- Each major component has an `integration.py` that coordinates submodules
- Integration modules are the primary entry points
- All components must work through the integration layer

### **2. PIPELINE CONFIGURATION**
- `pipeline_config.json` defines the data flow
- Configuration-driven architecture for flexibility
- Supports multiple trading profiles (production, testing, conservative)

### **3. TESTING STRATEGY**
- Integration tests in `tests/` directories
- Shadow trading for real-time validation
- Performance monitoring built into the system

### **4. MODULE STRUCTURE**
```
module/
├── solution.py      # Core implementation
├── integration.py   # Module coordinator (if parent)
├── __init__.py     # Package exports
└── tests/          # Module-specific tests
```

## Key Components

### **Analysis Engine (IFD v3.0)**
- Institutional Flow Detection version 3.0
- Real-time market analysis
- Signal generation and validation
- Performance tracking and optimization

### **Data Ingestion Pipeline**
- Databento API for real-time market data
- Barchart web scraper as backup
- Data normalization and caching
- MBO (Market by Order) streaming support

### **Output Generation**
- JSON export for external systems
- Human-readable trading reports
- Performance metrics and analytics

## Operational Modes

### **1. PRODUCTION MODE**
- Full IFD v3.0 algorithm
- Real-time data feeds
- Live signal generation

### **2. SHADOW TRADING MODE**
- Parallel execution without orders
- Signal validation and comparison
- Performance metrics collection

### **3. TESTING MODE**
- Conservative thresholds
- Enhanced logging
- Detailed diagnostics

## Best Practices

### **DO**:
- Use integration.py modules as entry points
- Follow the hierarchical structure
- Add comprehensive tests for new features
- Update pipeline_config.json for flow changes
- Monitor performance metrics

### **DON'T**:
- Create files outside the established structure
- Bypass the integration layer
- Add untested code to production
- Modify core algorithms without shadow testing

## Current Status
- **Active System**: IFD v3.0 in production
- **Architecture**: Hierarchical Pipeline Framework
- **Phase**: Continuous improvement and monitoring
- **Testing**: Shadow trading validation active

## Core Truth
**THE HIERARCHICAL PIPELINE IS THE SYSTEM**. All components integrate through defined interfaces, data flows through configured pipelines, and shadow trading validates everything before production.
