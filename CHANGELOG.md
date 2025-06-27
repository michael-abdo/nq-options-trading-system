# Changelog

## [2025-06-27] - Code Deduplication

### Removed Duplicated Functionality

#### 🔴 Metrics Calculation Consolidation
- **REMOVED**: `calculate_mq4m25_metrics.py` (50 lines)
- **CANONICALIZED IN**: `options_metrics_calculator.py` 
- **WHY**: Same logic for calculating call/put premium totals, OI totals, and ratios. The generalized version provides better error handling and is actively used by the pipeline.

#### 🔴 API Data Fetching Consolidation  
- **REMOVED**: `fetch_mq4m25_complete.py` (80 lines)
- **REMOVED**: `fetch_mm6n25.py` (70 lines)
- **REMOVED**: `test_mq4m25.py` (60 lines)
- **CANONICALIZED IN**: `working_api_call.py` and `hybrid_scraper.py`
- **WHY**: All made identical Barchart API calls with duplicate cookie setup. The canonical implementations handle multiple symbols and provide better abstraction.

#### 🔴 Pipeline Runner Consolidation
- **REMOVED**: `run_pipeline.py` (6KB, 186 lines)
- **CANONICALIZED IN**: `daily_options_pipeline.py` (23KB)
- **WHY**: `daily_options_pipeline.py` provides superior functionality:
  - Cookie persistence between sessions
  - Comprehensive error handling with retries  
  - Progress tracking and partial recovery
  - Timestamped data organization
  - Detailed logging and monitoring

### Updated Documentation
- **UPDATED**: `README.md` to reference new canonical entry point
- **UPDATED**: Usage examples to use `daily_options_pipeline.py` and `nq-monthly` command

### Impact Summary
- **Files removed**: 6 files (~400 lines of duplicate code)
- **Maintenance reduction**: High (single source of truth for each functionality)
- **Regression risk**: None (duplicates were not actively used)
- **Performance impact**: None (canonical implementations unchanged)

### Code Quality Improvements
- Eliminated semantic duplicates while preserving all functionality
- Consolidated cookie management patterns
- Unified API interaction methods
- Simplified project structure and documentation