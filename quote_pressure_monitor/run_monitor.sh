#!/bin/bash

# NQ Options Quote Pressure Monitor Launcher
# This script runs the quote pressure monitor with proper environment setup

echo "🎯 NQ OPTIONS QUOTE PRESSURE MONITOR"
echo "======================================"
echo ""
echo "Key Insight: Monitor QUOTES not TRADES for institutional flow"
echo "Focus: Bid/Ask size changes during 2:30-4:00 PM ET"
echo ""
echo "Starting monitor..."
echo ""

cd /Users/Mike/trading/algos/EOD/quote_pressure_monitor

# Check if Python environment is ready
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python3."
    exit 1
fi

# Check if databento is installed
python3 -c "import databento" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Databento package not found. Installing..."
    pip3 install databento
fi

# Check if .env file exists with API key
if [ ! -f "/Users/Mike/trading/algos/EOD/.env" ]; then
    echo "⚠️  Warning: .env file not found. Using hardcoded API key."
fi

# Run the monitor
echo "🚀 Launching quote pressure monitor..."
echo ""
python3 nq_options_quote_pressure.py

echo ""
echo "📊 Monitor stopped. Check institutional_alerts.jsonl for saved alerts."
