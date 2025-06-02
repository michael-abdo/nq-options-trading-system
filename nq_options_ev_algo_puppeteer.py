#!/usr/bin/env python3
"""
NQ Options Expected Value Trading System with Puppeteer Integration
Enhanced version that can use Chrome remote debugging for better scraping
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nq_options_ev_algo import *
from utils.puppeteer_scraper import run_puppeteer_scraper
from utils.stealth_scraper import run_stealth_scraper
from utils.chrome_connection_manager import get_chrome_page, close_chrome_page
from utils.manual_html_parser import extract_from_manual_html, find_latest_manual_html
from utils.feedback_loop_scraper import run_feedback_loop_scraper
import asyncio
import argparse

@log_function_call
def scrape_barchart_options_puppeteer(url: str, use_puppeteer: bool = True, remote_port: int = 9222, use_feedback_loop: bool = True, use_stealth: bool = True, use_manual_html: bool = False) -> Tuple[float, List[OptionsStrike]]:
    """Enhanced scraping with Puppeteer option and feedback loop"""
    log_section("Data Scraping (Puppeteer Enhanced)", logging.INFO)
    
    # If manual HTML parsing is requested, try that first
    if use_manual_html:
        data_logger.info("Manual HTML parsing mode enabled - checking for saved files...")
        try:
            manual_file = find_latest_manual_html()
            if manual_file:
                data_logger.info(f"Found manual HTML file: {manual_file}")
                result = extract_from_manual_html(manual_file)
                
                if result["success"]:
                    current_price = result["current_price"]
                    options_dict = result["options_data"]
                    
                    data_logger.info(f"Manual parser successfully extracted price: {current_price}")
                    data_logger.info(f"Manual parser found {len(options_dict)} option strikes")
                    
                    # Convert dict format to OptionsStrike objects
                    strikes = []
                    for opt in options_dict:
                        strike = OptionsStrike(
                            opt['strike'],
                            opt['call_volume'],
                            opt['call_oi'],
                            opt['call_premium'],
                            opt['put_volume'],
                            opt['put_oi'],
                            opt['put_premium']
                        )
                        strikes.append(strike)
                    
                    return current_price, strikes
                else:
                    data_logger.error(f"Manual parser failed: {result.get('error', 'Unknown error')}")
            else:
                data_logger.warning("No manually saved HTML files found in data/html_snapshots/")
                data_logger.info("Save a page manually using browser 'Save Page As' to use this feature")
        except Exception as e:
            data_logger.error(f"Manual HTML parsing error: {e}")
    
    if use_puppeteer:
        data_logger.info(f"Using Puppeteer scraper on port {remote_port}")
        if use_feedback_loop:
            data_logger.info("🔄 Feedback loop enabled - primary method with Shadow DOM support")
        if use_stealth:
            data_logger.info("🥷 Stealth mode enabled - bypassing bot detection")
        
        current_price, options_dict = None, None
        
        try:
            # Primary method: Use feedback loop scraper with Shadow DOM support
            if use_feedback_loop:
                async def run_feedback():
                    page = None
                    try:
                        page = await get_chrome_page(remote_port)
                        result = await run_feedback_loop_scraper(page, url)
                        return result
                    finally:
                        if page:
                            await close_chrome_page(page)
                
                result = asyncio.run(run_feedback())
                if result.get("success"):
                    current_price = result.get("current_price")
                    options_dict = result.get("options_data")
                    data_logger.info(f"Feedback loop scraper successfully extracted data")
                else:
                    data_logger.warning(f"Feedback loop scraper failed, trying stealth mode")
                    current_price, options_dict = None, None
            
            # Fallback to stealth scraper if feedback loop failed
            if (current_price is None or options_dict is None) and use_stealth:
                # Use advanced stealth scraper to bypass bot detection
                async def run_stealth():
                    page = None
                    try:
                        page = await get_chrome_page(remote_port)
                        result = await run_stealth_scraper(page, url)
                        return result
                    finally:
                        if page:
                            await close_chrome_page(page)
                
                result = asyncio.run(run_stealth())
                if result["success"]:
                    current_price = result["current_price"]
                    options_dict = result["options_data"]
                else:
                    data_logger.error(f"Stealth scraper failed: {result.get('error', 'Unknown error')}")
                    current_price, options_dict = None, None
            
            # Final fallback: Use regular Puppeteer scraper
            if current_price is None or options_dict is None:
                current_price, options_dict = run_puppeteer_scraper(url, remote_port, False)
            
            if current_price and options_dict:
                data_logger.info(f"Puppeteer successfully extracted price: {current_price}")
                data_logger.info(f"Puppeteer found {len(options_dict)} option strikes")
                
                # Convert dict format to OptionsStrike objects
                strikes = []
                for opt in options_dict:
                    strike = OptionsStrike(
                        opt['strike'],
                        opt['call_volume'],
                        opt['call_oi'],
                        opt['call_premium'],
                        opt['put_volume'],
                        opt['put_oi'],
                        opt['put_premium']
                    )
                    strikes.append(strike)
                
                return current_price, strikes
            else:
                data_logger.error("Puppeteer scraping failed - no data found")
                logger.error("!!! ERROR: Unable to extract options data")
                logger.error("Please check:")
                logger.error("1. Chrome is running with remote debugging")
                logger.error("2. You are logged into Barchart if required")
                logger.error("3. The page has fully loaded")
                if use_feedback_loop:
                    logger.error("4. Check data/debug/ for detailed analysis reports")
                raise Exception("Failed to extract options data with Puppeteer")
        except Exception as e:
            data_logger.error(f"Puppeteer error: {e}, trying manual HTML parsing")
    
    # Try manual HTML parsing from saved files
    data_logger.info("Attempting to use manually saved HTML files...")
    try:
        manual_file = find_latest_manual_html()
        if manual_file:
            data_logger.info(f"Found manual HTML file: {manual_file}")
            result = extract_from_manual_html(manual_file)
            
            if result["success"]:
                current_price = result["current_price"]
                options_dict = result["options_data"]
                
                data_logger.info(f"Manual parser successfully extracted price: {current_price}")
                data_logger.info(f"Manual parser found {len(options_dict)} option strikes")
                
                # Convert dict format to OptionsStrike objects
                strikes = []
                for opt in options_dict:
                    strike = OptionsStrike(
                        opt['strike'],
                        opt['call_volume'],
                        opt['call_oi'],
                        opt['call_premium'],
                        opt['put_volume'],
                        opt['put_oi'],
                        opt['put_premium']
                    )
                    strikes.append(strike)
                
                return current_price, strikes
            else:
                data_logger.error(f"Manual parser failed: {result.get('error', 'Unknown error')}")
        else:
            data_logger.warning("No manually saved HTML files found in data/html_snapshots/")
    except Exception as e:
        data_logger.error(f"Manual HTML parsing error: {e}")
    
    # Fall back to original BeautifulSoup scraper
    data_logger.info("Falling back to original BeautifulSoup scraper")
    return scrape_barchart_options(url)


def main():
    """Main execution function with Puppeteer support"""
    parser = argparse.ArgumentParser(description='NQ Options EV Trading System')
    parser.add_argument('--puppeteer', action='store_true', help='Use Puppeteer for scraping')
    parser.add_argument('--port', type=int, default=9222, help='Chrome remote debugging port (default: 9222)')
    parser.add_argument('--headless', action='store_true', help='Run Chrome in headless mode')
    parser.add_argument('--week', type=int, default=1, choices=[1, 2], help='Which week expiration to use (default: 1)')
    parser.add_argument('--feedback-loop', action='store_true', help='Enable feedback loop for auto-improving scraping')
    parser.add_argument('--no-stealth', action='store_true', help='Disable stealth mode (may trigger bot detection)')
    parser.add_argument('--manual-html', action='store_true', help='Use manually saved HTML files instead of live scraping')
    args = parser.parse_args()
    
    try:
        log_section("STARTING NQ OPTIONS EV SYSTEM (PUPPETEER ENHANCED)")
        
        if args.puppeteer:
            logger.info("Puppeteer mode enabled")
            logger.info(f"Chrome remote debugging port: {args.port}")
            logger.info(f"Headless mode: {args.headless}")
            if args.feedback_loop:
                logger.info("Feedback loop enabled - will auto-improve selectors if scraping fails")
        
        # Generate URL for current contract
        url = get_current_contract_url(week=args.week)
        
        if args.week == 2:
            logger.info("Using Week 2 expiration as requested")
        
        # Scrape data with Puppeteer option
        logger.info("Scraping options data...")
        current_price, strikes = scrape_barchart_options_puppeteer(
            url, 
            use_puppeteer=args.puppeteer,
            remote_port=args.port,
            use_feedback_loop=args.feedback_loop,
            use_stealth=not args.no_stealth,
            use_manual_html=args.manual_html
        )
        
        # Calculate EV for all combinations
        logger.info("Calculating EV for all TP/SL combinations...")
        all_setups = calculate_ev_for_all_combinations(current_price, strikes)
        
        # Filter quality setups
        quality_setups = filter_quality_setups(all_setups)
        logger.info(f"Found {len(quality_setups)} quality setups")
        
        # Generate report
        report = generate_report(current_price, quality_setups)
        print(report)
        
        # Save report to file
        os.makedirs('reports', exist_ok=True)
        filename = f"reports/nq_ev_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(filename, 'w') as f:
                f.write(report)
                if args.puppeteer:
                    f.write(f"\n\nData source: Puppeteer scraping on port {args.port}")
                    if args.feedback_loop:
                        f.write(" (with feedback loop enabled)")
                else:
                    f.write("\n\nData source: BeautifulSoup scraping (sample data)")
            logger.info(f"Report saved to {filename}")
        except Exception as e:
            logger.error(f"!!! ERROR saving report: {e}")
            logger.exception("Full traceback:")
        
        log_section("SYSTEM COMPLETED SUCCESSFULLY")
        
        # Return best opportunities for programmatic use
        return quality_setups[:5] if quality_setups else []
        
    except Exception as e:
        logger.error(f"!!! ERROR in main execution: {type(e).__name__}: {str(e)}")
        
        if "Failed to extract options data" in str(e):
            print("\n" + "="*80)
            print("ERROR: No options data could be extracted from Barchart")
            print("="*80)
            print("\nTroubleshooting steps:")
            print("1. Ensure Chrome is running with: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
            print("2. Navigate to Barchart and log in if required")
            print("3. Check if reCAPTCHA needs to be solved")
            print("4. Try refreshing the page manually in Chrome")
            print("5. Verify the options page loads correctly")
            print("\nExiting...")
        else:
            logger.exception("Full traceback:")
        
        log_section("SYSTEM FAILED", logging.ERROR)
        sys.exit(1)


if __name__ == "__main__":
    main()