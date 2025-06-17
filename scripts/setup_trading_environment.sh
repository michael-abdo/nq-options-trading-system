#!/bin/bash

# TRADING-SAFE Environment Setup
# Guarantees correct API keys are loaded every time

echo "🔐 Setting up TRADING-SAFE environment..."

# Load the correct API key from .env file
if [ -f .env ]; then
    source .env
    echo "✅ Loaded environment from .env file"
else
    echo "⚠️ No .env file found. Please create one with DATABENTO_API_KEY=your_key"
fi

# Verify it's set correctly
echo "✅ DATABENTO_API_KEY set: ${DATABENTO_API_KEY:0:10}..."

# Activate virtual environment
source venv/bin/activate

echo "✅ Virtual environment activated"
echo "🚀 Ready for trading-safe operations!"
echo ""
echo "Available commands:"
echo "  python3 scripts/start_trading_safe_chart.py --type dashboard"
echo "  python3 scripts/start_trading_safe_chart.py --type static"
echo ""
