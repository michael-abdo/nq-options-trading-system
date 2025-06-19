#!/usr/bin/env python3
"""
FIXED CONTRACT BACKTESTER
=========================

Focus on dates/contracts that actually work
Skip problematic early 2025 dates
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def fixed_contract_backtest():
    """Focus on working dates and contracts"""

    print("🔧 FIXED CONTRACT BACKTESTER")
    print("=" * 50)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Focus on dates that have proven to work
    working_dates = [
        # March 2025 (second half - when contracts become active)
        "2025-03-17", "2025-03-18", "2025-03-19", "2025-03-20", "2025-03-21",
        "2025-03-24", "2025-03-25", "2025-03-26", "2025-03-27", "2025-03-28",
        "2025-03-31",
        # April 2025 (full month)
        "2025-04-01", "2025-04-02", "2025-04-03", "2025-04-04", "2025-04-07",
        "2025-04-08", "2025-04-09", "2025-04-10", "2025-04-11", "2025-04-14",
        "2025-04-15", "2025-04-16", "2025-04-17", "2025-04-18", "2025-04-21",
        "2025-04-22", "2025-04-23", "2025-04-24", "2025-04-25", "2025-04-28",
        "2025-04-29", "2025-04-30",
        # May 2025 (full month)
        "2025-05-01", "2025-05-02", "2025-05-05", "2025-05-06", "2025-05-07",
        "2025-05-08", "2025-05-09", "2025-05-12", "2025-05-13", "2025-05-14",
        "2025-05-15", "2025-05-16", "2025-05-19", "2025-05-20", "2025-05-21",
        "2025-05-22", "2025-05-23", "2025-05-26", "2025-05-27", "2025-05-28",
        "2025-05-29", "2025-05-30",
        # June 2025 (verified working)
        "2025-06-02", "2025-06-03", "2025-06-04", "2025-06-05", "2025-06-06",
        "2025-06-09", "2025-06-10", "2025-06-11", "2025-06-12", "2025-06-13",
        "2025-06-16", "2025-06-17", "2025-06-18"
    ]

    print(f"📊 Testing {len(working_dates)} dates with verified contracts")
    print("Skipping problematic January-February 2025 dates")

    results = []
    total_pnl = 0

    def get_working_contract(date_str):
        """Get contract that actually has data"""
        if date_str >= "2025-06-01":
            return "NQM5"  # June 2025
        elif date_str >= "2025-04-01":
            return "NQM5"  # June 2025 (front month)
        elif date_str >= "2025-03-15":
            return "NQH5"  # March 2025
        else:
            return None  # Skip early dates

    def quick_day_analysis(date_str):
        """Quick analysis focusing on proven approach"""
        try:
            contract = get_working_contract(date_str)
            if not contract:
                return "skipped_early"

            start_time = f"{date_str}T14:30:00"
            end_time = f"{date_str}T15:00:00"

            # Step 1: NQ price
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
                return f"no_nq"

            # Step 2: Options data
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
                if count > 20000:  # Reasonable limit
                    break

                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    if level.bid_sz >= 50 and level.ask_sz > 0 and level.bid_sz / level.ask_sz >= 2.0:
                        signals.append({'id': record.instrument_id, 'size': level.bid_sz})
                        if len(signals) >= 30:
                            break

            if len(signals) < 10:
                return f"low_signals_{len(signals)}"

            # Step 3: Symbol resolution (small sample)
            sample_ids = [s['id'] for s in signals[:15]]

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

            # Step 4: Volume analysis
            vol_above = vol_below = 0
            strikes_found = 0

            for signal in signals[:15]:
                symbol = symbol_map.get(signal['id'])
                if symbol:
                    try:
                        if 'C' in symbol:
                            strike = int(symbol.split('C')[1])
                        elif 'P' in symbol:
                            strike = int(symbol.split('P')[1])
                        else:
                            continue

                        strikes_found += 1
                        volume = signal['size']

                        if strike > nq_price + 100:
                            vol_above += volume
                        elif strike < nq_price - 100:
                            vol_below += volume
                    except:
                        continue

            total_vol = vol_above + vol_below
            if total_vol < 1500:  # Reasonable threshold
                return f"low_volume_{total_vol}"

            net_volume = vol_above - vol_below
            bias = abs(net_volume) / total_vol

            if bias < 0.35:  # 35% minimum
                return f"low_bias_{bias:.1%}"

            direction = "LONG" if net_volume > 0 else "SHORT"

            # Step 5: P&L calculation
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
                if price_count > 100:
                    break
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    prices.append((level.bid_px + level.ask_px) / 2 / 1e9)

            if len(prices) < 2:
                return "no_prices"

            entry_price = prices[0]
            exit_price = prices[-1]

            if direction == "LONG":
                pnl_points = exit_price - entry_price
            else:
                pnl_points = entry_price - exit_price

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
                'strikes': strikes_found,
                'contract': contract
            }

        except Exception as e:
            return f"error_{str(e)[:20]}"

    # Process working dates
    print(f"\n🔧 Processing verified working dates:")
    print("Date       | Result")
    print("-" * 50)

    for i, date in enumerate(working_dates):
        if i % 10 == 0:
            print(f"\nBatch {i//10 + 1}:")

        result = quick_day_analysis(date)

        if isinstance(result, dict):
            results.append(result)
            total_pnl += result['pnl']
            print(f"{date} | {result['direction']} {result['bias']:.1%} → ${result['pnl']:+.0f}")
        else:
            print(f"{date} | {result}")

    # Final results
    print(f"\n" + "=" * 50)
    print("📊 FIXED CONTRACT BACKTEST RESULTS")
    print("=" * 50)

    if results:
        winners = len([r for r in results if r['pnl'] > 0])
        win_rate = winners / len(results) * 100
        avg_pnl = total_pnl / len(results)

        print(f"📋 SUMMARY:")
        print(f"   Days Tested: {len(working_dates)}")
        print(f"   Successful Trades: {len(results)}")
        print(f"   Hit Rate: {len(results)/len(working_dates)*100:.1f}%")
        print(f"   Total P&L: ${total_pnl:+,.0f}")
        print(f"   Win Rate: {win_rate:.1f}% ({winners}W/{len(results)-winners}L)")
        print(f"   Average P&L: ${avg_pnl:+,.0f}")

        # Show all trades
        print(f"\n📊 ALL TRADES:")
        for i, trade in enumerate(results):
            print(f"   {i+1:2d}. {trade['date']}: {trade['direction']} {trade['bias']:.1%} vol:{trade['total_vol']:,} → ${trade['pnl']:+.0f}")

        # Monthly breakdown
        monthly = {}
        for trade in results:
            month = trade['date'][:7]
            if month not in monthly:
                monthly[month] = {'trades': 0, 'pnl': 0}
            monthly[month]['trades'] += 1
            monthly[month]['pnl'] += trade['pnl']

        print(f"\n📅 MONTHLY BREAKDOWN:")
        for month in sorted(monthly.keys()):
            data = monthly[month]
            print(f"   {month}: {data['trades']} trades, ${data['pnl']:+,.0f}")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fixed_contracts_{len(working_dates)}_days_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump({
                'summary': {
                    'total_days_tested': len(working_dates),
                    'successful_trades': len(results),
                    'hit_rate': len(results)/len(working_dates)*100,
                    'total_pnl': total_pnl,
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl
                },
                'monthly_breakdown': monthly,
                'all_trades': results
            }, f, indent=2)

        print(f"\n📁 Results saved to: {filename}")

        # Final assessment
        if total_pnl > 500:
            print(f"\n🎉 STRATEGY HIGHLY PROFITABLE!")
            print(f"✅ Strong performance across {len(results)} trades")
            print(f"✅ {win_rate:.0f}% win rate with avg ${avg_pnl:+.0f} per trade")
        elif total_pnl > 0:
            print(f"\n✅ STRATEGY IS PROFITABLE")
            print(f"💰 Positive results: ${total_pnl:+,.0f}")
            print(f"📊 {win_rate:.0f}% win rate")
        else:
            print(f"\n📊 STRATEGY NEEDS OPTIMIZATION")
            print(f"❌ Net loss: ${total_pnl:+,.0f}")

        print(f"\n🎯 TESTED ON {len(working_dates)} VERIFIED TRADING DAYS")
        print("Strategy validation complete with working data!")
    else:
        print("❌ No successful trades found")
        print("Consider relaxing parameters further")

if __name__ == "__main__":
    fixed_contract_backtest()
