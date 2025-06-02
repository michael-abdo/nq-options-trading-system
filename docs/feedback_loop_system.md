# Feedback Loop Scraper System

## Overview

The Feedback Loop Scraper System is an intelligent, self-improving web scraping solution designed to automatically adapt to changes in the Barchart options page structure. It implements a closed feedback loop that analyzes scraping failures, generates new selector strategies, and iterates until successful data extraction.

## Key Features

### 1. Automatic HTML Analysis
- Saves complete HTML snapshots with timestamps
- Analyzes page structure to identify potential data elements
- Generates detailed reports of findings
- Tracks changes over time

### 2. Dynamic Selector Generation
- Creates new CSS selectors based on HTML analysis
- Tests XPath expressions for complex element selection
- Attempts Angular scope access for dynamic content
- Uses regex patterns for JSON data extraction

### 3. Self-Improving Logic
- Tests multiple selector strategies in priority order
- Learns from successful extractions
- Saves working selectors for future use
- Adapts to page structure changes automatically

### 4. Comprehensive Logging
- Detailed attempt logs with timestamps
- Success/failure tracking for each strategy
- Performance metrics and iteration counts
- Debugging artifacts for manual analysis

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Main Scraper  │───▶│ Feedback Loop   │───▶│ HTML Analysis   │
│                 │    │ Controller      │    │ Engine          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │ Selector Tester │    │ Report Generator│
                    │                 │    │                 │
                    └─────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │ Debug Storage   │    │ Success Tracker │
                    │                 │    │                 │
                    └─────────────────┘    └─────────────────┘
```

## Usage

### 1. Standalone Testing
```bash
# Test the feedback loop scraper directly
python test_feedback_loop.py

# Test with specific URL
python test_feedback_loop.py --url "https://www.barchart.com/..."

# Test with different Chrome port
python test_feedback_loop.py --port 9223
```

### 2. Integrated with Main Algorithm
```bash
# Enable feedback loop in main scraper
python nq_options_ev_algo_puppeteer.py --puppeteer --feedback-loop

# Use with specific port and week
python nq_options_ev_algo_puppeteer.py --puppeteer --feedback-loop --port 9222 --week 2
```

### 3. Interactive Demo
```bash
# Run comprehensive demo showing all features
python demo_feedback_loop.py
```

## Selector Strategies

The system uses multiple extraction strategies in priority order:

### Current Price Extraction
1. **CSS Selectors**: `.last-change`, `.last-price`, `.quote-price`
2. **Data Attributes**: `[data-ng-bind*="lastPrice"]`
3. **XPath Expressions**: `//span[contains(@class, 'price')]`
4. **Angular Scope**: `scope.item.lastPrice`
5. **JSON Regex**: `"lastPrice":\s*"?([0-9,]+\.?[0-9]*)"?`

### Options Table Extraction
1. **Table Selectors**: `.bc-table-scrollable-inner table`, `.options-table`
2. **Angular Repeats**: `[data-ng-repeat*="option"]`
3. **XPath Tables**: `//table[contains(.//text(), 'Strike')]`
4. **Angular Data**: `scope.optionsData`
5. **JSON Extraction**: `"options":\s*\[(.*?)\]`

## Debug Output

All debug information is saved to `data/debug/` directory:

### File Types
- `page_YYYYMMDD_HHMMSS.html` - Complete HTML snapshots
- `page_YYYYMMDD_HHMMSS_info.json` - Page metadata (URL, viewport, cookies)
- `analysis_YYYYMMDD_HHMMSS.json` - Detailed HTML analysis reports
- `attempts_log.json` - Log of all attempts with results
- `final_report_YYYYMMDD_HHMMSS.txt` - Human-readable summary
- `successful_selectors.json` - Working selectors for reuse

### Analysis Report Structure
```json
{
  "timestamp": "2024-06-02T10:30:00",
  "file": "data/debug/page_20240602_103000.html",
  "findings": {
    "price": {
      "elements_with_price_pattern": [...],
      "angular_bindings": [...],
      "json_data": [...]
    },
    "table": {
      "tables": [...],
      "angular_repeats": [...],
      "table_like_structures": [...]
    },
    "angular": {
      "controllers": [...],
      "scopes": [...],
      "models": [...]
    }
  },
  "potential_selectors": {
    "current_price": [...],
    "options_table": [...]
  }
}
```

## Configuration

### FeedbackLoopScraper Parameters
```python
scraper = FeedbackLoopScraper(
    debug_dir="data/debug",  # Directory for debug files
    max_attempts=10          # Maximum iteration attempts
)
```

