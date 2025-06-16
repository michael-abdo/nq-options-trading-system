#!/usr/bin/env python3
"""
Performance and Latency Benchmark Tests - Verify sub-5-second processing targets
"""

import unittest
from unittest.mock import Mock, patch
import os
import sys
import time
import threading
from datetime import datetime, timezone, timedelta
import statistics
import random

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from ..streaming_bridge import StreamingBridge, create_streaming_bridge
from ..event_processor import EventProcessor, create_standard_processor
from ..pressure_aggregator import RealTimePressureEngine, create_standard_engine
from ..data_validator import StreamingDataValidator, create_mbo_validation_rules
from ..baseline_context_manager import RealTimeBaselineManager, create_baseline_manager


class PerformanceTimer:
    """High-precision timer for latency measurements"""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        """Start timing"""
        self.start_time = time.perf_counter()

    def stop(self):
        """Stop timing and return elapsed milliseconds"""
        self.end_time = time.perf_counter()
        return (self.end_time - self.start_time) * 1000  # Convert to ms

    def elapsed_ms(self):
        """Get elapsed time in milliseconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time) * 1000
        return 0


class TestPerformanceBenchmarks(unittest.TestCase):
    """Test performance benchmarks and latency requirements"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'mode': 'development',
            'data_simulation': True,
            'market_hours_enforcement': False
        }

    def test_end_to_end_latency_benchmark(self):
        """Test end-to-end latency from MBO event to IFD signal"""
        print("\n🎯 Testing End-to-End Latency Benchmark")

        # Create all components
        processor = create_standard_processor()
        pressure_engine = create_standard_engine()
        validator = StreamingDataValidator(create_mbo_validation_rules())
        baseline_manager = create_baseline_manager("test_benchmark.db")

        # Track latencies
        latencies = []

        def process_batch(batch):
            """Process batch and measure latency"""
            for event in batch:
                timer = PerformanceTimer()
                timer.start()

                try:
                    # 1. Validate (should be very fast)
                    should_process, validation_result = validator.validate_streaming_data(event)

                    if should_process:
                        # 2. Generate pressure metrics
                        pressure_metrics_list = pressure_engine.process_mbo_event(event)

                        if pressure_metrics_list:
                            for metrics in pressure_metrics_list:
                                # 3. Update baseline
                                context = baseline_manager.update_baseline(
                                    strike=metrics.strike,
                                    option_type=metrics.option_type,
                                    pressure_ratio=metrics.pressure_ratio,
                                    volume=metrics.total_volume,
                                    confidence=metrics.confidence,
                                    timestamp=metrics.time_window
                                )

                                # 4. Check for signals
                                if context.anomaly_detected:
                                    elapsed = timer.stop()
                                    latencies.append(elapsed)
                except Exception as e:
                    elapsed = timer.stop()
                    print(f"    Error processing event: {e}")

        # Start processing
        processor.register_batch_callback(process_batch)
        processor.start_processing()

        # Generate test events
        print("    Generating 1000 test events...")
        base_time = datetime.now(timezone.utc)

        for i in range(1000):
            event = self._create_test_event(base_time + timedelta(milliseconds=i))
            processor.process_event(event)

        # Wait for processing
        time.sleep(2)
        processor.stop_processing()

        # Analyze results
        if latencies:
            avg_latency = statistics.mean(latencies)
            max_latency = max(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile

            print(f"    📊 Latency Results:")
            print(f"       Events processed: {len(latencies)}")
            print(f"       Average latency: {avg_latency:.2f}ms")
            print(f"       Maximum latency: {max_latency:.2f}ms")
            print(f"       95th percentile: {p95_latency:.2f}ms")

            # Assert performance requirements
            self.assertLess(avg_latency, 1000, "Average latency should be under 1 second")
            self.assertLess(p95_latency, 5000, "95th percentile should be under 5 seconds")
            self.assertLess(max_latency, 10000, "Maximum latency should be under 10 seconds")

            print("    ✅ All latency requirements met!")
        else:
            print("    ⚠️  No signals generated during test")

        # Cleanup
        if os.path.exists("test_benchmark.db"):
            os.remove("test_benchmark.db")

    def test_throughput_benchmark(self):
        """Test system throughput under load"""
        print("\n⚡ Testing Throughput Benchmark")

        processor = create_standard_processor()
        events_processed = 0

        def count_events(batch):
            nonlocal events_processed
            events_processed += len(batch)

        processor.register_batch_callback(count_events)
        processor.start_processing()

        # Send events as fast as possible
        start_time = time.time()
        target_events = 10000

        print(f"    Sending {target_events} events...")
        for i in range(target_events):
            event = self._create_test_event(datetime.now(timezone.utc))
            processor.process_event(event)

        # Wait for processing
        time.sleep(3)
        processor.stop_processing()

        elapsed = time.time() - start_time
        throughput = events_processed / elapsed

        print(f"    📊 Throughput Results:")
        print(f"       Events sent: {target_events}")
        print(f"       Events processed: {events_processed}")
        print(f"       Time elapsed: {elapsed:.2f}s")
        print(f"       Throughput: {throughput:.1f} events/second")

        # Assert minimum throughput
        self.assertGreater(throughput, 100, "Throughput should exceed 100 events/second")
        self.assertGreater(events_processed / target_events, 0.95, "Should process 95%+ of events")

    def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load"""
        import psutil
        import gc

        print("\n💾 Testing Memory Usage Under Load")

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create components
        bridge = StreamingBridge(self.config)
        processor = create_standard_processor()
        pressure_engine = create_standard_engine()

        print(f"    Initial memory: {initial_memory:.1f} MB")

        # Run intensive processing
        processor.start_processing()

        def process_batch(batch):
            for event in batch:
                pressure_engine.process_mbo_event(event)

        processor.register_batch_callback(process_batch)

        # Generate load for 30 seconds
        start_time = time.time()
        event_count = 0

        while time.time() - start_time < 30:
            for _ in range(100):  # Burst of events
                event = self._create_test_event(datetime.now(timezone.utc))
                processor.process_event(event)
                event_count += 1
            time.sleep(0.1)

        processor.stop_processing()

        # Force garbage collection
        gc.collect()
        time.sleep(1)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"    Final memory: {final_memory:.1f} MB")
        print(f"    Memory increase: {memory_increase:.1f} MB")
        print(f"    Events processed: {event_count}")
        print(f"    Memory per event: {memory_increase * 1024 / event_count:.2f} KB")

        # Assert reasonable memory usage
        self.assertLess(memory_increase, 100, "Memory increase should be under 100 MB")
        self.assertLess(memory_increase * 1024 / event_count, 1, "Should use less than 1 KB per event")

    def test_concurrent_processing_performance(self):
        """Test performance with concurrent processing"""
        print("\n🔄 Testing Concurrent Processing Performance")

        bridge = StreamingBridge(self.config)
        results = []

        def worker_thread(thread_id, events_per_thread):
            """Worker thread for concurrent testing"""
            thread_results = []

            for i in range(events_per_thread):
                timer = PerformanceTimer()
                timer.start()

                # Simulate streaming data processing
                event = self._create_test_event(datetime.now(timezone.utc))
                bridge._simulate_streaming_data()

                latency = timer.stop()
                thread_results.append({
                    'thread_id': thread_id,
                    'event_id': i,
                    'latency_ms': latency
                })

                time.sleep(0.001)  # Small delay

            results.extend(thread_results)

        # Start multiple worker threads
        threads = []
        num_threads = 4
        events_per_thread = 250

        print(f"    Starting {num_threads} threads, {events_per_thread} events each")

        start_time = time.time()

        for thread_id in range(num_threads):
            thread = threading.Thread(
                target=worker_thread,
                args=(thread_id, events_per_thread)
            )
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        elapsed = time.time() - start_time
        total_events = len(results)

        # Analyze concurrent performance
        latencies = [r['latency_ms'] for r in results]
        avg_latency = statistics.mean(latencies)
        throughput = total_events / elapsed

        print(f"    📊 Concurrent Performance Results:")
        print(f"       Total events: {total_events}")
        print(f"       Time elapsed: {elapsed:.2f}s")
        print(f"       Throughput: {throughput:.1f} events/second")
        print(f"       Average latency: {avg_latency:.2f}ms")

        # Assert concurrent performance
        self.assertGreater(throughput, 50, "Concurrent throughput should exceed 50 events/second")
        self.assertLess(avg_latency, 2000, "Average concurrent latency should be under 2 seconds")

    def test_stress_test_error_recovery(self):
        """Test system recovery under stress conditions"""
        print("\n⚡ Testing Stress Test Error Recovery")

        processor = create_standard_processor()
        error_count = 0
        processed_count = 0

        def error_prone_processor(batch):
            nonlocal error_count, processed_count

            for event in batch:
                processed_count += 1

                # Simulate random errors
                if random.random() < 0.1:  # 10% error rate
                    error_count += 1
                    raise Exception(f"Simulated error #{error_count}")

        processor.register_batch_callback(error_prone_processor)
        processor.start_processing()

        # Send events with errors
        start_time = time.time()
        events_sent = 1000

        print(f"    Sending {events_sent} events with 10% error rate...")

        for i in range(events_sent):
            event = self._create_test_event(datetime.now(timezone.utc))
            processor.process_event(event)

        time.sleep(3)
        processor.stop_processing()

        elapsed = time.time() - start_time
        success_rate = (processed_count - error_count) / processed_count * 100

        print(f"    📊 Stress Test Results:")
        print(f"       Events sent: {events_sent}")
        print(f"       Events processed: {processed_count}")
        print(f"       Errors encountered: {error_count}")
        print(f"       Success rate: {success_rate:.1f}%")
        print(f"       Recovery time: {elapsed:.2f}s")

        # Assert error recovery
        self.assertGreater(success_rate, 85, "Success rate should exceed 85% even with errors")
        self.assertGreater(processed_count / events_sent, 0.8, "Should process 80%+ of events")

    def _create_test_event(self, timestamp):
        """Create a test MBO event"""
        return {
            'timestamp': timestamp,
            'instrument_id': random.randint(10000, 99999),
            'strike': random.choice([21800, 21900, 22000, 22100, 22200]),
            'option_type': random.choice(['C', 'P']),
            'bid_px_00': random.randint(100000000, 102000000),
            'ask_px_00': random.randint(100500000, 102500000),
            'size': random.randint(10, 1000),
            'side': random.choice(['BUY', 'SELL']),
            'trade_price': random.uniform(100, 102),
            'confidence': random.uniform(0.7, 1.0)
        }


if __name__ == '__main__':
    # Run with detailed output
    unittest.main(verbosity=2)
