#!/usr/bin/env python3
"""
Test Tomorrow's Options Data
Check if tomorrow's expiration has live bid/ask data vs delayed data
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pyppeteer import launch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_tomorrow_data():
    logger.info("🔍 Testing tomorrow's options data for live bid/ask...")
    
    # Launch browser
    browser = await launch({
        'headless': False,
        'args': ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    })
    
    page = await browser.newPage()
    await page.setViewport({'width': 1920, 'height': 1080})
    await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    # Storage for API responses
    api_responses = []
    
    # Monitor API requests
    await page.setRequestInterception(True)
    
    def log_request(request):
        # Continue all requests
        asyncio.create_task(request.continue_())
    
    def log_response(response):
        # Capture options API responses
        if ('proxies/core-api' in response.url and 'quotes/get' in response.url and 
            'futures.options' in response.url):
            logger.info(f"📡 Captured options API: {response.url}")
            asyncio.create_task(analyze_options_response(response))
    
    async def analyze_options_response(response):
        try:
            body = await response.text()
            data = json.loads(body)
            
            # Extract symbol from URL
            symbol = "Unknown"
            if 'symbol=' in response.url:
                symbol = response.url.split('symbol=')[1].split('&')[0]
            
            # Analyze data quality
            total_options = 0
            live_bid_ask = 0
            live_volume = 0
            strike_range = []
            
            def analyze_option_data(options_list, option_type):
                nonlocal total_options, live_bid_ask, live_volume, strike_range
                
                if not options_list:
                    return
                    
                for option in options_list:
                    total_options += 1
                    
                    # Extract strike price
                    if 'strike' in option:
                        try:
                            strike_str = str(option['strike']).replace(',', '').replace('C', '').replace('P', '')
                            strike = float(strike_str)
                            if 15000 <= strike <= 30000:  # Valid NQ range
                                strike_range.append(strike)
                        except:
                            pass
                    
                    # Check for live bid/ask
                    bid = option.get('bidPrice', 'N/A')
                    ask = option.get('askPrice', 'N/A')
                    volume = option.get('volume', 'N/A')
                    
                    if bid and ask and bid != 'N/A' and ask != 'N/A':
                        try:
                            bid_val = float(str(bid).replace(',', ''))
                            ask_val = float(str(ask).replace(',', ''))
                            if bid_val > 0 and ask_val > 0:
                                live_bid_ask += 1
                        except:
                            pass
                    
                    if volume and volume != 'N/A':
                        try:
                            vol_val = int(str(volume).replace(',', ''))
                            if vol_val > 0:
                                live_volume += 1
                        except:
                            pass
            
            # Analyze calls and puts
            if 'data' in data:
                if 'Call' in data['data']:
                    analyze_option_data(data['data']['Call'], 'Call')
                if 'Put' in data['data']:
                    analyze_option_data(data['data']['Put'], 'Put')
            
            # Calculate quality metrics
            bid_ask_quality = (live_bid_ask / total_options * 100) if total_options > 0 else 0
            volume_quality = (live_volume / total_options * 100) if total_options > 0 else 0
            
            # Get strike range
            if strike_range:
                strike_range.sort()
                min_strike = strike_range[0]
                max_strike = strike_range[-1]
                liquid_strikes = len([s for s in strike_range if 21000 <= s <= 22000])
            else:
                min_strike = max_strike = liquid_strikes = 0
            
            analysis = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'url': response.url,
                'total_options': total_options,
                'live_bid_ask': live_bid_ask,
                'live_volume': live_volume,
                'bid_ask_quality': bid_ask_quality,
                'volume_quality': volume_quality,
                'strike_range': f"{min_strike:.0f} - {max_strike:.0f}" if strike_range else "None",
                'liquid_strikes_count': liquid_strikes,
                'sample_data': []
            }
            
            # Get sample data
            if 'data' in data and 'Call' in data['data']:
                for option in data['data']['Call'][:5]:  # First 5 calls
                    analysis['sample_data'].append({
                        'strike': option.get('strike', 'N/A'),
                        'bid': option.get('bidPrice', 'N/A'),
                        'ask': option.get('askPrice', 'N/A'),
                        'volume': option.get('volume', 'N/A'),
                        'openInterest': option.get('openInterest', 'N/A'),
                        'lastPrice': option.get('lastPrice', 'N/A')
                    })
            
            api_responses.append(analysis)
            
            # Log findings
            logger.info(f"🎯 ANALYSIS FOR {symbol}:")
            logger.info(f"   📊 Total options: {total_options}")
            logger.info(f"   💰 Live bid/ask: {live_bid_ask} ({bid_ask_quality:.1f}%)")
            logger.info(f"   📈 Live volume: {live_volume} ({volume_quality:.1f}%)")
            logger.info(f"   🎯 Strike range: {analysis['strike_range']}")
            logger.info(f"   🔥 Liquid strikes (21000-22000): {liquid_strikes}")
            
            if live_bid_ask > 0:
                logger.info(f"✅ FOUND LIVE DATA! This symbol has real bid/ask prices!")
            else:
                logger.info(f"❌ No live bid/ask data - likely delayed feed")
            
            # Show sample data
            if analysis['sample_data']:
                logger.info(f"📋 Sample options:")
                for sample in analysis['sample_data'][:3]:
                    logger.info(f"     Strike {sample['strike']}: Bid={sample['bid']}, Ask={sample['ask']}, Vol={sample['volume']}")
            
        except Exception as e:
            logger.error(f"Error analyzing response: {e}")
    
    page.on('request', log_request)
    page.on('response', log_response)
    
    try:
        # Test multiple expiration dates
        test_urls = [
            # Current expiration (should be the same delayed data)
            'https://www.barchart.com/futures/quotes/NQM25/options/MC6M25?futuresOptionsView=merged',
            
            # Try different NQ symbols for different expirations
            'https://www.barchart.com/futures/quotes/NQU25/options/MC6U25?futuresOptionsView=merged',  # September
            'https://www.barchart.com/futures/quotes/NQZ25/options/MC6Z25?futuresOptionsView=merged',  # December
            
            # Try current month but different contract
            'https://www.barchart.com/futures/quotes/NQM25/options?futuresOptionsView=merged',
        ]
        
        for i, url in enumerate(test_urls):
            logger.info(f"\n{'='*60}")
            logger.info(f"🔍 TESTING URL {i+1}/{len(test_urls)}")
            logger.info(f"📍 {url}")
            logger.info(f"{'='*60}")
            
            try:
                await page.goto(url, {'waitUntil': 'domcontentloaded', 'timeout': 15000})
                logger.info("✅ Page loaded successfully")
                
                # Wait for API calls
                await asyncio.sleep(8)
                
                # Take screenshot for verification
                screenshot_path = f"data/live_api/test_tomorrow_{i+1}_{datetime.now().strftime('%H%M%S')}.png"
                await page.screenshot({'path': screenshot_path, 'fullPage': True})
                logger.info(f"📸 Screenshot saved: {screenshot_path}")
                
            except Exception as e:
                logger.warning(f"⚠️ Error loading {url}: {e}")
                continue
            
            # Brief pause between requests
            await asyncio.sleep(3)
        
        # Summary
        logger.info(f"\n🎯 SUMMARY OF ALL TESTS:")
        logger.info(f"   📡 Total API responses analyzed: {len(api_responses)}")
        
        live_apis = [api for api in api_responses if api['live_bid_ask'] > 0]
        delayed_apis = [api for api in api_responses if api['live_bid_ask'] == 0]
        
        logger.info(f"   🔥 APIs with live data: {len(live_apis)}")
        logger.info(f"   📉 APIs with delayed data: {len(delayed_apis)}")
        
        if live_apis:
            logger.info(f"\n✅ SUCCESS! Found live data sources:")
            for api in live_apis:
                logger.info(f"   🚀 {api['symbol']}: {api['live_bid_ask']}/{api['total_options']} ({api['bid_ask_quality']:.1f}%) live")
                logger.info(f"      📍 URL: {api['url']}")
        else:
            logger.info(f"\n❌ No live data found across all tested symbols/expirations")
            logger.info(f"💡 This confirms that live data requires authentication/subscription")
        
        # Save detailed results
        results = {
            'test_timestamp': datetime.now().isoformat(),
            'total_tests': len(test_urls),
            'api_responses': api_responses,
            'live_apis_found': len(live_apis),
            'conclusion': 'Live data found' if live_apis else 'No live data - requires authentication'
        }
        
        results_file = f"data/live_api/tomorrow_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"📋 Complete results saved to: {results_file}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in tomorrow data test: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        await browser.close()

if __name__ == '__main__':
    result = asyncio.run(test_tomorrow_data())
    
    if result and result.get('live_apis_found', 0) > 0:
        print(f"\n🎉 SUCCESS! Found {result['live_apis_found']} API(s) with live bid/ask data!")
        print("We can now extract real-time options data from these sources.")
    else:
        print(f"\n📊 ANALYSIS COMPLETE: All tested APIs return delayed data.")
        print("Live data access requires Barchart Premium subscription.")