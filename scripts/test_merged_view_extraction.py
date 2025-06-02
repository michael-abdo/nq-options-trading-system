#!/usr/bin/env python3
"""
Test Merged View Extraction
Specifically target the merged view that shows complete options table
"""

import asyncio
import logging
from pyppeteer import launch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_merged_view_extraction():
    logger.info("🎯 Testing merged view extraction - targeting complete options table")
    
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
        # Navigate DIRECTLY to the merged view URL
        url = 'https://www.barchart.com/futures/quotes/NQM25/options/MC6M25?futuresOptionsView=merged'
        logger.info(f"🎯 Navigating DIRECTLY to merged view: {url}")
        await page.goto(url, {'waitUntil': 'networkidle2', 'timeout': 30000})
        
        # Wait for initial load
        await asyncio.sleep(10)
        
        # Force ensure merged view is selected
        logger.info("🔄 Ensuring merged view is active...")
        
        merged_view_activated = await page.evaluate('''() => {
            // Look for merged view controls and activate them
            const controls = [
                'button[data-value="merged"]',
                'input[value="merged"]',
                'option[value="merged"]',
                'a[href*="merged"]',
                '[ng-click*="merged"]'
            ];
            
            for (const selector of controls) {
                const elements = document.querySelectorAll(selector);
                for (const element of elements) {
                    try {
                        if (element.tagName === 'OPTION') {
                            element.selected = true;
                            element.parentElement.dispatchEvent(new Event('change'));
                        } else {
                            element.click();
                        }
                        return true;
                    } catch (e) {
                        continue;
                    }
                }
            }
            return false;
        }''')
        
        if merged_view_activated:
            logger.info("✅ Merged view control activated")
            await asyncio.sleep(5)  # Wait for data to load
        else:
            logger.info("ℹ️ No merged view control found or already active")
        
        # Wait longer for data to populate
        logger.info("⏳ Extended wait for merged view data...")
        await asyncio.sleep(15)
        
        # Check current URL to confirm merged view
        current_url = await page.url()
        logger.info(f"📍 Current URL: {current_url}")
        
        # Now try to find the complete options table
        logger.info("🔍 Searching for complete options table in merged view...")
        
        # Method 1: Look for table structure with many rows
        table_analysis = await page.evaluate('''() => {
            const results = [];
            
            // Search all possible table structures
            const tableSelectors = [
                'table',
                '[role="table"]',
                '.table',
                '.data-table',
                '.options-table',
                '.bc-table',
                'div[class*="table"]'
            ];
            
            for (const selector of tableSelectors) {
                const tables = document.querySelectorAll(selector);
                
                for (let i = 0; i < tables.length; i++) {
                    const table = tables[i];
                    const text = table.textContent || table.innerText || '';
                    
                    // Count strike prices in this table
                    const strikes = (text.match(/\\b2[01]\\d{3}(?:[,.]\\d+)?\\b/g) || []).length;
                    const rows = table.querySelectorAll('tr, .row, [class*="row"]').length;
                    
                    if (strikes >= 5 || rows >= 10) {
                        results.push({
                            selector: selector,
                            index: i,
                            element: table.tagName,
                            classes: Array.from(table.classList),
                            id: table.id || '',
                            strikes: strikes,
                            rows: rows,
                            textLength: text.length,
                            hasCallPut: /call.*put|put.*call/i.test(text),
                            hasVolume: /volume/i.test(text),
                            hasOI: /open.?interest|oi/i.test(text),
                            sampleText: text.substring(0, 200)
                        });
                    }
                }
            }
            
            return results.sort((a, b) => (b.strikes + b.rows) - (a.strikes + a.rows));
        }''')
        
        logger.info(f"📊 Found {len(table_analysis)} potential tables:")
        for i, table in enumerate(table_analysis[:5]):
            logger.info(f"  {i+1}. {table['element']}.{'.'.join(table['classes'][:2])}")
            logger.info(f"     {table['strikes']} strikes, {table['rows']} rows")
            logger.info(f"     Features: Call/Put={table['hasCallPut']}, Volume={table['hasVolume']}, OI={table['hasOI']}")
        
        # Method 2: Extract from the best table
        if table_analysis:
            best_table = table_analysis[0]
            logger.info(f"\n🎯 Extracting from best table: {best_table['element']} ({best_table['strikes']} strikes)")
            
            # Build selector for the best table
            if best_table['id']:
                table_selector = f"#{best_table['id']}"
            elif best_table['classes']:
                classes = '.'.join(best_table['classes'][:2])
                table_selector = f"{best_table['element'].lower()}.{classes}"
            else:
                table_selector = f"{best_table['selector']}:nth-of-type({best_table['index'] + 1})"
            
            logger.info(f"Using selector: {table_selector}")
            
            # Extract structured options data
            options_data = await page.evaluate(f'''() => {{
                const data = [];
                const table = document.querySelector('{table_selector}');
                
                if (table) {{
                    const rows = table.querySelectorAll('tr, .row, [class*="row"]');
                    
                    for (const row of rows) {{
                        const cells = row.querySelectorAll('td, th, .cell, [class*="cell"], span, div');
                        const rowText = row.textContent || row.innerText || '';
                        
                        // Look for strike prices in this row
                        const strikeMatches = rowText.match(/\\b(2[01]\\d{{3}}(?:[,.]\\d+)?)\\b/g);
                        
                        if (strikeMatches && cells.length >= 8) {{
                            for (const strikeStr of strikeMatches) {{
                                const strike = parseFloat(strikeStr.replace(/,/g, ''));
                                
                                if (strike >= 20000 && strike <= 23000) {{
                                    const cellTexts = Array.from(cells).map(cell => 
                                        (cell.textContent || cell.innerText || '').trim()
                                    );
                                    
                                    // Extract numbers from all cells
                                    const numbers = [];
                                    for (const cellText of cellTexts) {{
                                        const num = parseFloat(cellText.replace(/[,$%]/g, ''));
                                        if (!isNaN(num) && num > 0) {{
                                            numbers.push(num);
                                        }}
                                    }}
                                    
                                    // Find strike position in numbers
                                    const strikeIndex = numbers.findIndex(n => Math.abs(n - strike) < 1);
                                    
                                    if (strikeIndex !== -1) {{
                                        data.push({{
                                            strike: strike,
                                            call_last: numbers[strikeIndex - 6] || 0,
                                            call_bid: numbers[strikeIndex - 5] || 0,
                                            call_ask: numbers[strikeIndex - 4] || 0,
                                            call_volume: numbers[strikeIndex - 3] || 0,
                                            call_oi: numbers[strikeIndex - 2] || 0,
                                            call_iv: numbers[strikeIndex - 1] || 0,
                                            put_iv: numbers[strikeIndex + 1] || 0,
                                            put_oi: numbers[strikeIndex + 2] || 0,
                                            put_volume: numbers[strikeIndex + 3] || 0,
                                            put_ask: numbers[strikeIndex + 4] || 0,
                                            put_bid: numbers[strikeIndex + 5] || 0,
                                            put_last: numbers[strikeIndex + 6] || 0,
                                            raw_cells: cellTexts,
                                            raw_numbers: numbers,
                                            extraction_method: 'merged_view_table'
                                        }});
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
                
                // Remove duplicates and sort
                const uniqueData = [];
                const seenStrikes = new Set();
                
                for (const item of data) {{
                    if (!seenStrikes.has(item.strike)) {{
                        seenStrikes.add(item.strike);
                        uniqueData.push(item);
                    }}
                }}
                
                return uniqueData.sort((a, b) => a.strike - b.strike);
            }}''')
            
            if options_data and len(options_data) > 0:
                logger.info(f"🎉 MERGED VIEW SUCCESS! Extracted {len(options_data)} options:")
                
                # Show strike range
                if len(options_data) > 1:
                    min_strike = options_data[0]['strike']
                    max_strike = options_data[-1]['strike']
                    logger.info(f"📊 Strike range: ${min_strike:,.0f} - ${max_strike:,.0f}")
                
                # Check coverage in expected range (21,430-21,590)
                expected_min, expected_max = 21430, 21590
                in_range_strikes = [opt for opt in options_data if expected_min <= opt['strike'] <= expected_max]
                
                logger.info(f"📈 Expected range coverage: {len(in_range_strikes)}/{len(options_data)} strikes")
                if in_range_strikes:
                    logger.info(f"✅ Found {len(in_range_strikes)} strikes in target range!")
                
                # Show sample data
                logger.info(f"\n📋 SAMPLE OPTIONS DATA:")
                for opt in options_data[:8]:
                    logger.info(f"  Strike ${opt['strike']:,.0f}:")
                    logger.info(f"    Call: Last=${opt['call_last']:.2f}, Bid=${opt['call_bid']:.2f}, Ask=${opt['call_ask']:.2f}, Vol={opt['call_volume']:.0f}")
                    logger.info(f"    Put:  Last=${opt['put_last']:.2f}, Bid=${opt['put_bid']:.2f}, Ask=${opt['put_ask']:.2f}, Vol={opt['put_volume']:.0f}")
                
                return options_data
            else:
                logger.info("❌ No structured options data found in table")
        
        # Method 3: Fallback - comprehensive DOM search in merged view
        logger.info("\n🔍 Fallback: Comprehensive DOM search in merged view...")
        
        comprehensive_search = await page.evaluate('''() => {
            const data = [];
            const processedStrikes = new Set();
            
            // Get ALL text content and look for patterns
            const allText = document.body.textContent || document.body.innerText || '';
            
            // Find all strike prices
            const strikeMatches = allText.match(/\\b2[01]\\d{3}(?:[,.]\\d+)?\\b/g) || [];
            const uniqueStrikes = [...new Set(strikeMatches.map(s => s.replace(/,/g, '')))];
            const validStrikes = uniqueStrikes.filter(s => {
                const num = parseFloat(s);
                return num >= 20000 && num <= 23000;
            }).sort((a, b) => parseFloat(a) - parseFloat(b));
            
            return {
                totalStrikes: validStrikes.length,
                strikes: validStrikes,
                pageTextLength: allText.length,
                sampleStrikes: validStrikes.slice(0, 20)
            };
        }''')
        
        if comprehensive_search['totalStrikes'] > 0:
            logger.info(f"📊 Comprehensive search found {comprehensive_search['totalStrikes']} strikes:")
            logger.info(f"   Sample: {comprehensive_search['sampleStrikes'][:10]}")
            logger.info(f"   Page text: {comprehensive_search['pageTextLength']:,} characters")
            
            if comprehensive_search['totalStrikes'] >= 15:
                logger.info("✅ Substantial strike data found - merged view is working!")
                return comprehensive_search
        
        logger.info("❌ Limited data found even in merged view")
        return []
        
    except Exception as e:
        logger.error(f"❌ Error in merged view extraction: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        await browser.close()

if __name__ == '__main__':
    result = asyncio.run(test_merged_view_extraction())
    
    if result:
        if isinstance(result, list) and len(result) > 0:
            print(f"\n🎉 MERGED VIEW EXTRACTION SUCCESS!")
            print(f"📊 Extracted {len(result)} complete options")
            
            # Check target range coverage
            expected_strikes = list(range(21430, 21591, 10))  # Expected strikes
            actual_strikes = [opt['strike'] for opt in result]
            in_range = [s for s in actual_strikes if 21430 <= s <= 21590]
            
            print(f"🎯 Target range (21,430-21,590): {len(in_range)} strikes found")
            print(f"📈 Coverage: {len(in_range)/len(expected_strikes)*100:.1f}% of expected strikes")
            
        elif isinstance(result, dict) and result.get('totalStrikes', 0) > 0:
            print(f"\n✅ COMPREHENSIVE SEARCH SUCCESS!")
            print(f"📊 Found {result['totalStrikes']} strikes in merged view")
            print(f"🎯 This confirms the merged view loads more data")
            
    else:
        print("\n❌ Merged view extraction failed")
        print("🤔 The complete options table may require authentication or different approach")