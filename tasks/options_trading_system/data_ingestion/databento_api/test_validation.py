#!/usr/bin/env python3
"""
Comprehensive Test Validation for Databento MBO Streaming

This module tests all components of the MBO streaming implementation:
- Event processing and direction derivation
- Pressure aggregation and window calculations
- Database storage and retrieval
- Usage monitoring and cost tracking
- Integration with pipeline interface
"""

import unittest
import tempfile
import os
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import logging

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from solution import (
        MBOEvent, PressureMetrics, MBOEventProcessor, PressureAggregator,
        MBODatabase, UsageMonitor, DatabentoMBOIngestion,
        load_databento_mbo_data
    )
    MBO_IMPLEMENTATION_AVAILABLE = True
    logger.info("Successfully imported MBO streaming solution")
except ImportError as e:
    logger.error(f"MBO implementation not available: {e}")
    MBO_IMPLEMENTATION_AVAILABLE = False

class TestMBOEventProcessor(unittest.TestCase):
    """Test MBO event processing and trade direction derivation"""

    def setUp(self):
        """Set up test processor"""
        if not MBO_IMPLEMENTATION_AVAILABLE:
            self.skipTest("MBO implementation not available")

        self.processor = MBOEventProcessor()

    def test_process_valid_trade_event(self):
        """Test processing a valid trade event"""
        raw_event = {
            'ts_event': int(datetime.now().timestamp() * 1_000_000_000),  # nanoseconds
            'instrument_id': 123456,
            'bid_px_00': 16_000_000,  # $16.00 scaled
            'ask_px_00': 17_000_000,  # $17.00 scaled
            'price': 17_000_000,     # $17.00 - trade at ask
            'size': 10,
            'sequence': 1
        }

        event = self.processor.process_event(raw_event)

        self.assertIsNotNone(event)
        self.assertEqual(event.instrument_id, 123456)
        self.assertEqual(event.bid_price, 16.0)
        self.assertEqual(event.ask_price, 17.0)
        self.assertEqual(event.trade_price, 17.0)
        self.assertEqual(event.trade_size, 10)
        self.assertEqual(event.side, 'BUY')  # Trade at ask = BUY

    def test_derive_trade_side_buy(self):
        """Test deriving BUY side when trade hits ask"""
        side = self.processor._derive_trade_side(17.0, 16.0, 17.0)
        self.assertEqual(side, 'BUY')

    def test_derive_trade_side_sell(self):
        """Test deriving SELL side when trade hits bid"""
        side = self.processor._derive_trade_side(16.0, 16.0, 17.0)
        self.assertEqual(side, 'SELL')

    def test_derive_trade_side_unknown(self):
        """Test UNKNOWN side when trade between bid/ask"""
        side = self.processor._derive_trade_side(16.5, 16.0, 17.0)
        self.assertEqual(side, 'UNKNOWN')

    def test_process_invalid_event(self):
        """Test processing invalid event returns None"""
        raw_event = {
            'ts_event': None,  # Invalid timestamp
            'instrument_id': 0  # Invalid instrument
        }

        event = self.processor.process_event(raw_event)
        self.assertIsNone(event)

class TestPressureAggregator(unittest.TestCase):
    """Test pressure aggregation and window calculations"""

    def setUp(self):
        """Set up test aggregator"""
        if not MBO_IMPLEMENTATION_AVAILABLE:
            self.skipTest("MBO implementation not available")

        self.aggregator = PressureAggregator(window_minutes=5)
        self.base_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    def create_test_event(self, minutes_offset: int, side: str, size: int = 10) -> MBOEvent:
        """Create a test MBO event"""
        timestamp = self.base_time + timedelta(minutes=minutes_offset)
        return MBOEvent(
            timestamp=timestamp,
            instrument_id=123456,
            strike=21900.0,
            option_type='C',
            bid_price=16.0,
            ask_price=17.0,
            trade_price=17.0 if side == 'BUY' else 16.0,
            trade_size=size,
            side=side,
            sequence=1
        )

    def test_add_buy_events(self):
        """Test adding BUY events to aggregator"""
        event = self.create_test_event(0, 'BUY', 20)
        result = self.aggregator.add_event(event)

        # Should not return metrics until window is complete
        self.assertIsNone(result)

    def test_complete_window_calculation(self):
        """Test completing a time window and calculating pressure metrics"""
        # Add events within same window
        buy_event = self.create_test_event(1, 'BUY', 30)
        sell_event = self.create_test_event(2, 'SELL', 10)

        self.aggregator.add_event(buy_event)
        self.aggregator.add_event(sell_event)

        # Add event that completes the window
        completion_event = self.create_test_event(6, 'BUY', 5)  # 6 minutes later
        metrics = self.aggregator.add_event(completion_event)

        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.strike, 21900.0)
        self.assertEqual(metrics.option_type, 'C')
        self.assertEqual(metrics.ask_volume, 30)  # BUY events add to ask_volume
        self.assertEqual(metrics.bid_volume, 10)  # SELL events add to bid_volume
        self.assertEqual(metrics.pressure_ratio, 3.0)  # 30/10
        self.assertEqual(metrics.dominant_side, 'BUY')
        self.assertEqual(metrics.total_trades, 2)

    def test_window_start_calculation(self):
        """Test window start time calculation"""
        # Test time: 13:07:45
        test_time = self.base_time.replace(hour=13, minute=7, second=45)
        window_start = self.aggregator._get_window_start(test_time)

        # Should round down to 13:05:00 (nearest 5-minute boundary)
        expected = self.base_time.replace(hour=13, minute=5, second=0)
        self.assertEqual(window_start, expected)