### Iteration Control
```python
results = await scraper.iterate_until_successful(
    page,                    # Puppeteer page object
    max_attempts=5          # Override default max attempts
)
```

## Integration Points

### With Existing Puppeteer Scraper
The feedback loop integrates seamlessly with the existing scraper:

```python
# Enhanced scraper function
async def scrape_barchart_with_puppeteer(
    url: str, 
    remote_port: int = 9222, 
    use_feedback_loop: bool = False
) -> Tuple[Optional[float], List[Dict]]:
    # ... normal scraping logic ...
    
    # If normal extraction fails and feedback loop is enabled
    if use_feedback_loop and (not current_price or not options_data):
        feedback_results = await run_feedback_loop_scraper(page)
        if feedback_results.get("success"):
            current_price = feedback_results.get("current_price")
            options_data = feedback_results.get("options_data")
```

### With Main Algorithm
```python
# Modified main function call
current_price, strikes = scrape_barchart_options_puppeteer(
    url, 
    use_puppeteer=args.puppeteer,
    remote_port=args.port,
    use_feedback_loop=args.feedback_loop  # New parameter
)
```

## Error Handling

### Graceful Degradation
1. **Attempt Limit**: Stops after maximum attempts to prevent infinite loops
2. **Timeout Protection**: Each iteration has reasonable timeouts
3. **Exception Isolation**: Individual strategy failures don't crash the system
4. **Fallback Support**: Falls back to original scraper if feedback loop fails

### Error Reporting
- All errors logged with full context
- Failed selectors tracked with error messages
- Performance metrics for debugging
- Suggestions for manual intervention

## Performance Considerations

### Efficiency Optimizations
- **Priority-based Testing**: Tests most likely selectors first
- **Early Success Exit**: Stops immediately when data is found
- **Cached Analysis**: Reuses analysis results within iteration
- **Selective HTML Saving**: Only saves when needed

### Resource Management
- **Memory Cleanup**: Properly disposes of page resources
- **File Rotation**: Limits debug file accumulation
- **Connection Reuse**: Leverages persistent Chrome connections

## Best Practices

### Before Using
1. **Chrome Setup**: Ensure Chrome is running with remote debugging
2. **Manual Check**: Verify page loads correctly in browser
3. **Login State**: Complete any required authentication
4. **Network Stability**: Ensure stable internet connection

### During Operation
1. **Monitor Logs**: Watch for CAPTCHA or authentication issues
2. **Check Debug Files**: Review HTML snapshots for unexpected changes
3. **Validate Results**: Verify extracted data makes sense
4. **Performance Watch**: Monitor iteration counts and timing

### After Use
1. **Review Reports**: Analyze final reports for insights
2. **Save Successful Selectors**: Preserve working configurations
3. **Clean Debug Files**: Manage disk space usage
4. **Update Strategies**: Add new successful patterns to defaults

## Troubleshooting

### Common Issues

#### No Data Extracted
- Check if page fully loaded before analysis
- Verify Chrome connection is stable
- Review HTML snapshots for structure changes
- Check for CAPTCHA or authentication requirements

#### Slow Performance
- Reduce maximum attempts if taking too long
- Check network latency to Barchart
- Review selector complexity in strategies
- Monitor Chrome memory usage

#### Debug File Issues
- Ensure write permissions to debug directory
- Check available disk space
- Verify path resolution for debug_dir
- Review file system limitations

### Diagnostic Commands
```bash
# Check Chrome connection
curl http://localhost:9222/json/version

# Verify debug directory
ls -la data/debug/

# Review recent attempts
tail -f data/debug/attempts_log.json

# Check system resources
ps aux | grep chrome
```

## Future Enhancements

### Planned Features
1. **Machine Learning**: Train models on successful selector patterns
2. **A/B Testing**: Compare multiple strategies simultaneously
3. **Performance Optimization**: Parallel strategy testing
4. **Visual Analysis**: Screenshot-based element detection
5. **Adaptive Timing**: Dynamic wait times based on page loading

### Extension Points
1. **Custom Strategies**: Plugin system for domain-specific selectors
2. **Multi-site Support**: Generalize for other financial sites
3. **Real-time Monitoring**: Continuous health checking
4. **Integration APIs**: RESTful interface for external tools

## Conclusion

The Feedback Loop Scraper System provides a robust, self-improving solution for web scraping challenges. By automatically analyzing page structure and adapting extraction strategies, it significantly reduces maintenance overhead while improving reliability and success rates.

The system's comprehensive debugging and reporting capabilities make it easy to understand what's happening during extraction attempts and provide clear paths for manual intervention when needed.