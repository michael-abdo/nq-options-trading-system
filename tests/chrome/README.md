# Chrome Remote Debugging Tests

This directory contains tests and utilities for Chrome remote debugging integration with the IFD v3.0 trading system.

## Purpose

- Automated browser testing for dashboard components
- Visual validation of real-time charts and signals
- Screenshot capture for monitoring and alerts
- End-to-end UI testing with live data

## Setup

1. Start Chrome with remote debugging enabled:
   ```bash
   # macOS
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

   # Windows
   chrome.exe --remote-debugging-port=9222

   # Linux
   google-chrome --remote-debugging-port=9222
   ```

2. Install required dependencies:
   ```bash
   pip install selenium pyppeteer playwright
   ```

## Test Structure

- `test_dashboard_chrome.py` - Dashboard rendering tests
- `test_live_charts.py` - Real-time chart validation
- `test_websocket_updates.py` - WebSocket connection tests
- `screenshot_automation.py` - Automated screenshot capture
- `performance_profiling.py` - Browser performance metrics

## Usage

```bash
# Run all Chrome tests
python -m pytest tests/chrome/

# Run specific test
python tests/chrome/test_dashboard_chrome.py

# Capture dashboard screenshot
python tests/chrome/screenshot_automation.py
```
