#!/usr/bin/env python3
"""
Puppeteer-based scraper for Barchart options data
Uses Chrome remote debugging port for better control
"""

import asyncio
import json
import logging
from typing import List, Tuple, Dict, Optional
from pyppeteer import launch, connect
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class PuppeteerBarchartScraper:
    """Scraper using Puppeteer with Chrome remote debugging"""
    
    def __init__(self, remote_debugging_port: int = 9222, headless: bool = False):
        self.remote_debugging_port = remote_debugging_port
        self.headless = headless
        self.browser = None
        self.page = None
    
    async def connect_to_chrome(self) -> bool:
        """Connect to existing Chrome instance with remote debugging enabled"""
        try:
            # Try to connect to existing Chrome instance
            logger.info(f"Attempting to connect to Chrome on port {self.remote_debugging_port}")
            browser_url = f"http://localhost:{self.remote_debugging_port}"
            self.browser = await connect(browserURL=browser_url)
            logger.info("Successfully connected to Chrome remote debugging")
            return True
        except Exception as e:
            logger.warning(f"Could not connect to existing Chrome: {e}")
            return False
    
    async def launch_chrome(self) -> bool:
        """Launch new Chrome instance with remote debugging"""
        try:
            logger.info("Launching new Chrome instance with remote debugging")
            self.browser = await launch(
                headless=self.headless,
                args=[
                    f'--remote-debugging-port={self.remote_debugging_port}',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                ],
                executablePath='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'  # macOS path
            )
            logger.info("Chrome launched successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to launch Chrome: {e}")
            return False
    
    async def initialize(self) -> bool:
        """Initialize browser connection"""
        # First try to connect to existing Chrome
        if not await self.connect_to_chrome():
            # If that fails, launch new instance
            logger.warning("No existing Chrome found, launching new instance")
            if not await self.launch_chrome():
                return False
        
        # Get existing pages or create new one
        pages = await self.browser.pages()
        if pages:
            # Use first available page
            self.page = pages[0]
            logger.info(f"Using existing page: {await self.page.url()}")
        else:
            # Create new page
            self.page = await self.browser.newPage()
            logger.info("Created new page")
        
        # Set viewport
        await self.page.setViewport({'width': 1920, 'height': 1080})
        
        # Modify navigator to hide automation
        await self.page.evaluateOnNewDocument('''() => {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
        }''')
        
        return True
    
    async def scrape_options_data(self, url: str) -> Tuple[Optional[float], List[Dict]]:
        """Scrape options data from Barchart URL"""
        try:
            if not self.page:
                raise Exception("Browser not initialized")
            
            logger.info(f"Navigating to {url}")
            await self.page.goto(url, waitUntil='networkidle2', timeout=30000)
            
            # Wait for Angular to load
            await self.page.waitFor(2000)
            
            # Check for reCAPTCHA
            recaptcha_present = await self.page.evaluate('''() => {
                return document.querySelector('iframe[src*="recaptcha"]') !== null;
            }''')
            
            if recaptcha_present:
                logger.warning("reCAPTCHA detected - manual intervention may be required")
                # Wait for user to solve captcha manually
                logger.info("Waiting for manual captcha solution (60 seconds)...")
                await asyncio.sleep(60)
            
            # Wait for options table to load
            logger.info("Waiting for options data to load...")
            await self.page.waitForSelector('.bc-table-scrollable-inner, .options-table, table', 
                                           timeout=30000)
            
            # Extract current price
            current_price = await self._extract_current_price()
            
            # Extract options data
            options_data = await self._extract_options_data()
            
            return current_price, options_data
            
        except Exception as e:
            logger.error(f"Error scraping data: {e}")
            return None, []
    
    async def _extract_current_price(self) -> Optional[float]:
        """Extract current futures price"""
        try:
            # Try multiple selectors
            price_selectors = [
                '.last-change',
                '.last-price',
                '.quote-price',
                '[data-ng-bind*="lastPrice"]'
            ]
            
            for selector in price_selectors:
                try:
                    price_text = await self.page.evaluate(f'''() => {{
                        const elem = document.querySelector('{selector}');
                        return elem ? elem.innerText : null;
                    }}''')
                    
                    if price_text:
                        # Clean and parse price
                        price = float(re.sub(r'[^\d.-]', '', price_text))
                        if 15000 < price < 30000:  # Sanity check for NQ
                            logger.info(f"Found current price: {price}")
                            return price
                except:
                    continue
            
            # Try to get from Angular scope
            price = await self.page.evaluate('''() => {
                try {
                    const scope = angular.element(document.querySelector('[data-ng-controller]')).scope();
                    return parseFloat(scope.item?.lastPrice?.replace(/,/g, ''));
                } catch (e) {
                    return null;
                }
            }''')
            
            if price and 15000 < price < 30000:
                logger.info(f"Found current price from Angular: {price}")
                return price
            
            logger.warning("Could not extract current price")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting price: {e}")
            return None
    
    async def _extract_options_data(self) -> List[Dict]:
        """Extract options data from table"""
        try:
            # Wait for table data
            await self.page.waitFor(1000)
            
            # Extract data using JavaScript
            options_data = await self.page.evaluate('''() => {
                const data = [];
                
                // Try to find options table
                const tables = document.querySelectorAll('table');
                let optionsTable = null;
                
                for (const table of tables) {
                    const text = table.innerText.toLowerCase();
                    if (text.includes('strike') && text.includes('call') && text.includes('put')) {
                        optionsTable = table;
                        break;
                    }
                }
                
                if (!optionsTable) {
                    // Try Angular data binding
                    try {
                        const scope = angular.element(document.querySelector('[data-ng-controller]')).scope();
                        if (scope.optionsData) {
                            return scope.optionsData;
                        }
                    } catch (e) {}
                    return [];
                }
                
                // Parse table rows
                const rows = optionsTable.querySelectorAll('tr');
                for (let i = 1; i < rows.length; i++) {  // Skip header
                    const cells = rows[i].querySelectorAll('td');
                    if (cells.length >= 7) {
                        // Extract data based on common Barchart layout
                        const strike = parseFloat(cells[3]?.innerText.replace(/,/g, ''));
                        if (strike && !isNaN(strike)) {
                            data.push({
                                strike: strike,
                                call_volume: parseInt(cells[0]?.innerText.replace(/,/g, '') || '0'),
                                call_oi: parseInt(cells[1]?.innerText.replace(/,/g, '') || '0'),
                                call_premium: parseFloat(cells[2]?.innerText.replace(/,/g, '') || '0'),
                                put_premium: parseFloat(cells[4]?.innerText.replace(/,/g, '') || '0'),
                                put_oi: parseInt(cells[5]?.innerText.replace(/,/g, '') || '0'),
                                put_volume: parseInt(cells[6]?.innerText.replace(/,/g, '') || '0')
                            });
                        }
                    }
                }
                
                return data;
            }''')
            
            logger.info(f"Extracted {len(options_data)} option strikes")
            return options_data
            
        except Exception as e:
            logger.error(f"Error extracting options data: {e}")
            return []
    
    async def close(self):
        """Close page and disconnect from browser (but keep Chrome running)"""
        if self.page:
            await self.page.close()
            logger.info("Page closed")
        
        if self.browser:
            # Just disconnect, don't close the browser
            await self.browser.disconnect()
            logger.info("Disconnected from Chrome (browser still running)")


