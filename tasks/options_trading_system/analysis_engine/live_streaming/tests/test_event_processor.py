#!/usr/bin/env python3
"""
Unit tests for Event Processor component
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
from datetime import datetime, timezone, timedelta
import time

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from ..event_processor import EventProcessor, create_standard_processor


class TestEventProcessor(unittest.TestCase):
    """Test the EventProcessor component"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'min_trade_size': 10,
            'max_events_per_second': 50,
            'initial_batch_size': 20,
            'batch_timeout_ms': 2000
        }
        self.processor = EventProcessor(self.config)

    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, 'processor') and self.processor.is_running:
            self.processor.stop_processing()

    def test_processor_initialization(self):
        """Test processor initialization"""
        self.assertEqual(self.processor.config['min_trade_size'], 10)
        self.assertEqual(self.processor.batch_size, 20)
        self.assertFalse(self.processor.is_running)
        self.assertEqual(len(self.processor.event_queue), 0)

    def test_event_filtering(self):
        """Test event filtering logic"""
        # Small trade - should be filtered
        small_event = {
            'timestamp': datetime.now(timezone.utc),
            'size': 5,
            'confidence': 0.9
        }
        self.assertFalse(self.processor._should_process_event(small_event))

        # Normal trade - should pass
        normal_event = {
            'timestamp': datetime.now(timezone.utc),
            'size': 50,
            'confidence': 0.9
        }
        self.assertTrue(self.processor._should_process_event(normal_event))

        # Low confidence - should be filtered
        low_conf_event = {
            'timestamp': datetime.now(timezone.utc),
            'size': 50,
            'confidence': 0.3
        }
        self.assertFalse(self.processor._should_process_event(low_conf_event))

    def test_market_hours_filtering(self):
        """Test market hours filtering"""
        # During market hours (Tuesday 2 PM ET)
        with patch('event_processor.get_eastern_time') as mock_time:
            mock_time.return_value = datetime(2025, 6, 17, 14, 0, 0)
            event = {
                'timestamp': datetime.now(timezone.utc),
                'size': 50,
                'confidence': 0.9
            }
            self.assertTrue(self.processor._should_process_event(event))

        # Outside market hours (Saturday)
        with patch('event_processor.get_eastern_time') as mock_time:
            mock_time.return_value = datetime(2025, 6, 14, 14, 0, 0)
            self.assertFalse(self.processor._should_process_event(event))

    def test_event_queueing(self):
        """Test event queueing mechanism"""
        self.processor.start_processing()

        # Add events
        for i in range(5):
            event = {
                'id': i,
                'timestamp': datetime.now(timezone.utc),
                'size': 50,
                'confidence': 0.9
            }
            self.processor.process_event(event)

        # Events should be queued
        self.assertEqual(len(self.processor.event_queue), 5)

        self.processor.stop_processing()

    def test_batch_creation(self):
        """Test batch creation logic"""
        # Test batch size trigger
        events = []
        for i in range(25):
            events.append({
                'id': i,
                'timestamp': datetime.now(timezone.utc),
                'size': 50,
                'confidence': 0.9
            })

        # Should create batch when reaching size
        self.assertTrue(self.processor._is_batch_ready())

        # Test timeout trigger
        self.processor.event_queue.clear()
        self.processor.event_queue.append({
            'timestamp': datetime.now(timezone.utc),
            'size': 50
        })
        self.processor.last_batch_time = datetime.now(timezone.utc) - timedelta(seconds=3)

        self.assertTrue(self.processor._is_batch_ready())

    def test_adaptive_batching(self):
        """Test adaptive batch size adjustment"""
        # Simulate high load
        self.processor.processing_times = [0.05] * 10  # Fast processing
        self.processor._adapt_batch_size()

        # Batch size should increase
        self.assertGreater(self.processor.batch_size, 20)

        # Simulate slow processing
        self.processor.processing_times = [0.5] * 10  # Slow processing
        self.processor._adapt_batch_size()

        # Batch size should decrease
        self.assertLess(self.processor.batch_size, 50)

    def test_batch_callback_execution(self):
        """Test batch callback execution"""
        batches_received = []

        def test_callback(batch):
            batches_received.append(batch)

        self.processor.register_batch_callback(test_callback)
        self.processor.start_processing()

        # Add enough events to trigger batch
        for i in range(self.processor.batch_size):
            event = {
                'id': i,
                'timestamp': datetime.now(timezone.utc),
                'size': 50,
                'confidence': 0.9
            }
            self.processor.process_event(event)

        # Wait for processing
        time.sleep(0.5)

        # Should have received at least one batch
        self.assertGreater(len(batches_received), 0)

        self.processor.stop_processing()

    def test_performance_stats(self):
        """Test performance statistics tracking"""
        self.processor.start_processing()

        # Process some events
        for i in range(100):
            event = {
                'id': i,
                'timestamp': datetime.now(timezone.utc),
                'size': 50 if i % 2 == 0 else 5,  # Mix of sizes
                'confidence': 0.9
            }
            self.processor.process_event(event)

        time.sleep(0.5)

        # Get stats
        stats = self.processor.get_performance_stats()

        self.assertIn('metrics', stats)
        self.assertIn('events_processed', stats['metrics'])
        self.assertIn('events_filtered', stats['metrics'])
        self.assertIn('filtering', stats)
        self.assertIn('filter_ratio', stats['filtering'])

        self.processor.stop_processing()

    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        # Set low rate limit for testing
        self.processor.config['max_events_per_second'] = 10

        # Try to process many events quickly
        start_time = time.time()
        for i in range(50):
            event = {
                'id': i,
                'timestamp': datetime.now(timezone.utc),
                'size': 50,
                'confidence': 0.9
            }
            self.processor.process_event(event)

        elapsed = time.time() - start_time

        # Should have been rate limited (take more than instant)
        self.assertGreater(elapsed, 1.0)

    def test_error_handling(self):
        """Test error handling in event processing"""
        def error_callback(batch):
            raise Exception("Test error")

        self.processor.register_batch_callback(error_callback)
        self.processor.start_processing()

        # Process events - should handle error gracefully
        with patch('event_processor.logger') as mock_logger:
            for i in range(self.processor.batch_size):
                event = {
                    'id': i,
                    'timestamp': datetime.now(timezone.utc),
                    'size': 50,
                    'confidence': 0.9
                }
                self.processor.process_event(event)

            time.sleep(0.5)

            # Should have logged error
            mock_logger.error.assert_called()

        self.processor.stop_processing()

    def test_create_standard_processor_factory(self):
        """Test factory function"""
        processor = create_standard_processor()

        self.assertIsInstance(processor, EventProcessor)
        self.assertEqual(processor.config['min_trade_size'], 10)

    def test_quality_based_prioritization(self):
        """Test event prioritization based on quality"""
        # High quality event
        high_quality = {
            'timestamp': datetime.now(timezone.utc),
            'size': 1000,
            'confidence': 0.95,
            'bid_ask_spread': 0.1
        }

        # Low quality event
        low_quality = {
            'timestamp': datetime.now(timezone.utc),
            'size': 20,
            'confidence': 0.6,
            'bid_ask_spread': 2.0
        }

        # Calculate priorities
        high_priority = self.processor._calculate_event_priority(high_quality)
        low_priority = self.processor._calculate_event_priority(low_quality)

        self.assertGreater(high_priority, low_priority)


if __name__ == '__main__':
    unittest.main()
