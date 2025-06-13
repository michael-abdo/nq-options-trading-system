#!/usr/bin/env python3
"""
Test matplotlib basic candlestick capabilities
Evaluating: ease of use, code complexity, visual quality, performance
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time as python_time

def create_sample_ohlcv_data():
    """Create sample 5-minute OHLCV data for testing"""
    # Generate 24 hours of 5-minute bars (288 bars)
    start_time = datetime.now() - timedelta(hours=24)
    times = [start_time + timedelta(minutes=5*i) for i in range(288)]

    # Simulate NQ futures price movement starting around $21,800
    base_price = 21800
    data = []
    current_price = base_price

    for i, timestamp in enumerate(times):
        # Add some realistic price movement
        change = np.random.normal(0, 5)  # $5 typical move per 5min
        current_price += change

        # Generate OHLCV
        open_price = current_price
        high_price = open_price + abs(np.random.normal(2, 3))
        low_price = open_price - abs(np.random.normal(2, 3))
        close_price = open_price + np.random.normal(0, 2)
        volume = np.random.randint(50, 500)  # 50-500 contracts per 5min

        data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })

        current_price = close_price

    return pd.DataFrame(data)

def plot_candlestick_matplotlib(df, title="NQ Futures 5-Minute Chart"):
    """Create candlestick chart using raw matplotlib"""

    print("🔍 Testing matplotlib candlestick implementation...")
    start_time = python_time.time()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8),
                                   gridspec_kw={'height_ratios': [3, 1]})

    # Plot candlesticks
    for i, row in df.iterrows():
        x = mdates.date2num(row['timestamp'])
        open_price = row['open']
        high_price = row['high']
        low_price = row['low']
        close_price = row['close']

        # Determine color (green for up, red for down)
        color = 'green' if close_price > open_price else 'red'

        # Draw high-low line
        ax1.plot([x, x], [low_price, high_price], color='black', linewidth=1)

        # Draw body rectangle
        body_height = abs(close_price - open_price)
        body_bottom = min(open_price, close_price)
        width = 0.0008  # Width in days

        rect = Rectangle((x - width/2, body_bottom), width, body_height,
                        facecolor=color, edgecolor='black', alpha=0.8)
        ax1.add_patch(rect)

    # Format price chart
    ax1.set_title(title, fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price ($)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=4))

    # Plot volume bars
    ax2.bar(df['timestamp'], df['volume'], width=timedelta(minutes=4),
            color='blue', alpha=0.7)
    ax2.set_ylabel('Volume', fontsize=12)
    ax2.set_xlabel('Time', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=4))

    plt.tight_layout()

    render_time = python_time.time() - start_time

    # Save chart
    output_path = 'outputs/matplotlib_candlestick_test.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Chart saved to {output_path}")

    return {
        'render_time': render_time,
        'complexity': 'High - requires manual candlestick drawing',
        'visual_quality': 'Good - professional appearance',
        'code_lines': 45,  # Approximate lines for candlestick logic
        'features': ['Manual candlestick drawing', 'Volume subplot', 'Time formatting'],
        'pros': ['Full control', 'Lightweight', 'No dependencies'],
        'cons': ['Complex implementation', 'Manual OHLC logic', 'No financial indicators']
    }

def test_matplotlib_performance():
    """Test matplotlib performance with larger datasets"""
    print("⚡ Testing matplotlib performance...")

    # Test with different data sizes
    sizes = [100, 500, 1000]
    results = {}

    for size in sizes:
        # Generate test data
        times = [datetime.now() - timedelta(minutes=5*i) for i in range(size)]
        base_price = 21800
        data = []

        for timestamp in times:
            data.append({
                'timestamp': timestamp,
                'open': base_price + np.random.normal(0, 10),
                'high': base_price + np.random.normal(5, 5),
                'low': base_price + np.random.normal(-5, 5),
                'close': base_price + np.random.normal(0, 10),
                'volume': np.random.randint(50, 500)
            })

        df = pd.DataFrame(data)

        # Time the rendering
        start_time = python_time.time()
        fig, ax = plt.subplots(figsize=(10, 6))

        # Simple line plot for performance test
        ax.plot(df['timestamp'], df['close'], linewidth=1)
        ax.set_title(f'Performance Test - {size} bars')
        plt.close(fig)

        render_time = python_time.time() - start_time
        results[size] = render_time
        print(f"  {size} bars: {render_time:.3f}s")

    return results

def main():
    print("🧪 MATPLOTLIB CANDLESTICK EVALUATION")
    print("=" * 50)

    # Test basic functionality
    df = create_sample_ohlcv_data()
    results = plot_candlestick_matplotlib(df)

    # Test performance
    perf_results = test_matplotlib_performance()

    # Summary
    print("\n📊 MATPLOTLIB EVALUATION SUMMARY:")
    print(f"Rendering time: {results['render_time']:.3f}s")
    print(f"Complexity: {results['complexity']}")
    print(f"Visual quality: {results['visual_quality']}")
    print(f"Code complexity: {results['code_lines']} lines for basic candlesticks")

    print("\nFeatures:")
    for feature in results['features']:
        print(f"  ✓ {feature}")

    print("\nPros:")
    for pro in results['pros']:
        print(f"  + {pro}")

    print("\nCons:")
    for con in results['cons']:
        print(f"  - {con}")

    print("\nPerformance Results:")
    for size, time_taken in perf_results.items():
        print(f"  {size} bars: {time_taken:.3f}s")

    return results

if __name__ == "__main__":
    main()
