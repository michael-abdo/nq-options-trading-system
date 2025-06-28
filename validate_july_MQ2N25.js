
const puppeteer = require('puppeteer');

(async () => {
    console.log('Validating MQ2N25 (2nd Friday of July 2025)...');
    
    const browser = await puppeteer.launch({
        headless: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    try {
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36');
        
        const url = 'https://www.barchart.com/futures/quotes/NQU25/options/MQ2N25?futuresOptionsView=merged';
        console.log('Navigating to:', url);
        
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // Wait for content
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Get page text
        const pageText = await page.evaluate(() => document.body.innerText);
        
        // Look for expiration info
        const expirationMatch = pageText.match(/(\d+)\s+Days?\s+to\s+expiration\s+on\s+([\d\/]+)/i);
        
        if (expirationMatch) {
            console.log('✅ Found expiration info:');
            console.log('   Days to expiration:', expirationMatch[1]);
            console.log('   Expiration date:', expirationMatch[2]);
            console.log('   Expected: 07/11/25 (2nd Friday of July)');
            
            // Also look for the specific date format
            if (pageText.includes('07/11/25') || pageText.includes('7/11/25')) {
                console.log('   ✅ DATE CONFIRMED! MQ2N25 expires on July 11, 2025');
            }
        } else {
            console.log('❌ Could not find expiration info');
            
            // Check if we got redirected or see any error
            const currentUrl = page.url();
            console.log('Current URL:', currentUrl);
            
            // Look for any options data
            const hasOptionsData = pageText.includes('Call') && pageText.includes('Put');
            console.log('Has options data:', hasOptionsData);
        }
        
        await page.screenshot({ path: 'july_validation.png', fullPage: true });
        console.log('📸 Screenshot saved as july_validation.png');
        
        console.log('\nBrowser will close in 10 seconds...');
        await new Promise(resolve => setTimeout(resolve, 10000));
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        await browser.close();
    }
})();
