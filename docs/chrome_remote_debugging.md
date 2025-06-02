# Chrome Remote Debugging Setup for Barchart Scraping

## Overview
This guide explains how to use Puppeteer with Chrome remote debugging to scrape options data from Barchart, bypassing their Angular/reCAPTCHA protections.

## Prerequisites

1. Install Python dependencies:
```bash
cd /Users/Mike/trading/algos/EOD
source venv/bin/activate
pip install -r requirements.txt
```

2. Install Node.js dependencies (optional, for direct Puppeteer usage):
```bash
npm install
```

## Starting Chrome with Remote Debugging

### Option 1: Manual Chrome Launch (Recommended)
1. Close all Chrome instances
2. Open Terminal and run:
```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug \
  --disable-blink-features=AutomationControlled

# Or use npm script
npm run start-chrome-mac
```

3. Chrome will open with remote debugging enabled on port 9222
4. You can verify by visiting: http://localhost:9222/json/version

### Option 2: Let Puppeteer Launch Chrome
The scraper will automatically launch Chrome if no remote instance is found.

## Using the Puppeteer Scraper

### Basic Usage
```python
from utils.puppeteer_scraper import run_puppeteer_scraper
from nq_options_ev_algo import get_current_contract_url

# Get the current contract URL
url = get_current_contract_url()

# Scrape data
current_price, options_data = run_puppeteer_scraper(url, remote_port=9222)

print(f"Current Price: {current_price}")
print(f"Options Found: {len(options_data)}")
```

### Integration with Main Algorithm
```python
# In nq_options_ev_algo.py, replace the scrape_barchart_options function call with:
from utils.puppeteer_scraper import run_puppeteer_scraper

# Use Puppeteer instead of BeautifulSoup
current_price, options_dict = run_puppeteer_scraper(url)

# Convert dict format to OptionsStrike objects
strikes = []
for opt in options_dict:
    strikes.append(OptionsStrike(
        opt['strike'],
        opt['call_volume'],
        opt['call_oi'],
        opt['call_premium'],
        opt['put_volume'],
        opt['put_oi'],
        opt['put_premium']
    ))
```

## Handling reCAPTCHA

If Barchart shows a reCAPTCHA:
1. The scraper will detect it and pause for 60 seconds
2. Manually solve the captcha in the Chrome window
3. The scraper will continue automatically

## Debugging Tips

1. **View Chrome DevTools**: Connect to http://localhost:9222 to see all open tabs
2. **Check Console Logs**: Enable verbose logging to see what's happening
3. **Screenshot on Error**: Add screenshot capability for debugging:
```python
await page.screenshot({'path': 'error_screenshot.png'})
```

## Common Issues

### "Failed to connect to Chrome"
- Make sure Chrome is running with `--remote-debugging-port=9222`
- Check if port 9222 is already in use: `lsof -i :9222`

### "No options data found"
- Barchart may have changed their page structure
- Check if you're logged in (some data requires authentication)
- Try increasing wait times for dynamic content

### "reCAPTCHA loop"
- Use a different IP address (VPN)
- Add delays between requests
- Consider using authenticated session

## Advanced Configuration

### Custom Chrome Arguments
```python
scraper = PuppeteerBarchartScraper(
    remote_debugging_port=9222,
    headless=False  # Set to True for headless mode
)
```

### Proxy Support
Add proxy arguments when launching Chrome:
```bash
--proxy-server=http://proxy.example.com:8080
```

### User Agent Rotation
The scraper already sets a non-automated user agent, but you can customize it in the Chrome launch arguments.

## Security Notes

- Never commit credentials or session cookies
- Be respectful of Barchart's terms of service
- Consider rate limiting your requests
- Use this for personal research only