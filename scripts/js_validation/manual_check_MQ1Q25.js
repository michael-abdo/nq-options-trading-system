const puppeteer = require('puppeteer');

(async () => {
    console.log('Validating MQ1Q25 (generated for 2025-07-31)');
    
    const browser = await puppeteer.launch({
        headless: false,
        args: ['--no-sandbox']
    });
    
    const page = await browser.newPage();
    
    try {
        const url = 'https://www.barchart.com/futures/quotes/NQU25/options/MQ1Q25?futuresOptionsView=merged';
        console.log('URL:', url);
        
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        await page.waitForTimeout(3000);
        
        const pageText = await page.evaluate(() => document.body.innerText);
        const expirationMatch = pageText.match(/(\d+)\s+Days?\s+to\s+expiration\s+on\s+([\d\/]+)/i);
        
        if (expirationMatch) {
            console.log('✅ Found:', expirationMatch[0]);
            console.log('Expected expiry: 2025-08-01');
        } else {
            console.log('❌ No expiration info found');
        }
        
        console.log('\nBrowser will close in 10 seconds...');
        await page.waitForTimeout(10000);
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        await browser.close();
    }
})();