#!/usr/bin/env python3
"""
Test mplfinance financial-specific features and ease of use
Evaluating: financial chart quality, built-in indicators, ease of use, styling
"""

import mplfinance as mpf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time as python_time

def create_sample_ohlcv_data():
    """Create sample 5-minute OHLCV data for testing with proper pandas formatting"""
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
            'Open': open_price,
            'High': high_price,
            'Low': low_price,
            'Close': close_price,
            'Volume': volume
        })

        current_price = close_price

    # Create DataFrame with datetime index (required by mplfinance)
    df = pd.DataFrame(data, index=times)
    return df

def plot_candlestick_mplfinance(df, title="NQ Futures 5-Minute Chart"):
    """Create candlestick chart using mplfinance"""

    print("🔍 Testing mplfinance financial chart implementation...")
    start_time = python_time.time()

    # Basic candlestick chart with volume
    output_path = 'outputs/mplfinance_basic_test.png'

    mpf.plot(
        df,
        type='candle',
        volume=True,
        title=title,
        style='yahoo',  # Professional financial style
        savefig=output_path,
        figsize=(12, 8)
    )

    render_time = python_time.time() - start_time
    print(f"✅ Basic chart saved to {output_path}")

    return {
        'render_time': render_time,
        'complexity': 'Low - purpose-built for financial charts',
        'visual_quality': 'Excellent - professional financial appearance',
        'code_lines': 8,  # Just the mpf.plot call
        'features': ['Built-in candlestick', 'Volume subplot', 'Financial styling', 'Multiple themes'],
        'pros': ['Extremely simple', 'Professional financial charts', 'Built-in indicators', 'Optimized for OHLCV'],
        'cons': ['Less customization', 'Static output only', 'Limited interactivity']
    }

def test_mplfinance_advanced_features(df):
    """Test advanced mplfinance features"""
    print("📊 Testing mplfinance advanced features...")

    # Calculate moving averages
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()

    # Test multiple styles and features
    styles = ['yahoo', 'charles', 'nightclouds', 'sas']
    results = {}

    for style in styles:
        start_time = python_time.time()

        # Add moving averages as additional plots
        add_plots = [
            mpf.make_addplot(df['MA20'], color='blue', width=1),
            mpf.make_addplot(df['MA50'], color='red', width=1)
        ]

        output_path = f'outputs/mplfinance_{style}_style.png'

        mpf.plot(
            df,
            type='candle',
            volume=True,
            addplot=add_plots,
            title=f"NQ Futures - {style.title()} Style",
            style=style,
            savefig=output_path,
            figsize=(12, 8)
        )

        render_time = python_time.time() - start_time
        results[style] = render_time
        print(f"  {style} style: {render_time:.3f}s")

    return results

def test_mplfinance_performance():
    """Test mplfinance performance with larger datasets"""
    print("⚡ Testing mplfinance performance...")

    # Test with different data sizes
    sizes = [100, 500, 1000]
    results = {}

    for size in sizes:
        # Generate test data
        times = [datetime.now() - timedelta(minutes=5*i) for i in range(size)]
        times.reverse()  # Chronological order
        base_price = 21800
        data = []

        for timestamp in times:
            data.append({
                'Open': base_price + np.random.normal(0, 10),
                'High': base_price + np.random.normal(5, 5),
                'Low': base_price + np.random.normal(-5, 5),
                'Close': base_price + np.random.normal(0, 10),
                'Volume': np.random.randint(50, 500)
            })

        df = pd.DataFrame(data, index=times)

        # Time the rendering
        start_time = python_time.time()

        output_path = f'outputs/mplfinance_perf_{size}.png'
        mpf.plot(
            df,
            type='candle',
            volume=True,
            title=f'Performance Test - {size} bars',
            style='yahoo',
            savefig=output_path,
            figsize=(10, 6)
        )

        render_time = python_time.time() - start_time
        results[size] = render_time
        print(f"  {size} bars: {render_time:.3f}s")

    return results

