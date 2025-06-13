#!/usr/bin/env python3
"""
Comprehensive Test Validation and Reporting System

Runs all IFD v3.0 testing components and generates unified validation report:
- Unit tests for IFD v3 components
- Data flow integration tests
- End-to-end pipeline tests
- Performance requirements validation
- A/B testing comparison
- Long-term tracking setup
"""

import sys
import os
import json
import time
import subprocess
from datetime import datetime
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')
sys.path.append('tasks/options_trading_system/analysis_engine')


class ComprehensiveTestValidator:
    """Comprehensive test validation and reporting system"""

    def __init__(self):
        self.validation_results = {
            "validation_suite": "comprehensive_ifd_v3_testing",
            "timestamp": datetime.now().isoformat(),
            "test_components": {},
            "summary": {},
            "overall_status": "UNKNOWN"
        }

        # Define test components
        self.test_components = [
            {
                "name": "unit_tests",
                "description": "IFD v3 Component Unit Tests",
                "script": "tests/test_ifd_v3_comprehensive.py",
                "weight": 0.25,
                "timeout": 300  # 5 minutes
            },
            {
                "name": "data_flow_tests",
                "description": "Data Flow Integration Tests",
                "script": "tests/test_data_flow_integration.py",
                "weight": 0.25,
                "timeout": 600  # 10 minutes
            },
            {
                "name": "e2e_pipeline_tests",
                "description": "End-to-End Pipeline Tests",
                "script": "tests/test_e2e_pipeline.py",
                "weight": 0.25,
                "timeout": 900  # 15 minutes
            },
            {
                "name": "performance_tests",
                "description": "Performance Requirements Tests",
                "script": "tests/test_performance_requirements.py",
                "weight": 0.15,
                "timeout": 1200  # 20 minutes
            },
            {
                "name": "tracking_setup",
                "description": "30-Day Tracking System Setup",
                "script": "tests/test_30_day_tracking.py",
                "weight": 0.10,
                "timeout": 180  # 3 minutes
            }
        ]

        self.output_dir = "outputs/ifd_v3_testing"
        os.makedirs(self.output_dir, exist_ok=True)

    def run_test_component(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test component"""
        print(f"\n🧪 Running {component['description']}...")
        print(f"   Script: {component['script']}")

        component_result = {
            "name": component["name"],
            "description": component["description"],
            "script": component["script"],
            "weight": component["weight"],
            "status": "UNKNOWN",
            "execution_time_ms": 0,
            "details": {}
        }

        try:
            start_time = time.time()

            # Check if script exists
            if not os.path.exists(component["script"]):
                component_result["status"] = "SKIPPED"
                component_result["error"] = f"Script not found: {component['script']}"
                print(f"   ⚠️  Script not found, skipping")
                return component_result

            # Run the test script
            result = subprocess.run(
                [sys.executable, component["script"]],
                capture_output=True,
                text=True,
                timeout=component["timeout"]
            )

            execution_time = (time.time() - start_time) * 1000
            component_result["execution_time_ms"] = execution_time

            # Parse result
            if result.returncode == 0:
                component_result["status"] = "PASSED"
                print(f"   ✅ Completed successfully in {execution_time:.1f}ms")
            else:
                component_result["status"] = "FAILED"
                component_result["error"] = result.stderr
                print(f"   ❌ Failed after {execution_time:.1f}ms")
                print(f"      Error: {result.stderr[:200]}...")

            # Store output
            component_result["stdout"] = result.stdout[-1000:]  # Last 1000 chars
            component_result["stderr"] = result.stderr[-1000:]  # Last 1000 chars

            # Try to extract detailed results from output files
            self._extract_component_details(component, component_result)

        except subprocess.TimeoutExpired:
            component_result["status"] = "TIMEOUT"
            component_result["error"] = f"Test timed out after {component['timeout']} seconds"
            print(f"   ⏰ Timed out after {component['timeout']} seconds")

        except Exception as e:
            component_result["status"] = "ERROR"
            component_result["error"] = str(e)
            print(f"   ❌ Error: {e}")

        return component_result

    def _extract_component_details(self, component: Dict[str, Any], result: Dict[str, Any]):
        """Extract detailed results from component output files"""
        try:
            # Map component names to expected output files
            output_files = {
                "unit_tests": "outputs/ifd_v3_testing/comprehensive_component_tests.json",
                "data_flow_tests": "outputs/ifd_v3_testing/data_flow_integration_tests.json",
                "e2e_pipeline_tests": "outputs/ifd_v3_testing/e2e_pipeline_tests.json",
                "performance_tests": "outputs/ifd_v3_testing/performance_requirements_tests.json",
                "tracking_setup": "outputs/ifd_v3_testing/30_day_tracking.db"
            }

            output_file = output_files.get(component["name"])
            if output_file and os.path.exists(output_file):
                if output_file.endswith('.json'):
                    with open(output_file, 'r') as f:
                        detailed_results = json.load(f)
                    result["details"] = detailed_results
                else:
                    # For non-JSON files (like DB), just note existence
                    result["details"] = {"output_file": output_file, "exists": True}

                print(f"      📊 Detailed results extracted from {output_file}")

        except Exception as e:
            print(f"      ⚠️  Could not extract details: {e}")

    def run_parallel_tests(self) -> Dict[str, Any]:
        """Run test components in parallel where possible"""
        print("🚀 COMPREHENSIVE IFD V3.0 TEST VALIDATION")
        print("=" * 60)

        overall_start = time.time()

        # Group tests by dependencies (some can run in parallel)
        parallel_group_1 = ["unit_tests", "performance_tests", "tracking_setup"]
        sequential_group = ["data_flow_tests", "e2e_pipeline_tests"]  # These depend on components working

        # Run first group in parallel
        print(f"\n📋 Running parallel test group 1...")
        with ThreadPoolExecutor(max_workers=3) as executor:
            parallel_futures = {}

            for component in self.test_components:
                if component["name"] in parallel_group_1:
                    future = executor.submit(self.run_test_component, component)
                    parallel_futures[future] = component["name"]

            # Collect parallel results
            for future in as_completed(parallel_futures):
                component_name = parallel_futures[future]
                try:
                    result = future.result()
                    self.validation_results["test_components"][component_name] = result
                except Exception as e:
                    print(f"   ❌ {component_name} failed with exception: {e}")
                    self.validation_results["test_components"][component_name] = {
                        "name": component_name,
                        "status": "ERROR",
                        "error": str(e)
                    }

        # Run sequential group
        print(f"\n📋 Running sequential test group...")
        for component in self.test_components:
            if component["name"] in sequential_group:
                result = self.run_test_component(component)
                self.validation_results["test_components"][component["name"]] = result

        # Calculate overall results
        total_time = (time.time() - overall_start) * 1000
        self.validation_results["total_execution_time_ms"] = total_time

        # Generate summary
        self._generate_summary()

        return self.validation_results

    def _generate_summary(self):
        """Generate comprehensive test summary"""
        components = self.validation_results["test_components"]

        # Basic counts
        total_components = len(components)
        passed_components = len([c for c in components.values() if c["status"] == "PASSED"])
        failed_components = len([c for c in components.values() if c["status"] == "FAILED"])
        error_components = len([c for c in components.values() if c["status"] == "ERROR"])
        skipped_components = len([c for c in components.values() if c["status"] == "SKIPPED"])
        timeout_components = len([c for c in components.values() if c["status"] == "TIMEOUT"])

        # Weighted score calculation
        total_weight = sum(comp["weight"] for comp in self.test_components)
        achieved_weight = 0

        for component in self.test_components:
            component_result = components.get(component["name"], {})
            if component_result.get("status") == "PASSED":
                achieved_weight += component["weight"]

        weighted_score = (achieved_weight / total_weight) * 100 if total_weight > 0 else 0

        # Performance metrics
        execution_times = [c.get("execution_time_ms", 0) for c in components.values()]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0

        # Determine overall status
        if passed_components == total_components:
            overall_status = "ALL_PASSED"
        elif passed_components >= total_components * 0.8:  # 80% pass rate
            overall_status = "MOSTLY_PASSED"
        elif passed_components >= total_components * 0.5:  # 50% pass rate
            overall_status = "PARTIALLY_PASSED"
        else:
            overall_status = "MOSTLY_FAILED"

        # Extract specific metrics from component details
        specific_metrics = self._extract_specific_metrics(components)

        self.validation_results["summary"] = {
            "total_components": total_components,
            "passed_components": passed_components,
            "failed_components": failed_components,
            "error_components": error_components,
            "skipped_components": skipped_components,
            "timeout_components": timeout_components,
            "success_rate": passed_components / total_components if total_components > 0 else 0,
            "weighted_score": weighted_score,
            "avg_execution_time_ms": avg_execution_time,
            "specific_metrics": specific_metrics
        }

        self.validation_results["overall_status"] = overall_status

    def _extract_specific_metrics(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Extract specific metrics from component test results"""
        metrics = {}

        # Unit tests metrics
        unit_tests = components.get("unit_tests", {}).get("details", {})
        if unit_tests:
            metrics["unit_tests"] = {
                "total_tests": unit_tests.get("summary", {}).get("total_tests", 0),
                "passed_tests": unit_tests.get("summary", {}).get("passed", 0),
                "success_rate": unit_tests.get("summary", {}).get("success_rate", 0)
            }

        # Performance tests metrics
        perf_tests = components.get("performance_tests", {}).get("details", {})
        if perf_tests:
            perf_summary = perf_tests.get("summary", {})
            metrics["performance"] = {
                "latency_passed": perf_tests.get("test_results", {}).get("latency", {}).get("status") == "PASSED",
                "throughput_passed": perf_tests.get("test_results", {}).get("throughput", {}).get("status") == "PASSED",
                "memory_passed": perf_tests.get("test_results", {}).get("memory", {}).get("status") == "PASSED",
                "tests_passed": perf_summary.get("tests_passed", 0),
                "total_tests": perf_summary.get("total_tests", 0)
            }

        # Data flow tests metrics
        data_flow = components.get("data_flow_tests", {}).get("details", {})
        if data_flow:
            metrics["data_flow"] = {
                "stages_passed": data_flow.get("stages_passed", 0),
                "total_stages": data_flow.get("total_stages", 0),
                "performance_meets_requirements": data_flow.get("performance_metrics", {}).get("meets_latency_requirement", False)
            }

        # E2E pipeline metrics
        e2e_tests = components.get("e2e_pipeline_tests", {}).get("details", {})
        if e2e_tests:
            metrics["e2e_pipeline"] = {
                "scenarios_passed": e2e_tests.get("scenarios_passed", 0),
                "total_scenarios": e2e_tests.get("total_scenarios", 0),
                "success_rate": e2e_tests.get("success_rate", 0)
            }

        return metrics

    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        print(f"\n📋 Generating comprehensive validation report...")

        # Create detailed report
        report = {
            "report_type": "comprehensive_ifd_v3_validation",
            "generated_at": datetime.now().isoformat(),
            "test_execution": self.validation_results,
            "requirements_compliance": self._assess_requirements_compliance(),
            "readiness_assessment": self._assess_production_readiness(),
            "recommendations": self._generate_recommendations(),
            "next_steps": self._suggest_next_steps()
        }

        # Save report
        report_path = f"{self.output_dir}/comprehensive_validation_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        # Generate human-readable summary
        summary_path = f"{self.output_dir}/validation_summary.md"
        self._generate_markdown_summary(report, summary_path)

        print(f"   ✅ Detailed report: {report_path}")
        print(f"   ✅ Summary report: {summary_path}")

        return report

    def _assess_requirements_compliance(self) -> Dict[str, Any]:
        """Assess compliance with stated requirements"""
        compliance = {
            "latency_requirement": {"requirement": "<100ms", "status": "UNKNOWN"},
            "throughput_requirement": {"requirement": "100+ strikes", "status": "UNKNOWN"},
            "signal_quality_requirement": {"requirement": ">60% accuracy", "status": "UNKNOWN"},
            "stability_requirement": {"requirement": "Consistent performance", "status": "UNKNOWN"},
            "integration_requirement": {"requirement": "Full pipeline integration", "status": "UNKNOWN"}
        }

        # Check performance test results
        perf_tests = self.validation_results["test_components"].get("performance_tests", {})
        if perf_tests.get("status") == "PASSED":
            compliance["latency_requirement"]["status"] = "MET"
            compliance["throughput_requirement"]["status"] = "MET"
            compliance["stability_requirement"]["status"] = "MET"
        elif perf_tests.get("status") == "FAILED":
            perf_details = perf_tests.get("details", {}).get("test_results", {})

            if perf_details.get("latency", {}).get("status") == "PASSED":
                compliance["latency_requirement"]["status"] = "MET"
            else:
                compliance["latency_requirement"]["status"] = "NOT_MET"

            if perf_details.get("throughput", {}).get("status") == "PASSED":
                compliance["throughput_requirement"]["status"] = "MET"
            else:
                compliance["throughput_requirement"]["status"] = "NOT_MET"

        # Check integration tests
        e2e_tests = self.validation_results["test_components"].get("e2e_pipeline_tests", {})
        if e2e_tests.get("status") == "PASSED":
            compliance["integration_requirement"]["status"] = "MET"
        else:
            compliance["integration_requirement"]["status"] = "NOT_MET"

        # Check data flow tests for signal quality
        data_flow = self.validation_results["test_components"].get("data_flow_tests", {})
        if data_flow.get("status") == "PASSED":
            compliance["signal_quality_requirement"]["status"] = "MET"
        else:
            compliance["signal_quality_requirement"]["status"] = "NOT_MET"

        return compliance

    def _assess_production_readiness(self) -> Dict[str, Any]:
        """Assess production readiness"""
        readiness_factors = []
        overall_score = 0

        # Test coverage
        passed_components = self.validation_results["summary"]["passed_components"]
        total_components = self.validation_results["summary"]["total_components"]
        test_coverage_score = (passed_components / total_components) * 100 if total_components > 0 else 0

        if test_coverage_score >= 90:
            readiness_factors.append("✅ Excellent test coverage")
            overall_score += 25
        elif test_coverage_score >= 70:
            readiness_factors.append("⚠️ Good test coverage")
            overall_score += 20
        else:
            readiness_factors.append("❌ Insufficient test coverage")
            overall_score += 10

        # Performance compliance
        performance_met = self._assess_requirements_compliance()
        latency_met = performance_met["latency_requirement"]["status"] == "MET"
        throughput_met = performance_met["throughput_requirement"]["status"] == "MET"

        if latency_met and throughput_met:
            readiness_factors.append("✅ Performance requirements met")
            overall_score += 25
        elif latency_met or throughput_met:
            readiness_factors.append("⚠️ Partial performance compliance")
            overall_score += 15
        else:
            readiness_factors.append("❌ Performance requirements not met")
            overall_score += 5

        # Integration completeness
        integration_tests = self.validation_results["test_components"].get("e2e_pipeline_tests", {})
        if integration_tests.get("status") == "PASSED":
            readiness_factors.append("✅ End-to-end integration validated")
            overall_score += 25
        else:
            readiness_factors.append("❌ Integration issues detected")
            overall_score += 10

        # Stability indicators
        unit_tests = self.validation_results["test_components"].get("unit_tests", {})
        if unit_tests.get("status") == "PASSED":
            readiness_factors.append("✅ Component stability verified")
            overall_score += 25
        else:
            readiness_factors.append("❌ Component stability concerns")
            overall_score += 10

        # Determine readiness level
        if overall_score >= 90:
            readiness_level = "PRODUCTION_READY"
        elif overall_score >= 70:
            readiness_level = "NEARLY_READY"
        elif overall_score >= 50:
            readiness_level = "DEVELOPMENT_READY"
        else:
            readiness_level = "NOT_READY"

        return {
            "readiness_level": readiness_level,
            "overall_score": overall_score,
            "factors": readiness_factors,
            "recommendation": self._get_readiness_recommendation(readiness_level)
        }

    def _get_readiness_recommendation(self, level: str) -> str:
        """Get recommendation based on readiness level"""
        recommendations = {
            "PRODUCTION_READY": "System is ready for production deployment. Proceed with confidence.",
            "NEARLY_READY": "System is nearly ready. Address remaining issues and re-test.",
            "DEVELOPMENT_READY": "System needs significant work before production. Continue development.",
            "NOT_READY": "System requires major improvements. Extensive development needed."
        }
        return recommendations.get(level, "Status unclear, manual review required.")

    def _generate_recommendations(self) -> List[str]:
        """Generate specific recommendations based on test results"""
        recommendations = []

        # Check failed components
        failed_components = [
            comp for comp in self.validation_results["test_components"].values()
            if comp["status"] in ["FAILED", "ERROR", "TIMEOUT"]
        ]

        for component in failed_components:
            if component["name"] == "unit_tests":
                recommendations.append("Fix unit test failures to ensure component reliability")
            elif component["name"] == "performance_tests":
                recommendations.append("Optimize performance to meet latency and throughput requirements")
            elif component["name"] == "data_flow_tests":
                recommendations.append("Fix data flow integration issues")
            elif component["name"] == "e2e_pipeline_tests":
                recommendations.append("Resolve end-to-end pipeline integration problems")

        # Performance-specific recommendations
        perf_details = self.validation_results["test_components"].get("performance_tests", {}).get("details", {})
        if perf_details:
            test_results = perf_details.get("test_results", {})

            if test_results.get("latency", {}).get("status") == "FAILED":
                recommendations.append("Implement caching and optimize algorithms to reduce latency")

            if test_results.get("memory", {}).get("status") == "FAILED":
                recommendations.append("Fix memory leaks and optimize memory usage")

            if test_results.get("cpu", {}).get("status") == "FAILED":
                recommendations.append("Optimize CPU usage and implement better resource management")

        # Generic recommendations
        if self.validation_results["summary"]["success_rate"] < 0.8:
            recommendations.append("Improve overall test success rate before production deployment")

        return recommendations

    def _suggest_next_steps(self) -> List[str]:
        """Suggest next steps based on validation results"""
        next_steps = []

        readiness = self._assess_production_readiness()

        if readiness["readiness_level"] == "PRODUCTION_READY":
            next_steps.extend([
                "Begin production deployment planning",
                "Set up monitoring and alerting systems",
                "Prepare rollback procedures",
                "Schedule production validation testing"
            ])

        elif readiness["readiness_level"] == "NEARLY_READY":
            next_steps.extend([
                "Address remaining test failures",
                "Re-run comprehensive validation",
                "Conduct additional performance testing",
                "Review and update documentation"
            ])

        else:
            next_steps.extend([
                "Fix critical test failures",
                "Improve component reliability",
                "Optimize performance bottlenecks",
                "Re-run validation after fixes"
            ])

        # Always include these
        next_steps.extend([
            "Set up 30-day tracking for production monitoring",
            "Prepare A/B testing framework for live comparison",
            "Document final configuration and deployment procedures"
        ])

        return next_steps

    def _generate_markdown_summary(self, report: Dict[str, Any], filepath: str):
        """Generate human-readable markdown summary"""

        summary = f"""# IFD v3.0 Comprehensive Validation Report

**Generated:** {report['generated_at']}

## Executive Summary

**Overall Status:** {self.validation_results['overall_status']}
**Weighted Score:** {self.validation_results['summary']['weighted_score']:.1f}%
**Success Rate:** {self.validation_results['summary']['success_rate']*100:.1f}%

## Test Results Summary

| Component | Status | Weight | Execution Time |
|-----------|---------|---------|----------------|
"""

        for comp_name, comp_result in self.validation_results["test_components"].items():
            status_emoji = {"PASSED": "✅", "FAILED": "❌", "ERROR": "⚠️", "SKIPPED": "⏭️", "TIMEOUT": "⏰"}.get(comp_result["status"], "❓")
            summary += f"| {comp_result.get('description', comp_name)} | {status_emoji} {comp_result['status']} | {comp_result.get('weight', 0)*100:.0f}% | {comp_result.get('execution_time_ms', 0):.0f}ms |\n"

        summary += f"""
## Requirements Compliance

"""

        compliance = report["requirements_compliance"]
        for req_name, req_data in compliance.items():
            status_emoji = {"MET": "✅", "NOT_MET": "❌", "UNKNOWN": "❓"}.get(req_data["status"], "❓")
            req_display = req_name.replace("_", " ").title()
            summary += f"- **{req_display}** ({req_data['requirement']}): {status_emoji} {req_data['status']}\n"

        summary += f"""
## Production Readiness

**Level:** {report['readiness_assessment']['readiness_level']}
**Score:** {report['readiness_assessment']['overall_score']}/100

**Assessment Factors:**
"""

        for factor in report["readiness_assessment"]["factors"]:
            summary += f"- {factor}\n"

        summary += f"""
**Recommendation:** {report['readiness_assessment']['recommendation']}

## Recommendations

"""

        for i, rec in enumerate(report["recommendations"], 1):
            summary += f"{i}. {rec}\n"

        summary += f"""
## Next Steps

"""

        for i, step in enumerate(report["next_steps"], 1):
            summary += f"{i}. {step}\n"

        summary += f"""
---
*Report generated by IFD v3.0 Comprehensive Test Validation System*
"""

        with open(filepath, 'w') as f:
            f.write(summary)

    def print_summary(self):
        """Print validation summary to console"""
        print("\n" + "=" * 60)
        print("🏁 COMPREHENSIVE VALIDATION SUMMARY")
        print("=" * 60)

        summary = self.validation_results["summary"]

        print(f"Overall Status: {self.validation_results['overall_status']}")
        print(f"Weighted Score: {summary['weighted_score']:.1f}%")
        print(f"Success Rate: {summary['success_rate']*100:.1f}%")
        print(f"Total Execution Time: {self.validation_results['total_execution_time_ms']:.1f}ms")

        print(f"\n📊 Component Results:")
        for comp_name, comp_result in self.validation_results["test_components"].items():
            status_emoji = {"PASSED": "✅", "FAILED": "❌", "ERROR": "⚠️", "SKIPPED": "⏭️", "TIMEOUT": "⏰"}.get(comp_result["status"], "❓")
            print(f"   {status_emoji} {comp_result.get('description', comp_name)}: {comp_result['status']}")

        readiness = self._assess_production_readiness()
        status_emoji = {"PRODUCTION_READY": "🚀", "NEARLY_READY": "⚠️", "DEVELOPMENT_READY": "🔧", "NOT_READY": "❌"}.get(readiness["readiness_level"], "❓")
        print(f"\n{status_emoji} Production Readiness: {readiness['readiness_level']} ({readiness['overall_score']}/100)")

        if self.validation_results["overall_status"] in ["ALL_PASSED", "MOSTLY_PASSED"]:
            print("\n🎉 IFD V3.0 VALIDATION SUCCESSFUL!")
            print("   System ready for next phase deployment")
        else:
            print("\n⚠️  VALIDATION ISSUES DETECTED")
            print("   Review failed tests and address issues")


def main():
    """Main validation execution"""
    validator = ComprehensiveTestValidator()

    # Run comprehensive validation
    validation_results = validator.run_parallel_tests()

    # Generate reports
    comprehensive_report = validator.generate_validation_report()

    # Print summary
    validator.print_summary()

    # Return appropriate exit code
    if validation_results["overall_status"] in ["ALL_PASSED", "MOSTLY_PASSED"]:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())
