# NQ Futures 5-Minute Chart Documentation

## Overview

The NQ Futures 5-Minute Chart is a real-time candlestick charting tool that displays E-mini NASDAQ-100 futures data with automatic updates. Built using Plotly for interactive visualization and Databento for market data, it provides professional-grade financial charts with minimal setup.

## Features

### ✅ Core Functionality
- **5-Minute Candlestick Charts**: Automatic aggregation from 1-minute Databento data
- **Volume Analysis**: Color-coded volume bars (green for up, red for down)
- **Moving Averages**: MA20 and MA50 overlays when sufficient data available
- **Real-Time Updates**: Configurable refresh interval (default: 30 seconds)
- **Interactive Charts**: Zoom, pan, and hover for detailed price information
- **Dark Theme**: Professional dark theme optimized for trading

### 📊 Data Display
- Current price annotation with arrow
- High/Low/Volume statistics box
- Update timestamp
- Professional candlestick coloring (green up, red down)

## Installation

### Prerequisites
```bash
# Required packages (already installed in venv)
pip install plotly pandas databento
```

### Environment Setup
```bash
# Set your Databento API key
export DATABENTO_API_KEY="your-api-key-here"
```

## Usage

### Two Chart Options Available

#### Option 1: Static Chart (scripts/nq_5m_chart.py)
Perfect for quick snapshots and saved charts:

```bash
# Basic usage - interactive chart (opens in browser)
python3 scripts/nq_5m_chart.py

# Specify different contract
python3 scripts/nq_5m_chart.py --symbol NQZ5

# Change time range (hours of data)
python3 scripts/nq_5m_chart.py --hours 8

# Adjust update interval (seconds)
python3 scripts/nq_5m_chart.py --update 60

# Save to HTML file instead of displaying
python3 scripts/nq_5m_chart.py --save --output my_chart.html
```

#### Option 2: Real-Time Dashboard (scripts/nq_5m_dash_app.py) **[NEW]**
Professional auto-refreshing web dashboard:

```bash
# Launch real-time dashboard (auto-opens in browser)
python3 scripts/nq_5m_dash_app.py

# Custom settings
python3 scripts/nq_5m_dash_app.py --symbol NQZ5 --hours 8 --update 15

# Different port
python3 scripts/nq_5m_dash_app.py --port 8080

# Quick demo launch
python3 scripts/run_dash_demo.py
```

**Dashboard Features:**
- 🔴 **Auto-refreshing**: No manual browser refresh needed
- 🎛️ **Live controls**: Change symbol and timeframe on-the-fly
- 📊 **Real-time stats**: Live price, change %, volume, statistics
- ⚡ **Instant updates**: Data refreshes automatically every 30 seconds
- 🌐 **Web-based**: Access from any browser at http://localhost:8050

### Command Line Options

#### Static Chart (nq_5m_chart.py)

| Option | Default | Description |
|--------|---------|-------------|
| `--symbol` | NQM5 | Contract symbol to chart |
| `--hours` | 4 | Hours of historical data to display |
| `--update` | 30 | Update interval in seconds |
| `--save` | False | Save to HTML file instead of browser |
| `--output` | Auto | Output filename for saved charts |

#### Real-Time Dashboard (nq_5m_dash_app.py)

| Option | Default | Description |
|--------|---------|-------------|
| `--symbol` | NQM5 | Contract symbol to chart |
| `--hours` | 4 | Hours of historical data to display |
| `--update` | 30 | Update interval in seconds |
| `--port` | 8050 | Web dashboard port number |
| `--host` | 127.0.0.1 | Host address for dashboard |
| `--debug` | False | Run in debug mode |

## Architecture

### Data Flow
```
Databento API (1-min bars) → Aggregation (5-min bars) → Plotly Chart → Browser/HTML
```

### Key Components

1. **`databento_5m_provider.py`**
   - Fetches 1-minute OHLCV data from Databento
   - Aggregates to 5-minute bars using pandas resample
   - Caches data to minimize API calls
   - Handles both historical and live streaming

