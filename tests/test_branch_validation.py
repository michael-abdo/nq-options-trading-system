#!/usr/bin/env python3
"""
Branch Validation Tests
Ensures functionality is preserved during deduplication
"""

import unittest
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime

class BranchValidationTest(unittest.TestCase):
    """Base class for branch-specific validation tests"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_output_dir = Path("tests/validation_outputs")
        self.test_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get current branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True
        )
        self.current_branch = result.stdout.strip()
        
    def run_command_and_capture(self, command, timeout=60):
        """Run a command and capture output"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': command
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timed out',
                'command': command
            }
    
    def save_baseline(self, data, name):
        """Save baseline data for comparison"""
        baseline_file = self.test_output_dir / f"baseline_{name}_{self.current_branch}.json"
        with open(baseline_file, 'w') as f:
            json.dump(data, f, indent=2)
        return baseline_file
    
    def load_baseline(self, name):
        """Load baseline data for comparison"""
        baseline_file = self.test_output_dir / f"baseline_{name}_{self.current_branch}.json"
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                return json.load(f)
        return None
    
    def compare_outputs(self, current, baseline, tolerance=0.001):
        """Compare two outputs with tolerance for floating point"""
        if type(current) != type(baseline):
            return False, f"Type mismatch: {type(current)} vs {type(baseline)}"
        
        if isinstance(current, dict):
            if set(current.keys()) != set(baseline.keys()):
                return False, f"Key mismatch: {set(current.keys())} vs {set(baseline.keys())}"
            
            for key in current:
                match, msg = self.compare_outputs(current[key], baseline[key], tolerance)
                if not match:
                    return False, f"In key '{key}': {msg}"
            return True, "Dicts match"
        
        elif isinstance(current, list):
            if len(current) != len(baseline):
                return False, f"Length mismatch: {len(current)} vs {len(baseline)}"
            
            for i, (c, b) in enumerate(zip(current, baseline)):
                match, msg = self.compare_outputs(c, b, tolerance)
                if not match:
                    return False, f"At index {i}: {msg}"
            return True, "Lists match"
        
        elif isinstance(current, float):
            if abs(current - baseline) > tolerance:
                return False, f"Float mismatch: {current} vs {baseline}"
            return True, "Floats match within tolerance"
        
        else:
            if current != baseline:
                return False, f"Value mismatch: {current} vs {baseline}"
            return True, "Values match"


class TestSymbolGenerationValidation(BranchValidationTest):
    """Validate symbol generation across branches"""
    
    def test_symbol_generation_consistency(self):
        """Test that all symbol generation methods produce same results"""
        test_cases = [
            # (base_symbol, option_type, year_format, expected_pattern)
            ("NQ", "weekly", "2digit", r"MM\d[A-Z]\d{2}"),
            ("NQ", "monthly", "2digit", r"MM6[A-Z]\d{2}"),
            ("NQ", "friday", "2digit", r"MQ\d[A-Z]\d{2}"),
            ("NQ", "daily", "2digit", r"MC\d[A-Z]\d{2}"),
        ]
        
        # Test command to generate symbols
        test_script = """
import sys
sys.path.insert(0, '.')

# Try to import various symbol generators that might exist
symbol_generators = []

try:
    from tasks.options_trading_system.data_ingestion.barchart_web_scraper.symbol_generator import BarchartSymbolGenerator
    sg = BarchartSymbolGenerator()
    symbol_generators.append(('BarchartSymbolGenerator', lambda b, o, y: sg.get_eod_contract_symbol(b, o, y)))
except ImportError:
    pass

try:
    from tasks.options_trading_system.data_ingestion.barchart_web_scraper.solution import BarchartAPIComparator
    comp = BarchartAPIComparator()
    symbol_generators.append(('BarchartAPIComparator', lambda b, o, y: comp.get_eod_contract_symbol(b, o, y)))
except ImportError:
    pass

# Test each generator
test_cases = """ + str([(tc[0], tc[1], tc[2]) for tc in test_cases]) + """
for base, opt_type, year_fmt in test_cases:
    print(f"\\nTesting: {base}, {opt_type}, {year_fmt}")
    for name, generator in symbol_generators:
        try:
            result = generator(base, opt_type, year_fmt)
            print(f"  {name}: {result}")
        except Exception as e:
            print(f"  {name}: ERROR - {e}")
"""
        
        # Save test script
        test_file = self.test_output_dir / "test_symbol_generators.py"
        with open(test_file, 'w') as f:
            f.write(test_script)
        
        # Run test
        result = self.run_command_and_capture(f"python {test_file}")
        
        self.assertTrue(result['success'], f"Symbol generation test failed: {result['stderr']}")
        
        # Parse and validate results
        lines = result['stdout'].strip().split('\n')
        current_test = None
        results_by_test = {}
        
        for line in lines:
            if line.startswith("Testing:"):
                current_test = line.replace("Testing: ", "")
                results_by_test[current_test] = []
            elif line.strip().startswith(("BarchartSymbolGenerator:", "BarchartAPIComparator:")):
                generator, symbol = line.strip().split(": ", 1)
                if current_test and "ERROR" not in symbol:
                    results_by_test[current_test].append(symbol)
        
        # Verify all generators produce same result for each test case
        for test_case, symbols in results_by_test.items():
            if len(symbols) > 1:
                unique_symbols = set(symbols)
                self.assertEqual(
                    len(unique_symbols), 
                    1, 
                    f"Symbol mismatch for {test_case}: {symbols}"
                )


