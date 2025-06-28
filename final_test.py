#!/usr/bin/env python3
"""
Final test - the real issue
"""

import logging
import sys

sys.path.append('/Users/Mike/trading/algos/EOD/tasks/options_trading_system/data_ingestion/barchart_web_scraper')

from solution import BarchartWebScraper
from barchart_api_client import BarchartAPIClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use existing hybrid scraper logic
from hybrid_scraper import HybridBarchartScraper

scraper = HybridBarchartScraper(headless=True)

# This will use Selenium to get cookies
logger.info("Authenticating...")
if scraper.authenticate("NQU25"):
    logger.info("✅ Authentication successful")
    
    # Now test with the symbol you're viewing
    logger.info("\nTesting MM9M25...")
    data = scraper.fetch_options_data("MM9M25", "NQU25")
    
    if data:
        logger.info(f"Response: count={data.get('count')}, total={data.get('total')}")
        if 'data' in data:
            logger.info(f"Data type: {type(data['data'])}")
            if isinstance(data['data'], dict):
                logger.info(f"Data keys: {list(data['data'].keys())}")
            elif isinstance(data['data'], list):
                logger.info(f"Data is list with {len(data['data'])} items")
    
    # Also try the single digit format
    logger.info("\nTesting MM9M5...")
    data2 = scraper.fetch_options_data("MM9M5", "NQU25")
    
    if data2:
        logger.info(f"Response: count={data2.get('count')}, total={data2.get('total')}")
else:
    logger.error("Authentication failed")