2. **`data_aggregation.py`**
   - TimeBar class for OHLCV data structure
   - MinuteToFiveMinuteAggregator for streaming aggregation
   - Utility functions for batch aggregation

3. **`nq_5m_chart.py`**
   - Main script with CLI interface
   - Plotly chart creation and styling
   - Update loop management
   - Statistics calculation

## Examples

### 1. Day Trading Setup (1 hour of data, 15-second updates)
```bash
python3 scripts/nq_5m_chart.py --hours 1 --update 15
```

### 2. Swing Trading View (full day, 1-minute updates)
```bash
python3 scripts/nq_5m_chart.py --hours 24 --update 60
```

### 3. Save Chart for Report
```bash
python3 scripts/nq_5m_chart.py --save --output daily_report.html --hours 8
```

### 4. Different Contract Month
```bash
python3 scripts/nq_5m_chart.py --symbol NQZ5 --hours 4
```

## Technical Details

### Data Aggregation
- 1-minute bars are aggregated using:
  - Open: First value in 5-minute window
  - High: Maximum value in window
  - Low: Minimum value in window
  - Close: Last value in window
  - Volume: Sum of all volumes in window

### Update Mechanism
- Current implementation refreshes entire dataset
- Future enhancement: Incremental updates using Plotly Dash
- Data is cached to minimize API calls

### Memory Management
- In-memory cache with automatic cleanup
- Configurable data retention period
- Efficient pandas operations for aggregation

## Customization

### Modifying Chart Appearance
Edit `create_chart()` in `nq_5m_chart.py`:
```python
# Change theme
template='plotly_dark'  # Options: plotly, plotly_white, plotly_dark

# Modify colors
increasing_line_color='green'  # Bullish candles
decreasing_line_color='red'    # Bearish candles
```

### Adding Indicators
```python
# Add EMA example
ema20 = df['close'].ewm(span=20).mean()
self.fig.add_trace(
    go.Scatter(x=df.index, y=ema20, name='EMA20'),
    row=1, col=1
)
```

## Troubleshooting

### Common Issues

1. **No Data Returned**
   - Check Databento API key is set correctly
   - Verify contract symbol exists
   - Ensure market hours for futures trading

2. **Chart Not Updating**
   - Manual browser refresh needed in current version
   - Check update interval is reasonable (>10 seconds)

3. **Performance Issues**
   - Reduce hours of data displayed
   - Increase update interval
   - Clear cache with `provider.clear_cache()`

## Future Enhancements

### Planned Features
- [ ] Real-time WebSocket streaming integration
- [ ] Plotly Dash for automatic browser updates
- [ ] Additional technical indicators (RSI, MACD, Bollinger)
- [ ] Multi-timeframe support (1m, 5m, 15m, 1h)
- [ ] Trade execution integration
- [ ] Alerts and notifications
- [ ] Mobile-responsive design

### Performance Optimizations
- [ ] Incremental data updates
- [ ] WebGL rendering for large datasets
- [ ] Background data fetching
- [ ] Persistent cache storage

## API Reference

### NQFiveMinuteChart Class
```python
chart = NQFiveMinuteChart(
    symbol="NQM5",      # Contract symbol
    hours=4,            # Hours of data
    update_interval=30  # Seconds between updates
)

# Run interactive (browser)
chart.run_interactive()

# Save to file
filename = chart.save_chart("output.html")
```

### Databento5MinuteProvider Class
```python
provider = Databento5MinuteProvider()

# Get historical bars
df = provider.get_historical_5min_bars(
    symbol="NQM5",
    hours_back=24
)

# Get latest N bars
df = provider.get_latest_bars(symbol="NQM5", count=50)

# Clear cache
provider.clear_cache()
```

## License and Credits

Built with:
- **Plotly**: Interactive charting library
- **Databento**: Professional market data provider
- **Pandas**: Data manipulation and aggregation

---

**Note**: This tool requires a valid Databento subscription with access to GLBX.MDP3 dataset for CME futures data.
