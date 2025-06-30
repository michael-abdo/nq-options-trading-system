#!/usr/bin/env python3
"""
Barchart Data Validator
Validates that we're pulling correct options data by checking against known values
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

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
        """Validate symbol format and components"""
        if symbol not in self.validation_rules:
            return True, f"No validation rules for {symbol}"
        
        rules = self.validation_rules[symbol]
        
        # Check symbol format
        if symbol != rules["expected_symbol"]:
            return False, f"Symbol mismatch: expected {rules['expected_symbol']}, got {symbol}"
        
        # Check components
        if not symbol.startswith(rules["expected_prefix"]):
            return False, f"Prefix mismatch: expected {rules['expected_prefix']}, got {symbol[:2]}"
        
        if symbol[2] != rules["expected_week"]:
            return False, f"Week mismatch: expected {rules['expected_week']}, got {symbol[2]}"
        
        if symbol[3] != rules["expected_month"]:
            return False, f"Month mismatch: expected {rules['expected_month']}, got {symbol[3]}"
        
        return True, "Symbol validation passed"
    
    def validate_contract_count(self, data: Dict[str, Any], symbol: str) -> Tuple[bool, str]:
        """Validate number of contracts"""
        if symbol not in self.validation_rules:
            return True, f"No validation rules for {symbol}"
        
        rules = self.validation_rules[symbol]
        total_contracts = data.get("total", 0)
        
        if total_contracts < rules["min_contracts"]:
            return False, f"Too few contracts: expected >= {rules['min_contracts']}, got {total_contracts}"
        
        if total_contracts > rules["max_contracts"]:
            return False, f"Too many contracts: expected <= {rules['max_contracts']}, got {total_contracts}"
        
        # Check calls vs puts
        if "data" in data:
            calls = len(data["data"].get("Call", []))
            puts = len(data["data"].get("Put", []))
            
            if calls == 0 or puts == 0:
                return False, f"Missing option types: {calls} calls, {puts} puts"
            
            if abs(calls - puts) > 10:  # Should be roughly equal
                return False, f"Unbalanced options: {calls} calls vs {puts} puts"
        
        return True, f"Contract count validation passed ({total_contracts} contracts)"
    
    def validate_open_interest(self, metrics: Dict[str, Any], symbol: str) -> Tuple[bool, str]:
        """Validate open interest totals against expected values"""
        if symbol not in self.validation_rules:
            return True, f"No validation rules for {symbol}"
        
        rules = self.validation_rules[symbol]
        expected_oi = rules.get("expected_oi")
        
        if not expected_oi:
            return True, "No OI validation rules"
        
        call_oi = metrics.get("call_oi_total", 0)
        put_oi = metrics.get("put_oi_total", 0)
        tolerance = expected_oi.get("tolerance", 0.05)
        
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
        """Validate data quality and completeness"""
        issues = []
        
        if "data" not in data:
            return False, "Missing 'data' field in response"
        
        # Check for required fields
        for option_type in ["Call", "Put"]:
            if option_type not in data["data"]:
                issues.append(f"Missing {option_type} data")
                continue
            
            contracts = data["data"][option_type]
            if not contracts:
                issues.append(f"Empty {option_type} contracts")
                continue
            
            # Sample first contract for field validation
            sample = contracts[0] if contracts else {}
            required_fields = ["strike", "raw"]
            
            for field in required_fields:
                if field not in sample:
                    issues.append(f"Missing required field '{field}' in {option_type} contracts")
            
            # Check raw data fields
            if "raw" in sample:
                raw_fields = ["strike", "premium", "openInterest"]
                for field in raw_fields:
                    if field not in sample["raw"]:
                        issues.append(f"Missing raw field '{field}' in {option_type} contracts")
        
        if issues:
            return False, f"Data quality issues: {', '.join(issues)}"
        
        return True, "Data quality validation passed"
    
    def validate_api_response(self, file_path: str) -> Dict[str, Any]:
        """Validate a saved API response file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
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
            
            # Overall result
            results["valid"] = all(v["valid"] for v in results["validations"].values())
            
            return results
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Failed to validate file: {str(e)}",
                "file": file_path
            }
    
    def validate_metrics(self, metrics_file: str) -> Dict[str, Any]:
        """Validate calculated metrics against expected values"""
        try:
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)
            
            symbol = metrics.get("symbol")
            if not symbol:
                return {
                    "valid": False,
                    "error": "No symbol in metrics file",
                    "file": metrics_file
                }
            
            results = {
                "file": metrics_file,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "validations": {}
            }
            
            # Open Interest validation
            valid, msg = self.validate_open_interest(metrics, symbol)
            results["validations"]["open_interest"] = {"valid": valid, "message": msg}
            
            # Check P/C ratios are calculated
            if "put_call_premium_ratio" not in metrics:
                results["validations"]["pcr_calculation"] = {
                    "valid": False,
                    "message": "Missing put_call_premium_ratio"
                }
            else:
                pcr = metrics["put_call_premium_ratio"]
                results["validations"]["pcr_calculation"] = {
                    "valid": True,
                    "message": f"PCR calculated: {pcr:.3f}"
                }
            
            # Overall result
            results["valid"] = all(v["valid"] for v in results["validations"].values())
            
            return results
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Failed to validate metrics: {str(e)}",
                "file": metrics_file
            }
    
    def print_validation_report(self, results: Dict[str, Any]):
        """Print formatted validation report"""
        print(f"\n{'='*60}")
        print(f"📊 BARCHART DATA VALIDATION REPORT")
        print(f"{'='*60}")
        
        print(f"\nFile: {Path(results['file']).name}")
        print(f"Symbol: {results.get('symbol', 'Unknown')}")
        print(f"Valid: {'✅ YES' if results['valid'] else '❌ NO'}")
        
        if "error" in results:
            print(f"\n❌ ERROR: {results['error']}")
            return
        
        print(f"\nValidation Results:")
        for check, result in results.get("validations", {}).items():
            status = "✅" if result["valid"] else "❌"
            print(f"  {status} {check}: {result['message']}")
        
        print(f"\n{'='*60}")


def main():
    """Example usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate Barchart data')
    parser.add_argument('--api-file', help='API response file to validate')
    parser.add_argument('--metrics-file', help='Metrics file to validate')
    parser.add_argument('--latest', action='store_true', help='Validate latest files')
    
    args = parser.parse_args()
    
    validator = BarchartDataValidator()
    
    if args.latest:
        # Find latest files
        from pathlib import Path
        output_dir = Path("outputs")
        latest_date = sorted(output_dir.glob("2025*"))[-1] if output_dir.exists() else None
        
        if latest_date:
            api_files = sorted(latest_date.glob("api_data/*MQ6M25*.json"))
            metrics_files = sorted(latest_date.glob("metrics/*MQ6M25*.json"))
            
            if api_files:
                print(f"\nValidating latest API file: {api_files[-1]}")
                results = validator.validate_api_response(str(api_files[-1]))
                validator.print_validation_report(results)
            
            if metrics_files:
                print(f"\nValidating latest metrics file: {metrics_files[-1]}")
                results = validator.validate_metrics(str(metrics_files[-1]))
                validator.print_validation_report(results)
    
    elif args.api_file:
        results = validator.validate_api_response(args.api_file)
        validator.print_validation_report(results)
    
    elif args.metrics_file:
        results = validator.validate_metrics(args.metrics_file)
        validator.print_validation_report(results)
    
    else:
        print("Usage: python data_validator.py [--api-file FILE] [--metrics-file FILE] [--latest]")


if __name__ == "__main__":
    main()