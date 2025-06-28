#!/usr/bin/env python3
"""
Test Selenium-based authentication vs manual cookie extraction
"""

import logging
import json
from datetime import datetime
import os
import sys

# Add the task directory to path
sys.path.append('/Users/Mike/trading/algos/EOD/tasks/options_trading_system/data_ingestion/barchart_web_scraper')

from solution import BarchartWebScraper
from barchart_api_client import BarchartAPIClient

def test_selenium_authentication():
    """Test the original Selenium-based authentication approach"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info("🔬 TESTING SELENIUM-BASED AUTHENTICATION (original working method)")
    
    try:
        # Step 1: Use Selenium to get fresh cookies (original method)
        logger.info("🌐 Initializing Selenium WebDriver...")
        web_scraper = BarchartWebScraper(headless=True)
        driver = web_scraper.setup_driver()
        # CRITICAL BUG: setup_driver() returns a driver but doesn't assign it to self.driver
        web_scraper.driver = driver  # THIS IS THE FIX
        
        # Let's visit an options page directly to get better cookies
        auth_url = "https://www.barchart.com/futures/quotes/NQU25/options/MM9M25?futuresOptionsView=merged"
        logger.info(f"🔐 Visiting {auth_url} for authentication...")
        
        driver.set_page_load_timeout(10)
        try:
            driver.get(auth_url)
        except:
            logger.info("Page load timed out, continuing with cookies...")
        
        # Wait for cookies to be set
        import time
        time.sleep(3)
        
        # Let's debug why we're getting 0 cookies
        logger.info("🔍 Debugging cookie extraction...")
        
        # Check page title and URL
        logger.info(f"Current URL: {driver.current_url}")
        logger.info(f"Page title: {driver.title}")
        
        # Check if we're on a CloudFront error page
        page_source_snippet = driver.page_source[:500] if driver.page_source else "No page source"
        logger.info(f"Page source snippet: {page_source_snippet}")
        
        # Try to get ALL cookies from driver
        all_cookies = driver.get_cookies()
        logger.info(f"Raw cookies from driver: {len(all_cookies)} cookies")
        
        # Extract cookies using Selenium (original method)
        selenium_cookies = web_scraper.get_cookies_from_driver()
        logger.info(f"✅ Selenium extracted {len(selenium_cookies)} cookies")
        
        # Check for essential cookies
        essential_cookies = ['laravel_session', 'XSRF-TOKEN', 'laravel_token']
        found_cookies = [c for c in essential_cookies if c in selenium_cookies]
        logger.info(f"Essential cookies found: {found_cookies}")
        
        # Close browser
        driver.quit()
        
        # Step 2: Test API call with Selenium-extracted cookies
        logger.info("📡 Testing API call with Selenium-extracted cookies...")
        api_client = BarchartAPIClient()
        api_client.set_cookies(selenium_cookies)
        
        # Let's test with EXACT parameters from the working June 8th request
        # Maybe the issue is the futures_symbol parameter or the referer
        test_symbols = [
            ("MC7M5", "NQM25"),   # EXACT format from successful response
            ("MC7M5", "NQU25"),   # Try different futures month
            ("MC4M5", "NQU25"),   # Current date EOD option
            ("NQM25", "NQM25"),   # Try futures symbol itself
        ]
        
        for symbol, futures_symbol in test_symbols:
            logger.info(f"\n📊 Testing {symbol} (futures: {futures_symbol})...")
            try:
                data = api_client.get_options_data(symbol, futures_symbol)
                
                # Debug the ENTIRE response structure
                logger.info(f"API Response: count={data.get('count', 'N/A')}, total={data.get('total', 'N/A')}")
                logger.info(f"Response type: {type(data)}")
                logger.info(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                # Check the data structure in detail
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key == 'data':
                            logger.info(f"  {key}: {type(value)}")
                            if isinstance(value, list):
                                logger.info(f"    Data is a list with {len(value)} items")
                                if len(value) > 0:
                                    logger.info(f"    First item type: {type(value[0])}")
                                    logger.info(f"    First item: {value[0]}")
                            elif isinstance(value, dict):
                                logger.info(f"    Data is a dict with keys: {list(value.keys())}")
                        elif key != 'meta':
                            logger.info(f"  {key}: {type(value)} = {value}")
                
                if data and data.get('total', 0) > 0:
                    logger.info(f"🎉 SUCCESS! Retrieved {data.get('total', 0)} contracts!")
                    
                    # Save the data
                    saved_path = api_client.save_api_response(data, symbol)
                    logger.info(f"💾 Data saved to: {saved_path}")
                    return True
                else:
                    logger.warning(f"⚠️  No data returned for {symbol}")
                    
            except Exception as e:
                logger.error(f"❌ API call failed for {symbol}: {e}")
        
        logger.warning("⚠️  All symbols returned no data")
        return False
            
    except Exception as e:
        logger.error(f"❌ Selenium authentication test failed: {e}")
        if 'driver' in locals():
            driver.quit()
        return False

if __name__ == "__main__":
    success = test_selenium_authentication()
    if success:
        print("\n🎯 CONCLUSION: Selenium-based authentication works!")
        print("ROOT CAUSE: Manual cookie extraction vs Selenium cookie extraction difference")
    else:
        print("\n🔍 CONCLUSION: Even Selenium authentication fails now")
        print("ROOT CAUSE: Deeper API access change since June 8th")