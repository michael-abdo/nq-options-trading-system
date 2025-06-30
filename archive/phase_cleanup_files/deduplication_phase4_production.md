# Deduplication Plan: phase-4-production-deployment Branch

## Branch Overview
- **Total functions**: 1,191
- **Duplicate functions**: 465 (39%)
- **Estimated duplicate lines**: 13,041
- **Priority**: CRITICAL (Production branch)

## Pre-Deduplication Validation

### 1. Create branch backup
```bash
git checkout phase-4-production-deployment
git tag backup-phase4-$(date +%Y%m%d-%H%M%S)
git push origin --tags
```

### 2. Run existing tests and save baseline
```bash
# Save current test results
pytest > tests/baseline_phase4_$(date +%Y%m%d).txt 2>&1
python daily_options_pipeline.py --dry-run > tests/baseline_output_$(date +%Y%m%d).txt
```

### 3. Analyze specific duplicates
```bash
python analyze_branch_duplicates.py --branch phase-4-production-deployment --detailed
```

## Duplicate Groups to Address

### Group 1: Symbol Generation (5 variants, ~650 lines)

**Current duplicates:**
1. `BarchartAPIComparator.get_eod_contract_symbol()` 
2. `generate_barchart_symbol()` in utils/
3. `create_option_symbol()` in helpers/
4. `build_eod_symbol()` in scrapers/
5. `format_contract_symbol()` in api/

**Action:**
```python
# STEP 1: Verify all produce same output
# Create test_symbol_consolidation.py
def test_all_symbol_generators_match():
    test_cases = [
        ("NQ", "weekly", "2digit"),
        ("NQ", "monthly", "2digit"),
        ("NQ", "friday", "2digit"),
    ]
    
    for base, opt_type, year_fmt in test_cases:
        results = []
        # Call each variant and collect results
        results.append(comparator.get_eod_contract_symbol(base, opt_type, year_fmt))
        results.append(generate_barchart_symbol(base, opt_type, year_fmt))
        results.append(create_option_symbol(base, opt_type, year_fmt))
        # ... etc
        
        # All should match
        assert len(set(results)) == 1, f"Mismatch for {base}, {opt_type}: {results}"

# STEP 2: Replace all with canonical implementation
# Use symbol_generator.BarchartSymbolGenerator
```

**Commits:**
```bash
git commit -m "REMOVE duplicate generate_barchart_symbol from utils → canonicalized in symbol_generator.py"
git commit -m "REMOVE duplicate create_option_symbol from helpers → canonicalized in symbol_generator.py"
# ... one commit per removal
```

### Group 2: File I/O Operations (8 variants, ~400 lines)

**Current duplicates:**
1. `save_json()` / `load_json()` in utils/io.py
2. `write_data()` / `read_data()` in helpers/files.py
3. `save_results()` in analysis/
4. `persist_data()` in storage/
5. Various inline json.dump/load calls

**Action:**
```python
# STEP 1: Create migration script
# migrate_file_io.py
import ast
import os

def find_file_io_patterns(directory):
    patterns = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                # Parse and find json operations
                # Track location and usage
    return patterns

# STEP 2: Replace systematically
from scripts.utilities.file_io_utils import FileIOUtils

# Replace all variants with:
FileIOUtils.save_json(data, filepath)
FileIOUtils.load_json(filepath)
```

### Group 3: API Authentication (4 variants, ~300 lines)

**Current duplicates:**
1. `get_barchart_cookies()` in auth/
2. `authenticate_session()` in api/
3. `setup_credentials()` in scrapers/
4. `load_auth_cookies()` in utils/

**Action:**
```python
# Create canonical auth module
# scripts/utilities/auth_utils.py
class AuthenticationManager:
    def __init__(self):
        self.cookie_manager = CookieManager()
    
    def get_barchart_session(self):
        """Single method for all Barchart auth needs"""
        # Consolidate all auth logic here
```

### Group 4: Metrics Calculation (12 variants, ~2,400 lines)

**Current duplicates:**
- Various `calculate_*` functions with similar patterns
- Pressure calculations
- EV calculations
- Risk metrics

**Action:**
```python
# Create scripts/utilities/calculation_utils.py
class MetricsCalculator:
    """Consolidated metrics calculation"""
    
    @staticmethod
    def calculate_pressure(data, method='standard'):
        # Unified pressure calculation
    
    @staticmethod
    def calculate_expected_value(strikes, probabilities):
        # Unified EV calculation
    
    @staticmethod
    def calculate_risk_metrics(positions):
        # Unified risk calculation
```

## Validation After Each Group

### After Symbol Generation:
```bash
pytest tests/test_symbol_* -v
python daily_options_pipeline.py --dry-run | diff tests/baseline_output_*.txt -
```

### After File I/O:
```bash
pytest tests/test_file_io_* -v
# Verify all files are created in same locations with same content
find outputs/ -name "*.json" -exec md5sum {} \; > file_checksums_new.txt
diff file_checksums_old.txt file_checksums_new.txt
```

### After Auth:
```bash
# Test API connectivity
python -c "from scripts.utilities.auth_utils import AuthenticationManager; 
          am = AuthenticationManager(); 
          session = am.get_barchart_session(); 
          print('Auth successful' if session else 'Auth failed')"
```

### After Metrics:
```bash
# Run calculation regression tests
pytest tests/test_calculations_* -v
python tests/verify_metric_outputs.py
```

## Rollback Plan

If any step fails:
```bash
# Rollback to backup
git reset --hard backup-phase4-<timestamp>

# Or selectively revert
git revert <commit-hash>
```

## Success Criteria

- [ ] All 465 duplicate functions removed
- [ ] Zero test failures
- [ ] Output files identical (byte-for-byte)
- [ ] Performance same or better
- [ ] Code coverage increased

## Timeline

- **Day 1**: Symbol generation consolidation
- **Day 2**: File I/O consolidation  
- **Day 3**: Auth consolidation
- **Day 4**: Metrics consolidation (part 1)
- **Day 5**: Metrics consolidation (part 2)
- **Day 6**: Integration testing
- **Day 7**: Documentation and merge

## Final Validation

```bash
# Run full regression suite
pytest --cov=. --cov-report=term-missing

# Compare with baseline
python compare_outputs.py tests/baseline_output_*.txt current_output.txt

# Performance check
python -m cProfile daily_options_pipeline.py > profile_after.txt
```

---

*Estimated completion: 1 week*
*Risk level: Medium (with proper validation)*
*Savings: ~13,000 lines of code*