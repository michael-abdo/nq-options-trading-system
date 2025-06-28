const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    try {
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
        
        // Test the known working MM6N25 symbol
        const url = 'https://www.barchart.com/futures/quotes/NQU25/options/MM6N25?futuresOptionsView=merged';
        console.log('Testing MM6N25 for exact pattern: "6 Days to expiration on 07/03/25"');
        console.log('URL:', url);
        
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // Wait for dynamic content
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Search for the exact pattern and variations
        const result = await page.evaluate(() => {
            const pageText = document.body.textContent || document.body.innerText || '';
            
            // Try multiple regex patterns
            const patterns = [
                /(\d+)\s+Days?\s+to\s+expiration\s+on\s+([\d\/]+)/gi,
                /(\d+)\s+day\s+to\s+expiration\s+on\s+([\d\/]+)/gi,  
                /(\d+)\s+Days?\s+to\s+expiration/gi,
                /Days?\s+to\s+expiration\s+on\s+([\d\/]+)/gi,
                /expiration\s+on\s+([\d\/]+)/gi
            ];
            
            const results = {};
            
            patterns.forEach((pattern, i) => {
                const matches = [];
                let match;
                while ((match = pattern.exec(pageText)) !== null) {
                    matches.push({
                        fullMatch: match[0],
                        groups: match.slice(1),
                        index: match.index
                    });
                    if (matches.length > 5) break; // Limit results
                }
                results[`pattern_${i}`] = matches;
            });
            
            // Also search for the exact string
            const exactPattern = "6 Days to expiration on 07/03/25";
            const exactIndex = pageText.indexOf(exactPattern);
            results.exactMatch = exactIndex !== -1 ? {
                found: true,
                index: exactIndex,
                context: pageText.substring(Math.max(0, exactIndex - 100), exactIndex + exactPattern.length + 100)
            } : { found: false };
            
            // Search for any text containing key terms
            const searchTerms = ['expiration', 'Days to', '07/03/25', 'MM6N25'];
            results.termSearch = {};
            
            searchTerms.forEach(term => {
                const index = pageText.toLowerCase().indexOf(term.toLowerCase());
                if (index !== -1) {
                    results.termSearch[term] = {
                        found: true,
                        context: pageText.substring(Math.max(0, index - 50), index + term.length + 50)
                    };
                } else {
                    results.termSearch[term] = { found: false };
                }
            });
            
            return {
                results: results,
                pageTitle: document.title,
                textLength: pageText.length,
                firstChars: pageText.substring(0, 200)
            };
        });
        
        console.log('\n📊 ANALYSIS RESULTS:');
        console.log('Page Title:', result.pageTitle);
        console.log('Text Length:', result.textLength, 'characters');
        
        console.log('\n🔍 EXACT MATCH SEARCH:');
        if (result.results.exactMatch.found) {
            console.log('✅ Found exact pattern "6 Days to expiration on 07/03/25"');
            console.log('Context:', result.results.exactMatch.context);
        } else {
            console.log('❌ Exact pattern not found');
        }
        
        console.log('\n🎯 PATTERN MATCHES:');
        Object.entries(result.results).forEach(([key, matches]) => {
            if (key.startsWith('pattern_') && matches.length > 0) {
                console.log(`${key}: Found ${matches.length} matches`);
                matches.forEach((match, i) => {
                    console.log(`  ${i + 1}. "${match.fullMatch}" - Groups: [${match.groups.join(', ')}]`);
                });
            }
        });
        
        console.log('\n🔍 TERM SEARCH:');
        Object.entries(result.results.termSearch).forEach(([term, result]) => {
            if (result.found) {
                console.log(`✅ "${term}": ${result.context}`);
            } else {
                console.log(`❌ "${term}": Not found`);
            }
        });
        
        console.log('\n📄 FIRST 200 CHARS:');
        console.log(result.firstChars);
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        await browser.close();
    }
})();