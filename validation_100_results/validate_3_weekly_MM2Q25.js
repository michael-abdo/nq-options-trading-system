const puppeteer = require('puppeteer');

(async () => {
    const result = {
        symbol: 'MM2Q25',
        test_date: '2025-08-10',
        option_type: 'weekly',
        expected_expiry: '08/12/25',
        validation_start: new Date().toISOString()
    };
    
    console.log('🔍 Validating', result.symbol, 'for', result.test_date);
    
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    try {
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36');
        
        const url = 'https://www.barchart.com/futures/quotes/NQU25/options/MM2Q25?futuresOptionsView=merged';
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // Wait for content
        await page.waitForTimeout(3000);
        
        // Get page text
        const pageText = await page.evaluate(() => document.body.innerText);
        
        // Look for expiration info
        const expirationMatch = pageText.match(/(\d+)\s+Days?\s+to\s+expiration\s+on\s+([\d\/]+)/i);
        
        if (expirationMatch) {
            result.found_expiration = true;
            result.days_to_expiry = parseInt(expirationMatch[1]);
            result.actual_expiry = expirationMatch[2];
            result.match = expirationMatch[2] === '08/12/25' || 
                          expirationMatch[2] === '8/12/25';
            
            // Check for options data
            result.has_options_data = pageText.includes('Call') && pageText.includes('Put');
        } else {
            result.found_expiration = false;
            result.match = false;
            
            // Check if redirected or error
            result.current_url = page.url();
            result.page_title = await page.title();
        }
        
        result.validation_end = new Date().toISOString();
        result.success = result.found_expiration && result.match;
        
    } catch (error) {
        result.error = error.message;
        result.success = false;
    } finally {
        await browser.close();
        console.log(JSON.stringify(result));
    }
})();