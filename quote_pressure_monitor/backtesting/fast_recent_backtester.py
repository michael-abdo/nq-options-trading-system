#!/usr/bin/env python3
"""
FAST RECENT BACKTESTER
======================

Quick test on recent data with reduced processing limits
Get results fast to see strategy performance
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def fast_recent_backtest():
    """Fast test on recent data with reduced processing"""

    print("⚡ FAST RECENT BACKTESTER")
    print("=" * 50)
    print("Quick test with reduced processing limits")
    print("-" * 50)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Recent dates with good data
    recent_dates = [
        "2025-06-02", "2025-06-03", "2025-06-04", "2025-06-05", "2025-06-06",
        "2025-06-09", "2025-06-10", "2025-06-11", "2025-06-12", "2025-06-13",
        "2025-06-16", "2025-06-17", "2025-06-18"
    ]

    # Optimized parameters
    min_bid_size = 50
    min_pressure_ratio = 2.0
    min_volume_bias = 0.40  # 40% minimum
    min_total_volume = 2000

    results = []
    total_pnl = 0

    def analyze_day_fast(date_str):
        """Fast single day analysis"""
        try:
            print(f"\n📅 {date_str}: ", end="", flush=True)

            start_time = f"{date_str}T14:30:00"
            end_time = f"{date_str}T15:00:00"

            # Get NQ price
            nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQM5"],
                schema="mbp-1",
                start=start_time,
                end=f"{date_str}T14:31:00"
            )

            current_nq_price = None
            for record in nq_data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    current_nq_price = (level.bid_px + level.ask_px) / 2 / 1e9
                    break

            if not current_nq_price:
                print("❌ No NQ")
                return None

            print(f"${current_nq_price:,.0f}", end=" | ")

            # Get options data (limited)
            data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_time,
                end=end_time,
                stype_in="parent"
            )

            # Collect signals (fast)
            signals = []
            processed = 0

            for record in data:
                processed += 1
                if processed > 100000:  # 100k limit for speed
                    break

                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    bid_size = level.bid_sz
                    ask_size = level.ask_sz

                    if (bid_size >= min_bid_size and ask_size > 0 and
                        bid_size / ask_size >= min_pressure_ratio):
                        signals.append({'id': record.instrument_id, 'size': bid_size})

                        if len(signals) >= 100:  # 100 signal limit
                            break

            print(f"{len(signals)} sigs", end=" | ")

            if len(signals) < 10:
                print("❌ Low sigs")
                return None

            # Fast symbol resolution (sample)
            instrument_ids = list(set([s['id'] for s in signals[:50]]))  # Sample

            try:
                target = datetime.strptime(date_str, "%Y-%m-%d")
                start_date = (target - timedelta(days=1)).strftime("%Y-%m-%d")
                end_date = (target + timedelta(days=1)).strftime("%Y-%m-%d")

                resolution_result = client.symbology.resolve(
                    dataset="GLBX.MDP3",
                    symbols=[str(id) for id in instrument_ids],
                    stype_in="instrument_id",
                    stype_out="raw_symbol",
                    start_date=start_date,
                    end_date=end_date
                )

                symbol_map = {}
                if 'result' in resolution_result:
                    for instrument_id, mapping_list in resolution_result['result'].items():
                        if mapping_list:
                            symbol = mapping_list[0].get('s', '')
                            if symbol:
                                symbol_map[int(instrument_id)] = symbol
            except:
                symbol_map = {}

            # Strike analysis
            volume_above = 0
            volume_below = 0

            for signal in signals[:50]:  # Sample only
                symbol = symbol_map.get(signal['id'])
                if symbol:
                    try:
                        if 'C' in symbol:
                            strike = int(symbol.split('C')[1].strip())
                        elif 'P' in symbol:
                            strike = int(symbol.split('P')[1].strip())
                        else:
                            continue

                        volume = signal['size']
                        if strike > current_nq_price + 100:
                            volume_above += volume
                        elif strike < current_nq_price - 100:
                            volume_below += volume
                    except:
                        continue

            total_directional = volume_above + volume_below

            if total_directional < min_total_volume:
                print(f"❌ Vol {total_directional}")
                return None

            net_volume = volume_above - volume_below
            volume_bias = abs(net_volume) / total_directional

            if volume_bias < min_volume_bias:
                print(f"❌ Bias {volume_bias:.1%}")
                return None

            direction = "LONG" if net_volume > 0 else "SHORT"
            print(f"{direction} {volume_bias:.1%}", end=" | ")

            # P&L calculation
            full_nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQM5"],
                schema="mbp-1",
                start=start_time,
                end=end_time
            )

            prices = []
            count = 0
            for record in full_nq_data:
                count += 1
                if count > 200:  # Fast sample
                    break
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    prices.append((level.bid_px + level.ask_px) / 2 / 1e9)

            if len(prices) < 2:
                print("❌ No prices")
                return None

            entry_price = prices[0]
            exit_price = prices[-1]

            if direction == "LONG":
                pnl_points = exit_price - entry_price
            else:
                pnl_points = entry_price - exit_price

            pnl_dollars = pnl_points * 20

            print(f"${pnl_dollars:+,.0f}")

            return {
                'date': date_str,
                'direction': direction,
                'volume_bias': volume_bias,
                'volume_above': volume_above,
                'volume_below': volume_below,
                'pnl_dollars': pnl_dollars,
                'pnl_points': pnl_points
            }

        except Exception as e:
            print(f"❌ {str(e)[:20]}")
            return None

    # Run fast analysis
    print("\n⚡ Fast processing...")

    for date_str in recent_dates:
        result = analyze_day_fast(date_str)
        if result:
            results.append(result)
            total_pnl += result['pnl_dollars']

    # Results
    print("\n" + "=" * 50)
    print("📊 FAST BACKTEST RESULTS")
    print("=" * 50)

    if results:
        winning_trades = len([r for r in results if r['pnl_dollars'] > 0])
        win_rate = winning_trades / len(results) * 100
        avg_pnl = total_pnl / len(results)

        print(f"📋 SUMMARY:")
        print(f"   Days Tested: {len(recent_dates)}")
        print(f"   Successful Trades: {len(results)}")
        print(f"   Hit Rate: {len(results)/len(recent_dates)*100:.1f}%")
        print(f"   Total P&L: ${total_pnl:+,.2f}")
        print(f"   Win Rate: {win_rate:.1f}% ({winning_trades}W/{len(results)-winning_trades}L)")
        print(f"   Average P&L: ${avg_pnl:+,.2f}")

        print(f"\n📊 ALL TRADES:")
        for i, trade in enumerate(results):
            print(f"   {i+1}. {trade['date']}: {trade['direction']} {trade['volume_bias']:.1%} → ${trade['pnl_dollars']:+,.0f}")

        # Assessment
        if total_pnl > 0:
            print(f"\n🎉 STRATEGY IS PROFITABLE!")
            print(f"✅ Consistent {win_rate:.0f}% win rate")
            print(f"✅ Average ${avg_pnl:+,.0f} per trade")
            print(f"🚀 Ready for full validation!")
        else:
            print(f"\n📊 Strategy needs refinement")
    else:
        print("❌ No successful trades")

if __name__ == "__main__":
    fast_recent_backtest()
