#!/usr/bin/env python3
"""
Advanced Extraction Test
Test advanced extraction techniques to find the actual options table data
"""

import asyncio
import logging
import re
from pyppeteer import launch
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_advanced_extraction():
    logger.info("🚀 Testing advanced extraction techniques")
    
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
        
        logger.info("Testing comprehensive DOM search for options data...")
        
        # Method 1: Search for all elements containing strike-like numbers
        strike_elements = await page.evaluate('''() => {
            const results = [];
            const elements = document.querySelectorAll('*');
            
            for (const element of elements) {
                const text = element.textContent || element.innerText || '';
                
                // Look for strike prices in 21000-22000 range
                if (/21[,\\s]*[3-7]\\d{2}[,\\s]*\\.\\d{2}/.test(text)) {
                    // Check if this element contains multiple numbers (likely a table row)
                    const numbers = text.match(/\\d+(?:[,.]\\d+)?/g) || [];
                    if (numbers.length >= 3) {  // Likely contains strike + volume/OI/premium data
                        results.push({
                            tag: element.tagName,
                            classes: Array.from(element.classList),
                            id: element.id || '',
                            text: text.trim(),
                            numbers: numbers,
                            parent_tag: element.parentElement?.tagName || '',
                            parent_classes: Array.from(element.parentElement?.classList || [])
                        });
                    }
                }
            }
            
            return results;
        }''')
        
        if strike_elements:
            logger.info(f"🎯 Found {len(strike_elements)} elements with potential options data:")
            for i, elem in enumerate(strike_elements[:5]):  # Show first 5
                logger.info(f"  {i+1}. {elem['tag']}.{'.'.join(elem['classes'])} - {elem['numbers'][:7]}")
                logger.info(f"     Text: {elem['text'][:100]}...")
        else:
            logger.info("❌ No elements found with multiple numeric data")
        
        # Method 2: Search for Angular scope data directly
        logger.info("\\n Testing Angular scope data extraction...")
        
        angular_data = await page.evaluate('''() => {
            const results = [];
            
            try {
                // Find all elements with Angular controllers
                const ngElements = document.querySelectorAll('[ng-controller], [data-ng-controller]');
                
                for (const element of ngElements) {
                    try {
                        if (typeof angular !== 'undefined') {
                            const scope = angular.element(element).scope();
                            if (scope && scope.data) {
                                results.push({
                                    controller: element.getAttribute('ng-controller') || element.getAttribute('data-ng-controller'),
                                    hasData: !!scope.data,
                                    dataKeys: Object.keys(scope.data || {}),
                                    hasCalls: !!(scope.data && scope.data.calls),
                                    hasPuts: !!(scope.data && scope.data.puts),
                                    callsLength: scope.data?.calls?.data?.length || 0,
                                    putsLength: scope.data?.puts?.data?.length || 0
                                });
                            }
                        }
                    } catch (e) {
                        // Skip this element
                    }
                }
            } catch (e) {
                console.log('Angular not available:', e.message);
            }
            
            return results;
        }''')
        
        if angular_data:
            logger.info(f"🎯 Found {len(angular_data)} Angular controllers with data:")
            for data in angular_data:
                logger.info(f"  Controller: {data['controller']}")
                logger.info(f"  Has calls: {data['hasCalls']} ({data['callsLength']} items)")
                logger.info(f"  Has puts: {data['hasPuts']} ({data['putsLength']} items)")
        else:
            logger.info("❌ No Angular scope data found")
        
        # Method 3: Look for table-like structures containing numbers
        logger.info("\\n Testing table-like structure detection...")
        
        table_like = await page.evaluate('''() => {
            const results = [];
            
            // Look for divs or elements that might represent table rows
            const elements = document.querySelectorAll('div, tr, li');
            
            for (const element of elements) {
                const text = element.textContent || element.innerText || '';
                
                // Look for patterns that might be option rows
                // Pattern: numbers that could represent volume, OI, premium, strike, premium, OI, volume
                const numbers = text.match(/\\b\\d+(?:[,.]\\d+)?\\b/g) || [];
                
                if (numbers.length >= 5) {  // At least 5 numbers (could be option row)
                    // Check if one of the numbers looks like a strike price
                    const hasStrike = numbers.some(n => {
                        const num = parseFloat(n.replace(/,/g, ''));
                        return num >= 15000 && num <= 30000;
                    });
                    
                    if (hasStrike) {
                        results.push({
                            tag: element.tagName,
                            classes: Array.from(element.classList),
                            numbers: numbers,
                            text: text.trim().substring(0, 150)
                        });
                    }
                }
            }
            
            return results;
        }''')
        
        if table_like:
            logger.info(f"🎯 Found {len(table_like)} table-like elements:")
            for i, elem in enumerate(table_like[:3]):  # Show first 3
                logger.info(f"  {i+1}. {elem['tag']}.{'.'.join(elem['classes'])} - {len(elem['numbers'])} numbers")
                logger.info(f"     Numbers: {elem['numbers'][:10]}")
        else:
            logger.info("❌ No table-like structures found")
        
        # Method 4: Try to extract actual data from any found elements
        if table_like:
            logger.info("\\n Attempting to extract options data from found elements...")
            
            options_data = []
            
            for elem_info in table_like[:5]:  # Process first 5 elements
                try:
                    numbers = [float(n.replace(',', '')) for n in elem_info['numbers']]
                    
                    # Find the strike price (number in 15000-30000 range)
                    strike = None
                    strike_index = None
                    for i, num in enumerate(numbers):
                        if 15000 <= num <= 30000:
                            strike = num
                            strike_index = i
                            break
                    
                    if strike:
                        option = {
                            'strike': strike,
                            'call_volume': numbers[strike_index - 3] if strike_index >= 3 else 0,
                            'call_oi': numbers[strike_index - 2] if strike_index >= 2 else 0,
                            'call_premium': numbers[strike_index - 1] if strike_index >= 1 else 0,
                            'put_premium': numbers[strike_index + 1] if strike_index + 1 < len(numbers) else 0,
                            'put_oi': numbers[strike_index + 2] if strike_index + 2 < len(numbers) else 0,
                            'put_volume': numbers[strike_index + 3] if strike_index + 3 < len(numbers) else 0,
                            'source': f"{elem_info['tag']}.{'.'.join(elem_info['classes'])}"
                        }
                        options_data.append(option)
                        
                except Exception as e:
                    logger.debug(f"Error processing element: {e}")
                    continue
            
            if options_data:
                logger.info(f"🎉 SUCCESS! Extracted {len(options_data)} options:")
                for opt in options_data[:3]:
                    logger.info(f"  Strike {opt['strike']:,.0f}: Call ${opt['call_premium']:.2f}, Put ${opt['put_premium']:.2f}")
                    logger.info(f"    Source: {opt['source']}")
            else:
                logger.info("❌ Could not extract valid options data from found elements")
        
    except Exception as e:
        logger.error(f"❌ Error in advanced extraction test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_advanced_extraction())