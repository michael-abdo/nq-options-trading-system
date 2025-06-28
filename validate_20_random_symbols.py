#!/usr/bin/env python3
"""
Validate 20 random symbols with detailed logging
A lighter version for quicker results
"""

import json
import random
import os
from datetime import datetime, timedelta
import sys
from pathlib import Path
import logging

sys.path.append(str(Path(__file__).parent / "tasks/options_trading_system/data_ingestion/barchart_web_scraper"))
from robust_symbol_validator import RobustSymbolValidator

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('validation_20_detailed.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_symbols_batch():
    """Test a batch of random dates"""
    
    validator = RobustSymbolValidator()
    results = []
    
    logger.info("🚀 VALIDATING 20 RANDOM DATES")
    logger.info("="*80)
    
    # Generate 20 random dates in next 3 months
    start_date = datetime.now()
    end_date = start_date + timedelta(days=90)
    date_range = (end_date - start_date).days
    
    # Statistics
    stats = {
        'total_tests': 0,
        'by_type': {
            'weekly': {'total': 0, 'correct_prefix': 0, 'correct_weekday': 0},
            'friday': {'total': 0, 'correct_prefix': 0, 'correct_weekday': 0},
            '0dte': {'total': 0, 'matches_friday': 0},
            'monthly': {'total': 0, 'correct_prefix': 0, 'correct_weekday': 0}
        }
    }
    
    for i in range(1, 21):
        # Generate random date
        random_days = random.randint(0, date_range)
        test_date = start_date + timedelta(days=random_days)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST {i}: {test_date.strftime('%Y-%m-%d %A')}")
        logger.info(f"{'='*60}")
        
        date_result = {
            'test_num': i,
            'test_date': test_date.strftime('%Y-%m-%d'),
            'weekday': test_date.strftime('%A'),
            'symbols': {}
        }
        
        # Test each option type
        option_types = ['weekly', 'friday', 'monthly']
        if test_date.weekday() == 4:  # Friday
            option_types.append('0dte')
        
        for option_type in option_types:
            try:
                symbol, expiry_date = validator.generate_symbol_for_date(test_date, option_type)
                days_to_expiry = (expiry_date - test_date).days
                
                logger.info(f"\n{option_type.upper()}:")
                logger.info(f"  Symbol: {symbol}")
                logger.info(f"  Expires: {expiry_date.strftime('%Y-%m-%d %A')}")
                logger.info(f"  Days to expiry: {days_to_expiry}")
                
                # Validate the symbol
                validations = []
                
                # Check prefix
                if option_type in ['weekly', 'monthly']:
                    if symbol.startswith('MM'):
                        validations.append("✅ Prefix MM correct")
                        stats['by_type'][option_type]['correct_prefix'] += 1
                    else:
                        validations.append(f"❌ Wrong prefix: {symbol[:2]}")
                elif option_type in ['friday', '0dte']:
                    if symbol.startswith('MQ'):
                        validations.append("✅ Prefix MQ correct")
                        stats['by_type'][option_type]['correct_prefix'] += 1
                    else:
                        validations.append(f"❌ Wrong prefix: {symbol[:2]}")
                
                # Check expiration day of week
                if option_type == 'weekly' and expiry_date.weekday() == 1:  # Tuesday
                    validations.append("✅ Expires on Tuesday")
                    stats['by_type'][option_type]['correct_weekday'] += 1
                elif option_type in ['friday', '0dte'] and expiry_date.weekday() == 4:  # Friday
                    validations.append("✅ Expires on Friday")
                    stats['by_type'][option_type]['correct_weekday'] += 1
                elif option_type == 'monthly' and expiry_date.weekday() == 3:  # Thursday
                    validations.append("✅ Expires on Thursday")
                    stats['by_type'][option_type]['correct_weekday'] += 1
                else:
                    validations.append(f"❌ Wrong expiry day: {expiry_date.strftime('%A')}")
                
                # Check week number
                if len(symbol) >= 3 and symbol[2].isdigit():
                    week_num = int(symbol[2])
                    if 1 <= week_num <= 5:
                        validations.append(f"✅ Week number {week_num} valid")
                    else:
                        validations.append(f"❌ Invalid week number: {week_num}")
                
                # Log validations
                for v in validations:
                    logger.info(f"  {v}")
                
                date_result['symbols'][option_type] = {
                    'symbol': symbol,
                    'expiry': expiry_date.strftime('%Y-%m-%d'),
                    'validations': validations
                }
                
                stats['by_type'][option_type]['total'] += 1
                
            except Exception as e:
                logger.error(f"  ERROR: {e}")
                date_result['symbols'][option_type] = {'error': str(e)}
        
        # Special Friday validation
        if test_date.weekday() == 4:  # Friday
            friday_sym = date_result['symbols'].get('friday', {}).get('symbol')
            dte_sym = date_result['symbols'].get('0dte', {}).get('symbol')
            
            if friday_sym and dte_sym:
                if friday_sym == dte_sym:
                    logger.info("\n✅ Friday = 0DTE: CONFIRMED")
                    stats['by_type']['0dte']['matches_friday'] += 1
                else:
                    logger.error(f"\n❌ Friday ({friday_sym}) != 0DTE ({dte_sym})")
        
        results.append(date_result)
        stats['total_tests'] += 1
    
    # Print summary
    logger.info("\n" + "="*80)
    logger.info("📊 VALIDATION SUMMARY")
    logger.info("="*80)
    
    logger.info(f"\nTotal tests: {stats['total_tests']}")
    
    for option_type, type_stats in stats['by_type'].items():
        if type_stats['total'] > 0:
            logger.info(f"\n{option_type.upper()}:")
            logger.info(f"  Total tested: {type_stats['total']}")
            
            if 'correct_prefix' in type_stats:
                prefix_rate = (type_stats['correct_prefix'] / type_stats['total']) * 100
                logger.info(f"  Correct prefix: {type_stats['correct_prefix']}/{type_stats['total']} ({prefix_rate:.0f}%)")
            
            if 'correct_weekday' in type_stats:
                weekday_rate = (type_stats['correct_weekday'] / type_stats['total']) * 100
                logger.info(f"  Correct weekday: {type_stats['correct_weekday']}/{type_stats['total']} ({weekday_rate:.0f}%)")
            
            if option_type == '0dte' and 'matches_friday' in type_stats:
                logger.info(f"  Matches Friday: {type_stats['matches_friday']}/{type_stats['total']}")
    
    # Save results
    with open('validation_20_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'statistics': stats,
            'results': results
        }, f, indent=2)
    
    logger.info(f"\n📁 Results saved to: validation_20_results.json")
    logger.info(f"📁 Detailed log saved to: validation_20_detailed.log")
    
    # Create validation scripts for manual checking
    logger.info(f"\n🔍 Creating Puppeteer scripts for manual validation...")
    
    # Pick 5 random results to create scripts for
    sample_results = random.sample(results, min(5, len(results)))
    
    for result in sample_results:
        test_date = datetime.strptime(result['test_date'], '%Y-%m-%d')
        
        # Create script for Friday or Weekly
        option_type = 'friday' if 'friday' in result['symbols'] else 'weekly'
        if option_type in result['symbols']:
            symbol_info = result['symbols'][option_type]
            if 'symbol' in symbol_info:
                symbol = symbol_info['symbol']
                expiry = symbol_info['expiry']
                
                script = f'''const puppeteer = require('puppeteer');

(async () => {{
    console.log('Validating {symbol} (generated for {result["test_date"]})');
    
    const browser = await puppeteer.launch({{
        headless: false,
        args: ['--no-sandbox']
    }});
    
    const page = await browser.newPage();
    
    try {{
        const url = 'https://www.barchart.com/futures/quotes/NQU25/options/{symbol}?futuresOptionsView=merged';
        console.log('URL:', url);
        
        await page.goto(url, {{ waitUntil: 'networkidle2', timeout: 30000 }});
        await page.waitForTimeout(3000);
        
        const pageText = await page.evaluate(() => document.body.innerText);
        const expirationMatch = pageText.match(/(\\d+)\\s+Days?\\s+to\\s+expiration\\s+on\\s+([\\d\\/]+)/i);
        
        if (expirationMatch) {{
            console.log('✅ Found:', expirationMatch[0]);
            console.log('Expected expiry: {expiry}');
        }} else {{
            console.log('❌ No expiration info found');
        }}
        
        console.log('\\nBrowser will close in 10 seconds...');
        await page.waitForTimeout(10000);
        
    }} catch (error) {{
        console.error('Error:', error.message);
    }} finally {{
        await browser.close();
    }}
}})();'''
                
                script_name = f'manual_check_{symbol}.js'
                with open(script_name, 'w') as f:
                    f.write(script)
                
                logger.info(f"  Created: {script_name}")

if __name__ == "__main__":
    test_symbols_batch()