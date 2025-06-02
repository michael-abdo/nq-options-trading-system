#!/usr/bin/env python3
"""
Analyze Extraction vs Visible Data
Compare what we're extracting vs what's actually shown in the options table
"""

import asyncio
import logging
from pyppeteer import launch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def analyze_extraction_vs_visible():
    logger.info("🔍 Analyzing extraction vs visible data")
    
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
        
        logger.info("📊 ANALYSIS: What's visible vs what we're extracting")
        logger.info("="*60)
        
        # 1. Count all strike prices visible in text content
        visible_strikes = await page.evaluate('''() => {
            const text = document.body.textContent || document.body.innerText || '';
            
            // Find all potential strike prices
            const strikeMatches = text.match(/\\b21[,\\s]*[0-9]{3}[,\\s]*(?:\\.\\d{2})?\\b/g) || [];
            const uniqueStrikes = [...new Set(strikeMatches.map(s => s.replace(/[,\\s]/g, '')))];
            const validStrikes = uniqueStrikes.filter(s => {
                const num = parseFloat(s);
                return num >= 20000 && num <= 23000;  // Reasonable NQ range
            }).sort();
            
            return validStrikes;
        }''')
        
        logger.info(f"🎯 VISIBLE STRIKES on page: {len(visible_strikes)} strikes")
        if visible_strikes:
            logger.info(f"   Range: {visible_strikes[0]} - {visible_strikes[-1]}")
            logger.info(f"   Sample: {visible_strikes[:10]}")
        
        # 2. Look for actual options table structure
        table_analysis = await page.evaluate('''() => {
            const analysis = {
                tables: 0,
                rows_with_strikes: 0,
                calls_puts_headers: false,
                volume_oi_headers: false,
                visible_data_rows: []
            };
            
            // Count tables
            analysis.tables = document.querySelectorAll('table').length;
            
            // Look for options table headers
            const allText = document.body.textContent || document.body.innerText || '';
            analysis.calls_puts_headers = /calls?/i.test(allText) && /puts?/i.test(allText);
            analysis.volume_oi_headers = /volume/i.test(allText) && (/open.?interest|oi/i.test(allText));
            
            // Look for rows that might contain options data
            const allRows = document.querySelectorAll('tr, div[class*="row"]');
            for (const row of allRows) {
                const text = row.textContent || row.innerText || '';
                
                // Check if row contains a strike price and other numbers
                if (/21[,\\s]*[0-9]{3}/.test(text)) {
                    const numbers = text.match(/\\d+(?:[,.]\\d+)?/g) || [];
                    if (numbers.length >= 5) {  // Strike + some data
                        analysis.rows_with_strikes++;
                        
                        // Sample first few rows for analysis
                        if (analysis.visible_data_rows.length < 5) {
                            analysis.visible_data_rows.push({
                                text: text.trim().substring(0, 200),
                                numbers: numbers.slice(0, 10)
                            });
                        }
                    }
                }
            }
            
            return analysis;
        }''')
        
        logger.info(f"📋 TABLE STRUCTURE analysis:")
        logger.info(f"   Tables found: {table_analysis['tables']}")
        logger.info(f"   Rows with strikes: {table_analysis['rows_with_strikes']}")
        logger.info(f"   Has Calls/Puts headers: {table_analysis['calls_puts_headers']}")
        logger.info(f"   Has Volume/OI headers: {table_analysis['volume_oi_headers']}")
        
        if table_analysis['visible_data_rows']:
            logger.info(f"\\n📝 SAMPLE DATA ROWS found:")
            for i, row in enumerate(table_analysis['visible_data_rows']):
                logger.info(f"   Row {i+1}: {len(row['numbers'])} numbers")
                logger.info(f"   Numbers: {row['numbers']}")
                logger.info(f"   Text: {row['text'][:100]}...")
        
        # 3. Now run our extraction and compare
        logger.info(f"\\n🤖 RUNNING OUR EXTRACTION...")
        
        # Try page interactions first
        await page.evaluate('''() => {
            // Try to click show all buttons
            const buttons = document.querySelectorAll('button, a, option');
            for (const button of buttons) {
                const text = button.textContent || button.innerText || '';
                if (/show.?all|view.?all|all.?strikes/i.test(text)) {
                    button.click();
                    break;
                }
            }
        }''')
        
        await asyncio.sleep(2)
        
        # Run our extraction method
        extracted_data = await page.evaluate('''() => {
            const data = [];
            const processedStrikes = new Set();
            
            // Our current extraction method
            const allElements = document.querySelectorAll('*');
            
            for (const element of allElements) {
                const text = element.textContent || element.innerText || '';
                const numbers = text.match(/\\b\\d+(?:[,.]\\d+)?\\b/g) || [];
                
                if (numbers.length >= 3) {
                    const numericValues = numbers.map(n => parseFloat(n.replace(/,/g, ''))).filter(n => !isNaN(n));
                    
                    const strikeIndices = [];
                    numericValues.forEach((num, index) => {
                        if (num >= 15000 && num <= 30000) {
                            strikeIndices.push({value: num, index: index});
                        }
                    });
                    
                    for (const strikeInfo of strikeIndices) {
                        const strike = strikeInfo.value;
                        
                        if (!processedStrikes.has(strike)) {
                            processedStrikes.add(strike);
                            
                            const strikeIndex = strikeInfo.index;
                            data.push({
                                strike: strike,
                                call_volume: numericValues[strikeIndex - 3] || 0,
                                call_oi: numericValues[strikeIndex - 2] || 0,
                                call_premium: numericValues[strikeIndex - 1] || 0,
                                put_premium: numericValues[strikeIndex + 1] || 0,
                                put_oi: numericValues[strikeIndex + 2] || 0,
                                put_volume: numericValues[strikeIndex + 3] || 0
                            });
                        }
                    }
                }
            }
            
            return data.sort((a, b) => a.strike - b.strike);
        }''')
        
        logger.info(f"\\n🎯 OUR EXTRACTION RESULTS:")
        logger.info(f"   Extracted strikes: {len(extracted_data)}")
        
        if extracted_data:
            strikes = [opt['strike'] for opt in extracted_data]
            logger.info(f"   Strike range: ${strikes[0]:,.0f} - ${strikes[-1]:,.0f}")
            
            logger.info(f"\\n📊 EXTRACTED OPTIONS:")
            for opt in extracted_data:
                logger.info(f"   Strike ${opt['strike']:,.0f}:")
                logger.info(f"     Calls:  Vol={opt['call_volume']:>8.0f}, OI={opt['call_oi']:>8.0f}, Premium=${opt['call_premium']:>8.2f}")
                logger.info(f"     Puts:   Vol={opt['put_volume']:>8.0f}, OI={opt['put_oi']:>8.0f}, Premium=${opt['put_premium']:>8.2f}")
        
        # 4. Final comparison
        logger.info(f"\\n" + "="*60)
        logger.info(f"📈 COMPARISON SUMMARY:")
        logger.info(f"="*60)
        
        logger.info(f"🔍 Visible on page:")
        logger.info(f"   • Strike prices in text: {len(visible_strikes)} strikes")
        logger.info(f"   • Table structure: {table_analysis['tables']} tables")
        logger.info(f"   • Rows with options data: {table_analysis['rows_with_strikes']} rows")
        logger.info(f"   • Has proper headers: {table_analysis['calls_puts_headers'] and table_analysis['volume_oi_headers']}")
        
        logger.info(f"\\n🤖 Our extraction:")
        logger.info(f"   • Successfully extracted: {len(extracted_data)} strikes")
        logger.info(f"   • Data completeness: {'100%' if extracted_data and all(opt['call_premium'] or opt['put_premium'] for opt in extracted_data) else 'Partial'}")
        
        if len(visible_strikes) > len(extracted_data):
            logger.info(f"\\n⚠️  MISSING DATA:")
            logger.info(f"   • We're only extracting {len(extracted_data)} of {len(visible_strikes)} visible strikes")
            logger.info(f"   • Missing: {len(visible_strikes) - len(extracted_data)} strikes ({(len(visible_strikes) - len(extracted_data))/len(visible_strikes)*100:.1f}%)")
        elif len(extracted_data) >= len(visible_strikes):
            logger.info(f"\\n✅ GOOD COVERAGE:")
            logger.info(f"   • Extracting {len(extracted_data)} strikes vs {len(visible_strikes)} visible")
        
        return {
            'visible_strikes': len(visible_strikes),
            'extracted_strikes': len(extracted_data),
            'table_structure': table_analysis,
            'extracted_data': extracted_data
        }
        
    except Exception as e:
        logger.error(f"❌ Error in analysis: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        await browser.close()

if __name__ == '__main__':
    result = asyncio.run(analyze_extraction_vs_visible())
    
    if result:
        print(f"\\n🎯 FINAL ANSWER TO YOUR QUESTIONS:")
        print(f"="*50)
        print(f"❓ How many strike prices are we getting?")
        print(f"   ➤ {result['extracted_strikes']} strikes extracted")
        print(f"   ➤ {result['visible_strikes']} strikes visible on page")
        
        print(f"\\n❓ Are we getting both put and call?")
        if result['extracted_data']:
            with_calls = sum(1 for opt in result['extracted_data'] if opt['call_premium'] > 0 or opt['call_volume'] > 0)
            with_puts = sum(1 for opt in result['extracted_data'] if opt['put_premium'] > 0 or opt['put_volume'] > 0)
            print(f"   ➤ Calls: {with_calls}/{result['extracted_strikes']} strikes ({with_calls/result['extracted_strikes']*100:.1f}%)")
            print(f"   ➤ Puts:  {with_puts}/{result['extracted_strikes']} strikes ({with_puts/result['extracted_strikes']*100:.1f}%)")
        
        print(f"\\n❓ Are we getting all the data showing in screenshots?")
        coverage = (result['extracted_strikes'] / result['visible_strikes'] * 100) if result['visible_strikes'] > 0 else 0
        print(f"   ➤ Coverage: {coverage:.1f}% of visible data")
        if coverage < 100:
            print(f"   ➤ Missing: {result['visible_strikes'] - result['extracted_strikes']} strikes")
            print(f"   ➤ Status: NOT extracting all visible data")
        else:
            print(f"   ➤ Status: Extracting all or most visible data")
    else:
        print("\\n❌ Analysis failed")