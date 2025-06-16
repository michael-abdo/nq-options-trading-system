#!/usr/bin/env python3
"""
Unit tests for Data Validator component
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

from ..data_validator import StreamingDataValidator, create_mbo_validation_rules, ValidationResult


class TestDataValidator(unittest.TestCase):
    """Test the StreamingDataValidator component"""

    def setUp(self):
        """Set up test fixtures"""
        self.rules = create_mbo_validation_rules()
        self.validator = StreamingDataValidator(self.rules)

    def test_validator_initialization(self):
        """Test validator initialization"""
        self.assertEqual(len(self.validator.validation_rules), len(self.rules))
        self.assertEqual(self.validator.anomaly_threshold, 3.0)
        self.assertEqual(len(self.validator.validation_history), 0)

    def test_valid_mbo_event(self):
        """Test validation of valid MBO event"""
        valid_event = {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'strike': 21900.0,
            'option_type': 'C',
            'bid_px_00': 100500000,  # $100.50
            'ask_px_00': 101000000,  # $101.00
            'size': 100,
            'side': 'BUY',
            'trade_price': 100.75
        }

        should_process, result = self.validator.validate_streaming_data(valid_event)

        self.assertTrue(should_process)
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertGreater(result.quality_score, 0.7)
        self.assertEqual(len(result.warnings), 0)

    def test_missing_required_fields(self):
        """Test validation with missing required fields"""
        invalid_event = {
            'timestamp': datetime.now(timezone.utc),
            'strike': 21900.0,
            # Missing required fields
        }

        should_process, result = self.validator.validate_streaming_data(invalid_event)

        self.assertFalse(should_process)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
        self.assertIn('required_fields', result.errors[0])

    def test_price_validation(self):
        """Test price reasonableness validation"""
        # Negative price
        negative_price = {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'strike': 21900.0,
            'option_type': 'C',
            'bid_px_00': -100000000,  # Negative
            'ask_px_00': 101000000,
            'size': 100,
            'side': 'BUY'
        }

        should_process, result = self.validator.validate_streaming_data(negative_price)

        self.assertFalse(should_process)
        self.assertIn('price_validation', result.errors[0])

        # Extreme price
        extreme_price = negative_price.copy()
        extreme_price['bid_px_00'] = 10000000000  # $10,000

        should_process, result = self.validator.validate_streaming_data(extreme_price)

        self.assertFalse(should_process)
        self.assertIn('price_validation', result.errors[0])

    def test_spread_validation(self):
        """Test bid-ask spread validation"""
        # Inverted spread
        inverted_spread = {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'strike': 21900.0,
            'option_type': 'C',
            'bid_px_00': 102000000,  # $102 bid
            'ask_px_00': 101000000,  # $101 ask (inverted)
            'size': 100,
            'side': 'BUY'
        }

        should_process, result = self.validator.validate_streaming_data(inverted_spread)

        self.assertFalse(should_process)
        self.assertIn('spread_validation', result.errors[0])

        # Extreme spread
        extreme_spread = inverted_spread.copy()
        extreme_spread['bid_px_00'] = 100000000  # $100
        extreme_spread['ask_px_00'] = 200000000  # $200 (100% spread)

        should_process, result = self.validator.validate_streaming_data(extreme_spread)

        self.assertTrue(should_process)  # Allowed but with warning
        self.assertGreater(len(result.warnings), 0)
        self.assertLess(result.quality_score, 0.5)

    def test_size_validation(self):
        """Test trade size validation"""
        # Zero size
        zero_size = {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'strike': 21900.0,
            'option_type': 'C',
            'bid_px_00': 100500000,
            'ask_px_00': 101000000,
            'size': 0,
            'side': 'BUY'
        }

        should_process, result = self.validator.validate_streaming_data(zero_size)

        self.assertFalse(should_process)
        self.assertIn('size_validation', result.errors[0])

        # Extreme size
        extreme_size = zero_size.copy()
        extreme_size['size'] = 100000  # Very large

        should_process, result = self.validator.validate_streaming_data(extreme_size)

        self.assertTrue(should_process)  # Allowed but affects quality
        self.assertLess(result.quality_score, 0.8)

    def test_timestamp_validation(self):
        """Test timestamp validation"""
        # Future timestamp
        future_event = {
            'timestamp': datetime.now(timezone.utc) + timedelta(hours=1),
            'instrument_id': 12345,
            'strike': 21900.0,
            'option_type': 'C',
            'bid_px_00': 100500000,
            'ask_px_00': 101000000,
            'size': 100,
            'side': 'BUY'
        }

        should_process, result = self.validator.validate_streaming_data(future_event)

        self.assertFalse(should_process)
        self.assertIn('timestamp_validation', result.errors[0])

        # Very old timestamp
        old_event = future_event.copy()
        old_event['timestamp'] = datetime.now(timezone.utc) - timedelta(days=2)

        should_process, result = self.validator.validate_streaming_data(old_event)

        self.assertTrue(should_process)  # Allowed with warning
        self.assertGreater(len(result.warnings), 0)

    def test_quality_score_calculation(self):
        """Test quality score calculation"""
        # Perfect quality event
        perfect_event = {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'strike': 21900.0,
            'option_type': 'C',
            'bid_px_00': 100500000,
            'ask_px_00': 100750000,  # Tight spread
            'size': 100,
            'side': 'BUY',
            'confidence': 0.95
        }

        _, result = self.validator.validate_streaming_data(perfect_event)
        self.assertGreater(result.quality_score, 0.9)

        # Poor quality event
        poor_event = perfect_event.copy()
        poor_event['ask_px_00'] = 105000000  # Wide spread
        poor_event['confidence'] = 0.4
        poor_event['size'] = 10000  # Unusual size

        _, result = self.validator.validate_streaming_data(poor_event)
        self.assertLess(result.quality_score, 0.5)

    def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        # Generate many errors
        for i in range(15):
            bad_event = {
                'timestamp': datetime.now(timezone.utc),
                'strike': -1000,  # Invalid
                'size': -100      # Invalid
            }
            self.validator.validate_streaming_data(bad_event)

        # Circuit breaker should trigger
        self.assertTrue(self.validator.circuit_breaker_triggered)

        # Further validations should fail
        valid_event = {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'strike': 21900.0,
            'option_type': 'C',
            'bid_px_00': 100500000,
            'ask_px_00': 101000000,
            'size': 100,
            'side': 'BUY'
        }

        should_process, result = self.validator.validate_streaming_data(valid_event)
        self.assertFalse(should_process)
        self.assertIn('Circuit breaker', result.errors[0])

    def test_anomaly_detection(self):
        """Test anomaly detection in data patterns"""
        # Establish baseline with normal events
        for i in range(20):
            normal_event = {
                'timestamp': datetime.now(timezone.utc),
                'instrument_id': 12345,
                'strike': 21900.0,
                'option_type': 'C',
                'bid_px_00': 100500000 + (i * 10000),  # Small variations
                'ask_px_00': 101000000 + (i * 10000),
                'size': 100 + (i % 10) * 10,
                'side': 'BUY' if i % 2 == 0 else 'SELL'
            }
            self.validator.validate_streaming_data(normal_event)

        # Anomalous event
        anomaly_event = {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'strike': 21900.0,
            'option_type': 'C',
            'bid_px_00': 200000000,  # Sudden price jump
            'ask_px_00': 201000000,
            'size': 10000,           # Huge size
            'side': 'BUY'
        }

        should_process, result = self.validator.validate_streaming_data(anomaly_event)

        self.assertTrue(should_process)  # Still processed
        self.assertGreater(len(result.warnings), 0)
        self.assertIn('anomaly', result.warnings[0].lower())

    def test_validation_statistics(self):
        """Test validation statistics tracking"""
        # Process mix of valid and invalid events
        for i in range(100):
            if i % 10 == 0:
                # Invalid event
                event = {'timestamp': datetime.now(timezone.utc)}
            else:
                # Valid event
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
            self.validator.validate_streaming_data(event)

        stats = self.validator.get_comprehensive_stats()

        self.assertIn('events_validated', stats)
        self.assertIn('validation_failures', stats)
        self.assertIn('circuit_breaker_triggered', stats)
        self.assertIn('metrics', stats)
        self.assertGreater(stats['events_validated'], 0)

    def test_create_mbo_validation_rules(self):
        """Test validation rules creation"""
        rules = create_mbo_validation_rules()

        self.assertIsInstance(rules, list)
        self.assertGreater(len(rules), 0)

        # Check rule structure
        for rule in rules:
            self.assertIn('name', rule)
            self.assertIn('check', rule)
            self.assertIn('severity', rule)
            self.assertIn(rule['severity'], ['error', 'warning'])


if __name__ == '__main__':
    unittest.main()
