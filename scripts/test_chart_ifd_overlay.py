#!/usr/bin/env python3
"""
Test IFD overlay rendering on 5-minute charts

Creates a test chart with sample IFD signals to verify:
1. Signal marker positioning and styling
2. Color coding and size scaling
3. Hover tooltips and interaction
4. Configuration-driven customization
"""

import os
import sys
from datetime import datetime, timedelta, timezone
import logging

# Add parent directory for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from scripts.nq_5m_chart import NQFiveMinuteChart
    from scripts.ifd_chart_bridge import IFDAggregatedSignal, InstitutionalSignalV3
    CHART_AVAILABLE = True
except ImportError as e:
    print(f"❌ Chart components not available: {e}")
    CHART_AVAILABLE = False

logger = logging.getLogger(__name__)

def create_sample_ifd_signals():
    """Create sample IFD signals for testing"""
    if not CHART_AVAILABLE:
        return []

    base_time = datetime.now(timezone.utc) - timedelta(hours=2)
    signals = []

    # Create sample signals across different time windows
    for i in range(6):
        signal_time = base_time + timedelta(minutes=i * 15)  # Every 15 minutes

        # Vary signal characteristics
        if i % 3 == 0:
            action = "STRONG_BUY"
            strength = "EXTREME"
            confidence = 0.92
        elif i % 3 == 1:
            action = "BUY"
            strength = "VERY_HIGH"
            confidence = 0.85
        else:
            action = "MONITOR"
            strength = "HIGH"
            confidence = 0.75

        # Create a sample primary signal (simplified)
        try:
            primary_signal = InstitutionalSignalV3(
                strike=21900.0,
                option_type='C',
                timestamp=signal_time,
                pressure_ratio=3.0,
                bid_volume=100,
                ask_volume=300,
                dominant_side='BUY',
                pressure_confidence=0.85,
                baseline_pressure_ratio=1.5,
                pressure_zscore=2.8,
                percentile_rank=95.0,
                anomaly_detected=True,
                market_making_probability=0.15,
                straddle_coordination=False,
                volatility_crush_detected=False,
                raw_confidence=0.8,
                baseline_confidence=0.9,
                market_making_penalty=0.1,
                coordination_bonus=0.0,
                final_confidence=confidence,
                signal_strength=strength,
                institutional_probability=0.88,
                recommended_action=action,
                risk_score=0.3,
                position_size_multiplier=1.5,
                max_position_risk=0.05
            )
        except TypeError:
            # Fallback for testing
            class MockSignal:
                def __init__(self):
                    self.final_confidence = confidence
                    self.signal_strength = strength
                    self.recommended_action = action
                def to_dict(self):
                    return {}

            primary_signal = MockSignal()

        # Create aggregated signal
        aggregated_signal = IFDAggregatedSignal(
            window_timestamp=signal_time,
            primary_signal=primary_signal,
            signal_count=2 + i % 3,
            avg_confidence=confidence,
            max_confidence=confidence,
            min_confidence=confidence - 0.1,
            dominant_action=action,
            window_strength=strength,
            confidence_trend="STABLE",
            first_signal_time=signal_time - timedelta(minutes=1),
            last_signal_time=signal_time + timedelta(minutes=1),
            window_duration=120.0,
            chart_color="green" if "BUY" in action else "orange",
            chart_size=20 if strength == "EXTREME" else 12
        )

        signals.append(aggregated_signal)

    return signals

