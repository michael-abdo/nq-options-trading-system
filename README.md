# NQ Options Trading System - Hierarchical Pipeline Framework

## Quick Start

**Single Entry Point**: `python3 run_pipeline.py`

This runs the complete Hierarchical Pipeline Analysis Framework with your actual NQ Options EV algorithm.

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
├── archive/                            # Legacy files (archived)
├── data/                               # Market data
├── docs/                               # Documentation
└── tasks/options_trading_system/       # Active pipeline framework
    ├── analysis_engine/                # Analysis modules
    ├── data_ingestion/                 # Data loading
    └── output_generation/              # Results output
```

## Configuration Strategies

The system supports multiple analysis strategies via configuration:

- **Conservative**: Risk-first filtering with strict thresholds
- **Aggressive**: EV-first filtering with broader criteria  
- **Technical**: Pattern-first filtering for technical traders
- **Scalping**: Fast execution for intraday trading

Edit `tasks/options_trading_system/analysis_engine/pipeline_config.json` to switch strategies.

## Manual Cleanup Required

**Remove these empty files manually:**
```bash
rm analyze_nearby_strikes.py analyze_strike.py fast_run.py performance_test.py 
rm quick_risk_check.py run_trading_system.py simple_run.py cleanup_old_docs.sh
rm CLEANUP_COMPLETE.md CLEANUP_STATUS.md MANUAL_CLEANUP_INSTRUCTIONS.md
rm -rf coordination/ outputs/
```

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