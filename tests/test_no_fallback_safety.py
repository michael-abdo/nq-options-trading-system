#!/usr/bin/env python3
"""
Test to verify NO FALLBACK behavior - critical for trading safety
This test ensures the system FAILS IMMEDIATELY if Databento is unavailable
"""

import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from tasks.options_trading_system.data_ingestion.sources_registry import DataSourcesRegistry


class TestNoFallbackSafety(unittest.TestCase):
    """Test that system has NO FALLBACKS for trading safety"""

    def setUp(self):
        """Set up test environment"""
        self.registry = DataSourcesRegistry()

    def test_databento_only_priority(self):
        """Test that only Databento has priority 1"""
        priorities = self.registry._source_priorities

        # Databento should be priority 1
        self.assertEqual(priorities.get('databento'), 1, "Databento must be priority 1")

        # ALL other sources should be priority 999 (disabled)
        for source, priority in priorities.items():
            if source != 'databento':
                self.assertEqual(priority, 999, f"{source} must be disabled (priority 999)")

    def test_barchart_hybrid_disabled(self):
        """Test that barchart hybrid method is disabled"""
        config = {'use_live_api': True}

        with self.assertRaises(ValueError) as context:
            self.registry._load_barchart_hybrid(config)

        self.assertIn("DISABLED", str(context.exception))
        self.assertIn("Only live Databento data is allowed", str(context.exception))

    def test_load_first_available_databento_only(self):
        """Test that load_first_available only accepts Databento"""
        # Test 1: No Databento config - should fail
        config_no_databento = {
            'barchart': {'enabled': True},
            'polygon': {'enabled': True}
        }

        with self.assertRaises(Exception) as context:
            self.registry.load_first_available(config_no_databento)

        self.assertIn("CRITICAL", str(context.exception))
        self.assertIn("Databento configuration missing", str(context.exception))

        # Test 2: Databento disabled - should fail
        config_databento_disabled = {
            'databento': {'enabled': False}
        }

        with self.assertRaises(Exception) as context:
            self.registry.load_first_available(config_databento_disabled)

        self.assertIn("CRITICAL", str(context.exception))
        self.assertIn("Databento is disabled", str(context.exception))

        # Test 3: Other sources enabled - should fail
        config_others_enabled = {
            'databento': {'enabled': True},
            'barchart': {'enabled': True},
            'polygon': {'enabled': True}
        }

        with self.assertRaises(Exception) as context:
            self.registry.load_first_available(config_others_enabled)

        self.assertIn("CRITICAL", str(context.exception))
        self.assertIn("Other data sources are enabled", str(context.exception))
        self.assertIn("DISABLE ALL OTHER SOURCES", str(context.exception))

    def test_no_fallback_on_databento_failure(self):
        """Test that system fails immediately if Databento fails"""
        # Mock a Databento-only config
        config_databento_only = {
            'databento': {
                'enabled': True,
                'api_key': 'invalid_key_to_force_failure'
            }
        }

        # This should fail with NO FALLBACK message
        with self.assertRaises(Exception) as context:
            # We expect this to fail because of invalid API key
            self.registry.load_first_available(config_databento_only)

        error_msg = str(context.exception)

        # Should mention NO FALLBACK
        self.assertIn("NO FALLBACK", error_msg)
        self.assertIn("Cannot proceed without live data", error_msg)

    def test_config_files_safety(self):
        """Test that config files have correct settings"""
        import json

        # Check all_sources.json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'all_sources.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Databento should be enabled
            self.assertTrue(
                config['data_sources']['databento']['enabled'],
                "Databento must be enabled in all_sources.json"
            )

            # All others should be disabled
            for source in ['barchart', 'polygon', 'tradovate']:
                if source in config['data_sources']:
                    self.assertFalse(
                        config['data_sources'][source]['enabled'],
                        f"{source} must be disabled in all_sources.json"
                    )

    def test_error_messages_are_clear(self):
        """Test that error messages clearly indicate trading safety"""
        config_missing_databento = {
            'barchart': {'enabled': False}
        }

        try:
            self.registry.load_first_available(config_missing_databento)
            self.fail("Should have raised exception")
        except Exception as e:
            error_msg = str(e)
            # Check for clear safety indicators
            self.assertIn("❌", error_msg, "Error should have warning emoji")
            self.assertIn("CRITICAL", error_msg, "Error should say CRITICAL")
            self.assertIn("NO OTHER DATA SOURCES ALLOWED", error_msg)


class TestTradingSafetyIntegration(unittest.TestCase):
    """Integration tests for trading safety"""

    def test_pipeline_uses_databento_only(self):
        """Test that run_pipeline.py uses databento_only profile"""
        pipeline_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'run_pipeline.py')

        if os.path.exists(pipeline_path):
            with open(pipeline_path, 'r') as f:
                content = f.read()

            # Should load databento_only profile
            self.assertIn('databento_only', content, "Pipeline must use databento_only profile")
            self.assertIn('TRADING SAFETY', content, "Pipeline should mention trading safety")
            self.assertIn('NO FALLBACKS', content, "Pipeline should mention no fallbacks")


if __name__ == '__main__':
    print("🔒 TESTING TRADING SAFETY - NO FALLBACKS ALLOWED")
    print("=" * 60)
    print("This test verifies that ONLY live Databento data is used")
    print("System must FAIL IMMEDIATELY if Databento is unavailable")
    print("=" * 60)

    unittest.main(verbosity=2)
