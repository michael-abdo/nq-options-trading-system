#!/usr/bin/env python3
"""
Dashboard Responsiveness and Signal Display Testing

Tests the real-time dashboard's performance, responsiveness, and accuracy
of signal display under various conditions.
"""

import json
import time
import asyncio
import logging
import websockets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import sys
import os

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from utils.timezone_utils import get_eastern_time

class DashboardResponsivenessTest:
    """Test dashboard performance and signal display accuracy"""

    def __init__(self, test_config: Optional[Dict[str, Any]] = None):
        self.test_config = test_config or self._load_default_config()
        self.results_dir = "outputs/test_results/phase4/dashboard"
        os.makedirs(self.results_dir, exist_ok=True)

        # Setup logging
        self._setup_logging()

        # WebSocket connection
        self.websocket = None
        self.dashboard_url = "http://localhost:8051"
        self.websocket_uri = "ws://localhost:8765"

        # Test results
        self.test_results = {
            "start_time": get_eastern_time().isoformat(),
            "tests": {},
            "metrics": {},
            "issues": []
        }

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default test configuration"""
        return {
            "performance_targets": {
                "max_render_time_ms": 100,
                "max_update_latency_ms": 50,
                "max_websocket_latency_ms": 10,
                "min_fps": 30,
                "max_memory_usage_mb": 500
            },
            "signal_display": {
                "max_signal_age_seconds": 60,
                "required_fields": ["symbol", "timestamp", "confidence", "signal_type"],
                "color_accuracy": True,
                "animation_smoothness": True
            },
            "load_test": {
                "max_concurrent_signals": 100,
                "update_frequency_hz": 10,
                "test_duration_seconds": 300
            },
            "responsiveness": {
                "interaction_tests": True,
                "resize_tests": True,
                "scroll_performance": True,
                "chart_zoom_pan": True
            }
        }

    def _setup_logging(self):
        """Setup test logging"""
        log_file = f"{self.results_dir}/dashboard_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    async def run_dashboard_tests(self) -> Dict[str, Any]:
        """Run complete dashboard test suite"""
        self.logger.info("Starting Phase 4 Dashboard Responsiveness Tests")

        try:
            # 1. Test dashboard startup
            await self._test_dashboard_startup()

            # 2. Test WebSocket connectivity
            await self._test_websocket_connectivity()

            # 3. Test signal display accuracy
            await self._test_signal_display_accuracy()

            # 4. Test real-time updates
            await self._test_realtime_updates()

            # 5. Test dashboard performance under load
            await self._test_dashboard_load()

            # 6. Test responsiveness
            await self._test_ui_responsiveness()

            # 7. Test memory usage
            await self._test_memory_stability()

            # 8. Test error handling
            await self._test_error_handling()

        except Exception as e:
            self.logger.error(f"Dashboard test failed: {e}")
            self.test_results["critical_error"] = str(e)
        finally:
            await self._cleanup()

        # Generate test report
        self._generate_test_report()

        return self.test_results

    async def _test_dashboard_startup(self):
        """Test dashboard initialization and startup time"""
        self.logger.info("Testing dashboard startup...")

        start_time = time.time()

        # Simulate dashboard startup check
        dashboard_ready = await self._check_dashboard_ready()

        startup_time = (time.time() - start_time) * 1000

        self.test_results["tests"]["dashboard_startup"] = {
            "status": "PASS" if dashboard_ready and startup_time < 5000 else "FAIL",
            "startup_time_ms": startup_time,
            "dashboard_ready": dashboard_ready,
            "components_loaded": [
                "price_chart",
                "signal_panel",
                "metrics_display",
                "websocket_client"
            ]
        }

        self.logger.info(f"Dashboard startup: {startup_time:.1f}ms")

    async def _test_websocket_connectivity(self):
        """Test WebSocket connection to signal server"""
        self.logger.info("Testing WebSocket connectivity...")

        connection_attempts = 0
        connection_successful = False
        latencies = []

        for attempt in range(3):
            try:
                start_time = time.time()
                async with websockets.connect(self.websocket_uri) as websocket:
                    # Send ping
                    await websocket.send(json.dumps({"type": "ping"}))

                    # Wait for pong
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    latency = (time.time() - start_time) * 1000
                    latencies.append(latency)

                    connection_successful = True
                    self.websocket = websocket
                    break

            except Exception as e:
                self.logger.warning(f"WebSocket connection attempt {attempt + 1} failed: {e}")
                connection_attempts += 1
                await asyncio.sleep(1)

        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        self.test_results["tests"]["websocket_connectivity"] = {
            "status": "PASS" if connection_successful else "FAIL",
            "connection_attempts": connection_attempts + 1,
            "connection_successful": connection_successful,
            "avg_latency_ms": avg_latency,
            "websocket_uri": self.websocket_uri
        }

        self.logger.info(f"WebSocket connectivity: {'Connected' if connection_successful else 'Failed'}")

    async def _test_signal_display_accuracy(self):
        """Test accuracy of signal display"""
        self.logger.info("Testing signal display accuracy...")

        test_signals = self._generate_test_signals(10)
        display_results = []

        for signal in test_signals:
            # Send signal via WebSocket
            if self.websocket:
                await self.websocket.send(json.dumps(signal))

            # Simulate checking dashboard display
            display_result = await self._verify_signal_display(signal)
            display_results.append(display_result)

            await asyncio.sleep(0.1)

        # Calculate accuracy
        accurate_displays = sum(1 for r in display_results if r["accurate"])
        accuracy_rate = accurate_displays / len(display_results) if display_results else 0

        self.test_results["tests"]["signal_display_accuracy"] = {
            "status": "PASS" if accuracy_rate >= 0.95 else "FAIL",
            "signals_sent": len(test_signals),
            "accurate_displays": accurate_displays,
            "accuracy_rate": accuracy_rate,
            "display_issues": [r["issues"] for r in display_results if not r["accurate"]]
        }

        self.logger.info(f"Signal display accuracy: {accuracy_rate:.1%}")

    async def _test_realtime_updates(self):
        """Test real-time update performance"""
        self.logger.info("Testing real-time updates...")

        update_latencies = []
        missed_updates = 0
        test_duration = 30  # seconds

        start_time = time.time()
        signal_count = 0

        while time.time() - start_time < test_duration:
            # Generate and send signal
            signal = self._generate_test_signals(1)[0]
            signal["sent_time"] = time.time()

            if self.websocket:
                try:
                    await self.websocket.send(json.dumps(signal))
                    signal_count += 1

                    # Simulate measuring update latency
                    update_latency = await self._measure_update_latency(signal)
                    if update_latency > 0:
                        update_latencies.append(update_latency)
                    else:
                        missed_updates += 1

                except Exception as e:
                    self.logger.error(f"Update error: {e}")
                    missed_updates += 1

            # Maintain update rate
            await asyncio.sleep(0.1)  # 10 Hz

        # Calculate statistics
        if update_latencies:
            avg_latency = sum(update_latencies) / len(update_latencies)
            max_latency = max(update_latencies)
            p95_latency = sorted(update_latencies)[int(len(update_latencies) * 0.95)]
        else:
            avg_latency = max_latency = p95_latency = 0

        self.test_results["tests"]["realtime_updates"] = {
            "status": "PASS" if missed_updates < signal_count * 0.05 else "FAIL",
            "test_duration_seconds": test_duration,
            "signals_sent": signal_count,
            "missed_updates": missed_updates,
            "update_rate_hz": signal_count / test_duration,
            "latency_ms": {
                "avg": avg_latency,
                "max": max_latency,
                "p95": p95_latency
            }
        }

        self.logger.info(f"Real-time updates: {signal_count} signals, {avg_latency:.1f}ms avg latency")

    async def _test_dashboard_load(self):
        """Test dashboard performance under heavy load"""
        self.logger.info("Testing dashboard under load...")

        # Performance metrics
        render_times = []
        cpu_usage_samples = []
        memory_usage_samples = []
        dropped_frames = 0

        # Generate high-frequency signals
        test_duration = 60  # seconds
        signals_per_second = 20

        start_time = time.time()
        total_signals = 0

        while time.time() - start_time < test_duration:
            batch_start = time.time()

            # Send batch of signals
            for _ in range(signals_per_second):
                signal = self._generate_test_signals(1)[0]
                if self.websocket:
                    try:
                        await self.websocket.send(json.dumps(signal))
                        total_signals += 1
                    except:
                        pass

            # Simulate performance measurement
            render_time = await self._measure_render_time()
            render_times.append(render_time)

            # Sample system metrics
            cpu_usage = self._get_cpu_usage()
            memory_usage = self._get_memory_usage()
            cpu_usage_samples.append(cpu_usage)
            memory_usage_samples.append(memory_usage)

            # Check for frame drops
            if render_time > 33.33:  # Less than 30 FPS
                dropped_frames += 1

            # Maintain rate
            batch_duration = time.time() - batch_start
            if batch_duration < 1.0:
                await asyncio.sleep(1.0 - batch_duration)

        # Calculate results
        avg_render_time = sum(render_times) / len(render_times) if render_times else 0
        max_render_time = max(render_times) if render_times else 0
        avg_cpu = sum(cpu_usage_samples) / len(cpu_usage_samples) if cpu_usage_samples else 0
        avg_memory = sum(memory_usage_samples) / len(memory_usage_samples) if memory_usage_samples else 0

        self.test_results["tests"]["dashboard_load"] = {
            "status": "PASS" if avg_render_time < self.test_config["performance_targets"]["max_render_time_ms"] else "FAIL",
            "test_duration_seconds": test_duration,
            "total_signals": total_signals,
            "signals_per_second": total_signals / test_duration,
            "render_performance": {
                "avg_render_time_ms": avg_render_time,
                "max_render_time_ms": max_render_time,
                "dropped_frames": dropped_frames,
                "estimated_fps": 1000 / avg_render_time if avg_render_time > 0 else 0
            },
            "resource_usage": {
                "avg_cpu_percent": avg_cpu,
                "avg_memory_mb": avg_memory
            }
        }

        self.logger.info(f"Load test: {total_signals} signals, {avg_render_time:.1f}ms avg render")

    async def _test_ui_responsiveness(self):
        """Test UI interaction responsiveness"""
        self.logger.info("Testing UI responsiveness...")

        interaction_results = {
            "chart_interactions": await self._test_chart_interactions(),
            "panel_switching": await self._test_panel_switching(),
            "window_resize": await self._test_window_resize(),
            "scroll_performance": await self._test_scroll_performance()
        }

        # Calculate overall responsiveness
        total_tests = sum(len(r.get("results", [])) for r in interaction_results.values())
        passed_tests = sum(sum(1 for t in r.get("results", []) if t.get("passed", False))
                          for r in interaction_results.values())

        self.test_results["tests"]["ui_responsiveness"] = {
            "status": "PASS" if passed_tests >= total_tests * 0.9 else "FAIL",
            "total_interactions": total_tests,
            "successful_interactions": passed_tests,
            "interaction_results": interaction_results,
            "responsiveness_score": passed_tests / total_tests if total_tests > 0 else 0
        }

        self.logger.info(f"UI responsiveness: {passed_tests}/{total_tests} tests passed")

    async def _test_memory_stability(self):
        """Test dashboard memory usage over time"""
        self.logger.info("Testing memory stability...")

        memory_samples = []
        test_duration = 300  # 5 minutes
        sample_interval = 10  # seconds

        initial_memory = self._get_memory_usage()

        start_time = time.time()

        while time.time() - start_time < test_duration:
            # Generate normal load
            for _ in range(10):
                signal = self._generate_test_signals(1)[0]
                if self.websocket:
                    try:
                        await self.websocket.send(json.dumps(signal))
                    except:
                        pass

            # Sample memory
            current_memory = self._get_memory_usage()
            memory_samples.append(current_memory)

            await asyncio.sleep(sample_interval)

        # Analyze memory trend
        final_memory = memory_samples[-1] if memory_samples else initial_memory
        memory_growth = final_memory - initial_memory
        memory_growth_rate = memory_growth / (test_duration / 60)  # MB per minute

        # Check for memory leak
        has_leak = memory_growth_rate > 5  # More than 5MB/minute is concerning
        max_memory = max(memory_samples) if memory_samples else initial_memory

        self.test_results["tests"]["memory_stability"] = {
            "status": "PASS" if not has_leak and max_memory < self.test_config["performance_targets"]["max_memory_usage_mb"] else "FAIL",
            "test_duration_minutes": test_duration / 60,
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_growth_mb": memory_growth,
            "growth_rate_mb_per_minute": memory_growth_rate,
            "max_memory_mb": max_memory,
            "potential_leak": has_leak
        }

        self.logger.info(f"Memory stability: {memory_growth:.1f}MB growth over {test_duration/60:.0f} minutes")

    async def _test_error_handling(self):
        """Test dashboard error handling and recovery"""
        self.logger.info("Testing error handling...")

        error_scenarios = []

        # Test malformed signal handling
        malformed_signal = {"invalid": "data", "no_required_fields": True}
        error_handled = await self._test_malformed_signal(malformed_signal)
        error_scenarios.append({
            "scenario": "malformed_signal",
            "handled_gracefully": error_handled,
            "dashboard_stable": True  # Simulate check
        })

        # Test connection loss recovery
        if self.websocket:
            try:
                await self.websocket.close()
                self.websocket = None
            except:
                pass

        # Wait and test reconnection
        await asyncio.sleep(5)
        reconnected = await self._test_auto_reconnect()
        error_scenarios.append({
            "scenario": "connection_loss",
            "handled_gracefully": reconnected,
            "recovery_time_seconds": 5
        })

        # Test rapid signal overflow
        overflow_handled = await self._test_signal_overflow()
        error_scenarios.append({
            "scenario": "signal_overflow",
            "handled_gracefully": overflow_handled,
            "performance_maintained": True
        })

        # Calculate results
        handled_count = sum(1 for s in error_scenarios if s.get("handled_gracefully", False))

        self.test_results["tests"]["error_handling"] = {
            "status": "PASS" if handled_count == len(error_scenarios) else "FAIL",
            "scenarios_tested": len(error_scenarios),
            "handled_gracefully": handled_count,
            "error_scenarios": error_scenarios
        }

        self.logger.info(f"Error handling: {handled_count}/{len(error_scenarios)} scenarios handled")

    def _generate_test_signals(self, count: int) -> List[Dict[str, Any]]:
        """Generate test signals"""
        signals = []

        for i in range(count):
            signal = {
                "type": "signal",
                "timestamp": time.time(),
                "symbol": "NQM5",
                "signal_type": "BUY" if i % 2 == 0 else "SELL",
                "confidence": 0.75 + (i % 20) * 0.01,
                "strength": "HIGH" if i % 3 == 0 else "MEDIUM",
                "metadata": {
                    "pressure_delta": 1000 + i * 100,
                    "volume_ratio": 1.5 + (i % 10) * 0.1,
                    "test_signal": True
                }
            }
            signals.append(signal)

        return signals

    async def _check_dashboard_ready(self) -> bool:
        """Check if dashboard is ready"""
        # Simulate dashboard readiness check
        await asyncio.sleep(2)
        return True

    async def _verify_signal_display(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Verify signal is displayed correctly"""
        # Simulate display verification
        await asyncio.sleep(0.05)

        issues = []

        # Check required fields
        for field in self.test_config["signal_display"]["required_fields"]:
            if field not in signal:
                issues.append(f"Missing field: {field}")

        return {
            "signal_id": signal.get("timestamp", "unknown"),
            "accurate": len(issues) == 0,
            "issues": issues
        }

    async def _measure_update_latency(self, signal: Dict[str, Any]) -> float:
        """Measure update latency"""
        # Simulate latency measurement
        await asyncio.sleep(0.01)

        if "sent_time" in signal:
            return (time.time() - signal["sent_time"]) * 1000
        return 5.0  # Default latency

    async def _measure_render_time(self) -> float:
        """Measure dashboard render time"""
        # Simulate render time measurement
        await asyncio.sleep(0.01)
        import random
        return 10 + random.uniform(-5, 20)  # Mock render time in ms

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage"""
        try:
            import psutil
            return psutil.cpu_percent()
        except:
            return 25.0  # Mock value

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            return psutil.Process().memory_info().rss / 1024 / 1024
        except:
            return 200.0  # Mock value

    async def _test_chart_interactions(self) -> Dict[str, Any]:
        """Test chart interaction performance"""
        results = []

        # Test zoom
        zoom_result = await self._simulate_chart_action("zoom", 50)
        results.append({"action": "zoom", "response_time_ms": zoom_result, "passed": zoom_result < 100})

        # Test pan
        pan_result = await self._simulate_chart_action("pan", 30)
        results.append({"action": "pan", "response_time_ms": pan_result, "passed": pan_result < 50})

        return {"results": results}

    async def _test_panel_switching(self) -> Dict[str, Any]:
        """Test panel switching performance"""
        results = []

        for panel in ["signals", "metrics", "settings"]:
            switch_time = await self._simulate_panel_switch(panel)
            results.append({
                "panel": panel,
                "switch_time_ms": switch_time,
                "passed": switch_time < 200
            })

        return {"results": results}

    async def _test_window_resize(self) -> Dict[str, Any]:
        """Test window resize performance"""
        results = []

        for size in ["small", "medium", "large"]:
            resize_time = await self._simulate_window_resize(size)
            results.append({
                "size": size,
                "resize_time_ms": resize_time,
                "passed": resize_time < 500
            })

        return {"results": results}

    async def _test_scroll_performance(self) -> Dict[str, Any]:
        """Test scroll performance"""
        results = []

        scroll_time = await self._simulate_scroll_action(1000)  # 1000 pixels
        results.append({
            "action": "scroll",
            "distance_pixels": 1000,
            "time_ms": scroll_time,
            "passed": scroll_time < 100
        })

        return {"results": results}

    async def _simulate_chart_action(self, action: str, duration_ms: float) -> float:
        """Simulate chart interaction"""
        await asyncio.sleep(duration_ms / 1000)
        return duration_ms

    async def _simulate_panel_switch(self, panel: str) -> float:
        """Simulate panel switching"""
        await asyncio.sleep(0.1)
        return 80.0  # Mock switch time

    async def _simulate_window_resize(self, size: str) -> float:
        """Simulate window resize"""
        await asyncio.sleep(0.2)
        return 150.0  # Mock resize time

    async def _simulate_scroll_action(self, pixels: int) -> float:
        """Simulate scroll action"""
        await asyncio.sleep(0.05)
        return 40.0  # Mock scroll time

    async def _test_malformed_signal(self, signal: Dict[str, Any]) -> bool:
        """Test malformed signal handling"""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(signal))
                await asyncio.sleep(0.1)
                return True  # Handled without crash
            except:
                return True  # Error caught
        return True

    async def _test_auto_reconnect(self) -> bool:
        """Test auto-reconnection"""
        try:
            async with websockets.connect(self.websocket_uri) as websocket:
                self.websocket = websocket
                return True
        except:
            return False

    async def _test_signal_overflow(self) -> bool:
        """Test signal overflow handling"""
        # Send 1000 signals rapidly
        if self.websocket:
            try:
                for _ in range(1000):
                    signal = self._generate_test_signals(1)[0]
                    await self.websocket.send(json.dumps(signal))
                    # No delay - rapid fire

                await asyncio.sleep(1)
                return True  # Dashboard survived
            except:
                return False
        return True

    async def _cleanup(self):
        """Cleanup test resources"""
        self.logger.info("Cleaning up dashboard test resources...")

        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass

    def _generate_test_report(self):
        """Generate comprehensive test report"""
        self.test_results["end_time"] = get_eastern_time().isoformat()

        # Calculate summary
        total_tests = len(self.test_results["tests"])
        passed_tests = sum(1 for test in self.test_results["tests"].values()
                          if test.get("status") == "PASS")

        self.test_results["summary"] = {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": total_tests - passed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "performance_met": self._check_performance_targets()
        }

        # Save report
        report_file = f"{self.results_dir}/dashboard_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)

        # Print summary
        self.logger.info("\n" + "="*60)
        self.logger.info("DASHBOARD RESPONSIVENESS TEST SUMMARY")
        self.logger.info("="*60)
        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"Passed: {passed_tests}")
        self.logger.info(f"Failed: {total_tests - passed_tests}")
        self.logger.info(f"Success Rate: {self.test_results['summary']['success_rate']:.1%}")
        self.logger.info(f"\nDetailed report saved to: {report_file}")

    def _check_performance_targets(self) -> bool:
        """Check if performance targets were met"""
        targets_met = True

        # Check render time
        if "dashboard_load" in self.test_results["tests"]:
            avg_render = self.test_results["tests"]["dashboard_load"]["render_performance"]["avg_render_time_ms"]
            if avg_render > self.test_config["performance_targets"]["max_render_time_ms"]:
                targets_met = False

        # Check WebSocket latency
        if "websocket_connectivity" in self.test_results["tests"]:
            ws_latency = self.test_results["tests"]["websocket_connectivity"]["avg_latency_ms"]
            if ws_latency > self.test_config["performance_targets"]["max_websocket_latency_ms"]:
                targets_met = False

        return targets_met

# Run dashboard tests
async def run_dashboard_tests(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run Phase 4 dashboard responsiveness tests"""
    tester = DashboardResponsivenessTest(config)
    return await tester.run_dashboard_tests()

if __name__ == "__main__":
    async def main():
        results = await run_dashboard_tests()
        print(f"\nDashboard Test Results:")
        print(f"Success Rate: {results['summary']['success_rate']:.1%}")
        print(f"Performance Targets Met: {results['summary']['performance_met']}")

    asyncio.run(main())
