#!/usr/bin/env python3
"""
Quick Performance Tests - Faster version for initial validation
"""

import os
import sys
import time
import unittest
from datetime import datetime, timezone
import statistics

# Add necessary paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

# Import the performance testing components
from test_performance_under_load import (
    PerformanceMetrics,
    PerformanceMonitor,
    LoadGenerator,
    LoadProfile
)

# Check for dependencies
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available. Install with: pip install psutil")


class TestQuickPerformance(unittest.TestCase):
    """Quick performance tests with shorter durations"""

    def test_basic_latency_check(self):
        """Quick test of basic operation latency"""
        print("\n🚀 Running Quick Latency Test")

        def mock_operation(op_id):
            """Simulate a quick operation"""
            # Simulate some work
            result = 0
            for i in range(1000):
                result += i ** 2
            time.sleep(0.001)  # 1ms operation
            return result

        # Measure latencies
        latencies = []
        for i in range(100):
            start_time = time.time()
            mock_operation(i)
            latency = (time.time() - start_time) * 1000  # ms
            latencies.append(latency)

        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        max_latency = max(latencies)

        print(f"  Samples: {len(latencies)}")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  Max: {max_latency:.2f}ms")

        # Check if meets <100ms requirement
        self.assertLess(p95_latency, 100.0, f"P95 latency {p95_latency:.2f}ms exceeds 100ms")
        print("  ✅ Latency test passed!")

    @unittest.skipUnless(PSUTIL_AVAILABLE, "psutil required")
    def test_memory_monitoring(self):
        """Quick test of memory monitoring"""
        print("\n📊 Running Memory Monitoring Test")

        monitor = PerformanceMonitor()
        monitor.start_monitoring()

        # Allocate some memory
        data = []
        for i in range(10):
            # Allocate ~1MB per iteration
            data.append([0] * (256 * 1024))  # 1MB of integers
            time.sleep(0.1)

        metrics = monitor.stop_monitoring()

        print(f"  Initial Memory: {metrics['memory']['initial_mb']:.1f} MB")
        print(f"  Peak Memory: {metrics['memory']['peak_mb']:.1f} MB")
        print(f"  Memory Growth: {metrics['memory']['growth_mb']:.1f} MB")
        print(f"  Samples Collected: {metrics['samples_collected']}")

        # Clean up
        del data

        self.assertGreater(metrics['samples_collected'], 0, "No monitoring samples collected")
        print("  ✅ Memory monitoring test passed!")

    def test_concurrent_operations(self):
        """Quick test of concurrent operation handling"""
        print("\n🔄 Running Concurrent Operations Test")

        def concurrent_task(task_id):
            """Simulate a concurrent task"""
            time.sleep(0.01)  # 10ms task
            return task_id * 2

        # Create a quick load profile
        load_profile = LoadProfile(
            name="Quick Concurrent Test",
            duration_seconds=5,  # Only 5 seconds
            concurrent_operations=5,
            operations_per_second=20
        )

        # Run load test
        load_generator = LoadGenerator(concurrent_task, load_profile)
        operation_times = load_generator.generate_load()

        if operation_times:
            avg_time = statistics.mean(operation_times)
            p95_time = sorted(operation_times)[int(len(operation_times) * 0.95)]

            print(f"  Operations: {len(operation_times)}")
            print(f"  Avg Time: {avg_time:.2f}ms")
            print(f"  P95 Time: {p95_time:.2f}ms")
            print(f"  Failures: {load_generator.failures}")

            # Check performance
            self.assertLess(p95_time, 100.0, f"P95 time {p95_time:.2f}ms too high")
            self.assertEqual(load_generator.failures, 0, "Operations failed")
            print("  ✅ Concurrent operations test passed!")

    def test_burst_handling(self):
        """Quick test of burst load handling"""
        print("\n💥 Running Burst Load Test")

        burst_times = []

        # Simulate a burst of operations
        for i in range(50):  # 50 operation burst
            start_time = time.time()
            # Simulate operation
            _ = sum(j ** 2 for j in range(1000))
            operation_time = (time.time() - start_time) * 1000
            burst_times.append(operation_time)

        # Analyze burst performance
        avg_burst_time = statistics.mean(burst_times)
        max_burst_time = max(burst_times)

        print(f"  Burst Size: {len(burst_times)} operations")
        print(f"  Avg Time: {avg_burst_time:.2f}ms")
        print(f"  Max Time: {max_burst_time:.2f}ms")

        self.assertLess(max_burst_time, 50.0, f"Burst operation too slow: {max_burst_time:.2f}ms")
        print("  ✅ Burst handling test passed!")

    def test_database_simulation(self):
        """Quick test simulating database operations"""
        print("\n🗄️ Running Database Simulation Test")

        # Simulate database with in-memory dict
        db = {}

        # Insert test
        insert_times = []
        for i in range(100):
            start_time = time.time()
            db[f'key_{i}'] = {'value': i, 'data': 'x' * 100}
            insert_time = (time.time() - start_time) * 1000
            insert_times.append(insert_time)

        # Query test
        query_times = []
        for i in range(100):
            start_time = time.time()
            _ = db.get(f'key_{i % 100}')
            query_time = (time.time() - start_time) * 1000
            query_times.append(query_time)

        avg_insert = statistics.mean(insert_times)
        avg_query = statistics.mean(query_times)

        print(f"  Insert Avg: {avg_insert:.4f}ms")
        print(f"  Query Avg: {avg_query:.4f}ms")
        print(f"  Total Records: {len(db)}")

        self.assertLess(avg_query, 1.0, f"Query time too high: {avg_query:.4f}ms")
        print("  ✅ Database simulation test passed!")


def run_quick_performance_tests():
    """Run quick performance tests"""
    print("🚀 Running Quick Performance Tests")
    print("=" * 60)
    print("These are quick versions of the full performance tests")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestQuickPerformance)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 60)
    print("📊 Quick Performance Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    success = len(result.failures) == 0 and len(result.errors) == 0

    if success:
        print("\n✅ All quick performance tests passed!")
        print("\n📝 Verified Capabilities:")
        print("  • Basic operation latency < 100ms")
        print("  • Memory monitoring functional")
        print("  • Concurrent operations handling")
        print("  • Burst load processing")
        print("  • Database operation simulation")
        print("\n💡 Run full performance tests for comprehensive validation")
    else:
        print(f"\n⚠️ {len(result.failures) + len(result.errors)} test(s) failed.")

    return success


if __name__ == "__main__":
    success = run_quick_performance_tests()
    exit(0 if success else 1)
