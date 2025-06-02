#!/usr/bin/env python3
"""
Test script for the feedback loop scraper
Integrates with existing Puppeteer infrastructure
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.chrome_connection_manager import get_chrome_page, close_chrome_page
from utils.feedback_loop_scraper import run_feedback_loop_scraper
from utils.logging_config import setup_logging
from nq_options_ev_algo import get_current_contract_url

async def test_feedback_loop(url: str, remote_port: int = 9222):
    """Test the feedback loop scraper with a Barchart URL"""
    page = None
    
    try:
        # Setup logging
        log_dir, session_id = setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("=" * 80)
        logger.info("STARTING FEEDBACK LOOP SCRAPER TEST")
        logger.info("=" * 80)
        
        # Get a page from Chrome
        logger.info(f"Connecting to Chrome on port {remote_port}")
        page = await get_chrome_page(remote_port)
        
        # Navigate to the URL
        logger.info(f"Navigating to {url}")
        await page.goto(url, waitUntil='networkidle2', timeout=30000)
        
        # Wait for initial page load
        await asyncio.sleep(3)
        
        # Check for reCAPTCHA
        recaptcha_present = await page.evaluate('''() => {
            return document.querySelector('iframe[src*="recaptcha"]') !== null;
        }''')
        
        if recaptcha_present:
            logger.warning("reCAPTCHA detected!")
            logger.info("Please solve the CAPTCHA manually in Chrome")
            logger.info("Waiting 60 seconds for manual intervention...")
            await asyncio.sleep(60)
        
        # Run the feedback loop scraper
        logger.info("\nStarting feedback loop scraper...")
        results = await run_feedback_loop_scraper(page, debug_dir="data/debug")
        
        # Print results
        if results["success"]:
            logger.info("\n" + "=" * 60)
            logger.info("FEEDBACK LOOP SUCCESS!")
            logger.info("=" * 60)
            logger.info(f"Current Price: ${results['current_price']:,.2f}")
            logger.info(f"Options Found: {len(results['options_data'])} strikes")
            
            if results['options_data']:
                logger.info("\nSample Options Data (first 5 strikes):")
                for i, opt in enumerate(results['options_data'][:5]):
                    logger.info(f"  Strike {opt['strike']:,.0f}: "
                              f"Call ${opt['call_premium']:.2f}, "
                              f"Put ${opt['put_premium']:.2f}")
            
            # Save successful configuration
            logger.info("\nSuccessful selectors saved for future use:")
            for data_type, selector in results.get("successful_selectors", {}).items():
                logger.info(f"  {data_type}: {selector['method']} - {selector['selector']}")
        else:
            logger.error("\n" + "=" * 60)
            logger.error("FEEDBACK LOOP FAILED")
            logger.error("=" * 60)
            logger.error("Could not extract required data after all attempts")
            logger.error("Check the debug directory for detailed analysis")
        
        return results
        
    except Exception as e:
        logging.error(f"Error in test_feedback_loop: {e}")
        logging.exception("Full traceback:")
        return {"success": False, "error": str(e)}
    
    finally:
        if page:
            await close_chrome_page(page)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Feedback Loop Scraper')
    parser.add_argument('--url', type=str, help='Specific URL to test')
    parser.add_argument('--port', type=int, default=9222, help='Chrome remote debugging port')
    parser.add_argument('--week', type=int, default=1, choices=[1, 2], help='Which week expiration to use')
    args = parser.parse_args()
    
    # Get URL
    if args.url:
        url = args.url
    else:
        url = get_current_contract_url(week=args.week)
    
    print(f"Testing feedback loop scraper with URL: {url}")
    print(f"Chrome port: {args.port}")
    print(f"Debug files will be saved to: data/debug/")
    print("-" * 60)
    
    # Run the test
    results = asyncio.run(test_feedback_loop(url, args.port))
    
    # Exit with appropriate code
    sys.exit(0 if results.get("success") else 1)


if __name__ == "__main__":
    main()