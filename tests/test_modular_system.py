#!/usr/bin/env python3
"""
Test the new modular trading analysis system
"""

import sys
import os
import unittest
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_models import OptionsContract, OptionsChain, OptionType, DataRequirements
from plugins.data_sources.saved_data import SavedDataSource
from plugins.strategies.expected_value import ExpectedValueStrategy


class TestModularSystem(unittest.TestCase):
    """Test the modular trading analysis system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_data_path = "data/api_responses/options_data_20250602_141553.json"
        
    def test_data_models(self):
        """Test core data models"""
        print("\n🧪 Testing data models...")
        
        # Test OptionsContract
        contract = OptionsContract(
            symbol="NQ21300C",
            strike=21300,
            expiration=datetime(2025, 6, 30),
            option_type=OptionType.CALL,
            underlying_price=21376.75,
            timestamp=datetime.now(),
            volume=100,
            open_interest=500,
            last_price=125.50
        )
        
        self.assertEqual(contract.strike, 21300)
        self.assertEqual(contract.option_type, OptionType.CALL)
        self.assertIsNotNone(contract.moneyness)
        self.assertGreater(contract.intrinsic_value, 0)  # ITM call
        
        print(f"✅ Contract: {contract.symbol}, Moneyness: {contract.moneyness:.3f}, "
              f"Intrinsic: {contract.intrinsic_value:.2f}")
    
    def test_saved_data_source(self):
        """Test saved data source plugin"""
        print("\n🧪 Testing saved data source...")
        
        # Check if test data exists
        if not os.path.exists(self.test_data_path):
            self.skipTest(f"Test data not found: {self.test_data_path}")
        
        # Initialize data source
        config = {"file_path": self.test_data_path}
        data_source = SavedDataSource(config)
        
        # Test connection
        self.assertTrue(data_source.validate_connection())
        
        # Fetch data
        chain = data_source.fetch_data()
        
        # Validate results
        self.assertIsInstance(chain, OptionsChain)
        self.assertEqual(chain.underlying_symbol, "NQ")
        self.assertGreater(len(chain.contracts), 0)
        self.assertGreater(len(chain.calls), 0)
        self.assertGreater(len(chain.puts), 0)
        
        # Check data quality
        quality = chain.data_quality_metrics
        self.assertGreater(quality['volume_coverage'], 0.4)  # Should be > 40%
        self.assertGreater(quality['oi_coverage'], 0.5)     # Should be > 50%
        
        print(f"✅ Loaded {len(chain.contracts)} contracts, "
              f"Volume: {quality['volume_coverage']:.1%}, OI: {quality['oi_coverage']:.1%}")
    
    def test_expected_value_strategy(self):
        """Test Expected Value strategy plugin"""
        print("\n🧪 Testing Expected Value strategy...")
        
        # Check if test data exists
        if not os.path.exists(self.test_data_path):
            self.skipTest(f"Test data not found: {self.test_data_path}")
        
        # Get test data
        data_source = SavedDataSource({"file_path": self.test_data_path})
        chain = data_source.fetch_data()
        
        # Initialize strategy
        config = {
            "weights": {
                "oi_factor": 0.35,
                "vol_factor": 0.25,
                "pcr_factor": 0.25,
                "distance_factor": 0.15
            },
            "min_ev": 15,
            "min_probability": 0.60
        }
        strategy = ExpectedValueStrategy(config)
        
        # Test requirements
        requirements = strategy.get_requirements()
        self.assertIsInstance(requirements, DataRequirements)
        self.assertTrue(requirements.requires_volume)
        self.assertTrue(requirements.requires_open_interest)
        
        # Validate data
        is_valid, errors = strategy.validate_data(chain)
        if not is_valid:
            print(f"⚠️ Data validation warnings: {errors}")
        
        # Run analysis
        result = strategy.analyze(chain)
        
        # Validate results
        self.assertEqual(result.strategy_name, "ExpectedValueStrategy")
        self.assertEqual(result.underlying_symbol, "NQ")
        self.assertGreater(result.underlying_price, 0)
        
        # Check for signals and metrics
        print(f"✅ Strategy generated {len(result.signals)} signals, {len(result.metrics)} metrics")
        
        if result.signals:
            top_signal = result.signals[0]
            print(f"   Top signal: {top_signal['direction']} {top_signal['confidence']:.1%} confidence")
            print(f"   Target: ${top_signal['target_price']:,.0f}, Stop: ${top_signal['stop_loss']:,.0f}")
            print(f"   EV: {top_signal['expected_value']:+.1f}, R/R: {top_signal['risk_reward_ratio']:.1f}")
        
        if result.warnings:
            print(f"   Warnings: {len(result.warnings)}")
    
    def test_data_requirements_validation(self):
        """Test data requirements validation"""
        print("\n🧪 Testing data requirements validation...")
        
        # Create test requirements
        requirements = DataRequirements(
            requires_volume=True,
            requires_open_interest=True,
            min_contracts=5
        )
        
        # Create minimal test chain
        contracts = [
            OptionsContract(
                symbol=f"TEST{i}",
                strike=21000 + i * 100,
                expiration=datetime(2025, 6, 30),
                option_type=OptionType.CALL if i % 2 == 0 else OptionType.PUT,
                underlying_price=21376.75,
                timestamp=datetime.now(),
                volume=50,
                open_interest=100
            )
            for i in range(10)
        ]
        
        chain = OptionsChain(
            underlying_symbol="TEST",
            underlying_price=21376.75,
            timestamp=datetime.now(),
            contracts=contracts
        )
        
        # Test validation
        is_valid, errors = requirements.validate_data(chain)
        self.assertTrue(is_valid, f"Validation failed: {errors}")
        
        print(f"✅ Data validation passed for {len(contracts)} contracts")


def run_modular_tests():
    """Run all modular system tests"""
    print("="*80)
    print("MODULAR TRADING SYSTEM TESTS")
    print("="*80)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestModularSystem)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*80)
    if result.wasSuccessful():
        print("✅ ALL MODULAR SYSTEM TESTS PASSED!")
    else:
        print(f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        
        for test, traceback in result.failures + result.errors:
            print(f"\nFailed: {test}")
            print(traceback)
    
    print("="*80)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_modular_tests()
    exit(0 if success else 1)