class TestMBODatabase(unittest.TestCase):
    """Test SQLite database storage and retrieval"""

    def setUp(self):
        """Set up test database"""
        if not MBO_IMPLEMENTATION_AVAILABLE:
            self.skipTest("MBO implementation not available")

        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_mbo.db')
        self.database = MBODatabase(self.db_path)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def create_test_metrics(self) -> PressureMetrics:
        """Create test pressure metrics"""
        return PressureMetrics(
            strike=21900.0,
            option_type='C',
            time_window=datetime.now(timezone.utc),
            bid_volume=100,
            ask_volume=200,
            pressure_ratio=2.0,
            total_trades=15,
            avg_trade_size=20.0,
            dominant_side='BUY',
            confidence=0.85
        )

    def test_store_pressure_metrics(self):
        """Test storing pressure metrics in database"""
        metrics = self.create_test_metrics()

        # Should not raise exception
        self.database.store_pressure_metrics(metrics)

        # Verify data was stored
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM pressure_metrics")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)

    def test_get_pressure_history(self):
        """Test retrieving pressure history"""
        metrics = self.create_test_metrics()
        self.database.store_pressure_metrics(metrics)

        history = self.database.get_pressure_history(21900.0, 'C', hours=24)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['strike'], 21900.0)
        self.assertEqual(history[0]['option_type'], 'C')
        self.assertEqual(history[0]['pressure_ratio'], 2.0)

class TestUsageMonitor(unittest.TestCase):
    """Test usage monitoring and cost tracking"""

    def setUp(self):
        """Set up test monitor"""
        if not MBO_IMPLEMENTATION_AVAILABLE:
            self.skipTest("MBO implementation not available")

        self.monitor = UsageMonitor(daily_budget=10.0)

    def test_record_event(self):
        """Test recording an event and updating costs"""
        initial_cost = self.monitor.estimated_cost

        self.monitor.record_event(1000)  # 1KB event

        self.assertEqual(self.monitor.events_processed, 1)
        self.assertEqual(self.monitor.bytes_processed, 1000)
        self.assertGreater(self.monitor.estimated_cost, initial_cost)

    def test_should_continue_streaming_under_budget(self):
        """Test streaming should continue when under budget"""
        # Record small amount of usage
        self.monitor.record_event(1000)

        self.assertTrue(self.monitor.should_continue_streaming())

    def test_should_stop_streaming_over_budget(self):
        """Test streaming should stop when approaching budget limit"""
        # Simulate high usage to reach 80% of budget
        self.monitor.estimated_cost = 8.5  # 85% of $10 budget

        self.assertFalse(self.monitor.should_continue_streaming())

class TestDatabentoMBOIngestion(unittest.TestCase):
    """Test main MBO ingestion interface"""

    def setUp(self):
        """Set up test ingestion"""
        if not MBO_IMPLEMENTATION_AVAILABLE:
            self.skipTest("MBO implementation not available")

        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'api_key': 'test_key_12345',
            'symbols': ['NQ'],
            'streaming_mode': False,  # Use historical mode for testing
            'cache_dir': self.temp_dir
        }

    def tearDown(self):
        """Clean up test files"""
        # Clean up temp directory
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_initialization(self):
        """Test MBO ingestion initialization"""
        ingestion = DatabentoMBOIngestion(self.config)

        self.assertEqual(ingestion.api_key, 'test_key_12345')
        self.assertEqual(ingestion.symbols, ['NQ.OPT'])
        self.assertFalse(ingestion.streaming_mode)
        self.assertIsNotNone(ingestion.database)

    def test_load_historical_data(self):
        """Test loading historical data (fallback mode)"""
        ingestion = DatabentoMBOIngestion(self.config)
        result = ingestion.load_options_data()

        self.assertIsNotNone(result)
        self.assertEqual(result['metadata']['source'], 'databento_mbo')
        self.assertEqual(result['metadata']['mode'], 'historical')
        self.assertTrue(result['raw_data_available'])

