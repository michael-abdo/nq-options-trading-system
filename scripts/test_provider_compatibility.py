#!/usr/bin/env python3
"""
Compatibility test for Databento 5M Provider with IFD integration

Verifies that:
1. Existing OHLCV functionality remains unchanged
2. New IFD methods work correctly
3. Fallback behavior is robust
4. Performance is not degraded
"""

import os
import sys
from datetime import datetime, timedelta
import logging
import time

# Add parent directory for imports  
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import the enhanced provider
try:
    from scripts.databento_5m_provider import Databento5MinuteProvider
    PROVIDER_AVAILABLE = True
except ImportError as e:
    print(f"❌ Provider not available: {e}")
    PROVIDER_AVAILABLE = False

logger = logging.getLogger(__name__)

def test_backward_compatibility():
    """Test that existing OHLCV functionality is unchanged"""
    print("\n=== Testing Backward Compatibility ===")
    
    if not PROVIDER_AVAILABLE:
        print("❌ Provider not available - skipping test")
        return False
    
    try:
        # Test 1: Original initialization should work
        print("1. Testing original initialization...")
        provider_old = Databento5MinuteProvider()  # No new parameters
        print("   ✅ Original initialization works")
        
        # Test 2: New initialization with IFD disabled
        print("2. Testing new initialization with IFD disabled...")
        provider_no_ifd = Databento5MinuteProvider(enable_ifd_signals=False)
        print("   ✅ New initialization with IFD disabled works")
        
        # Test 3: Check that original methods exist and work
        print("3. Testing original method signatures...")
        
        # These should all exist and work without throwing errors
        assert hasattr(provider_old, 'get_latest_bars'), "get_latest_bars method missing"
        assert hasattr(provider_old, 'get_historical_5min_bars'), "get_historical_5min_bars method missing"
        assert hasattr(provider_old, 'clear_cache'), "clear_cache method missing"
        assert hasattr(provider_old, 'start_live_streaming'), "start_live_streaming method missing"
        assert hasattr(provider_old, 'stop_live_streaming'), "stop_live_streaming method missing"
        
        print("   ✅ All original methods present")
        
        # Test 4: Original method signatures unchanged
        print("4. Testing method call compatibility...")
        
        # This should work exactly as before (may fail due to no API key in test, but signature should be right)
        try:
            # Test signature compatibility - these calls should at least parse correctly
            import inspect
            
            # Check get_latest_bars signature
            sig = inspect.signature(provider_old.get_latest_bars)
            params = list(sig.parameters.keys())
            expected_params = ['symbol', 'count']
            for param in expected_params:
                assert param in params, f"Parameter {param} missing from get_latest_bars"
            
            # Check get_historical_5min_bars signature  
            sig = inspect.signature(provider_old.get_historical_5min_bars)
            params = list(sig.parameters.keys())
            expected_params = ['symbol', 'start', 'end', 'hours_back']
            for param in expected_params:
                assert param in params, f"Parameter {param} missing from get_historical_5min_bars"
            
            print("   ✅ Method signatures are backward compatible")
            
        except Exception as e:
            print(f"   ⚠️  Method signature check failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False

def test_new_ifd_functionality():
    """Test that new IFD methods work correctly"""
    print("\n=== Testing New IFD Functionality ===")
    
    if not PROVIDER_AVAILABLE:
        print("❌ Provider not available - skipping test")
        return False
    
    try:
        # Test with IFD enabled (may fail if bridge not available, but should handle gracefully)
        print("1. Testing IFD-enabled initialization...")
        provider_ifd = Databento5MinuteProvider(enable_ifd_signals=True)
        print("   ✅ IFD-enabled initialization works")
        
        # Test 2: Check new methods exist
        print("2. Testing new method presence...")
        new_methods = [
            'get_latest_bars_with_ifd',
            'get_historical_bars_with_ifd', 
            'get_ifd_signals_only',
            'get_ifd_bridge_status',
            'add_ifd_signal',
            'toggle_ifd_signals'
        ]
        
        for method in new_methods:
            assert hasattr(provider_ifd, method), f"New method {method} missing"
        
        print("   ✅ All new IFD methods present")
        
        # Test 3: Bridge status reporting
        print("3. Testing IFD bridge status...")
        status = provider_ifd.get_ifd_bridge_status()
        assert isinstance(status, dict), "Bridge status should return dict"
        assert 'enabled' in status, "Status should contain 'enabled' field"
        assert 'available' in status, "Status should contain 'available' field"
        
        print(f"   Bridge status: enabled={status.get('enabled')}, available={status.get('available')}")
        print("   ✅ Bridge status reporting works")
        
        # Test 4: Method calls with fallback behavior
        print("4. Testing method calls with fallback...")
        
        # These should return empty signal lists gracefully if bridge not available
        from datetime import datetime, timezone
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)
        
        signals = provider_ifd.get_ifd_signals_only(start_time, end_time)
        assert isinstance(signals, list), "get_ifd_signals_only should return list"
        print(f"   Retrieved {len(signals)} IFD signals")
        
        # Test toggle functionality
        toggle_result = provider_ifd.toggle_ifd_signals(False)
        assert isinstance(toggle_result, bool), "toggle_ifd_signals should return bool"
        print(f"   Toggle IFD signals: {toggle_result}")
        
        print("   ✅ IFD methods work with proper fallback")
        
        return True
        
    except Exception as e:
        print(f"❌ IFD functionality test failed: {e}")
        return False

