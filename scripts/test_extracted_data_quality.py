#!/usr/bin/env python3
"""
Test Extracted Data Quality
Examine the actual extracted options data to verify completeness
"""

import asyncio
import logging
import json
from utils.feedback_loop_scraper import run_feedback_loop_scraper
from pyppeteer import launch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_data_quality():
    logger.info("🔍 Testing extracted data quality and completeness")
    
    # Launch browser
    browser = await launch({
        'headless': False,
        'args': ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    })
    
    page = await browser.newPage()
    await page.setViewport({'width': 1920, 'height': 1080})
    
    # Set user agent to avoid bot detection
    await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    try:
        # Run the feedback loop system
        url = 'https://www.barchart.com/futures/quotes/NQM25/options/MC6M25'
        results = await run_feedback_loop_scraper(page, url)
        
        if results['success']:
            options_data = results.get('options_data', [])
            logger.info(f"✅ Successfully extracted {len(options_data)} options")
            
            # Analyze the data quality
            logger.info("\n" + "="*60)
            logger.info("DETAILED DATA ANALYSIS")
            logger.info("="*60)
            
            # Group by strike price to see unique strikes
            strikes = {}
            for opt in options_data:
                strike = opt['strike']
                if strike not in strikes:
                    strikes[strike] = []
                strikes[strike].append(opt)
            
            logger.info(f"📊 Found {len(strikes)} unique strike prices:")
            
            for strike in sorted(strikes.keys()):
                options_for_strike = strikes[strike]
                logger.info(f"\n🎯 Strike {strike:,.0f}: {len(options_for_strike)} entries")
                
                for i, opt in enumerate(options_for_strike):
                    call_vol = opt.get('call_volume', 0)
                    call_oi = opt.get('call_oi', 0)
                    call_prem = opt.get('call_premium', 0)
                    put_vol = opt.get('put_volume', 0)
                    put_oi = opt.get('put_oi', 0)
                    put_prem = opt.get('put_premium', 0)
                    
                    logger.info(f"  Entry {i+1}:")
                    logger.info(f"    Calls:  Vol={call_vol:>6}, OI={call_oi:>6}, Premium=${call_prem:>6.2f}")
                    logger.info(f"    Puts:   Vol={put_vol:>6}, OI={put_oi:>6}, Premium=${put_prem:>6.2f}")
                    
                    if hasattr(opt, 'element_type'):
                        logger.info(f"    Source: {opt.get('element_type', '')}.{opt.get('element_classes', '')}")
            
            # Data quality analysis
            logger.info("\n" + "="*60)
            logger.info("DATA QUALITY ANALYSIS")
            logger.info("="*60)
            
            total_with_call_data = sum(1 for opt in options_data if opt.get('call_premium', 0) > 0 or opt.get('call_volume', 0) > 0)
            total_with_put_data = sum(1 for opt in options_data if opt.get('put_premium', 0) > 0 or opt.get('put_volume', 0) > 0)
            
            logger.info(f"📈 Entries with Call data: {total_with_call_data}/{len(options_data)} ({total_with_call_data/len(options_data)*100:.1f}%)")
            logger.info(f"📉 Entries with Put data:  {total_with_put_data}/{len(options_data)} ({total_with_put_data/len(options_data)*100:.1f}%)")
            
            # Check for duplicates
            strike_counts = {}
            for opt in options_data:
                strike = opt['strike']
                strike_counts[strike] = strike_counts.get(strike, 0) + 1
            
            duplicates = {s: c for s, c in strike_counts.items() if c > 1}
            if duplicates:
                logger.info(f"⚠️  Duplicate strikes found: {duplicates}")
            else:
                logger.info("✅ No duplicate strikes found")
            
            # Check strike price range
            if options_data:
                min_strike = min(opt['strike'] for opt in options_data)
                max_strike = max(opt['strike'] for opt in options_data)
                current_price = results.get('current_price', 0)
                
                logger.info(f"📊 Strike range: ${min_strike:,.0f} - ${max_strike:,.0f}")
                logger.info(f"💰 Current price: ${current_price:,.2f}")
                
                if current_price:
                    # Find ATM options
                    closest_strike = min(options_data, key=lambda opt: abs(opt['strike'] - current_price))['strike']
                    logger.info(f"🎯 Closest strike to current price: ${closest_strike:,.0f}")
            
            # Save detailed analysis
            analysis = {
                'total_options': len(options_data),
                'unique_strikes': len(strikes),
                'entries_with_call_data': total_with_call_data,
                'entries_with_put_data': total_with_put_data,
                'duplicates': duplicates,
                'strike_range': f"${min_strike:,.0f} - ${max_strike:,.0f}" if options_data else "N/A",
                'current_price': results.get('current_price', 0),
                'detailed_data': options_data
            }
            
            with open('data/debug/data_quality_analysis.json', 'w') as f:
                json.dump(analysis, f, indent=2)
            
            logger.info(f"\n📄 Detailed analysis saved to data/debug/data_quality_analysis.json")
            
        else:
            logger.error("❌ Feedback loop did not succeed")
            
    except Exception as e:
        logger.error(f"❌ Error in data quality test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_data_quality())