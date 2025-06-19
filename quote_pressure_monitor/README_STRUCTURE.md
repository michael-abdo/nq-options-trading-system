# Quote Pressure Monitor - Organized Structure

## 📁 Directory Organization

### `/core/` - Main Implementation Files
- `enhanced_quote_pressure_monitor.py` - **BREAKTHROUGH** implementation with real symbol mapping
- `nq_options_quote_pressure_with_ifd.py` - Full IFD v3 integrated version  
- `quote_pressure_adapter.py` - Adapter for IFD v3 integration
- `ifd_integration.py` - Integration pipeline demonstration

### `/tests/` - Testing & Validation
- `test_adapter.py` - Tests for the quote pressure adapter
- `test_connection.py` - Basic connection testing
- `test_historical_quote_pressure.py` - Historical data validation
- `test_working_symbol_approach.py` - Working symbol resolution method

### `/docs/` - Documentation
- `README.md` - Main documentation
- `BREAKTHROUGH_SYMBOL_MAPPING_SOLUTION.md` - Symbol mapping breakthrough
- `EXHAUSTIVE_OPTIONS_TESTING_REPORT.md` - Comprehensive testing results
- `ADAPTER_README.md` - Adapter documentation
- `GOLDEN_QUOTE_PRESSURE_ADAPTER_SOLUTION.md` - Golden solution documentation
- `SUCCESSFUL_DATA_PROCESSING_METHOD.md` - Successful processing methods

### `/backtesting/` - Analysis & Validation
- Complete 122-day backtesting system
- Progress tracking and results
- Multiple backtesting approaches and optimizations

### `/archive/` - Legacy Files
- `legacy_versions/` - Older implementation versions preserved for reference

### Root Level Scripts
- `run_monitor.sh` - Shell script to run the quote pressure monitor
- `run_monitor_with_ifd.sh` - Shell script to run with IFD integration

## 🚀 Quick Start

**Run Enhanced Monitor:**
```bash
./run_monitor.sh
```

**Run with IFD Integration:**
```bash
./run_monitor_with_ifd.sh
```

**Run Specific Version:**
```bash
cd core/
python3 enhanced_quote_pressure_monitor.py
```

## 🧪 Testing

```bash
cd tests/
python3 test_adapter.py
python3 test_connection.py
```

This organization separates concerns while maintaining easy access to all components of the quote pressure monitoring system.