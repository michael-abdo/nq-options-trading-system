import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import pandas as pd
from bs4 import BeautifulSoup

@dataclass
class OptionsContract:
    strike: float
    call_last: Optional[float]
    call_change: Optional[float]
    call_bid: Optional[float] 
    call_ask: Optional[float]
    call_volume: Optional[int]
    call_open_interest: Optional[int]
    call_implied_volatility: Optional[float]
    put_last: Optional[float]
    put_change: Optional[float]
    put_bid: Optional[float]
    put_ask: Optional[float]
    put_volume: Optional[int]
    put_open_interest: Optional[int]
    put_implied_volatility: Optional[float]
    expiration_date: str
    underlying_price: Optional[float]
    source: str  # 'web_scrape' or 'api'
    timestamp: datetime

@dataclass
class OptionsChainData:
    underlying_symbol: str
    expiration_date: str
    underlying_price: Optional[float]
    contracts: List[OptionsContract]
    source: str
    timestamp: datetime
    total_contracts: int

class BarchartWebScraper:
    """
    EXPERIMENTAL FRAMEWORK: Web scraping barchart.com options data
    for comparison with API data to validate data consistency
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.wait_time = 10  # seconds
        self.comparison_results = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def setup_driver(self) -> webdriver.Chrome:
        """
        Setup Chrome WebDriver with appropriate options
        """
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
            
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Speed up loading
        
        # User agent to avoid detection
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.implicitly_wait(10)
            return driver
        except Exception as e:
            self.logger.error(f"Failed to setup Chrome driver: {e}")
            raise
    
    def scrape_barchart_options(self, url: str) -> OptionsChainData:
        """
        CORE SCRAPING FUNCTION: Extract options data from barchart.com
        
        Args:
            url: Barchart options page URL
            
        Returns:
            OptionsChainData object with scraped information
        """
        
        self.logger.info(f"Starting to scrape: {url}")
        
        try:
            # Setup driver
            self.driver = self.setup_driver()
            
            # Navigate to page
            self.driver.get(url)
            self.logger.info("Page loaded, waiting for content...")
            
            # Wait for the page to load (10 seconds as requested)
            time.sleep(self.wait_time)
            
            # Wait for options table to be present
            wait = WebDriverWait(self.driver, 30)
            
            # Look for the options table - barchart uses different selectors
            table_selectors = [
                "table.datatable",
                ".options-table",
                "[data-ng-show*='options']",
                "table[class*='option']",
                ".bc-table"
            ]
            
            options_table = None
            for selector in table_selectors:
                try:
                    options_table = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    self.logger.info(f"Found options table with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not options_table:
                # Fallback: get page source and parse manually
                self.logger.warning("Options table not found with standard selectors, parsing HTML manually")
                return self._parse_page_source_fallback()
            
            # Extract underlying symbol and price
            underlying_info = self._extract_underlying_info()
            
            # Extract options contracts
            contracts = self._extract_options_contracts(options_table)
            
            # Create result
            options_data = OptionsChainData(
                underlying_symbol=underlying_info['symbol'],
                expiration_date=underlying_info['expiration'],
                underlying_price=underlying_info['price'],
                contracts=contracts,
                source='web_scrape',
                timestamp=datetime.now(),
                total_contracts=len(contracts)
            )
            
            self.logger.info(f"Successfully scraped {len(contracts)} options contracts")
            return options_data
            
        except Exception as e:
            self.logger.error(f"Error scraping barchart options: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
    
    def _parse_page_source_fallback(self) -> OptionsChainData:
        """
        Fallback method to parse page source when table selectors fail
        """
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Look for any table containing options data
        tables = soup.find_all('table')
        
        contracts = []
        underlying_symbol = "NQM25"  # Default from URL
        underlying_price = None
        expiration_date = "2025-06-20"  # Default
        
        # Try to find underlying price
        price_elements = soup.find_all(text=lambda text: text and '$' in str(text) and ',' in str(text))
        for element in price_elements:
            try:
                price_str = str(element).replace('$', '').replace(',', '')
                if price_str.replace('.', '').isdigit():
                    underlying_price = float(price_str)
                    break
            except:
                continue
        
        # Parse tables for options data
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:  # Skip tables with no data rows
                continue
                
            headers = [th.get_text().strip().lower() for th in rows[0].find_all(['th', 'td'])]
            
            # Check if this looks like an options table
            options_indicators = ['strike', 'call', 'put', 'bid', 'ask', 'volume', 'oi']
            if not any(indicator in ' '.join(headers) for indicator in options_indicators):
                continue
            
            self.logger.info(f"Found potential options table with headers: {headers}")
            
            # Parse data rows
            for row in rows[1:]:
                cells = [td.get_text().strip() for td in row.find_all(['td', 'th'])]
                if len(cells) < 5:  # Need minimum columns for options data
                    continue
                
                try:
                    contract = self._parse_options_row(cells, headers, underlying_price, expiration_date)
                    if contract:
                        contracts.append(contract)
                except Exception as e:
                    self.logger.debug(f"Error parsing row {cells}: {e}")
                    continue
        
        return OptionsChainData(
            underlying_symbol=underlying_symbol,
            expiration_date=expiration_date,
            underlying_price=underlying_price,
            contracts=contracts,
            source='web_scrape',
            timestamp=datetime.now(),
            total_contracts=len(contracts)
        )
    
    def _extract_underlying_info(self) -> Dict[str, Any]:
        """
        Extract underlying symbol, price, and expiration from page
        """
        info = {
            'symbol': 'NQM25',
            'price': None,
            'expiration': '2025-06-20'
        }
        
        try:
            # Look for underlying price
            price_selectors = [
                "[data-ng-bind*='quote.lastPrice']",
                ".last-price",
                ".quote-price",
                "[class*='last']",
                "[class*='price']"
            ]
            
            for selector in price_selectors:
                try:
                    price_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_element.text.replace('$', '').replace(',', '')
                    if price_text.replace('.', '').isdigit():
                        info['price'] = float(price_text)
                        break
                except:
                    continue
            
            # Look for symbol in page title or headers
            try:
                title = self.driver.title
                if 'NQ' in title:
                    # Extract symbol from title
                    import re
                    symbol_match = re.search(r'(NQ[A-Z]\d{2})', title)
                    if symbol_match:
                        info['symbol'] = symbol_match.group(1)
            except:
                pass
                
        except Exception as e:
            self.logger.debug(f"Error extracting underlying info: {e}")
        
        return info
    
    def _extract_options_contracts(self, table_element) -> List[OptionsContract]:
        """
        Extract options contracts from the table element
        """
        contracts = []
        
        try:
            # Get table HTML and parse with BeautifulSoup for easier handling
            table_html = table_element.get_attribute('outerHTML')
            soup = BeautifulSoup(table_html, 'html.parser')
            
            rows = soup.find_all('tr')
            if not rows:
                return contracts
            
            # Get headers
            headers = [th.get_text().strip().lower() for th in rows[0].find_all(['th', 'td'])]
            self.logger.info(f"Options table headers: {headers}")
            
            # Parse data rows
            for row in rows[1:]:
                cells = [td.get_text().strip() for td in row.find_all(['td', 'th'])]
                if len(cells) < 5:
                    continue
                
                try:
                    contract = self._parse_options_row(cells, headers, None, "2025-06-20")
                    if contract:
                        contracts.append(contract)
                except Exception as e:
                    self.logger.debug(f"Error parsing options row: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error extracting options contracts: {e}")
        
        return contracts
    
    def _parse_options_row(self, cells: List[str], headers: List[str], 
                          underlying_price: Optional[float], expiration_date: str) -> Optional[OptionsContract]:
        """
        Parse a single options table row into an OptionsContract
        """
        
        def safe_float(value: str) -> Optional[float]:
            try:
                clean_value = value.replace('$', '').replace(',', '').replace('%', '')
                if clean_value in ['-', '--', '', 'N/A']:
                    return None
                return float(clean_value)
            except:
                return None
        
        def safe_int(value: str) -> Optional[int]:
            try:
                clean_value = value.replace(',', '')
                if clean_value in ['-', '--', '', 'N/A']:
                    return None
                return int(float(clean_value))
            except:
                return None
        
        try:
            # Find strike price (usually in middle or first column)
            strike = None
            for i, cell in enumerate(cells):
                try:
                    potential_strike = safe_float(cell)
                    if potential_strike and 10000 <= potential_strike <= 30000:  # NQ typical range
                        strike = potential_strike
                        break
                except:
                    continue
            
            if not strike:
                return None
            
            # Initialize contract with defaults
            contract = OptionsContract(
                strike=strike,
                call_last=None, call_change=None, call_bid=None, call_ask=None,
                call_volume=None, call_open_interest=None, call_implied_volatility=None,
                put_last=None, put_change=None, put_bid=None, put_ask=None,
                put_volume=None, put_open_interest=None, put_implied_volatility=None,
                expiration_date=expiration_date,
                underlying_price=underlying_price,
                source='web_scrape',
                timestamp=datetime.now()
            )
            
            # Parse remaining cells based on typical barchart layout
            # This is a best-effort parsing since layout may vary
            if len(cells) >= 10:
                # Typical layout: Strike | Call_Bid | Call_Ask | Call_Last | Call_Vol | Put_Bid | Put_Ask | Put_Last | Put_Vol
                try:
                    contract.call_bid = safe_float(cells[1]) if len(cells) > 1 else None
                    contract.call_ask = safe_float(cells[2]) if len(cells) > 2 else None
                    contract.call_last = safe_float(cells[3]) if len(cells) > 3 else None
                    contract.call_volume = safe_int(cells[4]) if len(cells) > 4 else None
                    contract.put_bid = safe_float(cells[5]) if len(cells) > 5 else None
                    contract.put_ask = safe_float(cells[6]) if len(cells) > 6 else None
                    contract.put_last = safe_float(cells[7]) if len(cells) > 7 else None
                    contract.put_volume = safe_int(cells[8]) if len(cells) > 8 else None
                except:
                    pass
            
            return contract
            
        except Exception as e:
            self.logger.debug(f"Error parsing options row {cells}: {e}")
            return None

class BarchartAPIComparator:
    """
    Compare web scraped data with API data from barchart
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def fetch_api_data(self, symbol: str = "NQM25") -> OptionsChainData:
        """
        Fetch options data from barchart API (mock implementation)
        
        In real implementation, this would use the actual barchart API
        """
        
        # This is a placeholder - would need actual API credentials and endpoints
        self.logger.info(f"Fetching API data for {symbol}")
        
        # Mock API response structure
        mock_contracts = [
            OptionsContract(
                strike=19000.0,
                call_last=150.0, call_change=5.0, call_bid=148.0, call_ask=152.0,
                call_volume=100, call_open_interest=500, call_implied_volatility=0.25,
                put_last=50.0, put_change=-2.0, put_bid=48.0, put_ask=52.0,
                put_volume=80, put_open_interest=300, put_implied_volatility=0.23,
                expiration_date="2025-06-20",
                underlying_price=19100.0,
                source='api',
                timestamp=datetime.now()
            )
        ]
        
        return OptionsChainData(
            underlying_symbol=symbol,
            expiration_date="2025-06-20",
            underlying_price=19100.0,
            contracts=mock_contracts,
            source='api',
            timestamp=datetime.now(),
            total_contracts=len(mock_contracts)
        )
    
    def compare_data_sources(self, web_data: OptionsChainData, api_data: OptionsChainData) -> Dict[str, Any]:
        """
        EXPERIMENTAL VALIDATION: Compare web scraped vs API data
        
        Returns comprehensive comparison analysis
        """
        
        comparison = {
            'comparison_timestamp': datetime.now().isoformat(),
            'web_data_summary': {
                'source': web_data.source,
                'contract_count': web_data.total_contracts,
                'underlying_symbol': web_data.underlying_symbol,
                'underlying_price': web_data.underlying_price,
                'timestamp': web_data.timestamp.isoformat()
            },
            'api_data_summary': {
                'source': api_data.source,
                'contract_count': api_data.total_contracts,
                'underlying_symbol': api_data.underlying_symbol,
                'underlying_price': api_data.underlying_price,
                'timestamp': api_data.timestamp.isoformat()
            },
            'differences': {
                'contract_count_diff': web_data.total_contracts - api_data.total_contracts,
                'underlying_price_diff': None,
                'missing_strikes_web': [],
                'missing_strikes_api': [],
                'price_discrepancies': []
            },
            'data_quality': {
                'web_completeness': 0.0,
                'api_completeness': 0.0,
                'overall_similarity': 0.0
            }
        }
        
        # Compare underlying prices
        if web_data.underlying_price and api_data.underlying_price:
            comparison['differences']['underlying_price_diff'] = web_data.underlying_price - api_data.underlying_price
        
        # Create strike mappings
        web_strikes = {c.strike: c for c in web_data.contracts}
        api_strikes = {c.strike: c for c in api_data.contracts}
        
        # Find missing strikes
        comparison['differences']['missing_strikes_web'] = list(set(api_strikes.keys()) - set(web_strikes.keys()))
        comparison['differences']['missing_strikes_api'] = list(set(web_strikes.keys()) - set(api_strikes.keys()))
        
        # Compare overlapping strikes
        common_strikes = set(web_strikes.keys()) & set(api_strikes.keys())
        
        for strike in common_strikes:
            web_contract = web_strikes[strike]
            api_contract = api_strikes[strike]
            
            discrepancies = self._compare_contracts(web_contract, api_contract, strike)
            if discrepancies:
                comparison['differences']['price_discrepancies'].append({
                    'strike': strike,
                    'discrepancies': discrepancies
                })
        
        # Calculate data quality metrics
        comparison['data_quality'] = self._calculate_quality_metrics(web_data, api_data, common_strikes)
        
        return comparison
    
    def _compare_contracts(self, web_contract: OptionsContract, api_contract: OptionsContract, strike: float) -> Dict[str, Any]:
        """
        Compare individual contracts for discrepancies
        """
        discrepancies = {}
        
        fields_to_compare = [
            'call_last', 'call_bid', 'call_ask', 'call_volume', 'call_open_interest',
            'put_last', 'put_bid', 'put_ask', 'put_volume', 'put_open_interest'
        ]
        
        for field in fields_to_compare:
            web_value = getattr(web_contract, field)
            api_value = getattr(api_contract, field)
            
            if web_value is not None and api_value is not None:
                if isinstance(web_value, (int, float)) and isinstance(api_value, (int, float)):
                    diff = abs(web_value - api_value)
                    if diff > 0.01:  # Threshold for significance
                        discrepancies[field] = {
                            'web': web_value,
                            'api': api_value,
                            'difference': diff,
                            'percentage_diff': (diff / max(abs(api_value), 0.01)) * 100
                        }
        
        return discrepancies
    
    def _calculate_quality_metrics(self, web_data: OptionsChainData, api_data: OptionsChainData, common_strikes: set) -> Dict[str, float]:
        """
        Calculate data quality and similarity metrics
        """
        
        # Web data completeness
        web_complete_fields = 0
        web_total_fields = 0
        
        for contract in web_data.contracts:
            fields = ['call_last', 'call_bid', 'call_ask', 'put_last', 'put_bid', 'put_ask']
            for field in fields:
                web_total_fields += 1
                if getattr(contract, field) is not None:
                    web_complete_fields += 1
        
        web_completeness = web_complete_fields / max(web_total_fields, 1)
        
        # API data completeness
        api_complete_fields = 0
        api_total_fields = 0
        
        for contract in api_data.contracts:
            fields = ['call_last', 'call_bid', 'call_ask', 'put_last', 'put_bid', 'put_ask']
            for field in fields:
                api_total_fields += 1
                if getattr(contract, field) is not None:
                    api_complete_fields += 1
        
        api_completeness = api_complete_fields / max(api_total_fields, 1)
        
        # Overall similarity (based on common strikes and data agreement)
        total_strikes = len(set(c.strike for c in web_data.contracts) | set(c.strike for c in api_data.contracts))
        strike_overlap = len(common_strikes) / max(total_strikes, 1)
        
        # Simple similarity metric
        overall_similarity = (strike_overlap + web_completeness + api_completeness) / 3
        
        return {
            'web_completeness': round(web_completeness, 3),
            'api_completeness': round(api_completeness, 3),
            'overall_similarity': round(overall_similarity, 3)
        }

