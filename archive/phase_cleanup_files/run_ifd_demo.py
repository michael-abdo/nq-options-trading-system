#!/usr/bin/env python3
"""
IFD Demo Analysis - Show Institutional Flow Detection with test data
"""

import sys
import os
from datetime import datetime

# Add task system to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tasks', 'options_trading_system'))

def run_ifd_demo():
    """Demonstrate IFD analysis with realistic test data"""

    print("🎯 IFD Demo Analysis - Institutional Flow Detection")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        from analysis_engine.volume_spike_dead_simple.solution import DeadSimpleVolumeSpike
        print("✅ Dead Simple Volume Spike (IFD v1.0) - Available")
    except ImportError as e:
        print(f"❌ Dead Simple Volume Spike - Import Error: {e}")
        return

    print()
    print("📊 Creating Realistic Test Data...")
    print("-" * 40)

    # Create realistic options data that should trigger institutional signals
    current_nq_price = 21050.0
    print(f"Current NQ Price: ${current_nq_price:,.2f}")

    # Create options chain with various scenarios (using correct field names)
    options_chain = [
        # Scenario 1: High volume call buying (institutional bullish)
        {
            'strike': 21100.0,
            'optionType': 'CALL',
            'volume': 2500,       # High volume
            'openInterest': 150,  # Low OI = Vol/OI ratio of 16.67 (> 10)
            'lastPrice': 125.0,
            'expiration': '2025-06-20'
        },

        # Scenario 2: Massive put buying (institutional bearish)
        {
            'strike': 21000.0,
            'optionType': 'PUT',
            'volume': 3000,       # Very high volume
            'openInterest': 200,  # Vol/OI ratio of 15 (> 10)
            'lastPrice': 110.0,
            'expiration': '2025-06-20'
        },

        # Scenario 3: Normal volume (should not trigger)
        {
            'strike': 21200.0,
            'optionType': 'CALL',
            'volume': 100,        # Normal volume
            'openInterest': 500,  # Vol/OI ratio of 0.2 (< 10)
            'lastPrice': 80.0,
            'expiration': '2025-06-20'
        },

        # Scenario 4: High dollar value put position
        {
            'strike': 20950.0,
            'optionType': 'PUT',
            'volume': 1800,       # High volume
            'openInterest': 120,  # Vol/OI ratio of 15 (> 10)
            'lastPrice': 90.0,   # High dollar value
            'expiration': '2025-06-20'
        },

        # Scenario 5: Extreme volume spike
        {
            'strike': 21150.0,
            'optionType': 'CALL',
            'volume': 5000,       # Extreme volume
            'openInterest': 100,  # Vol/OI ratio of 50 (extreme)
            'lastPrice': 75.0,
            'expiration': '2025-06-20'
        }
    ]

    print(f"Options Chain: {len(options_chain)} contracts")
    for i, opt in enumerate(options_chain, 1):
        vol_oi = opt['volume'] / opt['openInterest'] if opt['openInterest'] > 0 else 0
        dollar_size = opt['volume'] * opt['lastPrice'] * 20  # $20 per point
        print(f"  {i}. {opt['strike']:.0f} {opt['optionType']}: "
              f"Vol={opt['volume']}, OI={opt['openInterest']}, "
              f"Vol/OI={vol_oi:.1f}, ${dollar_size:,.0f}")

    print()
    print("🧮 Running IFD Analysis...")
    print("-" * 30)

    # Run Dead Simple Volume Spike analysis
    analyzer = DeadSimpleVolumeSpike()

    try:
        signals = analyzer.find_institutional_flow(options_chain, current_nq_price)

        print(f"\n🎯 Analysis Complete!")
        print(f"   ✅ {len(signals)} institutional signals detected")

        if signals:
            print("\n📋 Institutional Flow Signals:")
            print("=" * 50)

            for i, signal in enumerate(signals, 1):
                print(f"\n🔹 Signal #{i}")
                print(f"   Strike: ${signal.strike:,.0f} {signal.option_type}")
                print(f"   Direction: {signal.direction}")
                print(f"   Confidence: {signal.confidence}")
                print(f"   Volume: {signal.volume:,}")
                print(f"   Open Interest: {signal.open_interest:,}")
                print(f"   Vol/OI Ratio: {signal.vol_oi_ratio:.1f}")
                print(f"   Dollar Size: ${signal.dollar_size:,.0f}")
                print(f"   Target Price: ${signal.target_price:,.0f}")
                print(f"   Option Price: ${signal.option_price:.2f}")
        else:
            print("\n   ℹ️  No institutional signals met criteria")
            print("      (Vol/OI > 10, Volume > 500, Dollar Size > $100K)")

        # Show analysis criteria
        print(f"\n📊 Analysis Criteria (Dead Simple Strategy):")
        print(f"   • Minimum Vol/OI Ratio: {analyzer.MIN_VOL_OI_RATIO}")
        print(f"   • Minimum Volume: {analyzer.MIN_VOLUME}")
        print(f"   • Minimum Dollar Size: ${analyzer.MIN_DOLLAR_SIZE:,.0f}")
        print(f"   • Contract Multiplier: ${analyzer.CONTRACT_MULTIPLIER}")

        # Show strategy logic
        print(f"\n🎯 Strategy Logic:")
        print(f"   • Find abnormal volume (Vol/OI > {analyzer.MIN_VOL_OI_RATIO})")
        print(f"   • Verify institutional size (${analyzer.MIN_DOLLAR_SIZE:,.0f}+ positions)")
        print(f"   • Follow the direction (Calls = LONG, Puts = SHORT)")
        print(f"   • Target: Price hits strike level")

        # Save results
        output_file = f"outputs/ifd_demo_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("outputs", exist_ok=True)

        import json
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'analysis_type': 'ifd_demo',
            'current_price': current_nq_price,
            'options_chain': options_chain,
            'signals': [signal.to_dict() for signal in signals],
            'criteria': {
                'min_vol_oi_ratio': analyzer.MIN_VOL_OI_RATIO,
                'min_volume': analyzer.MIN_VOLUME,
                'min_dollar_size': analyzer.MIN_DOLLAR_SIZE,
                'contract_multiplier': analyzer.CONTRACT_MULTIPLIER
            }
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)

        print(f"\n💾 Results saved: {output_file}")

        return signals

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    try:
        signals = run_ifd_demo()
        print(f"\n🎯 Demo Complete: {len(signals)} signals detected")
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n💥 Demo failed: {e}")
        import traceback
        traceback.print_exc()
