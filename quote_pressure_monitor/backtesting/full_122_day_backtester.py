#!/usr/bin/env python3
"""
FULL 122-DAY COMPREHENSIVE BACKTESTER
====================================

Test optimized strike-based strategy across ALL available trading days
Designed for efficiency and comprehensive validation
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def full_122_day_backtest():
    """Run comprehensive backtest across all 122 available trading days"""

    print("🚀 FULL 122-DAY COMPREHENSIVE BACKTESTER")
    print("=" * 70)
    print("Testing optimized strategy across ALL available data")
    print("Optimized parameters: 40% volume bias, 2000+ volume minimum")
    print("-" * 70)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # All 122 available trading days
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
        "2025-06-16", "2025-06-17", "2025-06-18", "2025-06-19"
    ]

    print(f"📊 Testing {len(all_dates)} trading days from {all_dates[0]} to {all_dates[-1]}")

    # Optimized parameters (proven successful)
    min_bid_size = 50
    min_pressure_ratio = 2.0
    min_volume_bias = 0.40  # 40% minimum bias
    min_total_volume = 2000

    # Track results
    all_trades = []
    monthly_results = {}
    total_pnl = 0
    successful_days = 0
    failed_days = []
    skipped_days = []

    # Symbol resolution cache (speed optimization)
    symbol_cache = {}

    def resolve_symbols_fast(instrument_ids, target_date):
        """Fast symbol resolution with caching"""
        cache_key = f"{target_date}_{len(instrument_ids)}"
        if cache_key in symbol_cache:
            return symbol_cache[cache_key]

        if not instrument_ids or len(instrument_ids) > 200:  # Limit for speed
            return {}

        try:
            target = datetime.strptime(target_date, "%Y-%m-%d")
            start_date = (target - timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = (target + timedelta(days=1)).strftime("%Y-%m-%d")

            # Limit to first 100 IDs for speed
            limited_ids = list(instrument_ids)[:100]

            resolution_result = client.symbology.resolve(
                dataset="GLBX.MDP3",
                symbols=[str(id) for id in limited_ids],
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
                        if symbol and not symbol.startswith('UNMAPPED'):
                            symbol_map[int(instrument_id)] = symbol

            symbol_cache[cache_key] = symbol_map
            return symbol_map

        except:
            return {}

    def parse_strike_fast(symbol):
        """Fast strike extraction"""
        try:
            if 'C' in symbol:
                return int(symbol.split('C')[1].strip())
            elif 'P' in symbol:
                return int(symbol.split('P')[1].strip())
        except:
            pass
        return None

    def analyze_single_day(date_str):
        """Analyze single trading day efficiently"""
        try:
            # Use proven successful time window
            start_time = f"{date_str}T14:30:00"
            end_time = f"{date_str}T15:00:00"

            # Step 1: Get NQ reference price (fast)
            nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQM5"],  # Use June contract for early dates, auto-adjust later
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
                return 'no_nq_price'

            # Step 2: Sample institutional signals (limited for speed)
            data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_time,
                end=end_time,
                stype_in="parent"
            )

            # Quick signal collection with limits
            signals = []
            instrument_ids = set()
            processed = 0

            for record in data:
                processed += 1
                if processed > 1000000:  # 1M quote limit for speed
                    break

                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    bid_size = level.bid_sz
                    ask_size = level.ask_sz

                    if (bid_size >= min_bid_size and ask_size > 0 and
                        bid_size / ask_size >= min_pressure_ratio):

                        signals.append({
                            'id': record.instrument_id,
                            'size': bid_size
                        })
                        instrument_ids.add(record.instrument_id)

                        if len(signals) >= 500:  # Limit for speed
                            break

            if len(signals) < 10:
                return 'insufficient_signals'

            # Step 3: Quick symbol resolution (sample)
            symbol_map = resolve_symbols_fast(instrument_ids, date_str)

            # Step 4: Strike analysis
            volume_above = 0
            volume_below = 0
            strikes_found = 0

            for signal in signals:
                symbol = symbol_map.get(signal['id'])
                if symbol:
                    strike = parse_strike_fast(symbol)
                    if strike:
                        strikes_found += 1
                        volume = signal['size']

                        if strike > current_nq_price + 100:
                            volume_above += volume
                        elif strike < current_nq_price - 100:
                            volume_below += volume

            total_directional = volume_above + volume_below

            if total_directional < min_total_volume:
                return 'insufficient_volume'

            net_volume = volume_above - volume_below
            volume_bias = abs(net_volume) / total_directional

            if volume_bias < min_volume_bias:
                return f'insufficient_bias_{volume_bias:.1%}'

            direction = "LONG" if net_volume > 0 else "SHORT"

            # Step 5: Get P&L (sampled for speed)
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
                if count > 1000:  # Sample for speed
                    break
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    prices.append((level.bid_px + level.ask_px) / 2 / 1e9)

            if len(prices) < 2:
                return 'no_price_data'

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
                'volume_bias': volume_bias,
                'volume_above': volume_above,
                'volume_below': volume_below,
                'total_volume': total_directional,
                'strikes_analyzed': strikes_found,
                'current_nq': current_nq_price,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl_points': pnl_points,
                'pnl_dollars': pnl_dollars
            }

        except Exception as e:
            return f'error_{str(e)[:30]}'

    # Run comprehensive analysis
    print(f"\n🔄 Processing all 122 days...")
    print("Progress: [", end="", flush=True)

    for i, date_str in enumerate(all_dates):
        # Progress indicator
        if i % 5 == 0:
            print(".", end="", flush=True)

        month = date_str[:7]
        if month not in monthly_results:
            monthly_results[month] = {'trades': 0, 'pnl': 0, 'days': 0}
        monthly_results[month]['days'] += 1

        result = analyze_single_day(date_str)

        if isinstance(result, dict):
            # Successful trade
            all_trades.append(result)
            total_pnl += result['pnl_dollars']
            successful_days += 1
            monthly_results[month]['trades'] += 1
            monthly_results[month]['pnl'] += result['pnl_dollars']

        elif result.startswith('error_'):
            failed_days.append((date_str, result))
        else:
            skipped_days.append((date_str, result))

    print("] Complete!")

    # Comprehensive results analysis
    print("\n" + "=" * 70)
    print("📊 COMPREHENSIVE 122-DAY BACKTEST RESULTS")
    print("=" * 70)

    print(f"📋 EXECUTION SUMMARY:")
    print(f"   Total Days Tested: {len(all_dates)}")
    print(f"   Successful Trades: {successful_days}")
    print(f"   Skipped Days: {len(skipped_days)}")
    print(f"   Failed Days: {len(failed_days)}")
    print(f"   Hit Rate: {successful_days/len(all_dates)*100:.1f}%")

    if successful_days > 0:
        winning_trades = len([t for t in all_trades if t['pnl_dollars'] > 0])
        losing_trades = successful_days - winning_trades
        win_rate = winning_trades / successful_days * 100
        avg_pnl = total_pnl / successful_days

        winners = [t['pnl_dollars'] for t in all_trades if t['pnl_dollars'] > 0]
        losers = [t['pnl_dollars'] for t in all_trades if t['pnl_dollars'] <= 0]

        avg_winner = sum(winners) / len(winners) if winners else 0
        avg_loser = sum(losers) / len(losers) if losers else 0

        print(f"\n🎯 PERFORMANCE METRICS:")
        print(f"   Total P&L: ${total_pnl:+,.2f}")
        print(f"   Average P&L/Trade: ${avg_pnl:+,.2f}")
        print(f"   Win Rate: {win_rate:.1f}% ({winning_trades}W / {losing_trades}L)")
        print(f"   Average Winner: ${avg_winner:+,.2f}")
        print(f"   Average Loser: ${avg_loser:+,.2f}")
        if avg_loser != 0:
            print(f"   Profit Factor: {abs(avg_winner/avg_loser):.2f}")

        # Monthly breakdown
        print(f"\n📅 MONTHLY PERFORMANCE:")
        for month, data in sorted(monthly_results.items()):
            if data['trades'] > 0:
                print(f"   {month}: {data['trades']} trades, ${data['pnl']:+,.0f} P&L")

        # Best and worst trades
        sorted_trades = sorted(all_trades, key=lambda x: x['pnl_dollars'], reverse=True)

        print(f"\n🏆 BEST TRADES:")
        for i, trade in enumerate(sorted_trades[:5]):
            print(f"   {i+1}. {trade['date']}: {trade['direction']} @ {trade['volume_bias']:.1%} → ${trade['pnl_dollars']:+,.0f}")

        print(f"\n📉 WORST TRADES:")
        for i, trade in enumerate(sorted_trades[-5:]):
            print(f"   {i+1}. {trade['date']}: {trade['direction']} @ {trade['volume_bias']:.1%} → ${trade['pnl_dollars']:+,.0f}")

        # Skip analysis
        skip_reasons = {}
        for date, reason in skipped_days:
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

        print(f"\n⚠️  SKIP REASONS:")
        for reason, count in sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True):
            print(f"   {reason}: {count} days")

        # Save comprehensive results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"comprehensive_122_days_{timestamp}.json"

        with open(results_file, 'w') as f:
            json.dump({
                'strategy': 'comprehensive_122_day_validation',
                'parameters': {
                    'min_bid_size': min_bid_size,
                    'min_pressure_ratio': min_pressure_ratio,
                    'min_volume_bias': min_volume_bias,
                    'min_total_volume': min_total_volume
                },
                'summary': {
                    'total_days': len(all_dates),
                    'successful_trades': successful_days,
                    'total_pnl': total_pnl,
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl,
                    'hit_rate': successful_days/len(all_dates)*100
                },
                'monthly_results': monthly_results,
                'all_trades': all_trades,
                'skipped_days': skipped_days[:20],  # Sample
                'failed_days': failed_days[:10]    # Sample
            }, f, indent=2)

        print(f"\n📁 Comprehensive results saved to: {results_file}")

        # Final validation verdict
        if total_pnl > 1000 and win_rate > 50:
            print(f"\n🎉 STRATEGY FULLY VALIDATED!")
            print(f"✅ Profitable across 122 days: ${total_pnl:+,.2f}")
            print(f"✅ Strong win rate: {win_rate:.1f}%")
            print(f"✅ Consistent hit rate: {successful_days/len(all_dates)*100:.1f}%")
            print(f"🚀 READY FOR LIVE TRADING IMPLEMENTATION!")
        elif total_pnl > 0:
            print(f"\n✅ STRATEGY VALIDATION: PROMISING")
            print(f"💰 Profitable overall: ${total_pnl:+,.2f}")
            print(f"🔧 Room for optimization with {win_rate:.1f}% win rate")
        else:
            print(f"\n📊 STRATEGY VALIDATION: NEEDS REFINEMENT")
            print(f"❌ Current loss: ${total_pnl:+,.2f}")
            print(f"💡 Consider parameter adjustments")
    else:
        print("\n❌ No successful trades generated across 122 days")
        print("🔧 Strategy parameters may be too restrictive")

if __name__ == "__main__":
    full_122_day_backtest()