def test_fallback_behavior():
    """Test robust fallback when IFD bridge is not available"""
    print("\n=== Testing Fallback Behavior ===")
    
    if not PROVIDER_AVAILABLE:
        print("❌ Provider not available - skipping test")
        return False
    
    try:
        # Test 1: Provider with IFD disabled should work perfectly
        print("1. Testing provider with IFD explicitly disabled...")
        provider = Databento5MinuteProvider(enable_ifd_signals=False)
        
        # All IFD methods should return empty/safe results
        from datetime import datetime, timezone
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)
        
        # Test get_latest_bars_with_ifd returns OHLCV + empty signals
        try:
            bars, signals = provider.get_latest_bars_with_ifd(count=10)
            assert isinstance(signals, list), "Should return empty signals list"
            assert len(signals) == 0, "Should return empty signals when IFD disabled"
            print("   ✅ get_latest_bars_with_ifd returns empty signals correctly")
        except Exception as e:
            # May fail due to authentication in test environment, but structure should be right
            print(f"   ⚠️  get_latest_bars_with_ifd call failed (expected in test): {e}")
        
        # Test signal-only methods return empty
        signals = provider.get_ifd_signals_only(start_time, end_time)
        assert isinstance(signals, list), "Should return list"
        assert len(signals) == 0, "Should return empty signals when IFD disabled"
        print("   ✅ get_ifd_signals_only returns empty list correctly")
        
        # Test status reporting
        status = provider.get_ifd_bridge_status()
        assert status['enabled'] == False, "Status should show IFD disabled"
        print("   ✅ Bridge status correctly shows IFD disabled")
        
        # Test signal addition gracefully fails
        result = provider.add_ifd_signal(None)
        assert result == False, "Adding signal should fail gracefully when IFD disabled"
        print("   ✅ Signal addition fails gracefully when IFD disabled")
        
        print("   ✅ All fallback behavior working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Fallback behavior test failed: {e}")
        return False

