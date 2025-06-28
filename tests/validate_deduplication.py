#!/usr/bin/env python3
"""
Deduplication Validation Framework
Ensures functionality is preserved when removing duplicates
"""

import json
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class DeduplicationValidator:
    """Validates that deduplication preserves functionality"""
    
    def __init__(self):
        self.baseline_dir = Path("tests/dedup_baselines")
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
        
    def create_baseline(self, test_name, test_func):
        """Create baseline measurement for a test"""
        baseline_file = self.baseline_dir / f"{test_name}_baseline.json"
        
        print(f"Creating baseline for {test_name}...")
        try:
            result = test_func()
            baseline = {
                "test_name": test_name,
                "timestamp": datetime.now().isoformat(),
                "result": result,
                "hash": hashlib.md5(json.dumps(result, sort_keys=True).encode()).hexdigest()
            }
            
            with open(baseline_file, 'w') as f:
                json.dump(baseline, f, indent=2)
            
            print(f"✓ Baseline created: {baseline_file}")
            return baseline
            
        except Exception as e:
            print(f"✗ Failed to create baseline: {e}")
            return None
    
    def validate_against_baseline(self, test_name, test_func):
        """Validate current results against baseline"""
        baseline_file = self.baseline_dir / f"{test_name}_baseline.json"
        
        if not baseline_file.exists():
            print(f"No baseline found for {test_name}, creating one...")
            return self.create_baseline(test_name, test_func)
        
        # Load baseline
        with open(baseline_file, 'r') as f:
            baseline = json.load(f)
        
        # Run current test
        print(f"Validating {test_name}...")
        try:
            current_result = test_func()
            current_hash = hashlib.md5(json.dumps(current_result, sort_keys=True).encode()).hexdigest()
            
            # Compare
            if current_hash == baseline['hash']:
                print(f"✓ {test_name}: PASSED (identical to baseline)")
                self.results.append({"test": test_name, "status": "PASSED", "identical": True})
                return True
            else:
                # Check if results are semantically equivalent
                if self._are_equivalent(baseline['result'], current_result):
                    print(f"✓ {test_name}: PASSED (equivalent to baseline)")
                    self.results.append({"test": test_name, "status": "PASSED", "identical": False})
                    return True
                else:
                    print(f"✗ {test_name}: FAILED (differs from baseline)")
                    print(f"  Baseline: {baseline['result']}")
                    print(f"  Current:  {current_result}")
                    self.results.append({"test": test_name, "status": "FAILED", "identical": False})
                    return False
                    
        except Exception as e:
            print(f"✗ {test_name}: ERROR - {e}")
            self.results.append({"test": test_name, "status": "ERROR", "error": str(e)})
            return False
    
    def _are_equivalent(self, baseline, current):
        """Check if results are semantically equivalent (not just identical)"""
        # For now, just check type and length for lists
        if type(baseline) != type(current):
            return False
            
        if isinstance(baseline, list):
            return len(baseline) == len(current)
        
        # Add more sophisticated equivalence checks as needed
        return baseline == current
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.results if r['status'] == 'PASSED')
        failed = sum(1 for r in self.results if r['status'] == 'FAILED')
        errors = sum(1 for r in self.results if r['status'] == 'ERROR')
        
        print(f"Total tests: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        
        if failed > 0 or errors > 0:
            print("\nFailed/Error tests:")
            for r in self.results:
                if r['status'] in ['FAILED', 'ERROR']:
                    print(f"  - {r['test']}: {r['status']}")
        
        return failed == 0 and errors == 0


# Test functions for symbol generation
def test_symbol_generation():
    """Test all symbol generation methods produce same results"""
    results = {}
    
    # Test cases
    test_cases = [
        ("NQ", "weekly", "2digit"),
        ("NQ", "monthly", "2digit"),
        ("NQ", "friday", "2digit"),
        ("NQ", "daily", "2digit"),
    ]
    
    # Import and test BarchartSymbolGenerator
    try:
        from tasks.options_trading_system.data_ingestion.barchart_web_scraper.symbol_generator import BarchartSymbolGenerator
        sg = BarchartSymbolGenerator()
        
        results['BarchartSymbolGenerator'] = []
        for base, opt_type, year_fmt in test_cases:
            symbol = sg.get_eod_contract_symbol(base, opt_type, year_fmt)
            results['BarchartSymbolGenerator'].append({
                'input': (base, opt_type, year_fmt),
                'output': symbol
            })
    except Exception as e:
        results['BarchartSymbolGenerator'] = f"Error: {e}"
    
    # Import and test BarchartAPIComparator
    try:
        from tasks.options_trading_system.data_ingestion.barchart_web_scraper.solution import BarchartAPIComparator
        comp = BarchartAPIComparator()
        
        results['BarchartAPIComparator'] = []
        for base, opt_type, year_fmt in test_cases:
            symbol = comp.get_eod_contract_symbol(base, opt_type, year_fmt)
            results['BarchartAPIComparator'].append({
                'input': (base, opt_type, year_fmt),
                'output': symbol
            })
    except Exception as e:
        results['BarchartAPIComparator'] = f"Error: {e}"
    
    return results


def test_file_io_operations():
    """Test file I/O operations"""
    test_data = {
        "test": "deduplication",
        "number": 42,
        "list": [1, 2, 3],
        "nested": {"key": "value"}
    }
    
    results = {}
    test_file = Path("tests/dedup_test_io.json")
    
    # Test direct JSON operations
    try:
        import json
        with open(test_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        with open(test_file, 'r') as f:
            loaded = json.load(f)
        
        results['direct_json'] = {
            'save': 'success',
            'load': 'success',
            'data_intact': loaded == test_data
        }
        test_file.unlink()  # Clean up
    except Exception as e:
        results['direct_json'] = f"Error: {e}"
    
    # Test FileIOUtils if available
    try:
        from scripts.utilities.file_io_utils import FileIOUtils
        
        FileIOUtils.save_json(test_data, test_file)
        loaded = FileIOUtils.load_json(test_file)
        
        results['FileIOUtils'] = {
            'save': 'success',
            'load': 'success',
            'data_intact': loaded == test_data
        }
        test_file.unlink()  # Clean up
    except Exception as e:
        results['FileIOUtils'] = f"Error: {e}"
    
    return results


def test_calculation_functions():
    """Test calculation functions"""
    # Simple test data
    strikes = [19000, 19100, 19200]
    call_oi = [1000, 2000, 1500]
    put_oi = [1500, 1000, 2000]
    underlying = 19100
    
    results = {}
    
    # Test simple pressure calculation
    try:
        total_call = sum(call_oi)
        total_put = sum(put_oi)
        simple_pressure = (total_call - total_put) / (total_call + total_put) if (total_call + total_put) > 0 else 0
        
        results['simple_pressure'] = {
            'value': round(simple_pressure, 4),
            'total_call': total_call,
            'total_put': total_put
        }
    except Exception as e:
        results['simple_pressure'] = f"Error: {e}"
    
    # Test weighted pressure calculation
    try:
        weighted_call = sum(c * abs(s - underlying) for c, s in zip(call_oi, strikes))
        weighted_put = sum(p * abs(s - underlying) for p, s in zip(put_oi, strikes))
        weighted_pressure = (weighted_call - weighted_put) / (weighted_call + weighted_put) if (weighted_call + weighted_put) > 0 else 0
        
        results['weighted_pressure'] = {
            'value': round(weighted_pressure, 4),
            'weighted_call': weighted_call,
            'weighted_put': weighted_put
        }
    except Exception as e:
        results['weighted_pressure'] = f"Error: {e}"
    
    return results


def test_save_evidence():
    """Test save_evidence function behavior across all implementations"""
    import tempfile
    import shutil
    
    results = {}
    
    # Test data
    test_data = {
        "status": "VALIDATED",
        "tests_passed": 10,
        "tests_failed": 0,
        "timestamp": "2025-06-28T15:30:00",
        "details": {
            "test1": "passed",
            "test2": "passed"
        }
    }
    
    # Test implementations from different files
    implementations = [
        "tasks.options_trading_system.test_integration",
        "tasks.options_trading_system.output_generation.json_exporter.test_validation",
        "tasks.options_trading_system.output_generation.report_generator.test_validation",
        "tasks.options_trading_system.analysis_engine.expected_value_analysis.test_validation",
        "tasks.options_trading_system.analysis_engine.risk_analysis.test_validation",
        "tasks.options_trading_system.data_ingestion.barchart_saved_data.test_validation",
        "tasks.options_trading_system.data_ingestion.tradovate_api_data.test_validation",
        "tasks.options_trading_system.data_ingestion.data_normalizer.test_validation",
    ]
    
    for impl_path in implementations:
        try:
            # Create temp directory to isolate test
            with tempfile.TemporaryDirectory() as tmpdir:
                # Import the module
                module_parts = impl_path.split('.')
                module = __import__(impl_path, fromlist=[module_parts[-1]])
                
                # Temporarily change to temp directory
                original_dir = os.getcwd()
                os.chdir(tmpdir)
                
                # Create a mock __file__ path for the function
                module.__file__ = os.path.join(tmpdir, "test_module.py")
                
                # Call save_evidence
                module.save_evidence(test_data)
                
                # Check if evidence.json was created
                evidence_path = os.path.join(tmpdir, "evidence.json")
                if os.path.exists(evidence_path):
                    with open(evidence_path, 'r') as f:
                        saved_data = json.load(f)
                    
                    results[impl_path] = {
                        'status': 'success',
                        'file_created': True,
                        'data_matches': saved_data == test_data,
                        'file_size': os.path.getsize(evidence_path)
                    }
                else:
                    results[impl_path] = {
                        'status': 'error',
                        'file_created': False
                    }
                
                os.chdir(original_dir)
                
        except Exception as e:
            results[impl_path] = {
                'status': 'error',
                'error': str(e)
            }
    
    return results


def test_estimate_underlying_price():
    """Test _estimate_underlying_price function behavior"""
    results = {}
    
    # Test data with various scenarios
    test_cases = [
        # Case 1: Contract has underlying_price
        {
            "name": "with_underlying_price",
            "contracts": [
                {"strike": 100, "underlying_price": 105.5},
                {"strike": 110, "underlying_price": 105.5}
            ],
            "expected": 105.5
        },
        # Case 2: No underlying_price, use strike average
        {
            "name": "no_underlying_price",
            "contracts": [
                {"strike": 100},
                {"strike": 110},
                {"strike": 120}
            ],
            "expected": 110.0
        },
        # Case 3: Mixed - should use underlying_price
        {
            "name": "mixed",
            "contracts": [
                {"strike": 100},
                {"strike": 110, "underlying_price": 108.75},
                {"strike": 120}
            ],
            "expected": 108.75
        },
        # Case 4: Empty contracts
        {
            "name": "empty",
            "contracts": [],
            "expected": None  # Should handle gracefully
        }
    ]
    
    # Test both implementations
    implementations = [
        ("expected_value_analysis", "tasks.options_trading_system.analysis_engine.expected_value_analysis.solution"),
        ("risk_analysis", "tasks.options_trading_system.analysis_engine.risk_analysis.solution")
    ]
    
    for impl_name, impl_path in implementations:
        try:
            # Import the module
            module = __import__(impl_path, fromlist=['ExpectedValueAnalyzer', 'RiskAnalyzer'])
            
            # Get the appropriate class
            if impl_name == "expected_value_analysis":
                analyzer = module.ExpectedValueAnalyzer({})
            else:
                analyzer = module.RiskAnalyzer({})
            
            # Test each case
            impl_results = []
            for test_case in test_cases:
                try:
                    result = analyzer._estimate_underlying_price(test_case["contracts"])
                    impl_results.append({
                        "case": test_case["name"],
                        "result": result,
                        "expected": test_case["expected"],
                        "matches": abs(result - test_case["expected"]) < 0.01 if test_case["expected"] else False
                    })
                except Exception as e:
                    impl_results.append({
                        "case": test_case["name"],
                        "error": str(e)
                    })
            
            results[impl_name] = impl_results
            
        except Exception as e:
            results[impl_name] = f"Error: {e}"
    
    return results


def find_duplicate_functions():
    """Find specific duplicate functions to target"""
    print("\nSearching for duplicate functions in current branch...")
    
    # Look for get_eod_contract_symbol implementations
    result = subprocess.run(
        ["grep", "-r", "get_eod_contract_symbol", ".", "--include=*.py"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        print(f"\nFound {len(lines)} references to get_eod_contract_symbol:")
        for line in lines[:10]:  # Show first 10
            print(f"  {line}")
        
        if len(lines) > 10:
            print(f"  ... and {len(lines) - 10} more")
    
    return result.stdout


def main():
    """Main validation runner"""
    validator = DeduplicationValidator()
    
    # Create baselines if needed, or validate against existing
    print("DEDUPLICATION VALIDATION FRAMEWORK")
    print("="*60)
    print(f"Baseline directory: {validator.baseline_dir}")
    print()
    
    # Test 1: Symbol Generation
    validator.validate_against_baseline("symbol_generation", test_symbol_generation)
    
    # Test 2: File I/O
    validator.validate_against_baseline("file_io", test_file_io_operations)
    
    # Test 3: Calculations
    validator.validate_against_baseline("calculations", test_calculation_functions)
    
    # Test 4: Save Evidence
    validator.validate_against_baseline("save_evidence", test_save_evidence)
    
    # Test 5: Estimate Underlying Price
    validator.validate_against_baseline("estimate_underlying_price", test_estimate_underlying_price)
    
    # Find duplicates
    print("\n" + "="*60)
    print("DUPLICATE FUNCTION ANALYSIS")
    print("="*60)
    find_duplicate_functions()
    
    # Summary
    success = validator.print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())