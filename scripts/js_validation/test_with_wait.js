const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({
        headless: false,  // Show browser for debugging
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        slowMo: 100
    });
    
    const page = await browser.newPage();
    
    try {
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
        
        // Test with a working symbol we know exists
        const url = 'https://www.barchart.com/futures/quotes/NQU25/options/MM6N25?futuresOptionsView=merged';
        console.log('Testing with known monthly symbol:', url);
        
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // Wait longer for dynamic content
        console.log('Waiting for page to fully load...');
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Try to find expiration info with multiple strategies
        const result = await page.evaluate(() => {
            // Strategy 1: Look for text containing "Days" and "expiration"
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            let expirationTexts = [];
            let node;
            while (node = walker.nextNode()) {
                const text = node.textContent;
                if (text && text.toLowerCase().includes('days') && text.toLowerCase().includes('expiration')) {
                    expirationTexts.push({
                        text: text.trim(),
                        parentClass: node.parentElement.className,
                        parentTag: node.parentElement.tagName
                    });
                }
            }
            
            // Strategy 2: Look for specific patterns
            const elements = document.querySelectorAll('*');
            let patternMatches = [];
            
            for (let element of elements) {
                const text = element.textContent || '';
                if (text.match(/\\d+\\s+days?\\s+to\\s+expiration/i)) {
                    patternMatches.push({
                        text: text.trim(),
                        className: element.className,
                        tagName: element.tagName,
                        id: element.id
                    });
                }
            }
            
            // Strategy 3: Look for elements with class names containing relevant terms
            const relevantClasses = [
                '[class*="toolbar"]',
                '[class*="expir"]',
                '[class*="days"]',
                '[class*="option"]'
            ];
            
            let classMatches = [];
            for (let selector of relevantClasses) {
                const elements = document.querySelectorAll(selector);
                for (let element of elements) {
                    if (element.textContent && element.textContent.includes('Days')) {
                        classMatches.push({
                            selector: selector,
                            text: element.textContent.trim(),
                            className: element.className
                        });
                    }
                }
            }
            
            return {
                expirationTexts: expirationTexts.slice(0, 3),
                patternMatches: patternMatches.slice(0, 3),
                classMatches: classMatches.slice(0, 3),
                pageTitle: document.title,
                bodyText: document.body.textContent.substring(0, 500)
            };
        });
        
        console.log('\nRESULTS:');
        console.log('Page Title:', result.pageTitle);
        
        console.log('\nEXPIRATION TEXTS FOUND:');
        result.expirationTexts.forEach((item, i) => {
            console.log(`${i + 1}. "${item.text}"`);
            console.log(`   Parent: ${item.parentTag}.${item.parentClass}`);
        });
        
        console.log('\nPATTERN MATCHES:');
        result.patternMatches.forEach((item, i) => {
            console.log(`${i + 1}. "${item.text}"`);
            console.log(`   Element: ${item.tagName}.${item.className}`);
        });
        
        console.log('\nCLASS MATCHES:');
        result.classMatches.forEach((item, i) => {
            console.log(`${i + 1}. Selector: ${item.selector}`);
            console.log(`   Text: "${item.text}"`);
        });
        
        console.log('\nFIRST 500 CHARS OF BODY:');
        console.log(result.bodyText);
        
        // Take a screenshot for debugging
        await page.screenshot({ path: 'debug_screenshot.png', fullPage: true });
        console.log('\nScreenshot saved: debug_screenshot.png');
        
        // Keep browser open for manual inspection
        console.log('\nBrowser will stay open for 30 seconds for manual inspection...');
        await new Promise(resolve => setTimeout(resolve, 30000));
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        await browser.close();
    }
})();