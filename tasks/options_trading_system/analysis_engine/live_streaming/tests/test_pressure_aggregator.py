#!/usr/bin/env python3
"""
Unit tests for Pressure Aggregator component
"""

import unittest
from unittest.mock import Mock, patch
import os
import sys
from datetime import datetime, timezone, timedelta

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from ..pressure_aggregator import RealTimePressureEngine, create_standard_engine
from data_ingestion.databento_api.solution import PressureMetrics


class TestPressureAggregator(unittest.TestCase):
    """Test the RealTimePressureEngine component"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'window_sizes': [1, 5, 15],
            'min_events_for_window': 5,
            'pressure_decay_factor': 0.95
        }
        self.engine = RealTimePressureEngine(self.config)

    def test_engine_initialization(self):
        """Test engine initialization"""
        self.assertEqual(self.engine.window_sizes, [1, 5, 15])
        self.assertEqual(len(self.engine.active_windows), 0)
        self.assertEqual(len(self.engine.completed_metrics), 0)

    def test_mbo_event_processing(self):
        """Test processing of MBO events"""
        # Create test event
        event = {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'strike': 21900.0,
            'option_type': 'C',
            'bid_px_00': 100500000,  # $100.50
            'ask_px_00': 101000000,  # $101.00
            'size': 100,
            'side': 'BUY',
            'trade_price': 101.0
        }

        # Process event
        metrics = self.engine.process_mbo_event(event)

        # Should not complete window immediately
        self.assertEqual(len(metrics), 0)

        # Should have active windows
        self.assertGreater(len(self.engine.active_windows), 0)

    def test_window_completion(self):
        """Test window completion logic"""
        base_time = datetime.now(timezone.utc)

        # Process multiple events to complete a 1-minute window
        for i in range(10):
            event = {
                'timestamp': base_time + timedelta(seconds=i*6),
                'instrument_id': 12345,
                'strike': 21900.0,
                'option_type': 'C',
                'bid_px_00': 100500000,
                'ask_px_00': 101000000,
                'size': 50,
                'side': 'BUY' if i % 2 == 0 else 'SELL',
                'trade_price': 100.75
            }
            self.engine.process_mbo_event(event)

        # Check for expired windows after 1 minute
        future_time = base_time + timedelta(minutes=1, seconds=10)
        expired_metrics = self.engine._check_expired_windows(future_time, 1)

        # Should have completed 1-minute window
        self.assertGreater(len(expired_metrics), 0)

    def test_pressure_calculation(self):
        """Test pressure ratio calculation"""
        window_key = (21900.0, 'C', 1, datetime.now(timezone.utc))
        window_data = self.engine.active_windows[window_key] = {
            'events': [],
            'bid_volume': 500,
            'ask_volume': 300,
            'total_volume': 800,
            'bid_value': 50000.0,
            'ask_value': 30300.0,
            'max_bid': 101.0,
            'min_ask': 100.5,
            'unique_prices': set([100.5, 100.75, 101.0]),
            'start_time': datetime.now(timezone.utc),
            'trade_count': 10
        }

        # Calculate pressure
        pressure_ratio = self.engine._calculate_pressure_ratio(window_data)

        # Buy pressure > sell pressure
        self.assertGreater(pressure_ratio, 1.0)
        self.assertAlmostEqual(pressure_ratio, 500/300, places=2)

    def test_multi_timeframe_aggregation(self):
        """Test aggregation across multiple timeframes"""
        base_time = datetime.now(timezone.utc)

        # Process events
        for i in range(20):
            event = {
                'timestamp': base_time + timedelta(seconds=i*3),
                'instrument_id': 12345,
                'strike': 21900.0,
                'option_type': 'C',
                'bid_px_00': 100500000,
                'ask_px_00': 101000000,
                'size': 100,
                'side': 'BUY',
                'trade_price': 100.75
            }
            self.engine.process_mbo_event(event)

        # Should have windows for all timeframes
        window_keys = list(self.engine.active_windows.keys())
        timeframes = set(key[2] for key in window_keys)

        self.assertEqual(timeframes, {1, 5, 15})

    def test_pressure_metrics_creation(self):
        """Test PressureMetrics object creation"""
        window_data = {
            'bid_volume': 600,
            'ask_volume': 400,
            'total_volume': 1000,
            'trade_count': 50,
            'unique_prices': set(range(10)),
            'start_time': datetime.now(timezone.utc),
            'events': []
        }

        metrics = self.engine._create_pressure_metrics(
            21900.0, 'C', 5, window_data
        )

        self.assertIsInstance(metrics, PressureMetrics)
        self.assertEqual(metrics.strike, 21900.0)
        self.assertEqual(metrics.option_type, 'C')
        self.assertEqual(metrics.total_trades, 50)
        self.assertEqual(metrics.dominant_side, 'BUY')
        self.assertGreater(metrics.confidence, 0.5)

    def test_confidence_calculation(self):
        """Test confidence score calculation"""
        # High volume, clear direction
        high_conf_data = {
            'bid_volume': 1000,
            'ask_volume': 200,
            'total_volume': 1200,
            'trade_count': 100,
            'unique_prices': set(range(20))
        }

        confidence = self.engine._calculate_confidence(
            high_conf_data, 2.0
        )
        self.assertGreater(confidence, 0.8)

        # Low volume, unclear direction
        low_conf_data = {
            'bid_volume': 55,
            'ask_volume': 45,
            'total_volume': 100,
            'trade_count': 5,
            'unique_prices': set(range(3))
        }

        confidence = self.engine._calculate_confidence(
            low_conf_data, 1.0
        )
        self.assertLess(confidence, 0.5)

    def test_engine_statistics(self):
        """Test engine statistics tracking"""
        # Process some events
        for i in range(50):
            event = {
                'timestamp': datetime.now(timezone.utc) + timedelta(seconds=i),
                'instrument_id': 12345,
                'strike': 21900.0,
                'option_type': 'C',
                'bid_px_00': 100500000,
                'ask_px_00': 101000000,
                'size': 50,
                'side': 'BUY' if i % 2 == 0 else 'SELL',
                'trade_price': 100.75
            }
            self.engine.process_mbo_event(event)

        # Get stats
        stats = self.engine.get_engine_stats()

        self.assertIn('events_processed', stats)
        self.assertIn('active_windows', stats)
        self.assertIn('aggregation', stats)
        self.assertEqual(stats['events_processed'], 50)

    def test_create_standard_engine_factory(self):
        """Test factory function"""
        engine = create_standard_engine()

        self.assertIsInstance(engine, RealTimePressureEngine)
        self.assertEqual(engine.window_sizes, [1, 5, 15])

    def test_event_deduplication(self):
        """Test duplicate event handling"""
        event = {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'strike': 21900.0,
            'option_type': 'C',
            'bid_px_00': 100500000,
            'ask_px_00': 101000000,
            'size': 100,
            'side': 'BUY',
            'trade_price': 101.0,
            'event_id': 'test123'
        }

        # Process same event twice
        self.engine.process_mbo_event(event)
        self.engine.process_mbo_event(event)

        # Should only count once
        self.assertEqual(self.engine.events_processed, 1)

    def test_option_type_separation(self):
        """Test that calls and puts are tracked separately"""
        base_time = datetime.now(timezone.utc)

        # Process call events
        for i in range(5):
            event = {
                'timestamp': base_time + timedelta(seconds=i),
                'instrument_id': 12345,
                'strike': 21900.0,
                'option_type': 'C',
                'bid_px_00': 100500000,
                'ask_px_00': 101000000,
                'size': 100,
                'side': 'BUY',
                'trade_price': 100.75
            }
            self.engine.process_mbo_event(event)

        # Process put events
        for i in range(5):
            event = {
                'timestamp': base_time + timedelta(seconds=i),
                'instrument_id': 12346,
                'strike': 21900.0,
                'option_type': 'P',
                'bid_px_00': 50500000,
                'ask_px_00': 51000000,
                'size': 100,
                'side': 'SELL',
                'trade_price': 50.75
            }
            self.engine.process_mbo_event(event)

        # Check windows are separate
        call_windows = [k for k in self.engine.active_windows.keys() if k[1] == 'C']
        put_windows = [k for k in self.engine.active_windows.keys() if k[1] == 'P']

        self.assertGreater(len(call_windows), 0)
        self.assertGreater(len(put_windows), 0)
        self.assertNotEqual(call_windows, put_windows)


if __name__ == '__main__':
    unittest.main()
