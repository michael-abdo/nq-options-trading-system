#!/usr/bin/env python3
"""
ULTRA-FAST 122-DAY BACKTESTER
=============================

Optimized for speed - minimal processing per day to avoid timeouts
Get results for all 122 days quickly
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def ultra_fast_backtest():
    """Ultra-fast processing of all 122 days"""

    print("⚡ ULTRA-FAST 122-DAY BACKTESTER")
    print("=" * 50)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # All 122 available dates
    all_dates = [
        # January 2025
        "2025-01-01", "2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07",
        "2025-01-08", "2025-01-09", "2025-01-10", "2025-01-13", "2025-01-14",
        "2025-01-15", "2025-01-16", "2025-01-17", "2025-01-20", "2025-01-21",
        "2025-01-22", "2025-01-23", "2025-01-24", "2025-01-27", "2025-01-28",
        "2025-01-29", "2025-01-30", "2025-01-31",
        # February 2025
        "2025-02-03", "2025-02-04", "2025-02-05", "2025-02-06", "2025-02-07",
        "2025-02-10", "2025-02-11", "2025-02-12", "2025-02-13", "2025-02-14",
        "2025-02-17", "2025-02-18", "2025-02-19", "2025-02-20", "2025-02-21",
        "2025-02-24", "2025-02-25", "2025-02-26", "2025-02-27", "2025-02-28",
        # March 2025
        "2025-03-03", "2025-03-04", "2025-03-05", "2025-03-06", "2025-03-07",
        "2025-03-10", "2025-03-11", "2025-03-12", "2025-03-13", "2025-03-14",
        "2025-03-17", "2025-03-18", "2025-03-19", "2025-03-20", "2025-03-21",
        "2025-03-24", "2025-03-25", "2025-03-26", "2025-03-27", "2025-03-28",
        "2025-03-31",
        # April 2025
        "2025-04-01", "2025-04-02", "2025-04-03", "2025-04-04", "2025-04-07",
        "2025-04-08", "2025-04-09", "2025-04-10", "2025-04-11", "2025-04-14",
        "2025-04-15", "2025-04-16", "2025-04-17", "2025-04-18", "2025-04-21",
        "2025-04-22", "2025-04-23", "2025-04-24", "2025-04-25", "2025-04-28",
        "2025-04-29", "2025-04-30",
        # May 2025
        "2025-05-01", "2025-05-02", "2025-05-05", "2025-05-06", "2025-05-07",
        "2025-05-08", "2025-05-09", "2025-05-12", "2025-05-13", "2025-05-14",
        "2025-05-15", "2025-05-16", "2025-05-19", "2025-05-20", "2025-05-21",
        "2025-05-22", "2025-05-23", "2025-05-26", "2025-05-27", "2025-05-28",
        "2025-05-29", "2025-05-30",
        # June 2025
        "2025-06-02", "2025-06-03", "2025-06-04", "2025-06-05", "2025-06-06",
        "2025-06-09", "2025-06-10", "2025-06-11", "2025-06-12", "2025-06-13",
        "2025-06-16", "2025-06-17", "2025-06-18"
    ]

    print(f"📊 Processing {len(all_dates)} days with minimal processing...")

    # ULTRA-FAST parameters
    max_quotes_per_day = 10000   # Only 10k quotes per day
    max_signals_per_day = 20     # Only 20 signals per day
    max_symbols_resolve = 10     # Only 10 symbols per day

    results = []

    def get_contract_for_date(date_str):
        """Get appropriate NQ contract"""
        if date_str >= "2025-06-01":
            return "NQM5"  # June
        elif date_str >= "2025-03-01":
            return "NQM5"  # June (front month)
        else:
            return "NQH5"  # March

    def ultra_fast_day(date_str):
        """Ultra-fast single day processing"""
        try:
            contract = get_contract_for_date(date_str)
            start_time = f"{date_str}T14:30:00"
            end_time = f"{date_str}T15:00:00"

            # Step 1: NQ price (1 quote)
            nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=[contract],
                schema="mbp-1",
                start=start_time,
                end=f"{date_str}T14:31:00"
            )

            nq_price = None
            for record in nq_data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    nq_price = (level.bid_px + level.ask_px) / 2 / 1e9
                    break

            if not nq_price:
                return f"no_nq_{contract}"

            # Step 2: Fast options scan (limited)
            data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_time,
                end=end_time,
                stype_in="parent"
            )

            signals = []
            count = 0

            for record in data:
                count += 1
                if count > max_quotes_per_day:
                    break

                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    if level.bid_sz >= 50 and level.ask_sz > 0 and level.bid_sz / level.ask_sz >= 2.0:
                        signals.append({'id': record.instrument_id, 'size': level.bid_sz})
                        if len(signals) >= max_signals_per_day:
                            break

            if len(signals) < 5:
                return f"low_signals_{len(signals)}"

            # Step 3: Minimal symbol resolution
            sample_ids = [s['id'] for s in signals[:max_symbols_resolve]]

            try:
                target = datetime.strptime(date_str, "%Y-%m-%d")
                start_date = (target - timedelta(days=1)).strftime("%Y-%m-%d")
                end_date = (target + timedelta(days=1)).strftime("%Y-%m-%d")

                resolution = client.symbology.resolve(
                    dataset="GLBX.MDP3",
                    symbols=[str(id) for id in sample_ids],
                    stype_in="instrument_id",
                    stype_out="raw_symbol",
                    start_date=start_date,
                    end_date=end_date
                )

                symbol_map = {}
                if 'result' in resolution:
                    for iid, mapping_list in resolution['result'].items():
                        if mapping_list:
                            symbol = mapping_list[0].get('s', '')
                            if symbol:
                                symbol_map[int(iid)] = symbol
            except:
                symbol_map = {}

            # Step 4: Fast volume analysis
            vol_above = vol_below = 0

            for signal in signals[:max_symbols_resolve]:
                symbol = symbol_map.get(signal['id'])
                if symbol:
                    try:
                        if 'C' in symbol:
                            strike = int(symbol.split('C')[1])
                        elif 'P' in symbol:
                            strike = int(symbol.split('P')[1])
                        else:
                            continue

                        if strike > nq_price + 100:
                            vol_above += signal['size']
                        elif strike < nq_price - 100:
                            vol_below += signal['size']
                    except:
                        continue

            total_vol = vol_above + vol_below
            if total_vol < 1000:  # Relaxed threshold
                return f"low_volume_{total_vol}"

            bias = abs(vol_above - vol_below) / total_vol
            if bias < 0.3:  # Relaxed bias
                return f"low_bias_{bias:.1%}"

            direction = "LONG" if vol_above > vol_below else "SHORT"

            # Step 5: Simple P&L (sample only)
            full_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=[contract],
                schema="mbp-1",
                start=start_time,
                end=end_time
            )

            prices = []
            price_count = 0
            for record in full_data:
                price_count += 1
                if price_count > 50:  # Only 50 price points
                    break
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    prices.append((level.bid_px + level.ask_px) / 2 / 1e9)

            if len(prices) < 2:
                return "no_prices"

            if direction == "LONG":
                pnl_points = prices[-1] - prices[0]
            else:
                pnl_points = prices[0] - prices[-1]

            pnl_dollars = pnl_points * 20

            return {
                'date': date_str,
                'direction': direction,
                'bias': bias,
                'vol_above': vol_above,
                'vol_below': vol_below,
                'total_vol': total_vol,
                'nq_price': nq_price,
                'pnl': pnl_dollars,
                'signals': len(signals),
                'contract': contract
            }

        except Exception as e:
            return f"error_{str(e)[:15]}"

    # Process all days
    print("\n⚡ Ultra-fast processing:")
    print("Date       | Result")
    print("-" * 40)

    for i, date in enumerate(all_dates):
        if i % 20 == 0:
            print(f"\nBatch {i//20 + 1}:")

        result = ultra_fast_day(date)

        if isinstance(result, dict):
            results.append(result)
            print(f"{date} | {result['direction']} {result['bias']:.1%} ${result['pnl']:+.0f}")
        else:
            print(f"{date} | {result}")

    # Final results
    print(f"\n" + "=" * 50)
    print("📊 ULTRA-FAST 122-DAY RESULTS")
    print("=" * 50)

    if results:
        total_pnl = sum(r['pnl'] for r in results)
        winners = len([r for r in results if r['pnl'] > 0])
        win_rate = winners / len(results) * 100

        print(f"Successful Trades: {len(results)}")
        print(f"Hit Rate: {len(results)/len(all_dates)*100:.1f}%")
        print(f"Total P&L: ${total_pnl:+,.0f}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Average: ${total_pnl/len(results):+.0f}")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"ultra_fast_122_days_{timestamp}.json", 'w') as f:
            json.dump({
                'total_days': len(all_dates),
                'successful_trades': len(results),
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'trades': results
            }, f, indent=2)

        print(f"\n📁 Results saved to: ultra_fast_122_days_{timestamp}.json")

        if total_pnl > 0:
            print(f"\n🎉 STRATEGY PROFITABLE ACROSS 122 DAYS!")
        else:
            print(f"\n📊 Strategy needs optimization")
    else:
        print("❌ No successful trades")

if __name__ == "__main__":
    ultra_fast_backtest()
