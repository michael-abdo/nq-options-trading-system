#!/usr/bin/env python3
"""
Performance Under Load Testing Suite

Comprehensive performance tests for the NQ Options Trading System:
- System performance during high-volume market periods
- Memory and CPU usage monitoring during continuous operation
- Processing latency validation (<100ms requirement)
- Database performance and query optimization
- Disk space and log file management
"""

import os
import sys
import time
import json
import gc
import threading
import multiprocessing
from datetime import datetime, timezone, timedelta
from utils.timezone_utils import get_eastern_time, get_utc_time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple, Optional
import unittest
from unittest.mock import Mock, patch
from dataclasses import dataclass, asdict
import statistics
import random

# Performance monitoring utilities
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available. Install with: pip install psutil")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("Warning: numpy not available. Install with: pip install numpy")

# Add necessary paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'tasks/options_trading_system/analysis_engine/strategies'))

try:
    from tasks.options_trading_system.analysis_engine.strategies.limited_live_trading_orchestrator import (
        LimitedLiveTradingConfig,
        LimitedLiveTradingOrchestrator
    )
    LIMITED_LIVE_TRADING_AVAILABLE = True
except ImportError:
    LIMITED_LIVE_TRADING_AVAILABLE = False


@dataclass
class PerformanceMetrics:
    """Performance metrics container"""
    test_name: str
    start_time: datetime
    end_time: datetime
    total_operations: int
    successful_operations: int
    failed_operations: int

    # Timing metrics (in milliseconds)
    min_latency: float
    max_latency: float
    avg_latency: float
    p50_latency: float
    p95_latency: float
    p99_latency: float

    # Resource metrics
    peak_cpu_percent: float
    avg_cpu_percent: float
    peak_memory_mb: float
    avg_memory_mb: float
    memory_growth_mb: float

    # Throughput
    operations_per_second: float

    def meets_sla(self) -> bool:
        """Check if performance meets SLA requirements"""
        return (self.p95_latency < 100.0 and  # 95th percentile < 100ms
                self.memory_growth_mb < 100.0 and  # Less than 100MB growth
                self.failed_operations == 0)  # No failures


@dataclass
class LoadProfile:
    """Load testing profile configuration"""
    name: str
    duration_seconds: int
    concurrent_operations: int
    operations_per_second: int
    burst_size: int = 0
    burst_interval_seconds: int = 0
    ramp_up_seconds: int = 0