class TestPipelineIntegration(unittest.TestCase):
    """Test integration with existing pipeline interface"""

    def setUp(self):
        """Set up integration test"""
        if not MBO_IMPLEMENTATION_AVAILABLE:
            self.skipTest("MBO implementation not available")

        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'api_key': 'test_integration_key',
            'symbols': ['NQ'],
            'streaming_mode': False,
            'cache_dir': self.temp_dir
        }

    def tearDown(self):
        """Clean up test files"""
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_load_databento_mbo_data_function(self):
        """Test standard interface function"""
        result = load_databento_mbo_data(self.config)

        self.assertIsNotNone(result)
        self.assertIn('metadata', result)
        self.assertIn('options_summary', result)
        self.assertIn('quality_metrics', result)
        self.assertEqual(result['metadata']['source'], 'databento_mbo')

    def test_pipeline_compatibility(self):
        """Test compatibility with existing pipeline structure"""
        result = load_databento_mbo_data(self.config)

        # Check required fields for pipeline integration
        required_fields = ['loader', 'metadata', 'options_summary', 'quality_metrics', 'raw_data_available']
        for field in required_fields:
            self.assertIn(field, result)

        # Check metadata structure
        self.assertIn('source', result['metadata'])
        self.assertIn('mode', result['metadata'])

        # Check quality metrics structure
        self.assertIn('data_source', result['quality_metrics'])
        self.assertIn('timestamp', result['quality_metrics'])

def run_comprehensive_tests():
    """Run all MBO streaming tests and return results"""

    if not MBO_IMPLEMENTATION_AVAILABLE:
        return {
            'status': 'SKIPPED',
            'reason': 'MBO implementation not available',
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'errors': []
        }

    # Create test suite
    test_classes = [
        TestMBOEventProcessor,
        TestPressureAggregator,
        TestMBODatabase,
        TestUsageMonitor,
        TestDatabentoMBOIngestion,
        TestPipelineIntegration
    ]

    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Calculate results
    total_tests = result.testsRun
    failed = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failed - errors

    # Collect error details
    error_details = []
    for test, error in result.failures + result.errors:
        error_details.append(f"{test}: {error}")

    return {
        'status': 'PASSED' if passed == total_tests else 'FAILED',
        'total_tests': total_tests,
        'passed': passed,
        'failed': failed,
        'errors': errors,
        'error_details': error_details,
        'success_rate': (passed / total_tests * 100) if total_tests > 0 else 0
    }

def run_all_tests():
    """Run all validation tests and generate evidence"""
    logger.info("=== Running Databento MBO Streaming Validation Tests ===")

    # Run comprehensive tests
    results = run_comprehensive_tests()

    # Generate evidence
    evidence = {
        "timestamp": datetime.now().isoformat(),
        "implementation": "databento_mbo_streaming",
        "version": "v3.0",
        "test_results": {
            "status": results['status'],
            "total_tests": results['total_tests'],
            "passed": results['passed'],
            "failed": results['failed'],
            "errors": results['errors'],
            "success_rate": results.get('success_rate', 0)
        },
        "capabilities_tested": [
            "MBO event processing",
            "Trade direction derivation",
            "Pressure aggregation",
            "Time window calculations",
            "SQLite storage",
            "Usage monitoring",
            "Cost tracking",
            "Pipeline integration"
        ],
        "key_features_validated": [
            "Real-time MBO streaming architecture",
            "Bid/ask pressure derivation from tick data",
            "Local SQLite storage for processed metrics",
            "Cost-effective streaming with monitoring",
            "Standard pipeline interface compatibility"
        ],
        "status": "VALIDATED" if results['status'] == 'PASSED' else "PARTIAL"
    }

    # Add error details if any
    if results.get('error_details'):
        evidence['error_details'] = results['error_details']

    # Save evidence
    with open('evidence.json', 'w') as f:
        json.dump(evidence, f, indent=2)

    # Summary
    logger.info(f"\n=== MBO Streaming Test Summary ===")
    logger.info(f"Status: {results['status']}")
    logger.info(f"Passed: {results['passed']}/{results['total_tests']} ({results.get('success_rate', 0):.1f}%)")

    if results.get('error_details'):
        logger.info(f"\nError Details:")
        for error in results['error_details']:
            logger.info(f"  - {error}")

    logger.info(f"\nEvidence saved to: evidence.json")

    return evidence

if __name__ == "__main__":
    evidence = run_all_tests()

    # Exit with appropriate code
    exit_code = 0 if evidence['status'] == 'VALIDATED' else 1
    sys.exit(exit_code)
