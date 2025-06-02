#!/usr/bin/env python3
"""
Deep DOM Investigation
Wait longer, try different timing, and find where the complete table data is actually stored
"""

import asyncio
import logging
from pyppeteer import launch
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def deep_dom_investigation():
    logger.info("🔍 Deep DOM investigation - finding the complete options table")
    
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
        
        # EXTENDED WAIT AND MONITORING
        logger.info("⏳ Extended waiting and monitoring for data to load...")
        
        for wait_time in [5, 10, 15, 20, 30, 45, 60]:
            logger.info(f"📊 CHECKING AT {wait_time} SECONDS...")
            await asyncio.sleep(5 if wait_time == 5 else 5)  # Incremental waits
            
            # Check 1: Count all strike prices on page
            strike_count = await page.evaluate('''() => {
                const text = document.body.textContent || document.body.innerText || '';
                const strikes = text.match(/\\b2[01]\\d{3}(?:[,.]\\d+)?\\b/g) || [];
                const uniqueStrikes = [...new Set(strikes.map(s => s.replace(/,/g, '')))];
                return uniqueStrikes.filter(s => {
                    const num = parseFloat(s);
                    return num >= 20000 && num <= 23000;
                }).length;
            }''')
            
            logger.info(f"   Strike prices found: {strike_count}")
            
            # Check 2: Look for table structures
            table_info = await page.evaluate('''() => {
                return {
                    tables: document.querySelectorAll('table').length,
                    rows: document.querySelectorAll('tr').length,
                    divs_with_data: document.querySelectorAll('div').length,
                    text_bindings: document.querySelectorAll('text-binding').length,
                    ng_repeats: document.querySelectorAll('[ng-repeat]').length
                };
            }''')
            
            logger.info(f"   Tables: {table_info['tables']}, Rows: {table_info['rows']}, Text-bindings: {table_info['text_bindings']}")
            
            # Check 3: Angular scope data
            angular_data = await page.evaluate('''() => {
                try {
                    const elements = document.querySelectorAll('[data-ng-controller]');
                    for (const element of elements) {
                        try {
                            const scope = angular.element(element).scope();
                            if (scope && scope.data && scope.data.calls) {
                                return {
                                    found: true,
                                    calls: scope.data.calls.data ? scope.data.calls.data.length : 0,
                                    puts: scope.data.puts ? scope.data.puts.data.length : 0
                                };
                            }
                        } catch (e) {
                            continue;
                        }
                    }
                    return { found: false, calls: 0, puts: 0 };
                } catch (e) {
                    return { found: false, error: e.message };
                }
            }''')
            
            if angular_data['found']:
                logger.info(f"   ✅ Angular data found: {angular_data['calls']} calls, {angular_data['puts']} puts")
                break
            else:
                logger.info(f"   ❌ No Angular data yet")
            
            # Check 4: If we have good strike count, try extraction
            if strike_count >= 15:
                logger.info(f"🎯 Good strike count detected ({strike_count}), attempting extraction...")
                break
        
        # COMPREHENSIVE TABLE SEARCH
        logger.info("\n🔍 COMPREHENSIVE TABLE SEARCH...")
        
        # Method 1: Find ALL tables and analyze them
        all_tables = await page.evaluate('''() => {
            const results = [];
            const tables = document.querySelectorAll('table, [role="table"], .table, [class*="table"]');
            
            for (let i = 0; i < tables.length; i++) {
                const table = tables[i];
                const text = table.textContent || table.innerText || '';
                const rows = table.querySelectorAll('tr, [role="row"], .row');
                
                // Count strike-like numbers
                const strikes = (text.match(/\\b2[01]\\d{3}(?:[,.]\\d+)?\\b/g) || []).length;
                
                if (strikes > 0) {
                    results.push({
                        index: i,
                        tag: table.tagName,
                        classes: Array.from(table.classList),
                        id: table.id || '',
                        rowCount: rows.length,
                        strikeCount: strikes,
                        textLength: text.length,
                        hasVolume: /volume/i.test(text),
                        hasOpenInt: /open.?int/i.test(text),
                        hasBidAsk: /bid.*ask/i.test(text),
                        sampleText: text.substring(0, 200)
                    });
                }
            }
            
            return results.sort((a, b) => b.strikeCount - a.strikeCount);
        }''')
        
        logger.info(f"📋 Found {len(all_tables)} tables with strikes:")
        for i, table in enumerate(all_tables[:5]):
            logger.info(f"  {i+1}. {table['tag']}.{'.'.join(table['classes'][:2])} - {table['strikeCount']} strikes, {table['rowCount']} rows")
            logger.info(f"     Volume: {table['hasVolume']}, OI: {table['hasOpenInt']}, Bid/Ask: {table['hasBidAsk']}")
        
        # Method 2: Extract from the best table if found
        if all_tables:
            best_table = all_tables[0]
            logger.info(f"\n🎯 Extracting from best table (index {best_table['index']})...")
            
            # Create specific selector
            if best_table['id']:
                selector = f"#{best_table['id']}"
            elif best_table['classes']:
                classes = '.'.join(best_table['classes'][:2])
                selector = f"{best_table['tag'].lower()}.{classes}"
            else:
                selector = f"{best_table['tag'].lower()}:nth-of-type({best_table['index'] + 1})"
            
            logger.info(f"Using selector: {selector}")
            
            table_data = await page.evaluate(f'''() => {{
                const data = [];
                const table = document.querySelector('{selector}');
                
                if (table) {{
                    const rows = table.querySelectorAll('tr, [role="row"], .row');
                    
                    for (const row of rows) {{
                        const cells = row.querySelectorAll('td, th, [role="cell"], .cell');
                        const rowText = row.textContent || row.innerText || '';
                        
                        // Look for strike prices in this row
                        const strikeMatch = rowText.match(/\\b(2[01]\\d{{3}}(?:[,.]\\d+)?)\\b/);
                        
                        if (strikeMatch && cells.length >= 5) {{
                            const strike = parseFloat(strikeMatch[1].replace(/,/g, ''));
                            
                            if (strike >= 20000 && strike <= 23000) {{
                                const cellTexts = Array.from(cells).map(cell => 
                                    (cell.textContent || cell.innerText || '').trim()
                                );
                                
                                // Try to parse standard options table format
                                const extractNumber = (text) => {{
                                    const cleaned = text.replace(/[,$%]/g, '');
                                    const num = parseFloat(cleaned);
                                    return isNaN(num) ? 0 : num;
                                }};
                                
                                data.push({{
                                    strike: strike,
                                    raw_cells: cellTexts,
                                    cell_count: cells.length,
                                    row_text: rowText.trim().substring(0, 200)
                                }});
                            }}
                        }}
                    }}
                }}
                
                return data.sort((a, b) => a.strike - b.strike);
            }}''')
            
            if table_data:
                logger.info(f"🎉 FOUND TABLE DATA! {len(table_data)} options extracted:")
                for opt in table_data[:10]:
                    logger.info(f"  Strike ${opt['strike']:,.0f}: {opt['cell_count']} cells")
                    logger.info(f"    Cells: {opt['raw_cells'][:8]}")
                
                return table_data
        
        # Method 3: Brute force - check every element with substantial strike data
        logger.info("\n🔍 BRUTE FORCE ELEMENT SEARCH...")
        
        comprehensive_data = await page.evaluate('''() => {
            const results = [];
            const allElements = document.querySelectorAll('*');
            
            for (const element of allElements) {
                const text = element.textContent || element.innerText || '';
                
                // Skip if too little text
                if (text.length < 100) continue;
                
                // Count strikes in this element
                const strikes = (text.match(/\\b2[01]\\d{3}(?:[,.]\\d+)?\\b/g) || []);
                
                if (strikes.length >= 5) {  // Element with multiple strikes
                    const uniqueStrikes = [...new Set(strikes.map(s => s.replace(/,/g, '')))];
                    const validStrikes = uniqueStrikes.filter(s => {
                        const num = parseFloat(s);
                        return num >= 20000 && num <= 23000;
                    }).sort();
                    
                    if (validStrikes.length >= 5) {
                        results.push({
                            tag: element.tagName,
                            classes: Array.from(element.classList),
                            id: element.id || '',
                            strikeCount: validStrikes.length,
                            strikes: validStrikes,
                            textLength: text.length,
                            childCount: element.children.length,
                            sampleText: text.substring(0, 300)
                        });
                    }
                }
            }
            
            return results.sort((a, b) => b.strikeCount - a.strikeCount);
        }''')
        
        if comprehensive_data:
            logger.info(f"🎯 BRUTE FORCE FOUND {len(comprehensive_data)} elements with 5+ strikes:")
            for i, elem in enumerate(comprehensive_data[:3]):
                logger.info(f"  {i+1}. {elem['tag']}.{'.'.join(elem['classes'][:2])}")
                logger.info(f"     {elem['strikeCount']} strikes: {elem['strikes'][:8]}")
                logger.info(f"     {elem['childCount']} children, {elem['textLength']:,} chars")
                logger.info(f"     Sample: {elem['sampleText'][:100]}...")
        
        # If we found comprehensive data, extract structured options
        if comprehensive_data:
            best_element = comprehensive_data[0]
            logger.info(f"\n🎯 EXTRACTING FROM BEST ELEMENT: {best_element['tag']} ({best_element['strikeCount']} strikes)")
            
            # Final extraction attempt
            final_data = await page.evaluate(f'''() => {{
                const strikes = {json.dumps(best_element['strikes'])};
                const data = [];
                
                // For each strike, try to find associated data
                for (const strikeStr of strikes) {{
                    const strike = parseFloat(strikeStr);
                    
                    // Find elements containing this exact strike
                    const allElements = document.querySelectorAll('*');
                    for (const element of allElements) {{
                        const text = element.textContent || element.innerText || '';
                        
                        if (text.includes(strikeStr)) {{
                            // Extract numbers from this element and surrounding context
                            const numbers = text.match(/\\b\\d+(?:[,.]\\d+)?\\b/g) || [];
                            const numericValues = numbers.map(n => parseFloat(n.replace(/,/g, ''))).filter(n => !isNaN(n));
                            
                            // Find the strike in the numbers
                            const strikeIndex = numericValues.findIndex(n => Math.abs(n - strike) < 1);
                            
                            if (strikeIndex !== -1) {{
                                data.push({{
                                    strike: strike,
                                    call_volume: numericValues[strikeIndex - 6] || 0,
                                    call_oi: numericValues[strikeIndex - 5] || 0,
                                    call_premium: numericValues[strikeIndex - 4] || 0,
                                    call_bid: numericValues[strikeIndex - 3] || 0,
                                    call_ask: numericValues[strikeIndex - 2] || 0,
                                    call_last: numericValues[strikeIndex - 1] || 0,
                                    put_last: numericValues[strikeIndex + 1] || 0,
                                    put_bid: numericValues[strikeIndex + 2] || 0,
                                    put_ask: numericValues[strikeIndex + 3] || 0,
                                    put_premium: numericValues[strikeIndex + 4] || 0,
                                    put_oi: numericValues[strikeIndex + 5] || 0,
                                    put_volume: numericValues[strikeIndex + 6] || 0,
                                    source_element: element.tagName,
                                    total_numbers: numericValues.length,
                                    context: text.substring(Math.max(0, text.indexOf(strikeStr) - 50), 
                                                          text.indexOf(strikeStr) + 100)
                                }});
                                break; // Found this strike, move to next
                            }}
                        }}
                    }}
                }}
                
                return data.sort((a, b) => a.strike - b.strike);
            }}''')
            
            if final_data:
                logger.info(f"🎉 FINAL EXTRACTION SUCCESS! {len(final_data)} complete options extracted:")
                
                # Show range
                if len(final_data) > 1:
                    min_strike = final_data[0]['strike']
                    max_strike = final_data[-1]['strike']
                    logger.info(f"📊 Strike range: ${min_strike:,.0f} - ${max_strike:,.0f}")
                
                # Show sample data
                for opt in final_data[:5]:
                    logger.info(f"  Strike ${opt['strike']:,.0f}:")
                    logger.info(f"    Call: Last=${opt['call_last']:.2f}, Bid=${opt['call_bid']:.2f}, Ask=${opt['call_ask']:.2f}, Vol={opt['call_volume']:.0f}")
                    logger.info(f"    Put:  Last=${opt['put_last']:.2f}, Bid=${opt['put_bid']:.2f}, Ask=${opt['put_ask']:.2f}, Vol={opt['put_volume']:.0f}")
                
                return final_data
        
        logger.info("❌ No comprehensive table data found despite extended investigation")
        return []
        
    except Exception as e:
        logger.error(f"❌ Error in deep DOM investigation: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        await browser.close()

if __name__ == '__main__':
    result = asyncio.run(deep_dom_investigation())
    
    if result:
        print(f"\n🎉 DEEP INVESTIGATION SUCCESS!")
        print(f"🎯 Extracted {len(result)} complete options from the loaded DOM")
        
        # Check if we got the expected range
        expected_min, expected_max = 21430, 21590
        actual_strikes = [opt['strike'] for opt in result]
        in_range = [s for s in actual_strikes if expected_min <= s <= expected_max]
        
        print(f"📊 Expected range (21,430-21,590): {len(in_range)}/{len(actual_strikes)} strikes")
        print(f"📈 Coverage: {len(in_range)/17*100:.1f}% of expected 17 strikes")
        
        if len(in_range) >= 10:
            print("✅ SUCCESS: Found substantial options data in expected range!")
        else:
            print("⚠️ PARTIAL: Found options data but may need refinement")
    else:
        print("\n❌ Deep investigation could not locate the complete options table")
        print("🤔 The data in the screenshot may load through different mechanisms")