# Analysis Engine Directory Structure

## Optimized Organization (Phase 4 Complete)

### Root Directory
Only essential integration and configuration files remain in root:
- `integration.py` - Main integration point for all analysis strategies
- `config_manager.py` - Configuration management system  
- `pipeline_config.json` - Pipeline configuration
- `evidence_rollup.json` - Aggregated evidence from all tasks

### Directory Structure

```
analysis_engine/
├── config/                     # Configuration files
│   └── profiles/              # Trading profiles (production, testing, etc.)
├── docs/                      # Documentation
│   ├── IFD_v3_COMPLETE_IMPLEMENTATION_OVERVIEW.md
│   ├── PHASE4_COMPLETION_SUMMARY.md
│   └── ...
├── examples/                  # Demo and example scripts ✨NEW
│   └── volume_spike_demo.py
├── expected_value_analysis/   # Core NQ Options EV algorithm
│   ├── __init__.py
│   ├── solution.py
│   ├── test_validation.py
│   └── evidence.json
├── expiration_pressure_calculator/  # Expiration pressure analysis
│   ├── __init__.py
│   ├── solution.py
│   ├── test_validation.py
│   └── evidence.json
├── institutional_flow_v3/     # IFD v3.0 detection
│   ├── __init__.py
│   ├── solution.py
│   ├── test_validation.py
│   └── evidence.json
├── monitoring/                # Performance monitoring
│   ├── __init__.py
│   ├── performance_dashboard.py
│   └── performance_tracker.py
├── outputs/                   # Generated outputs and results
│   ├── 20250610/             # Daily outputs
│   ├── ab_testing/           # A/B test results
│   ├── backtests/            # Backtest results
│   ├── dashboard/            # Dashboard snapshots
│   ├── paper_trading/        # Paper trading results
│   ├── performance_tracking/ # Performance metrics
│   ├── production_logs/      # Production logs
│   ├── rollback/             # Rollback snapshots
│   ├── rollout/              # Rollout events
│   └── transition/           # Transition logs
├── phase4/                    # Phase 4 Production Components
│   ├── __init__.py
│   ├── adaptive_integration.py
│   ├── adaptive_threshold_manager.py
│   ├── historical_download_cost_tracker.py
│   ├── latency_monitor.py
│   ├── monthly_budget_dashboard.py
│   ├── staged_rollout_framework.py
│   ├── success_metrics_tracker.py
│   ├── uptime_monitor.py
│   └── websocket_backfill_manager.py
├── pipeline/                  # Pipeline components
│   ├── __init__.py
│   └── opportunity.py
├── risk_analysis/             # Risk assessment
│   ├── __init__.py
│   ├── solution.py
│   ├── test_validation.py
│   └── evidence.json
├── scripts/                   # Utility scripts ✨NEW
│   └── __init__.py
├── strategies/                # Trading strategies
│   ├── __init__.py
│   ├── ab_testing_coordinator.py
│   ├── call_put_coordination_detector.py
│   ├── cost_analyzer.py
│   ├── emergency_rollback_system.py
│   ├── gradual_transition_manager.py
│   ├── historical_backtester.py
│   ├── market_making_filter.py
│   ├── paper_trading_executor.py
│   ├── production_error_handler.py
│   ├── production_rollout_strategy.py
│   └── volatility_crush_detector.py
├── tests/                     # All test files
│   ├── __init__.py
│   ├── debug_test_expiration_pressure.py ✨MOVED
│   ├── extended_test_runner.py
│   ├── phase_4_integration_test.py
│   ├── phase_4_validation.py
│   ├── test_fixes_validation.py
│   ├── test_gap_implementations.py
│   ├── test_ifd_v3_integration.py
│   ├── test_integration.py
│   ├── test_phase3_validation.py
│   └── test_phase4_integration.py
├── volume_shock_analysis/     # Volume shock detection
│   ├── __init__.py
│   ├── solution.py
│   ├── test_validation.py
│   └── evidence.json
└── volume_spike_dead_simple/  # Simple volume spike detection
    ├── __init__.py
    ├── solution.py
    ├── test_validation.py
    ├── evidence.json
    └── enhanced_validation_results.json
```

## Key Improvements Made

1. **Python Package Structure**: Added `__init__.py` to all directories
2. **Organized Test Files**: Moved debug_test.py to tests/
3. **Created Examples Directory**: Moved demo.py to examples/
4. **Created Scripts Directory**: For future utility scripts
5. **Clean Root Directory**: Only 4 essential files remain

## Module Import Examples

```python
# Core imports
from integration import AnalysisEngine
from config_manager import ConfigManager

# Analysis module imports
from expected_value_analysis.solution import analyze_expected_value
from institutional_flow_v3.solution import create_ifd_v3_analyzer

# Strategy imports
from strategies.ab_testing_coordinator import ABTestingCoordinator
from strategies.market_making_filter import MarketMakingFilter

# Phase 4 imports
from phase4.success_metrics_tracker import SuccessMetricsTracker
from phase4.adaptive_threshold_manager import AdaptiveThresholdManager

# Monitoring imports
from monitoring.performance_tracker import PerformanceTracker
```

## Benefits of This Structure

1. **Clear Separation of Concerns**: Each directory has a specific purpose
2. **Easy Navigation**: Logical grouping makes finding files intuitive
3. **Proper Python Packages**: All directories can be imported as modules
4. **Clean Root**: Only essential integration files at top level
5. **Scalability**: Easy to add new strategies, tests, or components
6. **Maintainability**: Clear structure reduces cognitive load

This organization follows Python best practices and makes the codebase production-ready.