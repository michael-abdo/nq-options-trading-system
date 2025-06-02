#!/usr/bin/env python3
"""
Extract Complete Options Table
Target the actual full options table with all strikes and complete data
"""

import asyncio
import logging
from pyppeteer import launch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def extract_complete_options_table():
    logger.info("🎯 Targeting the COMPLETE options table extraction")
    
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
        
        # First, let's see if we can find the actual options table
        logger.info("🔍 Searching for the actual options table structure...")
        
        # Method 1: Look for the complete options table
        table_search = await page.evaluate('''() => {
            const results = {
                tables_found: 0,
                potential_options_tables: [],
                best_table_info: null
            };
            
            // Search all tables
            const tables = document.querySelectorAll('table, [role="table"], .table, [class*="table"]');
            results.tables_found = tables.length;
            
            for (const table of tables) {
                const text = table.textContent || table.innerText || '';
                const rows = table.querySelectorAll('tr, [role="row"], .row, [class*="row"]');
                
                // Look for options table indicators
                const hasStrike = /strike/i.test(text);
                const hasCallPut = /call|put/i.test(text);
                const hasVolume = /volume/i.test(text);
                const hasBidAsk = /bid.*ask|ask.*bid/i.test(text);
                const hasOpenInt = /open.?int/i.test(text);
                
                // Count rows with strike-like numbers
                let strikeRows = 0;
                for (const row of rows) {
                    const rowText = row.textContent || row.innerText || '';
                    if (/21[,\\s]*[4-6]\\d{2}/.test(rowText)) {
                        strikeRows++;
                    }
                }
                
                if (strikeRows >= 5) {  // Likely options table
                    const tableInfo = {
                        element: table.tagName,
                        classes: Array.from(table.classList),
                        id: table.id || '',
                        totalRows: rows.length,
                        strikeRows: strikeRows,
                        hasStrike: hasStrike,
                        hasCallPut: hasCallPut,
                        hasVolume: hasVolume,
                        hasBidAsk: hasBidAsk,
                        hasOpenInt: hasOpenInt,
                        score: strikeRows + (hasStrike ? 5 : 0) + (hasCallPut ? 5 : 0) + (hasVolume ? 3 : 0) + (hasBidAsk ? 3 : 0) + (hasOpenInt ? 3 : 0)
                    };
                    
                    results.potential_options_tables.push(tableInfo);
                }
            }
            
            // Find the best table
            if (results.potential_options_tables.length > 0) {
                results.best_table_info = results.potential_options_tables.reduce((best, current) => 
                    current.score > best.score ? current : best
                );
            }
            
            return results;
        }''')
        
        logger.info(f"📊 TABLE SEARCH RESULTS:")
        logger.info(f"   Total tables found: {table_search['tables_found']}")
        logger.info(f"   Potential options tables: {len(table_search['potential_options_tables'])}")
        
        if table_search['best_table_info']:
            best = table_search['best_table_info']
            logger.info(f"   Best table: {best['element']}.{'.'.join(best['classes'][:2])}")
            logger.info(f"   Score: {best['score']}, Rows: {best['totalRows']}, Strike rows: {best['strikeRows']}")
            logger.info(f"   Features: Strike={best['hasStrike']}, Call/Put={best['hasCallPut']}, Volume={best['hasVolume']}")
        
        # Method 2: If we found a good table, extract from it
        if table_search['best_table_info']:
            best = table_search['best_table_info']
            
            # Create selector for the best table
            if best['id']:
                selector = f"#{best['id']}"
            elif best['classes']:
                selector = f"{best['element'].lower()}.{'.'.join(best['classes'][:2])}"
            else:
                selector = best['element'].lower()
            
            logger.info(f"🎯 Extracting from best table: {selector}")
            
            options_data = await page.evaluate(f'''() => {{
                const data = [];
                const table = document.querySelector('{selector}');
                
                if (table) {{
                    const rows = table.querySelectorAll('tr, [role="row"], .row, [class*="row"]');
                    
                    for (const row of rows) {{
                        const cells = row.querySelectorAll('td, th, [role="cell"], .cell, [class*="cell"]');
                        const rowText = row.textContent || row.innerText || '';
                        
                        // Look for rows with strike prices in the expected range
                        const strikeMatch = rowText.match(/21[,\\s]*[4-6]\\d{{2}}[,\\s]*\\.?\\d*/);
                        
                        if (strikeMatch && cells.length >= 8) {{
                            const cellTexts = Array.from(cells).map(cell => (cell.textContent || cell.innerText || '').trim());
                            
                            // Try to parse the strike price
                            const strikeStr = strikeMatch[0].replace(/[,\\s]/g, '');
                            const strike = parseFloat(strikeStr);
                            
                            if (strike >= 21000 && strike <= 22000) {{
                                // Try to extract other data from cells
                                const extractNumber = (text) => {{
                                    const num = parseFloat(text.replace(/[,$]/g, ''));
                                    return isNaN(num) ? 0 : num;
                                }};
                                
                                // Common column patterns for options tables
                                let optionData = {{
                                    strike: strike,
                                    type: rowText.includes('C') ? 'call' : (rowText.includes('P') ? 'put' : 'unknown'),
                                    open: 0,
                                    high: 0,
                                    low: 0,
                                    last: 0,
                                    change: 0,
                                    bid: 0,
                                    ask: 0,
                                    volume: 0,
                                    open_interest: 0,
                                    premium: 0,
                                    last_trade: '',
                                    raw_cells: cellTexts,
                                    cell_count: cells.length
                                }};
                                
                                // Try to map common patterns
                                for (let i = 0; i < cellTexts.length; i++) {{
                                    const cell = cellTexts[i];
                                    const num = extractNumber(cell);
                                    
                                    // Look for recognizable patterns
                                    if (cell.includes(':') && cell.includes('ET')) {{
                                        optionData.last_trade = cell;
                                    }} else if (num > 0) {{
                                        // Try to identify what this number represents
                                        if (num > 10000) {{
                                            // Likely volume or open interest
                                            if (optionData.volume === 0) optionData.volume = num;
                                            else if (optionData.open_interest === 0) optionData.open_interest = num;
                                        }} else if (num > 100) {{
                                            // Likely premium or price
                                            if (optionData.premium === 0) optionData.premium = num;
                                            else if (optionData.last === 0) optionData.last = num;
                                        }} else {{
                                            // Smaller numbers - could be bid/ask/change
                                            if (optionData.bid === 0) optionData.bid = num;
                                            else if (optionData.ask === 0) optionData.ask = num;
                                        }}
                                    }}
                                }}
                                
                                data.push(optionData);
                            }}
                        }}
                    }}
                }}
                
                return data;
            }}''')
            
            if options_data:
                logger.info(f"🎉 SUCCESS! Extracted {len(options_data)} options from table:")
                logger.info(f"📊 Strike range: ${min(opt['strike'] for opt in options_data):,.0f} - ${max(opt['strike'] for opt in options_data):,.0f}")
                
                # Show detailed breakdown
                calls = [opt for opt in options_data if opt['type'] == 'call']
                puts = [opt for opt in options_data if opt['type'] == 'put']
                
                logger.info(f"📈 Calls: {len(calls)} options")
                logger.info(f"📉 Puts: {len(puts)} options")
                
                # Show sample data
                logger.info(f"\\n📋 SAMPLE EXTRACTED DATA:")
                for i, opt in enumerate(options_data[:5]):
                    logger.info(f"  {i+1}. Strike ${opt['strike']:,.0f} {opt['type'].upper()}:")
                    logger.info(f"     Last: ${opt['last']:.2f}, Bid: ${opt['bid']:.2f}, Ask: ${opt['ask']:.2f}")
                    logger.info(f"     Volume: {opt['volume']:,}, OI: {opt['open_interest']:,}")
                    logger.info(f"     Cells: {opt['cell_count']}, Trade: {opt['last_trade']}")
                
                return options_data
            else:
                logger.info("❌ No options data extracted from table")
        
        # Method 3: Fallback - comprehensive DOM search
        logger.info("\\n🔍 Fallback: Comprehensive DOM search for options data...")
        
        comprehensive_search = await page.evaluate('''() => {
            const data = [];
            const processedStrikes = new Set();
            
            // Look for any element containing options-like data
            const allElements = document.querySelectorAll('*');
            
            for (const element of allElements) {
                const text = element.textContent || element.innerText || '';
                
                // Look for text containing multiple options indicators
                if (/21[4-6]\\d{2}/.test(text) && 
                    (/volume|vol/i.test(text) || /bid|ask/i.test(text) || /open|high|low/i.test(text))) {
                    
                    const strikeMatches = text.match(/21[4-6]\\d{2}(?:\\.\\d{2})?/g) || [];
                    
                    for (const strikeStr of strikeMatches) {
                        const strike = parseFloat(strikeStr);
                        
                        if (!processedStrikes.has(strike) && strike >= 21400 && strike <= 21600) {
                            processedStrikes.add(strike);
                            
                            data.push({
                                strike: strike,
                                source: 'comprehensive_search',
                                element: element.tagName,
                                classes: Array.from(element.classList).join('.'),
                                text_sample: text.substring(0, 200)
                            });
                        }
                    }
                }
            }
            
            return data.sort((a, b) => a.strike - b.strike);
        }''')
        
        if comprehensive_search:
            logger.info(f"🎯 Comprehensive search found {len(comprehensive_search)} potential strikes:")
            for strike_data in comprehensive_search[:10]:
                logger.info(f"   ${strike_data['strike']:,.0f} in {strike_data['element']}.{strike_data['classes'][:50]}")
        
        return comprehensive_search or []
        
    except Exception as e:
        logger.error(f"❌ Error in complete table extraction: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        await browser.close()

if __name__ == '__main__':
    result = asyncio.run(extract_complete_options_table())
    
    print(f"\\n🎯 FINAL ASSESSMENT:")
    print(f"="*50)
    
    if result:
        print(f"✅ Found {len(result)} options in the expected range")
        strikes = [opt['strike'] for opt in result]
        print(f"📊 Range: ${min(strikes):,.0f} - ${max(strikes):,.0f}")
        
        # Check coverage vs what you showed me
        expected_strikes = list(range(21430, 21591, 10))  # 21430, 21440, 21450, etc.
        found_strikes = strikes
        
        coverage = len([s for s in expected_strikes if s in found_strikes]) / len(expected_strikes) * 100
        print(f"📈 Coverage of expected strikes: {coverage:.1f}%")
        
        if coverage < 50:
            print(f"❌ Still missing most of the actual options table data")
            print(f"🎯 Need to find the real table with 20+ strikes and complete OHLC/bid/ask data")
        else:
            print(f"✅ Good progress toward extracting the complete options table")
    else:
        print(f"❌ No options found - need to locate the actual table structure")
        print(f"🎯 The complete options table with 20+ strikes is not being captured")