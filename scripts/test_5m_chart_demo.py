#!/usr/bin/env python3
"""
Demo 5-minute chart with simulated data
Tests the charting functionality without requiring API access
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_demo_data(hours=4):
    """Create realistic demo 5-minute OHLCV data"""
    # Start time
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)

    # Create 5-minute timestamps
    timestamps = pd.date_range(start=start_time, end=end_time, freq='5min')

    # Generate realistic price movement
    num_bars = len(timestamps)
    base_price = 21800

    # Random walk for prices
    price_changes = np.random.normal(0, 5, num_bars)
    price_changes = np.cumsum(price_changes)

    data = []
    for i, ts in enumerate(timestamps):
        # Base price with trend
        mid_price = base_price + price_changes[i]

        # OHLC generation
        open_price = mid_price + np.random.normal(0, 2)
        close_price = mid_price + np.random.normal(0, 2)
        high_price = max(open_price, close_price) + abs(np.random.normal(0, 3))
        low_price = min(open_price, close_price) - abs(np.random.normal(0, 3))

        # Volume generation (higher during market hours)
        hour = ts.hour
        if 9 <= hour <= 16:
            volume = np.random.randint(1000, 5000)
        else:
            volume = np.random.randint(100, 1000)

        data.append({
            'timestamp': ts,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })

    return pd.DataFrame(data).set_index('timestamp')

def create_chart(df, symbol="NQM5"):
    """Create the plotly figure with candlestick and volume"""
    # Create subplots
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f'{symbol} - 5 Minute Chart (Demo Data)', 'Volume'),
        row_heights=[0.7, 0.3]
    )

    # Add candlestick chart
    candlestick = go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Price',
        increasing_line_color='green',
        decreasing_line_color='red'
    )
    fig.add_trace(candlestick, row=1, col=1)

    # Add volume bars
    colors = ['red' if close < open else 'green'
             for close, open in zip(df['close'], df['open'])]

    volume_bars = go.Bar(
        x=df.index,
        y=df['volume'],
        name='Volume',
        marker_color=colors,
        opacity=0.7
    )
    fig.add_trace(volume_bars, row=2, col=1)

    # Add moving averages if we have enough data
    if len(df) >= 20:
        ma20 = df['close'].rolling(window=20).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=ma20,
                name='MA20',
                line=dict(color='blue', width=1)
            ),
            row=1, col=1
        )

    if len(df) >= 50:
        ma50 = df['close'].rolling(window=50).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=ma50,
                name='MA50',
                line=dict(color='orange', width=1)
            ),
            row=1, col=1
        )

    # Update layout
    fig.update_layout(
        title=dict(
            text=f"{symbol} - 5 Minute Chart (Demo)",
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
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_xaxes(title_text="Time", row=2, col=1)

    # Add current price annotation
    last_price = df['close'].iloc[-1]
    last_time = df.index[-1]

    fig.add_annotation(
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

    # Add statistics box
    high_price = df['high'].max()
    low_price = df['low'].min()
    total_volume = df['volume'].sum()

    stats_text = (
        f"Current: ${last_price:,.2f}<br>"
        f"High: ${high_price:,.2f}<br>"
        f"Low: ${low_price:,.2f}<br>"
        f"Volume: {total_volume:,}"
    )

    fig.add_annotation(
        text=stats_text,
        xref="paper", yref="paper",
        x=0.99, y=0.99,
        showarrow=False,
        font=dict(size=12, color="white"),
        bgcolor="rgba(0,0,0,0.8)",
        xanchor="right",
        yanchor="top"
    )

    # Add demo notice
    fig.add_annotation(
        text="⚠️ DEMO DATA - Not Live Market Data",
        xref="paper", yref="paper",
        x=0.5, y=1.05,
        showarrow=False,
        font=dict(size=14, color="yellow"),
        xanchor="center",
        yanchor="bottom"
    )

    return fig

def main():
    """Run the demo"""
    print("🎨 Creating 5-Minute Chart Demo with Simulated Data")
    print("=" * 50)

    # Generate demo data
    print("\n📊 Generating demo data...")
    df = create_demo_data(hours=4)
    print(f"✅ Generated {len(df)} 5-minute bars")
    print(f"Time range: {df.index[0]} to {df.index[-1]}")

    # Create chart
    print("\n📈 Creating interactive chart...")
    fig = create_chart(df)

    # Save to HTML
    output_file = "outputs/demo_5m_chart.html"
    fig.write_html(output_file)
    print(f"\n✅ Chart saved to: {output_file}")

    # Show in browser
    print("\n🌐 Opening chart in browser...")
    fig.show()

    # Display sample data
    print("\n📊 Sample data (last 5 bars):")
    print(df.tail())

if __name__ == "__main__":
    main()
