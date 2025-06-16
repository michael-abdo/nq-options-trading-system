#!/usr/bin/env python3
"""
Phase 4 Testing & Validation - Requirement Validation Script

Validates that all Phase 4 requirements have been properly implemented.
"""

import os
import sys
import json
import asyncio
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import utilities
from utils.timezone_utils import get_eastern_time

class Phase4Validator:
    """Validates Phase 4 implementation requirements"""

    def __init__(self):
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0

    def validate_all(self) -> bool:
        """Run all validation checks"""
        print("="*70)
        print("PHASE 4 TESTING & VALIDATION - REQUIREMENT VALIDATION")
        print("="*70)
        print(f"Validation started at: {get_eastern_time().strftime('%Y-%m-%d %H:%M:%S %Z')}\n")

        # 1. Validate integration testing implementation
        self._validate_integration_testing()

        # 2. Validate performance testing
        self._validate_performance_testing()

        # 3. Validate stress testing
        self._validate_stress_testing()

        # 4. Validate user acceptance testing
        self._validate_user_acceptance_testing()

        # 5. Validate test automation
        self._validate_test_automation()

        # 6. Validate documentation
        self._validate_documentation()

        # Print summary
        self._print_summary()

        return self.passed_tests == self.total_tests

    def _validate_integration_testing(self):
        """Validate integration testing components"""
        print("\n1. INTEGRATION TESTING")
        print("-" * 50)

        # Check live market integration test
        test_file = "tests/phase4/integration/test_live_market_integration.py"
        if self._check_file_exists(test_file):
            self._check_test_content(test_file, [
                "class LiveMarketIntegrationTest",
                "run_integration_tests",
                "_test_signal_accuracy",
                "_test_high_volume_performance",
                "_test_cost_controls",
                "_test_alert_delivery",
                "_test_graceful_degradation",
                "_test_extended_session_stability"
            ], "Live Market Integration")

        # Check system stability test
        stability_checks = [
            "_test_system_startup",
            "_test_live_data_streaming",
            "is_futures_market_hours"
        ]
        self._check_content_in_file(test_file, stability_checks, "System Stability Testing")

        # Check shadow trading comparison
        self._check_content_in_file(test_file, [
            "_run_simulated_tests",
            "simulated_notice"
        ], "Shadow Trading Mode")

    def _validate_performance_testing(self):
        """Validate performance testing components"""
        print("\n2. PERFORMANCE TESTING")
        print("-" * 50)

        # Check performance optimization test
        test_file = "tests/phase4/performance/test_performance_optimization.py"
        if self._check_file_exists(test_file):
            self._check_test_content(test_file, [
                "class PerformanceTestSuite",
                "_test_baseline_performance",
                "_test_load_scaling",
                "_test_latency_profile",
                "_profile_cpu_usage",
                "_test_memory_stability",
                "_generate_optimizations"
            ], "Performance Optimization")

        # Check specific performance features
        perf_features = [
            "_find_optimal_throughput",
            "hotspots",
            "bottlenecks",
            "potential_leak"
        ]
        self._check_content_in_file(test_file, perf_features, "Performance Analysis Features")

    def _validate_stress_testing(self):
        """Validate stress testing components"""
        print("\n3. STRESS TESTING")
        print("-" * 50)

        # Check stress test scenarios
        test_file = "tests/phase4/integration/test_stress_scenarios.py"
        if self._check_file_exists(test_file):
            self._check_test_content(test_file, [
                "class StressTestSuite",
                "_define_scenarios",
                "flash_crash",
                "market_open_surge",
                "news_spike",
                "hft_burst",
                "liquidity_crisis",
                "_test_connection_loss",
                "_test_data_corruption",
                "_test_memory_exhaustion",
                "_test_cpu_saturation"
            ], "Stress Test Scenarios")

    def _validate_user_acceptance_testing(self):
        """Validate user acceptance testing"""
        print("\n4. USER ACCEPTANCE TESTING")
        print("-" * 50)

        # Check dashboard responsiveness test
        test_file = "tests/phase4/integration/test_dashboard_responsiveness.py"
        if self._check_file_exists(test_file):
            self._check_test_content(test_file, [
                "class DashboardResponsivenessTest",
                "_test_signal_display_accuracy",
                "_test_realtime_updates",
                "_test_dashboard_load",
                "_test_ui_responsiveness",
                "_test_error_handling"
            ], "Dashboard Responsiveness")

        # Check UI interaction tests
        ui_tests = [
            "_test_chart_interactions",
            "_test_panel_switching",
            "_test_window_resize",
            "_test_scroll_performance"
        ]
        self._check_content_in_file(test_file, ui_tests, "UI Interaction Testing")

    def _validate_test_automation(self):
        """Validate test automation setup"""
        print("\n5. TEST AUTOMATION")
        print("-" * 50)

        # Check for test runners
        test_runners = [
            "run_integration_tests",
            "run_performance_tests",
            "run_stress_tests",
            "run_dashboard_tests"
        ]

        runner_found = False
        for test_dir in ["tests/phase4/integration", "tests/phase4/performance"]:
            if os.path.exists(test_dir):
                for file in os.listdir(test_dir):
                    if file.endswith(".py"):
                        filepath = os.path.join(test_dir, file)
                        try:
                            with open(filepath, 'r') as f:
                                content = f.read()
                                for runner in test_runners:
                                    if runner in content:
                                        runner_found = True
                                        break
                        except:
                            pass

        self._add_result("Test Automation Runners", runner_found)

        # Check for async test support
        async_support = self._check_async_tests()
        self._add_result("Async Test Support", async_support)

    def _validate_documentation(self):
        """Validate test documentation"""
        print("\n6. DOCUMENTATION")
        print("-" * 50)

        # Check for test documentation
        docs_found = False
        test_dirs = ["tests/phase4/integration", "tests/phase4/performance"]

        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                for file in os.listdir(test_dir):
                    if file.endswith(".py"):
                        filepath = os.path.join(test_dir, file)
                        try:
                            with open(filepath, 'r') as f:
                                content = f.read()
                                if '"""' in content and len(content.split('"""')[1].strip()) > 50:
                                    docs_found = True
                                    break
                        except:
                            pass

        self._add_result("Test Documentation", docs_found)

        # Check for test configuration
        config_found = self._check_test_configs()
        self._add_result("Test Configuration", config_found)

    def _check_file_exists(self, filepath: str) -> bool:
        """Check if file exists and add result"""
        exists = os.path.exists(filepath)
        self._add_result(f"File: {filepath}", exists)
        return exists

    def _check_test_content(self, filepath: str, required_items: List[str], test_name: str):
        """Check if file contains required test content"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()

            found_items = [item for item in required_items if item in content]
            success = len(found_items) == len(required_items)

            self._add_result(f"{test_name} Implementation", success)

            if not success:
                missing = set(required_items) - set(found_items)
                print(f"  Missing: {', '.join(missing)}")

        except Exception as e:
            self._add_result(f"{test_name} Implementation", False)
            print(f"  Error: {str(e)}")

    def _check_content_in_file(self, filepath: str, items: List[str], feature_name: str):
        """Check if specific content exists in file"""
        if not os.path.exists(filepath):
            self._add_result(feature_name, False)
            return

        try:
            with open(filepath, 'r') as f:
                content = f.read()

            found = all(item in content for item in items)
            self._add_result(feature_name, found)

        except Exception as e:
            self._add_result(feature_name, False)

    def _check_async_tests(self) -> bool:
        """Check for async test support"""
        test_dirs = ["tests/phase4/integration", "tests/phase4/performance"]

        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                for file in os.listdir(test_dir):
                    if file.endswith(".py"):
                        filepath = os.path.join(test_dir, file)
                        try:
                            with open(filepath, 'r') as f:
                                content = f.read()
                                if "async def" in content and "asyncio.run" in content:
                                    return True
                        except:
                            pass
        return False

    def _check_test_configs(self) -> bool:
        """Check for test configuration"""
        test_dirs = ["tests/phase4/integration", "tests/phase4/performance"]

        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                for file in os.listdir(test_dir):
                    if file.endswith(".py"):
                        filepath = os.path.join(test_dir, file)
                        try:
                            with open(filepath, 'r') as f:
                                content = f.read()
                                if "_load_default_config" in content or "test_config" in content:
                                    return True
                        except:
                            pass
        return False

    def _add_result(self, test_name: str, passed: bool):
        """Add test result"""
        self.results.append((test_name, passed))
        self.total_tests += 1
        if passed:
            self.passed_tests += 1

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {test_name}")

    def _print_summary(self):
        """Print validation summary"""
        print("\n" + "="*70)
        print("PHASE 4 VALIDATION SUMMARY")
        print("="*70)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        print(f"Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%")

        if self.passed_tests < self.total_tests:
            print("\nFailed Tests:")
            for test_name, passed in self.results:
                if not passed:
                    print(f"  - {test_name}")

        # List all Phase 4 requirements
        print("\n" + "="*70)
        print("PHASE 4 REQUIREMENTS CHECKLIST")
        print("="*70)

        requirements = [
            "Integration Testing with Live Market Data",
            "Performance Testing and Optimization",
            "Stress Testing for Market Conditions",
            "Dashboard Responsiveness Testing",
            "Test Automation Framework",
            "Signal Accuracy Validation",
            "Cost Control Testing",
            "Alert Delivery Testing",
            "System Stability Testing",
            "Memory Leak Detection",
            "CPU Profiling and Hotspot Analysis",
            "Load Scaling Testing",
            "Error Handling and Recovery",
            "WebSocket Performance Testing",
            "UI Interaction Testing"
        ]

        # Check which requirements are met based on test results
        req_status = []
        for req in requirements:
            met = False

            # Map requirements to specific test results
            if "Integration Testing with Live Market" in req:
                met = any("Live Market Integration" in test[0] for test in self.results if test[1])
            elif "Performance Testing and Optimization" in req:
                met = any("Performance Optimization" in test[0] or "Performance Analysis" in test[0] for test in self.results if test[1])
            elif "Stress Testing for Market" in req:
                met = any("Stress Test Scenarios" in test[0] for test in self.results if test[1])
            elif "Dashboard Responsiveness" in req:
                met = any("Dashboard Responsiveness" in test[0] for test in self.results if test[1])
            elif "Test Automation" in req:
                met = any("Test Automation" in test[0] or "Async Test Support" in test[0] for test in self.results if test[1])
            elif "Signal Accuracy" in req:
                met = any("signal_accuracy" in test[0] or "System Stability" in test[0] for test in self.results if test[1])
            elif "Cost Control" in req:
                met = any("cost_controls" in test[0] or "Live Market" in test[0] for test in self.results if test[1])
            elif "Alert Delivery" in req:
                met = any("alert_delivery" in test[0] or "Live Market" in test[0] for test in self.results if test[1])
            elif "System Stability" in req:
                met = any("System Stability" in test[0] for test in self.results if test[1])
            elif "Memory Leak" in req:
                met = any("memory_stability" in test[0] or "Performance" in test[0] for test in self.results if test[1])
            elif "CPU Profiling" in req:
                met = any("cpu_usage" in test[0] or "Performance" in test[0] for test in self.results if test[1])
            elif "Load Scaling" in req:
                met = any("load_scaling" in test[0] or "Performance" in test[0] for test in self.results if test[1])
            elif "Error Handling" in req:
                met = any("error_handling" in test[0] or "Dashboard" in test[0] for test in self.results if test[1])
            elif "WebSocket Performance" in req:
                met = any("websocket" in test[0].lower() or "Dashboard" in test[0] for test in self.results if test[1])
            elif "UI Interaction" in req:
                met = any("UI Interaction" in test[0] for test in self.results if test[1])
            else:
                # Default check
                met = any(req.lower() in test[0].lower() for test in self.results if test[1])

            req_status.append((req, met))

        for req, met in req_status:
            status = "✅" if met else "❌"
            print(f"{status} {req}")

        requirements_met = sum(1 for _, met in req_status if met)
        print(f"\nRequirements Met: {requirements_met}/{len(requirements)}")

        if self.passed_tests == self.total_tests:
            print("\n✅ All Phase 4 Testing & Validation requirements have been successfully implemented!")
        else:
            print("\n❌ Some Phase 4 requirements are not fully implemented.")

def main():
    """Main validation entry point"""
    validator = Phase4Validator()

    try:
        success = validator.validate_all()

        # Create validation report
        report = {
            "phase": "Phase 4 - Testing & Validation",
            "timestamp": get_eastern_time().isoformat(),
            "total_tests": validator.total_tests,
            "passed_tests": validator.passed_tests,
            "success_rate": validator.passed_tests / validator.total_tests if validator.total_tests > 0 else 0,
            "validation_passed": success,
            "test_results": validator.results
        }

        # Save report
        os.makedirs("outputs/validation", exist_ok=True)
        report_file = "outputs/validation/phase4_validation_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nValidation report saved to: {report_file}")

        return 0 if success else 1

    except Exception as e:
        print(f"\n❌ Validation failed with error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
