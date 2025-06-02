#!/usr/bin/env python3
"""
Extract from Working HTML
Parse the HTML file that contains the complete options data to reverse engineer where it's stored
"""

import re
from bs4 import BeautifulSoup
import json

def extract_from_working_html():
    print("🔍 Extracting options data from working HTML file...")
    
    # Read the HTML file that has the complete options table
    with open("/Users/Mike/trading/algos/EOD/data/debug/page_20250602_131625.html", 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    print(f"📄 HTML file size: {len(html_content):,} characters")
    
    # Method 1: Look for JavaScript data/JSON containing options
    print("\n🔍 METHOD 1: Searching for JavaScript data...")
    
    # Find all script tags
    scripts = soup.find_all('script')
    print(f"Found {len(scripts)} script tags")
    
    options_data_found = []
    
    for i, script in enumerate(scripts):
        if script.string:
            script_content = script.string
            
            # Look for JSON-like data with strike prices
            if "21" in script_content and any(term in script_content.lower() for term in ['option', 'call', 'put', 'strike']):
                # Look for strike prices in expected range
                strike_matches = re.findall(r'21[45]\d{2}(?:\.\d{2})?', script_content)
                if len(strike_matches) >= 3:
                    print(f"  Script {i}: Found {len(strike_matches)} potential strikes")
                    print(f"    Sample strikes: {strike_matches[:5]}")
                    
                    # Try to extract JSON objects
                    json_patterns = [
                        r'\{[^{}]*?21[45]\d{2}[^{}]*?\}',  # Simple objects
                        r'\[[^\[\]]*?21[45]\d{2}[^\[\]]*?\]',  # Arrays
                        r'"data":\s*(\[[^\]]+\])',  # data arrays
                        r'"options":\s*(\[[^\]]+\])',  # options arrays
                        r'"calls":\s*(\[[^\]]+\])',  # calls arrays
                        r'"puts":\s*(\[[^\]]+\])',  # puts arrays
                    ]
                    
                    for pattern in json_patterns:
                        matches = re.findall(pattern, script_content)
                        if matches:
                            print(f"    Found JSON pattern: {pattern[:30]}... ({len(matches)} matches)")
                            for match in matches[:2]:  # Show first 2 matches
                                print(f"      {match[:200]}...")
                    
                    # Store for further analysis
                    options_data_found.append({
                        'script_index': i,
                        'strikes_count': len(strike_matches),
                        'strikes': strike_matches[:10],
                        'content_preview': script_content[:500]
                    })
    
    # Method 2: Look for Angular data in script content
    print("\n🔍 METHOD 2: Searching for Angular scope data...")
    
    for i, script in enumerate(scripts):
        if script.string and 'angular' in script.string.lower():
            script_content = script.string
            
            # Look for scope data patterns
            angular_patterns = [
                r'scope\.data\s*=\s*(\{[^;]+\})',
                r'"futuresOptionsQuotes"[^}]*data[^}]*(\{[^}]+\})',
                r'data\.calls\s*=\s*(\[[^\]]+\])',
                r'data\.puts\s*=\s*(\[[^\]]+\])',
            ]
            
            for pattern in angular_patterns:
                matches = re.findall(pattern, script_content)
                if matches:
                    print(f"  Script {i}: Found Angular pattern: {pattern[:40]}...")
                    for match in matches[:1]:
                        print(f"    {match[:300]}...")
    
    # Method 3: Look for data attributes or hidden elements
    print("\n🔍 METHOD 3: Searching for data attributes and hidden elements...")
    
    # Look for elements with data-* attributes
    data_elements = soup.find_all(attrs=lambda x: x and any(attr.startswith('data-') for attr in x.keys()))
    print(f"Found {len(data_elements)} elements with data attributes")
    
    for elem in data_elements[:10]:
        for attr, value in elem.attrs.items():
            if attr.startswith('data-') and '21' in str(value):
                print(f"  {elem.name}.{attr} = {str(value)[:100]}...")
    
    # Look for hidden inputs or elements that might contain data
    hidden_elements = soup.find_all(['input', 'script'], type='hidden') + \
                     soup.find_all(style=re.compile(r'display:\s*none', re.I))
    
    print(f"Found {len(hidden_elements)} hidden elements")
    
    for elem in hidden_elements:
        if elem.get_text() and '21' in elem.get_text():
            strikes = re.findall(r'21[45]\d{2}(?:\.\d{2})?', elem.get_text())
            if strikes:
                print(f"  Hidden {elem.name}: {len(strikes)} strikes - {strikes[:3]}")
    
    # Method 4: Search for specific text patterns that might be data
    print("\n🔍 METHOD 4: Text pattern analysis...")
    
    # Look for tabular data patterns (multiple strikes with numbers)
    text_content = soup.get_text()
    
    # Find lines with multiple numbers that could be options data
    lines = text_content.split('\n')
    potential_data_lines = []
    
    for line_num, line in enumerate(lines):
        # Look for lines with strikes and multiple numbers
        if re.search(r'21[45]\d{2}', line):
            numbers = re.findall(r'\b\d+(?:\.\d{2})?\b', line)
            if len(numbers) >= 5:  # Strike + at least 4 other numbers
                potential_data_lines.append({
                    'line_number': line_num,
                    'content': line.strip(),
                    'numbers_count': len(numbers),
                    'numbers': numbers[:10]
                })
    
    print(f"Found {len(potential_data_lines)} potential data lines")
    
    for line in potential_data_lines[:5]:
        print(f"  Line {line['line_number']}: {line['numbers_count']} numbers")
        print(f"    Numbers: {line['numbers']}")
        print(f"    Content: {line['content'][:100]}...")
    
    # Method 5: Look for specific Barchart table structures
    print("\n🔍 METHOD 5: Barchart-specific structures...")
    
    # Look for bc-datatable or futures-options specific elements
    bc_elements = soup.find_all(class_=re.compile(r'bc-|futures|options|table', re.I))
    print(f"Found {len(bc_elements)} Barchart-specific elements")
    
    for elem in bc_elements[:10]:
        if elem.get_text() and '21' in elem.get_text():
            strikes = re.findall(r'21[45]\d{2}(?:\.\d{2})?', elem.get_text())
            if strikes:
                print(f"  {elem.name}.{elem.get('class', [])} : {len(strikes)} strikes")
    
    # Method 6: Search for the actual options table based on known structure
    print("\n🔍 METHOD 6: Known options table structure search...")
    
    # Look for table headers that match options tables
    table_headers = ['Strike', 'Call', 'Put', 'Volume', 'Open Int', 'Last', 'Bid', 'Ask']
    
    # Find elements containing these headers
    for header in table_headers:
        elements = soup.find_all(text=re.compile(header, re.I))
        if elements:
            print(f"  Found '{header}' in {len(elements)} elements")
            for elem in elements[:2]:
                parent = elem.parent
                if parent:
                    print(f"    In {parent.name}.{parent.get('class', [])} : {parent.get_text()[:100]}...")
    
    # Summary
    print(f"\n📊 ANALYSIS SUMMARY:")
    print(f"  Scripts with potential options data: {len(options_data_found)}")
    print(f"  Potential data lines found: {len(potential_data_lines)}")
    print(f"  BC-specific elements: {len(bc_elements)}")
    
    if options_data_found:
        print(f"\n🎯 MOST PROMISING: Script {options_data_found[0]['script_index']} with {options_data_found[0]['strikes_count']} strikes")
        return options_data_found[0]
    elif potential_data_lines:
        print(f"\n🎯 ALTERNATIVE: Data line {potential_data_lines[0]['line_number']} with {potential_data_lines[0]['numbers_count']} numbers")
        return potential_data_lines[0]
    else:
        print(f"\n❌ No obvious options data structure found")
        return None

if __name__ == '__main__':
    result = extract_from_working_html()
    
    if result:
        print(f"\n✅ Found potential options data location!")
        print(f"📍 Location details: {result}")
    else:
        print(f"\n❌ Could not locate options data in the HTML")
        print("The data might be loaded dynamically after page load or through AJAX")