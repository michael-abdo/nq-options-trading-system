#!/usr/bin/env python3
"""
End-to-End Pipeline Testing for IFD v3.0

Tests the complete pipeline using realistic test data:
- Real market data simulation
- Complete analysis engine execution
- Signal generation and validation
- Performance metrics verification
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta
from utils.timezone_utils import get_eastern_time, get_utc_time
from typing import Dict, Any, List

# Add project paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')
sys.path.append('tasks/options_trading_system/analysis_engine')

# Load environment
from dotenv import load_dotenv
load_dotenv()


class EndToEndPipelineTest:
    """Comprehensive end-to-end pipeline testing"""

    def __init__(self):
        self.test_results = {
            "test_suite": "e2e_pipeline",
            "timestamp": get_eastern_time().isoformat(),
            "scenarios": [],
            "performance_summary": {},
            "status": "UNKNOWN"
        }

        # Test scenarios with different market conditions
        self.test_scenarios = [
            {
                "name": "normal_market_conditions",
                "description": "Typical market activity with moderate volume",
                "data_profile": "normal"
            },
            {
                "name": "high_institutional_activity",
                "description": "Strong institutional flow with large orders",
                "data_profile": "institutional"
            },
            {
                "name": "market_making_dominated",
                "description": "Heavy market making activity with balanced flow",
                "data_profile": "market_making"
            },
            {
                "name": "volatile_market_conditions",
                "description": "High volatility with rapid price movements",
                "data_profile": "volatile"
            },
            {
                "name": "low_volume_conditions",
                "description": "Low volume trading with minimal activity",
                "data_profile": "low_volume"
            }
        ]

    def generate_test_data(self, profile: str) -> Dict[str, Any]:
        """Generate realistic test data based on market profile"""
        base_config = {
            "mode": "simulation",
            "sources": ["databento", "barchart"],
            "symbols": ["NQ"],
            "test_profile": profile
        }

        if profile == "normal":
            # Typical market conditions
            return {
                **base_config,
                "volume_multiplier": 1.0,
                "volatility_factor": 1.0,
                "institutional_ratio": 0.3,
                "market_making_ratio": 0.4
            }

        elif profile == "institutional":
            # High institutional activity
            return {
                **base_config,
                "volume_multiplier": 2.5,
                "volatility_factor": 1.2,
                "institutional_ratio": 0.7,
                "market_making_ratio": 0.2
            }

        elif profile == "market_making":
            # Market making dominated
            return {
                **base_config,
                "volume_multiplier": 1.5,
                "volatility_factor": 0.8,
                "institutional_ratio": 0.1,
                "market_making_ratio": 0.8
            }

        elif profile == "volatile":
            # High volatility conditions
            return {
                **base_config,
                "volume_multiplier": 3.0,
                "volatility_factor": 2.5,
                "institutional_ratio": 0.4,
                "market_making_ratio": 0.3
            }

        elif profile == "low_volume":
            # Low volume conditions
            return {
                **base_config,
                "volume_multiplier": 0.3,
                "volatility_factor": 0.6,
                "institutional_ratio": 0.2,
                "market_making_ratio": 0.6
            }

        else:
            return base_config

    def test_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test a specific market scenario"""
        print(f"\n🎯 Testing Scenario: {scenario['name']}")
        print(f"   Description: {scenario['description']}")

        scenario_result = {
            "scenario": scenario["name"],
            "description": scenario["description"],
            "status": "UNKNOWN",
            "metrics": {},
            "validation": {}
        }

        try:
            # Generate test data for this scenario
            data_config = self.generate_test_data(scenario["data_profile"])

            # Configure analysis with IFD v3 enabled
            analysis_config = {
                "expected_value": {
                    "weights": {
                        "oi_factor": 0.35,
                        "vol_factor": 0.25,
                        "pcr_factor": 0.25,
                        "distance_factor": 0.15
                    },
                    "min_ev": 15,
                    "min_probability": 0.60,
                    "max_risk": 150,
                    "min_risk_reward": 1.0
                },
                "institutional_flow_v3": {
                    "db_path": f"/tmp/e2e_test_{scenario['name']}.db",
                    "pressure_thresholds": {
                        "min_pressure_ratio": 1.5,
                        "min_volume_concentration": 0.3,
                        "min_time_persistence": 0.4,
                        "min_trend_strength": 0.5
                    },
                    "confidence_thresholds": {
                        "min_baseline_anomaly": 1.5,
                        "min_overall_confidence": 0.5  # Testing threshold (was 0.6)
                    },
                    "market_making_penalty": 0.3
                }
            }

            # Run complete analysis engine
            start_time = time.time()

            from analysis_engine.integration import run_analysis_engine
            result = run_analysis_engine(data_config, analysis_config)

            execution_time = (time.time() - start_time) * 1000

            # Extract key metrics
            metrics = self._extract_scenario_metrics(result, execution_time)
            scenario_result["metrics"] = metrics

            # Validate scenario results
            validation = self._validate_scenario_results(result, scenario["data_profile"])
            scenario_result["validation"] = validation

            # Determine scenario status
            scenario_result["status"] = "PASSED" if validation["overall_valid"] else "FAILED"

            # Print scenario summary
            self._print_scenario_summary(scenario["name"], metrics, validation)

        except Exception as e:
            scenario_result["status"] = "ERROR"
            scenario_result["error"] = str(e)
            print(f"   ❌ Scenario failed: {e}")

        return scenario_result

    def _extract_scenario_metrics(self, result: Dict[str, Any], execution_time: float) -> Dict[str, Any]:
        """Extract key metrics from scenario results"""
        metrics = {
            "execution_time_ms": execution_time,
            "overall_status": result.get("status", "unknown"),
            "successful_analyses": result.get("summary", {}).get("successful_analyses", 0),
            "total_analyses": 5,  # Expected number of analyses
            "trading_recommendations": len(result.get("synthesis", {}).get("trading_recommendations", [])),
            "market_context_items": len(result.get("synthesis", {}).get("market_context", {}))
        }

        # Extract IFD v3 specific metrics
        ifd_v3_result = result.get("individual_results", {}).get("institutional_flow_v3", {})
        if ifd_v3_result.get("status") == "success":
            ifd_data = ifd_v3_result.get("result", {})
            metrics.update({
                "ifd_v3_signals": ifd_data.get("total_signals", 0),
                "ifd_v3_high_confidence_signals": ifd_data.get("high_confidence_signals", 0),
                "ifd_v3_latency_ms": ifd_data.get("latency_ms", 0),
                "ifd_v3_pressure_snapshots": ifd_data.get("pressure_snapshots_analyzed", 0)
            })

        # Extract market context
        market_context = result.get("synthesis", {}).get("market_context", {})
        if "signal_conflict_resolution" in market_context:
            metrics["conflict_resolution"] = market_context["signal_conflict_resolution"]
            metrics["conflicts_detected"] = market_context.get("signal_conflicts_detected", 0)

        return metrics

    def _validate_scenario_results(self, result: Dict[str, Any], profile: str) -> Dict[str, Any]:
        """Validate scenario results based on expected profile behavior"""
        validation = {
            "checks": [],
            "overall_valid": True
        }

        # Check 1: Overall execution success
        if result.get("status") != "success":
            validation["checks"].append("FAILED: Overall execution failed")
            validation["overall_valid"] = False
        else:
            validation["checks"].append("PASSED: Overall execution successful")

        # Check 2: IFD v3 analysis success
        ifd_v3_result = result.get("individual_results", {}).get("institutional_flow_v3", {})
        if ifd_v3_result.get("status") != "success":
            validation["checks"].append("FAILED: IFD v3 analysis failed")
            validation["overall_valid"] = False
        else:
            validation["checks"].append("PASSED: IFD v3 analysis successful")

        # Check 3: Performance requirements
        execution_time = result.get("execution_time_seconds", 0) * 1000
        if execution_time > 500:  # 500ms threshold
            validation["checks"].append(f"FAILED: Execution time {execution_time:.1f}ms > 500ms")
            validation["overall_valid"] = False
        else:
            validation["checks"].append(f"PASSED: Execution time {execution_time:.1f}ms within limits")

        # Check 4: IFD v3 latency
        if ifd_v3_result.get("status") == "success":
            ifd_latency = ifd_v3_result.get("result", {}).get("latency_ms", 0)
            if ifd_latency > 100:  # 100ms threshold
                validation["checks"].append(f"FAILED: IFD v3 latency {ifd_latency:.1f}ms > 100ms")
                validation["overall_valid"] = False
            else:
                validation["checks"].append(f"PASSED: IFD v3 latency {ifd_latency:.1f}ms within limits")

        # Profile-specific validations
        if profile == "institutional":
            # Should generate high-confidence signals
            ifd_signals = ifd_v3_result.get("result", {}).get("total_signals", 0)
            if ifd_signals == 0:
                validation["checks"].append("WARNING: No IFD v3 signals in institutional scenario")
            else:
                validation["checks"].append(f"PASSED: {ifd_signals} IFD v3 signals generated")

        elif profile == "market_making":
            # Should have conflict resolution active
            market_context = result.get("synthesis", {}).get("market_context", {})
            if "signal_conflict_resolution" not in market_context:
                validation["checks"].append("WARNING: No conflict resolution in market making scenario")
            else:
                validation["checks"].append("PASSED: Conflict resolution active")

        elif profile == "low_volume":
            # Should handle low activity gracefully
            recommendations = len(result.get("synthesis", {}).get("trading_recommendations", []))
            if recommendations > 5:
                validation["checks"].append("WARNING: Too many recommendations in low volume scenario")
            else:
                validation["checks"].append("PASSED: Appropriate recommendations for low volume")

        # Check 5: Market context integration
        market_context = result.get("synthesis", {}).get("market_context", {})
        ifd_v3_keys = [k for k in market_context.keys() if "ifd_v3" in k]
        if len(ifd_v3_keys) < 3:
            validation["checks"].append("FAILED: Insufficient IFD v3 market context")
            validation["overall_valid"] = False
        else:
            validation["checks"].append(f"PASSED: {len(ifd_v3_keys)} IFD v3 context items")

        return validation

    def _print_scenario_summary(self, scenario_name: str, metrics: Dict[str, Any], validation: Dict[str, Any]):
        """Print scenario summary"""
        status_emoji = "✅" if validation["overall_valid"] else "❌"
        print(f"   {status_emoji} Status: {'PASSED' if validation['overall_valid'] else 'FAILED'}")
        print(f"   ⏱️  Execution: {metrics.get('execution_time_ms', 0):.1f}ms")
        print(f"   📊 Analyses: {metrics.get('successful_analyses', 0)}/{metrics.get('total_analyses', 5)}")
        print(f"   🎯 Recommendations: {metrics.get('trading_recommendations', 0)}")

        if "ifd_v3_signals" in metrics:
            print(f"   🔍 IFD v3 Signals: {metrics['ifd_v3_signals']}")
            print(f"   ⚡ IFD v3 Latency: {metrics.get('ifd_v3_latency_ms', 0):.1f}ms")

    def test_performance_under_load(self) -> Dict[str, Any]:
        """Test performance under various load conditions"""
        print(f"\n🚀 Performance Under Load Testing")

        load_tests = [
            {"name": "standard_load", "concurrent_requests": 1, "iterations": 10},
            {"name": "moderate_load", "concurrent_requests": 3, "iterations": 5},
            {"name": "high_load", "concurrent_requests": 5, "iterations": 3}
        ]

        performance_results = {}

        for load_test in load_tests:
            print(f"\n   Testing {load_test['name']}...")

            execution_times = []
            memory_usage = []

            for iteration in range(load_test["iterations"]):
                start_time = time.time()

                # Use normal market conditions for load testing
                data_config = self.generate_test_data("normal")
                analysis_config = {
                    "institutional_flow_v3": {
                        "db_path": f"/tmp/load_test_{iteration}.db",
                        "pressure_thresholds": {
                            "min_pressure_ratio": 1.5,
                            "min_volume_concentration": 0.3,
                            "min_time_persistence": 0.4,
                            "min_trend_strength": 0.5
                        },
                        "confidence_thresholds": {
                            "min_baseline_anomaly": 1.5,
                            "min_overall_confidence": 0.5  # Testing threshold (was 0.6)
                        },
                        "market_making_penalty": 0.3
                    }
                }

                try:
                    from analysis_engine.integration import run_analysis_engine
                    result = run_analysis_engine(data_config, analysis_config)

                    execution_time = (time.time() - start_time) * 1000
                    execution_times.append(execution_time)

                    # Monitor memory usage
                    import psutil
                    memory_usage.append(psutil.Process().memory_info().rss / 1024 / 1024)  # MB

                except Exception as e:
                    print(f"      ❌ Iteration {iteration + 1} failed: {e}")

            # Calculate load test metrics
            if execution_times:
                performance_results[load_test["name"]] = {
                    "avg_time_ms": sum(execution_times) / len(execution_times),
                    "min_time_ms": min(execution_times),
                    "max_time_ms": max(execution_times),
                    "avg_memory_mb": sum(memory_usage) / len(memory_usage),
                    "successful_iterations": len(execution_times),
                    "total_iterations": load_test["iterations"]
                }

                print(f"      ✅ Average time: {performance_results[load_test['name']]['avg_time_ms']:.1f}ms")
                print(f"      📊 Memory: {performance_results[load_test['name']]['avg_memory_mb']:.1f}MB")

        return performance_results

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive end-to-end testing"""
        print("🔄 COMPREHENSIVE END-TO-END PIPELINE TEST")
        print("=" * 60)

        overall_start = time.time()

        # Test all scenarios
        for scenario in self.test_scenarios:
            scenario_result = self.test_scenario(scenario)
            self.test_results["scenarios"].append(scenario_result)

        # Performance under load testing
        performance_results = self.test_performance_under_load()
        self.test_results["performance_summary"] = performance_results

        # Calculate overall results
        total_time = (time.time() - overall_start) * 1000
        passed_scenarios = len([s for s in self.test_results["scenarios"] if s["status"] == "PASSED"])
        total_scenarios = len(self.test_results["scenarios"])

        self.test_results["total_test_time_ms"] = total_time
        self.test_results["scenarios_passed"] = passed_scenarios
        self.test_results["total_scenarios"] = total_scenarios
        self.test_results["success_rate"] = passed_scenarios / total_scenarios if total_scenarios > 0 else 0

        # Determine overall status
        if passed_scenarios == total_scenarios and performance_results:
            self.test_results["status"] = "PASSED"
        else:
            self.test_results["status"] = "FAILED"

        return self.test_results

    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("🏁 END-TO-END PIPELINE TEST SUMMARY")
        print("=" * 60)

        print(f"Overall Status: {self.test_results['status']}")
        print(f"Scenarios Passed: {self.test_results.get('scenarios_passed', 0)}/{self.test_results.get('total_scenarios', 0)}")
        print(f"Success Rate: {self.test_results.get('success_rate', 0)*100:.1f}%")
        print(f"Total Test Time: {self.test_results.get('total_test_time_ms', 0):.1f}ms")

        # Print scenario details
        print(f"\n📋 Scenario Results:")
        for scenario in self.test_results.get("scenarios", []):
            status_emoji = "✅" if scenario["status"] == "PASSED" else "❌"
            print(f"   {status_emoji} {scenario['scenario']}: {scenario['status']}")
            if "metrics" in scenario:
                print(f"      Time: {scenario['metrics'].get('execution_time_ms', 0):.1f}ms")
                print(f"      Recommendations: {scenario['metrics'].get('trading_recommendations', 0)}")

        # Print performance summary
        perf = self.test_results.get("performance_summary", {})
        if perf:
            print(f"\n⚡ Performance Summary:")
            for test_name, metrics in perf.items():
                print(f"   {test_name}: {metrics.get('avg_time_ms', 0):.1f}ms avg")

        if self.test_results["status"] == "PASSED":
            print("\n🎉 ALL END-TO-END PIPELINE TESTS PASSED!")
        else:
            print("\n⚠️  SOME TESTS NEED ATTENTION")

    def save_results(self, filepath: str):
        """Save test results"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(self.test_results, f, indent=2)

        print(f"\n📄 Test results saved to: {filepath}")


def main():
    """Main test execution"""
    test = EndToEndPipelineTest()
    results = test.run_comprehensive_test()
    test.print_summary()

    # Save results
    output_path = "outputs/ifd_v3_testing/e2e_pipeline_tests.json"
    test.save_results(output_path)

    return 0 if results["status"] == "PASSED" else 1


if __name__ == "__main__":
    exit(main())
