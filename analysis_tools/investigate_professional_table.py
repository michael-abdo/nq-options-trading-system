#!/usr/bin/env python3
"""
Investigate Professional Options Table
Deep dive to find how the complete professional options table is loaded
"""

import asyncio
import logging
from pyppeteer import launch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def investigate_professional_table():
    logger.info("🔍 Deep investigation of professional options table structure")
    
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
        # Navigate to the page
        url = 'https://www.barchart.com/futures/quotes/NQM25/options/MC6M25'
        logger.info(f"Navigating to: {url}")
        await page.goto(url, {'waitUntil': 'networkidle2', 'timeout': 30000})
        
        # Wait for page to load
        await asyncio.sleep(10)
        
        logger.info("🔍 INVESTIGATION 1: Authentication and access requirements")
        logger.info("="*60)
        
        # Check for authentication barriers
        auth_analysis = await page.evaluate('''() => {
            const analysis = {
                login_required: false,
                premium_required: false,
                subscription_wall: false,
                paywall_detected: false,
                auth_indicators: [],
                premium_indicators: [],
                data_access_level: 'unknown'
            };
            
            const text = document.body.textContent || document.body.innerText || '';
            const lowText = text.toLowerCase();
            
            // Check for authentication requirements
            const authTerms = ['log in', 'sign in', 'login required', 'please login', 'subscription required'];
            for (const term of authTerms) {
                if (lowText.includes(term)) {
                    analysis.auth_indicators.push(term);
                    analysis.login_required = true;
                }
            }
            
            // Check for premium/subscription requirements
            const premiumTerms = ['premium', 'upgrade', 'subscription', 'subscribe', 'paid', 'trial', 'pro'];
            for (const term of premiumTerms) {
                if (lowText.includes(term)) {
                    analysis.premium_indicators.push(term);
                    analysis.premium_required = true;
                }
            }
            
            // Check for data access limitations
            if (lowText.includes('limited') || lowText.includes('restricted') || lowText.includes('upgrade for full')) {
                analysis.subscription_wall = true;
            }
            
            // Check for paywall indicators
            if (lowText.includes('paywall') || lowText.includes('unlock') || lowText.includes('full access')) {
                analysis.paywall_detected = true;
            }
            
            return analysis;
        }''')
        
        logger.info(f"🔐 AUTHENTICATION ANALYSIS:")
        logger.info(f"   Login required: {auth_analysis['login_required']}")
        logger.info(f"   Premium required: {auth_analysis['premium_required']}")
        logger.info(f"   Subscription wall: {auth_analysis['subscription_wall']}")
        logger.info(f"   Paywall detected: {auth_analysis['paywall_detected']}")
        
        if auth_analysis['auth_indicators']:
            logger.info(f"   Auth indicators: {auth_analysis['auth_indicators']}")
        if auth_analysis['premium_indicators']:
            logger.info(f"   Premium indicators: {auth_analysis['premium_indicators']}")
        
        logger.info(f"\\n🔍 INVESTIGATION 2: Network requests and data loading")
        logger.info("="*60)
        
        # Monitor network requests
        network_requests = []
        
        def log_request(request):
            if 'option' in request.url.lower() or 'quote' in request.url.lower():
                network_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'resource_type': request.resourceType
                })
        
        page.on('request', log_request)
        
        # Try to trigger data loading
        logger.info("🔄 Attempting to trigger options data loading...")
        
        # Try various interactions to load more data
        interactions_tried = []
        
        # 1. Try clicking tabs or views
        tab_clicked = await page.evaluate('''() => {
            const tabs = document.querySelectorAll('a[href*="option"], button[class*="option"], [role="tab"]');
            for (const tab of tabs) {
                const text = tab.textContent || tab.innerText || '';
                if (/option|call|put/i.test(text)) {
                    tab.click();
                    return true;
                }
            }
            return false;
        }''')
        
        if tab_clicked:
            interactions_tried.append("Clicked options tab")
            await asyncio.sleep(3)
        
        # 2. Try expanding tables or views
        expand_clicked = await page.evaluate('''() => {
            const expandButtons = document.querySelectorAll('button, a, [role="button"]');
            for (const button of expandButtons) {
                const text = button.textContent || button.innerText || '';
                if (/expand|show all|view all|more/i.test(text)) {
                    button.click();
                    return true;
                }
            }
            return false;
        }''')
        
        if expand_clicked:
            interactions_tried.append("Clicked expand/show all")
            await asyncio.sleep(3)
        
        # 3. Try dropdown selections
        dropdown_changed = await page.evaluate('''() => {
            const selects = document.querySelectorAll('select');
            for (const select of selects) {
                const options = select.querySelectorAll('option');
                for (const option of options) {
                    const text = option.textContent || option.value || '';
                    if (/all|unlimited|complete|full/i.test(text)) {
                        select.value = option.value;
                        select.dispatchEvent(new Event('change'));
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if dropdown_changed:
            interactions_tried.append("Changed dropdown to show all")
            await asyncio.sleep(3)
        
        logger.info(f"🎯 Interactions tried: {interactions_tried}")
        logger.info(f"📡 Network requests captured: {len(network_requests)}")
        
        for req in network_requests:
            logger.info(f"   {req['method']} {req['resource_type']}: {req['url'][:100]}...")
        
        logger.info(f"\\n🔍 INVESTIGATION 3: Deep DOM structure analysis")
        logger.info("="*60)
        
        # Analyze the current DOM structure in detail
        dom_analysis = await page.evaluate('''() => {
            const analysis = {
                total_elements: document.querySelectorAll('*').length,
                tables: document.querySelectorAll('table').length,
                data_tables: 0,
                angular_controllers: [],
                data_attributes: [],
                potential_data_containers: [],
                iframe_count: document.querySelectorAll('iframe').length,
                canvas_count: document.querySelectorAll('canvas').length
            };
            
            // Look for Angular controllers
            const ngElements = document.querySelectorAll('[ng-controller], [data-ng-controller]');
            for (const elem of ngElements) {
                const controller = elem.getAttribute('ng-controller') || elem.getAttribute('data-ng-controller');
                analysis.angular_controllers.push(controller);
            }
            
            // Look for data attributes
            const allElements = document.querySelectorAll('*');
            for (const elem of allElements) {
                for (const attr of elem.attributes) {
                    if (attr.name.includes('data-') && attr.value.includes('option')) {
                        analysis.data_attributes.push({
                            name: attr.name,
                            value: attr.value.substring(0, 50)
                        });
                    }
                }
            }
            
            // Look for potential data containers
            const containers = document.querySelectorAll('div[class*="table"], div[class*="grid"], div[class*="data"]');
            for (const container of containers) {
                const text = container.textContent || container.innerText || '';
                if (text.length > 1000 && /21[4-6]\\d{2}/.test(text)) {
                    analysis.potential_data_containers.push({
                        tag: container.tagName,
                        classes: Array.from(container.classList),
                        id: container.id || '',
                        textLength: text.length,
                        hasStrike: /21[4-6]\\d{2}/.test(text)
                    });
                }
            }
            
            return analysis;
        }''')
        
        logger.info(f"📊 DOM STRUCTURE:")
        logger.info(f"   Total elements: {dom_analysis['total_elements']:,}")
        logger.info(f"   Tables: {dom_analysis['tables']}")
        logger.info(f"   iFrames: {dom_analysis['iframe_count']}")
        logger.info(f"   Canvas elements: {dom_analysis['canvas_count']}")
        logger.info(f"   Angular controllers: {len(dom_analysis['angular_controllers'])}")
        logger.info(f"   Data attributes: {len(dom_analysis['data_attributes'])}")
        logger.info(f"   Potential data containers: {len(dom_analysis['potential_data_containers'])}")
        
        if dom_analysis['angular_controllers']:
            logger.info(f"   Controllers: {dom_analysis['angular_controllers']}")
        
        if dom_analysis['potential_data_containers']:
            logger.info(f"\\n📦 POTENTIAL DATA CONTAINERS:")
            for container in dom_analysis['potential_data_containers']:
                logger.info(f"   {container['tag']}.{'.'.join(container['classes'][:3])}")
                logger.info(f"     Text length: {container['textLength']:,}, Has strikes: {container['hasStrike']}")
        
        logger.info(f"\\n🔍 INVESTIGATION 4: JavaScript execution environment")
        logger.info("="*60)
        
        # Check for JavaScript frameworks and data
        js_analysis = await page.evaluate('''() => {
            const analysis = {
                jquery: typeof $ !== 'undefined',
                angular: typeof angular !== 'undefined',
                react: typeof React !== 'undefined',
                vue: typeof Vue !== 'undefined',
                global_data: [],
                window_properties: []
            };
            
            // Check for global data variables
            for (const prop in window) {
                if (typeof window[prop] === 'object' && window[prop] !== null) {
                    try {
                        const str = JSON.stringify(window[prop]).substring(0, 100);
                        if (str.includes('option') || str.includes('strike') || str.includes('21')) {
                            analysis.global_data.push({
                                name: prop,
                                preview: str
                            });
                        }
                    } catch (e) {
                        // Skip non-serializable objects
                    }
                }
            }
            
            // Check for interesting window properties
            const interestingProps = Object.keys(window).filter(prop => 
                prop.toLowerCase().includes('data') || 
                prop.toLowerCase().includes('option') ||
                prop.toLowerCase().includes('quote')
            );
            
            analysis.window_properties = interestingProps;
            
            return analysis;
        }''')
        
        logger.info(f"⚙️  JAVASCRIPT ENVIRONMENT:")
        logger.info(f"   jQuery: {js_analysis['jquery']}")
        logger.info(f"   Angular: {js_analysis['angular']}")
        logger.info(f"   React: {js_analysis['react']}")
        logger.info(f"   Vue: {js_analysis['vue']}")
        logger.info(f"   Global data objects: {len(js_analysis['global_data'])}")
        logger.info(f"   Window properties: {len(js_analysis['window_properties'])}")
        
        if js_analysis['global_data']:
            logger.info(f"\\n📊 GLOBAL DATA OBJECTS:")
            for data_obj in js_analysis['global_data'][:5]:
                logger.info(f"   {data_obj['name']}: {data_obj['preview']}...")
        
        logger.info(f"\\n🔍 INVESTIGATION 5: Current data availability")
        logger.info("="*60)
        
        # Final check of what's actually available right now
        current_data = await page.evaluate('''() => {
            const strikes = [];
            const text = document.body.textContent || document.body.innerText || '';
            
            // Find all strike-like numbers
            const strikeMatches = text.match(/21[4-6]\\d{2}(?:\\.\\d{2})?/g) || [];
            const uniqueStrikes = [...new Set(strikeMatches)];
            
            return {
                total_text_length: text.length,
                strike_matches: strikeMatches.length,
                unique_strikes: uniqueStrikes.length,
                strikes: uniqueStrikes.slice(0, 10),
                has_professional_data: /open.*high.*low.*last/i.test(text) && /bid.*ask/i.test(text)
            };
        }''')
        
        logger.info(f"📈 CURRENT DATA AVAILABILITY:")
        logger.info(f"   Total page text: {current_data['total_text_length']:,} characters")
        logger.info(f"   Strike matches: {current_data['strike_matches']}")
        logger.info(f"   Unique strikes: {current_data['unique_strikes']}")
        logger.info(f"   Professional data format: {current_data['has_professional_data']}")
        
        if current_data['strikes']:
            logger.info(f"   Sample strikes: {current_data['strikes']}")
        
        # Final assessment
        logger.info(f"\\n" + "="*60)
        logger.info(f"🎯 INVESTIGATION SUMMARY")
        logger.info(f"="*60)
        
        professional_data_available = (
            current_data['unique_strikes'] >= 15 and 
            current_data['has_professional_data']
        )
        
        logger.info(f"✅ Professional options data available: {professional_data_available}")
        
        if not professional_data_available:
            logger.info(f"❌ BARRIERS IDENTIFIED:")
            if auth_analysis['login_required']:
                logger.info(f"   • Login/authentication required")
            if auth_analysis['premium_required']:
                logger.info(f"   • Premium subscription required")
            if current_data['unique_strikes'] < 15:
                logger.info(f"   • Limited data access (only {current_data['unique_strikes']} strikes)")
            if not current_data['has_professional_data']:
                logger.info(f"   • Missing professional data format (OHLC, bid/ask)")
        else:
            logger.info(f"✅ EXTRACTION POSSIBLE:")
            logger.info(f"   • {current_data['unique_strikes']} strikes available")
            logger.info(f"   • Professional data format detected")
            logger.info(f"   • No major authentication barriers")
        
        return {
            'auth_analysis': auth_analysis,
            'dom_analysis': dom_analysis,
            'js_analysis': js_analysis,
            'current_data': current_data,
            'professional_data_available': professional_data_available,
            'interactions_tried': interactions_tried,
            'network_requests': len(network_requests)
        }
        
    except Exception as e:
        logger.error(f"❌ Error in investigation: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        await browser.close()

if __name__ == '__main__':
    result = asyncio.run(investigate_professional_table())
    
    if result:
        print(f"\\n🎯 INVESTIGATION COMPLETE")
        print(f"="*50)
        print(f"Professional data available: {result['professional_data_available']}")
        print(f"Authentication barriers: {result['auth_analysis']['login_required'] or result['auth_analysis']['premium_required']}")
        print(f"Unique strikes found: {result['current_data']['unique_strikes']}")
        print(f"Network requests captured: {result['network_requests']}")
        print(f"Interactions tried: {len(result['interactions_tried'])}")
        
        if not result['professional_data_available']:
            print(f"\\n🚧 NEXT STEPS REQUIRED:")
            print(f"1. Investigate authentication/premium access")
            print(f"2. Find alternative data sources or APIs")
            print(f"3. Analyze network requests for data endpoints")
    else:
        print(f"\\n❌ Investigation failed")