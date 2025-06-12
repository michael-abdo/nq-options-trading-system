#!/usr/bin/env python3
"""
Test Barchart caching functionality
"""

import sys
import os
import time
from datetime import datetime

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'tasks', 'options_trading_system', 'data_ingestion'))

def test_barchart_caching():
    """Test the Barchart caching functionality"""
    
    print("🧪 Testing Barchart Caching System")
    print("=" * 50)
    
    try:
        from barchart_web_scraper.hybrid_scraper import HybridBarchartScraper
        from barchart_web_scraper.cache_manager import get_cache_manager
        
        # Clear any existing cache
        cache_manager = get_cache_manager()
        cache_manager.clear()
        print("🧹 Cleared existing cache")
        
        # Create scraper with caching enabled
        scraper = HybridBarchartScraper(headless=True, use_cache=True)
        
        print("\n1. Testing First API Call (should be fresh)")
        print("-" * 40)
        
        # Authenticate first
        if not scraper.authenticate("NQM25"):
            print("❌ Authentication failed")
            return False
        
        # First call - should hit API
        start_time = time.time()
        symbol = "MC4M25"
        futures_symbol = "NQM25"
        
        data1 = scraper.fetch_options_data(symbol, futures_symbol)
        first_call_time = time.time() - start_time
        
        if data1:
            contracts = data1.get('total', 0)
            print(f"✅ First call: {contracts} contracts in {first_call_time:.2f}s")
        else:
            print("❌ First call failed")
            return False
        
        print("\n2. Testing Second API Call (should use cache)")
        print("-" * 40)
        
        # Second call - should hit cache
        start_time = time.time()
        data2 = scraper.fetch_options_data(symbol, futures_symbol)
        second_call_time = time.time() - start_time
        
        if data2:
            contracts = data2.get('total', 0)
            print(f"✅ Second call: {contracts} contracts in {second_call_time:.2f}s")
            
            # Verify cache was used (should be much faster)
            if second_call_time < first_call_time / 2:
                print(f"🎯 Cache hit confirmed! {second_call_time:.2f}s vs {first_call_time:.2f}s")
            else:
                print(f"⚠️ Cache may not have been used. Times: {second_call_time:.2f}s vs {first_call_time:.2f}s")
        else:
            print("❌ Second call failed")
            return False
        
        print("\n3. Cache Statistics")
        print("-" * 40)
        scraper.print_cache_stats()
        
        # Test with different symbol (should miss cache)
        print("\n4. Testing Different Symbol (should miss cache)")
        print("-" * 40)
        
        start_time = time.time()
        data3 = scraper.fetch_options_data("MC5M25", futures_symbol)
        third_call_time = time.time() - start_time
        
        if data3:
            contracts = data3.get('total', 0)
            print(f"✅ Third call (different symbol): {contracts} contracts in {third_call_time:.2f}s")
        else:
            print("⚠️ Third call failed (expected if contract doesn't exist)")
        
        print("\n5. Final Cache Statistics")
        print("-" * 40)
        scraper.print_cache_stats()
        
        # Cleanup
        scraper.cleanup()
        
        print("\n✅ Barchart caching test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Caching test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_barchart_caching()
    sys.exit(0 if success else 1)