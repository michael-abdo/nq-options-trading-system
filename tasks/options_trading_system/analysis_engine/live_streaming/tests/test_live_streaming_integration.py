#!/usr/bin/env python3
"""
Integration tests for complete live streaming pipeline
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
import time
import tempfile
from datetime import datetime, timezone, timedelta
import json

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from ..streaming_bridge import StreamingBridge, create_streaming_bridge
from ..event_processor import EventProcessor, create_standard_processor
from ..pressure_aggregator import RealTimePressureEngine, create_standard_engine
from ..data_validator import StreamingDataValidator, create_mbo_validation_rules
from ..baseline_context_manager import RealTimeBaselineManager, create_baseline_manager


class TestLiveStreamingIntegration(unittest.TestCase):
    """Test complete live streaming pipeline integration"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        # Initialize all components
        self.processor = create_standard_processor()
        self.pressure_engine = create_standard_engine()
        self.validator = StreamingDataValidator(create_mbo_validation_rules())
        self.baseline_manager = create_baseline_manager(self.db_path)

        # Track outputs
        self.detected_signals = []
        self.pressure_metrics_generated = []
        self.validation_results = []

    def tearDown(self):
        """Clean up after tests"""
        if self.processor.is_running:
            self.processor.stop_processing()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_end_to_end_signal_detection(self):
        """Test complete pipeline from MBO event to IFD signal"""

        # Set up batch processing callback
        def process_batch(batch):
            for event in batch:
                # Validate
                should_process, validation_result = self.validator.validate_streaming_data(event)
                self.validation_results.append(validation_result)

                if should_process:
                    # Generate pressure metrics
                    metrics_list = self.pressure_engine.process_mbo_event(event)

                    for metrics in metrics_list:
                        self.pressure_metrics_generated.append(metrics)

                        # Update baseline
                        context = self.baseline_manager.update_baseline(
                            strike=metrics.strike,
                            option_type=metrics.option_type,
                            pressure_ratio=metrics.pressure_ratio,
                            volume=metrics.total_volume,
                            confidence=metrics.confidence,
                            timestamp=metrics.time_window
                        )

                        # Check for signal
                        if context.anomaly_detected and context.anomaly_severity in ['severe', 'extreme']:
                            signal = {
                                'timestamp': datetime.now(timezone.utc),
                                'strike': metrics.strike,
                                'option_type': metrics.option_type,
                                'pressure_ratio': metrics.pressure_ratio,
                                'severity': context.anomaly_severity,
                                'confidence': context.confidence
                            }
                            self.detected_signals.append(signal)

        # Register callback and start processing
        self.processor.register_batch_callback(process_batch)
        self.processor.start_processing()

        # Simulate normal market activity
        base_time = datetime.now(timezone.utc)
        for i in range(50):
            event = {
                'timestamp': base_time + timedelta(seconds=i),
                'instrument_id': 12345,
                'strike': 21900.0,
                'option_type': 'C',
                'bid_px_00': 100500000,
                'ask_px_00': 101000000,
                'size': 100,
                'side': 'BUY' if i % 2 == 0 else 'SELL',
                'trade_price': 100.75
            }
            self.processor.process_event(event)

        # Simulate institutional activity (should trigger signal)
        for i in range(10):
            institutional_event = {
                'timestamp': base_time + timedelta(seconds=50+i),
                'instrument_id': 12345,
                'strike': 21900.0,
                'option_type': 'C',
                'bid_px_00': 100500000,
                'ask_px_00': 101000000,
                'size': 1000,  # Large size
                'side': 'BUY',  # All buys
                'trade_price': 101.0  # Aggressive price
            }
            self.processor.process_event(institutional_event)

        # Allow processing to complete
        time.sleep(0.5)
        self.processor.stop_processing()

        # Verify pipeline operation
        self.assertGreater(len(self.validation_results), 0, "No validation results")
        self.assertGreater(len(self.pressure_metrics_generated), 0, "No pressure metrics generated")

        # Check if signal was detected
        if self.detected_signals:
            signal = self.detected_signals[0]
            self.assertEqual(signal['strike'], 21900.0)
            self.assertEqual(signal['option_type'], 'C')
            self.assertIn(signal['severity'], ['severe', 'extreme'])

    def test_streaming_bridge_integration(self):
        """Test streaming bridge coordinating all components"""
        bridge_config = {
            'symbols': ['NQ.OPT'],
            'daily_budget': 25.0,
            'market_hours_enforcement': False,  # Disable for testing
            'cost_monitoring': True,
            'mode': 'development'
        }

        bridge = StreamingBridge(bridge_config)

        # Track signals
        signals_received = []

        def signal_callback(signal):
            signals_received.append(signal)

        bridge.register_signal_callback(signal_callback)

        # Mock the IFD analyzer to return signals
        mock_signal = Mock(
            confidence=0.85,
            expected_direction='LONG',
            strike=21900.0,
            option_type='C',
            final_confidence=0.85
        )

        with patch.object(bridge, 'ifd_analyzer') as mock_analyzer:
            mock_analyzer.analyze_pressure_metrics.return_value = mock_signal

            # Process a pressure metrics event
            mock_metrics = Mock(
                strike=21900.0,
                option_type='C',
                pressure_ratio=2.5,
                total_volume=1000,
                confidence=0.8
            )

            bridge._on_pressure_metrics(mock_metrics)

        # Verify signal was received
        self.assertEqual(len(signals_received), 1)
        self.assertEqual(signals_received[0].confidence, 0.85)

    def test_performance_under_load(self):
        """Test system performance under high load"""
        self.processor.start_processing()

        # Track performance
        start_time = time.time()
        events_sent = 0

        # Send many events rapidly
        base_time = datetime.now(timezone.utc)
        for i in range(1000):
            event = {
                'timestamp': base_time + timedelta(milliseconds=i*10),
                'instrument_id': 12345,
                'strike': 21900.0 + (i % 10) * 100,
                'option_type': 'C' if i % 2 == 0 else 'P',
                'bid_px_00': 100500000 + (i % 100) * 10000,
                'ask_px_00': 101000000 + (i % 100) * 10000,
                'size': 50 + (i % 20) * 10,
                'side': 'BUY' if i % 3 != 0 else 'SELL',
                'trade_price': 100.75 + (i % 100) * 0.01
            }
            self.processor.process_event(event)
            events_sent += 1

        # Wait for processing
        time.sleep(1.0)
        self.processor.stop_processing()

        # Calculate throughput
        elapsed = time.time() - start_time
        throughput = events_sent / elapsed

        # Get statistics
        processor_stats = self.processor.get_performance_stats()

        # Verify performance
        self.assertGreater(throughput, 100, "Throughput too low")  # At least 100 events/sec
        self.assertGreater(processor_stats['metrics']['events_processed'], 0)
        self.assertLess(processor_stats['performance']['avg_batch_time'], 0.1)  # <100ms per batch

    def test_configuration_loading(self):
        """Test loading configuration from pipeline_config.json"""
        # Load config
        config_path = os.path.join(parent_dir, 'pipeline_config.json')

        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)

            streaming_config = config.get('live_streaming', {})

            # Verify configuration structure
            self.assertIn('enabled', streaming_config)
            self.assertIn('mode', streaming_config)
            self.assertIn('data_source', streaming_config)
            self.assertIn('ifd_integration', streaming_config)
            self.assertIn('cost_controls', streaming_config)

            # Test configuration values
            self.assertEqual(streaming_config['data_source']['provider'], 'databento')
            self.assertEqual(streaming_config['cost_controls']['daily_budget'], 25.0)

    def test_development_vs_production_mode(self):
        """Test differences between development and production modes"""
        # Development mode
        dev_config = {
            'mode': 'development',
            'symbols': ['NQ.OPT'],
            'market_hours_enforcement': True
        }

        dev_bridge = StreamingBridge(dev_config)

        # Should allow operation outside market hours
        with patch('streaming_bridge.get_eastern_time') as mock_time:
            # Saturday
            mock_time.return_value = datetime(2025, 6, 14, 14, 0, 0)
            self.assertTrue(dev_bridge._check_market_hours())

        # Production mode
        prod_config = {
            'mode': 'production',
            'symbols': ['NQ.OPT'],
            'market_hours_enforcement': True
        }

        prod_bridge = StreamingBridge(prod_config)

        # Should enforce market hours
        with patch('streaming_bridge.get_eastern_time') as mock_time:
            # Saturday
            mock_time.return_value = datetime(2025, 6, 14, 14, 0, 0)
            self.assertFalse(prod_bridge._check_market_hours())

    def test_error_recovery(self):
        """Test system recovery from errors"""
        # Set up processor with error-prone callback
        error_count = 0

        def error_callback(batch):
            nonlocal error_count
            error_count += 1
            if error_count < 3:
                raise Exception("Simulated error")
            # Process normally after 3 errors

        self.processor.register_batch_callback(error_callback)
        self.processor.start_processing()

        # Send events
        for i in range(100):
            event = {
                'timestamp': datetime.now(timezone.utc),
                'instrument_id': 12345,
                'strike': 21900.0,
                'option_type': 'C',
                'bid_px_00': 100500000,
                'ask_px_00': 101000000,
                'size': 100,
                'side': 'BUY'
            }
            self.processor.process_event(event)

        time.sleep(0.5)
        self.processor.stop_processing()

        # System should have recovered and continued processing
        stats = self.processor.get_performance_stats()
        self.assertGreater(stats['metrics']['batches_created'], 3)

    def test_multi_strike_processing(self):
        """Test processing multiple strikes simultaneously"""
        self.processor.start_processing()

        strikes = [21800, 21900, 22000, 22100, 22200]

        # Process batch callback to track metrics by strike
        metrics_by_strike = {}

        def process_batch(batch):
            for event in batch:
                should_process, _ = self.validator.validate_streaming_data(event)

                if should_process:
                    metrics_list = self.pressure_engine.process_mbo_event(event)

                    for metrics in metrics_list:
                        strike_key = f"{metrics.strike}{metrics.option_type}"
                        if strike_key not in metrics_by_strike:
                            metrics_by_strike[strike_key] = []
                        metrics_by_strike[strike_key].append(metrics)

        self.processor.register_batch_callback(process_batch)

        # Send events for multiple strikes
        base_time = datetime.now(timezone.utc)
        for i in range(100):
            for strike in strikes:
                event = {
                    'timestamp': base_time + timedelta(seconds=i),
                    'instrument_id': 12345 + strikes.index(strike),
                    'strike': float(strike),
                    'option_type': 'C',
                    'bid_px_00': 100500000,
                    'ask_px_00': 101000000,
                    'size': 50 + i % 50,
                    'side': 'BUY' if i % 2 == 0 else 'SELL',
                    'trade_price': 100.75
                }
                self.processor.process_event(event)

        time.sleep(1.0)
        self.processor.stop_processing()

        # Verify all strikes were processed
        for strike in strikes:
            strike_key = f"{float(strike)}C"
            self.assertIn(strike_key, metrics_by_strike, f"Strike {strike} not processed")


if __name__ == '__main__':
    unittest.main()
