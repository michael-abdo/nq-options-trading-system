#!/usr/bin/env python3
"""
Barchart Data Validator - Refactored to use centralized validation
Validates that we're pulling correct options data by checking against known values
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import sys

# Add path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
from scripts.utilities.validation_utils import (
    ContractValidator, SymbolValidator, DataStructureValidator,
    validate_symbol, validate_contract
)
from scripts.utilities.file_io_utils import FileIOUtils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BarchartDataValidator:
    """Validate Barchart options data against expected values"""
    
    def __init__(self):
        self.validation_rules = {
            "MQ6M25": {
                "expected_symbol": "MQ6M25",
                "expected_prefix": "MQ",
                "expected_month": "M",  # June
                "expected_week": "6",   # Monthly indicator
                "min_contracts": 700,   # Should have at least 700 contracts
                "max_contracts": 900,   # Upper bound for sanity check
                "expected_oi": {
                    "call_total": 8581,
                    "put_total": 12407,
                    "tolerance": 0.05  # 5% tolerance for OI changes
                }
            }
        }
    
    def validate_symbol(self, symbol: str) -> Tuple[bool, str]:
        """Validate symbol format and components - now uses centralized validation"""
        # First use the centralized validator
        valid, msg = validate_symbol(symbol)
        if not valid:
            return valid, msg
        
        # Then apply business-specific rules if we have them
        if symbol in self.validation_rules:
            rules = self.validation_rules[symbol]
            
            # Check symbol matches expected
            if symbol != rules["expected_symbol"]:
                return False, f"Symbol mismatch: expected {rules['expected_symbol']}, got {symbol}"
        
        return True, "Symbol validation passed"
    
    def validate_contract_count(self, data: Dict[str, Any], symbol: str) -> Tuple[bool, str]:
        """Validate contract counts are within expected ranges"""
        # Use centralized validator first
        if symbol in self.validation_rules:
            rules = self.validation_rules[symbol]
            valid, msg = ContractValidator.validate_contract_count(
                data, 
                min_contracts=rules["min_contracts"],
                max_contracts=rules["max_contracts"]
            )
            return valid, msg
        else:
            # Default validation
            return ContractValidator.validate_contract_count(data)
    
    def validate_open_interest(self, data: Dict[str, Any], symbol: str) -> Tuple[bool, str]:
        """Validate open interest matches expected values"""
        if symbol not in self.validation_rules:
            return True, f"No OI validation rules for {symbol}"
        
        rules = self.validation_rules[symbol]
        expected_oi = rules.get("expected_oi", {})
        tolerance = expected_oi.get("tolerance", 0.05)
        
        # Calculate actual OI
        call_oi = 0
        put_oi = 0
        
        if "data" in data and isinstance(data["data"], dict):
            # Sum up OI for calls
            for contract in data["data"].get("Call", []):
                if "raw" in contract and "openInterest" in contract["raw"]:
                    oi = contract["raw"]["openInterest"]
                    if oi is not None:
                        call_oi += oi
            
            # Sum up OI for puts
            for contract in data["data"].get("Put", []):
                if "raw" in contract and "openInterest" in contract["raw"]:
                    oi = contract["raw"]["openInterest"]
                    if oi is not None:
                        put_oi += oi
        
        # Check call OI
        expected_call = expected_oi["call_total"]
        call_diff = abs(call_oi - expected_call) / expected_call
        if call_diff > tolerance:
            return False, f"Call OI mismatch: expected ~{expected_call}, got {call_oi} ({call_diff:.1%} diff)"
        
        # Check put OI
        expected_put = expected_oi["put_total"]
        put_diff = abs(put_oi - expected_put) / expected_put
        if put_diff > tolerance:
            return False, f"Put OI mismatch: expected ~{expected_put}, got {put_oi} ({put_diff:.1%} diff)"
        
        # Check P/C ratio
        actual_ratio = put_oi / call_oi if call_oi > 0 else 0
        expected_ratio = expected_put / expected_call
        ratio_diff = abs(actual_ratio - expected_ratio)
        
        if ratio_diff > 0.1:  # 0.1 tolerance for ratio
            return False, f"P/C ratio mismatch: expected ~{expected_ratio:.2f}, got {actual_ratio:.2f}"
        
        return True, f"OI validation passed (Call: {call_oi}, Put: {put_oi}, Ratio: {actual_ratio:.2f})"
    
    def validate_data_quality(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate data quality and completeness - now uses centralized validation"""
        # Use centralized API response validator
        valid, msg = DataStructureValidator.validate_api_response(data)
        if not valid:
            return valid, msg
        
        # Additional quality checks specific to our use case
        issues = []
        
        # Check raw data fields
        for option_type in ["Call", "Put"]:
            contracts = data["data"].get(option_type, [])
            if contracts:
                sample = contracts[0]
                if "raw" in sample:
                    raw_fields = ["strike", "premium", "openInterest"]
                    for field in raw_fields:
                        if field not in sample["raw"]:
                            issues.append(f"Missing raw field '{field}' in {option_type} contracts")
        
        if issues:
            return False, f"Additional data quality issues: {', '.join(issues)}"
        
        return True, "Data quality validation passed"
    
    def validate_api_response(self, file_path: str) -> Dict[str, Any]:
        """Validate a saved API response file"""
        try:
            data = FileIOUtils.load_json(file_path)
            
            # Extract symbol from filename
            filename = Path(file_path).stem
            parts = filename.split('_')
            symbol = None
            for part in parts:
                if part.startswith('M') and len(part) == 6:  # Matches MQ6M25 format
                    symbol = part
                    break
            
            if not symbol:
                return {
                    "valid": False,
                    "error": "Could not extract symbol from filename",
                    "file": file_path
                }
            
            # Run validations
            results = {
                "file": file_path,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "validations": {}
            }
            
            # Symbol validation
            valid, msg = self.validate_symbol(symbol)
            results["validations"]["symbol"] = {"valid": valid, "message": msg}
            
            # Contract count validation
            valid, msg = self.validate_contract_count(data, symbol)
            results["validations"]["contract_count"] = {"valid": valid, "message": msg}
            
            # Data quality validation
            valid, msg = self.validate_data_quality(data)
            results["validations"]["data_quality"] = {"valid": valid, "message": msg}
            
            # Open interest validation
            valid, msg = self.validate_open_interest(data, symbol)
            results["validations"]["open_interest"] = {"valid": valid, "message": msg}
            
            # Overall result
            all_valid = all(v["valid"] for v in results["validations"].values())
            results["valid"] = all_valid
            
            return results
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Error processing file: {str(e)}",
                "file": file_path
            }