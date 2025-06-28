#!/usr/bin/env python3
"""
Hybrid Barchart Scraper - Uses Selenium for auth, then API for data
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

from solution import BarchartWebScraper
from barchart_api_client import BarchartAPIClient
from symbol_generator import BarchartSymbolGenerator

class HybridBarchartScraper:
    """
    Combines Selenium for authentication with direct API calls for speed
    """
    
    def __init__(self, headless: bool = True):
        self.logger = logging.getLogger(__name__)
        self.headless = headless
        self.web_scraper = None
        self.api_client = None
        self.cookies = None
        self.symbol_generator = BarchartSymbolGenerator()
        
    def authenticate(self, futures_symbol: str = "NQM25") -> bool:
        """
        Use Selenium to visit Barchart and get authentication cookies
        
        Args:
            futures_symbol: Futures symbol to visit (for getting cookies)
            
        Returns:
            True if authentication successful
        """
        try:
            self.logger.info("Starting authentication via Selenium...")
            
            # Initialize web scraper
            self.web_scraper = BarchartWebScraper(headless=self.headless)
            self.web_scraper.driver = self.web_scraper.setup_driver()
            
            # Visit a Barchart page to get cookies
            # We'll use the main futures page which should be lighter
            auth_url = f"https://www.barchart.com/futures/quotes/{futures_symbol}"
            
            self.logger.info(f"Visiting {auth_url} for authentication...")
            
            # Set page load timeout
            self.web_scraper.driver.set_page_load_timeout(10)
            
            try:
                self.web_scraper.driver.get(auth_url)
            except:
                # Page load timeout is OK - we just need cookies
                self.logger.info("Page load timed out, but continuing with cookies")
            
            # Wait a bit for cookies to be set
            import time
            time.sleep(3)
            
            # Extract cookies
            self.cookies = self.web_scraper.get_cookies_from_driver()
            
            # Check for essential cookies
            essential_cookies = ['laravel_session', 'XSRF-TOKEN', 'laravel_token']
            found_cookies = [c for c in essential_cookies if c in self.cookies]
            
            self.logger.info(f"Found {len(found_cookies)}/{len(essential_cookies)} essential cookies")
            
            # Close the browser - we don't need it anymore
            if self.web_scraper.driver:
                self.web_scraper.driver.quit()
                
            return len(found_cookies) > 0
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
    
    def fetch_options_data(self, symbol: str, futures_symbol: str = "NQM25", calculate_metrics: bool = True) -> Dict[str, Any]:
        """
        Fetch options data using API with authenticated cookies
        
        Args:
            symbol: Options symbol (e.g., "MC7M25")
            futures_symbol: Underlying futures symbol
            calculate_metrics: Whether to calculate and save metrics
            
        Returns:
            Options data from API with optional metrics
        """
        if not self.cookies:
            self.logger.error("No cookies available. Run authenticate() first.")
            return None
            
        try:
            # Initialize API client
            self.api_client = BarchartAPIClient()
            
            # Set cookies
            self.api_client.set_cookies(self.cookies)
            
            # Fetch data
            self.logger.info(f"Fetching options data for {symbol} via API...")
            data = self.api_client.get_options_data(symbol, futures_symbol)
            
            # Save the data to file
            if data and data.get('total', 0) > 0:
                saved_path = self.api_client.save_api_response(data, symbol)
                self.logger.info(f"✅ Saved {data.get('total', 0)} contracts to {saved_path}")
                
                # Calculate and save metrics if requested
                if calculate_metrics:
                    try:
                        import sys
                        import os
                        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
                        from options_metrics_calculator import OptionsMetricsCalculator
                        
                        calculator = OptionsMetricsCalculator()
                        metrics, metrics_file = calculator.calculate_and_save_metrics(data, symbol)
                        calculator.print_metrics_summary(metrics)
                        
                        # Add metrics to return data
                        data['_metrics'] = metrics
                        data['_metrics_file'] = metrics_file
                        
                    except Exception as me:
                        self.logger.warning(f"Metrics calculation failed: {me}")
            
            return data
            
        except Exception as e:
            self.logger.error(f"API call failed: {e}")
            return None
    
    def fetch_eod_options(self, futures_symbol: str = "NQM25") -> Dict[str, Any]:
        """
        Fetch today's EOD options
        
        Args:
            futures_symbol: Underlying futures symbol
            
        Returns:
            EOD options data
        """
        # Get today's EOD symbol
        eod_symbol = self.symbol_generator.get_eod_contract_symbol()
        
        self.logger.info(f"Fetching EOD options: {eod_symbol}")
        return self.fetch_options_data(eod_symbol, futures_symbol)
    
    def get_eod_contract_symbol(self, option_type: str = "weekly", year_format: str = "2digit") -> str:
        """Get EOD contract symbol - convenience method"""
        return self.symbol_generator.get_eod_contract_symbol(option_type=option_type, year_format=year_format)


def main():
    """Test the hybrid scraper"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hybrid Barchart Scraper')
    parser.add_argument('--symbol', help='Options symbol (default: today\'s EOD)')
    parser.add_argument('--futures', default='NQM25', help='Futures symbol')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--save', action='store_true', help='Save data to file')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create scraper
    scraper = HybridBarchartScraper(headless=args.headless)
    
    # Authenticate
    print("🔐 Authenticating with Barchart...")
    if not scraper.authenticate(args.futures):
        print("❌ Authentication failed!")
        return 1
    
    print("✅ Authentication successful!")
    
    # Fetch data
    if args.symbol:
        print(f"\n📊 Fetching data for {args.symbol}...")
        data = scraper.fetch_options_data(args.symbol, args.futures)
    else:
        print("\n📊 Fetching today's EOD options...")
        data = scraper.fetch_eod_options(args.futures)
    
    if data:
        print(f"✅ Success! Retrieved {data.get('total', 0)} contracts")
        
        # Show sample data
        if 'data' in data and 'Call' in data['data'] and data['data']['Call']:
            first_call = data['data']['Call'][0]
            print(f"\nSample contract:")
            print(f"  Symbol: {first_call.get('symbol')}")
            print(f"  Strike: {first_call.get('strike')}")
            print(f"  Last: {first_call.get('lastPrice')}")
        
        if args.save:
            # Save the data using organized structure
            import os
            date_str = datetime.now().strftime('%Y%m%d')
            output_dir = f"outputs/{date_str}/api_data"
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"barchart_api_data_{timestamp}.json"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n💾 Data saved to {filepath}")
    else:
        print("❌ Failed to fetch data")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())