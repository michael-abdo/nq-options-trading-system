const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({
        headless: false,  // Set to false to see what's happening
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    try {
        // Set user agent to avoid bot detection
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
        
        // Navigate to the Barchart options page for MQ4M25
        const symbol = 'MQ4M25';
        const url = `https://www.barchart.com/futures/quotes/NQU25/options/${symbol}?futuresOptionsView=merged`;
        console.log('Navigating to:', url);
        
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // Wait a bit for dynamic content
        await page.waitForTimeout(3000);
        
        // Try multiple selectors
        const selectors = [
            '.bc-datatable-toolbar.bc-options-toolbar',
            '.bc-options-toolbar__second-row',
            'div:contains("Days to expiration")',
            'div:contains("expiration")',
            '.column.small-12.medium-4',
            '[class*="expir"]',
            'strong'
        ];
        
        let expirationInfo = null;
        
        for (const selector of selectors) {
            try {
                console.log(`Trying selector: ${selector}`);
                const elements = await page.$$(selector);
                console.log(`Found ${elements.length} elements with selector: ${selector}`);
                
                // Check all text content on the page for expiration info
                if (selector.includes('expir')) {
                    const pageText = await page.evaluate(() => document.body.innerText);
                    const expirationMatch = pageText.match(/(\d+)\s+Days?\s+to\s+expiration\s+on\s+([\d/]+)/i);
                    if (expirationMatch) {
                        console.log('Found expiration text via page search:', expirationMatch[0]);
                        expirationInfo = expirationMatch[0];
                        break;
                    }
                }
            } catch (e) {
                console.log(`Selector ${selector} failed:`, e.message);
            }
        }
        
        // If not found, get all text with "expiration"
        if (!expirationInfo) {
            const allText = await page.evaluate(() => {
                const elements = Array.from(document.querySelectorAll('*'));
                return elements
                    .map(el => el.textContent)
                    .filter(text => text && text.toLowerCase().includes('expiration'))
                    .join('\n');
            });
            console.log('All expiration-related text found:', allText);
        }
        
        // Parse the expiration date
        let actualExpiry = null;
        let daysToExpiry = null;
        
        if (expirationInfo) {
            const match = expirationInfo.match(/(\d+)\s+Days?\s+to\s+expiration\s+on\s+([\d/]+)/i);
            if (match) {
                daysToExpiry = parseInt(match[1]);
                actualExpiry = match[2];
            }
        }
        
        // Also capture a screenshot
        await page.screenshot({ path: 'mq4m25_validation.png', fullPage: true });
        console.log('Screenshot saved as mq4m25_validation.png');
        
        // Output results as JSON
        const result = {
            symbol: 'MQ4M25',
            test_date: '2025-06-27',
            expected_expiry: '06/27/25',
            actual_expiry: actualExpiry,
            days_to_expiry: daysToExpiry,
            raw_text: expirationInfo,
            url: url,
            success: actualExpiry !== null,
            match: actualExpiry === '06/27/25',
            is_0dte: daysToExpiry === 0
        };
        
        console.log('RESULT:', JSON.stringify(result, null, 2));
        
        // Keep browser open for 5 seconds to see the page
        await page.waitForTimeout(5000);
        
    } catch (error) {
        console.error('Error:', error.message);
        
        const result = {
            symbol: 'MQ4M25',
            test_date: '2025-06-27',
            expected_expiry: '06/27/25',
            actual_expiry: null,
            days_to_expiry: null,
            raw_text: null,
            url: `https://www.barchart.com/futures/quotes/NQU25/options/MQ4M25?futuresOptionsView=merged`,
            success: false,
            match: false,
            error: error.message
        };
        
        console.log('RESULT:', JSON.stringify(result, null, 2));
    } finally {
        await browser.close();
    }
})();