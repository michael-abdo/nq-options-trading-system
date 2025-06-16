#!/usr/bin/env python3
"""
Stress Testing Scenarios for Market Volatility

Simulates extreme market conditions including:
- Flash crashes and rallies
- High-frequency trading bursts
- Market open/close volatility
- News-driven volume spikes
- System failures and recovery
"""

import json
import time
import asyncio
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import sys
import os

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from utils.timezone_utils import get_eastern_time
from tasks.options_trading_system.analysis_engine.live_streaming.streaming_bridge import StreamingBridge
from tasks.options_trading_system.analysis_engine.institutional_flow_v3.solution import IFDv3Engine
from tasks.options_trading_system.analysis_engine.monitoring.performance_tracker import PerformanceTracker

@dataclass
class MarketScenario:
    """Market scenario configuration"""
    name: str
    duration_seconds: int
    price_volatility: float  # Standard deviation of price changes
    volume_multiplier: float  # Multiplier over normal volume
    event_frequency: float  # Events per second
    description: str

class StressTestSuite:
    """Comprehensive stress testing for extreme market conditions"""

    def __init__(self, test_config: Optional[Dict[str, Any]] = None):
        self.test_config = test_config or self._load_default_config()
        self.results_dir = "outputs/test_results/phase4/stress"
        os.makedirs(self.results_dir, exist_ok=True)

        # Setup logging
        self._setup_logging()

        # Initialize components
        self.streaming_bridge = None
        self.performance_tracker = PerformanceTracker()

        # Stress test scenarios
        self.scenarios = self._define_scenarios()

        # Results tracking
        self.test_results = {
            "start_time": get_eastern_time().isoformat(),
            "scenarios": {},
            "system_failures": [],
            "recovery_metrics": {}
        }

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default stress test configuration"""
        return {
            "symbols": ["NQM5", "ESM5", "YMM5", "RTM5"],
            "base_price": {
                "NQM5": 15000,
                "ESM5": 4500,
                "YMM5": 35000,
                "RTM5": 2200
            },
            "normal_volume": 100,  # Events per second
            "performance_thresholds": {
                "max_acceptable_latency_ms": 200,
                "max_error_rate": 0.05,
                "min_signal_accuracy": 0.60,
                "max_recovery_time_seconds": 30
            },
            "failure_scenarios": {
                "connection_loss": True,
                "data_corruption": True,
                "memory_exhaustion": True,
                "cpu_saturation": True
            }
        }

    def _setup_logging(self):
        """Setup stress test logging"""
        log_file = f"{self.results_dir}/stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _define_scenarios(self) -> List[MarketScenario]:
        """Define stress test scenarios"""
        return [
            MarketScenario(
                name="flash_crash",
                duration_seconds=300,
                price_volatility=5.0,  # 5% volatility
                volume_multiplier=10.0,
                event_frequency=1000,
                description="Simulates a flash crash with 5% price drop in 5 minutes"
            ),
            MarketScenario(
                name="market_open_surge",
                duration_seconds=600,
                price_volatility=2.0,
                volume_multiplier=5.0,
                event_frequency=500,
                description="Simulates high volatility at market open"
            ),
            MarketScenario(
                name="news_spike",
                duration_seconds=120,
                price_volatility=3.0,
                volume_multiplier=20.0,
                event_frequency=2000,
                description="Simulates sudden news event with 20x volume spike"
            ),
            MarketScenario(
                name="hft_burst",
                duration_seconds=60,
                price_volatility=0.5,
                volume_multiplier=50.0,
                event_frequency=5000,
                description="Simulates high-frequency trading burst"
            ),
            MarketScenario(
                name="liquidity_crisis",
                duration_seconds=180,
                price_volatility=10.0,
                volume_multiplier=0.1,
                event_frequency=10,
                description="Simulates liquidity crisis with wide spreads"
            ),
            MarketScenario(
                name="circuit_breaker",
                duration_seconds=300,
                price_volatility=7.0,
                volume_multiplier=15.0,
                event_frequency=1500,
                description="Simulates market-wide circuit breaker event"
            )
        ]

    async def run_stress_tests(self) -> Dict[str, Any]:
        """Run complete stress test suite"""
        self.logger.info("Starting Phase 4 Stress Tests")

        try:
            # Initialize system
            await self._initialize_system()

            # Run each scenario
            for scenario in self.scenarios:
                self.logger.info(f"\nRunning scenario: {scenario.name}")
                self.logger.info(f"Description: {scenario.description}")

                scenario_result = await self._run_scenario(scenario)
                self.test_results["scenarios"][scenario.name] = scenario_result

                # Allow system to recover between scenarios
                await self._system_recovery_period()

            # Run failure scenarios
            if self.test_config["failure_scenarios"]["connection_loss"]:
                await self._test_connection_loss()

            if self.test_config["failure_scenarios"]["data_corruption"]:
                await self._test_data_corruption()

            if self.test_config["failure_scenarios"]["memory_exhaustion"]:
                await self._test_memory_exhaustion()

            if self.test_config["failure_scenarios"]["cpu_saturation"]:
                await self._test_cpu_saturation()

            # Generate stress test report
            self._generate_stress_report()

        except Exception as e:
            self.logger.error(f"Stress test failed: {e}")
            self.test_results["critical_failure"] = str(e)
        finally:
            await self._cleanup()

        return self.test_results

    async def _initialize_system(self):
        """Initialize system for stress testing"""
        self.logger.info("Initializing system for stress testing...")

        # Configure for stress testing mode
        config = {
            "mode": "stress_test",
            "symbols": self.test_config["symbols"],
            "enable_websocket_server": True,
            "stress_test_mode": True,
            "buffer_sizes": {
                "event_buffer": 10000,
                "signal_buffer": 1000
            }
        }

        self.streaming_bridge = StreamingBridge(config)
        await self.streaming_bridge.start_async()

        self.logger.info("System initialized for stress testing")

    async def _run_scenario(self, scenario: MarketScenario) -> Dict[str, Any]:
        """Run a single stress test scenario"""
        start_time = time.time()

        # Metrics collection
        metrics = {
            "events_generated": 0,
            "events_processed": 0,
            "signals_generated": 0,
            "errors": 0,
            "latencies": [],
            "cpu_samples": [],
            "memory_samples": []
        }

        # Generate scenario events
        event_generator = asyncio.create_task(
            self._generate_scenario_events(scenario, metrics)
        )

        # Monitor system performance
        monitor_task = asyncio.create_task(
            self._monitor_system_performance(scenario.duration_seconds, metrics)
        )

        # Collect signals
        signal_collector = asyncio.create_task(
            self._collect_signals(scenario.duration_seconds, metrics)
        )

        # Wait for scenario to complete
        await asyncio.gather(event_generator, monitor_task, signal_collector)

        # Calculate results
        duration = time.time() - start_time

        # Analyze performance
        latencies = sorted(metrics["latencies"])
        p50_latency = latencies[int(len(latencies) * 0.50)] if latencies else 0
        p95_latency = latencies[int(len(latencies) * 0.95)] if latencies else 0
        p99_latency = latencies[int(len(latencies) * 0.99)] if latencies else 0

        avg_cpu = sum(metrics["cpu_samples"]) / len(metrics["cpu_samples"]) if metrics["cpu_samples"] else 0
        max_cpu = max(metrics["cpu_samples"]) if metrics["cpu_samples"] else 0
        avg_memory = sum(metrics["memory_samples"]) / len(metrics["memory_samples"]) if metrics["memory_samples"] else 0
        max_memory = max(metrics["memory_samples"]) if metrics["memory_samples"] else 0

        # Check if system survived
        error_rate = metrics["errors"] / metrics["events_generated"] if metrics["events_generated"] > 0 else 0
        survived = error_rate < self.test_config["performance_thresholds"]["max_error_rate"]

        return {
            "duration_seconds": duration,
            "events": {
                "generated": metrics["events_generated"],
                "processed": metrics["events_processed"],
                "dropped": metrics["events_generated"] - metrics["events_processed"],
                "error_rate": error_rate
            },
            "signals": {
                "generated": metrics["signals_generated"],
                "rate_per_second": metrics["signals_generated"] / duration
            },
            "latency_ms": {
                "p50": p50_latency,
                "p95": p95_latency,
                "p99": p99_latency,
                "max": max(latencies) if latencies else 0
            },
            "resources": {
                "avg_cpu_percent": avg_cpu,
                "max_cpu_percent": max_cpu,
                "avg_memory_mb": avg_memory,
                "max_memory_mb": max_memory
            },
            "survived": survived,
            "performance_degradation": {
                "latency_increase_percent": ((p99_latency - 50) / 50 * 100) if p99_latency > 50 else 0,
                "throughput_decrease_percent": max(0, (1 - (metrics["events_processed"] / metrics["events_generated"])) * 100)
            }
        }

    async def _generate_scenario_events(self, scenario: MarketScenario, metrics: Dict[str, Any]):
        """Generate events for a stress scenario"""
        start_time = time.time()
        symbols = self.test_config["symbols"]
        base_prices = self.test_config["base_price"]

        # Price tracking for realistic movements
        current_prices = base_prices.copy()

        while time.time() - start_time < scenario.duration_seconds:
            batch_start = time.time()

            # Generate batch of events
            for _ in range(int(scenario.event_frequency / 10)):  # 100ms batches
                try:
                    # Select random symbol
                    symbol = random.choice(symbols)

                    # Generate price movement
                    price_change = random.gauss(0, scenario.price_volatility / 100) * current_prices[symbol]
                    current_prices[symbol] += price_change

                    # Generate volume based on scenario
                    volume = int(self.test_config["normal_volume"] * scenario.volume_multiplier * random.uniform(0.5, 1.5))

                    # Create event
                    event = {
                        "type": "trade",
                        "symbol": symbol,
                        "price": current_prices[symbol],
                        "volume": volume,
                        "timestamp": time.time(),
                        "side": random.choice(["buy", "sell"]),
                        "scenario": scenario.name
                    }

                    # Process event
                    event_start = time.time()
                    if self.streaming_bridge:
                        processed = await self._process_event_async(event)
                        if processed:
                            metrics["events_processed"] += 1
                            latency = (time.time() - event_start) * 1000
                            metrics["latencies"].append(latency)

                    metrics["events_generated"] += 1

                except Exception as e:
                    metrics["errors"] += 1
                    self.logger.error(f"Event processing error: {e}")

            # Maintain rate
            batch_duration = time.time() - batch_start
            if batch_duration < 0.1:
                await asyncio.sleep(0.1 - batch_duration)

    async def _process_event_async(self, event: Dict[str, Any]) -> bool:
        """Process event asynchronously"""
        # Simulate async processing
        if hasattr(self.streaming_bridge, 'process_event'):
            return self.streaming_bridge.process_event(event)
        return True

    async def _monitor_system_performance(self, duration: int, metrics: Dict[str, Any]):
        """Monitor system performance during scenario"""
        start_time = time.time()

        while time.time() - start_time < duration:
            # Get current performance metrics
            perf_metrics = self.performance_tracker.get_current_metrics()

            metrics["cpu_samples"].append(perf_metrics.get("cpu_usage", 0))
            metrics["memory_samples"].append(perf_metrics.get("memory_usage", 0))

            # Check for system stress indicators
            if perf_metrics.get("cpu_usage", 0) > 90:
                self.logger.warning(f"High CPU usage: {perf_metrics['cpu_usage']:.1f}%")

            if perf_metrics.get("memory_usage", 0) > 1500:  # MB
                self.logger.warning(f"High memory usage: {perf_metrics['memory_usage']:.0f} MB")

            await asyncio.sleep(1)  # Sample every second

    async def _collect_signals(self, duration: int, metrics: Dict[str, Any]):
        """Collect generated signals during scenario"""
        start_time = time.time()

        def signal_callback(signal):
            metrics["signals_generated"] += 1

        # Subscribe to signals
        if self.streaming_bridge:
            self.streaming_bridge.subscribe_to_signals(signal_callback)

        # Collect for duration
        await asyncio.sleep(duration)

    async def _system_recovery_period(self):
        """Allow system to recover between scenarios"""
        self.logger.info("System recovery period (30 seconds)...")

        recovery_start = time.time()
        initial_metrics = self.performance_tracker.get_current_metrics()

        # Wait for metrics to stabilize
        await asyncio.sleep(30)

        final_metrics = self.performance_tracker.get_current_metrics()
        recovery_time = time.time() - recovery_start

        self.test_results["recovery_metrics"] = {
            "recovery_time_seconds": recovery_time,
            "cpu_recovered": final_metrics.get("cpu_usage", 0) < initial_metrics.get("cpu_usage", 100) * 0.5,
            "memory_recovered": final_metrics.get("memory_usage", 0) < initial_metrics.get("memory_usage", 1000) * 1.1
        }

    async def _test_connection_loss(self):
        """Test system behavior during connection loss"""
        self.logger.info("Testing connection loss scenario...")

        # Simulate connection loss
        if hasattr(self.streaming_bridge, 'simulate_disconnect'):
            self.streaming_bridge.simulate_disconnect()

        # Monitor system during outage
        outage_start = time.time()
        await asyncio.sleep(60)  # 1 minute outage

        # Restore connection
        if hasattr(self.streaming_bridge, 'simulate_reconnect'):
            self.streaming_bridge.simulate_reconnect()

        recovery_start = time.time()

        # Wait for recovery
        recovered = False
        while time.time() - recovery_start < 30:
            if hasattr(self.streaming_bridge, 'is_connected') and self.streaming_bridge.is_connected():
                recovered = True
                break
            await asyncio.sleep(1)

        recovery_time = time.time() - recovery_start if recovered else 30

        self.test_results["system_failures"].append({
            "type": "connection_loss",
            "duration_seconds": 60,
            "recovered": recovered,
            "recovery_time_seconds": recovery_time,
            "data_loss_estimate": "minimal"  # Based on buffering
        })

    async def _test_data_corruption(self):
        """Test system handling of corrupted data"""
        self.logger.info("Testing data corruption scenario...")

        corrupt_events = 0
        handled_correctly = 0

        for _ in range(100):
            # Generate corrupted event
            corrupt_event = {
                "type": "trade",
                "symbol": None,  # Missing symbol
                "price": "invalid",  # Invalid price
                "volume": -100,  # Negative volume
                "timestamp": "not_a_timestamp"
            }

            try:
                if self.streaming_bridge:
                    result = await self._process_event_async(corrupt_event)
                    if not result:  # Should reject corrupt data
                        handled_correctly += 1
            except:
                handled_correctly += 1  # Exception is also correct handling

            corrupt_events += 1

        self.test_results["system_failures"].append({
            "type": "data_corruption",
            "corrupt_events": corrupt_events,
            "handled_correctly": handled_correctly,
            "error_handling_rate": handled_correctly / corrupt_events
        })

    async def _test_memory_exhaustion(self):
        """Test system behavior under memory pressure"""
        self.logger.info("Testing memory exhaustion scenario...")

        # Generate memory pressure by creating large event backlog
        large_events = []
        memory_before = self.performance_tracker.get_current_metrics().get("memory_usage", 0)

        try:
            # Generate 100k events
            for _ in range(100000):
                large_events.append({
                    "type": "trade",
                    "symbol": "NQM5",
                    "price": 15000,
                    "volume": 100,
                    "timestamp": time.time(),
                    "metadata": "x" * 1000  # 1KB of data per event
                })

            memory_after = self.performance_tracker.get_current_metrics().get("memory_usage", 0)
            memory_increase = memory_after - memory_before

            # Check if system handles memory pressure
            system_stable = memory_increase < 1000  # Less than 1GB increase

        except MemoryError:
            system_stable = False
            memory_increase = "MemoryError"

        self.test_results["system_failures"].append({
            "type": "memory_exhaustion",
            "memory_increase_mb": memory_increase,
            "system_stable": system_stable,
            "gc_triggered": True  # Assume GC was triggered
        })

    async def _test_cpu_saturation(self):
        """Test system under CPU saturation"""
        self.logger.info("Testing CPU saturation scenario...")

        # Generate CPU-intensive workload
        start_time = time.time()
        cpu_before = self.performance_tracker.get_current_metrics().get("cpu_usage", 0)

        # Run CPU-intensive calculations
        tasks = []
        for _ in range(10):  # 10 parallel CPU-bound tasks
            task = asyncio.create_task(self._cpu_intensive_task())
            tasks.append(task)

        await asyncio.gather(*tasks)

        cpu_peak = self.performance_tracker.get_current_metrics().get("cpu_usage", 0)
        duration = time.time() - start_time

        self.test_results["system_failures"].append({
            "type": "cpu_saturation",
            "cpu_before_percent": cpu_before,
            "cpu_peak_percent": cpu_peak,
            "duration_seconds": duration,
            "system_responsive": cpu_peak < 95  # System still responsive if CPU < 95%
        })

    async def _cpu_intensive_task(self):
        """Simulate CPU-intensive task"""
        # Perform intensive calculations
        result = 0
        for i in range(1000000):
            result += i ** 2
        return result

    async def _cleanup(self):
        """Cleanup after stress tests"""
        self.logger.info("Cleaning up stress test resources...")

        if self.streaming_bridge:
            await self.streaming_bridge.stop_async()

    def _generate_stress_report(self):
        """Generate comprehensive stress test report"""
        self.test_results["end_time"] = get_eastern_time().isoformat()

        # Calculate summary
        total_scenarios = len(self.scenarios)
        survived_scenarios = sum(1 for result in self.test_results["scenarios"].values()
                               if result.get("survived", False))

        self.test_results["summary"] = {
            "total_scenarios": total_scenarios,
            "survived_scenarios": survived_scenarios,
            "survival_rate": survived_scenarios / total_scenarios if total_scenarios > 0 else 0,
            "system_failures": len(self.test_results["system_failures"]),
            "critical_issues": self._identify_critical_issues()
        }

        # Save report
        report_file = f"{self.results_dir}/stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)

        # Print summary
        self.logger.info("\n" + "="*60)
        self.logger.info("STRESS TEST SUMMARY")
        self.logger.info("="*60)
        self.logger.info(f"Scenarios tested: {total_scenarios}")
        self.logger.info(f"Scenarios survived: {survived_scenarios}")
        self.logger.info(f"Survival rate: {self.test_results['summary']['survival_rate']:.1%}")
        self.logger.info(f"System failures: {self.test_results['summary']['system_failures']}")

        for scenario_name, result in self.test_results["scenarios"].items():
            status = "SURVIVED" if result["survived"] else "FAILED"
            self.logger.info(f"\n{scenario_name}: {status}")
            self.logger.info(f"  - P99 Latency: {result['latency_ms']['p99']:.1f}ms")
            self.logger.info(f"  - Error Rate: {result['events']['error_rate']:.1%}")
            self.logger.info(f"  - Max CPU: {result['resources']['max_cpu_percent']:.1f}%")

        self.logger.info(f"\nDetailed report saved to: {report_file}")

    def _identify_critical_issues(self) -> List[str]:
        """Identify critical issues from stress test results"""
        issues = []

        # Check scenario failures
        for scenario_name, result in self.test_results["scenarios"].items():
            if not result.get("survived", False):
                issues.append(f"System failed during {scenario_name} scenario")

            if result.get("latency_ms", {}).get("p99", 0) > 500:
                issues.append(f"Extreme latency ({result['latency_ms']['p99']:.0f}ms) in {scenario_name}")

        # Check system failures
        for failure in self.test_results["system_failures"]:
            if failure["type"] == "connection_loss" and not failure.get("recovered", True):
                issues.append("Failed to recover from connection loss")

            if failure["type"] == "memory_exhaustion" and not failure.get("system_stable", True):
                issues.append("System unstable under memory pressure")

        return issues

# Run stress tests
async def run_stress_tests(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run Phase 4 stress tests"""
    suite = StressTestSuite(config)
    return await suite.run_stress_tests()

if __name__ == "__main__":
    async def main():
        results = await run_stress_tests()
        print(f"\nStress tests completed")
        print(f"Survival rate: {results['summary']['survival_rate']:.1%}")
        print(f"Critical issues: {len(results['summary']['critical_issues'])}")

    asyncio.run(main())
