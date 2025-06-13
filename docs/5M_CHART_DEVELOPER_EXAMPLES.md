# 5-Minute Chart Developer Integration Examples

## Overview
This document provides code examples for integrating the 5-minute chart system into your own applications.

## Basic Usage

### Simple Chart Creation
```python
#!/usr/bin/env python3
"""
Basic 5-minute chart example
"""
import sys
sys.path.append('scripts')

from nq_5m_chart import NQFiveMinuteChart
from chart_config_manager import ChartConfigManager

# Load default configuration
config_manager = ChartConfigManager()
config = config_manager.load_config("default")

# Create and display chart
chart = NQFiveMinuteChart(config=config)
chart.run_interactive()
```

### Custom Configuration
```python
#!/usr/bin/env python3
"""
Custom configuration example
"""
import sys
sys.path.append('scripts')

from nq_5m_chart import NQFiveMinuteChart

# Define custom configuration
custom_config = {
    "chart": {
        "theme": "light",
        "height": 1000,
        "width": 1400,
        "update_interval": 15,
        "time_range_hours": 6,
        "show_volume": True
    },
    "indicators": {
        "enabled": ["sma", "ema", "vwap"],
        "sma": {
            "periods": [10, 20, 50],
            "colors": ["blue", "red", "green"]
        },
        "ema": {
            "periods": [8, 21],
            "colors": ["cyan", "magenta"]
        },
        "vwap": {
            "enabled": True,
            "color": "orange",
            "line_width": 2.5
        }
    },
    "data": {
        "symbol": "NQU5",
        "timezone": "US/Eastern"
    }
}

# Create chart with custom config
chart = NQFiveMinuteChart(config=custom_config)
chart.save_chart("my_custom_chart.html")
```

## Integration with Web Applications

### Flask Integration
```python
#!/usr/bin/env python3
"""
Flask web application with embedded chart
"""
from flask import Flask, render_template, jsonify
import sys
sys.path.append('scripts')

from nq_5m_chart import NQFiveMinuteChart
from chart_config_manager import ChartConfigManager

app = Flask(__name__)
config_manager = ChartConfigManager()

@app.route('/')
def index():
    return render_template('chart.html')

@app.route('/chart/<config_name>')
def get_chart(config_name):
    """Get chart HTML for embedding"""
    try:
        config = config_manager.load_config(config_name)
        chart = NQFiveMinuteChart(config=config)

        if chart.update_chart():
            # Return chart as HTML div
            return chart.fig.to_html(include_plotlyjs=True, div_id="chart-div")
        else:
            return "Error: Could not generate chart", 500

    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/api/configs')
def list_configs():
    """API endpoint to list available configurations"""
    configs = []
    for name in config_manager.list_available_configs():
        config = config_manager.load_config(name)
        summary = config_manager.get_config_summary(config)
        configs.append({
            "name": name,
            "summary": summary
        })
    return jsonify(configs)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### Django Integration
```python
# views.py
"""
Django view integration
"""
from django.shortcuts import render
from django.http import JsonResponse
import sys
sys.path.append('scripts')

from nq_5m_chart import NQFiveMinuteChart
from chart_config_manager import ChartConfigManager

def chart_view(request, config_name='default'):
    """Render chart page"""
    config_manager = ChartConfigManager()

    try:
        config = config_manager.load_config(config_name)
        chart = NQFiveMinuteChart(config=config)

        if chart.update_chart():
            chart_html = chart.fig.to_html(include_plotlyjs=True)
            context = {
                'chart_html': chart_html,
                'config_name': config_name
            }
            return render(request, 'chart_template.html', context)
        else:
            return render(request, 'error.html', {'error': 'Chart generation failed'})

    except Exception as e:
        return render(request, 'error.html', {'error': str(e)})