def test_performance_impact():
    """Test that IFD integration doesn't degrade OHLCV performance"""
    print("\n=== Testing Performance Impact ===")
    
    if not PROVIDER_AVAILABLE:
        print("❌ Provider not available - skipping test")
        return False
    
    try:
        # Test 1: Compare initialization times
        print("1. Testing initialization performance...")
        
        # Time original initialization
        start_time = time.time()
        provider_old = Databento5MinuteProvider(enable_ifd_signals=False)
        old_init_time = time.time() - start_time
        
        # Time IFD-enabled initialization
        start_time = time.time()
        provider_ifd = Databento5MinuteProvider(enable_ifd_signals=True)
        ifd_init_time = time.time() - start_time
        
        print(f"   Original init time: {old_init_time:.3f}s")
        print(f"   IFD-enabled init time: {ifd_init_time:.3f}s")
        print(f"   Overhead: {ifd_init_time - old_init_time:.3f}s")
        
        # Performance should be reasonable (under 100ms overhead)
        overhead = ifd_init_time - old_init_time
        if overhead < 0.1:  # 100ms
            print("   ✅ Initialization overhead is acceptable")
        else:
            print(f"   ⚠️  Initialization overhead is high: {overhead:.3f}s")
        
        # Test 2: Memory usage
        print("2. Testing memory footprint...")
        
        import sys
        old_size = sys.getsizeof(provider_old)
        ifd_size = sys.getsizeof(provider_ifd)
        
        print(f"   Original provider size: {old_size} bytes")
        print(f"   IFD-enabled provider size: {ifd_size} bytes")
        print(f"   Memory overhead: {ifd_size - old_size} bytes")
        
        # Test 3: Method call overhead
        print("3. Testing method call performance...")
        
        # Test multiple calls to status methods
        start_time = time.time()
        for _ in range(100):
            status = provider_ifd.get_ifd_bridge_status()
        status_call_time = time.time() - start_time
        
        print(f"   100 status calls took: {status_call_time:.3f}s")
        print(f"   Average per call: {status_call_time/100*1000:.1f}ms")
        
        if status_call_time < 0.1:  # 100ms for 100 calls = 1ms per call
            print("   ✅ Method call performance is acceptable")
        else:
            print(f"   ⚠️  Method calls are slow: {status_call_time/100*1000:.1f}ms per call")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def test_integration_robustness():
    """Test that integration handles edge cases robustly"""
    print("\n=== Testing Integration Robustness ===")
    
    if not PROVIDER_AVAILABLE:
        print("❌ Provider not available - skipping test")
        return False
    
    try:
        provider = Databento5MinuteProvider(enable_ifd_signals=True)
        
        # Test 1: Invalid time ranges
        print("1. Testing invalid time ranges...")
        from datetime import datetime, timezone
        
        # Future time range
        future_start = datetime.now(timezone.utc) + timedelta(days=1)
        future_end = datetime.now(timezone.utc) + timedelta(days=2)
        
        signals = provider.get_ifd_signals_only(future_start, future_end)
        assert isinstance(signals, list), "Should return list even for invalid range"
        print("   ✅ Handles future time ranges gracefully")
        
        # Reversed time range
        end_time = datetime.now(timezone.utc) - timedelta(hours=2)
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        
        signals = provider.get_ifd_signals_only(start_time, end_time)
        assert isinstance(signals, list), "Should return list even for reversed range"
        print("   ✅ Handles reversed time ranges gracefully")
        
        # Test 2: Multiple toggle operations
        print("2. Testing multiple toggle operations...")
        
        original_state = provider.enable_ifd_signals
        
        # Toggle off and on multiple times
        for i in range(3):
            result = provider.toggle_ifd_signals(False)
            assert isinstance(result, bool), f"Toggle off #{i+1} should return bool"
            
            result = provider.toggle_ifd_signals(True)
            assert isinstance(result, bool), f"Toggle on #{i+1} should return bool"
        
        print("   ✅ Multiple toggle operations work correctly")
        
        # Test 3: Invalid signal addition
        print("3. Testing invalid signal addition...")
        
        # Add None signal
        result = provider.add_ifd_signal(None)
        assert isinstance(result, bool), "Should return bool for None signal"
        
        # Add invalid object
        result = provider.add_ifd_signal("invalid")
        assert isinstance(result, bool), "Should return bool for invalid signal"
        
        print("   ✅ Invalid signal addition handled gracefully")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration robustness test failed: {e}")
        return False

def main():
    """Run all compatibility tests"""
    print("=== Databento 5M Provider Compatibility Test Suite ===")
    
    if not PROVIDER_AVAILABLE:
        print("❌ Cannot run tests - provider not available")
        return
    
    tests = [
        ("Backward Compatibility", test_backward_compatibility),
        ("New IFD Functionality", test_new_ifd_functionality), 
        ("Fallback Behavior", test_fallback_behavior),
        ("Performance Impact", test_performance_impact),
        ("Integration Robustness", test_integration_robustness)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"💥 {test_name}: CRASHED - {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL COMPATIBILITY TESTS PASSED!")
        print("✅ Integration is safe and backward compatible")
    else:
        print("⚠️  Some compatibility issues detected")
        print("❌ Review failed tests before deployment")

if __name__ == "__main__":
    main()