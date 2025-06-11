# IFD v3.0 Analysis Engine

## Directory Structure

### Root Files (Essential)
- `integration.py` - Main integration point for all analysis strategies
- `config_manager.py` - Configuration management system
- `pipeline_config.json` - Main pipeline configuration
- `evidence_rollup.json` - Aggregated evidence from all child tasks

### Organized Subdirectories

#### `/config/`
Configuration profiles and settings
- `profiles/` - Various configuration profiles for different trading modes

#### `/docs/`
Documentation and implementation summaries
- `IFD_v3_COMPLETE_IMPLEMENTATION_OVERVIEW.md` - Complete implementation overview
- `PHASE4_COMPLETION_SUMMARY.md` - Phase 4 completion summary
- `phase3_final_comparison.md` - Phase 3 vs v1.0 comparison
- `phase3_gap_analysis.md` - Gap analysis documentation

#### `/expected_value_analysis/`
Core NQ Options expected value analysis (main algorithm)
- `solution.py` - Expected value calculation engine
- `test_validation.py` - Validation tests
- `evidence.json` - Performance evidence

#### `/expiration_pressure_calculator/`
Options expiration pressure analysis
- `solution.py` - Expiration pressure calculation
- `test_validation.py` - Validation tests
- `evidence.json` - Performance evidence

#### `/institutional_flow_v3/`
IFD v3.0 institutional flow detection
- `solution.py` - IFD v3.0 detection engine
- `test_validation.py` - Validation tests
- `evidence.json` - Performance evidence

#### `/monitoring/`
Performance monitoring and dashboard systems
- `performance_dashboard.py` - Real-time performance dashboard
- `performance_tracker.py` - Performance metrics tracking

#### `/outputs/`
Generated outputs, results, and cached data
- `20250610/` - Daily output directory
- `ab_testing/` - A/B testing results
- `backtests/` - Backtest results
- `dashboard/` - Dashboard snapshots
- `paper_trading/` - Paper trading results
- `performance_tracking/` - Performance metrics
- `production_logs/` - Production logs
- `rollback/` - Rollback state snapshots
- `rollout/` - Rollout events and logs
- `transition/` - Transition logs
- `ifd_v3_baselines.db` - Historical baseline database
- Phase 4 validation reports and results

#### `/phase4/`
Phase 4 Production Deployment components
- `success_metrics_tracker.py` - Success metrics tracking (accuracy >75%, cost <$5, ROI >25%)
- `websocket_backfill_manager.py` - Automatic backfill after WebSocket disconnection
- `monthly_budget_dashboard.py` - Budget visualization ($150-200 monthly target)
- `adaptive_threshold_manager.py` - ML-based threshold optimization
- `staged_rollout_framework.py` - A/B testing and staged rollout
- `historical_download_cost_tracker.py` - One-time download cost tracking
- `latency_monitor.py` - <100ms latency monitoring
- `uptime_monitor.py` - 99.9% uptime SLA monitoring
- `adaptive_integration.py` - Adaptive integration engine

#### `/pipeline/`
Pipeline components and orchestration
- `opportunity.py` - Trading opportunity detection

#### `/risk_analysis/`
Risk assessment and management
- `solution.py` - Risk analysis engine
- `test_validation.py` - Validation tests
- `evidence.json` - Performance evidence

#### `/strategies/`
Trading strategies and coordination systems
- `ab_testing_coordinator.py` - A/B testing coordination
- `call_put_coordination_detector.py` - Call/put coordination detection
- `cost_analyzer.py` - Cost analysis and optimization
- `emergency_rollback_system.py` - Emergency rollback system
- `gradual_transition_manager.py` - Gradual transition management
- `historical_backtester.py` - Historical backtesting engine
- `market_making_filter.py` - Market maker activity filter
- `paper_trading_executor.py` - Paper trading execution
- `production_error_handler.py` - Production error handling
- `production_rollout_strategy.py` - Production rollout strategy
- `volatility_crush_detector.py` - Volatility crush detection

