#!/usr/bin/env python3
"""
Unit tests for Baseline Context Manager component
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
import sqlite3
from datetime import datetime, timezone, timedelta
import tempfile

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from ..baseline_context_manager import (
    RealTimeBaselineManager,
    create_baseline_manager,
    BaselineContext
)


class TestBaselineContextManager(unittest.TestCase):
    """Test the RealTimeBaselineManager component"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        self.config = {
            'window_size': 20,
            'update_frequency': 100,
            'anomaly_threshold': 2.0,
            'decay_factor': 0.95
        }
        self.manager = RealTimeBaselineManager(self.db_path, self.config)

    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, 'manager'):
            del self.manager
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_manager_initialization(self):
        """Test manager initialization and database setup"""
        self.assertEqual(self.manager.config['window_size'], 20)
        self.assertEqual(self.manager.config['anomaly_threshold'], 2.0)

        # Check database tables exist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        self.assertIn('realtime_baselines', tables)
        self.assertIn('baseline_history', tables)

    def test_baseline_update(self):
        """Test baseline update with new data"""
        context = self.manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=1.5,
            volume=1000,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        self.assertIsInstance(context, BaselineContext)
        self.assertEqual(context.current_value, 1.5)
        self.assertFalse(context.anomaly_detected)  # First update, no anomaly

    def test_anomaly_detection(self):
        """Test anomaly detection functionality"""
        # Establish baseline with normal values
        for i in range(25):
            self.manager.update_baseline(
                strike=21900.0,
                option_type='C',
                pressure_ratio=1.2 + (i % 5) * 0.1,  # Values between 1.2-1.6
                volume=100,
                confidence=0.8,
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=25-i)
            )

        # Normal update
        normal_context = self.manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=1.4,
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        self.assertFalse(normal_context.anomaly_detected)

        # Anomalous update (high value)
        anomaly_context = self.manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=5.0,  # Much higher than baseline
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        self.assertTrue(anomaly_context.anomaly_detected)
        self.assertIn(anomaly_context.anomaly_severity, ['moderate', 'severe', 'extreme'])

    def test_incremental_statistics(self):
        """Test incremental statistics calculation"""
        # Add multiple updates
        values = [1.0, 1.5, 2.0, 1.2, 1.8, 1.3, 1.7, 1.1, 1.6, 1.4]

        for i, value in enumerate(values):
            context = self.manager.update_baseline(
                strike=21900.0,
                option_type='C',
                pressure_ratio=value,
                volume=100,
                confidence=0.8,
                timestamp=datetime.now(timezone.utc) + timedelta(minutes=i)
            )

        # Check statistics are reasonable
        self.assertGreater(context.baseline_mean, 1.0)
        self.assertLess(context.baseline_mean, 2.0)
        self.assertGreater(context.baseline_std, 0)
        self.assertGreater(context.sample_size, 5)

    def test_confidence_adjustment(self):
        """Test confidence adjustment based on sample size"""
        # First update - low confidence due to no history
        context1 = self.manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=1.5,
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        initial_confidence = context1.confidence

        # Add more updates
        for i in range(20):
            self.manager.update_baseline(
                strike=21900.0,
                option_type='C',
                pressure_ratio=1.5 + (i % 3) * 0.1,
                volume=100,
                confidence=0.8,
                timestamp=datetime.now(timezone.utc) + timedelta(minutes=i+1)
            )

        # Latest update - higher confidence due to history
        context2 = self.manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=1.5,
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc) + timedelta(minutes=25)
        )

        self.assertGreater(context2.confidence, initial_confidence)

    def test_separate_strike_baselines(self):
        """Test that different strikes maintain separate baselines"""
        # Update strike 1
        context1 = self.manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=2.0,
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        # Update strike 2
        context2 = self.manager.update_baseline(
            strike=22000.0,
            option_type='C',
            pressure_ratio=1.0,
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        # Baselines should be different
        self.assertNotEqual(context1.baseline_mean, context2.baseline_mean)

    def test_call_put_separation(self):
        """Test that calls and puts maintain separate baselines"""
        # Update call
        call_context = self.manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=2.0,
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        # Update put
        put_context = self.manager.update_baseline(
            strike=21900.0,
            option_type='P',
            pressure_ratio=0.5,
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        # Same strike but different baselines
        self.assertNotEqual(call_context.baseline_mean, put_context.baseline_mean)

    def test_baseline_persistence(self):
        """Test baseline persistence across manager instances"""
        # Add baseline data
        self.manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=1.5,
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        # Create new manager instance
        new_manager = RealTimeBaselineManager(self.db_path, self.config)

        # Should load existing baseline
        context = new_manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=1.5,
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        # Should have historical data
        self.assertGreater(context.sample_size, 1)

    def test_manager_statistics(self):
        """Test manager statistics tracking"""
        # Process various updates
        for i in range(50):
            strike = 21900.0 + (i % 3) * 100
            pressure = 1.0 + (i % 10) * 0.5

            self.manager.update_baseline(
                strike=strike,
                option_type='C' if i % 2 == 0 else 'P',
                pressure_ratio=pressure,
                volume=100,
                confidence=0.8,
                timestamp=datetime.now(timezone.utc) + timedelta(minutes=i)
            )

        stats = self.manager.get_manager_stats()

        self.assertIn('updates_processed', stats)
        self.assertIn('anomalies_detected', stats)
        self.assertIn('unique_strikes', stats)
        self.assertIn('baseline_count', stats)
        self.assertEqual(stats['updates_processed'], 50)

    def test_create_baseline_manager_factory(self):
        """Test factory function"""
        manager = create_baseline_manager(self.db_path)

        self.assertIsInstance(manager, RealTimeBaselineManager)
        self.assertEqual(manager.config['window_size'], 20)

    def test_anomaly_severity_levels(self):
        """Test different anomaly severity levels"""
        # Establish baseline
        for i in range(20):
            self.manager.update_baseline(
                strike=21900.0,
                option_type='C',
                pressure_ratio=1.0,
                volume=100,
                confidence=0.8,
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=20-i)
            )

        # Test different severity levels
        # Mild anomaly (1-2 std dev)
        mild_context = self.manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=1.8,
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        # Moderate anomaly (2-3 std dev)
        moderate_context = self.manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=2.5,
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        # Severe anomaly (3-4 std dev)
        severe_context = self.manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=3.5,
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        # Extreme anomaly (>4 std dev)
        extreme_context = self.manager.update_baseline(
            strike=21900.0,
            option_type='C',
            pressure_ratio=5.0,
            volume=100,
            confidence=0.8,
            timestamp=datetime.now(timezone.utc)
        )

        # Check severity progression
        severities = [
            mild_context.anomaly_severity,
            moderate_context.anomaly_severity,
            severe_context.anomaly_severity,
            extreme_context.anomaly_severity
        ]

        self.assertIn('mild', severities)
        self.assertIn('extreme', severities)

    def test_history_cleanup(self):
        """Test automatic history cleanup"""
        # Add many historical entries
        for i in range(1000):
            self.manager.update_baseline(
                strike=21900.0,
                option_type='C',
                pressure_ratio=1.0 + (i % 10) * 0.1,
                volume=100,
                confidence=0.8,
                timestamp=datetime.now(timezone.utc) - timedelta(hours=1000-i)
            )

        # Check that old entries are cleaned up
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM baseline_history")
        count = cursor.fetchone()[0]
        conn.close()

        # Should keep reasonable history (not all 1000)
        self.assertLess(count, 500)


if __name__ == '__main__':
    unittest.main()
