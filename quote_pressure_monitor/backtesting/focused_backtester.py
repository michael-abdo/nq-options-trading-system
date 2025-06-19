#!/usr/bin/env python3
"""
FOCUSED BACKTESTER
==================

Run on known good dates with proven data availability
Focus on speed and core results
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def focused_backtest():
    """Run focused backtest on known good dates"""

    print("🚀 FOCUSED INSTITUTIONAL FLOW BACKTEST")
    print("=" * 60)
    print("Testing on known trading days with proven data")
    print("-" * 60)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Known good dates (weekdays with confirmed data)
    test_dates = [
        "2025-06-16",  # Monday
        "2025-06-17",  # Tuesday (proven working)
        "2025-06-18",  # Wednesday (today)
    ]

    # Strategy parameters
    min_bid_size = 50
    min_pressure_ratio = 2.0

    all_results = []
    total_pnl = 0
    total_trades = 0

    for date_str in test_dates:
        print(f"\n📊 Testing {date_str}")
        print("-" * 30)

        # Focus on one proven time window per day
        start_time = f"{date_str}T14:30:00"
        end_time = f"{date_str}T15:00:00"    # 30 min window

        try:
            # Get institutional signals (proven method)
            print("   🔍 Detecting institutional flow...")

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
            processed = 0

            for record in data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    processed += 1
                    level = record.levels[0]
                    bid_size = level.bid_sz
                    ask_size = level.ask_sz

                    if bid_size == 0 or ask_size == 0:
                        continue

                    pressure_ratio = bid_size / ask_size

                    if bid_size >= min_bid_size and pressure_ratio >= min_pressure_ratio:
                        signals.append({
                            'bid_size': bid_size,
                            'pressure_ratio': pressure_ratio
                        })

            print(f"   📈 Processed: {processed:,} quotes")
            print(f"   🎯 Signals: {len(signals)}")

            if not signals:
                print("   📭 No institutional flow")
                continue

            # Get NQ futures performance for this period
            print("   💰 Calculating P&L...")

            nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQM5"],
                schema="mbp-1",
                start=start_time,
                end=end_time
            )

            nq_prices = []
            for record in nq_data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    mid_price = (level.bid_px + level.ask_px) / 2 / 1e9
                    nq_prices.append(mid_price)

            if len(nq_prices) >= 2:
                entry_price = nq_prices[0]
                exit_price = nq_prices[-1]

                # Assume institutional flow = bullish (most signals are calls)
                # Simple strategy: if big flow detected, go LONG
                pnl_points = exit_price - entry_price
                pnl_dollars = pnl_points * 20  # NQ multiplier

                result = {
                    'date': date_str,
                    'signals': len(signals),
                    'quotes_processed': processed,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_points': pnl_points,
                    'pnl_dollars': pnl_dollars,
                    'signal_rate': len(signals) / processed * 100
                }

                all_results.append(result)
                total_pnl += pnl_dollars
                total_trades += 1

                print(f"   📈 Entry: ${entry_price:.2f}")
                print(f"   📈 Exit: ${exit_price:.2f}")
                print(f"   💰 P&L: {pnl_points:+.2f} pts = ${pnl_dollars:+,.2f}")
                print(f"   🎯 Signal Rate: {len(signals)/processed*100:.3f}%")

            else:
                print("   ⚠️  Insufficient NQ price data")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue

    # Final results
    print("\n" + "=" * 60)
    print("📊 FOCUSED BACKTEST RESULTS")
    print("=" * 60)

    if all_results:
        avg_pnl = total_pnl / len(all_results)
        winning_days = len([r for r in all_results if r['pnl_dollars'] > 0])
        win_rate = winning_days / len(all_results) * 100

        total_signals = sum(r['signals'] for r in all_results)
        total_processed = sum(r['quotes_processed'] for r in all_results)

        print(f"🎯 PERFORMANCE:")
        print(f"   Days Tested: {len(all_results)}")
        print(f"   Total P&L: ${total_pnl:+,.2f}")
        print(f"   Average P&L/Day: ${avg_pnl:+,.2f}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Total Signals: {total_signals:,}")
        print(f"   Total Quotes: {total_processed:,}")
        print(f"   Overall Signal Rate: {total_signals/total_processed*100:.3f}%")

        print(f"\n📅 DAILY BREAKDOWN:")
        for result in all_results:
            print(f"   {result['date']}: {result['signals']:,} signals → ${result['pnl_dollars']:+.2f}")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"focused_backtest_{timestamp}.json"

        with open(results_file, 'w') as f:
            json.dump({
                'summary': {
                    'days_tested': len(all_results),
                    'total_pnl': total_pnl,
                    'avg_pnl_per_day': avg_pnl,
                    'win_rate': win_rate,
                    'total_signals': total_signals,
                    'signal_rate': total_signals/total_processed*100
                },
                'daily_results': all_results
            }, f, indent=2)

        print(f"\n📁 Results saved to: {results_file}")

        # Strategy verdict
        if total_pnl > 0:
            print(f"\n🎉 STRATEGY SHOWS PROMISE!")
            print(f"Following institutional flow generated ${total_pnl:+,.2f} over {len(all_results)} days")
            print(f"Average daily return: ${avg_pnl:+.2f}")
        else:
            print(f"\n📉 Strategy shows loss: ${total_pnl:,.2f}")
            print("May need parameter tuning or different approach")
    else:
        print("❌ No valid results generated")

if __name__ == "__main__":
    focused_backtest()
