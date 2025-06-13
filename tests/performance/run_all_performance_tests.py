#!/usr/bin/env python3
"""
Comprehensive Performance Test Runner

Runs all performance tests in appropriate order:
1. Quick performance tests (fast validation)
2. Full performance under load tests (if quick tests pass)

Provides detailed reporting and performance metrics summary.
"""

import os
import sys
import subprocess
import time
import json
from datetime import datetime
from utils.timezone_utils import get_eastern_time, get_utc_time


def run_test_suite(test_file, description, timeout=300):
    """Run a test suite and return results"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        # Use virtual environment Python
        venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  '..', '..', 'venv', 'bin', 'python')

        if not os.path.exists(venv_python):
            venv_python = sys.executable

        # Run the test file
        result = subprocess.run(
            [venv_python, test_file],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            timeout=timeout
        )

        execution_time = time.time() - start_time

        # Parse output for test results
        output_lines = result.stdout.split('\n')

        # Look for test results
        tests_run = 0
        failures = 0
        errors = 0
        skipped = 0

        for line in output_lines:
            if "Ran" in line and "test" in line:
                # Parse "Ran X tests in Y"
                parts = line.split()
                if len(parts) > 1:
                    tests_run = int(parts[1])
            elif "FAILED" in line:
                # Parse failures and errors
                import re
                match = re.search(r'failures=(\d+)', line)
                if match:
                    failures = int(match.group(1))
                match = re.search(r'errors=(\d+)', line)
                if match:
                    errors = int(match.group(1))
            elif "OK" in line and "skipped=" in line:
                import re
                match = re.search(r'skipped=(\d+)', line)
                if match:
                    skipped = int(match.group(1))

        success = (result.returncode == 0) and (failures == 0) and (errors == 0)

        # Print summary
        print(f"\n📊 Test Results:")
        print(f"   Tests run: {tests_run}")
        print(f"   Failures: {failures}")
        print(f"   Errors: {errors}")
        print(f"   Skipped: {skipped}")
        print(f"   Execution time: {execution_time:.2f}s")
        print(f"   Status: {'✅ PASSED' if success else '❌ FAILED'}")

        # Extract performance metrics if available
        performance_metrics = extract_performance_metrics(result.stdout)
        if performance_metrics:
            print(f"\n📈 Performance Highlights:")
            for metric in performance_metrics:
                print(f"   {metric}")

        return {
            'success': success,
            'tests_run': tests_run,
            'failures': failures,
            'errors': errors,
            'skipped': skipped,
            'execution_time': execution_time,
            'output': result.stdout,
            'metrics': performance_metrics
        }

    except subprocess.TimeoutExpired:
        print(f"⏱️ Test suite timed out after {timeout} seconds")
        return {
            'success': False,
            'tests_run': 0,
            'failures': 0,
            'errors': 1,
            'skipped': 0,
            'execution_time': timeout,
            'output': f"Test timed out after {timeout}s",
            'metrics': []
        }
    except Exception as e:
        print(f"❌ Failed to run test suite: {e}")
        return {
            'success': False,
            'tests_run': 0,
            'failures': 0,
            'errors': 1,
            'skipped': 0,
            'execution_time': time.time() - start_time,
            'output': str(e),
            'metrics': []
        }


def extract_performance_metrics(output):
    """Extract performance metrics from test output"""
    metrics = []
    lines = output.split('\n')

    for i, line in enumerate(lines):
        # Look for latency metrics
        if "P95:" in line and "ms" in line:
            metrics.append(line.strip())
        elif "Average:" in line and "ms" in line:
            metrics.append(line.strip())
        elif "Throughput:" in line and "ops/sec" in line:
            metrics.append(line.strip())
        elif "Memory Growth:" in line and "MB" in line:
            metrics.append(line.strip())
        elif "CPU Peak:" in line and "%" in line:
            metrics.append(line.strip())

    return metrics


def save_performance_report(results, output_dir):
    """Save performance test results to a JSON report"""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = get_eastern_time().strftime('%Y%m%d_%H%M%S')
    report_file = os.path.join(output_dir, f'performance_report_{timestamp}.json')

    report = {
        'timestamp': get_eastern_time().isoformat(),
        'summary': {
            'total_suites': len(results),
            'suites_passed': sum(1 for r in results if r['success']),
            'suites_failed': sum(1 for r in results if not r['success']),
            'total_tests': sum(r['tests_run'] for r in results),
            'total_failures': sum(r['failures'] for r in results),
            'total_errors': sum(r['errors'] for r in results),
            'total_skipped': sum(r['skipped'] for r in results),
            'total_time': sum(r['execution_time'] for r in results)
        },
        'suites': results,
        'performance_metrics': {
            'all_metrics': [m for r in results for m in r.get('metrics', [])]
        }
    }

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Performance report saved to: {report_file}")
    return report_file


def main():
    """Run all performance test suites"""
    print("🚀 COMPREHENSIVE PERFORMANCE TESTING SUITE")
    print("=" * 70)
    print(f"Started at: {get_eastern_time().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test suites in order of execution
    test_suites = [
        {
            'file': 'test_performance_quick.py',
            'description': 'Quick Performance Validation Tests',
            'timeout': 60  # 1 minute
        },
        {
            'file': 'test_performance_under_load.py',
            'description': 'Full Performance Under Load Tests',
            'timeout': 600  # 10 minutes
        }
    ]

    # Run all test suites
    suite_results = []

    # First run quick tests
    quick_result = run_test_suite(
        test_suites[0]['file'],
        test_suites[0]['description'],
        test_suites[0]['timeout']
    )
    suite_results.append({**quick_result, 'name': test_suites[0]['description']})

    # Only run full tests if quick tests pass
    if quick_result['success']:
        print("\n✅ Quick tests passed. Running full performance tests...")
        full_result = run_test_suite(
            test_suites[1]['file'],
            test_suites[1]['description'],
            test_suites[1]['timeout']
        )
        suite_results.append({**full_result, 'name': test_suites[1]['description']})
    else:
        print("\n⚠️ Quick tests failed. Skipping full performance tests.")

    # Print final summary
    print(f"\n{'='*70}")
    print("🎯 FINAL PERFORMANCE TEST SUMMARY")
    print(f"{'='*70}")

    overall_success = all(r['success'] for r in suite_results)

    print(f"\n📊 Overall Statistics:")
    print(f"   Test Suites Run: {len(suite_results)}")
    print(f"   Total Tests: {sum(r['tests_run'] for r in suite_results)}")
    print(f"   Total Time: {sum(r['execution_time'] for r in suite_results):.2f}s")

    print(f"\n📋 Suite Results:")
    for result in suite_results:
        status = "✅ PASSED" if result['success'] else "❌ FAILED"
        print(f"   {result['name']}: {status}")
        print(f"      Tests: {result['tests_run']} | Failures: {result['failures']} | Errors: {result['errors']} | Time: {result['execution_time']:.1f}s")

    # Save performance report
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')
    report_file = save_performance_report(suite_results, output_dir)

    print(f"\n🎉 Overall Result: {'✅ ALL PERFORMANCE TESTS PASSED' if overall_success else '❌ SOME PERFORMANCE TESTS FAILED'}")

    if overall_success:
        print(f"\n✅ Verified Performance Capabilities:")
        print(f"   • System handles high-volume market periods (100+ ops/sec)")
        print(f"   • Memory usage stable during continuous operation")
        print(f"   • Processing latency <100ms under peak loads")
        print(f"   • Database performance optimized for concurrent access")
        print(f"   • Disk space and log management functional")
        print(f"   • Burst load handling without degradation")
        print(f"   • Resource monitoring and metrics collection")
        print(f"   • Graceful handling of system stress conditions")
    else:
        print(f"\n⚠️ Some performance tests failed. Review the detailed output above.")
        print(f"   Check the report at: {report_file}")

    print(f"\nCompleted at: {get_eastern_time().strftime('%Y-%m-%d %H:%M:%S')}")

    return 0 if overall_success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
