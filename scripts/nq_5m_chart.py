#!/usr/bin/env python3
"""
Simple 5-Minute NQ Futures Chart
Real-time candlestick chart with volume using Plotly and Databento data
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
from databento_5m_provider import Databento5MinuteProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NQFiveMinuteChart:
    """Interactive 5-minute chart for NQ futures"""

    def __init__(self, symbol="NQM5", hours=4, update_interval=30):
        """
        Initialize the chart

        Args:
            symbol: Contract symbol (default: NQM5)
            hours: Hours of data to display (default: 4)
            update_interval: Seconds between updates (default: 30)
        """
        self.symbol = symbol
        self.hours = hours
        self.update_interval = update_interval
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

    def create_chart(self, df):
        """
        Create the plotly figure with candlestick and volume

        Args:
            df: DataFrame with OHLCV data
        """
        # Convert UTC timestamps to Eastern Time for display
        et_tz = pytz.timezone('US/Eastern')
        df_display = df.copy()
        df_display.index = df_display.index.tz_convert(et_tz)

        # Create subplots
        self.fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(f'{self.symbol} - 5 Minute Chart', 'Volume'),
            row_heights=[0.7, 0.3]
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

        # Add volume bars
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

        # Add moving averages if we have enough data
        if len(df_display) >= 20:
            ma20 = df_display['close'].rolling(window=20).mean()
            self.fig.add_trace(
                go.Scatter(
                    x=df_display.index,
                    y=ma20,
                    name='MA20',
                    line=dict(color='blue', width=1)
                ),
                row=1, col=1
            )

        if len(df_display) >= 50:
            ma50 = df_display['close'].rolling(window=50).mean()
            self.fig.add_trace(
                go.Scatter(
                    x=df_display.index,
                    y=ma50,
                    name='MA50',
                    line=dict(color='orange', width=1)
                ),
                row=1, col=1
            )

        # Update layout
        self.fig.update_layout(
            title=dict(
                text=f"{self.symbol} - 5 Minute Chart (Eastern Time)",
                font=dict(size=20)
            ),
            yaxis_title="Price ($)",
            xaxis_rangeslider_visible=False,
            height=800,
            showlegend=True,
            hovermode='x unified',
            template='plotly_dark'  # Dark theme
        )

        # Update y-axis labels
        self.fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        self.fig.update_yaxes(title_text="Volume", row=2, col=1)
        self.fig.update_xaxes(title_text="Time (Eastern)", row=2, col=1)

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
        """Run the chart in interactive mode (opens in browser)"""
        logger.info(f"Starting {self.symbol} 5-minute chart...")
        logger.info(f"Update interval: {self.update_interval} seconds")
        logger.info(f"Time range: {self.hours} hours")

        # Initial chart creation
        if not self.update_chart():
            logger.error("Failed to create initial chart")
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
        """Save the chart as an HTML file"""
        if filename is None:
            filename = f"nq_5m_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        if self.update_chart():
            self.fig.write_html(filename)
            logger.info(f"Chart saved to {filename}")
            return filename
        return None

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='NQ Futures 5-Minute Chart')
    parser.add_argument('--symbol', default='NQM5', help='Contract symbol (default: NQM5)')
    parser.add_argument('--hours', type=int, default=4, help='Hours of data to display (default: 4)')
    parser.add_argument('--update', type=int, default=30, help='Update interval in seconds (default: 30)')
    parser.add_argument('--save', action='store_true', help='Save chart to HTML file instead of interactive')
    parser.add_argument('--output', help='Output filename for saved chart')

    args = parser.parse_args()

    # Create chart instance
    chart = NQFiveMinuteChart(
        symbol=args.symbol,
        hours=args.hours,
        update_interval=args.update
    )

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
