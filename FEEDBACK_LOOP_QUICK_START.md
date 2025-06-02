# Feedback Loop Scraper - Quick Start Guide

## What is this?

The Feedback Loop Scraper is an intelligent system that automatically improves the Barchart options scraper when it fails. Instead of giving up when selectors don't work, it:

1. **Saves** the current page HTML for analysis
2. **Analyzes** the HTML to understand the structure  
3. **Generates** new potential selectors
4. **Tests** the new selectors
5. **Iterates** until successful or max attempts reached

## Quick Test

### 1. Start Chrome with Remote Debugging
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

### 2. Run the Demo
```bash
python demo_feedback_loop.py
```

### 3. Or Test Directly
```bash
python test_feedback_loop.py
```

## Integration with Main Algorithm

### Enable in Main Scraper
```bash
# Basic usage
python nq_options_ev_algo_puppeteer.py --puppeteer --feedback-loop

# With custom port
python nq_options_ev_algo_puppeteer.py --puppeteer --feedback-loop --port 9222
```

## What You'll See

### Successful Run
```
Feedback Loop Attempt 1/10
✓ HTML saved to: data/debug/page_20240602_103000.html
✓ Found 3 price-like elements
✓ Found 2 tables  
✓ Generated 5 new price selectors
✓ Successfully extracted price: $20,150.25
✓ Successfully extracted 50 option strikes
SUCCESS! Feedback loop completed successfully
```

### Failed Attempt
```
Feedback Loop Attempt 1/10
✓ HTML saved to: data/debug/page_20240602_103000.html
✗ Failed to extract price
✗ Failed to extract options data
Attempt 1 failed, trying next iteration...
```

## Debug Files Created

All files saved to `data/debug/`:

- `page_*.html` - HTML snapshots of each attempt
- `analysis_*.json` - Detailed structure analysis  
- `attempts_log.json` - Log of all attempts and results
- `final_report_*.txt` - Human-readable summary
- `successful_selectors.json` - Working selectors (if found)

## Common Use Cases

### 1. Page Structure Changed
When Barchart updates their page and normal scraping fails, the feedback loop will automatically analyze the new structure and find working selectors.

### 2. Data Loading Issues  
If the page loads differently (slower, different timing), the system will adapt and find elements that are actually present.

### 3. New Authentication Requirements
When new login or verification steps are added, the system will save the HTML for manual analysis.

## Troubleshooting

### If Nothing Works
1. Check Chrome is running: `curl http://localhost:9222/json/version`
2. Manually navigate to Barchart in Chrome
3. Solve any CAPTCHAs or login requirements
4. Run the scraper again

### If It's Slow
- Reduce max attempts: `python test_feedback_loop.py --max-attempts 3`
- Check your internet connection
- Verify Barchart site is responsive

### If Debug Files Fill Up
```bash
# Clean old debug files (keep last 10)
cd data/debug && ls -t | tail -n +11 | xargs rm -f
```

## Success Indicators

✅ **Good Signs:**
- Price extracted successfully
- Options data found (usually 40-60 strikes)
- Successful selectors saved
- Low attempt count (1-3 attempts)

❌ **Warning Signs:**  
- Multiple failed attempts
- No price or options data
- CAPTCHA detected messages
- HTML files are very small

## Next Steps

1. **Review the documentation**: See `docs/feedback_loop_system.md` for complete details
2. **Check debug files**: Look at saved HTML and analysis reports
3. **Integrate with your workflow**: Add `--feedback-loop` to your regular scraper runs
4. **Monitor performance**: Watch attempt counts and success rates over time

The feedback loop system makes the scraper much more robust and self-healing!