#### `/tests/`
Test suites and validation scripts
- `extended_test_runner.py` - Extended test suite runner
- `phase_4_integration_test.py` - Phase 4 integration tests
- `phase_4_validation.py` - Phase 4 validation tests
- `test_fixes_validation.py` - Bug fix validation tests
- `test_gap_implementations.py` - Gap implementation tests
- `test_ifd_v3_integration.py` - IFD v3.0 integration tests
- `test_integration.py` - Main integration tests
- `test_phase3_validation.py` - Phase 3 validation tests
- `test_phase4_integration.py` - Phase 4 integration tests

#### `/volume_shock_analysis/`
Volume shock detection and analysis
- `solution.py` - Volume shock analysis engine
- `test_validation.py` - Validation tests
- `evidence.json` - Performance evidence

#### `/volume_spike_dead_simple/`
Simple volume spike detection algorithm
- `solution.py` - Dead simple volume spike detection
- `test_validation.py` - Validation tests
- `evidence.json` - Performance evidence
- `demo.py` - Demonstration script

## Implementation Status

### Phase 4 Production Deployment: ✅ COMPLETE
- **Components**: 9/9 implemented (100%)
- **Requirements**: 35/35 covered (100%)
- **Production Ready**: YES
- **Validation**: All tests passing

### Key Features
- Real-time Databento MBO streaming (GLBX.MDP3)
- Parent symbol subscription (NQ.OPT) for all strikes
- Bid/ask pressure derivation with microsecond precision
- 20-day historical baseline system with statistical metrics
- Market making pattern recognition and filtering
- Monthly budget management ($150-200 target)
- Success metrics tracking (accuracy >75%, cost <$5, ROI >25%)
- 99.9% uptime SLA monitoring
- <100ms latency requirements
- Staged rollout framework with A/B testing
- Automatic backfill after WebSocket disconnection
- ML-based adaptive threshold adjustment

### Usage
```python
from integration import AnalysisEngine
from config_manager import ConfigManager

# Initialize configuration
config_mgr = ConfigManager()
config = config_mgr.load_config('ifd_v3_production')

# Initialize analysis engine
engine = AnalysisEngine(config)

# Run analysis
results = engine.run_full_analysis(data_config)
```

## Architecture
The system follows a hierarchical task-based architecture with:
1. **Root Integration Layer**: Main coordination and configuration
2. **Analysis Strategies**: Specialized algorithms for different market conditions
3. **Phase 4 Components**: Production deployment infrastructure
4. **Monitoring Systems**: Real-time performance and cost tracking
5. **Testing Framework**: Comprehensive validation and integration tests

## Dependencies

### Core Requirements
The analysis engine is designed to run with **zero external dependencies**! It uses only Python 3.8+ standard library modules:
- `json`, `sqlite3`, `datetime`, `threading`, `logging`, `dataclasses`, `enum`, `collections`, `statistics`, `pathlib`

### Optional Dependencies (Enhanced Features)
While the system works perfectly without any external packages, optional dependencies can enhance functionality:

```bash
# Check which optional dependencies are installed
python scripts/check_dependencies.py

# Install all optional dependencies for enhanced features
pip install -r requirements/phase4.txt
```

#### Optional Packages:
- **pandas** (≥1.3.0) - Enhanced data analysis and DataFrame operations
  - *Fallback: Basic dict/list operations*
- **matplotlib** (≥3.4.0) - Visual dashboards and charts
  - *Fallback: Text-based logging*
- **scipy** (≥1.7.0) - Statistical significance testing for A/B tests
  - *Fallback: Basic statistical calculations*
- **scikit-learn** (≥0.24.0) - ML-based adaptive threshold optimization
  - *Fallback: Rule-based threshold adjustments*
- **numpy** (≥1.20.0) - Fast numerical computations
  - *Fallback: Python built-in math*
- **pytz** (≥2021.1) - Timezone handling for market hours
  - *Fallback: Basic UTC operations*

### Installation Options

```bash
# Option 1: Minimal installation (no dependencies)
# Just run the code - it works out of the box!

# Option 2: Full features
pip install -r requirements/phase4.txt

# Option 3: Selective installation
pip install pandas matplotlib  # Just what you need
```

**Note**: All Phase 4 components include intelligent fallbacks. The system maintains full functionality even without optional dependencies, making it extremely robust and deployment-friendly.