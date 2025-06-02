#!/usr/bin/env python3
"""
Hunt for Live Authenticated API
Monitor network requests to capture the authenticated API endpoint that serves live market data
"""

import asyncio
import json
import logging
from datetime import datetime
from pyppeteer import launch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def hunt_live_api():
    logger.info("🏹 HUNTING FOR LIVE AUTHENTICATED API ENDPOINT...")
    
    # Launch browser with extended timeout
    browser = await launch({
        'headless': False,
        'args': [
            '--no-sandbox', 
            '--disable-setuid-sandbox', 
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor'
        ]
    })
    
    page = await browser.newPage()
    await page.setViewport({'width': 1920, 'height': 1080})
    
    # Set user agent to avoid bot detection
    await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    # Storage for captured requests
    captured_authenticated_requests = []
    captured_live_apis = []
    
    # Monitor ALL network requests
    await page.setRequestInterception(True)
    
    def log_request(request):
        # Log ALL requests to find authenticated endpoints
        request_data = {
            'timestamp': datetime.now().isoformat(),
            'url': request.url,
            'method': request.method,
            'headers': dict(request.headers),
            'resourceType': request.resourceType
        }
        
        # Look for API requests that might be authenticated
        if any(term in request.url.lower() for term in ['api', 'quotes', 'data', 'options', 'futures']):
            logger.info(f"🔍 POTENTIAL API: {request.method} {request.url}")
            
            # Check for authentication headers
            has_auth = any(header.lower() in ['authorization', 'x-api-key', 'cookie', 'session'] 
                          for header in request.headers.keys())
            
            if has_auth:
                logger.info(f"🔐 AUTHENTICATED REQUEST: {request.url}")
                captured_authenticated_requests.append({
                    **request_data,
                    'has_authentication': True,
                    'auth_headers': {k: v for k, v in request.headers.items() 
                                   if k.lower() in ['authorization', 'x-api-key', 'cookie', 'session']}
                })
        
        # Continue the request
        asyncio.create_task(request.continue_())
    
    def log_response(response):
        # Check for responses that contain live options data
        if any(term in response.url.lower() for term in ['api', 'quotes', 'data', 'options', 'futures']):
            logger.info(f"📥 API RESPONSE: {response.status} {response.url}")
            
            # Capture response body for analysis
            asyncio.create_task(analyze_response(response))
    
    async def analyze_response(response):
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                body = await response.text()
                
                # Check if this response contains live options data with bid/ask
                contains_strikes = '21' in body and any(term in body.lower() for term in ['strike', 'call', 'put'])
                contains_live_data = any(term in body for term in ['"bid"', '"ask"', '"volume"', '"openInterest"'])
                
                if contains_strikes and contains_live_data:
                    logger.info(f"🎯 LIVE OPTIONS DATA API FOUND: {response.url}")
                    
                    # Save this response - this is likely the authenticated live API!
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"data/live_api/authenticated_live_data_{timestamp}.json"
                    
                    import os
                    os.makedirs("data/live_api", exist_ok=True)
                    
                    with open(filename, 'w') as f:
                        f.write(body)
                    
                    # Check data quality
                    try:
                        data = json.loads(body)
                        
                        # Analyze the data structure
                        strikes_with_bid_ask = 0
                        total_strikes = 0
                        
                        def count_live_data(obj):
                            nonlocal strikes_with_bid_ask, total_strikes
                            if isinstance(obj, dict):
                                if 'strike' in obj or any(k for k in obj.keys() if '21' in str(k)):
                                    total_strikes += 1
                                    if obj.get('bid') and obj.get('ask') and obj.get('bid') != 'N/A' and obj.get('ask') != 'N/A':
                                        strikes_with_bid_ask += 1
                                for value in obj.values():
                                    count_live_data(value)
                            elif isinstance(obj, list):
                                for item in obj:
                                    count_live_data(item)
                        
                        count_live_data(data)
                        
                        live_data_quality = (strikes_with_bid_ask / total_strikes * 100) if total_strikes > 0 else 0
                        
                        logger.info(f"🔥 LIVE DATA QUALITY ANALYSIS:")
                        logger.info(f"   📊 Total strikes found: {total_strikes}")
                        logger.info(f"   💰 Strikes with live bid/ask: {strikes_with_bid_ask}")
                        logger.info(f"   📈 Live data quality: {live_data_quality:.1f}%")
                        
                        if live_data_quality > 50:
                            logger.info(f"✅ HIGH QUALITY LIVE DATA SOURCE IDENTIFIED!")
                            captured_live_apis.append({
                                'url': response.url,
                                'filename': filename,
                                'quality': live_data_quality,
                                'total_strikes': total_strikes,
                                'live_strikes': strikes_with_bid_ask,
                                'timestamp': timestamp
                            })
                        else:
                            logger.info(f"⚠️ LOW QUALITY DATA - likely delayed feed")
                            
                    except Exception as e:
                        logger.debug(f"Error analyzing response data: {e}")
                        
        except Exception as e:
            logger.debug(f"Error capturing response body: {e}")
    
    # Set up monitoring
    page.on('request', log_request)
    page.on('response', log_response)
    
    try:
        # Navigate to the page - use a shorter timeout and retry
        url = 'https://www.barchart.com/futures/quotes/NQM25/options/MC6M25?futuresOptionsView=merged'
        logger.info(f"🌐 Navigating to: {url}")
        
        try:
            await page.goto(url, {'waitUntil': 'domcontentloaded', 'timeout': 15000})
        except Exception as e:
            logger.warning(f"Initial navigation timeout: {e}")
            logger.info("🔄 Trying to load page content anyway...")
        
        # Wait for initial requests
        logger.info("⏳ Monitoring initial API requests...")
        await asyncio.sleep(10)
        
        # Try to interact with the page to trigger authenticated API calls
        logger.info("🖱️ Attempting page interactions to trigger authenticated APIs...")
        
        try:
            # Check if we need to accept cookies or handle popups
            await page.evaluate('''() => {
                // Close any cookie banners or popups
                const buttons = document.querySelectorAll('button');
                for (const button of buttons) {
                    const text = button.textContent.toLowerCase();
                    if (text.includes('accept') || text.includes('ok') || text.includes('agree')) {
                        button.click();
                        break;
                    }
                }
            }''')
            await asyncio.sleep(2)
            
            # Try to refresh the options data
            await page.evaluate('''() => {
                // Look for refresh or reload buttons
                const buttons = document.querySelectorAll('button, a');
                for (const button of buttons) {
                    const text = button.textContent.toLowerCase();
                    if (text.includes('refresh') || text.includes('reload') || text.includes('update')) {
                        button.click();
                        break;
                    }
                }
            }''')
            await asyncio.sleep(5)
            
            # Try changing filters to trigger new API calls
            await page.evaluate('''() => {
                // Try changing dropdown selections
                const selects = document.querySelectorAll('select');
                for (const select of selects) {
                    if (select.options.length > 1) {
                        select.selectedIndex = 1;
                        select.dispatchEvent(new Event('change'));
                        break;
                    }
                }
            }''')
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.debug(f"Page interaction error: {e}")
        
        # Monitor for longer to catch all authenticated requests
        logger.info("🔍 Extended monitoring for authenticated API calls...")
        await asyncio.sleep(15)
        
        # Take a screenshot for verification
        screenshot_path = f"data/live_api/hunt_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await page.screenshot({'path': screenshot_path, 'fullPage': True})
        logger.info(f"📸 Screenshot saved: {screenshot_path}")
        
        # Summary
        logger.info(f"\n🎯 HUNT SUMMARY:")
        logger.info(f"   📡 Authenticated requests captured: {len(captured_authenticated_requests)}")
        logger.info(f"   🔥 Live API endpoints found: {len(captured_live_apis)}")
        
        if captured_live_apis:
            logger.info(f"\n✅ SUCCESS! LIVE AUTHENTICATED APIs DISCOVERED:")
            for api in captured_live_apis:
                logger.info(f"   🚀 {api['url']}")
                logger.info(f"      📊 Quality: {api['quality']:.1f}% ({api['live_strikes']}/{api['total_strikes']} live)")
                logger.info(f"      💾 Saved to: {api['filename']}")
        
        if captured_authenticated_requests:
            logger.info(f"\n🔐 AUTHENTICATED REQUESTS FOUND:")
            for req in captured_authenticated_requests[:5]:
                logger.info(f"   🔑 {req['url']}")
                if req.get('auth_headers'):
                    for header, value in req['auth_headers'].items():
                        logger.info(f"      {header}: {value[:50]}..." if len(value) > 50 else f"      {header}: {value}")
        
        # Save detailed results
        results = {
            'hunt_timestamp': datetime.now().isoformat(),
            'authenticated_requests': captured_authenticated_requests,
            'live_apis': captured_live_apis,
            'success': len(captured_live_apis) > 0
        }
        
        results_file = f"data/live_api/hunt_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"📋 Complete results saved to: {results_file}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in API hunt: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        await browser.close()

if __name__ == '__main__':
    result = asyncio.run(hunt_live_api())
    
    if result and result.get('success'):
        print(f"\n🎉 SUCCESS! Found {len(result['live_apis'])} live authenticated API endpoints!")
        print("Now we can build a production scraper using these endpoints.")
    else:
        print(f"\n⚠️ No live APIs found. The data may require login or premium subscription.")
        print("Consider manually logging in first, then running this script.")