#!/usr/bin/env python3
"""
Comprehensive Test Suite for IFD Live Streaming Pipeline

This script tests the complete live streaming infrastructure end-to-end,
validating each component and the integrated system.

Test Coverage:
1. Component Tests - Individual module validation
2. Integration Tests - End-to-end pipeline testing
3. Performance Tests - Latency and throughput validation
4. Error Handling Tests - Failure scenarios and recovery
5. Live Simulation - Simulated real-time data flow
"""

import os
import sys
import time
import json
import asyncio
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import random
import statistics

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(current_dir))

# Import all components
from tasks.options_trading_system.analysis_engine.streaming_bridge import (
    StreamingBridge, create_streaming_bridge
)
from tasks.options_trading_system.analysis_engine.event_processor import (
    EventProcessor, create_standard_processor
)
from tasks.options_trading_system.analysis_engine.pressure_aggregator import (
    RealTimePressureEngine, create_standard_engine
)
from tasks.options_trading_system.analysis_engine.data_validator import (
    StreamingDataValidator, create_mbo_validation_rules
)
from tasks.options_trading_system.analysis_engine.baseline_context_manager import (
    RealTimeBaselineManager, create_baseline_manager
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestMetrics:
    """Track test metrics and results"""

    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.component_results = {}
        self.performance_metrics = {}
        self.errors = []

    def record_test(self, test_name: str, passed: bool, error: Optional[str] = None):
        """Record test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            logger.info(f"✅ {test_name} PASSED")
        else:
            self.tests_failed += 1
            logger.error(f"❌ {test_name} FAILED: {error}")
            self.errors.append(f"{test_name}: {error}")

    def record_performance(self, metric_name: str, value: float):
        """Record performance metric"""
        if metric_name not in self.performance_metrics:
            self.performance_metrics[metric_name] = []
        self.performance_metrics[metric_name].append(value)

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed} ({self.tests_passed/max(self.tests_run,1)*100:.1f}%)")
        print(f"Failed: {self.tests_failed}")

        if self.performance_metrics:
            print("\nPERFORMANCE METRICS:")
            for metric, values in self.performance_metrics.items():
                avg = statistics.mean(values)
                print(f"  {metric}: {avg:.2f}ms (avg)")

        if self.errors:
            print("\nERRORS:")
            for error in self.errors:
                print(f"  - {error}")

class DataSimulator:
    """Simulates realistic MBO streaming data"""

    def __init__(self):
        self.base_bid = 100.0
        self.base_ask = 100.5
        self.volatility = 0.1
        self.trade_counter = 0

    def generate_mbo_event(self) -> Dict[str, Any]:
        """Generate realistic MBO event data"""
        self.trade_counter += 1

        # Add some price movement
        price_change = random.gauss(0, self.volatility)
        self.base_bid += price_change
        self.base_ask += price_change

        # Ensure valid spread
        if self.base_ask <= self.base_bid:
            self.base_ask = self.base_bid + 0.5

        # Generate trade
        trade_price = random.uniform(self.base_bid, self.base_ask)
        trade_size = random.randint(1, 50) * 10  # 10-500 contracts

        return {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'strike': 21900.0,
            'option_type': 'C',
            'bid_price': self.base_bid,
            'ask_price': self.base_ask,
            'trade_price': trade_price,
            'trade_size': trade_size,
            'side': 'BUY' if trade_price > (self.base_bid + self.base_ask) / 2 else 'SELL',
            'confidence': 0.85,
            'sequence': self.trade_counter
        }

    def generate_anomaly_event(self) -> Dict[str, Any]:
        """Generate anomalous data for testing"""
        event = self.generate_mbo_event()

        anomaly_type = random.choice(['price_spike', 'invalid_spread', 'huge_volume'])

        if anomaly_type == 'price_spike':
            event['trade_price'] *= 3.0
            event['bid_price'] *= 3.0
            event['ask_price'] *= 3.0
        elif anomaly_type == 'invalid_spread':
            event['bid_price'] = event['ask_price'] + 1.0  # Invalid: bid > ask
        elif anomaly_type == 'huge_volume':
            event['trade_size'] = 10000  # Unusually large

        return event

# Component Tests
def test_event_processor(metrics: TestMetrics):
    """Test event filtering and batching"""
    logger.info("\n=== Testing Event Processor ===")

    try:
        # Create processor
        processor = create_standard_processor()
        processor.start_processing()

        # Track batch completions
        batches_received = []

        def batch_callback(batch: List[Dict[str, Any]]):
            batches_received.append(len(batch))

        processor.register_batch_callback(batch_callback)

        # Generate test events
        simulator = DataSimulator()
        start_time = time.time()

        for i in range(100):
            event = simulator.generate_mbo_event()
            processor.process_event(event)
            time.sleep(0.01)  # 10ms between events

        # Wait for processing
        time.sleep(2)
        processor.stop_processing()

        # Check results
        stats = processor.get_performance_stats()

        # Validate processing
        if stats['metrics']['events_processed'] > 0:
            metrics.record_test("Event Processor - Basic Processing", True)
        else:
            metrics.record_test("Event Processor - Basic Processing", False,
                              "No events processed")

        # Check filtering
        filter_ratio = stats['filtering']['filter_ratio']
        if 0.5 < filter_ratio < 1.0:  # Some filtering expected
            metrics.record_test("Event Processor - Filtering", True)
        else:
            metrics.record_test("Event Processor - Filtering", False,
                              f"Unexpected filter ratio: {filter_ratio}")

        # Check batching
        if len(batches_received) > 0:
            avg_batch_size = statistics.mean(batches_received)
            metrics.record_test("Event Processor - Batching", True)
            metrics.record_performance("batch_size", avg_batch_size)
        else:
            metrics.record_test("Event Processor - Batching", False,
                              "No batches created")

        # Performance metrics
        processing_time = (time.time() - start_time) * 1000
        metrics.record_performance("event_processing", processing_time / 100)  # Per event

    except Exception as e:
        metrics.record_test("Event Processor", False, str(e))

def test_pressure_aggregator(metrics: TestMetrics):
    """Test pressure metrics aggregation"""
    logger.info("\n=== Testing Pressure Aggregator ===")

    try:
        # Create engine
        engine = create_standard_engine()

        # Track pressure metrics
        pressure_metrics_received = []

        def pressure_callback(metrics_obj):
            pressure_metrics_received.append(metrics_obj)

        engine.register_pressure_callback(pressure_callback)

        # Generate events
        simulator = DataSimulator()

        for i in range(50):
            event = simulator.generate_mbo_event()
            mbo_data = {
                'timestamp': event['timestamp'],
                'strike': event['strike'],
                'option_type': event['option_type'],
                'trade_price': event['trade_price'],
                'trade_size': event['trade_size'],
                'bid_price': event['bid_price'],
                'ask_price': event['ask_price']
            }

            engine.process_mbo_event(mbo_data)
            time.sleep(0.02)

        # Check results
        stats = engine.get_engine_stats()

        if stats['events_processed'] > 0:
            metrics.record_test("Pressure Aggregator - Event Processing", True)
        else:
            metrics.record_test("Pressure Aggregator - Event Processing", False,
                              "No events processed")

        if stats['metrics_generated'] > 0:
            metrics.record_test("Pressure Aggregator - Metrics Generation", True)

            # Check pressure calculations
            for pm in pressure_metrics_received:
                if pm.pressure_ratio > 0 and pm.total_volume > 0:
                    metrics.record_test("Pressure Aggregator - Calculations", True)
                    break
            else:
                metrics.record_test("Pressure Aggregator - Calculations", False,
                                  "Invalid pressure metrics")
        else:
            metrics.record_test("Pressure Aggregator - Metrics Generation", False,
                              "No metrics generated")

    except Exception as e:
        metrics.record_test("Pressure Aggregator", False, str(e))

def test_data_validator(metrics: TestMetrics):
    """Test data validation and quality checks"""
    logger.info("\n=== Testing Data Validator ===")

    try:
        # Create validator
        rules = create_mbo_validation_rules()
        validator = StreamingDataValidator(rules)

        simulator = DataSimulator()

        # Test valid data
        valid_event = simulator.generate_mbo_event()
        should_process, result = validator.validate_streaming_data(valid_event)

        if should_process and result.is_valid:
            metrics.record_test("Data Validator - Valid Data", True)
        else:
            metrics.record_test("Data Validator - Valid Data", False,
                              f"Failed rules: {result.failed_rules}")

        # Test invalid data
        invalid_event = {
            'bid_price': 100.0,
            'ask_price': 99.0,  # Invalid: bid > ask
            'trade_size': -10   # Invalid: negative size
        }

        should_process, result = validator.validate_streaming_data(invalid_event)

        if not result.is_valid:
            metrics.record_test("Data Validator - Invalid Data Detection", True)
        else:
            metrics.record_test("Data Validator - Invalid Data Detection", False,
                              "Failed to detect invalid data")

        # Test anomaly detection
        for i in range(20):
            event = simulator.generate_mbo_event()
            validator.validate_streaming_data(event)

        # Generate anomaly
        anomaly_event = simulator.generate_anomaly_event()
        should_process, result = validator.validate_streaming_data(anomaly_event)

        stats = validator.get_comprehensive_stats()
        if stats['anomaly_detection']['total_anomalies'] > 0:
            metrics.record_test("Data Validator - Anomaly Detection", True)
        else:
            metrics.record_test("Data Validator - Anomaly Detection", False,
                              "No anomalies detected")

    except Exception as e:
        metrics.record_test("Data Validator", False, str(e))

def test_baseline_manager(metrics: TestMetrics):
    """Test baseline context management"""
    logger.info("\n=== Testing Baseline Manager ===")

    try:
        # Create manager
        manager = create_baseline_manager("test_baseline.db")

        simulator = DataSimulator()
        anomalies_detected = 0

        # Generate baseline data
        for i in range(30):
            event = simulator.generate_mbo_event()

            context = manager.update_baseline(
                strike=event['strike'],
                option_type=event['option_type'],
                pressure_ratio=2.0 + random.gauss(0, 0.2),
                volume=event['trade_size'],
                confidence=0.85,
                timestamp=event['timestamp']
            )

            if context.anomaly_detected:
                anomalies_detected += 1

        # Test baseline retrieval
        context = manager.get_baseline_context(21900.0, 'C')

        if context and context.baseline.sample_count > 0:
            metrics.record_test("Baseline Manager - Context Creation", True)
        else:
            metrics.record_test("Baseline Manager - Context Creation", False,
                              "No baseline context created")

        # Test anomaly detection
        # Generate extreme pressure
        extreme_context = manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=10.0,  # Extreme value
            volume=1000,
            confidence=0.9,
            timestamp=datetime.now(timezone.utc)
        )

        if extreme_context.anomaly_detected:
            metrics.record_test("Baseline Manager - Anomaly Detection", True)
        else:
            metrics.record_test("Baseline Manager - Anomaly Detection", False,
                              "Failed to detect extreme anomaly")

        # Check stats
        stats = manager.get_manager_stats()
        if stats['updates_processed'] > 0:
            metrics.record_test("Baseline Manager - Update Processing", True)
        else:
            metrics.record_test("Baseline Manager - Update Processing", False,
                              "No updates processed")

    except Exception as e:
        metrics.record_test("Baseline Manager", False, str(e))

    finally:
        # Cleanup test database
        if os.path.exists("test_baseline.db"):
            os.remove("test_baseline.db")

# Integration Tests
def test_end_to_end_pipeline(metrics: TestMetrics):
    """Test complete pipeline integration"""
    logger.info("\n=== Testing End-to-End Pipeline ===")

    try:
        # Track signals
        signals_received = []

        def signal_callback(signal):
            signals_received.append(signal)
            logger.info(f"📡 Signal received: {signal.strike}{signal.option_type} "
                       f"confidence={signal.final_confidence:.2f}")

        # Create integrated pipeline
        processor = create_standard_processor()
        pressure_engine = create_standard_engine()
        validator = StreamingDataValidator(create_mbo_validation_rules())
        baseline_manager = create_baseline_manager("test_integration.db")

        # Connect components
        def process_batch(batch: List[Dict[str, Any]]):
            for event in batch:
                # Validate
                should_process, validation_result = validator.validate_streaming_data(event)

                if should_process:
                    # Generate pressure metrics
                    pressure_metrics = pressure_engine.process_mbo_event(event)

                    # Update baseline
                    if pressure_metrics:
                        for pm in pressure_metrics:
                            context = baseline_manager.update_baseline(
                                strike=pm.strike,
                                option_type=pm.option_type,
                                pressure_ratio=pm.pressure_ratio,
                                volume=pm.total_volume,
                                confidence=pm.confidence,
                                timestamp=pm.time_window
                            )

        processor.register_batch_callback(process_batch)
        processor.start_processing()

        # Generate test data
        simulator = DataSimulator()
        start_time = time.time()

        for i in range(200):
            event = simulator.generate_mbo_event()
            processor.process_event(event)
            time.sleep(0.005)  # 5ms between events

        # Wait for processing
        time.sleep(3)
        processor.stop_processing()

        # Check results
        processor_stats = processor.get_performance_stats()
        engine_stats = pressure_engine.get_engine_stats()
        validator_stats = validator.get_comprehensive_stats()
        baseline_stats = baseline_manager.get_manager_stats()

        # Validate pipeline flow
        if (processor_stats['metrics']['events_processed'] > 0 and
            engine_stats['events_processed'] > 0 and
            baseline_stats['updates_processed'] > 0):
            metrics.record_test("Pipeline Integration - Data Flow", True)
        else:
            metrics.record_test("Pipeline Integration - Data Flow", False,
                              "Data not flowing through pipeline")

        # Check quality metrics
        avg_quality = validator_stats['metrics']['avg_quality_score']
        if avg_quality > 0.7:
            metrics.record_test("Pipeline Integration - Data Quality", True)
        else:
            metrics.record_test("Pipeline Integration - Data Quality", False,
                              f"Low data quality: {avg_quality}")

        # Performance metrics
        total_time = (time.time() - start_time) * 1000
        events_processed = processor_stats['metrics']['events_processed']
        if events_processed > 0:
            latency_per_event = total_time / events_processed
            metrics.record_performance("pipeline_latency", latency_per_event)

            if latency_per_event < 50:  # Target: <50ms per event
                metrics.record_test("Pipeline Integration - Performance", True)
            else:
                metrics.record_test("Pipeline Integration - Performance", False,
                              f"High latency: {latency_per_event:.1f}ms")

    except Exception as e:
        metrics.record_test("Pipeline Integration", False, str(e))

    finally:
        # Cleanup
        if os.path.exists("test_integration.db"):
            os.remove("test_integration.db")

def test_error_handling(metrics: TestMetrics):
    """Test error handling and recovery"""
    logger.info("\n=== Testing Error Handling ===")

    try:
        # Test invalid data handling
        processor = create_standard_processor()
        processor.start_processing()

        # Send various invalid events
        invalid_events = [
            {},  # Empty event
            {'timestamp': 'invalid'},  # Invalid timestamp
            {'trade_size': 'not_a_number'},  # Invalid type
            None,  # Null event
        ]

        for event in invalid_events:
            try:
                processor.process_event(event)
            except:
                pass  # Should handle gracefully

        # Check processor still running
        stats = processor.get_performance_stats()
        if stats['threads']['running']:
            metrics.record_test("Error Handling - Invalid Data", True)
        else:
            metrics.record_test("Error Handling - Invalid Data", False,
                              "Processor crashed on invalid data")

        processor.stop_processing()

        # Test circuit breaker
        validator = StreamingDataValidator(create_mbo_validation_rules())

        # Generate many failures
        for i in range(15):
            bad_event = {'invalid': 'data'}
            validator.validate_streaming_data(bad_event)

        # Check circuit breaker state
        stats = validator.get_comprehensive_stats()
        circuit_state = stats['circuit_breaker']['state']

        if circuit_state == 'OPEN':
            metrics.record_test("Error Handling - Circuit Breaker", True)
        else:
            metrics.record_test("Error Handling - Circuit Breaker", False,
                              f"Circuit breaker not triggered: {circuit_state}")

    except Exception as e:
        metrics.record_test("Error Handling", False, str(e))

def test_performance_under_load(metrics: TestMetrics):
    """Test system performance under high load"""
    logger.info("\n=== Testing Performance Under Load ===")

    try:
        # Create high-performance configuration
        processor = create_standard_processor()
        processor.start_processing()

        simulator = DataSimulator()
        events_sent = 0
        start_time = time.time()

        # Send rapid events
        for i in range(1000):
            event = simulator.generate_mbo_event()
            processor.process_event(event)
            events_sent += 1

            # No sleep - maximum throughput

        # Wait for processing to complete
        time.sleep(5)

        # Check results
        stats = processor.get_performance_stats()
        events_processed = stats['metrics']['events_processed']
        processing_time = time.time() - start_time

        # Calculate throughput
        throughput = events_processed / processing_time
        metrics.record_performance("throughput_events_per_sec", throughput)

        # Check queue utilization
        max_queue_size = stats['metrics']['current_queue_size']

        if events_processed > 0:
            success_rate = events_processed / events_sent

            if success_rate > 0.95:  # 95% processing success
                metrics.record_test("Performance - High Load Processing", True)
            else:
                metrics.record_test("Performance - High Load Processing", False,
                                  f"Low success rate: {success_rate:.2%}")

            if throughput > 100:  # Target: >100 events/sec
                metrics.record_test("Performance - Throughput", True)
            else:
                metrics.record_test("Performance - Throughput", False,
                                  f"Low throughput: {throughput:.1f} events/sec")
        else:
            metrics.record_test("Performance - High Load", False,
                              "No events processed under load")

        processor.stop_processing()

    except Exception as e:
        metrics.record_test("Performance Under Load", False, str(e))

def run_live_simulation(metrics: TestMetrics, duration_seconds: int = 30):
    """Run a live market simulation"""
    logger.info(f"\n=== Running {duration_seconds}s Live Market Simulation ===")

    try:
        # Create full pipeline
        processor = create_standard_processor()
        pressure_engine = create_standard_engine()
        validator = StreamingDataValidator(create_mbo_validation_rules())
        baseline_manager = create_baseline_manager("test_simulation.db")

        # Track metrics
        signals = []
        anomalies = []

        def pressure_callback(pressure_metrics):
            # Update baseline
            context = baseline_manager.update_baseline(
                strike=pressure_metrics.strike,
                option_type=pressure_metrics.option_type,
                pressure_ratio=pressure_metrics.pressure_ratio,
                volume=pressure_metrics.total_volume,
                confidence=pressure_metrics.confidence,
                timestamp=pressure_metrics.time_window
            )

            # Check for signals
            if context.anomaly_detected and context.anomaly_severity in ['severe', 'extreme']:
                signal = {
                    'timestamp': context.timestamp,
                    'strike': pressure_metrics.strike,
                    'option_type': pressure_metrics.option_type,
                    'pressure_ratio': pressure_metrics.pressure_ratio,
                    'severity': context.anomaly_severity,
                    'confidence': context.confidence
                }
                signals.append(signal)
                logger.info(f"🎯 SIGNAL: {signal['strike']}{signal['option_type']} "
                           f"pressure={signal['pressure_ratio']:.2f} "
                           f"severity={signal['severity']}")

        def anomaly_callback(detected_anomalies):
            anomalies.extend(detected_anomalies)

        # Register callbacks
        pressure_engine.register_pressure_callback(pressure_callback)
        validator.register_anomaly_callback(anomaly_callback)

        # Connect processor to pipeline
        def process_batch(batch: List[Dict[str, Any]]):
            for event in batch:
                should_process, _ = validator.validate_streaming_data(event)
                if should_process:
                    pressure_engine.process_mbo_event(event)

        processor.register_batch_callback(process_batch)
        processor.start_processing()

        # Run simulation
        simulator = DataSimulator()
        start_time = time.time()
        events_generated = 0

        logger.info("📊 Starting live market simulation...")

        while time.time() - start_time < duration_seconds:
            # Normal market activity
            if random.random() < 0.98:
                event = simulator.generate_mbo_event()
            else:
                # Occasional anomaly
                event = simulator.generate_anomaly_event()

            processor.process_event(event)
            events_generated += 1

            # Simulate realistic timing
            time.sleep(random.uniform(0.01, 0.05))  # 10-50ms between events

        # Stop simulation
        processor.stop_processing()
        time.sleep(2)  # Allow final processing

        # Analyze results
        logger.info(f"\n📈 Simulation Results:")
        logger.info(f"  Events generated: {events_generated}")
        logger.info(f"  Signals detected: {len(signals)}")
        logger.info(f"  Anomalies detected: {len(anomalies)}")

        # Validate simulation
        if events_generated > 0:
            signal_rate = len(signals) / events_generated

            if 0.001 < signal_rate < 0.1:  # Reasonable signal rate
                metrics.record_test("Live Simulation - Signal Detection", True)
            else:
                metrics.record_test("Live Simulation - Signal Detection", False,
                                  f"Unusual signal rate: {signal_rate:.3%}")

            if len(anomalies) > 0:
                metrics.record_test("Live Simulation - Anomaly Detection", True)
            else:
                metrics.record_test("Live Simulation - Anomaly Detection", False,
                                  "No anomalies detected")

            # Performance metrics
            total_time = time.time() - start_time
            avg_latency = (total_time * 1000) / events_generated
            metrics.record_performance("simulation_latency", avg_latency)

            if avg_latency < 100:  # Target: <100ms average
                metrics.record_test("Live Simulation - Latency", True)
            else:
                metrics.record_test("Live Simulation - Latency", False,
                                  f"High latency: {avg_latency:.1f}ms")
        else:
            metrics.record_test("Live Simulation", False, "No events generated")

    except Exception as e:
        metrics.record_test("Live Simulation", False, str(e))

    finally:
        # Cleanup
        if os.path.exists("test_simulation.db"):
            os.remove("test_simulation.db")

def main():
    """Run all tests"""
    print("🚀 IFD Live Streaming Pipeline Test Suite")
    print("=" * 60)

    metrics = TestMetrics()

    # Component tests
    test_event_processor(metrics)
    test_pressure_aggregator(metrics)
    test_data_validator(metrics)
    test_baseline_manager(metrics)

    # Integration tests
    test_end_to_end_pipeline(metrics)
    test_error_handling(metrics)
    test_performance_under_load(metrics)

    # Live simulation
    run_live_simulation(metrics, duration_seconds=20)

    # Print summary
    metrics.print_summary()

    # Return exit code
    return 0 if metrics.tests_failed == 0 else 1

if __name__ == "__main__":
    exit(main())