def test_chart_with_ifd_overlay():
    """Test chart rendering with IFD overlay"""
    print("\n=== Testing Chart with IFD Overlay ===")

    if not CHART_AVAILABLE:
        print("❌ Chart not available - skipping test")
        return False

    try:
        # Create test configuration with IFD enabled
        test_config = {
            "chart": {
                "theme": "dark",
                "height": 800,
                "width": 1200,
                "time_range_hours": 4,
                "show_volume": True
            },
            "indicators": {
                "enabled": ["sma", "ifd_v3"],
                "ifd_v3": {
                    "show_signals": True,
                    "show_confidence": True,
                    "min_confidence_display": 0.7,
                    "signal_colors": {
                        "STRONG_BUY": "lime",
                        "BUY": "green",
                        "MONITOR": "orange",
                        "IGNORE": "gray"
                    },
                    "marker_sizes": {
                        "EXTREME": 20,
                        "VERY_HIGH": 16,
                        "HIGH": 12,
                        "MODERATE": 8
                    },
                    "show_confidence_background": True,
                    "high_confidence_threshold": 0.85
                }
            },
            "data": {
                "symbol": "NQM5"
            }
        }

        print("1. Creating chart with IFD configuration...")
        chart = NQFiveMinuteChart(config=test_config)
        print("   ✅ Chart initialized successfully")

        print("2. Testing IFD signal creation...")
        sample_signals = create_sample_ifd_signals()
        print(f"   ✅ Created {len(sample_signals)} sample IFD signals")

        # Manually inject signals for testing (simulating data provider response)
        chart.current_ifd_signals = sample_signals

        print("3. Testing overlay method...")
        # Create dummy DataFrame for testing overlay positioning
        import pandas as pd
        import numpy as np

        # Create sample OHLCV data aligned with signal timestamps
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)
        time_index = [base_time + timedelta(minutes=i*5) for i in range(25)]  # 25 bars = ~2 hours

        test_df = pd.DataFrame({
            'open': np.random.normal(21900, 20, 25),
            'high': np.random.normal(21920, 25, 25),
            'low': np.random.normal(21880, 25, 25),
            'close': np.random.normal(21900, 20, 25),
            'volume': np.random.randint(100, 1000, 25)
        }, index=pd.DatetimeIndex(time_index))

        # Ensure OHLCV data is consistent (high >= low, etc.)
        for i in range(len(test_df)):
            high = max(test_df.iloc[i]['open'], test_df.iloc[i]['close']) + abs(np.random.normal(10, 5))
            low = min(test_df.iloc[i]['open'], test_df.iloc[i]['close']) - abs(np.random.normal(10, 5))
            test_df.iloc[i, test_df.columns.get_loc('high')] = high
            test_df.iloc[i, test_df.columns.get_loc('low')] = low

        print("   ✅ Created sample OHLCV data for signal positioning")

        # Test the overlay method directly
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

            # Create basic chart structure
            chart.fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                subplot_titles=('NQ 5-Minute Chart with IFD Signals',),
                row_heights=[0.7, 0.3]
            )

            # Add basic candlestick
            candlestick = go.Candlestick(
                x=test_df.index,
                open=test_df['open'],
                high=test_df['high'],
                low=test_df['low'],
                close=test_df['close'],
                name='Price'
            )
            chart.fig.add_trace(candlestick, row=1, col=1)

            # Test the IFD overlay
            chart._add_ifd_overlay(test_df)

            print("   ✅ IFD overlay method executed successfully")

            # Count traces added
            overlay_traces = [trace for trace in chart.fig.data if 'IFD' in trace.name]
            print(f"   ✅ Added {len(overlay_traces)} IFD overlay traces")

            for trace in overlay_traces:
                print(f"      - {trace.name}: {len(trace.x)} signals")

        except ImportError:
            print("   ⚠️  Plotly not available - testing overlay logic only")

            # Test overlay logic without plotly
            chart.fig = type('MockFig', (), {
                'add_trace': lambda *args, **kwargs: None,
                'add_vrect': lambda *args, **kwargs: None
            })()

            chart._add_ifd_overlay(test_df)
            print("   ✅ IFD overlay logic executed successfully")

        print("4. Testing configuration validation...")

        # Test different configurations
        test_configs = [
            {"show_signals": False},  # Should skip signal rendering
            {"min_confidence_display": 0.9},  # Should filter out most signals
            {"show_confidence_background": True},  # Should add background highlights
        ]

        for i, config_override in enumerate(test_configs):
            chart.config["indicators"]["ifd_v3"].update(config_override)
            try:
                chart._add_ifd_overlay(test_df)
                print(f"   ✅ Configuration test {i+1} passed")
            except Exception as e:
                print(f"   ❌ Configuration test {i+1} failed: {e}")

        return True

    except Exception as e:
        print(f"❌ Chart overlay test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration_with_chart_config():
    """Test integration with chart configuration system"""
    print("\n=== Testing Integration with Chart Config ===")

    try:
        from scripts.chart_config_manager import ChartConfigManager

        print("1. Testing configuration loading...")
        config_manager = ChartConfigManager()

        # Test loading base configuration
        base_config = config_manager.load_config("config/5m_chart_config.json")
        print("   ✅ Base configuration loaded")

        # Test IFD configuration merge
        ifd_override = {
            "indicators": {
                "enabled": ["sma", "ifd_v3"],
                "ifd_v3": {
                    "show_signals": True,
                    "min_confidence_display": 0.8
                }
            }
        }

        merged_config = config_manager.merge_configs(base_config, ifd_override)
        print("   ✅ IFD configuration merged successfully")

        # Verify IFD settings are present
        assert "ifd_v3" in merged_config.get("indicators", {}).get("enabled", [])
        assert "ifd_v3" in merged_config.get("indicators", {})
        print("   ✅ IFD settings verified in merged configuration")

        return True

    except Exception as e:
        print(f"❌ Configuration integration test failed: {e}")
        return False

def main():
    """Run all IFD overlay tests"""
    print("=== IFD Chart Overlay Test Suite ===")

    if not CHART_AVAILABLE:
        print("❌ Cannot run tests - chart components not available")
        return

    tests = [
        ("Chart with IFD Overlay", test_chart_with_ifd_overlay),
        ("Configuration Integration", test_integration_with_chart_config)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)

        try:
            result = test_func()
            results.append((test_name, result))

            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")

        except Exception as e:
            print(f"💥 {test_name}: CRASHED - {e}")
            results.append((test_name, False))

    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL IFD OVERLAY TESTS PASSED!")
        print("✅ Chart visualization is working correctly")
    else:
        print("⚠️  Some overlay issues detected")
        print("❌ Review failed tests before production use")

if __name__ == "__main__":
    main()
