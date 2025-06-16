# Frequently Asked Questions (FAQ)

## Overview
This FAQ addresses the most common questions about the IFD v3.0 Live Streaming Trading System. Questions are organized by category and include practical solutions and examples.

## Table of Contents
- [Getting Started](#getting-started)
- [System Setup & Configuration](#system-setup--configuration)
- [Data Sources & Streaming](#data-sources--streaming)
- [Signal Interpretation](#signal-interpretation)
- [Trading & Risk Management](#trading--risk-management)
- [Performance & Optimization](#performance--optimization)
- [Troubleshooting](#troubleshooting)
- [API & Integration](#api--integration)
- [Cost & Billing](#cost--billing)
- [Advanced Features](#advanced-features)

## Getting Started

### Q: What is the IFD v3.0 Trading System?
**A:** IFD (Institutional Flow Detection) v3.0 is a real-time trading system that identifies large institutional orders in the market by analyzing Market-By-Order (MBO) data streams. It generates signals when institutions are actively positioning, allowing retail traders to follow "smart money" movements.

### Q: What markets does the system support?
**A:** Currently supports:
- **Primary**: NASDAQ-100 futures (NQ) and options
- **Secondary**: S&P 500 futures (ES) and options
- **Extended**: SPY ETF options
- **Planned**: Individual stock options on major indices

### Q: Do I need programming experience to use the system?
**A:** No. The system provides:
- **Web dashboard** for visual signal monitoring
- **Email/Slack alerts** for signal notifications
- **Pre-configured settings** for different trading styles
- **One-click setup** scripts for common configurations

However, programming knowledge helps with customization and advanced features.

### Q: How much does it cost to run the system?
**A:** Typical monthly costs:
- **Databento subscription**: $200-500 (depending on data volume)
- **Server hosting**: $50-200 (based on performance requirements)
- **API costs**: $20-50 (Polygon, Barchart fallbacks)
- **Total**: $270-750/month for professional setup

See [Cost & Billing](#cost--billing) section for detailed breakdown.

### Q: What's the minimum hardware requirement?
**A:**
- **Minimum**: 8GB RAM, 4-core CPU, 500GB SSD, 100Mbps internet
- **Recommended**: 16GB RAM, 8-core CPU, 1TB NVMe SSD, 1Gbps internet
- **Professional**: 32GB RAM, 16-core CPU, enterprise SSD, dedicated connection

## System Setup & Configuration

### Q: How do I get started quickly?
**A:** Follow the 5-minute setup:
```bash
# 1. Clone and setup
git clone <repository>
cd EOD
cp .env.example .env

# 2. Add your API keys to .env file
nano .env

# 3. Install dependencies (optional)
pip install plotly jsonschema

# 4. Start the system
python3 scripts/run_pipeline.py

# 5. Open dashboard
python3 scripts/nq_realtime_ifd_dashboard.py
```

Visit `http://localhost:8765` to see live signals.

### Q: Which configuration should I use?
**A:** Choose based on your needs:
- **`config/development.json`**: Learning and testing
- **`config/staging.json`**: Paper trading validation
- **`config/production.json`**: Live trading
- **`config/shadow_trading.json`**: Risk-free signal validation
- **`config/databento_only.json`**: Premium data only

### Q: How do I switch between paper trading and live trading?
**A:**
```bash
# Paper trading (safe)
python3 scripts/run_shadow_trading.py

# Live trading (requires broker integration)
python3 scripts/run_pipeline.py --config config/production.json
```

**Important**: Always test in shadow trading mode first.

### Q: Can I run the system on Windows?
**A:** Yes, but Linux/Mac is recommended:
```bash
# Windows (PowerShell)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python scripts\run_pipeline.py

# Or use WSL2 (recommended)
wsl --install Ubuntu
# Then follow Linux instructions
```

### Q: How do I backup my configuration?
**A:**
```bash
# Backup all configurations
cp -r config/ config_backup_$(date +%Y%m%d)/

# Backup specific environment
cp .env .env.backup

# Restore from backup
cp config_backup_20250616/production.json config/
```

## Data Sources & Streaming

### Q: What's the difference between Databento and Barchart?
**A:**
| Feature | Databento | Barchart |
|---------|-----------|----------|
| **Data Quality** | Professional MBO | End-of-bar aggregated |
| **Latency** | <15ms | 5-15 minutes |
| **Cost** | $200-500/month | Free (web scraping) |
| **Reliability** | 99.9% | 95% (fallback only) |
| **Best For** | Live trading | Development/testing |

### Q: Why do I sometimes see "No live data" messages?
**A:** Common causes:
1. **Market closed**: System switches to historical data automatically
2. **API key issues**: Check `.env` file for correct keys
3. **Network problems**: Verify internet connection
4. **Data provider maintenance**: Check Databento status page

**Solution**: System automatically falls back to cached data during outages.

### Q: How fresh is the data?
**A:** Data freshness by source:
- **Databento MBO**: <15ms from exchange
- **Barchart real-time**: 5-15 minutes delayed
- **Polygon**: 15 minutes delayed (free tier)
- **Cached data**: Updates every 5 minutes

### Q: Can I use multiple data sources simultaneously?
**A:** Yes, the system automatically:
1. **Prioritizes** Databento for real-time trading
2. **Falls back** to Barchart during outages
3. **Validates** data quality across sources
4. **Switches** seamlessly between sources

Configure in `config/all_sources.json`.

### Q: What happens if my internet connection drops?
**A:** The system includes:
- **Automatic reconnection** with exponential backoff
- **Data buffering** to handle short disconnections
- **Fallback to cached data** during extended outages
- **Quality monitoring** to detect connection issues

## Signal Interpretation

### Q: What does signal confidence mean?
**A:** Confidence indicates the statistical probability that the signal will be profitable:
- **0.85-1.00**: Extremely high (premium signals)
- **0.75-0.84**: High (strong signals)
- **0.65-0.74**: Moderate (good signals)
- **0.50-0.64**: Low (caution required)
- **Below 0.50**: Very low (typically filtered out)

Historical performance shows 73% accuracy for signals above 0.80 confidence.

### Q: Should I trade every signal?
**A:** No. Recommended filtering:
```
✅ TRADE: Confidence ≥ 0.75 + Regular market hours + Risk score ≤ 0.60
⚠️ CAUTION: 0.65-0.75 confidence (reduce position size)
❌ AVOID: <0.65 confidence or extended hours
```

### Q: What's the difference between signal strength and confidence?
**A:**
- **Confidence**: Statistical probability of success (0.0-1.0)
- **Strength**: Intensity of institutional activity (weak/moderate/strong)

Example: A signal can have high confidence (0.85) but weak strength (small institutional order) or low confidence (0.65) but strong strength (large but uncertain institutional move).

### Q: How long should I hold a position from a signal?
**A:** Typical timeframes:
- **Scalping**: 5-30 minutes
- **Day trading**: 1-4 hours
- **Swing trading**: 4-24 hours

Monitor the signal's expected timeframe and market conditions. Most signals resolve within 2-4 hours.

### Q: What does "Expected Value" mean?
**A:** Expected Value is the estimated profit potential in points:
- **NQ futures**: Each point = $20 (so 50 points = $1,000 profit)
- **Options**: Points vary by strike and expiration
- **Calculation**: Based on historical similar signals

This is an estimate, not a guarantee.

## Trading & Risk Management

### Q: How much should I risk per signal?
**A:** Conservative guidelines:
- **Account size risk**: 1-2% of total account per trade
- **Signal-based sizing**: Confidence × (1 - Risk Score) × Base Position
- **Maximum single trade**: Never more than 5% of account

Example: $100k account, 0.80 confidence signal with 0.30 risk score:
Position = $2000 × 0.80 × 0.70 = $1,120 risk

### Q: Should I use stop losses with signals?
**A:** Yes, always:
- **Initial stop**: 1.5 × signal's max drawdown
- **Trailing stop**: Move to breakeven after 50% of target reached
- **Time stop**: Exit if no movement within expected timeframe

Example: Signal shows 40-point max drawdown → set stop at 60 points.

### Q: Can I automate the trading?
**A:** Partial automation is possible:
- **Signal alerts**: Fully automated via webhooks/API
- **Position sizing**: Can be automated based on rules
- **Order placement**: Requires broker API integration
- **Risk management**: Can automate stops and targets

**Note**: Full automation requires significant development work.

### Q: How do I handle conflicting signals?
**A:** When multiple signals conflict:
1. **Higher confidence wins**: Choose signal with highest confidence
2. **Time proximity**: Prefer more recent signals
3. **Risk assessment**: Choose lower-risk option
4. **Portfolio balance**: Consider existing positions

### Q: What's shadow trading mode?
**A:** Shadow trading runs the system without real money:
- **Real signals**: Uses live market data
- **Paper positions**: Simulates trades without broker
- **Performance tracking**: Measures signal accuracy
- **Risk-free validation**: Perfect for learning

Run with: `python3 scripts/run_shadow_trading.py`

## Performance & Optimization

### Q: Why is the system running slowly?
**A:** Common performance issues:
1. **Insufficient RAM**: System needs 8GB+ for optimal performance
2. **CPU overload**: Close unnecessary programs
3. **Network latency**: Check internet speed (need 100Mbps+)
4. **Background processes**: Disable antivirus scanning of trading folder

**Quick fixes**:
```bash
# Check system resources
top
df -h

# Optimize configuration
# Edit config/production.json to reduce max_workers if needed
```

### Q: How can I improve signal accuracy?
**A:** Signal quality improvements:
1. **Time filtering**: Only trade during regular market hours
2. **Confidence filtering**: Raise minimum confidence threshold
3. **Market condition filtering**: Avoid trading during news events
4. **Correlation filtering**: Don't take multiple correlated positions

### Q: What's the optimal number of workers?
**A:**
- **4-core CPU**: max_workers = 2-4
- **8-core CPU**: max_workers = 4-6
- **16-core CPU**: max_workers = 8-12

Monitor CPU usage; if >80%, reduce workers.

### Q: How much historical data should I keep?
**A:** Recommended retention:
- **Signals**: 90 days for analysis
- **Market data**: 30 days for baselines
- **System logs**: 7 days for debugging
- **Performance metrics**: 180 days for trends

Configure in `config/production.json` logging section.

## Troubleshooting

### Q: "Authentication failed" error - what do I do?
**A:** Check these in order:
1. **API key format**: Should start with 'db-' for Databento
2. **Environment file**: Verify `.env` file exists and has correct keys
3. **Key validity**: Test keys at provider's website
4. **Network access**: Check firewall/proxy settings

```bash
# Test API key
python3 -c "import os; print(os.getenv('DATABENTO_API_KEY')[:10])"

# Validate key format
echo $DATABENTO_API_KEY | grep -E '^db-[A-Za-z0-9]{32}$'
```

### Q: Dashboard shows "Connection lost" - how to fix?
**A:** Connection troubleshooting:
1. **Check WebSocket server**: `netstat -an | grep 8765`
2. **Restart services**: `./scripts/restart_services.sh`
3. **Browser cache**: Clear cache and refresh
4. **Firewall**: Ensure port 8765 is open

```bash
# Check if WebSocket server is running
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8765/
```

### Q: System crashes with "Out of Memory" error?
**A:** Memory management:
1. **Increase system RAM** (recommended)
2. **Reduce buffer sizes** in configuration
3. **Limit concurrent workers**
4. **Enable swap file** (temporary fix)

```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head

# Reduce memory usage in config
# Edit config/production.json:
# "buffer_size": 5000 (instead of 10000)
# "max_workers": 2 (instead of 4)
```

### Q: No signals being generated - what's wrong?
**A:** Signal generation checklist:
1. **Market hours**: System only generates signals during trading hours
2. **Data feed**: Verify live data is flowing
3. **Confidence threshold**: Check if threshold is too high
4. **Symbol configuration**: Ensure correct symbols are configured

```bash
# Check if market is open
python3 -c "
from datetime import datetime
import time
now = datetime.now()
market_open = time(9, 30)
market_close = time(16, 0)
print('Market open' if market_open <= now.time() <= market_close else 'Market closed')
"
```

### Q: High CPU usage - how to optimize?
**A:** CPU optimization steps:
1. **Reduce max_workers** in configuration
2. **Disable debug logging** in production
3. **Use compiled functions** for hot paths
4. **Close unnecessary applications**

```bash
# Monitor CPU usage by process
top -p $(pgrep -f python)

# Optimize configuration
# In config/production.json:
# "max_workers": 2
# "enable_profiling": false
# "log_level": "INFO" (not DEBUG)
```

## API & Integration

### Q: How do I integrate with my trading platform?
**A:** Integration options:
1. **WebSocket API**: Real-time signal streaming
2. **REST API**: Historical signal retrieval
3. **Webhook notifications**: Push signals to external systems
4. **File exports**: CSV/JSON signal exports

Example WebSocket connection:
```javascript
const ws = new WebSocket('ws://localhost:8765/signals');
ws.onmessage = function(event) {
    const signal = JSON.parse(event.data);
    // Process signal in your platform
};
```

### Q: Can I get signals via email/Slack?
**A:** Yes, configure alerts in `config/alerting.json`:
```json
{
    "channels": {
        "email": {"enabled": true, "recipients": ["trader@email.com"]},
        "slack": {"enabled": true, "webhook_url": "your-webhook"}
    }
}
```

### Q: What's the API rate limit?
**A:** Default limits:
- **WebSocket connections**: 10 per API key
- **REST API requests**: 1000 per hour
- **Signal stream**: No limit (subject to system capacity)

Contact support for higher limits.

### Q: How do I create a custom integration?
**A:** Follow the API Integration Guide:
1. **Authentication**: Get API key from system
2. **Choose method**: WebSocket (real-time) or REST (historical)
3. **Handle data**: Parse JSON signal format
4. **Error handling**: Implement reconnection logic

Example integration templates available in `/docs/technical/API_Integration_Guide.md`.

## Cost & Billing

### Q: What are the monthly costs?
**A:** Typical cost breakdown:

**Basic Setup** ($70-170/month):
- Barchart (free) + VPS ($50) + Polygon ($20) = $70
- Small Databento subscription = +$100

**Professional Setup** ($270-750/month):
- Full Databento MBO subscription: $200-500
- Dedicated server: $50-200
- Additional APIs: $20-50

**Enterprise Setup** ($1000+/month):
- Premium Databento feeds: $500-1500
- High-performance hardware: $200-500
- Redundant connections: $200-300

### Q: How can I reduce costs?
**A:** Cost optimization strategies:
1. **Use free tier**: Barchart + Polygon free tier for testing
2. **Limit symbols**: Focus on NQ only to reduce data costs
3. **Optimize queries**: Reduce API call frequency
4. **Schedule usage**: Only run during trading hours

```bash
# Cost monitoring
python3 scripts/cost_monitor.py --daily-limit 20
```

### Q: Is there a free trial?
**A:** Yes:
- **System software**: Completely free and open source
- **Databento**: 30-day free trial with limited data
- **Demo mode**: Runs on saved/simulated data indefinitely

### Q: What happens if I exceed my budget?
**A:** Built-in cost controls:
- **Daily limits**: System stops at configured daily cost limit
- **Monthly budgets**: Warnings at 80%, shutdown at 100%
- **Usage alerts**: Email/Slack notifications for high usage

Configure limits in `config/production.json`:
```json
{
    "cost_controls": {
        "daily_limit": 50,
        "monthly_limit": 1000,
        "auto_shutdown": true
    }
}
```

## Advanced Features

### Q: Can I create custom signals?
**A:** Yes, the system is extensible:
1. **Custom indicators**: Add your own pressure calculations
2. **Signal filters**: Create custom filtering logic
3. **Machine learning**: Integrate ML models for signal enhancement
4. **Backtesting**: Test custom signals on historical data

See `/docs/technical/` for development guides.

### Q: How do I backtest strategies?
**A:** Built-in backtesting features:
```bash
# Backtest signal strategy
python3 scripts/backtest_signals.py --start-date 2025-01-01 --end-date 2025-06-01

# Shadow trading validation
python3 scripts/run_shadow_trading.py --duration 7  # 7 days
```

### Q: Can I trade multiple timeframes?
**A:** Yes, configure multiple timeframes:
- **1-minute**: Ultra-short scalping
- **5-minute**: Short-term momentum
- **15-minute**: Swing position entries
- **1-hour**: Trend confirmation

Each timeframe generates separate signals.

### Q: How do I set up high-frequency trading?
**A:** HFT optimization:
1. **Use HFT configuration**: `config/hft_optimized.json`
2. **Dedicated hardware**: 16+ cores, 64GB RAM, NVMe SSD
3. **Network optimization**: Co-location near exchanges
4. **Code optimization**: Compiled functions, memory pinning

**Warning**: HFT requires significant technical expertise and capital.

### Q: Can I run multiple strategies simultaneously?
**A:** Yes, the system supports:
- **Multi-symbol trading**: NQ, ES, SPY simultaneously
- **Multi-timeframe analysis**: Different timeframes per symbol
- **Strategy combinations**: Conservative + aggressive strategies
- **Portfolio management**: Risk allocation across strategies

Configure in `config/multi_strategy.json`.

### Q: How do I contribute to the project?
**A:** Contribution guidelines:
1. **Fork repository**: Create your own fork
2. **Follow conventions**: Use existing code style
3. **Add tests**: Include tests for new features
4. **Documentation**: Update docs for changes
5. **Submit PR**: Create pull request with clear description

See `CONTRIBUTING.md` for detailed guidelines.

### Q: Where can I get additional support?
**A:** Support resources:
- **Documentation**: `/docs/` directory has comprehensive guides
- **GitHub Issues**: Report bugs and request features
- **Community**: Trading Discord server (link in README)
- **Professional Support**: Contact for custom development

**Emergency Support**: For critical production issues, see emergency procedures in `/docs/operations/System_Maintenance_Guide.md`.

---

## Quick Reference Card

### Essential Commands
```bash
# Start system
python3 scripts/run_pipeline.py

# Start dashboard
python3 scripts/nq_realtime_ifd_dashboard.py

# Run shadow trading
python3 scripts/run_shadow_trading.py

# Health check
python3 scripts/health_check.py --all-services

# Cost monitoring
python3 scripts/cost_monitor.py

# Stop all services
pkill -f "python.*nq_realtime"
```

### Key Configuration Files
- `config/production.json`: Live trading configuration
- `config/development.json`: Safe testing configuration
- `config/alerting.json`: Alert system setup
- `.env`: API keys and secrets (never commit!)

### Important URLs
- **Dashboard**: http://localhost:8765
- **Monitoring**: http://localhost:8080
- **API Health**: http://localhost:8080/health
- **WebSocket**: ws://localhost:8765/signals

### Emergency Procedures
1. **Stop trading**: `pkill -f python.*pipeline`
2. **Emergency shutdown**: `bash scripts/emergency_shutdown.sh`
3. **Check system health**: `python3 scripts/health_check.py`
4. **View logs**: `tail -f outputs/$(date +%Y%m%d)/logs/system.log`

---

*This FAQ is regularly updated. For the latest version, check the documentation repository.*
