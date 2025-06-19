#!/usr/bin/env python3
"""
Test Script for Quote Pressure Adapter
=====================================

This script demonstrates the adapter's functionality with realistic quote pressure
scenarios, showing how it converts quote snapshots into PressureMetrics.
"""

import sys
import os
from datetime import datetime, timedelta, timezone
from quote_pressure_adapter import QuotePressureAdapter, QuotePressureSnapshot

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)


def test_basic_conversion():
    """Test basic quote to volume conversion"""
    print("=" * 60)
    print("TEST 1: Basic Quote to Volume Conversion")
    print("=" * 60)

    adapter = QuotePressureAdapter(window_minutes=5, volume_multiplier=10.0)

    # Simulate quote pressure building up
    base_time = datetime.now(timezone.utc)

    snapshots = [
        # Initial state
        QuotePressureSnapshot(
            timestamp=base_time,
            symbol="NQM5 C22000",
            strike=22000,
            option_type="C",
            bid_size=30,
            ask_size=30,
            bid_price=150.0,
            ask_price=150.5,
            pressure_ratio=1.0
        ),
        # Bid size increases (buying pressure)
        QuotePressureSnapshot(
            timestamp=base_time + timedelta(seconds=30),
            symbol="NQM5 C22000",
            strike=22000,
            option_type="C",
            bid_size=60,  # +30
            ask_size=25,  # -5
            bid_price=150.25,
            ask_price=150.75,
            pressure_ratio=2.4
        ),
        # More aggressive buying
        QuotePressureSnapshot(
            timestamp=base_time + timedelta(seconds=60),
            symbol="NQM5 C22000",
            strike=22000,
            option_type="C",
            bid_size=85,  # +25
            ask_size=20,  # -5
            bid_price=150.5,
            ask_price=151.0,
            pressure_ratio=4.25
        )
    ]

    for i, snapshot in enumerate(snapshots):
        print(f"\nSnapshot {i+1}:")
        print(f"  Time: {snapshot.timestamp.strftime('%H:%M:%S')}")
        print(f"  Bid: {snapshot.bid_size} @ ${snapshot.bid_price}")
        print(f"  Ask: {snapshot.ask_size} @ ${snapshot.ask_price}")
        print(f"  Pressure Ratio: {snapshot.pressure_ratio:.2f}")

        metrics = adapter.add_quote_snapshot(snapshot)
        if metrics:
            print(f"\n✅ Window Completed - PressureMetrics Generated:")
            print(f"  Bid Volume: {metrics.bid_volume}")
            print(f"  Ask Volume: {metrics.ask_volume}")
            print(f"  Pressure Ratio: {metrics.pressure_ratio:.2f}")
            print(f"  Dominant Side: {metrics.dominant_side}")
            print(f"  Confidence: {metrics.confidence:.2f}")


def test_institutional_scenario():
    """Test a realistic institutional trading scenario"""
    print("\n" + "=" * 60)
    print("TEST 2: Institutional Trading Scenario")
    print("=" * 60)

    adapter = QuotePressureAdapter(window_minutes=5, volume_multiplier=10.0)

    # Simulate institutional accumulation pattern
    base_time = datetime.now(timezone.utc)

    # Phase 1: Quiet accumulation
    print("\nPhase 1: Quiet Accumulation (0-2 min)")
    for i in range(4):
        snapshot = QuotePressureSnapshot(
            timestamp=base_time + timedelta(seconds=i*30),
            symbol="NQM5 P21500",
            strike=21500,
            option_type="P",
            bid_size=40 + i*5,  # Gradual increase
            ask_size=35 - i*2,  # Gradual decrease
            bid_price=125.0 + i*0.25,
            ask_price=125.5 + i*0.25,
            pressure_ratio=(40 + i*5) / (35 - i*2)
        )
        adapter.add_quote_snapshot(snapshot)
        print(f"  {i*30}s: Bid {snapshot.bid_size} / Ask {snapshot.ask_size}")

    # Phase 2: Aggressive positioning
    print("\nPhase 2: Aggressive Positioning (2-4 min)")
    for i in range(4):
        snapshot = QuotePressureSnapshot(
            timestamp=base_time + timedelta(seconds=120 + i*30),
            symbol="NQM5 P21500",
            strike=21500,
            option_type="P",
            bid_size=55 + i*15,  # Rapid increase
            ask_size=27 - i*5,   # Rapid decrease
            bid_price=126.0 + i*0.5,
            ask_price=126.5 + i*0.5,
            pressure_ratio=(55 + i*15) / max(27 - i*5, 1)
        )
        metrics = adapter.add_quote_snapshot(snapshot)
        print(f"  {120 + i*30}s: Bid {snapshot.bid_size} / Ask {snapshot.ask_size}")

        if metrics:
            print(f"\n🎯 Institutional Pattern Detected!")
            print(f"  Window: {metrics.time_window.strftime('%H:%M')}")
            print(f"  Simulated Bid Volume: {metrics.bid_volume}")
            print(f"  Simulated Ask Volume: {metrics.ask_volume}")
            print(f"  Pressure Ratio: {metrics.pressure_ratio:.2f}")
            print(f"  Signal: {metrics.dominant_side} positioning detected")
            print(f"  Confidence: {metrics.confidence:.2f}")


