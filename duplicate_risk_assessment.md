# Duplicate Risk Assessment Matrix

## Risk Levels
- **LOW**: Internal functions, good test coverage, no external callers
- **MEDIUM**: Used across modules, some test coverage
- **HIGH**: Public API, external dependencies, limited tests

## Identified Duplicates Risk Assessment

### 1. Exact Duplicate: __init__ methods (OutputGenerationEngine & AnalysisEngine)
- **Risk**: LOW
- **Callers**: Internal only (integration tests)
- **Test Coverage**: Both have test_integration.py
- **Action**: Safe to consolidate immediately

### 2. Similar __init__ patterns
- **Risk**: LOW-MEDIUM
- **Patterns Found**:
  - 2 args, 3 lines: OutputGenerationEngine, AnalysisEngine
  - 2 args, 12 lines: json_exporter, risk_analysis
  - 2 args, 18 lines: expected_value_analysis, tradovate_api_data
  - 2 args, 10 lines: barchart_saved_data, interactive_brokers_api
- **Action**: Can extract to base class patterns

### 3. Test setUp Methods (4 duplicates)
- **Risk**: LOW
- **Locations**:
  - expiration_pressure_calculator/test_validation.py
  - barchart_web_scraper/test_validation.py
  - real_time_options_feed/test_validation.py
  - interactive_brokers_api/test_validation.py
- **Test Coverage**: These ARE the tests
- **Action**: Create test base class

### 4. Utility Methods (from baseline scan)
- **save_evidence**: Already deduplicated ✓
- **estimate_underlying_price**: Already deduplicated ✓
- **get_eod_contract_symbol**: Already deduplicated ✓

## Priority Order for Safe Deduplication

1. **Immediate (LOW risk)**:
   - Exact __init__ duplicates in integration classes
   - Test setUp methods
   - Internal utility functions with no external callers

2. **Next Phase (MEDIUM risk)**:
   - Similar __init__ patterns (parameterize differences)
   - Cross-module utilities (create shared modules)
   - Data validation patterns

3. **Careful Review (HIGH risk)**:
   - Public API methods
   - Methods called by external systems
   - Core business logic with complex dependencies

## Validation Strategy
- Run affected tests after each removal
- Check import dependencies with grep
- Verify no external projects depend on removed functions