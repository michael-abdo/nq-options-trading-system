#!/usr/bin/env python3
"""
Test script for saved data report generation
"""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.run_saved_data_report import (
    load_saved_data, analyze_data_quality, convert_api_to_strikes,
    calculate_probability, calculate_ev_for_all_combinations
)

def test_load_saved_data():
    """Test that we can load saved data"""
    print("Testing load_saved_data...")
    data = load_saved_data()
    assert data is not None
    assert 'data' in data
    assert 'Call' in data['data']
    assert 'Put' in data['data']
    print("✅ load_saved_data passed")

def test_analyze_data_quality():
    """Test data quality analysis"""
    print("\nTesting analyze_data_quality...")
    data = load_saved_data()
    quality = analyze_data_quality(data)
    
    assert 'volume_coverage' in quality
    assert 'oi_coverage' in quality
    assert quality['volume_coverage'] > 50  # We know it's 51.9%
    assert quality['oi_coverage'] > 60      # We know it's 62.7%
    print(f"✅ analyze_data_quality passed - Volume: {quality['volume_coverage']:.1f}%, OI: {quality['oi_coverage']:.1f}%")

def test_convert_api_to_strikes():
    """Test API data conversion"""
    print("\nTesting convert_api_to_strikes...")
    data = load_saved_data()
    current_price, strikes = convert_api_to_strikes(data)
    
    assert current_price > 0
    assert len(strikes) > 0
    assert all(hasattr(s, 'price') for s in strikes)
    print(f"✅ convert_api_to_strikes passed - Price: ${current_price:,.2f}, Strikes: {len(strikes)}")

def test_calculate_probability():
    """Test probability calculation"""
    print("\nTesting calculate_probability...")
    data = load_saved_data()
    current_price, strikes = convert_api_to_strikes(data)
    
    # Test a simple long setup
    tp = current_price + 100
    sl = current_price - 50
    prob = calculate_probability(current_price, tp, sl, strikes, 'long')
    
    assert 0 <= prob <= 1
    print(f"✅ calculate_probability passed - Probability: {prob:.2%}")

def test_calculate_ev():
    """Test EV calculation"""
    print("\nTesting calculate_ev_for_all_combinations...")
    data = load_saved_data()
    current_price, strikes = convert_api_to_strikes(data)
    
    # Use all strikes for real test
    setups = calculate_ev_for_all_combinations(current_price, strikes)
    
    assert len(setups) > 0
    assert all(hasattr(s, 'ev') for s in setups)
    print(f"✅ calculate_ev_for_all_combinations passed - Found {len(setups)} setups")

def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("Running NQ Options EV System Tests")
    print("="*60)
    
    try:
        test_load_saved_data()
        test_analyze_data_quality()
        test_convert_api_to_strikes()
        test_calculate_probability()
        test_calculate_ev()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)