#!/usr/bin/env python3
"""
Direct HTML analysis tool for Barchart page debugging
Saves the page and analyzes structure to find the correct selectors
"""

import asyncio
import logging
from datetime import datetime
import sys
import os
import json
from pathlib import Path
from bs4 import BeautifulSoup
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.chrome_connection_manager import get_chrome_page, close_chrome_page
from utils.logging_config import setup_logging
from nq_options_ev_algo import get_current_contract_url

async def save_and_analyze_page():
    """Save current Barchart page and analyze its structure"""
    page = None
    
    try:
        # Setup logging
        log_dir, session_id = setup_logging()
        logger = logging.getLogger(__name__)
        
        # Create debug directory
        debug_dir = Path("data/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        # Get URL
        url = get_current_contract_url()
        logger.info(f"Analyzing page: {url}")
        
        # Get page from Chrome
        logger.info("Connecting to Chrome...")
        page = await get_chrome_page(9222)
        
        # Navigate to page
        logger.info("Navigating to Barchart...")
        await page.goto(url, waitUntil='networkidle2', timeout=30000)
        
        # Wait for page to settle
        await page.waitFor(3000)
        
        # Save HTML
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_content = await page.content()
        html_path = debug_dir / f"barchart_page_{timestamp}.html"
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"✅ Saved HTML to: {html_path}")
        
        # Analyze structure
        logger.info("🔍 Analyzing page structure...")
        analysis = analyze_page_structure(html_content)
        
        # Save analysis
        analysis_path = debug_dir / f"analysis_{timestamp}.json"
        with open(analysis_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        logger.info(f"✅ Saved analysis to: {analysis_path}")
        
        # Print summary
        print_analysis_summary(analysis)
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if page:
            await close_chrome_page(page)


def analyze_page_structure(html_content: str) -> dict:
    """Analyze HTML structure to find options data"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "price_elements": [],
        "table_elements": [],
        "angular_elements": [],
        "json_data": [],
        "scripts_with_data": [],
        "potential_selectors": {
            "price": [],
            "options": []
        }
    }
    
    # 1. Find price elements
    print("🔍 Looking for price elements...")
    
    # Look for elements with numbers that could be prices
    price_patterns = [
        r'\b2[01]\d{3}\.?\d*\b',  # 20000-21999 price range
        r'\b\d{1,3},\d{3}\.?\d*\b'  # Comma-separated numbers
    ]
    
    for element in soup.find_all(text=True):
        text = element.strip()
        for pattern in price_patterns:
            if re.search(pattern, text):
                parent = element.parent
                if parent:
                    analysis["price_elements"].append({
                        "text": text,
                        "tag": parent.name,
                        "class": parent.get('class', []),
                        "id": parent.get('id', ''),
                        "selector": get_css_selector(parent)
                    })
    
    # 2. Find all tables
    print("🔍 Looking for table elements...")
    tables = soup.find_all('table')
    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        headers = [th.text.strip() for th in table.find_all('th')]
        
        analysis["table_elements"].append({
            "index": i,
            "rows": len(rows),
            "headers": headers,
            "class": table.get('class', []),
            "id": table.get('id', ''),
            "selector": get_css_selector(table),
            "has_strike_header": any('strike' in h.lower() for h in headers),
            "has_call_put": any('call' in h.lower() or 'put' in h.lower() for h in headers)
        })
    
    # 3. Look for Angular bindings
    print("🔍 Looking for Angular elements...")
    angular_patterns = [
        r'\{\{[^}]+\}\}',  # Angular interpolation
        r'ng-[a-z-]+',     # Angular directives
        r'data-ng-[a-z-]+' # Angular data attributes
    ]
    
    for pattern in angular_patterns:
        matches = re.findall(pattern, html_content)
        if matches:
            analysis["angular_elements"].extend(matches)
    
    # 4. Look for JSON data in scripts
    print("🔍 Looking for JSON data in scripts...")
    scripts = soup.find_all('script')
    for i, script in enumerate(scripts):
        if script.string:
            # Look for option-related data
            if any(keyword in script.string.lower() for keyword in ['option', 'strike', 'call', 'put', 'lastprice']):
                analysis["scripts_with_data"].append({
                    "index": i,
                    "contains": [],
                    "snippet": script.string[:500] + "..." if len(script.string) > 500 else script.string
                })
                
                # Look for specific patterns
                if 'lastprice' in script.string.lower():
                    matches = re.findall(r'"lastPrice"[^,]+', script.string)
                    analysis["scripts_with_data"][-1]["contains"].extend(matches)
                
                if 'option' in script.string.lower():
                    analysis["scripts_with_data"][-1]["contains"].append("options data")
    
    # 5. Generate potential selectors
    analysis["potential_selectors"]["price"] = generate_price_selectors(analysis["price_elements"])
    analysis["potential_selectors"]["options"] = generate_options_selectors(analysis["table_elements"])
    
    return analysis


def get_css_selector(element):
    """Generate CSS selector for an element"""
    selectors = []
    
    # Add tag
    selectors.append(element.name)
    
    # Add ID if present
    if element.get('id'):
        return f"#{element.get('id')}"
    
    # Add classes
    classes = element.get('class', [])
    if classes:
        class_selector = '.' + '.'.join(classes)
        selectors.append(class_selector)
    
    return ' '.join(selectors) if len(selectors) > 1 else selectors[0]


def generate_price_selectors(price_elements):
    """Generate price selector suggestions"""
    selectors = []
    
    for elem in price_elements:
        selectors.append({
            "method": "css",
            "selector": elem["selector"],
            "confidence": "high" if any(keyword in str(elem["class"]).lower() 
                                      for keyword in ['price', 'last', 'quote']) else "medium"
        })
    
    return selectors


def generate_options_selectors(table_elements):
    """Generate options table selector suggestions"""
    selectors = []
    
    for table in table_elements:
        confidence = "low"
        if table["has_strike_header"] and table["has_call_put"]:
            confidence = "high"
        elif table["has_strike_header"] or table["has_call_put"]:
            confidence = "medium"
        
        selectors.append({
            "method": "css",
            "selector": table["selector"],
            "confidence": confidence,
            "rows": table["rows"],
            "headers": table["headers"]
        })
    
    return selectors


def print_analysis_summary(analysis):
    """Print a summary of the analysis"""
    print("\n" + "="*80)
    print("📊 BARCHART PAGE ANALYSIS SUMMARY")
    print("="*80)
    
    print(f"\n💰 Price Elements Found: {len(analysis['price_elements'])}")
    for elem in analysis['price_elements'][:5]:  # Show first 5
        print(f"  • {elem['text']} → {elem['selector']}")
    
    print(f"\n📋 Tables Found: {len(analysis['table_elements'])}")
    for table in analysis['table_elements']:
        confidence = "🔥" if table['has_strike_header'] and table['has_call_put'] else "🤔"
        print(f"  {confidence} {table['rows']} rows → {table['selector']}")
        if table['headers']:
            print(f"     Headers: {', '.join(table['headers'][:3])}...")
    
    print(f"\n🅰️ Angular Elements: {len(set(analysis['angular_elements']))}")
    for elem in list(set(analysis['angular_elements']))[:5]:
        print(f"  • {elem}")
    
    print(f"\n📜 Scripts with Data: {len(analysis['scripts_with_data'])}")
    for script in analysis['scripts_with_data']:
        print(f"  • Script {script['index']}: {', '.join(script['contains'])}")
    
    print(f"\n🎯 Recommended Selectors:")
    print(f"  Price selectors: {len(analysis['potential_selectors']['price'])}")
    for sel in analysis['potential_selectors']['price'][:3]:
        print(f"    {sel['confidence']}: {sel['selector']}")
    
    print(f"  Options selectors: {len(analysis['potential_selectors']['options'])}")
    for sel in analysis['potential_selectors']['options'][:3]:
        print(f"    {sel['confidence']}: {sel['selector']} ({sel['rows']} rows)")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    print("🚀 Starting Barchart page analysis...")
    print("Make sure Chrome is running with remote debugging on port 9222")
    print("The page should be loaded and ready at the Barchart options URL")
    print()
    
    asyncio.run(save_and_analyze_page())