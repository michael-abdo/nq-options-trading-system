
const puppeteer = require('puppeteer');

(async () => {
    console.log('🔍 Validating MQ2Z25 for 2025-12-07...');
    
    const browser = await puppeteer.launch({
        headless: false,  // Show browser for verification
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    try {
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36');
        
        const url = 'https://www.barchart.com/futures/quotes/NQU25/options/MQ2Z25?futuresOptionsView=merged';
        console.log('Navigating to:', url);
        
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // Wait for page to load
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Try to find expiration info
        const pageText = await page.evaluate(() => document.body.innerText);
        
        // Look for expiration pattern
        const expirationMatch = pageText.match(/(\d+)\s+Days?\s+to\s+expiration\s+on\s+([\d\/]+)/i);
        
        if (expirationMatch) {
            console.log('✅ Found expiration info:');
            console.log('   Days to expiration:', expirationMatch[1]);
            console.log('   Expiration date:', expirationMatch[2]);
            console.log('   Expected date: 12/12/25');
            
            if (expirationMatch[2].includes('12/12/25') || 
                expirationMatch[2].includes('12/12/2025')) {
                console.log('   ✅ DATE MATCHES! Symbol is correct.');
            } else {
                console.log('   ❌ Date mismatch!');
            }
        } else {
            console.log('❌ Could not find expiration info on page');
            console.log('This might mean the symbol does not exist');
        }
        
        // Take screenshot
        await page.screenshot({ path: 'random_date_validation.png', fullPage: true });
        console.log('📸 Screenshot saved as random_date_validation.png');
        
        // Keep browser open for manual verification
        console.log('\n👀 Browser will stay open for 10 seconds for manual verification...');
        await new Promise(resolve => setTimeout(resolve, 10000));
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        await browser.close();
    }
})();