async def scrape_barchart_with_puppeteer(url: str, remote_port: int = 9222) -> Tuple[Optional[float], List[Dict]]:
    """Main function to scrape Barchart using Puppeteer"""
    # Import here to avoid circular imports
    from .chrome_connection_manager import get_chrome_page, close_chrome_page
    
    page = None
    try:
        # Get a page from persistent Chrome connection
        logger.info(f"Getting page from Chrome on port {remote_port}")
        page = await get_chrome_page(remote_port)
        
        logger.info(f"Navigating to {url}")
        await page.goto(url, waitUntil='networkidle2', timeout=30000)
        
        # Wait for Angular to load
        await page.waitFor(2000)
        
        # Check for reCAPTCHA
        recaptcha_present = await page.evaluate('''() => {
            return document.querySelector('iframe[src*="recaptcha"]') !== null;
        }''')
        
        if recaptcha_present:
            logger.warning("reCAPTCHA detected - manual intervention may be required")
            logger.info("Waiting for manual captcha solution (60 seconds)...")
            await asyncio.sleep(60)
        
        # Wait for options table to load
        logger.info("Waiting for options data to load...")
        try:
            await page.waitForSelector('.bc-table-scrollable-inner, .options-table, table', 
                                     timeout=30000)
        except:
            logger.warning("Table selector timeout, trying to extract data anyway")
        
        # Extract current price
        current_price = await _extract_current_price_from_page(page)
        
        # Extract options data
        options_data = await _extract_options_data_from_page(page)
        
        return current_price, options_data
        
    except Exception as e:
        logger.error(f"Error in scrape_barchart_with_puppeteer: {e}")
        return None, []
    finally:
        if page:
            await close_chrome_page(page)


