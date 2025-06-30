# Branch-Specific Deduplication Strategy

## Overview
Based on comprehensive analysis of 18 branches, we've identified **significant duplication** across the codebase:
- **Total duplicate functions**: ~7,500
- **Total duplicate lines**: ~140,000+ lines
- **Average duplication rate**: 35-40% per branch

## Priority Branches for Deduplication

### 1. 🔴 **phase-4-production-deployment** (Highest Impact)
- **Duplicate lines**: 13,041
- **Duplicate functions**: 465
- **Why prioritize**: Production branch with highest duplication
- **Key duplicates**:
  - Symbol generation logic (5 variants)
  - File I/O operations (8 variants)
  - API authentication (4 variants)
  - Metrics calculation (12 variants)

### 2. 🟠 **Initial-Live-Trading-Phase** 
- **Duplicate lines**: 14,943
- **Duplicate functions**: 564
- **Why prioritize**: Active trading branch with critical duplicates
- **Key duplicates**:
  - Options pricing calculations (7 variants)
  - Risk assessment logic (6 variants)
  - Order execution code (4 variants)

### 3. 🟡 **main**
- **Duplicate lines**: 12,489
- **Duplicate functions**: 577
- **Why prioritize**: Primary branch - all changes eventually merge here
- **Key duplicates**:
  - Data validation functions (9 variants)
  - Configuration loading (5 variants)
  - Logging utilities (6 variants)

### 4. 🟢 **pure-barchart-system** (Current Branch)
- **Duplicate lines**: 6,130
- **Duplicate functions**: 134
- **Status**: Already deduplicated significantly
- **Remaining work**: Integration with other branches

### 5. 🔵 **databento-test**
- **Duplicate lines**: 6,080
- **Duplicate functions**: 127
- **Key duplicates**:
  - Market data parsing (5 variants)
  - Time series operations (4 variants)

## Common Duplicate Patterns Across All Branches

### 1. **Calculation Functions** (153 instances, ~3,900 lines)
```python
# Pattern found in:
- calculate_pressure_metrics()
- calculate_notional_value()
- calculate_ev_combinations()
- _calculate_baseline_stats()
```

### 2. **File I/O Operations** (87 instances, ~2,200 lines)
```python
# Pattern found in:
- save_json() / load_json() variants
- save_data() / load_data() variants
- write_results() / read_results() variants
```

### 3. **Validation Functions** (74 instances, ~1,850 lines)
```python
# Pattern found in:
- validate_symbol()
- validate_data()
- check_integrity()
```

### 4. **Data Fetching** (66 instances, ~1,650 lines)
```python
# Pattern found in:
- fetch_options_data()
- get_market_data()
- retrieve_prices()
```

## Strategic Deduplication Approach

### Phase 1: Create Core Utilities (Week 1)
1. **Extend existing utilities** from pure-barchart-system:
   - `file_io_utils.py` - Already created
   - `options_data_models.py` - Already created
   - `symbol_generator.py` - Already created

2. **Add new core utilities**:
   - `calculation_utils.py` - Consolidate all calculation functions
   - `validation_utils.py` - Centralize validation logic
   - `data_fetcher.py` - Unified data fetching interface

### Phase 2: Branch-by-Branch Deduplication (Weeks 2-3)

#### Week 2: Production-Critical Branches
1. **phase-4-production-deployment**
   - Replace 465 duplicate functions
   - Test thoroughly in staging
   - Validate with existing test suite

2. **Initial-Live-Trading-Phase**
   - Focus on trading-critical functions
   - Ensure no regression in order execution
   - Validate calculations match exactly

#### Week 3: Main and Supporting Branches
3. **main**
   - Merge utilities from pure-barchart-system
   - Update all references
   - Run full regression suite

4. **databento-test**
   - Update data parsing to use common models
   - Consolidate time series operations

### Phase 3: Cross-Branch Integration (Week 4)
1. Create unified test suite
2. Document migration guide
3. Update CI/CD pipelines

## Validation Strategy

### For Each Branch:
1. **Inventory Phase**
   ```bash
   git checkout <branch>
   python analyze_branch_duplicates.py --single-branch
   ```

2. **Test Coverage Check**
   ```bash
   pytest --cov=. --cov-report=html
   ```

3. **Replace & Validate**
   - Replace one duplicate group at a time
   - Run tests after each replacement
   - Compare outputs with original

4. **Commit Pattern**
   ```bash
   git commit -m "REMOVE duplicate <function> from <file> → canonicalized in <utils>"
   ```

## Expected Outcomes

### Immediate Benefits:
- **Code reduction**: ~140,000 lines removed
- **Maintenance**: Single source of truth for each function
- **Performance**: Reduced memory footprint
- **Quality**: Easier to fix bugs (fix once, not 10 times)

### Long-term Benefits:
- **Development velocity**: Faster feature development
- **Onboarding**: Easier for new developers
- **Testing**: Comprehensive test coverage
- **Reliability**: Consistent behavior across branches

## Risk Mitigation

1. **Gradual rollout**: One branch at a time
2. **Extensive testing**: Unit + integration + regression
3. **Rollback plan**: Tag before each major change
4. **Communication**: Document all changes in CHANGELOG.md

## Success Metrics

- [ ] 90%+ reduction in duplicate functions
- [ ] All tests passing on all branches
- [ ] No performance regression
- [ ] Improved code coverage
- [ ] Reduced build times

## Next Steps

1. Review and approve this strategy
2. Begin with phase-4-production-deployment branch
3. Create missing utility modules
4. Start systematic deduplication

---

*Generated: 2025-06-28*
*Total potential savings: ~140,000 lines of code*