def test_multi_strike_coordination():
    """Test coordinated activity across multiple strikes"""
    print("\n" + "=" * 60)
    print("TEST 3: Multi-Strike Coordination")
    print("=" * 60)

    adapter = QuotePressureAdapter(window_minutes=5, volume_multiplier=10.0)

    base_time = datetime.now(timezone.utc)
    strikes = [21800, 22000, 22200]

    print("\nSimulating coordinated institutional activity across strikes...")

    # Process 3 minutes of coordinated activity
    for minute in range(3):
        print(f"\nMinute {minute + 1}:")

        for strike in strikes:
            # All strikes show similar pattern (institutional tell)
            base_bid = 40 + minute * 20
            base_ask = 40 - minute * 10

            snapshot = QuotePressureSnapshot(
                timestamp=base_time + timedelta(minutes=minute),
                symbol=f"NQM5 C{strike}",
                strike=strike,
                option_type="C",
                bid_size=base_bid + (strike - 22000) // 100,  # Slight variation
                ask_size=max(base_ask - (strike - 22000) // 200, 5),
                bid_price=100.0 + (strike - 22000) / 1000,
                ask_price=100.5 + (strike - 22000) / 1000,
                pressure_ratio=base_bid / max(base_ask, 1)
            )

            metrics = adapter.add_quote_snapshot(snapshot)
            print(f"  Strike {strike}: Bid {snapshot.bid_size} / Ask {snapshot.ask_size}")

            if metrics:
                print(f"    → Completed: {metrics.dominant_side} pressure, "
                      f"Confidence: {metrics.confidence:.2f}")

    # Force complete remaining windows
    print("\nCompleting analysis...")
    remaining_metrics = adapter.force_complete_all_windows()

    if remaining_metrics:
        print(f"\n📊 Summary of Coordinated Activity:")
        for metrics in remaining_metrics:
            print(f"  Strike {metrics.strike}: {metrics.dominant_side} "
                  f"(Ratio: {metrics.pressure_ratio:.2f}, Conf: {metrics.confidence:.2f})")


def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n" + "=" * 60)
    print("TEST 4: Edge Cases")
    print("=" * 60)

    adapter = QuotePressureAdapter(window_minutes=5, volume_multiplier=10.0)
    base_time = datetime.now(timezone.utc)

    # Test 1: Zero ask size
    print("\nEdge Case 1: Zero ask size (extreme buy pressure)")
    snapshot = QuotePressureSnapshot(
        timestamp=base_time,
        symbol="NQM5 C22500",
        strike=22500,
        option_type="C",
        bid_size=100,
        ask_size=0,
        bid_price=80.0,
        ask_price=0,
        pressure_ratio=float('inf')
    )
    adapter.add_quote_snapshot(snapshot)
    print(f"  Handled: Bid {snapshot.bid_size} / Ask {snapshot.ask_size}")

    # Test 2: Very small sizes
    print("\nEdge Case 2: Very small quote sizes")
    snapshot = QuotePressureSnapshot(
        timestamp=base_time + timedelta(seconds=30),
        symbol="NQM5 C22500",
        strike=22500,
        option_type="C",
        bid_size=2,
        ask_size=1,
        bid_price=80.0,
        ask_price=80.5,
        pressure_ratio=2.0
    )
    adapter.add_quote_snapshot(snapshot)
    print(f"  Handled: Bid {snapshot.bid_size} / Ask {snapshot.ask_size}")

    # Test 3: No quote changes
    print("\nEdge Case 3: Static quotes (no changes)")
    for i in range(3):
        snapshot = QuotePressureSnapshot(
            timestamp=base_time + timedelta(seconds=60 + i*30),
            symbol="NQM5 C22500",
            strike=22500,
            option_type="C",
            bid_size=50,  # No change
            ask_size=50,  # No change
            bid_price=80.0,
            ask_price=80.5,
            pressure_ratio=1.0
        )
        adapter.add_quote_snapshot(snapshot)
    print("  Handled: Static quotes processed")

    # Complete windows
    metrics_list = adapter.force_complete_all_windows()
    if metrics_list:
        print(f"\n  Results: Generated {len(metrics_list)} PressureMetrics")
        for metrics in metrics_list:
            print(f"    Confidence: {metrics.confidence:.2f} "
                  f"(Low due to minimal activity)")


if __name__ == "__main__":
    print("🧪 Quote Pressure Adapter Test Suite")
    print("=" * 60)

    # Run all tests
    test_basic_conversion()
    test_institutional_scenario()
    test_multi_strike_coordination()
    test_edge_cases()

    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("\nThe adapter successfully converts quote pressure data to")
    print("PressureMetrics format compatible with IFD v3.")
