const puppeteer = require('puppeteer');

(async () => {
    console.log('🔍 Final verification of TODAY\'s 0DTE symbol MQ4M25...');
    console.log('Today is Friday, June 27, 2025');
    
    const browser = await puppeteer.launch({
        headless: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    try {
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36');
        
        const url = 'https://www.barchart.com/futures/quotes/NQU25/options/MQ4M25?futuresOptionsView=merged';
        console.log('Navigating to:', url);
        
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // Wait for content to load
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Get page text
        const pageText = await page.evaluate(() => document.body.innerText);
        
        // Look for expiration info
        const expirationMatch = pageText.match(/(\d+)\s+Days?\s+to\s+expiration\s+on\s+([\d\/]+)/i);
        
        if (expirationMatch) {
            console.log('\\n✅ Found expiration info:');
            console.log('   Days to expiration:', expirationMatch[1]);
            console.log('   Expiration date:', expirationMatch[2]);
            
            if (expirationMatch[1] === '0') {
                console.log('   ✅ CONFIRMED: This is a 0DTE option!');
            }
            
            if (expirationMatch[2] === '06/27/25' || expirationMatch[2] === '6/27/25') {
                console.log('   ✅ CONFIRMED: Expires TODAY (June 27, 2025)!');
                console.log('\\n🎯 MQ4M25 is the CORRECT 0DTE symbol for today!');
            }
        } else {
            console.log('❌ Could not find expiration info');
        }
        
        // Look for options data
        const hasOptionsData = pageText.includes('Call') && pageText.includes('Put');
        if (hasOptionsData) {
            console.log('\\n✅ Options chain data is present');
            
            // Count contracts
            const callMatches = pageText.match(/\d+,?\d*\.?\d*C/g);
            const putMatches = pageText.match(/\d+,?\d*\.?\d*P/g);
            
            if (callMatches && putMatches) {
                console.log(`   Found approximately ${callMatches.length} calls and ${putMatches.length} puts`);
            }
        }
        
        await page.screenshot({ path: 'today_0dte_final_verification.png', fullPage: true });
        console.log('\\n📸 Screenshot saved as today_0dte_final_verification.png');
        
        console.log('\\nBrowser will stay open for 15 seconds for manual verification...');
        await new Promise(resolve => setTimeout(resolve, 15000));
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        await browser.close();
        console.log('\\n✅ Verification complete!');
    }
})();