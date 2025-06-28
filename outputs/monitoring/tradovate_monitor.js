
// Tradovate Live Data Monitor
// Run this in Chrome DevTools Console on the Tradovate page

console.log('🚀 Starting Tradovate Live Data Monitor...');

// Function to find Copy Trading Data button
function findCopyButton() {
    const buttons = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
    const copyButton = buttons.find(b => 
        b.textContent.toLowerCase().includes('copy') && 
        b.textContent.toLowerCase().includes('trading')
    );
    
    if (copyButton) {
        console.log('✅ Found Copy Trading Data button:', copyButton);
        return copyButton;
    }
    
    console.log('❌ Copy Trading Data button not found');
    return null;
}

// Function to extract NQ data from page
function extractNQData() {
    const data = {
        timestamp: new Date().toISOString(),
        symbol: 'NQ',
        quotes: [],
        trades: []
    };
    
    // Look for NQ price elements (adjust selectors based on actual page)
    const priceElements = document.querySelectorAll('[data-symbol*="NQ"], [class*="price"], [class*="quote"]');
    
    priceElements.forEach(el => {
        const text = el.textContent;
        if (text && text.match(/\d+\.\d+/)) {
            data.quotes.push({
                element: el.className || el.id,
                value: text,
                timestamp: new Date().toISOString()
            });
        }
    });
    
    console.log('📊 Extracted NQ Data:', data);
    return data;
}

// Function to monitor clipboard
async function monitorClipboard() {
    try {
        const text = await navigator.clipboard.readText();
        console.log('📋 Clipboard content:', text);
        
        // Parse if it looks like JSON
        try {
            const data = JSON.parse(text);
            console.log('✅ Parsed trading data:', data);
            
            // Send to your system via webhook
            fetch('http://localhost:8083/api/tradovate-data', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            
        } catch (e) {
            console.log('📄 Clipboard contains text (not JSON):', text.substring(0, 100) + '...');
        }
    } catch (err) {
        console.log('❌ Cannot read clipboard:', err);
    }
}

// Set up monitoring
const copyButton = findCopyButton();
if (copyButton) {
    copyButton.addEventListener('click', () => {
        console.log('🔘 Copy button clicked!');
        setTimeout(monitorClipboard, 100);
    });
}

// Extract data every 5 seconds
setInterval(() => {
    extractNQData();
}, 5000);

// Monitor for NQ updates
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.target.textContent && mutation.target.textContent.includes('NQ')) {
            console.log('🔄 NQ data updated:', mutation.target.textContent);
        }
    });
});

// Start observing
observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true
});

console.log('✅ Tradovate monitor is running!');
console.log('📋 Click "Copy Trading Data" to capture data');