async def _extract_current_price_from_page(page) -> Optional[float]:
    """Extract current price from page"""
    try:
        # Try multiple selectors
        price_selectors = [
            '.last-change',
            '.last-price',
            '.quote-price',
            '[data-ng-bind*="lastPrice"]'
        ]
        
        for selector in price_selectors:
            try:
                price_text = await page.evaluate(f'''() => {{
                    const elem = document.querySelector('{selector}');
                    return elem ? elem.innerText : null;
                }}''')
                
                if price_text:
                    price = float(re.sub(r'[^\d.-]', '', price_text))
                    if 15000 < price < 30000:
                        logger.info(f"Found current price: {price}")
                        return price
            except:
                continue
        
        # Try to get from Angular scope
        price = await page.evaluate('''() => {
            try {
                const scope = angular.element(document.querySelector('[data-ng-controller]')).scope();
                return parseFloat(scope.item?.lastPrice?.replace(/,/g, ''));
            } catch (e) {
                return null;
            }
        }''')
        
        if price and 15000 < price < 30000:
            logger.info(f"Found current price from Angular: {price}")
            return price
        
        logger.warning("Could not extract current price")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting price: {e}")
        return None


async def _extract_options_data_from_page(page) -> List[Dict]:
    """Extract options data from page"""
    try:
        # Wait a bit for data to load
        await page.waitFor(1000)
        
        # Extract data using JavaScript
        options_data = await page.evaluate('''() => {
            const data = [];
            
            // Try to find options table
            const tables = document.querySelectorAll('table');
            let optionsTable = null;
            
            for (const table of tables) {
                const text = table.innerText.toLowerCase();
                if (text.includes('strike') && text.includes('call') && text.includes('put')) {
                    optionsTable = table;
                    break;
                }
            }
            
            if (!optionsTable) {
                // Try Angular data binding
                try {
                    const scope = angular.element(document.querySelector('[data-ng-controller]')).scope();
                    if (scope.optionsData) {
                        return scope.optionsData;
                    }
                } catch (e) {}
                return [];
            }
            
            // Parse table rows
            const rows = optionsTable.querySelectorAll('tr');
            for (let i = 1; i < rows.length; i++) {  // Skip header
                const cells = rows[i].querySelectorAll('td');
                if (cells.length >= 7) {
                    const strike = parseFloat(cells[3]?.innerText.replace(/,/g, ''));
                    if (strike && !isNaN(strike)) {
                        data.push({
                            strike: strike,
                            call_volume: parseInt(cells[0]?.innerText.replace(/,/g, '') || '0'),
                            call_oi: parseInt(cells[1]?.innerText.replace(/,/g, '') || '0'),
                            call_premium: parseFloat(cells[2]?.innerText.replace(/,/g, '') || '0'),
                            put_premium: parseFloat(cells[4]?.innerText.replace(/,/g, '') || '0'),
                            put_oi: parseInt(cells[5]?.innerText.replace(/,/g, '') || '0'),
                            put_volume: parseInt(cells[6]?.innerText.replace(/,/g, '') || '0')
                        });
                    }
                }
            }
            
            return data;
        }''')
        
        logger.info(f"Extracted {len(options_data)} option strikes")
        return options_data
        
    except Exception as e:
        logger.error(f"Error extracting options data: {e}")
        return []


def run_puppeteer_scraper(url: str, remote_port: int = 9222) -> Tuple[Optional[float], List[Dict]]:
    """Synchronous wrapper for async scraper"""
    return asyncio.run(scrape_barchart_with_puppeteer(url, remote_port))


if __name__ == "__main__":
    # Test the scraper
    import sys
    sys.path.append('..')
    from nq_options_ev_algo import get_current_contract_url
    
    logging.basicConfig(level=logging.INFO)
    
    url = get_current_contract_url()
    print(f"Testing Puppeteer scraper with URL: {url}")
    
    current_price, options = run_puppeteer_scraper(url)
    
    print(f"\nCurrent Price: {current_price}")
    print(f"Options Found: {len(options)}")
    
    if options:
        print("\nFirst 3 strikes:")
        for opt in options[:3]:
            print(f"  Strike {opt['strike']}: Call ${opt['call_premium']}, Put ${opt['put_premium']}")