#!/usr/bin/env python3
"""
Test with EXACT parameters from the HTML page
"""

import logging
import json
import sys

sys.path.append('/Users/Mike/trading/algos/EOD/tasks/options_trading_system/data_ingestion/barchart_web_scraper')

from solution import BarchartWebScraper
from barchart_api_client import BarchartAPIClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get cookies via Selenium first
web_scraper = BarchartWebScraper(headless=True)
driver = web_scraper.setup_driver()
web_scraper.driver = driver

# Visit the actual page that's showing data
auth_url = "https://www.barchart.com/futures/quotes/NQU25/options/MM9M25?futuresOptionsView=merged"
logger.info(f"Visiting {auth_url}...")

driver.get(auth_url)
import time
time.sleep(5)  # Wait longer

cookies = web_scraper.get_cookies_from_driver()
logger.info(f"Got {len(cookies)} cookies")

driver.quit()

# Now test the API
api_client = BarchartAPIClient()
api_client.set_cookies(cookies)

# Test different symbol formats for MM9M25
test_cases = [
    # Symbol from URL vs API format
    ("MM9M25", "NQU25", "URL format"),
    ("MM9M5", "NQU25", "Single digit year"),
    ("MM9U5", "NQU25", "Single digit month+year"),
    ("OQU25|19400C", "NQU25", "Full option symbol format"),
    ("NQU25", "NQU25", "Just futures symbol"),
]

for symbol, futures, desc in test_cases:
    logger.info(f"\nTesting {desc}: {symbol}")
    try:
        # Let's also try without raw=1
        params = {
            'symbol': symbol,
            'list': 'futures.options',
            'fields': 'strike,openPrice,highPrice,lowPrice,lastPrice,priceChange,bidPrice,askPrice,volume,openInterest,premium,tradeTime,longSymbol,optionType,symbol',
            'meta': 'field.shortName,field.description,field.type',
            'groupBy': 'optionType',
            'orderBy': 'strike',
            'orderDir': 'asc'
        }
        
        # Make direct request without raw=1
        import requests
        
        # Add XSRF token header
        headers = api_client.headers.copy()
        xsrf_token = None
        for cookie in api_client.session.cookies:
            if cookie.name == 'XSRF-TOKEN':
                xsrf_token = cookie.value
                break
        
        if xsrf_token:
            import urllib.parse
            headers['X-XSRF-TOKEN'] = urllib.parse.unquote(xsrf_token)
            
        response = api_client.session.get(
            f"{api_client.base_url}/quotes/get",
            params=params,
            headers=headers
        )
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response text: {response.text[:500]}")
        
        data = None
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Response: count={data.get('count')}, total={data.get('total')}")
        
        if data and 'data' in data and isinstance(data['data'], dict):
            logger.info(f"✅ Data is dict with keys: {list(data['data'].keys())}")
            for key, value in data['data'].items():
                if isinstance(value, list):
                    logger.info(f"  {key}: {len(value)} items")
                    if len(value) > 0:
                        logger.info(f"    First {key}: {value[0].get('symbol', 'N/A')}")
        elif data and 'data' in data and isinstance(data['data'], list):
            logger.info(f"❌ Data is list with {len(data['data'])} items")
            
    except Exception as e:
        logger.error(f"Error: {e}")