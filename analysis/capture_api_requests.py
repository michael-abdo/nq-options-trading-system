#!/usr/bin/env python3
"""
Capture API Requests
Monitor network requests to find the API endpoints that load the complete options data
"""

import asyncio
import logging
from pyppeteer import launch
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def capture_api_requests():
    logger.info("🔍 Capturing API requests that load options data...")
    
    # Launch browser
    browser = await launch({
        'headless': False,
        'args': ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    })
    
    page = await browser.newPage()
    await page.setViewport({'width': 1920, 'height': 1080})
    
    # Set user agent to avoid bot detection
    await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    # Storage for captured requests
    captured_requests = []
    captured_responses = []
    
    # Enable request interception
    await page.setRequestInterception(True)
    
    def log_request(request):
        # Log all requests
        request_data = {
            'timestamp': datetime.now().isoformat(),
            'url': request.url,
            'method': request.method,
            'resourceType': request.resourceType,
            'headers': dict(request.headers),
            'postData': request.postData if request.postData else None
        }
        
        # Look for API requests that might contain options data
        if any(term in request.url.lower() for term in ['option', 'quote', 'api', 'data', 'futures']):
            logger.info(f"📡 API Request: {request.method} {request.url}")
            captured_requests.append(request_data)
        
        # Continue the request
        asyncio.create_task(request.continue_())
    
    def log_response(response):
        # Log responses from interesting requests
        if any(term in response.url.lower() for term in ['option', 'quote', 'api', 'data', 'futures']):
            response_data = {
                'timestamp': datetime.now().isoformat(),
                'url': response.url,
                'status': response.status,
                'headers': dict(response.headers),
                'ok': response.ok
            }
            logger.info(f"📥 API Response: {response.status} {response.url}")
            captured_responses.append(response_data)
            
            # Try to capture response body for JSON APIs
            asyncio.create_task(capture_response_body(response))
    
    async def capture_response_body(response):
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                body = await response.text()
                
                # Check if this response contains options data
                if '21' in body and any(term in body.lower() for term in ['option', 'call', 'put', 'strike']):
                    logger.info(f"🎯 FOUND OPTIONS DATA in response from: {response.url}")
                    
                    # Save this response
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"data/api_responses/options_data_{timestamp}.json"
                    
                    import os
                    os.makedirs("data/api_responses", exist_ok=True)
                    
                    with open(filename, 'w') as f:
                        f.write(body)
                    
                    logger.info(f"💾 Saved options data to: {filename}")
                    
                    # Try to parse and count strikes
                    try:
                        data = json.loads(body)
                        import re
                        body_str = json.dumps(data)
                        strikes = re.findall(r'21[45]\d{2}(?:\.\d{2})?', body_str)
                        unique_strikes = list(set(strikes))
                        logger.info(f"📊 Response contains {len(unique_strikes)} unique strikes: {unique_strikes[:10]}")
                        
                        return {
                            'url': response.url,
                            'filename': filename,
                            'strikes_count': len(unique_strikes),
                            'strikes': unique_strikes[:20]
                        }
                    except:
                        pass
        except Exception as e:
            logger.debug(f"Error capturing response body: {e}")
    
    # Set up request/response monitoring
    page.on('request', log_request)
    page.on('response', log_response)
    
    try:
        # Navigate to the page
        url = 'https://www.barchart.com/futures/quotes/NQM25/options/MC6M25?futuresOptionsView=merged'
        logger.info(f"🌐 Navigating to: {url}")
        await page.goto(url, {'waitUntil': 'domcontentloaded', 'timeout': 30000})
        
        # Wait for initial load
        logger.info("⏳ Waiting for initial page load and API requests...")
        await asyncio.sleep(5)
        
        # Take a screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"data/screenshots/api_capture_{timestamp}.png"
        await page.screenshot({'path': screenshot_path, 'fullPage': True})
        logger.info(f"📸 Screenshot saved: {screenshot_path}")
        
        # Try interactions that might trigger more API calls
        logger.info("🔄 Attempting interactions to trigger more API calls...")
        
        # Try clicking merged view or show all buttons
        interactions = [
            'button[data-value="merged"]',
            'option[value="allRows"]',
            'button:contains("Show All")',
            'select[name="moneyness"]'
        ]
        
        for selector in interactions:
            try:
                element = await page.querySelector(selector)
                if element:
                    logger.info(f"🖱️ Clicking: {selector}")
                    await element.click()
                    await asyncio.sleep(3)  # Wait for potential API calls
            except:
                continue
        
        # Wait longer for any delayed API calls
        logger.info("⏳ Extended wait for delayed API calls...")
        await asyncio.sleep(15)
        
        # Check current page state
        final_strikes = await page.evaluate('''() => {
            const text = document.body.textContent || document.body.innerText || '';
            const strikes = text.match(/\\b21[45]\\d{2}(?:\\.\\d{2})?\\b/g) || [];
            const unique = [...new Set(strikes)];
            return unique.sort();
        }''')
        
        logger.info(f"📊 Final page state: {len(final_strikes)} unique strikes found")
        logger.info(f"🎯 Strikes: {final_strikes}")
        
        # Summary
        logger.info(f"\n📡 NETWORK MONITORING SUMMARY:")
        logger.info(f"   Captured API requests: {len(captured_requests)}")
        logger.info(f"   Captured API responses: {len(captured_responses)}")
        
        # Show most promising requests
        if captured_requests:
            logger.info(f"\n🎯 CAPTURED API REQUESTS:")
            for req in captured_requests[:5]:
                logger.info(f"   {req['method']} {req['url']}")
        
        if captured_responses:
            logger.info(f"\n📥 CAPTURED API RESPONSES:")
            for resp in captured_responses[:5]:
                logger.info(f"   {resp['status']} {resp['url']}")
        
        return {
            'captured_requests': captured_requests,
            'captured_responses': captured_responses,
            'final_strikes': final_strikes,
            'screenshot': screenshot_path
        }
        
    except Exception as e:
        logger.error(f"❌ Error in API capture: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        await browser.close()

if __name__ == '__main__':
    result = asyncio.run(capture_api_requests())
    
    if result:
        print(f"\n🎯 API CAPTURE COMPLETE!")
        print(f"📡 Requests captured: {len(result['captured_requests'])}")
        print(f"📥 Responses captured: {len(result['captured_responses'])}")
        print(f"📊 Final strikes on page: {len(result['final_strikes'])}")
        
        if len(result['final_strikes']) >= 10:
            print(f"✅ SUCCESS: Found substantial strike data!")
        else:
            print(f"⚠️ LIMITED: Only found {len(result['final_strikes'])} strikes")
            print(f"💡 Check API responses for the complete data")
            
        if result['captured_requests']:
            print(f"\n🔍 Check these API endpoints for options data:")
            for req in result['captured_requests'][:3]:
                print(f"   {req['url']}")
    else:
        print(f"\n❌ API capture failed")