#!/usr/bin/env python3
"""
Comprehensive Options Search
Find ALL options data on the page with different criteria
"""

import asyncio
import logging
from pyppeteer import launch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_comprehensive_search():
    logger.info("🚀 Testing comprehensive options search")
    
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
        
        logger.info("🔍 Comprehensive search for ALL strike prices on the page...")
        
        # Method 1: Find ALL elements containing ANY strike price patterns
        all_strikes = await page.evaluate('''() => {
            const results = [];
            const allElements = document.querySelectorAll('*');
            
            for (const element of allElements) {
                const text = element.textContent || element.innerText || '';
                
                // Look for strike price patterns (broader search)
                const strikeMatches = text.match(/\\b2[01]\\d{3}(?:[,.]\\d+)?\\b/g);
                
                if (strikeMatches) {
                    for (const match of strikeMatches) {
                        const strike = parseFloat(match.replace(/,/g, ''));
                        
                        // Valid NQ strike range
                        if (strike >= 15000 && strike <= 30000) {
                            results.push({
                                strike: strike,
                                element: element.tagName,
                                classes: Array.from(element.classList),
                                id: element.id || '',
                                text: text.trim().substring(0, 150),
                                parent: element.parentElement?.tagName || ''
                            });
                        }
                    }
                }
            }
            
            return results;
        }''')
        
        if all_strikes:
            # Group by strike to see unique strikes
            strikes_map = {}
            for item in all_strikes:
                strike = item['strike']
                if strike not in strikes_map:
                    strikes_map[strike] = []
                strikes_map[strike].append(item)
            
            logger.info(f"🎯 Found {len(strikes_map)} unique strike prices across page:")
            
            sorted_strikes = sorted(strikes_map.keys())
            logger.info(f"📊 Strike range: ${sorted_strikes[0]:,.0f} - ${sorted_strikes[-1]:,.0f}")
            
            # Show sample of strikes
            for strike in sorted_strikes[:10]:
                count = len(strikes_map[strike])
                logger.info(f"  ${strike:,.0f}: {count} occurrences")
        
        # Method 2: Look for structured rows containing multiple strikes
        logger.info("\\n🔍 Searching for rows/containers with multiple strike prices...")
        
        multi_strike_containers = await page.evaluate('''() => {
            const results = [];
            const containers = document.querySelectorAll('div, tr, section, table, tbody');
            
            for (const container of containers) {
                const text = container.textContent || container.innerText || '';
                const strikeMatches = text.match(/\\b2[01]\\d{3}(?:[,.]\\d+)?\\b/g) || [];
                
                // Only containers with multiple strikes
                if (strikeMatches.length >= 3) {
                    const uniqueStrikes = [...new Set(strikeMatches.map(s => parseFloat(s.replace(/,/g, ''))))];
                    const validStrikes = uniqueStrikes.filter(s => s >= 15000 && s <= 30000);
                    
                    if (validStrikes.length >= 3) {
                        results.push({
                            element: container.tagName,
                            classes: Array.from(container.classList),
                            id: container.id || '',
                            strikeCount: validStrikes.length,
                            strikes: validStrikes.sort((a,b) => a-b),
                            childCount: container.children.length,
                            textLength: text.length
                        });
                    }
                }
            }
            
            return results;
        }''')
        
        if multi_strike_containers:
            logger.info(f"🎯 Found {len(multi_strike_containers)} containers with multiple strikes:")
            
            # Sort by strike count (most promising first)
            multi_strike_containers.sort(key=lambda x: x['strikeCount'], reverse=True)
            
            for i, container in enumerate(multi_strike_containers[:5]):
                logger.info(f"  {i+1}. {container['element']}.{'.'.join(container['classes'][:3])}")
                logger.info(f"     {container['strikeCount']} strikes, {container['childCount']} children")
                logger.info(f"     Range: ${container['strikes'][0]:,.0f} - ${container['strikes'][-1]:,.0f}")
        
        # Method 3: Extract options data from the best container
        if multi_strike_containers:
            best_container = multi_strike_containers[0]
            logger.info(f"\\n🎯 Extracting from best container: {best_container['element']} ({best_container['strikeCount']} strikes)")
            
            # Create a more specific selector for this container
            selector_parts = [best_container['element'].lower()]
            if best_container['id']:
                selector = f"#{best_container['id']}"
            elif best_container['classes']:
                selector = f"{best_container['element'].lower()}.{'.'.join(best_container['classes'][:2])}"
            else:
                selector = best_container['element'].lower()
            
            logger.info(f"Using selector: {selector}")
            
            comprehensive_data = await page.evaluate(f'''() => {{
                const data = [];
                const processedStrikes = new Set();
                const container = document.querySelector('{selector}');
                
                if (container) {{
                    // Look for all elements within this container
                    const allElements = container.querySelectorAll('*');
                    
                    for (const element of allElements) {{
                        const text = element.textContent || element.innerText || '';
                        const numbers = text.match(/\\b\\d+(?:[,.]\\d+)?\\b/g) || [];
                        
                        // Look for elements with potential options data (3+ numbers)
                        if (numbers.length >= 3) {{
                            const numericValues = numbers.map(n => parseFloat(n.replace(/,/g, ''))).filter(n => !isNaN(n));
                            
                            // Find strike prices
                            const strikeIndices = [];
                            numericValues.forEach((num, index) => {{
                                if (num >= 15000 && num <= 30000) {{
                                    strikeIndices.push({{value: num, index: index}});
                                }}
                            }});
                            
                            // Process each unique strike
                            for (const strikeInfo of strikeIndices) {{
                                const strike = strikeInfo.value;
                                
                                if (!processedStrikes.has(strike)) {{
                                    processedStrikes.add(strike);
                                    
                                    const strikeIndex = strikeInfo.index;
                                    
                                    data.push({{
                                        strike: strike,
                                        call_volume: numericValues[strikeIndex - 3] || 0,
                                        call_oi: numericValues[strikeIndex - 2] || 0,
                                        call_premium: numericValues[strikeIndex - 1] || 0,
                                        put_premium: numericValues[strikeIndex + 1] || 0,
                                        put_oi: numericValues[strikeIndex + 2] || 0,
                                        put_volume: numericValues[strikeIndex + 3] || 0,
                                        extraction_method: 'comprehensive_search',
                                        source_element: element.tagName,
                                        source_classes: Array.from(element.classList).join('.'),
                                        total_numbers: numbers.length
                                    }});
                                }}
                            }}
                        }}
                    }}
                }}
                
                return data.sort((a, b) => a.strike - b.strike);
            }}''')
            
            if comprehensive_data:
                logger.info(f"🎉 COMPREHENSIVE SUCCESS! Extracted {len(comprehensive_data)} unique options:")
                
                if len(comprehensive_data) > 1:
                    min_strike = comprehensive_data[0]['strike']
                    max_strike = comprehensive_data[-1]['strike']
                    logger.info(f"📊 Complete strike range: ${min_strike:,.0f} - ${max_strike:,.0f}")
                
                # Show sample data
                for opt in comprehensive_data[:5]:
                    logger.info(f"  Strike ${opt['strike']:,.0f}: Call ${opt['call_premium']:.2f}, Put ${opt['put_premium']:.2f}")
                    logger.info(f"    Source: {opt['source_element']}.{opt['source_classes']} ({opt['total_numbers']} numbers)")
                
                return comprehensive_data
            else:
                logger.info("❌ No comprehensive data extracted")
        
        return []
        
    except Exception as e:
        logger.error(f"❌ Error in comprehensive search: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        await browser.close()

if __name__ == '__main__':
    result = asyncio.run(test_comprehensive_search())
    if result:
        print(f"\\n🎉 Final result: {len(result)} comprehensive options extracted!")
        
        # Data quality check
        with_call_data = sum(1 for opt in result if opt['call_premium'] > 0 or opt['call_volume'] > 0)
        with_put_data = sum(1 for opt in result if opt['put_premium'] > 0 or opt['put_volume'] > 0)
        
        print(f"📈 Options with Call data: {with_call_data}/{len(result)} ({with_call_data/len(result)*100:.1f}%)")
        print(f"📉 Options with Put data: {with_put_data}/{len(result)} ({with_put_data/len(result)*100:.1f}%)")
    else:
        print("\\n❌ No comprehensive options data found")