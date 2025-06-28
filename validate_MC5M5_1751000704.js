
const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    try {
        // Set user agent to avoid bot detection
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
        
        // Navigate to the Barchart options page
        const url = 'https://www.barchart.com/futures/quotes/NQU25/options/MC5M5?futuresOptionsView=merged';
        console.log('Navigating to:', url);
        
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // Wait for the expiration info element to load
        await page.waitForSelector('.bc-datatable-toolbar.bc-options-toolbar', { timeout: 15000 });
        
        // Extract expiration information
        const expirationInfo = await page.evaluate(() => {
            const toolbar = document.querySelector('.bc-datatable-toolbar.bc-options-toolbar');
            if (!toolbar) return null;
            
            const secondRow = toolbar.querySelector('.bc-options-toolbar__second-row');
            if (!secondRow) return null;
            
            const expirationDiv = secondRow.querySelector('.column.small-12.medium-4 div');
            if (!expirationDiv) return null;
            
            return expirationDiv.textContent.trim();
        });
        
        console.log('Raw expiration text:', expirationInfo);
        
        // Parse the expiration date
        let actualExpiry = null;
        let daysToExpiry = null;
        
        if (expirationInfo) {
            // Extract days and date using regex
            const match = expirationInfo.match(/(\d+)\s+Days?\s+to\s+expiration\s+on\s+([\d/]+)/i);
            if (match) {
                daysToExpiry = parseInt(match[1]);
                actualExpiry = match[2];
            }
        }
        
        // Output results as JSON
        const result = {
            symbol: 'MC5M5',
            test_date: '2025-06-27',
            expected_expiry: '06/27/25',
            actual_expiry: actualExpiry,
            days_to_expiry: daysToExpiry,
            raw_text: expirationInfo,
            url: url,
            success: actualExpiry !== null,
            match: actualExpiry === '06/27/25' || actualExpiry === '06/27/2025' 
        };
        
        console.log('RESULT:', JSON.stringify(result, null, 2));
        
    } catch (error) {
        console.error('Error:', error.message);
        
        const result = {
            symbol: 'MC5M5',
            test_date: '2025-06-27',
            expected_expiry: '06/27/25',
            actual_expiry: null,
            days_to_expiry: null,
            raw_text: null,
            url: 'https://www.barchart.com/futures/quotes/NQU25/options/MC5M5?futuresOptionsView=merged',
            success: false,
            match: false,
            error: error.message
        };
        
        console.log('RESULT:', JSON.stringify(result, null, 2));
    } finally {
        await browser.close();
    }
})();
