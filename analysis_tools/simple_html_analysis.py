#!/usr/bin/env python3
"""
Simple HTML Analysis
Find where the options data is stored in the working HTML file
"""

import re
from bs4 import BeautifulSoup

def analyze_working_html():
    print("🔍 Analyzing working HTML file for options data...")
    
    # Read the HTML file that has the complete options table
    with open("/Users/Mike/trading/algos/EOD/data/debug/page_20250602_131625.html", 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    print(f"📄 HTML file size: {len(html_content):,} characters")
    
    # Method 1: Search for multiple strike prices close together
    print("\n🔍 METHOD 1: Looking for strike price clusters...")
    
    # Find all strike prices in the expected range
    all_strikes = re.findall(r'21[45]\d{2}(?:\.\d{2})?', html_content)
    unique_strikes = list(set(all_strikes))
    unique_strikes.sort()
    
    print(f"Found {len(all_strikes)} total strike price mentions")
    print(f"Found {len(unique_strikes)} unique strikes: {unique_strikes[:10]}")
    
    # Method 2: Look for JSON data with multiple strikes
    print("\n🔍 METHOD 2: Searching for JSON data with options...")
    
    # Look for potential JSON arrays/objects
    json_patterns = [
        r'\[[^\[\]]*21[45]\d{2}[^\[\]]*\]',  # Arrays containing strikes
        r'\{[^{}]*21[45]\d{2}[^{}]*\}',      # Objects containing strikes
    ]
    
    for i, pattern in enumerate(json_patterns):
        matches = re.findall(pattern, html_content)
        print(f"Pattern {i+1}: Found {len(matches)} potential JSON structures")
        
        # Show matches with multiple strikes
        for match in matches:
            strikes_in_match = re.findall(r'21[45]\d{2}(?:\.\d{2})?', match)
            if len(strikes_in_match) >= 3:
                print(f"  Match with {len(strikes_in_match)} strikes: {match[:200]}...")
    
    # Method 3: Look for table-like text patterns
    print("\n🔍 METHOD 3: Looking for table-like patterns...")
    
    # Split into lines and look for lines with multiple numbers including strikes
    lines = html_content.split('\n')
    data_lines = []
    
    for line_num, line in enumerate(lines):
        if re.search(r'21[45]\d{2}', line):
            # Count numbers in this line
            numbers = re.findall(r'\b\d+(?:\.\d{2})?\b', line)
            if len(numbers) >= 6:  # Strike + at least 5 other numbers
                data_lines.append({
                    'line': line_num,
                    'numbers': len(numbers),
                    'content': line.strip()[:150]
                })
    
    print(f"Found {len(data_lines)} lines with strikes and multiple numbers")
    
    for data_line in data_lines[:5]:
        print(f"  Line {data_line['line']}: {data_line['numbers']} numbers")
        print(f"    {data_line['content']}")
    
    # Method 4: Search for specific options table keywords near strikes
    print("\n🔍 METHOD 4: Context analysis around strikes...")
    
    # Look for text around strike prices that might indicate table structure
    keywords = ['Call', 'Put', 'Volume', 'Last', 'Bid', 'Ask', 'Strike', 'Open Interest']
    
    for strike in unique_strikes[:5]:
        # Find positions of this strike in the HTML
        positions = [m.start() for m in re.finditer(re.escape(strike), html_content)]
        
        for pos in positions[:2]:  # Check first 2 occurrences
            # Get context around this strike
            start = max(0, pos - 200)
            end = min(len(html_content), pos + 200)
            context = html_content[start:end]
            
            # Count how many keywords appear in this context
            keyword_count = sum(1 for keyword in keywords if keyword.lower() in context.lower())
            
            if keyword_count >= 3:
                print(f"  Strike {strike} at position {pos}: {keyword_count} keywords nearby")
                print(f"    Context: {context[:100]}...")
    
    # Method 5: Look for the largest concentration of strike prices
    print("\n🔍 METHOD 5: Finding strike price concentration...")
    
    # Divide HTML into chunks and count strikes in each
    chunk_size = 5000
    chunks = []
    
    for i in range(0, len(html_content), chunk_size):
        chunk = html_content[i:i+chunk_size]
        strikes_in_chunk = len(re.findall(r'21[45]\d{2}(?:\.\d{2})?', chunk))
        if strikes_in_chunk > 0:
            chunks.append({
                'start': i,
                'end': i + chunk_size,
                'strikes': strikes_in_chunk,
                'preview': chunk[:200].replace('\n', ' ')
            })
    
    # Sort by strike count
    chunks.sort(key=lambda x: x['strikes'], reverse=True)
    
    print(f"Top 5 chunks with most strikes:")
    for chunk in chunks[:5]:
        print(f"  Position {chunk['start']:,}-{chunk['end']:,}: {chunk['strikes']} strikes")
        print(f"    Preview: {chunk['preview']}")
    
    # Method 6: Extract the exact data from the best chunk
    if chunks:
        best_chunk = chunks[0]
        print(f"\n🎯 EXTRACTING FROM BEST CHUNK (position {best_chunk['start']:,})...")
        
        chunk_text = html_content[best_chunk['start']:best_chunk['end']]
        
        # Try to parse this chunk for structured data
        soup = BeautifulSoup(chunk_text, 'html.parser')
        
        # Look for any table-like structures
        tables = soup.find_all(['table', 'div', 'span'])
        for table in tables[:3]:
            table_text = table.get_text()
            strikes = re.findall(r'21[45]\d{2}(?:\.\d{2})?', table_text)
            if len(strikes) >= 3:
                print(f"  Found element {table.name} with {len(strikes)} strikes")
                print(f"    Classes: {table.get('class', [])}")
                print(f"    Text preview: {table_text[:200]}")
        
        return {
            'best_chunk_start': best_chunk['start'],
            'best_chunk_end': best_chunk['end'],
            'strikes_in_chunk': best_chunk['strikes'],
            'total_unique_strikes': len(unique_strikes),
            'unique_strikes': unique_strikes
        }
    
    return None

if __name__ == '__main__':
    result = analyze_working_html()
    
    if result:
        print(f"\n✅ ANALYSIS COMPLETE!")
        print(f"🎯 Best data location: positions {result['best_chunk_start']:,} - {result['best_chunk_end']:,}")
        print(f"📊 Found {result['strikes_in_chunk']} strikes in best chunk")
        print(f"📈 Total unique strikes: {result['total_unique_strikes']}")
        print(f"💰 Strike range: {result['unique_strikes'][0]} - {result['unique_strikes'][-1]}")
    else:
        print(f"\n❌ Could not identify clear data structure")