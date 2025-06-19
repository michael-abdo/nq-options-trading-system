#!/usr/bin/env python3
"""
COMPREHENSIVE STRIKE-BASED BACKTESTER
=====================================

Run the profitable strike-based strategy on ALL available data
Expand date range to test robustness across different market conditions
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def comprehensive_strike_backtest():
    """Run comprehensive backtesting on expanded date range"""

    print("🚀 COMPREHENSIVE STRIKE-BASED BACKTESTER")
    print("=" * 70)
    print("🎯 Strategy: Follow institutional strike positioning")
    print("📅 Testing: All available data periods")
    print("-" * 70)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Expanded test range - go back further to get more data
    test_dates = []

    # Generate date range from mid-May through current
    start_date = datetime(2025, 5, 15)  # Go back to mid-May
    end_date = datetime(2025, 6, 19)    # Through today

    current = start_date
    while current <= end_date:
        # Only include weekdays (Monday = 0, Sunday = 6)
        if current.weekday() < 5:  # Monday to Friday
            test_dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    print(f"📊 Testing {len(test_dates)} trading days:")
    for i, date in enumerate(test_dates):
        if i < 10:  # Show first 10
            print(f"   • {date}")
        elif i == 10:
            print(f"   • ... and {len(test_dates)-10} more dates")
            break

    # Strategy parameters (proven working)
    min_bid_size = 50
    min_pressure_ratio = 2.0
    min_volume_bias = 0.2  # 20% directional edge required

    all_results = []
    total_pnl = 0
    total_trades = 0
    failed_dates = []
    skipped_dates = []

    # Symbol resolution cache to speed up processing
    symbol_cache = {}

    def resolve_symbols_batch(instrument_ids, target_date):
        """Resolve instrument IDs to symbols with caching"""
        if not instrument_ids:
            return {}

        # Check cache first
        cache_key = f"{target_date}_{len(instrument_ids)}"
        if cache_key in symbol_cache:
            return symbol_cache[cache_key]

        try:
            target = datetime.strptime(target_date, "%Y-%m-%d")
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
                        symbol = mapping_list[0].get('s', f'UNMAPPED_{instrument_id}')
                        symbol_map[int(instrument_id)] = symbol

            # Cache the result
            symbol_cache[cache_key] = symbol_map
            return symbol_map

        except Exception as e:
            print(f"      ⚠️  Symbol resolution error: {e}")
            return {}

    def parse_option_strike(symbol):
        """Extract strike price from option symbol"""
        try:
            if 'C' in symbol or 'P' in symbol:
                if 'C' in symbol:
                    parts = symbol.split('C')
                else:
                    parts = symbol.split('P')

                if len(parts) == 2:
                    underlying_exp = parts[0].strip()
                    strike = int(parts[1].strip())

                    if underlying_exp.startswith('NQ'):
                        return strike
        except:
            pass

        return None

    def analyze_day(date_str):
        """Analyze single day with error handling"""
        try:
            print(f"\n📊 {date_str}")

            start_time = f"{date_str}T14:30:00"
            end_time = f"{date_str}T15:00:00"

            # Step 1: Get current NQ price
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
                print("   ❌ No NQ price data")
                return None

            print(f"   💰 NQ: ${current_nq_price:,.2f}", end=" | ")

            # Step 2: Get institutional signals
            data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_time,
                end=end_time,
                stype_in="parent"
            )

            # Collect signals
            raw_signals = []
            instrument_ids = set()
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
                        raw_signals.append({
                            'instrument_id': record.instrument_id,
                            'bid_size': bid_size
                        })
                        instrument_ids.add(record.instrument_id)

            print(f"Signals: {len(raw_signals)}", end=" | ")

            if len(raw_signals) < 10:  # Need minimum signal count
                print("Insufficient signals")
                return 'skipped'

            # Step 3: Resolve symbols
            symbol_map = resolve_symbols_batch(list(instrument_ids), date_str)

            # Step 4: Analyze strikes
            volume_above = 0
            volume_below = 0

            for signal in raw_signals:
                symbol = symbol_map.get(signal['instrument_id'])
                if symbol:
                    strike = parse_option_strike(symbol)
                    if strike:
                        volume = signal['bid_size']
                        strike_diff = strike - current_nq_price

                        if strike_diff > 100:
                            volume_above += volume
                        elif strike_diff < -100:
                            volume_below += volume

            total_directional = volume_above + volume_below

            if total_directional < 1000:  # Need minimum volume
                print("Low volume")
                return 'skipped'

            net_volume = volume_above - volume_below
            volume_ratio = abs(net_volume) / total_directional

            if volume_ratio < min_volume_bias:
                print(f"No bias ({volume_ratio:.1%})")
                return 'skipped'

            # Determine direction
            direction = "LONG" if net_volume > 0 else "SHORT"
            print(f"{direction} ({volume_ratio:.1%})", end=" | ")

            # Step 5: Calculate P&L
            full_nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQM5"],
                schema="mbp-1",
                start=start_time,
                end=end_time
            )

            nq_prices = []
            for record in full_nq_data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    mid_price = (level.bid_px + level.ask_px) / 2 / 1e9
                    nq_prices.append(mid_price)

            if len(nq_prices) >= 2:
                entry_price = nq_prices[0]
                exit_price = nq_prices[-1]

                if direction == "LONG":
                    pnl_points = exit_price - entry_price
                else:
                    pnl_points = entry_price - exit_price

                pnl_dollars = pnl_points * 20

                print(f"P&L: ${pnl_dollars:+.0f}")

                return {
                    'date': date_str,
                    'direction': direction,
                    'volume_above': volume_above,
                    'volume_below': volume_below,
                    'volume_ratio': volume_ratio,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_points': pnl_points,
                    'pnl_dollars': pnl_dollars
                }
            else:
                print("No price data")
                return None

        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}")
            return None

    # Run analysis on all dates
    print(f"\n🔄 Processing {len(test_dates)} dates...")
    print("-" * 50)

    for i, date_str in enumerate(test_dates):
        if i % 5 == 0:  # Progress indicator
            print()

        result = analyze_day(date_str)

        if result == 'skipped':
            skipped_dates.append(date_str)
        elif result is None:
            failed_dates.append(date_str)
        else:
            all_results.append(result)
            total_pnl += result['pnl_dollars']
            total_trades += 1

    # Final comprehensive results
    print("\n" + "=" * 70)
    print("📊 COMPREHENSIVE STRIKE-BASED RESULTS")
    print("=" * 70)

    print(f"📅 COVERAGE:")
    print(f"   Total Days Tested: {len(test_dates)}")
    print(f"   Successful Trades: {total_trades}")
    print(f"   Skipped (Low Activity): {len(skipped_dates)}")
    print(f"   Failed (Data Issues): {len(failed_dates)}")
    print(f"   Success Rate: {total_trades/len(test_dates)*100:.1f}%")

    if total_trades > 0:
        winning_trades = len([r for r in all_results if r['pnl_dollars'] > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades * 100
        avg_pnl = total_pnl / total_trades

        winners = [r['pnl_dollars'] for r in all_results if r['pnl_dollars'] > 0]
        losers = [r['pnl_dollars'] for r in all_results if r['pnl_dollars'] <= 0]

        avg_winner = sum(winners) / len(winners) if winners else 0
        avg_loser = sum(losers) / len(losers) if losers else 0

        print(f"\n🎯 PERFORMANCE:")
        print(f"   Total P&L: ${total_pnl:+,.2f}")
        print(f"   Average P&L/Trade: ${avg_pnl:+,.2f}")
        print(f"   Win Rate: {win_rate:.1f}% ({winning_trades}W / {losing_trades}L)")
        print(f"   Average Winner: ${avg_winner:+,.2f}")
        print(f"   Average Loser: ${avg_loser:+,.2f}")
        if avg_loser != 0:
            print(f"   Profit Factor: {abs(avg_winner/avg_loser):.2f}")

        # Show best and worst days
        sorted_results = sorted(all_results, key=lambda x: x['pnl_dollars'], reverse=True)

        print(f"\n🏆 BEST DAYS:")
        for i, result in enumerate(sorted_results[:3]):
            print(f"   {i+1}. {result['date']}: {result['direction']} → ${result['pnl_dollars']:+,.2f}")

        print(f"\n📉 WORST DAYS:")
        for i, result in enumerate(sorted_results[-3:]):
            print(f"   {i+1}. {result['date']}: {result['direction']} → ${result['pnl_dollars']:+,.2f}")

        # Save comprehensive results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"comprehensive_strike_results_{timestamp}.json"

        with open(results_file, 'w') as f:
            json.dump({
                'strategy': 'comprehensive_strike_based',
                'parameters': {
                    'min_bid_size': min_bid_size,
                    'min_pressure_ratio': min_pressure_ratio,
                    'min_volume_bias': min_volume_bias
                },
                'summary': {
                    'total_days_tested': len(test_dates),
                    'successful_trades': total_trades,
                    'total_pnl': total_pnl,
                    'avg_pnl_per_trade': avg_pnl,
                    'win_rate': win_rate,
                    'avg_winner': avg_winner,
                    'avg_loser': avg_loser,
                    'profit_factor': abs(avg_winner/avg_loser) if avg_loser != 0 else None
                },
                'all_trades': all_results,
                'failed_dates': failed_dates,
                'skipped_dates': skipped_dates
            }, f, indent=2)

        print(f"\n📁 Comprehensive results saved to: {results_file}")

        # Final verdict
        if total_pnl > 0 and win_rate > 50:
            print(f"\n🎉 STRATEGY VALIDATED ACROSS ALL DATA!")
            print(f"Consistent profitability: ${total_pnl:+,.2f} across {total_trades} trades")
            print(f"This is a robust, scalable institutional flow strategy!")
        elif total_pnl > 0:
            print(f"\n✅ Strategy is profitable but needs optimization")
            print(f"Total profit: ${total_pnl:+,.2f} but win rate of {win_rate:.1f}% could be improved")
        else:
            print(f"\n📊 Strategy needs refinement")
            print(f"Loss: ${total_pnl:,.2f} suggests parameter adjustment needed")
    else:
        print("\n❌ No successful trades generated")
        print("Data availability or parameter issues")

if __name__ == "__main__":
    comprehensive_strike_backtest()
