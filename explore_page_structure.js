const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    try {
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
        
        // Test with the known working symbol from previous conversation
        const url = 'https://www.barchart.com/futures/quotes/NQU25/options/MM1N25?futuresOptionsView=merged';
        console.log('Exploring page structure for:', url);
        
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // Take a screenshot for debugging
        await page.screenshot({ path: 'barchart_page.png', fullPage: true });
        console.log('Screenshot saved: barchart_page.png');
        
        // Try multiple selectors to find expiration info
        const explorationResult = await page.evaluate(() => {
            const results = {};
            
            // Check if the page loaded successfully
            results.title = document.title;
            results.url = window.location.href;
            
            // Look for any element containing "days" or "expiration"
            const allElements = document.querySelectorAll('*');
            const expirationElements = [];
            
            for (let element of allElements) {
                const text = element.textContent || '';
                if (text.toLowerCase().includes('days') && text.toLowerCase().includes('expiration')) {
                    expirationElements.push({
                        tagName: element.tagName,
                        className: element.className,
                        textContent: text.trim(),
                        selector: element.tagName + (element.className ? '.' + element.className.split(' ').join('.') : '')
                    });
                }
            }
            
            results.expirationElements = expirationElements.slice(0, 5); // Limit to first 5
            
            // Try specific selectors
            const selectorTests = [
                '.bc-datatable-toolbar',
                '.bc-options-toolbar', 
                '.bc-datatable-toolbar.bc-options-toolbar',
                '.bc-options-toolbar__second-row',
                '[class*="toolbar"]',
                '[class*="expiration"]',
                '[class*="days"]'
            ];
            
            results.selectorTests = {};
            for (let selector of selectorTests) {
                const element = document.querySelector(selector);
                results.selectorTests[selector] = element ? {
                    found: true,
                    textContent: element.textContent.trim().substring(0, 200)
                } : { found: false };
            }
            
            // Look for any text containing "Days"
            results.daysText = [];
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            let node;
            while (node = walker.nextNode()) {
                if (node.textContent.includes('Days')) {
                    results.daysText.push({
                        text: node.textContent.trim(),
                        parentTag: node.parentElement.tagName,
                        parentClass: node.parentElement.className
                    });
                }
            }
            
            return results;
        });
        
        console.log('\nPAGE EXPLORATION RESULTS:');
        console.log('Title:', explorationResult.title);
        console.log('URL:', explorationResult.url);
        
        console.log('\nEXPIRATION ELEMENTS FOUND:');
        explorationResult.expirationElements.forEach((elem, i) => {
            console.log(`${i + 1}. ${elem.tagName}.${elem.className}`);
            console.log(`   Text: ${elem.textContent}`);
        });
        
        console.log('\nSELECTOR TESTS:');
        for (let [selector, result] of Object.entries(explorationResult.selectorTests)) {
            console.log(`${selector}: ${result.found ? 'FOUND' : 'NOT FOUND'}`);
            if (result.found && result.textContent) {
                console.log(`   Text: ${result.textContent.substring(0, 100)}...`);
            }
        }
        
        console.log('\nTEXT CONTAINING "Days":');
        explorationResult.daysText.forEach((item, i) => {
            console.log(`${i + 1}. ${item.text}`);
            console.log(`   Parent: ${item.parentTag}.${item.parentClass}`);
        });
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        await browser.close();
    }
})();