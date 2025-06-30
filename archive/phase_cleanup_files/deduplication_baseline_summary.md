# Deduplication Baseline Metrics

**Date**: 2025-06-29
**Total Functions Analyzed**: 408

## Current Duplication Status

### Exact Duplicates
- **Groups**: 1
- **Functions**: 2 (OutputGenerationEngine.__init__ and AnalysisEngine.__init__)

### Semantic Duplicates
- **Groups**: 79
- **Estimated duplicate functions**: ~200-250 (average 2-5 per group)

### Name Pattern Duplicates
- **Groups**: 28
- **Common patterns**: get_, set_, test_, validate_, check_

## High-Priority Targets

1. **Identical __init__ methods** in integration classes
2. **Test utility functions** (setUp, assertions, mocks)
3. **Data validation patterns** (validate_file_exists, check_data_quality)
4. **Configuration handlers** (load_config, save_config patterns)
5. **Error handling patterns** (try/except blocks with similar structure)

## Estimated Savings Potential
- **Lines of code**: ~1,500-2,000
- **Maintenance reduction**: 30-40% in affected modules
- **Test coverage improvement**: Consolidation will improve coverage focus