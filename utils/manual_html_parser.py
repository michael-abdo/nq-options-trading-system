#!/usr/bin/env python3
"""
Manual HTML Parser for Manually Saved Barchart Pages
Extracts options data from HTML files saved via browser "Save Page As"
"""

import re
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def extract_from_manual_html(html_file_path: str) -> Dict[str, Any]:
    """Extract options data from manually saved HTML file"""
    logger.info(f"🔍 Extracting data from manually saved HTML: {html_file_path}")
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract current price
        current_price = extract_current_price(html_content, soup)
        
        # Extract options data from all possible sources
        options_data = extract_options_data(html_content, soup)
        
        logger.info(f"✅ Successfully extracted price: {current_price}")
        logger.info(f"✅ Successfully extracted {len(options_data)} option strikes")
        
        return {
            "success": True,
            "current_price": current_price,
            "options_data": options_data,
            "method": "manual_html_parser"
        }
        
    except Exception as e:
        logger.error(f"❌ Error parsing manual HTML: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def extract_current_price(html_content: str, soup: BeautifulSoup) -> Optional[float]:
    """Extract current NQ price from various sources"""
    
    # Method 1: Look for price in Angular bindings
    price_patterns = [
        r'"lastPrice":\s*"?([0-9,]+\.?[0-9]*)"?',
        r'lastPrice["\']:\s*["\']?([0-9,]+\.?[0-9]*)["\']?',
        r'ng-binding[^>]*>([0-9,]+\.?[0-9]*)<'
    ]
    
    for pattern in price_patterns:
        matches = re.findall(pattern, html_content)
        for match in matches:
            try:
                price = float(match.replace(',', ''))
                if 15000 < price < 30000:  # Reasonable NQ price range
                    logger.info(f"Found price via regex: {price}")
                    return price
            except:
                continue
    
    # Method 2: Look in specific elements
    price_selectors = [
        '.last-change.ng-binding',
        '.pricechangerow .last-change',
        '[data-ng-bind*="lastPrice"]'
    ]
    
    for selector in price_selectors:
        elements = soup.select(selector)
        for elem in elements:
            text = elem.get_text().strip()
            price_match = re.search(r'([0-9,]+\.?[0-9]*)', text)
            if price_match:
                try:
                    price = float(price_match.group(1).replace(',', ''))
                    if 15000 < price < 30000:
                        logger.info(f"Found price via CSS selector '{selector}': {price}")
                        return price
                except:
                    continue
    
    logger.warning("Could not extract current price")
    return None

def extract_options_data(html_content: str, soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract options data from various sources"""
    options = []
    
    # Method 1: Extract from rendered tables
    options.extend(extract_from_tables(soup))
    
    # Method 2: Extract from JavaScript data
    options.extend(extract_from_javascript(html_content))
    
    # Method 3: Extract from Angular scope data (if embedded)
    options.extend(extract_from_angular_data(html_content))
    
    # Remove duplicates and sort
    unique_options = {}
    for opt in options:
        strike = opt['strike']
        if strike not in unique_options:
            unique_options[strike] = opt
        else:
            # Merge data (prefer non-zero values)
            existing = unique_options[strike]
            for key in ['call_volume', 'call_oi', 'call_premium', 'put_volume', 'put_oi', 'put_premium']:
                if opt.get(key, 0) > 0 and existing.get(key, 0) == 0:
                    existing[key] = opt[key]
    
    final_options = sorted(unique_options.values(), key=lambda x: x['strike'])
    logger.info(f"Found {len(final_options)} unique option strikes")
    return final_options

def extract_from_tables(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract from HTML tables and Shadow DOM templates"""
    options = []
    
    # First try shadow DOM template extraction
    shadow_options = extract_from_shadow_dom(soup)
    if shadow_options:
        options.extend(shadow_options)
        logger.info(f"Extracted {len(shadow_options)} options from Shadow DOM")
    
    # Then try regular tables
    tables = soup.find_all('table')
    logger.info(f"Searching {len(tables)} tables for options data")
    
    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        if len(rows) < 3:  # Skip tiny tables
            continue
        
        # Check if this looks like an options table
        table_text = table.get_text().lower()
        if not any(keyword in table_text for keyword in ['strike', 'call', 'put', 'premium', 'volume']):
            continue
        
        logger.info(f"Analyzing table {i+1} with {len(rows)} rows")
        
        # Try to find header row and data rows
        header_row = None
        data_rows = []
        
        for row in rows:
            cells = row.find_all(['th', 'td'])
            if not cells:
                continue
                
            cell_texts = [cell.get_text().strip() for cell in cells]
            
            # Check if this is a header row
            if any(keyword.lower() in ' '.join(cell_texts).lower() 
                   for keyword in ['Strike', 'Call', 'Put', 'Volume', 'Premium', 'Last']):
                header_row = cell_texts
                continue
            
            # Check if this row has numeric data that could be strikes
            strike_found = False
            for cell_text in cell_texts:
                if re.match(r'^[0-9,]+\.?[0-9]*$', cell_text.replace(',', '')):
                    try:
                        value = float(cell_text.replace(',', ''))
                        if 15000 <= value <= 30000:  # Likely a strike price
                            strike_found = True
                            break
                    except:
                        continue
            
            if strike_found:
                data_rows.append(cell_texts)
        
        # Extract data from promising rows
        for row_data in data_rows:
            if len(row_data) >= 3:
                try:
                    option = parse_table_row(row_data)
                    if option:
                        options.append(option)
                except Exception as e:
                    logger.debug(f"Error parsing row {row_data}: {e}")
                    continue
    
    logger.info(f"Extracted {len(options)} options from tables")
    return options

def parse_table_row(row_data: List[str]) -> Optional[Dict[str, Any]]:
    """Parse a single table row into option data"""
    # Find the strike price (number in 15000-30000 range)
    strike = None
    strike_index = None
    
    for i, cell in enumerate(row_data):
        try:
            value = float(cell.replace(',', ''))
            if 15000 <= value <= 30000:
                strike = value
                strike_index = i
                break
        except:
            continue
    
    if strike is None:
        return None
    
    # Default values
    option = {
        'strike': strike,
        'call_volume': 0,
        'call_oi': 0,
        'call_premium': 0,
        'put_volume': 0,
        'put_oi': 0,
        'put_premium': 0
    }
    
    # Try to extract other values based on position relative to strike
    # Common patterns: [Call Vol, Call OI, Call Last, Strike, Put Last, Put OI, Put Vol]
    # or similar variations
    
    def safe_float(text):
        try:
            return float(text.replace(',', '').replace('$', ''))
        except:
            return 0
    
    # Extract values around the strike
    if len(row_data) >= 7:  # Full row with call and put data
        if strike_index >= 3:
            option['call_volume'] = safe_float(row_data[strike_index - 3])
            option['call_oi'] = safe_float(row_data[strike_index - 2])
            option['call_premium'] = safe_float(row_data[strike_index - 1])
        
        if strike_index + 3 < len(row_data):
            option['put_premium'] = safe_float(row_data[strike_index + 1])
            option['put_oi'] = safe_float(row_data[strike_index + 2])
            option['put_volume'] = safe_float(row_data[strike_index + 3])
    
    return option

def extract_from_shadow_dom(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract options data from Shadow DOM templates"""
    options = []
    
    # Find all text-binding elements with Shadow DOM templates
    text_bindings = soup.find_all('text-binding')
    
    # Group bindings by their parent row or container
    current_option = {}
    
    for binding in text_bindings:
        # Get the binding type (strike, volume, openInterest, etc.)
        binding_attr = binding.get('binding', '')
        
        # Find the template with shadow DOM content
        template = binding.find('template', attrs={'shadowrootmode': 'open'})
        if not template:
            continue
            
        value_text = template.get_text().strip()
        if not value_text:
            continue
            
        logger.debug(f"Found Shadow DOM binding: {binding_attr} = {value_text}")
        
        try:
            # Parse different types of data
            if 'strike' in binding_attr.lower():
                # Strike price like "21,450.00C" or "21,450.00P"
                strike_match = re.match(r'([0-9,]+\.?\d*)[CP]?', value_text)
                if strike_match:
                    strike = float(strike_match.group(1).replace(',', ''))
                    if 15000 <= strike <= 30000:  # Valid NQ strike range
                        # Start new option entry
                        if current_option and 'strike' in current_option:
                            options.append(current_option)
                        current_option = {
                            'strike': strike,
                            'call_volume': 0,
                            'call_oi': 0,
                            'call_premium': 0,
                            'put_volume': 0,
                            'put_oi': 0,
                            'put_premium': 0
                        }
                        
                        # Determine if this is call or put
                        if value_text.endswith('C'):
                            current_option['_type'] = 'call'
                        elif value_text.endswith('P'):
                            current_option['_type'] = 'put'
            
            elif 'volume' in binding_attr.lower():
                # Volume data
                volume = int(value_text.replace(',', ''))
                if current_option:
                    if current_option.get('_type') == 'call':
                        current_option['call_volume'] = volume
                    elif current_option.get('_type') == 'put':
                        current_option['put_volume'] = volume
            
            elif 'openinterest' in binding_attr.lower():
                # Open Interest data
                oi = int(value_text.replace(',', ''))
                if current_option:
                    if current_option.get('_type') == 'call':
                        current_option['call_oi'] = oi
                    elif current_option.get('_type') == 'put':
                        current_option['put_oi'] = oi
            
            elif 'lastprice' in binding_attr.lower() or 'premium' in binding_attr.lower():
                # Premium/Last Price data
                premium_match = re.search(r'([0-9,]+\.?\d*)', value_text)
                if premium_match:
                    premium = float(premium_match.group(1).replace(',', ''))
                    if current_option:
                        if current_option.get('_type') == 'call':
                            current_option['call_premium'] = premium
                        elif current_option.get('_type') == 'put':
                            current_option['put_premium'] = premium
                            
        except (ValueError, AttributeError) as e:
            logger.debug(f"Error parsing Shadow DOM value '{value_text}': {e}")
            continue
    
    # Add the last option if it exists
    if current_option and 'strike' in current_option:
        options.append(current_option)
    
    # Clean up the _type field and merge call/put data by strike
    merged_options = {}
    for opt in options:
        strike = opt['strike']
        opt.pop('_type', None)  # Remove temporary type field
        
        if strike not in merged_options:
            merged_options[strike] = opt
        else:
            # Merge call and put data
            existing = merged_options[strike]
            for key in ['call_volume', 'call_oi', 'call_premium', 'put_volume', 'put_oi', 'put_premium']:
                if opt.get(key, 0) > 0:
                    existing[key] = opt[key]
    
    final_options = sorted(merged_options.values(), key=lambda x: x['strike'])
    logger.info(f"Extracted {len(final_options)} options from Shadow DOM")
    return final_options

def extract_from_javascript(html_content: str) -> List[Dict[str, Any]]:
    """Extract options data from JavaScript/JSON embedded in page"""
    options = []
    
    # Look for JSON data structures
    patterns = [
        r'"strike":\s*"?([0-9,]+\.?[0-9]*)"?[^}]*"lastPrice":\s*"?([0-9,]+\.?[0-9]*)"?',
        r'strike["\']:\s*["\']?([0-9,]+\.?[0-9]*)["\']?[^}]*lastPrice["\']:\s*["\']?([0-9,]+\.?[0-9]*)["\']?'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content)
        for match in matches:
            try:
                strike = float(match[0].replace(',', ''))
                premium = float(match[1].replace(',', ''))
                
                if 15000 <= strike <= 30000 and premium > 0:
                    options.append({
                        'strike': strike,
                        'call_volume': 0,
                        'call_oi': 0,
                        'call_premium': premium,  # Assume it's call premium
                        'put_volume': 0,
                        'put_oi': 0,
                        'put_premium': 0
                    })
            except:
                continue
    
    logger.info(f"Extracted {len(options)} options from JavaScript")
    return options

def extract_from_angular_data(html_content: str) -> List[Dict[str, Any]]:
    """Extract from Angular scope data if embedded"""
    options = []
    
    # Look for Angular data structures
    angular_patterns = [
        r'scope\.data\s*=\s*({.*?});',
        r'optionsData\s*:\s*(\[.*?\])',
        r'"calls":\s*(\[.*?\])',
        r'"puts":\s*(\[.*?\])'
    ]
    
    # This would require more sophisticated parsing
    # For now, return empty list
    logger.info(f"Extracted {len(options)} options from Angular data")
    return options

def find_latest_manual_html() -> Optional[str]:
    """Find the most recent manually saved HTML file"""
    html_dir = Path("data/html_snapshots")
    if not html_dir.exists():
        return None
    
    html_files = list(html_dir.glob("*.html"))
    if not html_files:
        return None
    
    # Sort by modification time, get most recent
    latest_file = max(html_files, key=lambda f: f.stat().st_mtime)
    logger.info(f"Found latest manual HTML: {latest_file}")
    return str(latest_file)

# Quick test function
if __name__ == "__main__":
    import sys
    
    # Test with the manual file
    manual_file = "/Users/Mike/trading/algos/EOD/data/html_snapshots/Nasdaq 100 E-Mini Jun '25 Futures Options Prices - Barchart.com.html"
    
    if len(sys.argv) > 1:
        manual_file = sys.argv[1]
    
    result = extract_from_manual_html(manual_file)
    
    if result["success"]:
        print(f"✅ Price: ${result['current_price']:,.2f}")
        print(f"✅ Options: {len(result['options_data'])} strikes")
        
        # Show first few options
        for i, opt in enumerate(result['options_data'][:5]):
            print(f"  Strike {opt['strike']:,.0f}: Call ${opt['call_premium']:.2f}, Put ${opt['put_premium']:.2f}")
    else:
        print(f"❌ Error: {result['error']}")