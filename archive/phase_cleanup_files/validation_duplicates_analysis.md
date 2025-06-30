# Duplicate Validation Functions Analysis

## Summary

After searching through the codebase, I've identified several categories of validation functions with semantic duplicates across multiple modules.

## 1. Contract Validation (Price Ranges, Strikes, etc.)

### Found in `data_validator.py`:
- `validate_contract_count()` - Validates number of contracts and calls vs puts balance
- `validate_open_interest()` - Validates OI totals against expected values
- `validate_data_quality()` - Validates contract data has required fields

### Found in `screenshot_validator.py`:
- `_extract_page_data()` - Validates contract count from webpage (duplicate logic)
- `validate_with_screenshot()` - Compares contract counts between API and screenshot

### Found in `risk_analysis/solution.py`:
- Inline validation in `analyze_risk()` that checks if contracts exist and have required fields
- `calculate_danger_score()` - Validates price distances (similar to strike range validation)

**Duplication Pattern**: Multiple files validate contract counts and check if contracts have required fields, but with different implementations.

## 2. Data Structure Validation (Required Fields)

### Found in `data_validator.py`:
```python
required_fields = ["strike", "raw"]
raw_fields = ["strike", "premium", "openInterest"]
```

### Found in `data_normalizer/test_validation.py`:
```python
required_fields = [
    'source', 'type', 'symbol', 'strike', 'expiration',
    'volume', 'open_interest', 'last_price', 'timestamp'
]
```

### Found in `options_data_models.py`:
- Uses dataclasses with Optional fields, implicitly defining required vs optional fields
- No explicit validation, relies on type hints

**Duplication Pattern**: Different modules define different sets of "required fields" with no centralized validation.

## 3. Symbol Validation

### Found in `data_validator.py`:
- `validate_symbol()` - Validates symbol format and components (prefix, week, month)

### Found in `robust_symbol_validator.py`:
- `validate_symbol_rules()` - Comprehensive symbol validation with business rules
- `generate_symbol_for_date()` - Symbol generation with implicit validation

### Found in `parsing_utils.py`:
- No direct symbol validation, but has parsing functions that implicitly validate

**Duplication Pattern**: Symbol validation logic is spread across multiple files with different rule sets.

## 4. Date/Time Validation

### Found in `robust_symbol_validator.py`:
- `validate_symbol_rules()` - Validates expiry dates (Tuesday for weekly, Friday for friday options, etc.)
- Checks if expiry date is in the future

### Found in `daily_options_pipeline.py`:
- Uses datetime formatting but no explicit validation
- `datetime.now().strftime('%Y%m%d')` pattern repeated

### No centralized date validation found - each module handles dates differently

## 5. Price/Value Validation

### Found in `parsing_utils.py`:
- `parse_price()` - Parses and implicitly validates prices
- `is_valid_price()` - Explicit price validation
- `parse_strike()` - Strike price parsing with validation

### Found in `data_validator.py`:
- Validates premium values in `validate_open_interest()`
- No centralized price validation

### Found in `risk_analysis/solution.py`:
- Calculates risk amounts but doesn't validate price ranges

**Duplication Pattern**: Price parsing and validation is duplicated with slight variations.

## Semantic Duplicates Identified

1. **Contract Count Validation**
   - `data_validator.validate_contract_count()`
   - `screenshot_validator._extract_page_data()` 
   - Inline checks in multiple test files

2. **Required Fields Validation**
   - `data_validator.validate_data_quality()`
   - `data_normalizer/test_validation.py` contract format check
   - Implicit validation in dataclasses

3. **Symbol Format Validation**
   - `data_validator.validate_symbol()`
   - `robust_symbol_validator.validate_symbol_rules()`
   - Inline symbol checks in various modules

4. **Price Parsing and Validation**
   - `parsing_utils.parse_price()`
   - `parsing_utils.is_valid_price()`
   - Inline price checks scattered throughout

5. **Date/Expiry Validation**
   - `robust_symbol_validator.validate_symbol_rules()` expiry checks
   - No centralized date validation
   - Different date format handling in each module

## Recommendations

1. **Create a centralized validation module** (`validation_utils.py`) that consolidates:
   - Contract validation (counts, required fields, types)
   - Symbol validation (format, components, business rules)
   - Price validation (ranges, formats, nulls)
   - Date validation (formats, expiry rules, business days)

2. **Standardize validation approaches**:
   - Use consistent return types (Tuple[bool, str] vs Dict vs exceptions)
   - Define clear validation levels (strict vs lenient)
   - Create validation schemas for different data types

3. **Remove inline validation** and replace with calls to centralized validators

4. **Use data classes with validators** for automatic validation on instantiation

5. **Create validation decorators** for common patterns like required fields