def main():
    """
    Main execution function for barchart data comparison
    """
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Target URL
    url = "https://www.barchart.com/futures/quotes/NQM25/options/MC7M25?futuresOptionsView=merged"
    
    logger.info("Starting Barchart Data Comparison Analysis")
    
    try:
        # Initialize scraper
        scraper = BarchartWebScraper(headless=False)  # Set to False to see browser
        
        # Scrape web data
        logger.info("Scraping web data...")
        web_data = scraper.scrape_barchart_options(url)
        
        # Get API data
        logger.info("Fetching API data...")
        comparator = BarchartAPIComparator()
        api_data = comparator.fetch_api_data("NQM25")
        
        # Compare data sources
        logger.info("Comparing data sources...")
        comparison_results = comparator.compare_data_sources(web_data, api_data)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save web data
        with open(f'/Users/Mike/trading/algos/EOD/tasks/options_trading_system/data_ingestion/barchart_web_scraper/web_data_{timestamp}.json', 'w') as f:
            json.dump(asdict(web_data), f, indent=2, default=str)
        
        # Save API data
        with open(f'/Users/Mike/trading/algos/EOD/tasks/options_trading_system/data_ingestion/barchart_web_scraper/api_data_{timestamp}.json', 'w') as f:
            json.dump(asdict(api_data), f, indent=2, default=str)
        
        # Save comparison
        with open(f'/Users/Mike/trading/algos/EOD/tasks/options_trading_system/data_ingestion/barchart_web_scraper/comparison_{timestamp}.json', 'w') as f:
            json.dump(comparison_results, f, indent=2, default=str)
        
        # Print summary
        logger.info("=== COMPARISON SUMMARY ===")
        logger.info(f"Web scraped contracts: {web_data.total_contracts}")
        logger.info(f"API contracts: {api_data.total_contracts}")
        logger.info(f"Contract count difference: {comparison_results['differences']['contract_count_diff']}")
        logger.info(f"Web data completeness: {comparison_results['data_quality']['web_completeness']:.1%}")
        logger.info(f"API data completeness: {comparison_results['data_quality']['api_completeness']:.1%}")
        logger.info(f"Overall similarity: {comparison_results['data_quality']['overall_similarity']:.1%}")
        
        if comparison_results['differences']['price_discrepancies']:
            logger.info(f"Price discrepancies found: {len(comparison_results['differences']['price_discrepancies'])}")
        else:
            logger.info("No significant price discrepancies found")
        
        logger.info(f"Results saved with timestamp: {timestamp}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()