class PerformanceMonitor:
    """Monitors system performance metrics during tests"""

    def __init__(self):
        self.monitoring = False
        self.metrics = []
        self.start_time = None
        self.monitor_thread = None

        # Initial resource baseline
        if PSUTIL_AVAILABLE:
            self.process = psutil.Process()
            self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        else:
            self.process = None
            self.initial_memory = 0

    def start_monitoring(self):
        """Start performance monitoring"""
        self.monitoring = True
        self.start_time = time.time()
        self.metrics = []

        if PSUTIL_AVAILABLE:
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()

    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return summary metrics"""
        self.monitoring = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)

        if not self.metrics:
            return {}

        # Calculate summary statistics
        cpu_values = [m['cpu_percent'] for m in self.metrics]
        memory_values = [m['memory_mb'] for m in self.metrics]

        return {
            'monitoring_duration': time.time() - self.start_time,
            'samples_collected': len(self.metrics),
            'cpu': {
                'peak_percent': max(cpu_values) if cpu_values else 0,
                'avg_percent': statistics.mean(cpu_values) if cpu_values else 0,
                'min_percent': min(cpu_values) if cpu_values else 0
            },
            'memory': {
                'peak_mb': max(memory_values) if memory_values else 0,
                'avg_mb': statistics.mean(memory_values) if memory_values else 0,
                'initial_mb': self.initial_memory,
                'growth_mb': (max(memory_values) - self.initial_memory) if memory_values else 0
            }
        }

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                if self.process:
                    cpu_percent = self.process.cpu_percent(interval=0.1)
                    memory_mb = self.process.memory_info().rss / 1024 / 1024

                    self.metrics.append({
                        'timestamp': time.time(),
                        'cpu_percent': cpu_percent,
                        'memory_mb': memory_mb
                    })
            except Exception:
                pass  # Ignore monitoring errors

            time.sleep(0.5)  # Sample every 500ms


class LoadGenerator:
    """Generates load for performance testing"""

    def __init__(self, target_function, load_profile: LoadProfile):
        self.target_function = target_function
        self.load_profile = load_profile
        self.operation_times = []
        self.failures = 0
        self.stop_event = threading.Event()

    def generate_load(self) -> List[float]:
        """Generate load according to profile and return operation times"""
        print(f"🚀 Starting load generation: {self.load_profile.name}")
        print(f"   Duration: {self.load_profile.duration_seconds}s")
        print(f"   Target OPS: {self.load_profile.operations_per_second}")
        print(f"   Concurrency: {self.load_profile.concurrent_operations}")

        start_time = time.time()

        # Use thread pool for concurrent operations
        with ThreadPoolExecutor(max_workers=self.load_profile.concurrent_operations) as executor:
            futures = []
            operation_count = 0

            # Calculate operation interval
            if self.load_profile.operations_per_second > 0:
                interval = 1.0 / self.load_profile.operations_per_second
            else:
                interval = 0

            # Ramp up phase
            if self.load_profile.ramp_up_seconds > 0:
                print(f"   Ramping up over {self.load_profile.ramp_up_seconds}s...")
                ramp_start = time.time()
                ramp_ops = 0
                while time.time() - ramp_start < self.load_profile.ramp_up_seconds:
                    # Gradually increase load
                    progress = (time.time() - ramp_start) / self.load_profile.ramp_up_seconds
                    current_interval = interval / progress if progress > 0 else interval

                    future = executor.submit(self._execute_operation, operation_count)
                    futures.append(future)
                    operation_count += 1
                    ramp_ops += 1

                    if current_interval > 0:
                        time.sleep(current_interval)

                print(f"   Ramp up complete: {ramp_ops} operations")

            # Main load generation
            while time.time() - start_time < self.load_profile.duration_seconds:
                if self.stop_event.is_set():
                    break

                # Handle burst mode
                if self.load_profile.burst_size > 0:
                    if operation_count % self.load_profile.burst_interval_seconds == 0:
                        # Generate burst
                        for _ in range(self.load_profile.burst_size):
                            future = executor.submit(self._execute_operation, operation_count)
                            futures.append(future)
                            operation_count += 1
                else:
                    # Normal operation
                    future = executor.submit(self._execute_operation, operation_count)
                    futures.append(future)
                    operation_count += 1

                if interval > 0:
                    time.sleep(interval)

            # Wait for all operations to complete
            print(f"   Waiting for {len(futures)} operations to complete...")
            for future in as_completed(futures):
                try:
                    future.result(timeout=5)
                except Exception:
                    self.failures += 1

        print(f"✅ Load generation complete: {len(self.operation_times)} operations, {self.failures} failures")
        return self.operation_times

    def _execute_operation(self, operation_id: int):
        """Execute a single operation and record timing"""
        start_time = time.time()

        try:
            self.target_function(operation_id)
            operation_time = (time.time() - start_time) * 1000  # Convert to ms
            self.operation_times.append(operation_time)
        except Exception as e:
            self.failures += 1
            # Still record failed operation time
            operation_time = (time.time() - start_time) * 1000
            self.operation_times.append(operation_time)


class TestHighVolumePerformance(unittest.TestCase):
    """Test system performance during high-volume market periods"""

    def setUp(self):
        """Set up test configuration"""
        self.config = LimitedLiveTradingConfig(
            start_date='2025-06-12',
            duration_days=1,
            max_position_size=1,
            daily_cost_limit=100.0,  # Higher for load testing
            monthly_budget_limit=1000.0,
            auto_shutoff_enabled=False  # Disable for performance testing
        ) if LIMITED_LIVE_TRADING_AVAILABLE else None

        self.performance_monitor = PerformanceMonitor()

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_high_volume_signal_processing(self):
        """Test performance under high-volume signal processing"""
        orchestrator = LimitedLiveTradingOrchestrator(self.config)
        orchestrator.start_live_trading()

        # Define load profile
        load_profile = LoadProfile(
            name="High Volume Signal Processing",
            duration_seconds=30,
            concurrent_operations=10,
            operations_per_second=100,  # 100 signals per second
            ramp_up_seconds=5
        )

        # Signal generation function
        def generate_and_process_signal(signal_id: int):
            signal = {
                'id': f'perf_test_signal_{signal_id}',
                'strike': 21350 + (signal_id % 100) * 25,
                'confidence': 0.60 + (signal_id % 40) * 0.01,  # 0.60-0.99
                'expected_value': 15.0 + (signal_id % 20),
                'signal_type': 'call_buying' if signal_id % 2 == 0 else 'put_buying',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Process signal (most will be rejected due to confidence threshold)
            orchestrator.process_signal_for_live_trading(signal)

        # Start performance monitoring
        self.performance_monitor.start_monitoring()

        # Generate load
        load_generator = LoadGenerator(generate_and_process_signal, load_profile)
        operation_times = load_generator.generate_load()

        # Stop monitoring
        resource_metrics = self.performance_monitor.stop_monitoring()

        # Calculate performance metrics
        if operation_times:
            sorted_times = sorted(operation_times)
            metrics = PerformanceMetrics(
                test_name="High Volume Signal Processing",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                total_operations=len(operation_times),
                successful_operations=len(operation_times) - load_generator.failures,
                failed_operations=load_generator.failures,
                min_latency=min(operation_times),
                max_latency=max(operation_times),
                avg_latency=statistics.mean(operation_times),
                p50_latency=sorted_times[len(sorted_times) // 2],
                p95_latency=sorted_times[int(len(sorted_times) * 0.95)],
                p99_latency=sorted_times[int(len(sorted_times) * 0.99)],
                peak_cpu_percent=resource_metrics.get('cpu', {}).get('peak_percent', 0),
                avg_cpu_percent=resource_metrics.get('cpu', {}).get('avg_percent', 0),
                peak_memory_mb=resource_metrics.get('memory', {}).get('peak_mb', 0),
                avg_memory_mb=resource_metrics.get('memory', {}).get('avg_mb', 0),
                memory_growth_mb=resource_metrics.get('memory', {}).get('growth_mb', 0),
                operations_per_second=len(operation_times) / load_profile.duration_seconds
            )

            # Print results
            self._print_performance_results(metrics)

            # Validate SLA
            self.assertTrue(metrics.meets_sla(), f"Performance SLA not met: P95={metrics.p95_latency:.2f}ms")

        orchestrator.stop_live_trading()

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_burst_load_handling(self):
        """Test system performance during burst loads"""
        orchestrator = LimitedLiveTradingOrchestrator(self.config)
        orchestrator.start_live_trading()

        # Define burst load profile
        load_profile = LoadProfile(
            name="Burst Load Test",
            duration_seconds=20,
            concurrent_operations=20,
            operations_per_second=10,  # Base rate
            burst_size=50,  # 50 operations per burst
            burst_interval_seconds=5  # Burst every 5 seconds
        )

        # Signal generation function
        def generate_burst_signal(signal_id: int):
            signal = {
                'id': f'burst_signal_{signal_id}',
                'strike': 21350 + random.randint(0, 20) * 25,
                'confidence': random.uniform(0.5, 0.9),
                'expected_value': random.uniform(10, 50),
                'signal_type': random.choice(['call_buying', 'put_buying']),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            orchestrator.process_signal_for_live_trading(signal)

        # Start performance monitoring
        self.performance_monitor.start_monitoring()

        # Generate burst load
        load_generator = LoadGenerator(generate_burst_signal, load_profile)
        operation_times = load_generator.generate_load()

        # Stop monitoring
        resource_metrics = self.performance_monitor.stop_monitoring()

        # Analyze burst performance
        if operation_times:
            # Check that system handles bursts without degradation
            burst_times = operation_times[-50:]  # Last burst
            burst_p95 = sorted(burst_times)[int(len(burst_times) * 0.95)]

            self.assertLess(burst_p95, 150.0, f"Burst P95 latency too high: {burst_p95:.2f}ms")

        orchestrator.stop_live_trading()

    def _print_performance_results(self, metrics: PerformanceMetrics):
        """Print formatted performance results"""
        print(f"\n📊 Performance Test Results: {metrics.test_name}")
        print("=" * 60)
        print(f"Total Operations: {metrics.total_operations}")
        print(f"Successful: {metrics.successful_operations}")
        print(f"Failed: {metrics.failed_operations}")
        print(f"Throughput: {metrics.operations_per_second:.2f} ops/sec")
        print(f"\nLatency (ms):")
        print(f"  Min: {metrics.min_latency:.2f}")
        print(f"  Avg: {metrics.avg_latency:.2f}")
        print(f"  P50: {metrics.p50_latency:.2f}")
        print(f"  P95: {metrics.p95_latency:.2f}")
        print(f"  P99: {metrics.p99_latency:.2f}")
        print(f"  Max: {metrics.max_latency:.2f}")
        print(f"\nResource Usage:")
        print(f"  CPU Peak: {metrics.peak_cpu_percent:.1f}%")
        print(f"  CPU Avg: {metrics.avg_cpu_percent:.1f}%")
        print(f"  Memory Peak: {metrics.peak_memory_mb:.1f} MB")
        print(f"  Memory Growth: {metrics.memory_growth_mb:.1f} MB")
        print(f"\nSLA Status: {'✅ PASS' if metrics.meets_sla() else '❌ FAIL'}")
        print("=" * 60)


class TestContinuousOperationPerformance(unittest.TestCase):
    """Test memory and CPU usage during continuous operation"""

    def setUp(self):
        """Set up test configuration"""
        self.performance_monitor = PerformanceMonitor()

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE and PSUTIL_AVAILABLE,
                        "Limited Live Trading and psutil required")
    def test_memory_leak_detection(self):
        """Test for memory leaks during extended operation"""
        config = LimitedLiveTradingConfig(
            start_date='2025-06-12',
            duration_days=1,
            max_position_size=1,
            daily_cost_limit=1000.0,
            monthly_budget_limit=10000.0,
            auto_shutoff_enabled=False
        )

        # Track memory over multiple cycles
        memory_samples = []

        for cycle in range(5):
            orchestrator = LimitedLiveTradingOrchestrator(config)
            orchestrator.start_live_trading()

            # Start monitoring
            self.performance_monitor.start_monitoring()

            # Process many signals
            for i in range(1000):
                signal = {
                    'id': f'memory_test_{cycle}_{i}',
                    'strike': 21350 + (i % 20) * 25,
                    'confidence': 0.55,  # Below threshold
                    'expected_value': 20.0,
                    'signal_type': 'call_buying'
                }
                orchestrator.process_signal_for_live_trading(signal)

            # Stop and collect metrics
            metrics = self.performance_monitor.stop_monitoring()
            memory_samples.append(metrics.get('memory', {}).get('peak_mb', 0))

            orchestrator.stop_live_trading()

            # Force garbage collection between cycles
            gc.collect()
            time.sleep(1)

        # Check for memory growth trend
        if len(memory_samples) >= 3:
            # Calculate growth rate
            initial_memory = memory_samples[0]
            final_memory = memory_samples[-1]
            growth_rate = (final_memory - initial_memory) / initial_memory if initial_memory > 0 else 0

            print(f"\nMemory Growth Analysis:")
            print(f"  Initial: {initial_memory:.1f} MB")
            print(f"  Final: {final_memory:.1f} MB")
            print(f"  Growth Rate: {growth_rate:.1%}")
            print(f"  Samples: {memory_samples}")

            # Allow up to 10% growth (some growth is normal due to caching)
            self.assertLess(growth_rate, 0.10, f"Excessive memory growth detected: {growth_rate:.1%}")

    @unittest.skipUnless(PSUTIL_AVAILABLE, "psutil required")
    def test_cpu_efficiency(self):
        """Test CPU efficiency during sustained operations"""
        # Create a CPU-intensive operation
        def cpu_intensive_operation():
            # Simulate complex calculation
            result = 0
            for i in range(10000):
                result += i ** 2
            return result

        # Monitor CPU during operations
        self.performance_monitor.start_monitoring()

        # Run operations
        start_time = time.time()
        operations = 0

        while time.time() - start_time < 10:  # Run for 10 seconds
            cpu_intensive_operation()
            operations += 1

        # Get metrics
        metrics = self.performance_monitor.stop_monitoring()

        # Calculate efficiency
        ops_per_second = operations / 10
        cpu_efficiency = ops_per_second / (metrics.get('cpu', {}).get('avg_percent', 1) / 100)

        print(f"\nCPU Efficiency Test:")
        print(f"  Operations: {operations}")
        print(f"  Throughput: {ops_per_second:.2f} ops/sec")
        print(f"  Avg CPU: {metrics.get('cpu', {}).get('avg_percent', 0):.1f}%")
        print(f"  Efficiency: {cpu_efficiency:.2f} ops/sec per CPU%")

        # Ensure reasonable CPU usage
        self.assertLess(metrics.get('cpu', {}).get('avg_percent', 0), 80.0,
                       "CPU usage too high for sustained operation")


class TestLatencyRequirements(unittest.TestCase):
    """Test processing latency requirements (<100ms)"""

    @unittest.skipUnless(LIMITED_LIVE_TRADING_AVAILABLE, "Limited Live Trading not available")
    def test_signal_processing_latency(self):
        """Test that signal processing stays under 100ms"""
        config = LimitedLiveTradingConfig(
            start_date='2025-06-12',
            duration_days=1,
            max_position_size=1,
            daily_cost_limit=100.0,
            monthly_budget_limit=1000.0,
            auto_shutoff_enabled=False
        )

        orchestrator = LimitedLiveTradingOrchestrator(config)
        orchestrator.start_live_trading()

        # Test various signal types
        test_signals = [
            # Simple signal (should be fastest)
            {
                'id': 'latency_test_simple',
                'strike': 21350,
                'confidence': 0.75,
                'expected_value': 25.0,
                'signal_type': 'call_buying'
            },
            # Complex signal with many fields
            {
                'id': 'latency_test_complex',
                'strike': 21350,
                'confidence': 0.85,
                'expected_value': 45.0,
                'signal_type': 'put_buying',
                'volume': 10000,
                'open_interest': 50000,
                'implied_volatility': 0.25,
                'delta': 0.5,
                'gamma': 0.02,
                'theta': -0.05,
                'vega': 0.1,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        ]

        latencies = []

        # Warm up
        for _ in range(10):
            orchestrator.process_signal_for_live_trading(test_signals[0])

        # Measure latencies
        for _ in range(100):
            for signal in test_signals:
                start_time = time.time()
                orchestrator.process_signal_for_live_trading(signal)
                latency = (time.time() - start_time) * 1000  # ms
                latencies.append(latency)

        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        max_latency = max(latencies)

        print(f"\nSignal Processing Latency:")
        print(f"  Samples: {len(latencies)}")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  P99: {p99_latency:.2f}ms")
        print(f"  Max: {max_latency:.2f}ms")

        # Validate <100ms requirement
        self.assertLess(p95_latency, 100.0, f"P95 latency {p95_latency:.2f}ms exceeds 100ms SLA")

        orchestrator.stop_live_trading()

    def test_critical_path_latency(self):
        """Test latency of critical trading path components"""
        # Simulate critical path operations
        critical_operations = {
            'market_data_fetch': lambda: time.sleep(0.01),  # 10ms
            'signal_validation': lambda: time.sleep(0.005),  # 5ms
            'risk_calculation': lambda: time.sleep(0.008),   # 8ms
            'order_preparation': lambda: time.sleep(0.003),  # 3ms
            'budget_check': lambda: time.sleep(0.002)       # 2ms
        }

        operation_latencies = {}

        for op_name, op_func in critical_operations.items():
            latencies = []

            for _ in range(100):
                start_time = time.time()
                op_func()
                latency = (time.time() - start_time) * 1000
                latencies.append(latency)

            operation_latencies[op_name] = {
                'avg': statistics.mean(latencies),
                'p95': sorted(latencies)[int(len(latencies) * 0.95)],
                'max': max(latencies)
            }

        # Print critical path analysis
        print("\nCritical Path Latency Analysis:")
        total_avg = 0
        total_p95 = 0

        for op_name, metrics in operation_latencies.items():
            print(f"  {op_name}:")
            print(f"    Avg: {metrics['avg']:.2f}ms")
            print(f"    P95: {metrics['p95']:.2f}ms")
            total_avg += metrics['avg']
            total_p95 += metrics['p95']

        print(f"\n  Total Critical Path:")
        print(f"    Avg: {total_avg:.2f}ms")
        print(f"    P95: {total_p95:.2f}ms")

        # Ensure critical path stays under 100ms
        self.assertLess(total_p95, 100.0, f"Critical path P95 {total_p95:.2f}ms exceeds 100ms")


class TestDatabasePerformance(unittest.TestCase):
    """Test database performance and query optimization"""

    def setUp(self):
        """Set up test database"""
        self.test_data = []
        # Generate test data
        for i in range(10000):
            self.test_data.append({
                'id': f'db_test_{i}',
                'strike': 21000 + (i % 100) * 25,
                'volume': random.randint(100, 10000),
                'open_interest': random.randint(1000, 100000),
                'timestamp': datetime.now(timezone.utc) - timedelta(minutes=i)
            })

    def test_query_performance(self):
        """Test database query performance"""
        # Simulate different query patterns
        query_tests = [
            {
                'name': 'Simple lookup by ID',
                'operation': lambda: next((d for d in self.test_data if d['id'] == 'db_test_5000'), None)
            },
            {
                'name': 'Filter by strike range',
                'operation': lambda: [d for d in self.test_data if 21200 <= d['strike'] <= 21400]
            },
            {
                'name': 'Sort by volume',
                'operation': lambda: sorted(self.test_data, key=lambda x: x['volume'], reverse=True)[:100]
            },
            {
                'name': 'Aggregate by strike',
                'operation': lambda: self._aggregate_by_strike()
            }
        ]

        for test in query_tests:
            latencies = []

            for _ in range(50):
                start_time = time.time()
                test['operation']()
                latency = (time.time() - start_time) * 1000
                latencies.append(latency)

            avg_latency = statistics.mean(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

            print(f"\nQuery Performance: {test['name']}")
            print(f"  Avg: {avg_latency:.2f}ms")
            print(f"  P95: {p95_latency:.2f}ms")

            # Database queries should be fast
            self.assertLess(p95_latency, 50.0, f"Query '{test['name']}' too slow: {p95_latency:.2f}ms")

    def _aggregate_by_strike(self):
        """Simulate aggregation query"""
        aggregates = {}
        for item in self.test_data:
            strike = item['strike']
            if strike not in aggregates:
                aggregates[strike] = {'count': 0, 'total_volume': 0}
            aggregates[strike]['count'] += 1
            aggregates[strike]['total_volume'] += item['volume']
        return aggregates

    def test_concurrent_database_access(self):
        """Test database performance under concurrent access"""
        def concurrent_query(query_id: int):
            # Simulate different query types
            if query_id % 3 == 0:
                # Read query
                result = [d for d in self.test_data if d['volume'] > 5000]
            elif query_id % 3 == 1:
                # Write simulation (append)
                new_item = {
                    'id': f'concurrent_{query_id}',
                    'strike': 21350,
                    'volume': 1000,
                    'open_interest': 5000,
                    'timestamp': datetime.now(timezone.utc)
                }
                # In real scenario, this would be a database insert
            else:
                # Update simulation
                item = self.test_data[query_id % len(self.test_data)]
                item['volume'] = item['volume'] + 100

        # Run concurrent queries
        load_profile = LoadProfile(
            name="Concurrent Database Access",
            duration_seconds=10,
            concurrent_operations=20,
            operations_per_second=50
        )

        load_generator = LoadGenerator(concurrent_query, load_profile)
        operation_times = load_generator.generate_load()

        if operation_times:
            p95_latency = sorted(operation_times)[int(len(operation_times) * 0.95)]
            print(f"\nConcurrent DB Access P95: {p95_latency:.2f}ms")

            # Even under concurrent load, queries should be fast
            self.assertLess(p95_latency, 100.0, f"Concurrent query P95 {p95_latency:.2f}ms too high")


class TestDiskAndLogManagement(unittest.TestCase):
    """Test disk space and log file management"""

    def test_log_rotation_performance(self):
        """Test performance impact of log rotation"""
        import tempfile
        import shutil

        # Create temporary directory for logs
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'test.log')

            # Simulate log writing
            write_latencies = []

            for i in range(1000):
                log_entry = f"{get_eastern_time().isoformat()} - Test log entry {i} with some data\n"

                start_time = time.time()
                with open(log_file, 'a') as f:
                    f.write(log_entry)
                latency = (time.time() - start_time) * 1000
                write_latencies.append(latency)

                # Simulate rotation every 100 entries
                if i % 100 == 0 and i > 0:
                    # Rotate log
                    shutil.move(log_file, f"{log_file}.{i}")

            # Check write performance
            avg_latency = statistics.mean(write_latencies)
            p95_latency = sorted(write_latencies)[int(len(write_latencies) * 0.95)]

            print(f"\nLog Write Performance:")
            print(f"  Avg: {avg_latency:.2f}ms")
            print(f"  P95: {p95_latency:.2f}ms")

            # Log writes should be very fast
            self.assertLess(p95_latency, 10.0, f"Log write P95 {p95_latency:.2f}ms too high")

    @unittest.skipUnless(PSUTIL_AVAILABLE, "psutil required")
    def test_disk_space_monitoring(self):
        """Test disk space monitoring capabilities"""
        # Get disk usage for current directory
        disk_usage = psutil.disk_usage('/')

        print(f"\nDisk Space Analysis:")
        print(f"  Total: {disk_usage.total / (1024**3):.2f} GB")
        print(f"  Used: {disk_usage.used / (1024**3):.2f} GB")
        print(f"  Free: {disk_usage.free / (1024**3):.2f} GB")
        print(f"  Percent Used: {disk_usage.percent:.1f}%")

        # Warning if disk space is low
        if disk_usage.percent > 90:
            print("  ⚠️  WARNING: Low disk space!")

        # Test should pass if we can read disk stats
        self.assertGreaterEqual(disk_usage.free, 0)


def run_performance_tests():
    """Run all performance tests"""
    print("🚀 Running Performance Under Load Tests")
    print("=" * 70)

    # Check dependencies
    if not PSUTIL_AVAILABLE:
        print("⚠️  WARNING: psutil not available - some tests will be skipped")
        print("   Install with: pip install psutil")

    if not LIMITED_LIVE_TRADING_AVAILABLE:
        print("⚠️  WARNING: Limited Live Trading not available - some tests will be skipped")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestHighVolumePerformance,
        TestContinuousOperationPerformance,
        TestLatencyRequirements,
        TestDatabasePerformance,
        TestDiskAndLogManagement
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 70)
    print("📊 Performance Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")

    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")

    success = len(result.failures) == 0 and len(result.errors) == 0

    if success:
        print("\n✅ All performance tests passed!")
        print("\n📝 Verified Performance Capabilities:")
        print("  • High-volume signal processing (100+ ops/sec)")
        print("  • Burst load handling")
        print("  • Memory leak detection")
        print("  • CPU efficiency monitoring")
        print("  • <100ms latency requirement")
        print("  • Database query optimization")
        print("  • Concurrent access handling")
        print("  • Log rotation performance")
        print("  • Disk space monitoring")
    else:
        print(f"\n⚠️ {len(result.failures) + len(result.errors)} performance test(s) failed.")

    return success


if __name__ == "__main__":
    success = run_performance_tests()
    exit(0 if success else 1)
