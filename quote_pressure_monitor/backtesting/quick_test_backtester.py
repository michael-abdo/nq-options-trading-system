#!/usr/bin/env python3
"""
QUICK TEST BACKTESTER
Use the exact same parameters that worked in our successful test
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def quick_backtest():
    """Run quick backtest using proven working parameters"""

    print("🚀 QUICK INSTITUTIONAL FLOW BACKTEST")
    print("=" * 60)
    print("Using PROVEN working parameters from successful test")
    print("-" * 60)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Use exact same parameters that worked
    start_time = "2025-06-17T14:30:00"
    end_time = "2025-06-17T15:00:00"  # 30 minutes of proven data
    target_date = "2025-06-17"

    # Institutional thresholds (same as working test)
    min_bid_size = 50
    min_pressure_ratio = 2.0

    print(f"📊 Analyzing: {start_time} to {end_time}")
    print(f"⚙️ Thresholds: Bid ≥{min_bid_size}, Ratio ≥{min_pressure_ratio}")

    try:
        # Get options data (exact same call that worked)
        data = client.timeseries.get_range(
            dataset="GLBX.MDP3",
            symbols=["NQ.OPT"],
            schema="mbp-1",
            start=start_time,
            end=end_time,
            stype_in="parent"
        )

        # Collect signals
        signals = []
        processed_count = 0

        for record in data:
            if hasattr(record, 'levels') and len(record.levels) > 0:
                processed_count += 1

                level = record.levels[0]
                bid_size = level.bid_sz
                ask_size = level.ask_sz

                if bid_size == 0 or ask_size == 0:
                    continue

                pressure_ratio = bid_size / ask_size

                # Apply same institutional thresholds
                if bid_size >= min_bid_size and pressure_ratio >= min_pressure_ratio:
                    signals.append({
                        'instrument_id': record.instrument_id,
                        'timestamp': record.ts_event / 1e9,
                        'bid_size': bid_size,
                        'ask_size': ask_size,
                        'pressure_ratio': pressure_ratio,
                        'bid_price': level.bid_px / 1e9,
                        'ask_price': level.ask_px / 1e9
                    })

                # Progress
                if processed_count % 100000 == 0:
                    print(f"   Processed {processed_count:,} quotes... ({len(signals)} signals)")

        print(f"\n✅ Processing complete!")
        print(f"📊 Total quotes processed: {processed_count:,}")
        print(f"🎯 Institutional signals found: {len(signals)}")

        if signals:
            print(f"\n📋 Sample signals:")
            for i, signal in enumerate(signals[:5]):
                print(f"   {i+1}. ID:{signal['instrument_id']} - {signal['bid_size']} @ ${signal['bid_price']:.2f} (ratio: {signal['pressure_ratio']:.1f})")

            # Now get NQ futures price for entry/exit simulation
            print(f"\n🔄 Getting NQ futures prices for P&L calculation...")

            nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQM5"],  # Use specific NQ contract
                schema="mbp-1",
                start=start_time,
                end=end_time
            )

            nq_prices = []
            for record in nq_data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    nq_price = (level.bid_px + level.ask_px) / 2 / 1e9
                    nq_prices.append({
                        'timestamp': record.ts_event / 1e9,
                        'price': nq_price
                    })

            if nq_prices:
                entry_price = nq_prices[0]['price']
                exit_price = nq_prices[-1]['price']

                print(f"📈 NQ Entry Price: ${entry_price:,.2f}")
                print(f"📈 NQ Exit Price: ${exit_price:,.2f}")
                print(f"💰 Raw Move: {exit_price - entry_price:+.2f} points")
                print(f"💵 Value: ${(exit_price - entry_price) * 20:+,.2f} (per contract)")

                print(f"\n🎯 BACKTESTING INSIGHT:")
                print(f"We detected {len(signals)} institutional signals")
                print(f"If we went LONG NQ at entry, P&L would be: ${(exit_price - entry_price) * 20:+,.2f}")
                print(f"Signal-to-noise ratio: {len(signals)/processed_count*100:.4f}%")

                return True
            else:
                print("❌ Could not get NQ futures prices")
                return False
        else:
            print("❌ No institutional signals detected")
            print("💡 This means either:")
            print("   - No institutional activity in this timeframe")
            print("   - Thresholds are too strict")
            print("   - Data quality issue")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = quick_backtest()

    if success:
        print("\n🎉 Quick backtest successful! Ready for full implementation.")
    else:
        print("\n🔍 Need to debug before full backtesting implementation.")
