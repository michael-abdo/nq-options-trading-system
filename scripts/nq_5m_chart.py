#!/usr/bin/env python3
"""
Simple 5-Minute NQ Futures Chart
Real-time candlestick chart with volume using Plotly and Databento data
"""

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    print("📊 Plotly not available - running in data export mode")
    PLOTLY_AVAILABLE = False
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import signal
import sys
import time
import logging
import pytz
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from databento_5m_provider import Databento5MinuteProvider
from utils.timezone_utils import format_eastern_timestamp
from chart_config_manager import ChartConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NQFiveMinuteChart:
    """Interactive 5-minute chart for NQ futures"""

    def __init__(self, config=None, symbol=None, hours=None, update_interval=None):
        """
        Initialize the chart

        Args:
            config: Configuration dictionary (takes precedence over individual args)
            symbol: Contract symbol (default from config or NQM5)
            hours: Hours of data to display (default from config or 4)
            update_interval: Seconds between updates (default from config or 30)
        """
        # Use config or fallback to defaults
        if config:
            self.config = config
            self.symbol = symbol or config.get("data", {}).get("symbol", "NQM5")
            self.hours = hours or config.get("chart", {}).get("time_range_hours", 4)
            self.update_interval = update_interval or config.get("chart", {}).get("update_interval", 30)
            self.theme = config.get("chart", {}).get("theme", "dark")
            self.height = config.get("chart", {}).get("height", 800)
            self.width = config.get("chart", {}).get("width", 1200)
            self.show_volume = config.get("chart", {}).get("show_volume", True)
            self.volume_ratio = config.get("chart", {}).get("volume_height_ratio", 0.3)
            self.indicators_enabled = config.get("indicators", {}).get("enabled", ["sma"])
            self.display_config = config.get("display", {})
        else:
            self.config = {}
            self.symbol = symbol or "NQM5"
            self.hours = hours or 4
            self.update_interval = update_interval or 30
            self.theme = "dark"
            self.height = 800
            self.width = 1200
            self.show_volume = True
            self.volume_ratio = 0.3
            self.indicators_enabled = ["sma"]
            self.display_config = {}

        self.data_provider = Databento5MinuteProvider()
        self.fig = None
        self.running = True

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received")
        self.running = False
        sys.exit(0)

    def _create_data_export(self, df):
        """
        Export chart data when plotly is not available

        Args:
            df: DataFrame with OHLCV data
        """
        print("\n📊 5-MINUTE NQ CHART DATA")
        print("=" * 60)
        print(f"Symbol: {self.symbol}")
        print(f"Time Range: {df.index[0]} to {df.index[-1]}")
        print(f"Bars: {len(df)}")
        print("-" * 60)

        # Show recent data
        recent_bars = df.tail(10)
        print("📈 Recent 10 Bars:")
        print(recent_bars[['open', 'high', 'low', 'close', 'volume']].round(2))

        # Summary stats
        print("\n📊 Summary Statistics:")
        print(f"High: ${df['high'].max():.2f}")
        print(f"Low: ${df['low'].min():.2f}")
        print(f"Current: ${df['close'].iloc[-1]:.2f}")
        print(f"Volume (avg): {df['volume'].mean():.0f}")

        # Save to CSV
        filename = f"nq_5m_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename)
        print(f"\n💾 Data saved to: {filename}")
        print("\n💡 To see charts, install plotly: pip install plotly")
        return None

    def create_chart(self, df):
        """
        Create the plotly figure with candlestick and volume
        Or export data if plotly is not available

        Args:
            df: DataFrame with OHLCV data
        """
        if not PLOTLY_AVAILABLE:
            return self._create_data_export(df)
        # Convert UTC timestamps to Eastern Time for display
        et_tz = pytz.timezone('US/Eastern')
        df_display = df.copy()
        df_display.index = df_display.index.tz_convert(et_tz)

        # Create subplots (adjust based on volume display setting)
        if self.show_volume:
            self.fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=(f'{self.symbol} - 5 Minute Chart', 'Volume'),
                row_heights=[1.0 - self.volume_ratio, self.volume_ratio]
            )
        else:
            self.fig = make_subplots(
                rows=1, cols=1,
                subplot_titles=(f'{self.symbol} - 5 Minute Chart',)
            )

        # Add candlestick chart
        candlestick = go.Candlestick(
            x=df_display.index,
            open=df_display['open'],
            high=df_display['high'],
            low=df_display['low'],
            close=df_display['close'],
            name='Price',
            increasing_line_color='green',
            decreasing_line_color='red'
        )
        self.fig.add_trace(candlestick, row=1, col=1)

        # Add volume bars (only if volume is enabled)
        if self.show_volume:
            colors = ['red' if close < open else 'green'
                     for close, open in zip(df_display['close'], df_display['open'])]

            volume_bars = go.Bar(
                x=df_display.index,
                y=df_display['volume'],
                name='Volume',
                marker_color=colors,
                opacity=0.7
            )
            self.fig.add_trace(volume_bars, row=2, col=1)

        # Add indicators based on configuration
        self._add_indicators(df_display)

        # Update layout using configuration
        template = 'plotly_dark' if self.theme == 'dark' else 'plotly_white'
        self.fig.update_layout(
            title=dict(
                text=f"{self.symbol} - 5 Minute Chart (Eastern Time)",
                font=dict(size=20)
            ),
            yaxis_title="Price ($)",
            xaxis_rangeslider_visible=False,
            height=self.height,
            width=self.width,
            showlegend=True,
            hovermode='x unified',
            template=template
        )

        # Update y-axis labels
        self.fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        if self.show_volume:
            self.fig.update_yaxes(title_text="Volume", row=2, col=1)
            self.fig.update_xaxes(title_text="Time (Eastern)", row=2, col=1)
        else:
            self.fig.update_xaxes(title_text="Time (Eastern)", row=1, col=1)

        # Add current price annotation
        last_price = df['close'].iloc[-1]
        last_time = df_display.index[-1]  # Use Eastern Time for display

        self.fig.add_annotation(
            x=last_time,
            y=last_price,
            text=f"${last_price:,.2f}",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="cyan",
            ax=50,
            ay=0,
            bgcolor="rgba(0,0,0,0.8)",
            font=dict(size=14, color="white")
        )

    def _add_indicators(self, df_display):
        """Add technical indicators based on configuration"""
        if not self.indicators_enabled:
            return

        config_indicators = self.config.get("indicators", {})

        # Simple Moving Averages
        if "sma" in self.indicators_enabled:
            sma_config = config_indicators.get("sma", {})
            periods = sma_config.get("periods", [20, 50])
            colors = sma_config.get("colors", ["blue", "orange"])

            for i, period in enumerate(periods):
                if len(df_display) >= period:
                    ma = df_display['close'].rolling(window=period).mean()
                    color = colors[i] if i < len(colors) else "gray"
                    self.fig.add_trace(
                        go.Scatter(
                            x=df_display.index,
                            y=ma,
                            name=f'SMA{period}',
                            line=dict(color=color, width=1)
                        ),
                        row=1, col=1
                    )

        # Exponential Moving Averages
        if "ema" in self.indicators_enabled:
            ema_config = config_indicators.get("ema", {})
            periods = ema_config.get("periods", [12, 26])
            colors = ema_config.get("colors", ["cyan", "magenta"])

            for i, period in enumerate(periods):
                if len(df_display) >= period:
                    ema = df_display['close'].ewm(span=period).mean()
                    color = colors[i] if i < len(colors) else "gray"
                    self.fig.add_trace(
                        go.Scatter(
                            x=df_display.index,
                            y=ema,
                            name=f'EMA{period}',
                            line=dict(color=color, width=1)
                        ),
                        row=1, col=1
                    )

        # VWAP (Volume Weighted Average Price)
        if "vwap" in self.indicators_enabled:
            vwap_config = config_indicators.get("vwap", {})
            if vwap_config.get("enabled", False) and len(df_display) > 0:
                # Calculate VWAP
                typical_price = (df_display['high'] + df_display['low'] + df_display['close']) / 3
                vwap = (typical_price * df_display['volume']).cumsum() / df_display['volume'].cumsum()

                color = vwap_config.get("color", "yellow")
                line_width = vwap_config.get("line_width", 2.0)

                self.fig.add_trace(
                    go.Scatter(
                        x=df_display.index,
                        y=vwap,
                        name='VWAP',
                        line=dict(color=color, width=line_width)
                    ),
                    row=1, col=1
                )

    def update_chart(self):
        """Update the chart with latest data"""
        try:
            # Calculate number of 5-minute bars
            bars_needed = (self.hours * 60) // 5

            # Get latest data
            df = self.data_provider.get_latest_bars(
                symbol=self.symbol,
                count=bars_needed
            )

            if df.empty:
                logger.warning("No data available")
                return False

            # Create or update chart
            self.create_chart(df)

            # Add update timestamp
            self.fig.add_annotation(
                text=f"Updated: {datetime.now(pytz.UTC).strftime('%H:%M:%S')} UTC",
                xref="paper", yref="paper",
                x=0.01, y=0.99,
                showarrow=False,
                font=dict(size=12, color="gray"),
                bgcolor="rgba(0,0,0,0.8)"
            )

            # Calculate some statistics
            last_price = df['close'].iloc[-1]
            high_price = df['high'].max()
            low_price = df['low'].min()
            total_volume = df['volume'].sum()

            # Add statistics box
            stats_text = (
                f"Current: ${last_price:,.2f}<br>"
                f"High: ${high_price:,.2f}<br>"
                f"Low: ${low_price:,.2f}<br>"
                f"Volume: {total_volume:,}"
            )

            self.fig.add_annotation(
                text=stats_text,
                xref="paper", yref="paper",
                x=0.99, y=0.99,
                showarrow=False,
                font=dict(size=12, color="white"),
                bgcolor="rgba(0,0,0,0.8)",
                xanchor="right",
                yanchor="top"
            )

            logger.info(f"Chart updated - Last price: ${last_price:,.2f}")
            return True

        except Exception as e:
            logger.error(f"Error updating chart: {e}")
            return False

    def run_interactive(self):
        """Run the chart in interactive mode (opens in browser) or data export mode"""
        logger.info(f"Starting {self.symbol} 5-minute chart...")
        logger.info(f"Update interval: {self.update_interval} seconds")
        logger.info(f"Time range: {self.hours} hours")

        # Initial chart creation
        if not self.update_chart():
            logger.error("Failed to create initial chart")
            return

        if not PLOTLY_AVAILABLE:
            print("\n📊 Data export mode - no interactive chart available")
            print("💡 Install plotly for interactive charts: pip install plotly")
            return

        # Show the chart
        self.fig.show()

        # Keep updating
        logger.info("Chart opened in browser. Press Ctrl+C to stop.")
        while self.running:
            time.sleep(self.update_interval)

            # Update chart
            if self.update_chart():
                # In a real implementation, we'd update the existing chart
                # For now, this would require more complex Dash integration
                logger.info("Data refreshed (manual browser refresh needed)")

    def save_chart(self, filename=None):
        """Save the chart as an HTML file or CSV data"""
        if not PLOTLY_AVAILABLE:
            print("📊 Chart save not available without plotly - data already saved as CSV")
            return None

        if filename is None:
            filename = f"nq_5m_chart_{format_eastern_timestamp()}.html"

        if self.update_chart():
            self.fig.write_html(filename)
            logger.info(f"Chart saved to {filename}")
            return filename
        return None

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='NQ Futures 5-Minute Chart')
    parser.add_argument('--symbol', help='Contract symbol (overrides config)')
    parser.add_argument('--hours', type=int, help='Hours of data to display (overrides config)')
    parser.add_argument('--update', type=int, help='Update interval in seconds (overrides config)')
    parser.add_argument('--save', action='store_true', help='Save chart to HTML file instead of interactive')
    parser.add_argument('--output', help='Output filename for saved chart')

    # New configuration options
    parser.add_argument('--config', default='default', help='Configuration preset to use (default, scalping, swing_trading, minimal)')
    parser.add_argument('--theme', choices=['light', 'dark'], help='Chart theme (overrides config)')
    parser.add_argument('--indicators', nargs='*', choices=['sma', 'ema', 'vwap'], help='Indicators to enable (overrides config)')
    parser.add_argument('--no-volume', action='store_true', help='Hide volume subplot')
    parser.add_argument('--list-configs', action='store_true', help='List available configuration presets')

    args = parser.parse_args()

    # Initialize configuration manager
    config_manager = ChartConfigManager()

    # Handle list configs command
    if args.list_configs:
        print("Available configuration presets:")
        for config_name in config_manager.list_available_configs():
            config = config_manager.load_config(config_name)
            summary = config_manager.get_config_summary(config)
            print(f"  {config_name}: {summary['theme']} theme, {summary['time_range']}h, indicators: {summary['indicators_enabled']}")
        return

    # Load base configuration
    config = config_manager.load_config(args.config)

    # Create CLI overrides
    cli_overrides = {}

    if args.symbol:
        cli_overrides.setdefault("data", {})["symbol"] = args.symbol
    if args.hours:
        cli_overrides.setdefault("chart", {})["time_range_hours"] = args.hours
    if args.update:
        cli_overrides.setdefault("chart", {})["update_interval"] = args.update
    if args.theme:
        cli_overrides.setdefault("chart", {})["theme"] = args.theme
    if args.indicators is not None:
        cli_overrides.setdefault("indicators", {})["enabled"] = args.indicators
    if args.no_volume:
        cli_overrides.setdefault("chart", {})["show_volume"] = False

    # Merge configurations
    final_config = config_manager.merge_configs(config, cli_overrides)

    # Create chart instance with configuration
    chart = NQFiveMinuteChart(config=final_config)

    try:
        if args.save:
            # Save mode
            filename = chart.save_chart(args.output)
            if filename:
                print(f"✅ Chart saved to: {filename}")
            else:
                print("❌ Failed to save chart")
        else:
            # Interactive mode
            chart.run_interactive()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
