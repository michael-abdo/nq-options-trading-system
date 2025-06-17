#!/bin/bash
# Start the live NQ dashboard with streaming data

echo "🔴 Starting LIVE NQ Dashboard with Streaming Data"
echo "=================================================="

# Check if API key is set
if [ -z "$DATABENTO_API_KEY" ]; then
    echo "❌ DATABENTO_API_KEY not set"
    echo "💡 Set your API key first:"
    echo "   export DATABENTO_API_KEY='your-key'"
    exit 1
fi

echo "✅ API key found"
echo "🔴 Starting live streaming dashboard..."
echo "📊 Dashboard will show real-time data at http://localhost:8050"

cd "$(dirname "$0")/scripts"
python3 nq_5m_dash_app_ifd.py --symbol NQM5 --update 10
