const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    try {
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
        
        // Test symbols to validate
        const testCases = [
            {
                symbol: 'MM6N25',
                expectedPattern: /(\d+)\s+Days?\s+to\s+expiration\s+on\s+([\d\/]+)/i,
                description: 'Monthly July 2025 (Known working)',
                url: 'https://www.barchart.com/futures/quotes/NQU25/options/MM6N25?futuresOptionsView=merged'
            },
            {
                symbol: 'MM1N25', 
                expectedPattern: /(\d+)\s+Days?\s+to\s+expiration\s+on\s+([\d\/]+)/i,
                description: 'First Tuesday July 2025',
                url: 'https://www.barchart.com/futures/quotes/NQU25/options/MM1N25?futuresOptionsView=merged'
            },
            {
                symbol: 'MM1N5',
                expectedPattern: /(\d+)\s+Days?\s+to\s+expiration\s+on\s+([\d\/]+)/i,
                description: 'Generated with single digit year',
                url: 'https://www.barchart.com/futures/quotes/NQU25/options/MM1N5?futuresOptionsView=merged'
            }
        ];
        
        for (let testCase of testCases) {
            console.log(`\n${'='.repeat(60)}`);
            console.log(`Testing: ${testCase.symbol} - ${testCase.description}`);
            console.log(`URL: ${testCase.url}`);
            console.log(`${'='.repeat(60)}`);
            
            try {
                await page.goto(testCase.url, { waitUntil: 'networkidle2', timeout: 30000 });
                
                // Wait for dynamic content to load
                await new Promise(resolve => setTimeout(resolve, 3000));
                
                // Extract all text and search for the pattern
                const result = await page.evaluate((pattern) => {
                    const regex = new RegExp(pattern.source, pattern.flags);
                    
                    // Get all text content from the page
                    const pageText = document.body.textContent || document.body.innerText || '';
                    
                    // Search for the pattern
                    const match = pageText.match(regex);
                    
                    if (match) {
                        return {
                            found: true,
                            fullMatch: match[0],
                            days: match[1],
                            date: match[2],
                            rawText: pageText.substring(Math.max(0, pageText.indexOf(match[0]) - 50), 
                                                     pageText.indexOf(match[0]) + match[0].length + 50)
                        };
                    }
                    
                    // Also check for any text containing "Days" and "expiration"
                    const daysMatches = [];
                    const lines = pageText.split('\n');
                    for (let line of lines) {
                        if (line.toLowerCase().includes('days') && line.toLowerCase().includes('expiration')) {
                            daysMatches.push(line.trim());
                        }
                    }
                    
                    return {
                        found: false,
                        fullMatch: null,
                        days: null,
                        date: null,
                        daysMatches: daysMatches.slice(0, 5),
                        pageTitle: document.title
                    };
                }, testCase.expectedPattern);
                
                if (result.found) {
                    console.log(`✅ SUCCESS! Found expiration info:`);
                    console.log(`   Full Match: "${result.fullMatch}"`);
                    console.log(`   Days: ${result.days}`);
                    console.log(`   Date: ${result.date}`);
                    console.log(`   Context: "${result.rawText}"`);
                } else {
                    console.log(`❌ PATTERN NOT FOUND`);
                    console.log(`   Page Title: ${result.pageTitle}`);
                    if (result.daysMatches && result.daysMatches.length > 0) {
                        console.log(`   Found "Days" text:`);
                        result.daysMatches.forEach((match, i) => {
                            console.log(`     ${i + 1}. "${match}"`);
                        });
                    } else {
                        console.log(`   No "Days" text found on page`);
                    }
                }
                
            } catch (error) {
                console.log(`❌ ERROR testing ${testCase.symbol}: ${error.message}`);
            }
        }
        
        console.log(`\n${'='.repeat(60)}`);
        console.log('VALIDATION COMPLETE');
        console.log(`${'='.repeat(60)}`);
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        await browser.close();
    }
})();