def test_mplfinance_technical_indicators(df):
    """Test mplfinance with technical indicators"""
    print("📈 Testing built-in technical indicator support...")

    start_time = python_time.time()

    # Calculate various indicators
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['EMA_20'] = df['Close'].ewm(span=20).mean()
    df['BB_upper'] = df['SMA_20'] + (df['Close'].rolling(window=20).std() * 2)
    df['BB_lower'] = df['SMA_20'] - (df['Close'].rolling(window=20).std() * 2)

    # Create indicator plots
    add_plots = [
        mpf.make_addplot(df['SMA_20'], color='blue', width=1, label='SMA 20'),
        mpf.make_addplot(df['EMA_20'], color='orange', width=1, label='EMA 20'),
        mpf.make_addplot(df['BB_upper'], color='gray', width=0.5, alpha=0.7),
        mpf.make_addplot(df['BB_lower'], color='gray', width=0.5, alpha=0.7)
    ]

    output_path = 'outputs/mplfinance_indicators_test.png'

    mpf.plot(
        df,
        type='candle',
        volume=True,
        addplot=add_plots,
        title="NQ Futures with Technical Indicators",
        style='yahoo',
        savefig=output_path,
        figsize=(14, 10)
    )

    render_time = python_time.time() - start_time
    print(f"✅ Indicators chart saved to {output_path}")
    print(f"  Rendering time with indicators: {render_time:.3f}s")

    return {
        'indicators_supported': ['SMA', 'EMA', 'Bollinger Bands', 'Custom overlays'],
        'render_time': render_time,
        'ease_of_use': 'Excellent - built-in support'
    }

def evaluate_mplfinance_for_real_time():
    """Evaluate mplfinance suitability for real-time updates"""
    print("📡 Evaluating real-time update capabilities...")

    # mplfinance creates static images, so real-time would require:
    # 1. Recreating the entire chart each time
    # 2. Saving to file or displaying
    # 3. No built-in update mechanism

    assessment = {
        'real_time_support': 'Limited - requires full chart regeneration',
        'update_mechanism': 'None - static image generation only',
        'performance_impact': 'High - full redraw required',
        'best_use_case': 'Static reports, analysis charts, saved images',
        'real_time_recommendation': 'Not ideal for live streaming charts'
    }

    print("  Real-time assessment:")
    for key, value in assessment.items():
        print(f"    {key}: {value}")

    return assessment

def main():
    print("🧪 MPLFINANCE CANDLESTICK EVALUATION")
    print("=" * 50)

    # Test basic functionality
    df = create_sample_ohlcv_data()
    basic_results = plot_candlestick_mplfinance(df)

    # Test advanced features
    style_results = test_mplfinance_advanced_features(df)

    # Test performance
    perf_results = test_mplfinance_performance()

    # Test technical indicators
    indicator_results = test_mplfinance_technical_indicators(df)

    # Evaluate real-time capabilities
    realtime_assessment = evaluate_mplfinance_for_real_time()

    # Summary
    print("\n📊 MPLFINANCE EVALUATION SUMMARY:")
    print(f"Rendering time: {basic_results['render_time']:.3f}s")
    print(f"Complexity: {basic_results['complexity']}")
    print(f"Visual quality: {basic_results['visual_quality']}")
    print(f"Code complexity: {basic_results['code_lines']} lines for basic candlesticks")

    print("\nFeatures:")
    for feature in basic_results['features']:
        print(f"  ✓ {feature}")

    print("\nPros:")
    for pro in basic_results['pros']:
        print(f"  + {pro}")

    print("\nCons:")
    for con in basic_results['cons']:
        print(f"  - {con}")

    print("\nStyle Performance:")
    for style, time_taken in style_results.items():
        print(f"  {style}: {time_taken:.3f}s")

    print("\nPerformance Results:")
    for size, time_taken in perf_results.items():
        print(f"  {size} bars: {time_taken:.3f}s")

    print("\nTechnical Indicators:")
    print(f"  Supported: {', '.join(indicator_results['indicators_supported'])}")
    print(f"  Render time with indicators: {indicator_results['render_time']:.3f}s")
    print(f"  Ease of use: {indicator_results['ease_of_use']}")

    print("\nReal-time Suitability:")
    print(f"  Real-time support: {realtime_assessment['real_time_support']}")
    print(f"  Update mechanism: {realtime_assessment['update_mechanism']}")
    print(f"  Recommendation: {realtime_assessment['real_time_recommendation']}")

    return basic_results

if __name__ == "__main__":
    main()
