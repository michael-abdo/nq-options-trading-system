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
import argparse

@log_function_call
def scrape_barchart_options_puppeteer(url: str, use_puppeteer: bool = True, remote_port: int = 9222) -> Tuple[float, List[OptionsStrike]]:
    """Enhanced scraping with Puppeteer option"""
    log_section("Data Scraping (Puppeteer Enhanced)", logging.INFO)
    
    if use_puppeteer:
        data_logger.info(f"Using Puppeteer scraper on port {remote_port}")
        try:
            # Use Puppeteer scraper
            current_price, options_dict = run_puppeteer_scraper(url, remote_port)
            
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
                raise Exception("Failed to extract options data with Puppeteer")
        except Exception as e:
            data_logger.error(f"Puppeteer error: {e}, falling back to BeautifulSoup")
    
    # Fall back to original BeautifulSoup scraper
    return scrape_barchart_options(url)


def main():
    """Main execution function with Puppeteer support"""
    parser = argparse.ArgumentParser(description='NQ Options EV Trading System')
    parser.add_argument('--puppeteer', action='store_true', help='Use Puppeteer for scraping')
    parser.add_argument('--port', type=int, default=9222, help='Chrome remote debugging port (default: 9222)')
    parser.add_argument('--headless', action='store_true', help='Run Chrome in headless mode')
    args = parser.parse_args()
    
    try:
        log_section("STARTING NQ OPTIONS EV SYSTEM (PUPPETEER ENHANCED)")
        
        if args.puppeteer:
            logger.info("Puppeteer mode enabled")
            logger.info(f"Chrome remote debugging port: {args.port}")
            logger.info(f"Headless mode: {args.headless}")
        
        # Generate URL for current contract
        url = get_current_contract_url()
        
        # Scrape data with Puppeteer option
        logger.info("Scraping options data...")
        current_price, strikes = scrape_barchart_options_puppeteer(
            url, 
            use_puppeteer=args.puppeteer,
            remote_port=args.port
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