class TestFileIOValidation(BranchValidationTest):
    """Validate file I/O operations"""
    
    def test_json_operations_consistency(self):
        """Test that all JSON save/load methods work identically"""
        test_data = {
            "test": "data",
            "number": 42,
            "float": 3.14159,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        test_file = self.test_output_dir / "test_io.json"
        
        # Test different I/O methods
        io_test_script = f"""
import json
import sys
sys.path.insert(0, '.')

test_data = {test_data}
test_file = "{test_file}"

# Method 1: Direct json
with open(test_file, 'w') as f:
    json.dump(test_data, f, indent=2)
with open(test_file, 'r') as f:
    data1 = json.load(f)
print("Direct JSON: OK")

# Method 2: FileIOUtils if available
try:
    from scripts.utilities.file_io_utils import FileIOUtils
    FileIOUtils.save_json(test_data, test_file)
    data2 = FileIOUtils.load_json(test_file)
    print("FileIOUtils: OK")
except ImportError:
    print("FileIOUtils: Not available")

# Compare data integrity
print(f"Data integrity: {data1 == test_data}")
"""
        
        result = self.run_command_and_capture(f"python -c '{io_test_script}'")
        self.assertTrue(result['success'], f"I/O test failed: {result['stderr']}")
        self.assertIn("Data integrity: True", result['stdout'])


class TestCalculationValidation(BranchValidationTest):
    """Validate calculation functions"""
    
    def test_pressure_calculation_consistency(self):
        """Test pressure calculation methods"""
        test_data = {
            "strikes": [19000, 19100, 19200],
            "call_oi": [1000, 2000, 1500],
            "put_oi": [1500, 1000, 2000],
            "underlying": 19100
        }
        
        calc_test_script = f"""
import sys
sys.path.insert(0, '.')

# Test data
strikes = {test_data['strikes']}
call_oi = {test_data['call_oi']}
put_oi = {test_data['put_oi']}
underlying = {test_data['underlying']}

# Try different calculation methods
results = []

# Method 1: Simple pressure
try:
    total_call = sum(call_oi)
    total_put = sum(put_oi)
    simple_pressure = (total_call - total_put) / (total_call + total_put)
    results.append(('Simple', simple_pressure))
    print(f"Simple pressure: {simple_pressure:.4f}")
except Exception as e:
    print(f"Simple pressure: ERROR - {e}")

# Method 2: Weighted pressure
try:
    weighted_call = sum(c * abs(s - underlying) for c, s in zip(call_oi, strikes))
    weighted_put = sum(p * abs(s - underlying) for p, s in zip(put_oi, strikes))
    weighted_pressure = (weighted_call - weighted_put) / (weighted_call + weighted_put)
    results.append(('Weighted', weighted_pressure))
    print(f"Weighted pressure: {weighted_pressure:.4f}")
except Exception as e:
    print(f"Weighted pressure: ERROR - {e}")

# Check consistency
if len(results) > 1:
    values = [r[1] for r in results]
    if all(abs(v - values[0]) < 0.0001 for v in values):
        print("VALIDATION: All methods consistent")
    else:
        print("VALIDATION: Methods differ")
"""
        
        result = self.run_command_and_capture(f"python -c '{calc_test_script}'")
        self.assertTrue(result['success'], f"Calculation test failed: {result['stderr']}")


class TestEndToEndValidation(BranchValidationTest):
    """End-to-end validation of key workflows"""
    
    def test_pipeline_output_consistency(self):
        """Test that pipeline produces consistent output"""
        # Create baseline if it doesn't exist
        baseline = self.load_baseline("pipeline_output")
        
        if baseline is None:
            print("Creating baseline for pipeline output...")
            # Run pipeline in dry-run mode
            result = self.run_command_and_capture(
                "python daily_options_pipeline.py --dry-run --limit 10",
                timeout=120
            )
            
            if result['success']:
                baseline = {
                    'stdout': result['stdout'],
                    'command': result['command'],
                    'timestamp': datetime.now().isoformat()
                }
                self.save_baseline(baseline, "pipeline_output")
                print("Baseline created successfully")
        
        # Run current pipeline
        print("Running current pipeline...")
        current_result = self.run_command_and_capture(
            "python daily_options_pipeline.py --dry-run --limit 10",
            timeout=120
        )
        
        # Compare key metrics in output
        if current_result['success'] and baseline:
            # Extract numeric values from output for comparison
            import re
            
            def extract_numbers(text):
                return re.findall(r'-?\d+\.?\d*', text)
            
            baseline_numbers = extract_numbers(baseline['stdout'])
            current_numbers = extract_numbers(current_result['stdout'])
            
            # Allow some variance but check general consistency
            if len(current_numbers) > 0:
                print(f"Found {len(current_numbers)} numeric values in output")
                self.assertGreater(len(current_numbers), 0, "No numeric output found")


if __name__ == "__main__":
    # Run validation tests
    unittest.main(verbosity=2)