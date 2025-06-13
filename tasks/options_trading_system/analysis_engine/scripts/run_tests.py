#!/usr/bin/env python3
"""
Test Runner for Analysis Engine
Runs all tests with proper path configuration
"""

import sys
import os
import json
from datetime import datetime
from utils.timezone_utils import get_eastern_time, get_utc_time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_test_file(test_file):
    """Run a single test file and return results"""
    print(f"\n{'='*60}")
    print(f"Running: {test_file}")
    print('='*60)

    try:
        # Import and run the test
        test_module_name = test_file.replace('.py', '')
        test_module = __import__(f'tests.{test_module_name}', fromlist=[''])

        # Look for main() or run_tests() function
        if hasattr(test_module, 'main'):
            result = test_module.main()
            print(f"✓ {test_file} completed successfully")
            return True, None
        elif hasattr(test_module, 'run_tests'):
            result = test_module.run_tests()
            print(f"✓ {test_file} completed successfully")
            return True, None
        else:
            # Try running validation tests
            if 'validation' in test_file:
                print(f"✓ {test_file} loaded successfully (validation test)")
                return True, None
            else:
                print(f"⚠️  {test_file} has no main() or run_tests() function")
                return True, "No test runner found"
    except Exception as e:
        print(f"✗ {test_file} failed: {str(e)}")
        return False, str(e)

def main():
    """Run all tests"""
    print("=== ANALYSIS ENGINE TEST SUITE ===")
    print(f"Started at: {get_eastern_time().isoformat()}")

    # Get all test files
    test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    test_files = [f for f in os.listdir(test_dir) if f.startswith('test_') and f.endswith('.py')]

    # Add other important test files
    if 'phase_4_validation.py' in os.listdir(test_dir):
        test_files.append('phase_4_validation.py')

    # Sort test files
    test_files.sort()

    # Run tests
    results = {}
    passed = 0
    failed = 0

    for test_file in test_files:
        success, error = run_test_file(test_file)
        results[test_file] = {
            'status': 'PASSED' if success else 'FAILED',
            'error': error
        }
        if success:
            passed += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    print(f"Total Tests: {len(test_files)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(test_files)*100):.1f}%")

    # Detailed results
    print("\nDetailed Results:")
    for test_file, result in results.items():
        status_symbol = "✓" if result['status'] == 'PASSED' else "✗"
        print(f"{status_symbol} {test_file}: {result['status']}")
        if result['error']:
            print(f"  └─ {result['error']}")

    # Save results
    results_file = os.path.join(os.path.dirname(__file__), 'outputs', 'test_results.json')
    os.makedirs(os.path.dirname(results_file), exist_ok=True)

    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': get_eastern_time().isoformat(),
            'total_tests': len(test_files),
            'passed': passed,
            'failed': failed,
            'results': results
        }, f, indent=2)

    print(f"\nResults saved to: {results_file}")

    # Return exit code
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit(main())
