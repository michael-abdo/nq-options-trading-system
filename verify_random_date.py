#!/usr/bin/env python3
"""
Pick a random date and verify symbol generation is correct
"""

import random
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "tasks/options_trading_system/data_ingestion/barchart_web_scraper"))
from solution import BarchartAPIComparator
from robust_symbol_validator import RobustSymbolValidator

def main():
    # Pick a truly random date in 2025
    random.seed()  # Use system time for true randomness
    
    # Generate random date between now and end of 2025
    start_date = datetime.now()
    end_date = datetime(2025, 12, 31)
    days_range = (end_date - start_date).days
    
    random_days = random.randint(0, days_range)
    random_date = start_date + timedelta(days=random_days)
    
    print("🎲 RANDOM DATE VERIFICATION")
    print("="*80)
    print(f"\nRandomly selected date: {random_date.strftime('%Y-%m-%d %A')}")
    print(f"Day of month: {random_date.day}")
    print(f"Week of month: {(random_date.day - 1) // 7 + 1}")
    
    # Generate symbols using our logic
    validator = RobustSymbolValidator()
    
    print("\n📊 GENERATED SYMBOLS:")
    print("-"*40)
    
    # Generate all option types
    option_types = ["weekly", "friday", "monthly"]
    if random_date.weekday() == 4:  # Friday
        option_types.append("0dte")
    
    symbols = {}
    for option_type in option_types:
        symbol, expiry = validator.generate_symbol_for_date(random_date, option_type)
        symbols[option_type] = (symbol, expiry)
        
        # Calculate days to expiration
        days_to_exp = (expiry - random_date).days
        
        print(f"\n{option_type.upper()}:")
        print(f"  Symbol: {symbol}")
        print(f"  Expires: {expiry.strftime('%Y-%m-%d %A')}")
        print(f"  Days to expiration: {days_to_exp}")
        
        # Decode the symbol
        if len(symbol) >= 4:
            prefix = symbol[:2]
            week = symbol[2]
            month = symbol[3]
            year = symbol[4:]
            
            month_names = {
                'F': 'January', 'G': 'February', 'H': 'March', 'J': 'April',
                'K': 'May', 'M': 'June', 'N': 'July', 'Q': 'August',
                'U': 'September', 'V': 'October', 'X': 'November', 'Z': 'December'
            }
            
            print(f"  Decoded: {prefix} (prefix), Week {week}, {month_names.get(month, month)} ({month}), 20{year}")
    
    # Special validation for Fridays
    if random_date.weekday() == 4:
        print("\n✅ FRIDAY VALIDATION:")
        if symbols['friday'][0] == symbols['0dte'][0]:
            print("  ✅ Friday = 0DTE: CONFIRMED!")
        else:
            print("  ❌ Friday != 0DTE: ERROR!")
    
    # Create Puppeteer validation script
    print("\n🔍 CREATING VALIDATION SCRIPT...")
    
    # Pick one symbol to validate
    test_type = "friday" if "friday" in symbols else "weekly"
    test_symbol, test_expiry = symbols[test_type]
    
    script_content = f'''
const puppeteer = require('puppeteer');

(async () => {{
    console.log('🔍 Validating {test_symbol} for {random_date.strftime("%Y-%m-%d")}...');
    
    const browser = await puppeteer.launch({{
        headless: false,  // Show browser for verification
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }});
    
    const page = await browser.newPage();
    
    try {{
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36');
        
        const url = 'https://www.barchart.com/futures/quotes/NQU25/options/{test_symbol}?futuresOptionsView=merged';
        console.log('Navigating to:', url);
        
        await page.goto(url, {{ waitUntil: 'networkidle2', timeout: 30000 }});
        
        // Wait for page to load
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Try to find expiration info
        const pageText = await page.evaluate(() => document.body.innerText);
        
        // Look for expiration pattern
        const expirationMatch = pageText.match(/(\\d+)\\s+Days?\\s+to\\s+expiration\\s+on\\s+([\\d\\/]+)/i);
        
        if (expirationMatch) {{
            console.log('✅ Found expiration info:');
            console.log('   Days to expiration:', expirationMatch[1]);
            console.log('   Expiration date:', expirationMatch[2]);
            console.log('   Expected date: {test_expiry.strftime("%m/%d/%y")}');
            
            if (expirationMatch[2].includes('{test_expiry.strftime("%m/%d/%y")}') || 
                expirationMatch[2].includes('{test_expiry.strftime("%m/%d/%Y")}')) {{
                console.log('   ✅ DATE MATCHES! Symbol is correct.');
            }} else {{
                console.log('   ❌ Date mismatch!');
            }}
        }} else {{
            console.log('❌ Could not find expiration info on page');
            console.log('This might mean the symbol does not exist');
        }}
        
        // Take screenshot
        await page.screenshot({{ path: 'random_date_validation.png', fullPage: true }});
        console.log('📸 Screenshot saved as random_date_validation.png');
        
        // Keep browser open for manual verification
        console.log('\\n👀 Browser will stay open for 10 seconds for manual verification...');
        await new Promise(resolve => setTimeout(resolve, 10000));
        
    }} catch (error) {{
        console.error('Error:', error.message);
    }} finally {{
        await browser.close();
    }}
}})();
'''
    
    script_file = f"validate_{test_symbol}_random.js"
    with open(script_file, 'w') as f:
        f.write(script_content)
    
    print(f"✅ Created validation script: {script_file}")
    print(f"\nTo verify this random date:")
    print(f"1. Run: node {script_file}")
    print(f"2. The browser will open and show the Barchart page")
    print(f"3. Check if the expiration date matches: {test_expiry.strftime('%m/%d/%y')}")
    
    # Also test with our pipeline
    print(f"\n🚀 TESTING WITH PIPELINE...")
    print(f"If today was {random_date.strftime('%Y-%m-%d')}, the pipeline would generate:")
    
    # Show what the actual comparator would generate
    comp = BarchartAPIComparator()
    current_weekly = comp.get_eod_contract_symbol(option_type="weekly")
    current_friday = comp.get_eod_contract_symbol(option_type="friday")
    
    print(f"\nCurrent symbols (today {datetime.now().strftime('%Y-%m-%d')}):")
    print(f"  Weekly: {current_weekly}")
    print(f"  Friday: {current_friday}")

if __name__ == "__main__":
    main()