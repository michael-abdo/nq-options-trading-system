#!/usr/bin/env python3
"""
Complete Options Chain Extraction
Find and extract the complete options table with all strikes
"""

import asyncio
import logging
import re
from pyppeteer import launch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_complete_options_extraction():
    logger.info("🚀 Testing complete options chain extraction")
    
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
        
        logger.info("🔍 Searching for the actual options table structure...")
        
        # Method 1: Look for structured table data (rows with consistent patterns)
        table_structure = await page.evaluate('''() => {
            const results = [];
            
            // Look for table rows that might contain options data
            const allRows = document.querySelectorAll('tr, div[class*="row"], div[class*="table"]');
            
            for (const row of allRows) {
                const text = row.textContent || row.innerText || '';
                const cells = row.querySelectorAll('td, div[class*="cell"], span');
                
                // Look for rows that might represent options (with strike prices)
                if (/21[,\\s]*[3-7]\\d{2}[,\\s]*\\.\\d{2}/.test(text)) {
                    const numbers = text.match(/\\d+(?:[,.]\\d+)?/g) || [];
                    
                    // Check if this looks like a complete options row (7+ numbers)
                    if (numbers.length >= 7) {
                        const numericValues = numbers.map(n => parseFloat(n.replace(/,/g, ''))).filter(n => !isNaN(n));
                        const strikeIndex = numericValues.findIndex(n => n >= 15000 && n <= 30000);
                        
                        if (strikeIndex !== -1) {
                            results.push({
                                tag: row.tagName,
                                classes: Array.from(row.classList),
                                cellCount: cells.length,
                                numbers: numbers,
                                numericValues: numericValues,
                                strikeIndex: strikeIndex,
                                strike: numericValues[strikeIndex],
                                parentTag: row.parentElement?.tagName || '',
                                parentClasses: Array.from(row.parentElement?.classList || [])
                            });
                        }
                    }
                }
            }
            
            return results;
        }''')
        
        if table_structure:
            logger.info(f"🎯 Found {len(table_structure)} structured rows:")
            for i, row in enumerate(table_structure[:5]):  # Show first 5
                logger.info(f"  {i+1}. {row['tag']}.{'.'.join(row['classes'])} - {row['cellCount']} cells, Strike: ${row['strike']:,.0f}")
                logger.info(f"     Numbers: {row['numbers'][:10]}")
        
        # Method 2: Look for specific options table containers
        logger.info("\\n🔍 Searching for options table containers...")
        
        container_info = await page.evaluate('''() => {
            const containers = [];
            
            // Look for elements that might contain the options table
            const selectors = [
                '.bc-datatable',
                '.options-table',
                '.bc-table-scrollable',
                '[class*="option"]',
                '[class*="table"]',
                '[data-ng-repeat]',
                '.bc-datatable-middleware-wrapper'
            ];
            
            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                for (const element of elements) {
                    const text = element.textContent || element.innerText || '';
                    const rows = element.querySelectorAll('tr, div[class*="row"]');
                    
                    // Count how many strike prices are in this container
                    const strikeMatches = text.match(/21[,\\s]*[3-7]\\d{2}[,\\s]*\\.\\d{2}/g) || [];
                    
                    if (strikeMatches.length > 2) {  // More than just summary data
                        containers.push({
                            selector: selector,
                            classes: Array.from(element.classList),
                            id: element.id || '',
                            rowCount: rows.length,
                            strikeCount: strikeMatches.length,
                            strikes: strikeMatches.slice(0, 5),  // First 5 strikes
                            hasAngular: element.hasAttribute('data-ng-repeat') || element.hasAttribute('ng-repeat'),
                            textLength: text.length
                        });
                    }
                }
            }
            
            return containers;
        }''')
        
        if container_info:
            logger.info(f"🎯 Found {len(container_info)} potential table containers:")
            for i, container in enumerate(container_info):
                logger.info(f"  {i+1}. {container['selector']} - {container['strikeCount']} strikes, {container['rowCount']} rows")
                logger.info(f"     Strikes: {container['strikes']}")
                logger.info(f"     Angular: {container['hasAngular']}, Text length: {container['textLength']}")
        
        # Method 3: Try to extract from the most promising container
        if container_info:
            best_container = max(container_info, key=lambda x: x['strikeCount'])
            logger.info(f"\\n🎯 Extracting from best container: {best_container['selector']} ({best_container['strikeCount']} strikes)")
            
            options_data = await page.evaluate(f'''() => {{
                const data = [];
                const container = document.querySelector('{best_container['selector']}');
                
                if (container) {{
                    // Look for all rows within this container
                    const rows = container.querySelectorAll('tr, div[class*="row"]');
                    
                    for (const row of rows) {{
                        const text = row.textContent || row.innerText || '';
                        const numbers = text.match(/\\d+(?:[,.]\\d+)?/g) || [];
                        
                        if (numbers.length >= 5) {{  // Potential options row
                            const numericValues = numbers.map(n => parseFloat(n.replace(/,/g, ''))).filter(n => !isNaN(n));
                            const strikeIndex = numericValues.findIndex(n => n >= 15000 && n <= 30000);
                            
                            if (strikeIndex !== -1) {{
                                const strike = numericValues[strikeIndex];
                                
                                data.push({{
                                    strike: strike,
                                    call_volume: numericValues[strikeIndex - 3] || 0,
                                    call_oi: numericValues[strikeIndex - 2] || 0,
                                    call_premium: numericValues[strikeIndex - 1] || 0,
                                    put_premium: numericValues[strikeIndex + 1] || 0,
                                    put_oi: numericValues[strikeIndex + 2] || 0,
                                    put_volume: numericValues[strikeIndex + 3] || 0,
                                    source: 'best_container',
                                    row_text: text.trim().substring(0, 100)
                                }});
                            }}
                        }}
                    }}
                }}
                
                return data;
            }}''')
            
            if options_data:
                # Remove duplicates and sort
                unique_options = {}
                for opt in options_data:
                    strike = opt['strike']
                    if strike not in unique_options:
                        unique_options[strike] = opt
                
                sorted_options = sorted(unique_options.values(), key=lambda x: x['strike'])
                
                logger.info(f"🎉 SUCCESS! Extracted {len(sorted_options)} unique options:")
                logger.info(f"📊 Strike range: ${sorted_options[0]['strike']:,.0f} - ${sorted_options[-1]['strike']:,.0f}")
                
                # Show sample data
                for opt in sorted_options[:5]:
                    logger.info(f"  Strike ${opt['strike']:,.0f}: Call ${opt['call_premium']:.2f}, Put ${opt['put_premium']:.2f}")
                
                # Check data quality
                with_call_data = sum(1 for opt in sorted_options if opt['call_premium'] > 0 or opt['call_volume'] > 0)
                with_put_data = sum(1 for opt in sorted_options if opt['put_premium'] > 0 or opt['put_volume'] > 0)
                
                logger.info(f"📈 Options with Call data: {with_call_data}/{len(sorted_options)} ({with_call_data/len(sorted_options)*100:.1f}%)")
                logger.info(f"📉 Options with Put data: {with_put_data}/{len(sorted_options)} ({with_put_data/len(sorted_options)*100:.1f}%)")
                
                return sorted_options
            else:
                logger.info("❌ No options data extracted from best container")
        
        # Method 4: Try Angular scope extraction as fallback
        logger.info("\\n🔍 Trying Angular scope extraction...")
        
        angular_data = await page.evaluate('''() => {
            const results = [];
            
            try {
                if (typeof angular !== 'undefined') {
                    const ngElements = document.querySelectorAll('[ng-controller], [data-ng-controller]');
                    
                    for (const element of ngElements) {
                        try {
                            const scope = angular.element(element).scope();
                            if (scope && scope.data) {
                                // Look for calls and puts data
                                if (scope.data.calls && scope.data.calls.data) {
                                    const calls = scope.data.calls.data;
                                    const puts = scope.data.puts ? scope.data.puts.data : [];
                                    
                                    // Merge calls and puts by strike
                                    const options = {};
                                    
                                    for (const call of calls) {
                                        const strike = parseFloat(call.strike);
                                        if (strike >= 15000 && strike <= 30000) {
                                            options[strike] = {
                                                strike: strike,
                                                call_volume: parseInt(call.volume || 0),
                                                call_oi: parseInt(call.openInterest || 0),
                                                call_premium: parseFloat(call.lastPrice || 0),
                                                put_volume: 0,
                                                put_oi: 0,
                                                put_premium: 0,
                                                source: 'angular_scope'
                                            };
                                        }
                                    }
                                    
                                    for (const put of puts) {
                                        const strike = parseFloat(put.strike);
                                        if (strike >= 15000 && strike <= 30000) {
                                            if (options[strike]) {
                                                options[strike].put_volume = parseInt(put.volume || 0);
                                                options[strike].put_oi = parseInt(put.openInterest || 0);
                                                options[strike].put_premium = parseFloat(put.lastPrice || 0);
                                            } else {
                                                options[strike] = {
                                                    strike: strike,
                                                    call_volume: 0,
                                                    call_oi: 0,
                                                    call_premium: 0,
                                                    put_volume: parseInt(put.volume || 0),
                                                    put_oi: parseInt(put.openInterest || 0),
                                                    put_premium: parseFloat(put.lastPrice || 0),
                                                    source: 'angular_scope'
                                                };
                                            }
                                        }
                                    }
                                    
                                    results.push(...Object.values(options));
                                }
                            }
                        } catch (e) {
                            // Skip this element
                        }
                    }
                }
            } catch (e) {
                console.log('Angular extraction error:', e.message);
            }
            
            return results;
        }''')
        
        if angular_data:
            logger.info(f"🎉 Angular extraction SUCCESS! Found {len(angular_data)} options")
            sorted_angular = sorted(angular_data, key=lambda x: x['strike'])
            logger.info(f"📊 Strike range: ${sorted_angular[0]['strike']:,.0f} - ${sorted_angular[-1]['strike']:,.0f}")
            
            # Show sample
            for opt in sorted_angular[:5]:
                logger.info(f"  Strike ${opt['strike']:,.0f}: Call ${opt['call_premium']:.2f}, Put ${opt['put_premium']:.2f}")
            
            return sorted_angular
        else:
            logger.info("❌ No Angular scope data found")
        
        return []
        
    except Exception as e:
        logger.error(f"❌ Error in complete options extraction test: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        await browser.close()

if __name__ == '__main__':
    result = asyncio.run(test_complete_options_extraction())
    if result:
        print(f"\\n🎉 Final result: {len(result)} complete options extracted!")
    else:
        print("\\n❌ No complete options data found")