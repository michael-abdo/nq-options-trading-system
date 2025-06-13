#!/usr/bin/env python3
"""
Comprehensive Error Handling Test Runner

Runs all error handling and recovery tests in the correct order:
1. Core Error Handling and Recovery Tests
2. Market Data Validation Tests
3. Broker Connection Failure Tests
4. System Resilience and Stress Tests

Provides detailed reporting and failure analysis.
"""

import os
import sys
import subprocess
import time
from datetime import datetime
from utils.timezone_utils import get_eastern_time, get_utc_time


def run_test_suite(test_file, description):
    """Run a test suite and return results"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        # Run the test file
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

        execution_time = time.time() - start_time

        # Parse output for test results
        output_lines = result.stdout.split('\n')

        # Look for test results line
        tests_run = 0
        failures = 0
        errors = 0

        for line in output_lines:
            if "Tests run:" in line or "run:" in line:
                # Extract numbers from different formats
                parts = line.split()
                for i, part in enumerate(parts):
                    if "run" in part.lower() and i + 1 < len(parts):
                        try:
                            tests_run = int(parts[i + 1].rstrip(','))
                        except:
                            pass
                    elif "failure" in part.lower() and i + 1 < len(parts):
                        try:
                            failures = int(parts[i + 1].rstrip(','))
                        except:
                            pass
                    elif "error" in part.lower() and i + 1 < len(parts):
                        try:
                            errors = int(parts[i + 1])
                        except:
                            pass

        # Alternative parsing if standard format not found
        if tests_run == 0:
            for line in output_lines:
                if "📊" in line and ("Tests:" in line or "run," in line):
                    # Try to parse alternative format
                    import re
                    numbers = re.findall(r'\d+', line)
                    if len(numbers) >= 3:
                        tests_run = int(numbers[0])
                        failures = int(numbers[1])
                        errors = int(numbers[2])

        success = (result.returncode == 0) and (failures == 0) and (errors == 0)

        # Print summary
        print(f"\n📊 Test Results:")
        print(f"   Tests run: {tests_run}")
        print(f"   Failures: {failures}")
        print(f"   Errors: {errors}")
        print(f"   Execution time: {execution_time:.2f}s")
        print(f"   Status: {'✅ PASSED' if success else '❌ FAILED'}")

        # Print errors/failures if any
        if not success and result.stderr:
            print(f"\n🚨 Error Details:")
            print(result.stderr)

        if not success and "FAILED" in result.stdout:
            # Extract failure details
            failure_section = False
            for line in output_lines:
                if "FAILURES:" in line or "ERRORS:" in line:
                    failure_section = True
                    print(f"\n{line}")
                elif failure_section and line.strip():
                    print(f"   {line}")
                elif failure_section and not line.strip():
                    failure_section = False

        return {
            'success': success,
            'tests_run': tests_run,
            'failures': failures,
            'errors': errors,
            'execution_time': execution_time,
            'output': result.stdout
        }

    except Exception as e:
        print(f"❌ Failed to run test suite: {e}")
        return {
            'success': False,
            'tests_run': 0,
            'failures': 0,
            'errors': 1,
            'execution_time': time.time() - start_time,
            'output': str(e)
        }


def main():
    """Run all error handling test suites"""
    print("🛡️ COMPREHENSIVE ERROR HANDLING & RECOVERY TEST SUITE")
    print("=" * 70)
    print(f"Started at: {get_eastern_time().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test suites in order of execution
    test_suites = [
        {
            'file': 'test_error_handling_and_recovery.py',
            'description': 'Core Error Handling and Recovery Tests'
        },
        {
            'file': 'test_market_data_validation.py',
            'description': 'Market Data Validation Tests'
        },
        {
            'file': 'test_broker_connection_failures.py',
            'description': 'Broker Connection Failure Tests'
        },
        {
            'file': 'test_system_resilience.py',
            'description': 'System Resilience and Stress Tests'
        }
    ]

    # Run all test suites
    overall_results = {
        'total_tests': 0,
        'total_failures': 0,
        'total_errors': 0,
        'total_time': 0,
        'suites_passed': 0,
        'suites_failed': 0
    }

    suite_results = []

    for suite in test_suites:
        result = run_test_suite(suite['file'], suite['description'])
        suite_results.append({**result, 'name': suite['description']})

        # Update overall results
        overall_results['total_tests'] += result['tests_run']
        overall_results['total_failures'] += result['failures']
        overall_results['total_errors'] += result['errors']
        overall_results['total_time'] += result['execution_time']

        if result['success']:
            overall_results['suites_passed'] += 1
        else:
            overall_results['suites_failed'] += 1

    # Print final summary
    print(f"\n{'='*70}")
    print("🎯 FINAL SUMMARY")
    print(f"{'='*70}")

    print(f"\n📊 Overall Statistics:")
    print(f"   Test Suites: {len(test_suites)}")
    print(f"   Suites Passed: {overall_results['suites_passed']}")
    print(f"   Suites Failed: {overall_results['suites_failed']}")
    print(f"   Total Tests: {overall_results['total_tests']}")
    print(f"   Total Failures: {overall_results['total_failures']}")
    print(f"   Total Errors: {overall_results['total_errors']}")
    print(f"   Total Time: {overall_results['total_time']:.2f}s")

    print(f"\n📋 Suite-by-Suite Results:")
    for result in suite_results:
        status = "✅ PASSED" if result['success'] else "❌ FAILED"
        print(f"   {result['name']}: {status} ({result['tests_run']} tests, {result['execution_time']:.1f}s)")

    # Overall success determination
    overall_success = (overall_results['suites_failed'] == 0 and
                      overall_results['total_failures'] == 0 and
                      overall_results['total_errors'] == 0)

    print(f"\n🎉 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")

    if overall_success:
        print(f"\n🛡️ Verified Error Handling Capabilities:")
        print(f"   • Market volatility spike handling with strict position limits")
        print(f"   • Data feed interruption recovery with exponential backoff")
        print(f"   • Network connectivity recovery and timeout handling")
        print(f"   • API failure graceful degradation and automatic failover")
        print(f"   • Manual recovery procedures and emergency suspension")
        print(f"   • Broker connection failure recovery mechanisms")
        print(f"   • Market data validation and quality monitoring")
        print(f"   • System resilience under high-frequency errors")
        print(f"   • Resource exhaustion handling and memory stability")
        print(f"   • Concurrent operation stress testing")
        print(f"   • Extreme condition recovery and restart procedures")
        print(f"   • Comprehensive health monitoring and reporting")
        print(f"   • Production error handling and alert systems")
    else:
        print(f"\n⚠️ Some tests failed. Review the detailed output above for specific issues.")

    print(f"\nCompleted at: {get_eastern_time().strftime('%Y-%m-%d %H:%M:%S')}")

    return 0 if overall_success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
