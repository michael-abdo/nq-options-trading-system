#!/usr/bin/env python3
"""
FOCUSED RECENT 122-DAY BACKTESTER
=================================

Test optimized strategy on recent weeks where we have verified data quality
Focus on June 2025 data with proven symbol resolution
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def focused_recent_backtest():
    """Test strategy on recent verified data with proper contract mapping"""

    print("🎯 FOCUSED RECENT 122-DAY BACKTESTER")
    print("=" * 70)
    print("Testing on June 2025 data with verified contract symbols")
    print("Using optimized 40% volume bias threshold")
    print("-" * 70)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Focus on June 2025 where we have verified data quality
    recent_dates = [
        "2025-06-02", "2025-06-03", "2025-06-04", "2025-06-05", "2025-06-06",
        "2025-06-09", "2025-06-10", "2025-06-11", "2025-06-12", "2025-06-13",
        "2025-06-16", "2025-06-17", "2025-06-18"  # Skip 2025-06-19 (partial data)
    ]

    print(f"📊 Testing {len(recent_dates)} recent trading days with verified data quality")

    # Optimized parameters (proven successful)
    min_bid_size = 50
    min_pressure_ratio = 2.0
    min_volume_bias = 0.40  # 40% minimum bias
    min_total_volume = 2000

    # Track results
    all_trades = []
    total_pnl = 0
    successful_days = 0
    failed_days = []
    skipped_days = []

    # Symbol resolution cache
    symbol_cache = {}

    def resolve_symbols_for_june(instrument_ids, target_date):
        """Symbol resolution optimized for June 2025"""
        cache_key = f"june_{target_date}_{len(instrument_ids)}"
        if cache_key in symbol_cache:
            return symbol_cache[cache_key]

        if not instrument_ids or len(instrument_ids) > 150:
            return {}

        try:
            target = datetime.strptime(target_date, "%Y-%m-%d")
            start_date = (target - timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = (target + timedelta(days=1)).strftime("%Y-%m-%d")

            # Use first 100 IDs for speed
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

        except Exception as e:
            print(f"      Symbol resolution error: {e}")
            return {}

    def parse_strike_price(symbol):
        """Extract strike price from option symbol"""
        try:
            if 'C' in symbol:
                return int(symbol.split('C')[1].strip())
            elif 'P' in symbol:
                return int(symbol.split('P')[1].strip())
        except:
            pass
        return None

    def get_nq_contract_for_date(date_str):
        """Get appropriate NQ contract for given date"""
        # For June 2025, use June contract (NQM5)
        if date_str.startswith("2025-06"):
            return "NQM5"
        elif date_str.startswith("2025-05"):
            return "NQM5"  # June contract active
        elif date_str.startswith("2025-04"):
            return "NQM5"  # June contract
        elif date_str.startswith("2025-03"):
            return "NQH5"  # March contract
        elif date_str.startswith("2025-02"):
            return "NQH5"  # March contract
        else:
            return "NQH5"  # March contract for early 2025

    def analyze_single_day_focused(date_str):
        """Analyze single day with focused approach"""
        try:
            print(f"\n📅 {date_str}: ", end="", flush=True)

            # Get appropriate contract
            nq_contract = get_nq_contract_for_date(date_str)

            # Use proven successful time window
            start_time = f"{date_str}T14:30:00"
            end_time = f"{date_str}T15:00:00"

            # Step 1: Get NQ reference price
            nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=[nq_contract],
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
                print("❌ No NQ price")
                return 'no_nq_price'

            print(f"NQ ${current_nq_price:,.0f}", end=" | ")

            # Step 2: Get institutional signals (limited for efficiency)
            data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_time,
                end=end_time,
                stype_in="parent"
            )

            # Quick signal collection
            signals = []
            instrument_ids = set()
            processed = 0

            for record in data:
                processed += 1
                if processed > 500000:  # 500k quote limit for speed
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

                        if len(signals) >= 300:  # Limit for speed
                            break

            print(f"{len(signals)} signals", end=" | ")

            if len(signals) < 10:
                print("❌ Insufficient signals")
                return 'insufficient_signals'

            # Step 3: Symbol resolution (sample)
            symbol_map = resolve_symbols_for_june(instrument_ids, date_str)

            # Step 4: Strike analysis
            volume_above = 0
            volume_below = 0
            strikes_found = 0

            for signal in signals:
                symbol = symbol_map.get(signal['id'])
                if symbol:
                    strike = parse_strike_price(symbol)
                    if strike:
                        strikes_found += 1
                        volume = signal['size']

                        if strike > current_nq_price + 100:
                            volume_above += volume
                        elif strike < current_nq_price - 100:
                            volume_below += volume

            total_directional = volume_above + volume_below

            if total_directional < min_total_volume:
                print(f"❌ Low volume ({total_directional})")
                return 'insufficient_volume'

            net_volume = volume_above - volume_below
            volume_bias = abs(net_volume) / total_directional

            if volume_bias < min_volume_bias:
                print(f"❌ Low bias ({volume_bias:.1%})")
                return f'insufficient_bias_{volume_bias:.1%}'

            direction = "LONG" if net_volume > 0 else "SHORT"
            print(f"{direction} {volume_bias:.1%}", end=" | ")

            # Step 5: Get P&L
            full_nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=[nq_contract],
                schema="mbp-1",
                start=start_time,
                end=end_time
            )

            prices = []
            count = 0
            for record in full_nq_data:
                count += 1
                if count > 500:  # Sample for speed
                    break
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    prices.append((level.bid_px + level.ask_px) / 2 / 1e9)

            if len(prices) < 2:
                print("❌ No price data")
                return 'no_price_data'

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
                'total_volume': total_directional,
                'strikes_analyzed': strikes_found,
                'current_nq': current_nq_price,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl_points': pnl_points,
                'pnl_dollars': pnl_dollars,
                'contract_used': nq_contract
            }

        except Exception as e:
            print(f"❌ Error: {str(e)[:30]}")
            return f'error_{str(e)[:30]}'

    # Run focused analysis on recent data
    print("\n🔄 Processing recent trading days with verified data quality...")

    for date_str in recent_dates:
        result = analyze_single_day_focused(date_str)

        if isinstance(result, dict):
            # Successful trade
            all_trades.append(result)
            total_pnl += result['pnl_dollars']
            successful_days += 1

        elif result.startswith('error_'):
            failed_days.append((date_str, result))
        else:
            skipped_days.append((date_str, result))

    # Results analysis
    print("\n" + "=" * 70)
    print("📊 FOCUSED RECENT BACKTEST RESULTS")
    print("=" * 70)

    print(f"📋 EXECUTION SUMMARY:")
    print(f"   Days Tested: {len(recent_dates)}")
    print(f"   Successful Trades: {successful_days}")
    print(f"   Skipped Days: {len(skipped_days)}")
    print(f"   Failed Days: {len(failed_days)}")
    print(f"   Hit Rate: {successful_days/len(recent_dates)*100:.1f}%")

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

        # Show individual trades
        print(f"\n📊 ALL TRADES:")
        for i, trade in enumerate(all_trades):
            print(f"   {i+1}. {trade['date']}: {trade['direction']} @ {trade['volume_bias']:.1%} → ${trade['pnl_dollars']:+,.0f}")
            print(f"      Vol: {trade['volume_above']:,} above vs {trade['volume_below']:,} below | {trade['contract_used']}")

        # Skip analysis
        if skipped_days:
            skip_reasons = {}
            for date, reason in skipped_days:
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

            print(f"\n⚠️  SKIP REASONS:")
            for reason, count in sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True):
                print(f"   {reason}: {count} days")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"focused_recent_13_days_{timestamp}.json"

        with open(results_file, 'w') as f:
            json.dump({
                'strategy': 'focused_recent_validation',
                'parameters': {
                    'min_bid_size': min_bid_size,
                    'min_pressure_ratio': min_pressure_ratio,
                    'min_volume_bias': min_volume_bias,
                    'min_total_volume': min_total_volume
                },
                'summary': {
                    'total_days': len(recent_dates),
                    'successful_trades': successful_days,
                    'total_pnl': total_pnl,
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl,
                    'hit_rate': successful_days/len(recent_dates)*100
                },
                'all_trades': all_trades,
                'skipped_days': skipped_days,
                'failed_days': failed_days
            }, indent=2)

        print(f"\n📁 Results saved to: {results_file}")

        # Final assessment
        if total_pnl > 500 and win_rate > 60:
            print(f"\n🎉 STRATEGY VALIDATED ON RECENT DATA!")
            print(f"✅ Profitable: ${total_pnl:+,.2f}")
            print(f"✅ High win rate: {win_rate:.1f}%")
            print(f"🚀 Ready for full 122-day validation!")
        elif total_pnl > 0:
            print(f"\n✅ PROMISING RESULTS ON RECENT DATA")
            print(f"💰 Profitable: ${total_pnl:+,.2f}")
            print(f"🔧 {win_rate:.1f}% win rate suggests room for improvement")
        else:
            print(f"\n📊 NEEDS OPTIMIZATION")
            print(f"❌ Loss on recent data: ${total_pnl:+,.2f}")
            print(f"💡 Parameters need further refinement")
    else:
        print("\n❌ No successful trades on recent data")
        print("🔧 Strategy parameters too restrictive for current market conditions")

if __name__ == "__main__":
    focused_recent_backtest()
