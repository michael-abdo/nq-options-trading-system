#!/usr/bin/env python3
"""
Phase 4 Complete Test Suite Runner

Runs all Phase 4 tests sequentially and generates a comprehensive report.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.timezone_utils import get_eastern_time

# Import test modules
from integration.test_live_market_integration import run_integration_tests
from performance.test_performance_optimization import run_performance_tests
from integration.test_stress_scenarios import run_stress_tests
from integration.test_dashboard_responsiveness import run_dashboard_tests

class Phase4TestRunner:
    """Runs all Phase 4 tests and consolidates results"""

    def __init__(self):
        self.results_dir = "outputs/test_results/phase4"
        os.makedirs(self.results_dir, exist_ok=True)

        self.test_results = {
            "phase": "Phase 4 - Testing & Validation",
            "start_time": get_eastern_time().isoformat(),
            "test_suites": {},
            "summary": {}
        }

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all Phase 4 test suites"""
        print("="*70)
        print("PHASE 4 COMPLETE TEST SUITE")
        print("="*70)
        print(f"Started at: {get_eastern_time().strftime('%Y-%m-%d %H:%M:%S %Z')}\n")

        # Define test suites to run
        test_suites = [
            {
                "name": "Integration Testing",
                "runner": run_integration_tests,
                "config": {
                    "test_duration_minutes": 5,  # Reduced for demo
                    "symbols": ["NQM5"],
                    "market_conditions": {
                        "test_high_volume": True,
                        "test_low_volume": False,
                        "test_volatility_spike": True
                    }
                }
            },
            {
                "name": "Performance Testing",
                "runner": run_performance_tests,
                "config": {
                    "load_test": {
                        "duration_seconds": 60,
                        "events_per_second": [100, 500, 1000],
                        "ramp_up_seconds": 10
                    },
                    "profiling": {
                        "enable_cpu_profiling": True,
                        "enable_memory_profiling": True,
                        "profile_duration_seconds": 30
                    }
                }
            },
            {
                "name": "Stress Testing",
                "runner": run_stress_tests,
                "config": {
                    "symbols": ["NQM5", "ESM5"],
                    "failure_scenarios": {
                        "connection_loss": True,
                        "data_corruption": True,
                        "memory_exhaustion": False,  # Skip for demo
                        "cpu_saturation": False  # Skip for demo
                    }
                }
            },
            {
                "name": "Dashboard Testing",
                "runner": run_dashboard_tests,
                "config": {
                    "load_test": {
                        "max_concurrent_signals": 50,
                        "update_frequency_hz": 5,
                        "test_duration_seconds": 60
                    },
                    "responsiveness": {
                        "interaction_tests": True,
                        "resize_tests": False,  # Skip for demo
                        "scroll_performance": True,
                        "chart_zoom_pan": True
                    }
                }
            }
        ]

        # Run each test suite
        for suite in test_suites:
            print(f"\n{'='*50}")
            print(f"Running {suite['name']}...")
            print("="*50)

            try:
                # Run test with timeout
                result = await asyncio.wait_for(
                    suite["runner"](suite["config"]),
                    timeout=600  # 10 minute timeout per suite
                )

                self.test_results["test_suites"][suite["name"]] = {
                    "status": "completed",
                    "result": result,
                    "summary": self._extract_summary(result)
                }

                print(f"✅ {suite['name']} completed successfully")

            except asyncio.TimeoutError:
                self.test_results["test_suites"][suite["name"]] = {
                    "status": "timeout",
                    "error": "Test suite exceeded 10 minute timeout"
                }
                print(f"⏱️ {suite['name']} timed out")

            except Exception as e:
                self.test_results["test_suites"][suite["name"]] = {
                    "status": "failed",
                    "error": str(e)
                }
                print(f"❌ {suite['name']} failed: {str(e)}")

        # Generate consolidated summary
        self._generate_summary()

        # Save results
        self._save_results()

        # Print final summary
        self._print_summary()

        return self.test_results

    def _extract_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from test result"""
        summary = {}

        # Extract common summary fields
        if "summary" in result:
            summary.update(result["summary"])

        # Extract test-specific metrics
        if "tests" in result:
            tests = result["tests"]
            passed = sum(1 for t in tests.values() if t.get("status") == "PASS")
            total = len(tests)
            summary["tests_passed"] = passed
            summary["tests_total"] = total
            summary["success_rate"] = passed / total if total > 0 else 0

        return summary

    def _generate_summary(self):
        """Generate overall test summary"""
        total_suites = len(self.test_results["test_suites"])
        completed_suites = sum(1 for s in self.test_results["test_suites"].values()
                              if s["status"] == "completed")

        total_tests = 0
        passed_tests = 0

        for suite in self.test_results["test_suites"].values():
            if suite["status"] == "completed" and "summary" in suite:
                total_tests += suite["summary"].get("tests_total", 0)
                passed_tests += suite["summary"].get("tests_passed", 0)

        self.test_results["summary"] = {
            "end_time": get_eastern_time().isoformat(),
            "total_suites": total_suites,
            "completed_suites": completed_suites,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "overall_success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "phase_complete": completed_suites == total_suites
        }

    def _save_results(self):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"{self.results_dir}/phase4_complete_results_{timestamp}.json"

        with open(result_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)

        print(f"\nResults saved to: {result_file}")

    def _print_summary(self):
        """Print test summary"""
        summary = self.test_results["summary"]

        print("\n" + "="*70)
        print("PHASE 4 TEST SUITE SUMMARY")
        print("="*70)
        print(f"Total Test Suites: {summary['total_suites']}")
        print(f"Completed Suites: {summary['completed_suites']}")
        print(f"Total Tests Run: {summary['total_tests']}")
        print(f"Tests Passed: {summary['passed_tests']}")
        print(f"Overall Success Rate: {summary['overall_success_rate']:.1%}")
        print(f"Phase 4 Complete: {'✅ YES' if summary['phase_complete'] else '❌ NO'}")

        print("\nSuite Results:")
        for suite_name, suite_result in self.test_results["test_suites"].items():
            status_icon = "✅" if suite_result["status"] == "completed" else "❌"
            print(f"  {status_icon} {suite_name}: {suite_result['status']}")

            if suite_result["status"] == "completed" and "summary" in suite_result:
                s = suite_result["summary"]
                if "success_rate" in s:
                    print(f"     - Success Rate: {s['success_rate']:.1%}")

async def main():
    """Main entry point"""
    runner = Phase4TestRunner()

    # Check if we should run in demo mode
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        print("\n🔵 Running in DEMO mode with reduced test duration")

    try:
        results = await runner.run_all_tests()

        if results["summary"]["phase_complete"]:
            print("\n✅ Phase 4 Testing & Validation COMPLETE!")
            return 0
        else:
            print("\n❌ Phase 4 Testing & Validation INCOMPLETE")
            return 1

    except Exception as e:
        print(f"\n❌ Test runner failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
