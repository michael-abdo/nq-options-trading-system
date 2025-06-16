# IFD v3.0 Dashboard Setup Guide

## 🎯 Overview

The enhanced NQ futures dashboard integrates IFD (Institutional Flow Detection) v3.0 signals directly into the live web interface at `http://127.0.0.1:8050/`.

## 📦 Installation

### Required Dependencies

```bash
# Install Dash for web dashboard
pip install dash plotly

# Optional: JSON schema validation
pip install jsonschema
```

### Verify Installation

```bash
# Test the enhanced dashboard
python scripts/start_ifd_dashboard.py --help
```

## 🚀 Usage

### Quick Start

```bash
# Launch enhanced dashboard with IFD integration
python scripts/start_ifd_dashboard.py

# Custom settings
python scripts/start_ifd_dashboard.py --symbol NQM5 --hours 6 --update 15
```

### IFD Configuration Options

The dashboard includes a dropdown to select IFD presets:

1. **Default**: Standard chart without IFD signals
2. **IFD Enabled**: Basic IFD signals (70% confidence threshold)
3. **IFD Advanced**: Enhanced IFD with background highlighting and more indicators
4. **IFD Minimal**: Performance-optimized (80% confidence threshold, fewer signals)

## 📊 Dashboard Features

### Enhanced Controls

- **Symbol Input**: Change the futures contract symbol
- **Time Range**: Select from 1 hour to 1 day of data
- **IFD Configuration**: Live switching between IFD presets
- **Reset Chart**: Refresh data and chart

### IFD Signal Display

When IFD is enabled, you'll see:

- 🔺 **Triangle markers** above/below candlesticks
- 🎨 **Color coding**: Green (BUY), Lime (STRONG_BUY), Orange (MONITOR)
- 📏 **Size coding**: Larger triangles = stronger signals (EXTREME > VERY_HIGH > HIGH > MODERATE)
- 💬 **Hover tooltips** with detailed signal information:
  - Action (BUY, STRONG_BUY, MONITOR)
  - Confidence percentage
  - Signal strength
  - Number of signals in window
  - Timestamp

### Real-time Updates

- Chart refreshes every 30 seconds (configurable)
- Live status indicators show:
  - Current price
  - High/Low for the session
  - Total volume
  - Number of IFD signals displayed

## ⚙️ Configuration Details

### IFD Enabled (Basic)
```json
{
  "show_signals": true,
  "min_confidence_display": 0.7,
  "show_confidence_background": false,
  "max_signals_display": 200
}
```

### IFD Advanced (Enhanced)
```json
{
  "show_signals": true,
  "min_confidence_display": 0.65,
  "show_confidence_background": true,
  "max_signals_display": 300,
  "additional_indicators": ["sma", "ema", "vwap"]
}
```

### IFD Minimal (Performance)
```json
{
  "show_signals": true,
  "min_confidence_display": 0.8,
  "show_confidence_background": false,
  "max_signals_display": 100
}
```

## 🕐 Market Hours

The dashboard works best during active trading hours:

- **Futures Trading**: Sunday 6:00 PM - Friday 5:00 PM ET
- **Regular Session**: Monday 9:30 AM - Friday 4:00 PM ET
- **Weekends**: Limited data availability (markets closed)

## 🔧 Troubleshooting

### No Data Available

If you see "Waiting for market data...":
- Check if markets are open
- Verify Databento API key is valid
- Try a different symbol (NQZ5, ESM5, etc.)

### IFD Not Available

If IFD status shows "Not Available":
- Ensure IFD v3.0 components are installed
- Check that `ifd_chart_bridge.py` is accessible
- Verify MBO streaming permissions in Databento

### Dashboard Won't Start

Common issues:
```bash
# Missing Dash
pip install dash plotly

# Port already in use
python scripts/start_ifd_dashboard.py --port 8051

# Import errors
export PYTHONPATH=/Users/Mike/trading/algos/EOD:$PYTHONPATH
```

## 🎮 Live Dashboard URL

Once running, access the enhanced dashboard at:
**http://127.0.0.1:8050/**

The URL remains the same, but now includes:
- IFD configuration dropdown
- Real-time signal overlays
- Enhanced status indicators
- Configuration info panel

## 📈 Production Usage

For live trading, recommended settings:
- **Symbol**: Current month contract (NQM5, NQU5, etc.)
- **Time Range**: 4-6 hours
- **Update Interval**: 15-30 seconds
- **IFD Config**: "IFD Advanced" for full feature set

## 🆕 Differences from Standard Dashboard

### New Features
- IFD configuration dropdown
- Signal overlay visualization
- Configuration info panel
- Real-time signal counting
- Enhanced status indicators

### Backward Compatibility
- All original dashboard features preserved
- Same URL and port
- Graceful fallback when IFD unavailable
- No breaking changes to existing functionality

The enhanced dashboard is a drop-in replacement that adds IFD capabilities while maintaining full backward compatibility with the original functionality.