def api_chart_data(request):
    """API endpoint for chart data"""
    config_name = request.GET.get('config', 'default')

    try:
        config_manager = ChartConfigManager()
        config = config_manager.load_config(config_name)

        return JsonResponse({
            'status': 'success',
            'config': config,
            'summary': config_manager.get_config_summary(config)
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
```

## Custom Indicator Development

### Adding Custom Indicators
```python
#!/usr/bin/env python3
"""
Example of extending the chart with custom indicators
"""
import pandas as pd
import plotly.graph_objects as go
import sys
sys.path.append('scripts')

from nq_5m_chart import NQFiveMinuteChart

class CustomNQChart(NQFiveMinuteChart):
    """Extended chart with custom indicators"""

    def _add_indicators(self, df_display):
        """Override to add custom indicators"""
        # Call parent method first
        super()._add_indicators(df_display)

        # Add custom RSI indicator
        if "rsi" in self.indicators_enabled:
            rsi = self._calculate_rsi(df_display['close'])
            self._add_rsi_subplot(df_display.index, rsi)

        # Add Bollinger Bands
        if "bollinger" in self.indicators_enabled:
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(df_display['close'])
            self._add_bollinger_bands(df_display.index, bb_upper, bb_middle, bb_lower)

    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    def _add_rsi_subplot(self, x, rsi):
        """Add RSI as separate subplot"""
        # This would require modifying the subplot structure
        # Implementation depends on your specific needs
        pass

    def _add_bollinger_bands(self, x, upper, middle, lower):
        """Add Bollinger Bands to main chart"""
        # Upper band
        self.fig.add_trace(
            go.Scatter(
                x=x, y=upper, name='BB Upper',
                line=dict(color='gray', width=1, dash='dash'),
                showlegend=False
            ), row=1, col=1
        )

        # Lower band
        self.fig.add_trace(
            go.Scatter(
                x=x, y=lower, name='BB Lower',
                line=dict(color='gray', width=1, dash='dash'),
                fill='tonexty', fillcolor='rgba(128,128,128,0.1)',
                showlegend=False
            ), row=1, col=1
        )

# Usage
custom_config = {
    "chart": {"theme": "dark", "height": 900},
    "indicators": {
        "enabled": ["sma", "bollinger", "rsi"]
    }
}

chart = CustomNQChart(config=custom_config)
chart.save_chart("custom_indicators_chart.html")
```

## Automated Trading Integration

### Signal Generation Example
```python
#!/usr/bin/env python3
"""
Example of using chart data for signal generation
"""
import sys
sys.path.append('scripts')

from databento_5m_provider import Databento5MinuteProvider
from chart_config_manager import ChartConfigManager
import pandas as pd

class TradingSignalGenerator:
    """Generate trading signals from 5-minute data"""

    def __init__(self, config=None):
        self.data_provider = Databento5MinuteProvider()
        self.config = config or {}

    def get_latest_signals(self, symbol="NQM5", bars=50):
        """Get latest trading signals"""
        # Get latest data
        df = self.data_provider.get_latest_bars(symbol, bars)
        if df.empty:
            return None

        # Calculate indicators
        signals = {
            'timestamp': df.index[-1],
            'price': df['close'].iloc[-1],
            'volume': df['volume'].iloc[-1]
        }

        # SMA crossover signal
        if len(df) >= 20:
            sma_fast = df['close'].rolling(10).mean()
            sma_slow = df['close'].rolling(20).mean()

            signals['sma_signal'] = self._crossover_signal(sma_fast, sma_slow)

        # Volume spike signal
        vol_ma = df['volume'].rolling(20).mean()
        volume_ratio = df['volume'].iloc[-1] / vol_ma.iloc[-1]
        signals['volume_spike'] = volume_ratio > 2.0

        # Price momentum
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
        signals['momentum'] = price_change

        return signals

    def _crossover_signal(self, fast, slow):
        """Detect moving average crossover"""
        if len(fast) < 2 or len(slow) < 2:
            return 'neutral'

        current_diff = fast.iloc[-1] - slow.iloc[-1]
        previous_diff = fast.iloc[-2] - slow.iloc[-2]

        if previous_diff <= 0 and current_diff > 0:
            return 'bullish_crossover'
        elif previous_diff >= 0 and current_diff < 0:
            return 'bearish_crossover'
        else:
            return 'neutral'

# Usage example
def main():
    signal_gen = TradingSignalGenerator()

    while True:
        signals = signal_gen.get_latest_signals()
        if signals:
            print(f"Signals at {signals['timestamp']}:")
            print(f"  Price: ${signals['price']:,.2f}")
            print(f"  SMA Signal: {signals.get('sma_signal', 'N/A')}")
            print(f"  Volume Spike: {signals.get('volume_spike', False)}")
            print(f"  Momentum: {signals.get('momentum', 0):.3f}")
            print("-" * 40)

        # Wait 30 seconds before next check
        import time
        time.sleep(30)

if __name__ == "__main__":
    main()
```

## Data Export and Analysis

### Export to Pandas DataFrame
```python
#!/usr/bin/env python3
"""
Export chart data for analysis
"""
import sys
sys.path.append('scripts')

from databento_5m_provider import Databento5MinuteProvider
import pandas as pd

def export_chart_data(symbol="NQM5", hours=24, filename=None):
    """Export chart data to CSV"""
    provider = Databento5MinuteProvider()
    bars_needed = (hours * 60) // 5

    df = provider.get_latest_bars(symbol, bars_needed)
    if df.empty:
        print("No data available")
        return None

    # Add technical indicators
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['volume_ma'] = df['volume'].rolling(20).mean()
    df['price_change'] = df['close'].pct_change()

    # Export to CSV
    if filename:
        df.to_csv(filename)
        print(f"Data exported to {filename}")

    return df

# Usage
df = export_chart_data("NQM5", 8, "nq_5m_data.csv")
print(df.describe())
```

## Testing and Validation

### Unit Test Example
```python
#!/usr/bin/env python3
"""
Unit tests for chart functionality
"""
import unittest
import sys
sys.path.append('scripts')

from chart_config_manager import ChartConfigManager
from nq_5m_chart import NQFiveMinuteChart

class TestChartSystem(unittest.TestCase):

    def setUp(self):
        self.config_manager = ChartConfigManager()

    def test_load_default_config(self):
        """Test loading default configuration"""
        config = self.config_manager.load_config("default")
        self.assertIn("chart", config)
        self.assertIn("indicators", config)
        self.assertIn("data", config)

    def test_config_validation(self):
        """Test configuration validation"""
        valid_config = self.config_manager.load_config("default")
        self.assertTrue(self.config_manager.validate_config(valid_config))

    def test_chart_creation(self):
        """Test chart creation with config"""
        config = self.config_manager.load_config("minimal")
        chart = NQFiveMinuteChart(config=config)

        self.assertEqual(chart.theme, config["chart"]["theme"])
        self.assertEqual(chart.height, config["chart"]["height"])

    def test_config_merge(self):
        """Test configuration merging"""
        base_config = {"chart": {"theme": "dark", "height": 800}}
        override_config = {"chart": {"height": 1000}}

        merged = self.config_manager.merge_configs(base_config, override_config)

        self.assertEqual(merged["chart"]["theme"], "dark")
        self.assertEqual(merged["chart"]["height"], 1000)

if __name__ == "__main__":
    unittest.main()
```

## Configuration Best Practices

### Environment-Specific Configs
```python
#!/usr/bin/env python3
"""
Environment-specific configuration example
"""
import os
import sys
sys.path.append('scripts')

from chart_config_manager import ChartConfigManager

def get_environment_config():
    """Get configuration based on environment"""
    env = os.getenv('TRADING_ENV', 'development')
    config_manager = ChartConfigManager()

    if env == 'production':
        config = config_manager.load_config('swing_trading')
        # Override for production settings
        config['chart']['update_interval'] = 60
        config['data']['cache_duration_minutes'] = 30

    elif env == 'testing':
        config = config_manager.load_config('minimal')
        config['chart']['update_interval'] = 5

    else:  # development
        config = config_manager.load_config('default')

    return config

# Usage
config = get_environment_config()
print(f"Using configuration for {os.getenv('TRADING_ENV', 'development')} environment")
```

## Deployment Examples

### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'
services:
  nq-chart:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABENTO_API_KEY=${DATABENTO_API_KEY}
      - TRADING_ENV=production
    volumes:
      - ./config:/app/config
      - ./outputs:/app/outputs
    restart: unless-stopped
```

### Systemd Service
```ini
# /etc/systemd/system/nq-chart.service
[Unit]
Description=NQ 5-Minute Chart Service
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/opt/nq-chart
ExecStart=/opt/nq-chart/venv/bin/python scripts/nq_5m_chart.py --config production
Restart=always
RestartSec=10
Environment=DATABENTO_API_KEY=your_api_key_here

[Install]
WantedBy=multi-user.target
```

These examples provide a comprehensive foundation for integrating the 5-minute chart system into various applications and environments.
