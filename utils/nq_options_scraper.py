#!/usr/bin/env python3
"""
Enhanced NQ Options scraper with better HTML parsing for Barchart
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Tuple, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def extract_options_data_from_script(html_content: str) -> Tuple[float, List[Dict]]:
    """Extract options data from JavaScript in the HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    current_price = None
    options_data = []
    
    # Look for data in script tags
    scripts = soup.find_all('script')
    
    for script in scripts:
        if not script.string:
            continue
            
        # Look for current price
        if 'currentSymbol' in script.string or 'lastPrice' in script.string:
            # Try different patterns
            patterns = [
                r'"lastPrice":\s*"?([\d,\.]+)"?',
                r'"raw":\s*{[^}]*"lastPrice":\s*([\d\.]+)',
                r'lastPrice["\']?\s*:\s*["\']?([\d,\.]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, script.string)
                if match:
                    try:
                        current_price = float(match.group(1).replace(',', ''))
                        logger.info(f"Found current price: {current_price}")
                        break
                    except:
                        continue
        
        # Look for options data
        if 'optionsData' in script.string or 'tableData' in script.string:
            # Try to extract JSON data
            try:
                # Look for JSON objects
                json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                matches = re.findall(json_pattern, script.string)
                
                for match in matches:
                    try:
                        data = json.loads(match)
                        # Check if this looks like options data
                        if isinstance(data, dict) and any(key in str(data).lower() for key in ['strike', 'call', 'put']):
                            options_data.append(data)
                    except:
                        continue
            except:
                pass
    
    return current_price, options_data


def parse_options_table(html_content: str) -> List[Dict]:
    """Parse options data from HTML table"""
    soup = BeautifulSoup(html_content, 'html.parser')
    options_data = []
    
    # Look for tables with class names that might contain options data
    table_classes = ['bc-table', 'options-table', 'data-table', 'futures-options']
    
    for class_name in table_classes:
        tables = soup.find_all('table', class_=re.compile(class_name))
        
        for table in tables:
            # Check if this looks like an options table
            headers = table.find_all('th')
            header_text = ' '.join([h.text.lower() for h in headers])
            
            if any(word in header_text for word in ['strike', 'call', 'put', 'volume', 'open interest']):
                # Parse the table
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 7:  # Minimum for options data
                        try:
                            # Extract data based on common patterns
                            row_data = {}
                            cell_texts = [cell.text.strip() for cell in cells]
                            
                            # Find strike price
                            for i, text in enumerate(cell_texts):
                                # Strike prices are typically 5-digit numbers
                                if re.match(r'^\d{5}(\.\d+)?$', text.replace(',', '')):
                                    row_data['strike'] = float(text.replace(',', ''))
                                    
                                    # Assume structure around strike price
                                    # Typical order: Call Vol, Call OI, Call Last, Strike, Put Last, Put OI, Put Vol
                                    if i >= 3:
                                        row_data['call_volume'] = int(cell_texts[i-3].replace(',', '') or '0')
                                        row_data['call_oi'] = int(cell_texts[i-2].replace(',', '') or '0')
                                        row_data['call_premium'] = float(cell_texts[i-1].replace(',', '') or '0')
                                    
                                    if i <= len(cell_texts) - 4:
                                        row_data['put_premium'] = float(cell_texts[i+1].replace(',', '') or '0')
                                        row_data['put_oi'] = int(cell_texts[i+2].replace(',', '') or '0')
                                        row_data['put_volume'] = int(cell_texts[i+3].replace(',', '') or '0')
                                    
                                    options_data.append(row_data)
                                    break
                        except:
                            continue
    
    return options_data


def scrape_with_selenium(url: str) -> Tuple[float, List[Dict]]:
    """Use Selenium for JavaScript-heavy pages (optional fallback)"""
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        
        driver.get(url)
        
        # Wait for table to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "bc-table"))
        )
        
        # Get page source after JavaScript execution
        html = driver.page_source
        driver.quit()
        
        return extract_options_data_from_script(html)
        
    except ImportError:
        logger.warning("Selenium not available, skipping JavaScript rendering")
        return None, []


def enhanced_scrape_barchart(url: str) -> Tuple[float, List[Dict]]:
    """Enhanced scraping with multiple fallback methods"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        html_content = response.text
        
        # Method 1: Extract from JavaScript
        current_price, js_data = extract_options_data_from_script(html_content)
        
        # Method 2: Parse HTML tables
        table_data = parse_options_table(html_content)
        
        # Combine data
        all_data = js_data + table_data
        
        # If no data found, try Selenium
        if not all_data and not current_price:
            logger.info("Trying Selenium for JavaScript rendering...")
            current_price, all_data = scrape_with_selenium(url)
        
        return current_price, all_data
        
    except Exception as e:
        logger.error(f"Error in enhanced scraping: {e}")
        return None, []


if __name__ == "__main__":
    # Test the enhanced scraper
    from nq_options_ev_algo import get_current_contract_url
    
    logging.basicConfig(level=logging.INFO)
    
    url = get_current_contract_url()
    current_price, options_data = enhanced_scrape_barchart(url)
    
    print(f"Current Price: {current_price}")
    print(f"Found {len(options_data)} options strikes")
    
    if options_data:
        print("\nSample data:")
        for i, data in enumerate(options_data[:3]):
            print(f"Strike {i+1}: {data}")