#!/usr/bin/env python3
"""
Screenshot Investigation
Take screenshots at each step to see what's actually loading in the automated browser
"""

import asyncio
import logging
from pyppeteer import launch
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def screenshot_investigation():
    logger.info("📸 Screenshot investigation - visual confirmation of page loading")
    
    # Create screenshots directory
    screenshots_dir = "data/screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)
    
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Step 1: Navigate to the page
        url = 'https://www.barchart.com/futures/quotes/NQM25/options/MC6M25'
        logger.info(f"📍 Step 1: Navigating to {url}")
        await page.goto(url, {'waitUntil': 'domcontentloaded', 'timeout': 45000})
        
        # Screenshot 1: Initial load
        screenshot1 = f"{screenshots_dir}/step1_initial_load_{timestamp}.png"
        await page.screenshot({'path': screenshot1, 'fullPage': True})
        logger.info(f"📸 Screenshot 1 saved: {screenshot1}")
        
        # Step 2: Wait 5 seconds and screenshot
        logger.info("⏳ Step 2: Waiting 5 seconds for initial data...")
        await asyncio.sleep(5)
        
        screenshot2 = f"{screenshots_dir}/step2_after_5sec_{timestamp}.png"
        await page.screenshot({'path': screenshot2, 'fullPage': True})
        logger.info(f"📸 Screenshot 2 saved: {screenshot2}")
        
        # Check what we have so far
        strike_count_1 = await page.evaluate('''() => {
            const text = document.body.textContent || document.body.innerText || '';
            const strikes = (text.match(/\\b2[01]\\d{3}(?:[,.]\\d+)?\\b/g) || []).length;
            return strikes;
        }''')
        logger.info(f"📊 After 5 seconds: {strike_count_1} strike prices found")
        
        # Step 3: Try to click merged view or show all
        logger.info("🔄 Step 3: Attempting to activate merged view / show all...")
        
        interactions_tried = []
        
        # Try clicking merged view
        merged_clicked = await page.evaluate('''() => {
            const selectors = [
                'button[data-value="merged"]',
                'input[value="merged"]',
                'option[value="merged"]',
                '[ng-click*="merged"]',
                'button:contains("Merged")',
                'a:contains("Merged")'
            ];
            
            for (const selector of selectors) {
                try {
                    const elements = document.querySelectorAll(selector);
                    for (const element of elements) {
                        element.click();
                        return true;
                    }
                } catch (e) {
                    continue;
                }
            }
            return false;
        }''')
        
        if merged_clicked:
            interactions_tried.append("Clicked merged view")
            await asyncio.sleep(3)
        
        # Try show all buttons
        show_all_clicked = await page.evaluate('''() => {
            const buttons = document.querySelectorAll('button, a, option');
            for (const button of buttons) {
                const text = button.textContent || button.innerText || '';
                if (/show.?all|view.?all|all.?strikes/i.test(text)) {
                    button.click();
                    return true;
                }
            }
            return false;
        }''')
        
        if show_all_clicked:
            interactions_tried.append("Clicked show all")
            await asyncio.sleep(3)
        
        # Try dropdown changes
        dropdown_changed = await page.evaluate('''() => {
            const selects = document.querySelectorAll('select');
            for (const select of selects) {
                const options = select.querySelectorAll('option');
                for (const option of options) {
                    const text = option.textContent || option.value || '';
                    if (/all|unlimited|show.?all/i.test(text)) {
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
        
        # Screenshot 3: After interactions
        screenshot3 = f"{screenshots_dir}/step3_after_interactions_{timestamp}.png"
        await page.screenshot({'path': screenshot3, 'fullPage': True})
        logger.info(f"📸 Screenshot 3 saved: {screenshot3}")
        
        # Step 4: Wait longer for data to load
        logger.info("⏳ Step 4: Extended wait for data loading...")
        await asyncio.sleep(10)
        
        screenshot4 = f"{screenshots_dir}/step4_after_15sec_total_{timestamp}.png"
        await page.screenshot({'path': screenshot4, 'fullPage': True})
        logger.info(f"📸 Screenshot 4 saved: {screenshot4}")
        
        # Check strike count again
        strike_count_2 = await page.evaluate('''() => {
            const text = document.body.textContent || document.body.innerText || '';
            const strikes = (text.match(/\\b2[01]\\d{3}(?:[,.]\\d+)?\\b/g) || []).length;
            return strikes;
        }''')
        logger.info(f"📊 After 15 seconds total: {strike_count_2} strike prices found")
        
        # Step 5: Try direct URL navigation to merged view
        logger.info("🔄 Step 5: Trying direct navigation to merged view URL...")
        merged_url = 'https://www.barchart.com/futures/quotes/NQM25/options/MC6M25?futuresOptionsView=merged'
        
        try:
            await page.goto(merged_url, {'waitUntil': 'domcontentloaded', 'timeout': 30000})
            await asyncio.sleep(8)
            
            screenshot5 = f"{screenshots_dir}/step5_merged_url_{timestamp}.png"
            await page.screenshot({'path': screenshot5, 'fullPage': True})
            logger.info(f"📸 Screenshot 5 saved: {screenshot5}")
            
            strike_count_3 = await page.evaluate('''() => {
                const text = document.body.textContent || document.body.innerText || '';
                const strikes = (text.match(/\\b2[01]\\d{3}(?:[,.]\\d+)?\\b/g) || []).length;
                return strikes;
            }''')
            logger.info(f"📊 Merged URL: {strike_count_3} strike prices found")
            
        except Exception as e:
            logger.error(f"Merged URL navigation failed: {e}")
        
        # Step 6: Extended wait on merged view
        logger.info("⏳ Step 6: Extended wait on merged view...")
        await asyncio.sleep(15)
        
        screenshot6 = f"{screenshots_dir}/step6_merged_extended_{timestamp}.png"
        await page.screenshot({'path': screenshot6, 'fullPage': True})
        logger.info(f"📸 Screenshot 6 saved: {screenshot6}")
        
        # Final analysis
        final_analysis = await page.evaluate('''() => {
            const text = document.body.textContent || document.body.innerText || '';
            const strikes = text.match(/\\b2[01]\\d{3}(?:[,.]\\d+)?\\b/g) || [];
            const uniqueStrikes = [...new Set(strikes.map(s => s.replace(/,/g, '')))];
            const validStrikes = uniqueStrikes.filter(s => {
                const num = parseFloat(s);
                return num >= 20000 && num <= 23000;
            }).sort();
            
            return {
                totalStrikeMatches: strikes.length,
                uniqueStrikes: validStrikes.length,
                strikes: validStrikes,
                pageTextLength: text.length,
                hasCallPutHeaders: /call.*put|put.*call/i.test(text),
                hasVolumeHeaders: /volume/i.test(text),
                hasOIHeaders: /open.?interest/i.test(text),
                hasBidAskHeaders: /bid.*ask/i.test(text),
                tableCount: document.querySelectorAll('table').length,
                rowCount: document.querySelectorAll('tr').length,
                currentUrl: window.location.href
            };
        }''')
        
        logger.info(f"\n📊 FINAL ANALYSIS:")
        logger.info(f"   Current URL: {final_analysis['currentUrl']}")
        logger.info(f"   Total strike matches: {final_analysis['totalStrikeMatches']}")
        logger.info(f"   Unique valid strikes: {final_analysis['uniqueStrikes']}")
        logger.info(f"   Page text length: {final_analysis['pageTextLength']:,} chars")
        logger.info(f"   Tables found: {final_analysis['tableCount']}")
        logger.info(f"   Rows found: {final_analysis['rowCount']}")
        logger.info(f"   Has Call/Put headers: {final_analysis['hasCallPutHeaders']}")
        logger.info(f"   Has Volume headers: {final_analysis['hasVolumeHeaders']}")
        logger.info(f"   Has OI headers: {final_analysis['hasOIHeaders']}")
        logger.info(f"   Has Bid/Ask headers: {final_analysis['hasBidAskHeaders']}")
        
        if final_analysis['strikes']:
            logger.info(f"   Sample strikes: {final_analysis['strikes'][:10]}")
        
        # Step 7: Try extraction from current state
        logger.info("\n🎯 Step 7: Attempting extraction from current page state...")
        
        extraction_result = await page.evaluate('''() => {
            const data = [];
            const allElements = document.querySelectorAll('*');
            
            for (const element of allElements) {
                const text = element.textContent || element.innerText || '';
                const numbers = text.match(/\\b\\d+(?:[,.]\\d+)?\\b/g) || [];
                
                if (numbers.length >= 5) {
                    const numericValues = numbers.map(n => parseFloat(n.replace(/,/g, ''))).filter(n => !isNaN(n));
                    
                    for (let i = 0; i < numericValues.length; i++) {
                        const num = numericValues[i];
                        if (num >= 20000 && num <= 23000) {
                            data.push({
                                strike: num,
                                context: text.substring(0, 150),
                                elementType: element.tagName,
                                elementClasses: Array.from(element.classList).join('.'),
                                totalNumbers: numbers.length
                            });
                        }
                    }
                }
            }
            
            // Remove duplicates
            const uniqueData = [];
            const seenStrikes = new Set();
            
            for (const item of data) {
                if (!seenStrikes.has(item.strike)) {
                    seenStrikes.add(item.strike);
                    uniqueData.push(item);
                }
            }
            
            return uniqueData.sort((a, b) => a.strike - b.strike);
        }''')
        
        if extraction_result:
            logger.info(f"✅ Extracted {len(extraction_result)} unique strikes:")
            for opt in extraction_result[:10]:
                logger.info(f"   ${opt['strike']:,.0f} from {opt['elementType']}.{opt['elementClasses']} ({opt['totalNumbers']} numbers)")
        
        # Final screenshot with annotations
        screenshot7 = f"{screenshots_dir}/step7_final_state_{timestamp}.png"
        await page.screenshot({'path': screenshot7, 'fullPage': True})
        logger.info(f"📸 Final screenshot saved: {screenshot7}")
        
        return {
            'screenshots': [screenshot1, screenshot2, screenshot3, screenshot4, screenshot5, screenshot6, screenshot7],
            'analysis': final_analysis,
            'extracted_data': extraction_result,
            'interactions_tried': interactions_tried
        }
        
    except Exception as e:
        logger.error(f"❌ Error in screenshot investigation: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        await browser.close()

if __name__ == '__main__':
    result = asyncio.run(screenshot_investigation())
    
    if result:
        print(f"\n📸 SCREENSHOT INVESTIGATION COMPLETE")
        print(f"=" * 50)
        print(f"Screenshots saved: {len(result['screenshots'])}")
        for i, screenshot in enumerate(result['screenshots'], 1):
            print(f"  {i}. {screenshot}")
        
        print(f"\nFinal Results:")
        print(f"  Unique strikes found: {result['analysis']['uniqueStrikes']}")
        print(f"  Extracted options: {len(result['extracted_data'])}")
        print(f"  Interactions tried: {len(result['interactions_tried'])}")
        
        if result['analysis']['uniqueStrikes'] >= 10:
            print(f"✅ SUCCESS: Found substantial options data")
        else:
            print(f"⚠️ LIMITED: Found limited options data")
            print(f"💡 Check screenshots to see what's actually loading")
    else:
        print(f"\n❌ Screenshot investigation failed")