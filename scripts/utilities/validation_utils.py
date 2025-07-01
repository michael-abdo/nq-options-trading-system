#!/usr/bin/env python3
"""
Centralized Validation Utilities
Consolidates all validation logic from across the codebase
"""

import re
import logging
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

# Import canonical month codes
sys.path.append(str(Path(__file__).parent.parent.parent / "tasks/options_trading_system/data_ingestion/barchart_web_scraper"))
from symbol_generator import MONTH_CODES

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation failures"""
    pass


class ContractValidator:
    """Validates options contract data"""
    
    @staticmethod
    def validate_required_fields(contract: Dict[str, Any], 
                               required_fields: Optional[List[str]] = None) -> Tuple[bool, str]:
        """Validate contract has all required fields"""
        if required_fields is None:
            # Standard required fields for options contracts
            required_fields = ["strike", "type", "last", "bid", "ask"]
        
        missing_fields = []
        for field in required_fields:
            if field not in contract or contract[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        return True, "All required fields present"
    
    @staticmethod
    def validate_price_sanity(contract: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate prices are within reasonable bounds"""
        try:
            strike = float(contract.get("strike", 0))
            if strike <= 0:
                return False, f"Invalid strike price: {strike}"
            
            # Check bid/ask spread
            bid = contract.get("bid")
            ask = contract.get("ask")
            if bid is not None and ask is not None:
                if float(bid) > float(ask):
                    return False, f"Bid ({bid}) exceeds ask ({ask})"
            
            # Check that prices are non-negative
            for field in ["last", "bid", "ask", "premium"]:
                value = contract.get(field)
                if value is not None and float(value) < 0:
                    return False, f"Negative {field} price: {value}"
            
            return True, "Price validation passed"
            
        except (ValueError, TypeError) as e:
            return False, f"Price validation error: {str(e)}"
    
    @staticmethod
    def validate_contract_count(data: Dict[str, Any], 
                              min_contracts: int = 1, 
                              max_contracts: int = 10000) -> Tuple[bool, str]:
        """Validate total contract count is within expected range"""
        total = data.get("total", 0)
        
        if total < min_contracts:
            return False, f"Too few contracts: {total} < {min_contracts}"
        if total > max_contracts:
            return False, f"Too many contracts: {total} > {max_contracts}"
        
        return True, f"Contract count valid: {total}"


class SymbolValidator:
    """Validates options symbols and their components"""
    
    # Use canonical month codes from symbol_generator.py
    
    @staticmethod
    def validate_symbol_format(symbol: str) -> Tuple[bool, str]:
        """Validate symbol follows expected format"""
        # Pattern: MQ6M25 = Product(MQ) + Week(6) + Month(M) + Year(25)
        pattern = r'^[A-Z]{2}\d[A-Z]\d{2}$'
        
        if not re.match(pattern, symbol):
            return False, f"Symbol {symbol} doesn't match expected format"
        
        return True, "Symbol format valid"
    
    @staticmethod
    def validate_expiry_components(symbol: str) -> Tuple[bool, str]:
        """Validate symbol expiry date components"""
        if len(symbol) < 6:
            return False, "Symbol too short"
        
        try:
            # Extract components
            product = symbol[:2]  # MQ
            week = symbol[2]      # 6
            month = symbol[3]     # M
            year = symbol[4:6]    # 25
            
            # Validate month code
            if month not in MONTH_CODES:
                return False, f"Invalid month code: {month}"
            
            # Validate week (1-5 for weekly, 6 for monthly)
            week_num = int(week)
            if week_num < 1 or week_num > 6:
                return False, f"Invalid week number: {week}"
            
            # Validate year (should be 2-digit)
            year_num = int(year)
            if year_num < 0 or year_num > 99:
                return False, f"Invalid year: {year}"
            
            return True, "Expiry components valid"
            
        except (ValueError, IndexError) as e:
            return False, f"Error parsing symbol components: {str(e)}"


class DateTimeValidator:
    """Validates date/time formats and business rules"""
    
    # Standard formats used across the codebase
    FORMATS = {
        "api": "%Y-%m-%dT%H:%M:%S",
        "filename": "%Y%m%d_%H%M%S",
        "display": "%Y-%m-%d %H:%M:%S",
        "date_only": "%Y%m%d"
    }
    
    @staticmethod
    def validate_timestamp(timestamp: str, format_type: str = "api") -> Tuple[bool, str]:
        """Validate timestamp matches expected format"""
        format_string = DateTimeValidator.FORMATS.get(format_type)
        if not format_string:
            return False, f"Unknown format type: {format_type}"
        
        try:
            datetime.strptime(timestamp, format_string)
            return True, "Timestamp valid"
        except ValueError:
            return False, f"Timestamp {timestamp} doesn't match format {format_string}"
    
    @staticmethod
    def validate_trading_day(date: datetime) -> Tuple[bool, str]:
        """Validate date is a valid trading day"""
        # Markets closed on weekends
        if date.weekday() in [5, 6]:  # Saturday, Sunday
            return False, f"Weekend date: {date.strftime('%Y-%m-%d')}"
        
        # TODO: Add holiday calendar check
        
        return True, "Valid trading day"


class DataStructureValidator:
    """Validates data structure integrity"""
    
    @staticmethod
    def validate_api_response(data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate API response structure"""
        required_keys = ["success", "data", "total"]
        
        # Check top-level structure
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            return False, f"Missing required keys: {', '.join(missing_keys)}"
        
        # Check success flag
        if not data.get("success", False):
            return False, "API response indicates failure"
        
        # Check data structure
        if not isinstance(data.get("data"), dict):
            return False, "Data field is not a dictionary"
        
        # Check for Call/Put sections
        if "Call" not in data["data"] and "Put" not in data["data"]:
            return False, "No Call or Put data found"
        
        return True, "API response structure valid"
    
    @staticmethod
    def validate_normalized_data(data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate normalized data structure"""
        required_keys = ["symbol", "timestamp", "contracts", "summary"]
        
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            return False, f"Missing required keys: {', '.join(missing_keys)}"
        
        # Validate contracts is a list
        if not isinstance(data.get("contracts"), list):
            return False, "Contracts field is not a list"
        
        # Validate each contract
        for i, contract in enumerate(data["contracts"]):
            valid, msg = ContractValidator.validate_required_fields(contract)
            if not valid:
                return False, f"Contract {i}: {msg}"
        
        return True, "Normalized data structure valid"


# Convenience functions for backward compatibility
def validate_contract(contract: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate a single contract - backward compatible wrapper"""
    # First check required fields
    valid, msg = ContractValidator.validate_required_fields(contract)
    if not valid:
        return valid, msg
    
    # Then check price sanity
    return ContractValidator.validate_price_sanity(contract)


def validate_symbol(symbol: str) -> Tuple[bool, str]:
    """Validate symbol format and components - backward compatible wrapper"""
    # First check format
    valid, msg = SymbolValidator.validate_symbol_format(symbol)
    if not valid:
        return valid, msg
    
    # Then check components
    return SymbolValidator.validate_expiry_components(symbol)


def validate_data_structure(data: Dict[str, Any], 
                          data_type: str = "api") -> Tuple[bool, str]:
    """Validate data structure based on type - backward compatible wrapper"""
    if data_type == "api":
        return DataStructureValidator.validate_api_response(data)
    elif data_type == "normalized":
        return DataStructureValidator.validate_normalized_data(data)
    else:
        return False, f"Unknown data type: {data_type}"