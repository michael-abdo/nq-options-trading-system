#!/usr/bin/env python3
"""
Performance Requirements Testing for IFD v3.0

Tests comprehensive performance requirements:
- Latency: <100ms per analysis
- Throughput: 100+ strikes simultaneously
- Streaming updates processing
- Memory efficiency
- Response time consistency
"""

import sys
import os
import json
import time
import threading
import statistics
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List
import psutil
import gc

# Add project paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')
sys.path.append('tasks/options_trading_system/analysis_engine')

# Load environment
from dotenv import load_dotenv
load_dotenv()


class PerformanceRequirementsTest:
    """Comprehensive performance requirements testing"""

    def __init__(self):
        self.test_results = {
            "test_suite": "performance_requirements",
            "timestamp": datetime.now().isoformat(),
            "requirements": {
                "max_latency_ms": 100,
                "min_throughput_strikes": 100,
                "max_memory_growth_mb": 50,
                "max_cpu_usage_percent": 80
            },
            "test_results": {},
            "overall_status": "UNKNOWN"
        }

        self.process = psutil.Process()

    def test_latency_requirements(self) -> Dict[str, Any]:
        """Test latency requirement: <100ms per analysis"""
        print("⚡ Testing Latency Requirements (<100ms per analysis)")

        latency_results = {
            "test_name": "latency_requirements",
            "requirement_ms": 100,
            "measurements": [],
            "status": "UNKNOWN"
        }

        try:
            # Test with different data sizes
            test_cases = [
                {"name": "small_dataset", "pressure_metrics": 5},
                {"name": "medium_dataset", "pressure_metrics": 15},
                {"name": "large_dataset", "pressure_metrics": 50},
                {"name": "xlarge_dataset", "pressure_metrics": 100}
            ]

            for test_case in test_cases:
                print(f"   Testing {test_case['name']} ({test_case['pressure_metrics']} metrics)...")

                # Generate test data
                pressure_metrics = self._generate_pressure_metrics(test_case["pressure_metrics"])

                # Run multiple measurements for statistical validity
                measurements = []
                for run in range(10):
                    start_time = time.time()

                    from institutional_flow_v3.solution import run_ifd_v3_analysis
                    config = self._get_test_config()

                    result = run_ifd_v3_analysis(pressure_metrics, config)

                    execution_time = (time.time() - start_time) * 1000  # ms
                    measurements.append(execution_time)

                # Calculate statistics
                avg_latency = statistics.mean(measurements)
                median_latency = statistics.median(measurements)
                p95_latency = statistics.quantiles(measurements, n=20)[18]  # 95th percentile
                max_latency = max(measurements)

                case_result = {
                    "test_case": test_case["name"],
                    "pressure_metrics_count": test_case["pressure_metrics"],
                    "measurements": measurements,
                    "avg_latency_ms": avg_latency,
                    "median_latency_ms": median_latency,
                    "p95_latency_ms": p95_latency,
                    "max_latency_ms": max_latency,
                    "meets_requirement": max_latency < 100
                }

                latency_results["measurements"].append(case_result)

                status_emoji = "✅" if case_result["meets_requirement"] else "❌"
                print(f"      {status_emoji} Avg: {avg_latency:.1f}ms, P95: {p95_latency:.1f}ms, Max: {max_latency:.1f}ms")

            # Determine overall latency status
            all_meet_requirement = all(m["meets_requirement"] for m in latency_results["measurements"])
            latency_results["status"] = "PASSED" if all_meet_requirement else "FAILED"

            # Calculate overall statistics
            all_measurements = []
            for measurement in latency_results["measurements"]:
                all_measurements.extend(measurement["measurements"])

            latency_results["overall_stats"] = {
                "total_measurements": len(all_measurements),
                "overall_avg_ms": statistics.mean(all_measurements),
                "overall_p95_ms": statistics.quantiles(all_measurements, n=20)[18],
                "overall_max_ms": max(all_measurements)
            }

            print(f"   📊 Overall: Avg {latency_results['overall_stats']['overall_avg_ms']:.1f}ms, "
                  f"P95 {latency_results['overall_stats']['overall_p95_ms']:.1f}ms")

        except Exception as e:
            latency_results["status"] = "ERROR"
            latency_results["error"] = str(e)
            print(f"   ❌ Latency test error: {e}")

        return latency_results

    def test_throughput_requirements(self) -> Dict[str, Any]:
        """Test throughput requirement: 100+ strikes simultaneously"""
        print("\n📊 Testing Throughput Requirements (100+ strikes)")

        throughput_results = {
            "test_name": "throughput_requirements",
            "requirement_strikes": 100,
            "measurements": [],
            "status": "UNKNOWN"
        }

        try:
            # Test with increasing numbers of strikes
            strike_counts = [50, 100, 150, 200, 300]

            for strike_count in strike_counts:
                print(f"   Testing {strike_count} strikes...")

                # Generate pressure metrics for all strikes
                pressure_metrics = []
                base_strike = 21000

                for i in range(strike_count):
                    strike = base_strike + (i * 5)  # Every 5 points
                    metrics = self._create_pressure_metric(
                        strike=float(strike),
                        option_type="CALL",
                        confidence=0.6 + (i % 10) * 0.02
                    )
                    pressure_metrics.append(metrics)

                # Measure processing time
                start_time = time.time()

                from institutional_flow_v3.solution import run_ifd_v3_analysis
                config = self._get_test_config()

                result = run_ifd_v3_analysis(pressure_metrics, config)

                processing_time = (time.time() - start_time) * 1000  # ms

                # Calculate throughput metrics
                strikes_per_second = strike_count / (processing_time / 1000)
                signals_generated = len(result.get("signals", []))

                measurement = {
                    "strike_count": strike_count,
                    "processing_time_ms": processing_time,
                    "strikes_per_second": strikes_per_second,
                    "signals_generated": signals_generated,
                    "meets_requirement": processing_time < 1000  # 1 second for 100+ strikes
                }

                throughput_results["measurements"].append(measurement)

                status_emoji = "✅" if measurement["meets_requirement"] else "❌"
                print(f"      {status_emoji} {strike_count} strikes in {processing_time:.1f}ms "
                      f"({strikes_per_second:.1f} strikes/sec)")

            # Determine overall throughput status
            hundred_plus_measurements = [m for m in throughput_results["measurements"] if m["strike_count"] >= 100]
            all_meet_requirement = all(m["meets_requirement"] for m in hundred_plus_measurements)
            throughput_results["status"] = "PASSED" if all_meet_requirement else "FAILED"

            # Find best throughput
            best_measurement = max(throughput_results["measurements"], key=lambda x: x["strikes_per_second"])
            throughput_results["best_throughput"] = {
                "strikes_per_second": best_measurement["strikes_per_second"],
                "strike_count": best_measurement["strike_count"],
                "processing_time_ms": best_measurement["processing_time_ms"]
            }

            print(f"   🏆 Best throughput: {best_measurement['strikes_per_second']:.1f} strikes/sec")

        except Exception as e:
            throughput_results["status"] = "ERROR"
            throughput_results["error"] = str(e)
            print(f"   ❌ Throughput test error: {e}")

        return throughput_results

    def test_streaming_updates_processing(self) -> Dict[str, Any]:
        """Test streaming updates processing performance"""
        print("\n🌊 Testing Streaming Updates Processing")

        streaming_results = {
            "test_name": "streaming_updates",
            "measurements": [],
            "status": "UNKNOWN"
        }

        try:
            # Simulate streaming data updates
            update_frequencies = [1, 5, 10, 20]  # Updates per second

            for frequency in update_frequencies:
                print(f"   Testing {frequency} updates/second...")

                updates_processed = 0
                processing_times = []
                start_test = time.time()
                test_duration = 5  # 5 seconds

                while (time.time() - start_test) < test_duration:
                    # Generate new pressure metric update
                    pressure_metrics = self._generate_pressure_metrics(10)  # 10 metrics per update

                    update_start = time.time()

                    from institutional_flow_v3.solution import run_ifd_v3_analysis
                    config = self._get_test_config()

                    result = run_ifd_v3_analysis(pressure_metrics, config)

                    update_time = (time.time() - update_start) * 1000
                    processing_times.append(update_time)
                    updates_processed += 1

                    # Maintain update frequency
                    time.sleep(1.0 / frequency)

                # Calculate streaming performance metrics
                actual_frequency = updates_processed / test_duration
                avg_processing_time = statistics.mean(processing_times)
                max_processing_time = max(processing_times)

                measurement = {
                    "target_frequency": frequency,
                    "actual_frequency": actual_frequency,
                    "updates_processed": updates_processed,
                    "avg_processing_time_ms": avg_processing_time,
                    "max_processing_time_ms": max_processing_time,
                    "can_maintain_frequency": max_processing_time < (1000 / frequency)
                }

                streaming_results["measurements"].append(measurement)

                status_emoji = "✅" if measurement["can_maintain_frequency"] else "❌"
                print(f"      {status_emoji} {actual_frequency:.1f} actual freq, "
                      f"{avg_processing_time:.1f}ms avg processing")

            # Determine streaming performance status
            all_maintain_frequency = all(m["can_maintain_frequency"] for m in streaming_results["measurements"])
            streaming_results["status"] = "PASSED" if all_maintain_frequency else "FAILED"

            # Find maximum sustainable frequency
            sustainable_frequencies = [
                m["actual_frequency"] for m in streaming_results["measurements"]
                if m["can_maintain_frequency"]
            ]

            streaming_results["max_sustainable_frequency"] = max(sustainable_frequencies) if sustainable_frequencies else 0

            print(f"   🚀 Max sustainable frequency: {streaming_results['max_sustainable_frequency']:.1f} updates/sec")

        except Exception as e:
            streaming_results["status"] = "ERROR"
            streaming_results["error"] = str(e)
            print(f"   ❌ Streaming test error: {e}")

        return streaming_results

    def test_memory_efficiency(self) -> Dict[str, Any]:
        """Test memory efficiency and leak detection"""
        print("\n💾 Testing Memory Efficiency")

        memory_results = {
            "test_name": "memory_efficiency",
            "measurements": [],
            "status": "UNKNOWN"
        }

        try:
            # Record baseline memory
            gc.collect()  # Force garbage collection
            baseline_memory = self.process.memory_info().rss / 1024 / 1024  # MB

            # Run repeated analyses to test for memory leaks
            iterations = 50
            memory_measurements = [baseline_memory]

            print(f"   Running {iterations} iterations...")
            print(f"   Baseline memory: {baseline_memory:.1f}MB")

            for i in range(iterations):
                # Generate substantial test data
                pressure_metrics = self._generate_pressure_metrics(20)

                from institutional_flow_v3.solution import run_ifd_v3_analysis
                config = self._get_test_config()

                result = run_ifd_v3_analysis(pressure_metrics, config)

                # Measure memory every 10 iterations
                if i % 10 == 0:
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    memory_measurements.append(current_memory)
                    print(f"      Iteration {i}: {current_memory:.1f}MB")

            # Final memory measurement
            gc.collect()
            final_memory = self.process.memory_info().rss / 1024 / 1024
            memory_measurements.append(final_memory)

            # Calculate memory metrics
            memory_growth = final_memory - baseline_memory
            max_memory = max(memory_measurements)
            peak_growth = max_memory - baseline_memory

            memory_results["measurements"] = [{
                "baseline_memory_mb": baseline_memory,
                "final_memory_mb": final_memory,
                "max_memory_mb": max_memory,
                "memory_growth_mb": memory_growth,
                "peak_growth_mb": peak_growth,
                "iterations": iterations,
                "memory_timeline": memory_measurements,
                "meets_requirement": memory_growth < 50  # <50MB growth requirement
            }]

            memory_results["status"] = "PASSED" if memory_growth < 50 else "FAILED"

            status_emoji = "✅" if memory_growth < 50 else "❌"
            print(f"   {status_emoji} Memory growth: {memory_growth:.1f}MB (peak: {peak_growth:.1f}MB)")

        except Exception as e:
            memory_results["status"] = "ERROR"
            memory_results["error"] = str(e)
            print(f"   ❌ Memory test error: {e}")

        return memory_results

    def test_cpu_efficiency(self) -> Dict[str, Any]:
        """Test CPU usage efficiency"""
        print("\n🔥 Testing CPU Efficiency")

        cpu_results = {
            "test_name": "cpu_efficiency",
            "measurements": [],
            "status": "UNKNOWN"
        }

        try:
            # Monitor CPU usage during intensive processing
            cpu_measurements = []

            def monitor_cpu():
                """Monitor CPU usage in background thread"""
                for _ in range(30):  # Monitor for 30 seconds
                    cpu_percent = self.process.cpu_percent(interval=1)
                    cpu_measurements.append(cpu_percent)

            # Start CPU monitoring
            monitor_thread = threading.Thread(target=monitor_cpu)
            monitor_thread.start()

            # Run intensive processing
            print("   Running intensive processing for 30 seconds...")

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []

                for i in range(20):  # 20 concurrent analyses
                    pressure_metrics = self._generate_pressure_metrics(25)

                    future = executor.submit(self._run_analysis_with_config, pressure_metrics)
                    futures.append(future)

                # Wait for all analyses to complete
                for future in as_completed(futures):
                    try:
                        result = future.result()
                    except Exception as e:
                        print(f"      Analysis failed: {e}")

            # Wait for CPU monitoring to complete
            monitor_thread.join()

            # Calculate CPU metrics
            if cpu_measurements:
                avg_cpu = statistics.mean(cpu_measurements)
                max_cpu = max(cpu_measurements)

                cpu_results["measurements"] = [{
                    "avg_cpu_percent": avg_cpu,
                    "max_cpu_percent": max_cpu,
                    "cpu_timeline": cpu_measurements,
                    "meets_requirement": max_cpu < 80  # <80% CPU requirement
                }]

                cpu_results["status"] = "PASSED" if max_cpu < 80 else "FAILED"

                status_emoji = "✅" if max_cpu < 80 else "❌"
                print(f"   {status_emoji} CPU usage: {avg_cpu:.1f}% avg, {max_cpu:.1f}% max")
            else:
                cpu_results["status"] = "ERROR"
                cpu_results["error"] = "No CPU measurements collected"

        except Exception as e:
            cpu_results["status"] = "ERROR"
            cpu_results["error"] = str(e)
            print(f"   ❌ CPU test error: {e}")

        return cpu_results

    def _generate_pressure_metrics(self, count: int) -> List[Any]:
        """Generate test pressure metrics"""
        from analysis_engine.integration import AnalysisEngine

        # Generate mock MBO data
        mbo_data = []
        base_time = datetime.now()

        for i in range(count):
            mbo_data.append({
                "symbol": "NQM25",
                "window_start": (base_time - timedelta(minutes=i*5)).isoformat(),
                "window_end": (base_time - timedelta(minutes=(i-1)*5)).isoformat(),
                "total_trades": 100 + i*10,
                "buy_pressure": 0.4 + (i % 5) * 0.1,
                "sell_pressure": 0.6 - (i % 5) * 0.1,
                "total_volume": 2000 + i*200
            })

        # Convert to pressure metrics format
        engine = AnalysisEngine({})
        return engine._convert_to_pressure_metrics_objects(mbo_data)

    def _create_pressure_metric(self, strike: float, option_type: str, confidence: float) -> Any:
        """Create a single pressure metric for testing"""
        from analysis_engine.integration import AnalysisEngine

        mbo_data = [{
            "symbol": "NQM25",
            "window_start": datetime.now().isoformat(),
            "window_end": (datetime.now() + timedelta(minutes=5)).isoformat(),
            "total_trades": 100,
            "buy_pressure": confidence,
            "sell_pressure": 1.0 - confidence,
            "total_volume": 2000,
            "strike": strike,
            "option_type": option_type
        }]

        engine = AnalysisEngine({})
        return engine._convert_to_pressure_metrics_objects(mbo_data)[0]

    def _get_test_config(self) -> Dict[str, Any]:
        """Get standardized test configuration"""
        return {
            "db_path": "/tmp/perf_test.db",
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

    def _run_analysis_with_config(self, pressure_metrics: List[Any]) -> Dict[str, Any]:
        """Run analysis with standard config"""
        from institutional_flow_v3.solution import run_ifd_v3_analysis
        return run_ifd_v3_analysis(pressure_metrics, self._get_test_config())

    def run_comprehensive_performance_test(self) -> Dict[str, Any]:
        """Run comprehensive performance requirements testing"""
        print("⚡ COMPREHENSIVE PERFORMANCE REQUIREMENTS TEST")
        print("=" * 60)

        overall_start = time.time()

        # Run all performance tests
        test_functions = [
            ("latency", self.test_latency_requirements),
            ("throughput", self.test_throughput_requirements),
            ("streaming", self.test_streaming_updates_processing),
            ("memory", self.test_memory_efficiency),
            ("cpu", self.test_cpu_efficiency)
        ]

        for test_name, test_function in test_functions:
            try:
                result = test_function()
                self.test_results["test_results"][test_name] = result
            except Exception as e:
                self.test_results["test_results"][test_name] = {
                    "test_name": test_name,
                    "status": "ERROR",
                    "error": str(e)
                }
                print(f"   ❌ {test_name} test failed: {e}")

        # Calculate overall results
        total_time = (time.time() - overall_start) * 1000
        passed_tests = len([t for t in self.test_results["test_results"].values() if t["status"] == "PASSED"])
        total_tests = len(self.test_results["test_results"])

        self.test_results["summary"] = {
            "total_test_time_ms": total_time,
            "tests_passed": passed_tests,
            "total_tests": total_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0
        }

        # Determine overall status
        self.test_results["overall_status"] = "PASSED" if passed_tests == total_tests else "FAILED"

        return self.test_results

    def print_summary(self):
        """Print comprehensive performance test summary"""
        print("\n" + "=" * 60)
        print("🏁 PERFORMANCE REQUIREMENTS TEST SUMMARY")
        print("=" * 60)

        print(f"Overall Status: {self.test_results['overall_status']}")
        print(f"Tests Passed: {self.test_results.get('summary', {}).get('tests_passed', 0)}/{self.test_results.get('summary', {}).get('total_tests', 0)}")
        print(f"Success Rate: {self.test_results.get('summary', {}).get('success_rate', 0)*100:.1f}%")

        # Print individual test results
        print(f"\n📋 Individual Test Results:")
        for test_name, result in self.test_results.get("test_results", {}).items():
            status_emoji = "✅" if result["status"] == "PASSED" else ("❌" if result["status"] == "FAILED" else "⚠️")
            print(f"   {status_emoji} {test_name}: {result['status']}")

        # Print performance highlights
        requirements = self.test_results["requirements"]
        print(f"\n🎯 Performance Requirements:")
        print(f"   Latency Target: <{requirements['max_latency_ms']}ms")
        print(f"   Throughput Target: >{requirements['min_throughput_strikes']} strikes")
        print(f"   Memory Limit: <{requirements['max_memory_growth_mb']}MB growth")
        print(f"   CPU Limit: <{requirements['max_cpu_usage_percent']}% usage")

        if self.test_results["overall_status"] == "PASSED":
            print("\n🎉 ALL PERFORMANCE REQUIREMENTS MET!")
        else:
            print("\n⚠️  SOME PERFORMANCE REQUIREMENTS NOT MET")

    def save_results(self, filepath: str):
        """Save performance test results"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(self.test_results, f, indent=2)

        print(f"\n📄 Performance test results saved to: {filepath}")


def main():
    """Main test execution"""
    test = PerformanceRequirementsTest()
    results = test.run_comprehensive_performance_test()
    test.print_summary()

    # Save results
    output_path = "outputs/ifd_v3_testing/performance_requirements_tests.json"
    test.save_results(output_path)

    return 0 if results["overall_status"] == "PASSED" else 1


if __name__ == "__main__":
    exit(main())
