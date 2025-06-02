#!/usr/bin/env python3
"""
Test to validate scraped data from Barchart
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from nq_options_ev_algo import scrape_barchart_options, get_current_contract_url, OptionsStrike

def test_data_validation():
    """Test that scraped data meets expected format"""
    print("=== Testing Barchart Data Scraping ===")
    
    # Get URL
    url = get_current_contract_url()
    print(f"Generated URL: {url}")
    
    # Scrape data
    try:
        current_price, strikes = scrape_barchart_options(url)
        
        print(f"\nResults:")
        print(f"Current Price: {current_price}")
        print(f"Number of Strikes: {len(strikes)}")
        
        # Validate current price
        assert isinstance(current_price, float), "Current price should be a float"
        assert 15000 < current_price < 30000, f"Current price {current_price} seems unrealistic for NQ"
        
        # Validate strikes
        assert len(strikes) > 0, "Should have at least one strike"
        
        print("\nStrike Data:")
        print("Strike | Call Vol | Call OI | Call $ | Put Vol | Put OI | Put $")
        print("-" * 70)
        
        for strike in strikes:
            # Validate strike object
            assert isinstance(strike, OptionsStrike), "Strike should be OptionsStrike object"
            assert isinstance(strike.price, (int, float)), "Strike price should be numeric"
            assert isinstance(strike.call_volume, int), "Call volume should be int"
            assert isinstance(strike.call_oi, int), "Call OI should be int"
            assert isinstance(strike.call_premium, (int, float)), "Call premium should be numeric"
            assert isinstance(strike.put_volume, int), "Put volume should be int"
            assert isinstance(strike.put_oi, int), "Put OI should be int"
            assert isinstance(strike.put_premium, (int, float)), "Put premium should be numeric"
            
            # Validate reasonable values
            assert strike.price > 0, "Strike price should be positive"
            assert strike.call_volume >= 0, "Call volume should be non-negative"
            assert strike.call_oi >= 0, "Call OI should be non-negative"
            assert strike.call_premium >= 0, "Call premium should be non-negative"
            assert strike.put_volume >= 0, "Put volume should be non-negative"
            assert strike.put_oi >= 0, "Put OI should be non-negative"
            assert strike.put_premium >= 0, "Put premium should be non-negative"
            
            print(f"{strike.price:6.0f} | {strike.call_volume:8} | {strike.call_oi:7} | "
                  f"{strike.call_premium:6.2f} | {strike.put_volume:7} | {strike.put_oi:6} | "
                  f"{strike.put_premium:5.2f}")
        
        # Check if we're using sample data
        if len(strikes) == 7 and strikes[0].price == 21200:
            print("\n⚠️  WARNING: Using sample data, not live Barchart data")
            print("This indicates that the scraper couldn't find real options data")
            print("Possible reasons:")
            print("1. Barchart uses dynamic loading (Angular/React)")
            print("2. Anti-bot protection (reCAPTCHA/Cloudflare)")
            print("3. Page structure has changed")
            print("4. Authentication required")
        else:
            print("\n✅ Successfully scraped live data from Barchart")
        
        # Validate strike spacing
        if len(strikes) > 1:
            spacings = [strikes[i+1].price - strikes[i].price for i in range(len(strikes)-1)]
            print(f"\nStrike spacings: {spacings}")
            # NQ typically has 25 or 50 point spacing
            common_spacing = max(set(spacings), key=spacings.count)
            assert common_spacing in [25, 50], f"Unexpected strike spacing: {common_spacing}"
        
        print("\n✅ All validations passed")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_data_validation()
    sys.exit(0 if success else 1)