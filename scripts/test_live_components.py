#!/usr/bin/env python3
"""
Component-level Tests for IFD Live Streaming Pipeline

Tests each component in isolation without full integration dependencies.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import random
import statistics

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(current_dir))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def record(self, name: str, passed: bool, message: str = ""):
        if passed:
            self.passed += 1
            logger.info(f"✅ {name}")
        else:
            self.failed += 1
            logger.error(f"❌ {name}: {message}")
        self.tests.append((name, passed, message))

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY: {self.passed}/{total} passed ({self.passed/max(total,1)*100:.1f}%)")
        print(f"{'='*60}")

        if self.failed > 0:
            print("\nFailed tests:")
            for name, passed, message in self.tests:
                if not passed:
                    print(f"  - {name}: {message}")

def test_event_processor():
    """Test Event Processor component"""
    logger.info("\n=== Testing Event Processor ===")
    results = TestResults()

    try:
        # Import component
        from tasks.options_trading_system.analysis_engine.event_processor import (
            EventProcessor, EventFilter, BatchConfig, create_standard_processor
        )
        results.record("Import Event Processor", True)

        # Test creation
        processor = create_standard_processor()
        results.record("Create Standard Processor", True)

        # Test configuration
        filter_config = EventFilter(
            min_trade_size=10,
            max_events_per_second=50,
            market_hours_only=False  # Disable for testing
        )
        batch_config = BatchConfig(
            max_batch_size=20,
            batch_timeout_ms=2000
        )
        custom_processor = EventProcessor(filter_config, batch_config)
        results.record("Create Custom Processor", True)

        # Test event processing
        processor.start_processing()

        # Track batches
        batches_received = []
        def batch_callback(batch):
            batches_received.append(len(batch))

        processor.register_batch_callback(batch_callback)

        # Send test events
        for i in range(50):
            event = {
                'timestamp': datetime.now(timezone.utc),
                'instrument_id': 12345,
                'bid_px_00': 100000000,  # Databento format
                'ask_px_00': 100500000,
                'size': 10 + i,
                'price': 100250000
            }
            processor.process_event(event)
            time.sleep(0.01)

        # Allow processing
        time.sleep(3)

        # Check results
        stats = processor.get_performance_stats()

        results.record("Process Events",
                      stats['metrics']['events_processed'] > 0,
                      f"Processed {stats['metrics']['events_processed']} events")

        results.record("Create Batches",
                      len(batches_received) > 0,
                      f"Created {len(batches_received)} batches")

        results.record("Filter Events",
                      stats['filtering']['filter_ratio'] > 0,
                      f"Filter ratio: {stats['filtering']['filter_ratio']:.2f}")

        processor.stop_processing()
        results.record("Stop Processing", True)

    except Exception as e:
        results.record("Event Processor Test", False, str(e))

    return results

def test_pressure_aggregator():
    """Test Pressure Aggregator component"""
    logger.info("\n=== Testing Pressure Aggregator ===")
    results = TestResults()

    try:
        # Import component
        from tasks.options_trading_system.analysis_engine.pressure_aggregator import (
            RealTimePressureEngine, create_standard_engine, PressureMetrics
        )
        results.record("Import Pressure Aggregator", True)

        # Test creation
        engine = create_standard_engine()
        results.record("Create Standard Engine", True)

        # Track metrics
        pressure_metrics = []
        def pressure_callback(metrics):
            pressure_metrics.append(metrics)

        engine.register_pressure_callback(pressure_callback)

        # Process events over time to complete windows
        start_time = datetime.now(timezone.utc)
        for i in range(65):  # 65 seconds to ensure 1-minute window completes
            current_time = start_time + timedelta(seconds=i)
            event = {
                'timestamp': current_time,
                'strike': 21900.0,
                'option_type': 'C',
                'trade_price': 100.0 + i * 0.1,
                'trade_size': 10 + i,
                'bid_price': 99.5 + i * 0.1,
                'ask_price': 100.5 + i * 0.1
            }

            metrics_list = engine.process_mbo_event(event)
            time.sleep(0.01)  # Faster for testing

        # Check results
        stats = engine.get_engine_stats()

        results.record("Process MBO Events",
                      stats['events_processed'] > 0,
                      f"Processed {stats['events_processed']} events")

        results.record("Generate Metrics",
                      stats['metrics_generated'] > 0,
                      f"Generated {stats['metrics_generated']} metrics")

        # Validate metrics
        if pressure_metrics:
            sample = pressure_metrics[0]
            results.record("Valid Pressure Metrics",
                          hasattr(sample, 'pressure_ratio') and sample.pressure_ratio > 0,
                          f"Sample pressure ratio: {sample.pressure_ratio:.2f}")
        else:
            results.record("Valid Pressure Metrics", False, "No metrics generated")

    except Exception as e:
        results.record("Pressure Aggregator Test", False, str(e))

    return results

def test_data_validator():
    """Test Data Validator component"""
    logger.info("\n=== Testing Data Validator ===")
    results = TestResults()

    try:
        # Import component
        from tasks.options_trading_system.analysis_engine.data_validator import (
            StreamingDataValidator, create_mbo_validation_rules, ValidationResult
        )
        results.record("Import Data Validator", True)

        # Create validator
        rules = create_mbo_validation_rules()
        validator = StreamingDataValidator(rules)
        results.record("Create Validator", True)

        # Test valid data
        valid_data = {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'bid_price': 100.0,
            'ask_price': 100.5,
            'trade_price': 100.25,
            'trade_size': 10,
            'side': 'BUY',
            'confidence': 0.85
        }

        should_process, result = validator.validate_streaming_data(valid_data)
        results.record("Validate Good Data",
                      should_process and result.is_valid,
                      f"Quality score: {result.quality_score:.2f}")

        # Test invalid data
        invalid_data = {
            'bid_price': 100.5,
            'ask_price': 100.0,  # Bid > Ask
            'trade_size': -10    # Negative size
        }

        should_process, result = validator.validate_streaming_data(invalid_data)
        results.record("Detect Invalid Data",
                      not result.is_valid,
                      f"Failed rules: {result.failed_rules}")

        # Test circuit breaker
        for i in range(15):
            validator.validate_streaming_data({'invalid': 'data'})

        stats = validator.get_comprehensive_stats()
        circuit_state = stats['circuit_breaker']['state']

        results.record("Circuit Breaker Activation",
                      circuit_state == 'OPEN',
                      f"Circuit state: {circuit_state}")

    except Exception as e:
        results.record("Data Validator Test", False, str(e))

    return results

def test_baseline_manager():
    """Test Baseline Manager component"""
    logger.info("\n=== Testing Baseline Manager ===")
    results = TestResults()

    try:
        # Import component
        from tasks.options_trading_system.analysis_engine.baseline_context_manager import (
            RealTimeBaselineManager, create_baseline_manager, BaselineContext
        )
        results.record("Import Baseline Manager", True)

        # Create manager
        manager = create_baseline_manager("test_baseline_component.db")
        results.record("Create Baseline Manager", True)

        # Generate baseline data
        anomalies = 0
        for i in range(30):
            pressure = 2.0 + random.gauss(0, 0.2)

            context = manager.update_baseline(
                strike=21900.0,
                option_type='C',
                pressure_ratio=pressure,
                volume=100 + i * 10,
                confidence=0.85,
                timestamp=datetime.now(timezone.utc)
            )

            if context.anomaly_detected:
                anomalies += 1

        results.record("Update Baseline",
                      manager.get_manager_stats()['updates_processed'] > 0,
                      f"Processed {manager.get_manager_stats()['updates_processed']} updates")

        # Test anomaly detection
        extreme_context = manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=10.0,  # Extreme value
            volume=1000,
            confidence=0.9,
            timestamp=datetime.now(timezone.utc)
        )

        results.record("Detect Anomaly",
                      extreme_context.anomaly_detected,
                      f"Severity: {extreme_context.anomaly_severity}")

        # Test context retrieval
        context = manager.get_baseline_context(21900.0, 'C')
        results.record("Retrieve Context",
                      context is not None and context.baseline.sample_count > 0,
                      f"Sample count: {context.baseline.sample_count if context else 0}")

        # Cleanup
        manager.cleanup_old_data()
        results.record("Cleanup Old Data", True)

    except Exception as e:
        results.record("Baseline Manager Test", False, str(e))

    finally:
        # Remove test database
        if os.path.exists("test_baseline_component.db"):
            os.remove("test_baseline_component.db")

    return results

def test_integration_flow():
    """Test basic integration flow"""
    logger.info("\n=== Testing Integration Flow ===")
    results = TestResults()

    try:
        # Import components
        from tasks.options_trading_system.analysis_engine.event_processor import create_standard_processor
        from tasks.options_trading_system.analysis_engine.pressure_aggregator import create_standard_engine
        from tasks.options_trading_system.analysis_engine.data_validator import (
            StreamingDataValidator, create_mbo_validation_rules
        )

        # Create components
        processor = create_standard_processor()
        engine = create_standard_engine()
        validator = StreamingDataValidator(create_mbo_validation_rules())

        results.record("Create All Components", True)

        # Track flow
        events_validated = 0
        metrics_generated = 0

        def process_batch(batch):
            nonlocal events_validated, metrics_generated

            for event in batch:
                # Validate
                should_process, _ = validator.validate_streaming_data(event)
                if should_process:
                    events_validated += 1

                    # Process
                    metrics = engine.process_mbo_event(event)
                    if metrics:
                        metrics_generated += len(metrics)

        processor.register_batch_callback(process_batch)
        processor.start_processing()

        # Send test events
        for i in range(100):
            event = {
                'timestamp': datetime.now(timezone.utc),
                'instrument_id': 12345,
                'bid_px_00': 100000000,
                'ask_px_00': 100500000,
                'size': 20,
                'strike': 21900.0,
                'option_type': 'C',
                'trade_price': 100.25,
                'trade_size': 20,
                'bid_price': 100.0,
                'ask_price': 100.5
            }
            processor.process_event(event)
            time.sleep(0.01)

        # Wait for processing
        time.sleep(3)
        processor.stop_processing()

        results.record("Data Flow Through Pipeline",
                      events_validated > 0 and metrics_generated > 0,
                      f"Validated: {events_validated}, Metrics: {metrics_generated}")

    except Exception as e:
        results.record("Integration Flow Test", False, str(e))

    return results

def test_performance():
    """Test performance characteristics"""
    logger.info("\n=== Testing Performance ===")
    results = TestResults()

    try:
        from tasks.options_trading_system.analysis_engine.event_processor import create_standard_processor

        processor = create_standard_processor()
        processor.start_processing()

        # Measure throughput
        start_time = time.time()
        events_sent = 0

        for i in range(500):
            event = {
                'timestamp': datetime.now(timezone.utc),
                'instrument_id': 12345,
                'bid_px_00': 100000000,
                'ask_px_00': 100500000,
                'size': 10
            }
            processor.process_event(event)
            events_sent += 1

        # Wait for processing
        time.sleep(2)

        elapsed = time.time() - start_time
        stats = processor.get_performance_stats()
        events_processed = stats['metrics']['events_processed']

        throughput = events_processed / elapsed

        results.record("High Throughput",
                      throughput > 50,  # Target: >50 events/sec
                      f"Throughput: {throughput:.1f} events/sec")

        # Check memory usage
        queue_size = stats['metrics']['current_queue_size']
        results.record("Queue Management",
                      queue_size < 100,  # Should not build up
                      f"Queue size: {queue_size}")

        processor.stop_processing()

    except Exception as e:
        results.record("Performance Test", False, str(e))

    return results

def main():
    """Run all component tests"""
    print("\n🚀 IFD Live Streaming Component Tests")
    print("=" * 60)

    all_results = []

    # Run component tests
    all_results.append(test_event_processor())
    all_results.append(test_pressure_aggregator())
    all_results.append(test_data_validator())
    all_results.append(test_baseline_manager())
    all_results.append(test_integration_flow())
    all_results.append(test_performance())

    # Summary
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total_tests = total_passed + total_failed

    print(f"\n{'='*60}")
    print(f"OVERALL SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed} ({total_passed/max(total_tests,1)*100:.1f}%)")
    print(f"Failed: {total_failed}")

    if total_failed > 0:
        print("\n❌ Some tests failed. Review the output above for details.")
        return 1
    else:
        print("\n✅ All tests passed! Live streaming infrastructure is ready.")
        return 0

if __name__ == "__main__":
    exit(main())
