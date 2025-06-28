const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    try {
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
        
        // Test the known working symbol MM1N25
        const url = 'https://www.barchart.com/futures/quotes/NQU25/options/MM1N25?futuresOptionsView=merged';
        console.log('Testing known working symbol:', url);
        
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
        
        // Wait and extract expiration info
        await page.waitForSelector('.bc-datatable-toolbar.bc-options-toolbar', { timeout: 15000 });
        
        const expirationInfo = await page.evaluate(() => {
            const toolbar = document.querySelector('.bc-datatable-toolbar.bc-options-toolbar');
            if (!toolbar) return null;
            
            const secondRow = toolbar.querySelector('.bc-options-toolbar__second-row');
            if (!secondRow) return null;
            
            const expirationDiv = secondRow.querySelector('.column.small-12.medium-4 div');
            if (!expirationDiv) return null;
            
            return expirationDiv.textContent.trim();
        });
        
        console.log('MM1N25 expiration text:', expirationInfo);
        
        // Now test our generated symbol MM1N5
        const testUrl = 'https://www.barchart.com/futures/quotes/NQU25/options/MM1N5?futuresOptionsView=merged';
        console.log('Testing generated symbol:', testUrl);
        
        await page.goto(testUrl, { waitUntil: 'networkidle2', timeout: 30000 });
        
        const testResult = await page.evaluate(() => {
            const toolbar = document.querySelector('.bc-datatable-toolbar.bc-options-toolbar');
            if (!toolbar) return null;
            
            const secondRow = toolbar.querySelector('.bc-options-toolbar__second-row');
            if (!secondRow) return null;
            
            const expirationDiv = secondRow.querySelector('.column.small-12.medium-4 div');
            if (!expirationDiv) return null;
            
            return expirationDiv.textContent.trim();
        });
        
        console.log('MM1N5 expiration text:', testResult);
        
        // Compare results
        console.log('\nCOMPARISON:');
        console.log('MM1N25 (known working):', expirationInfo || 'NOT FOUND');
        console.log('MM1N5 (our generated):', testResult || 'NOT FOUND');
        
    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        await browser.close();
    }
})();