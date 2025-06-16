#!/bin/bash
# Start the live IFD dashboard with fixes applied
echo "🚀 Starting live IFD dashboard with fixes..."
echo "📊 Features:"
echo "   ✅ IFD configuration dropdown"
echo "   ✅ Demo mode for weekends"
echo "   ✅ Signal overlay visualization"
echo "   ✅ Dark theme"
echo ""
echo "Opening http://127.0.0.1:8050/"
# Use market-aware version that handles futures hours correctly
python3 scripts/nq_5m_dash_app_markets_fixed.py
