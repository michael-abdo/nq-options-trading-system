#!/usr/bin/env python3
"""
Test script to analyze Barchart HTML response
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

def test_barchart_scrape():
    # Generate URL
    url = "https://www.barchart.com/futures/quotes/NQM25/options/MC6M25?futuresOptionsView=merged"
    print(f"Testing URL: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    response = requests.get(url, headers=headers)
    print(f"Response status: {response.status_code}")
    print(f"Response length: {len(response.text)} bytes")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Look for current price
    print("\n--- Current Price Search ---")
    
    # Method 1: Script tags
    scripts = soup.find_all('script')
    print(f"Found {len(scripts)} script tags")
    
    for i, script in enumerate(scripts):
        if script.string and 'lastPrice' in script.string:
            matches = re.findall(r'"lastPrice":\s*"?([\d,\.]+)"?', script.string)
            if matches:
                print(f"Script {i}: Found lastPrice matches: {matches}")
    
    # Method 2: Look for price elements
    price_classes = ['last-change', 'last-price', 'price', 'quote-price']
    for cls in price_classes:
        elems = soup.find_all(class_=cls)
        if elems:
            print(f"Found {len(elems)} elements with class '{cls}'")
            for elem in elems[:3]:  # Show first 3
                print(f"  Text: {elem.text.strip()}")
    
    # Look for options data
    print("\n--- Options Data Search ---")
    
    # Method 1: Tables
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        # Check if table might contain options data
        table_text = table.text.lower()
        if any(word in table_text for word in ['strike', 'call', 'put', 'bid', 'ask', 'volume']):
            print(f"\nTable {i} appears to contain options data")
            rows = table.find_all('tr')
            print(f"  Rows: {len(rows)}")
            
            # Show first few rows
            for j, row in enumerate(rows[:3]):
                cells = row.find_all(['td', 'th'])
                cell_texts = [cell.text.strip() for cell in cells]
                print(f"  Row {j}: {cell_texts}")
    
    # Method 2: Look for divs with data attributes
    print("\n--- Data Attributes Search ---")
    data_divs = soup.find_all('div', attrs={'data-ng-repeat': True})
    print(f"Found {len(data_divs)} divs with data-ng-repeat")
    
    # Method 3: Look for specific classes
    option_classes = ['options-table', 'bc-table', 'data-table', 'futures-options']
    for cls in option_classes:
        elems = soup.find_all(class_=re.compile(cls))
        if elems:
            print(f"Found {len(elems)} elements with class containing '{cls}'")
    
    # Method 4: Look for JSON data in scripts
    print("\n--- JSON Data Search ---")
    for i, script in enumerate(scripts):
        if script.string:
            # Look for JSON patterns
            if 'optionsData' in script.string or 'tableData' in script.string:
                print(f"Script {i} contains options/table data")
                # Try to extract JSON
                json_matches = re.findall(r'\{[^{}]*"strike"[^{}]*\}', script.string)
                if json_matches:
                    print(f"  Found {len(json_matches)} potential strike JSON objects")
    
    # Save a sample of the HTML for manual inspection
    with open('barchart_response_sample.html', 'w') as f:
        f.write(response.text[:50000])  # First 50K chars
    print("\nSaved first 50K chars of response to 'barchart_response_sample.html'")
    
    # Check if we might be getting a different page
    if 'angular' in response.text.lower() or 'ng-' in response.text:
        print("\n⚠️  Page appears to use Angular - data might be loaded dynamically")
    
    if 'cloudflare' in response.text.lower():
        print("\n⚠️  Cloudflare detected - might be getting a challenge page")
    
    if 'recaptcha' in response.text.lower():
        print("\n⚠️  reCAPTCHA detected - might need to solve captcha")

if __name__ == "__main__":
    test_barchart_scrape()