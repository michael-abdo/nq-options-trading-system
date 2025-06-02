#!/usr/bin/env python3
"""
Enhanced Feedback Loop Runner
Runs the enhanced feedback loop system with strike element detection
"""

import asyncio
import logging
from utils.feedback_loop_scraper import run_feedback_loop_scraper
from pyppeteer import launch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("🚀 ENHANCED closed feedback loop with strike element detection")
    logger.info("🎯 Success criteria: Extract live options data using found strike elements")
    
    # Launch browser
    browser = await launch({
        'headless': False,
        'args': ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    })
    
    page = await browser.newPage()
    await page.setViewport({'width': 1920, 'height': 1080})
    
    # Set user agent to avoid bot detection
    await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    try:
        # Run the enhanced feedback loop system
        url = 'https://www.barchart.com/futures/quotes/NQM25/options/MC6M25'
        results = await run_feedback_loop_scraper(page, url)
        
        if results['success']:
            logger.info("🎉 SUCCESS! Enhanced feedback loop achieved its goal")
            price = results.get('current_price', 'N/A')
            options_count = len(results.get('options_data', []))
            logger.info(f"✅ Price: {price}")
            logger.info(f"✅ Options: {options_count} strikes")
            
            # Show sample of extracted options
            options = results.get('options_data', [])
            if options:
                logger.info("📊 Sample extracted options:")
                for i, opt in enumerate(options[:3]):
                    call_prem = opt.get('call_premium', 0)
                    put_prem = opt.get('put_premium', 0)
                    strike = opt.get('strike', 0)
                    logger.info(f"  Strike {strike}: Call ${call_prem:.2f}, Put ${put_prem:.2f}")
        else:
            logger.info("🔄 Enhanced feedback loop completed but did not achieve success")
            logger.info("📊 Analysis results available in data/debug/")
    
    except Exception as e:
        logger.error(f"❌ Error in enhanced feedback loop: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())