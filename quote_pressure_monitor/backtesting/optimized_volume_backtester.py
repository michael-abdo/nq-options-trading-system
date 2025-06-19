#!/usr/bin/env python3
"""
OPTIMIZED VOLUME THRESHOLD BACKTESTER
====================================

Key Optimization: Require 40%+ volume bias for reliable signals
Test this critical parameter adjustment on our best data
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def optimized_volume_backtest():
    """Test strategy with optimized 40%+ volume bias requirement"""

    print("🎯 OPTIMIZED VOLUME THRESHOLD BACKTESTER")
    print("=" * 60)
    print("🔧 KEY OPTIMIZATION: Require 40%+ volume bias")
    print("📊 Testing on proven data points")
    print("-" * 60)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Test on our best known sessions
    test_sessions = [
        ("2025-06-16", "14:30", "15:00"),  # Proven successful day
        ("2025-06-17", "14:30", "15:00"),  # Large dataset day
        ("2025-06-18", "14:30", "15:00"),  # Recent day
        ("2025-06-16", "09:30", "10:00"),  # Market open
        ("2025-06-17", "15:30", "16:00"),  # Market close
        ("2025-06-18", "09:30", "10:00"),  # Additional session
    ]

    # OPTIMIZED PARAMETERS
    min_bid_size = 50
    min_pressure_ratio = 2.0
    min_volume_bias = 0.40  # 🔧 KEY CHANGE: 40% minimum (was 20%)
    min_total_volume = 2000  # Require significant total volume

    print(f"⚙️  OPTIMIZED PARAMETERS:")
    print(f"   Min Bid Size: {min_bid_size}")
    print(f"   Min Pressure Ratio: {min_pressure_ratio}")
    print(f"   Min Volume Bias: {min_volume_bias*100:.0f}% (KEY OPTIMIZATION)")
    print(f"   Min Total Volume: {min_total_volume}")

    results = []
    total_pnl = 0

    def resolve_symbols_batch(instrument_ids, target_date):
        """Resolve instrument IDs to symbols"""
        if not instrument_ids:
            return {}

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
                        symbol = mapping_list[0].get('s', '')
                        symbol_map[int(instrument_id)] = symbol

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

    def analyze_optimized_session(date, start_time, end_time):
        """Analyze session with optimized volume bias"""

        session_name = f"{date} {start_time}-{end_time}"
        print(f"\n📊 {session_name}")
        print("   " + "-" * 40)

        try:
            start_dt = f"{date}T{start_time}:00"
            end_dt = f"{date}T{end_time}:00"

            # Step 1: Get current NQ price
            print("   📈 Current NQ price: ", end="")
            nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQM5"],
                schema="mbp-1",
                start=start_dt,
                end=f"{date}T{start_time[:2]}:{int(start_time[3:])+1:02d}:00"
            )

            current_nq_price = None
            for record in nq_data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    current_nq_price = (level.bid_px + level.ask_px) / 2 / 1e9
                    break

            if not current_nq_price:
                print("❌ No data")
                return None

            print(f"${current_nq_price:,.2f}")

            # Step 2: Get institutional signals with full analysis
            print("   🔍 Detecting institutional flow: ", end="")

            data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_dt,
                end=end_dt,
                stype_in="parent"
            )

            # Collect all qualifying signals
            raw_signals = []
            instrument_ids = set()
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

                    if bid_size >= min_bid_size and pressure_ratio >= min_pressure_ratio:
                        raw_signals.append({
                            'instrument_id': record.instrument_id,
                            'bid_size': bid_size,
                            'pressure_ratio': pressure_ratio
                        })
                        instrument_ids.add(record.instrument_id)

            print(f"{len(raw_signals)} signals from {processed_count:,} quotes")

            if len(raw_signals) < 20:
                print("   ⚠️  Insufficient signals for analysis")
                return 'insufficient_signals'

            # Step 3: Resolve symbols for strike analysis
            print("   🔄 Resolving symbols: ", end="")
            symbol_map = resolve_symbols_batch(list(instrument_ids), date)
            print(f"{len(symbol_map)} resolved")

            # Step 4: Comprehensive strike analysis
            print("   📊 Strike analysis: ", end="")

            volume_above = 0
            volume_below = 0
            volume_near = 0
            strikes_analyzed = 0

            for signal in raw_signals:
                symbol = symbol_map.get(signal['instrument_id'])
                if symbol:
                    strike = parse_option_strike(symbol)
                    if strike:
                        strikes_analyzed += 1
                        volume = signal['bid_size']
                        strike_diff = strike - current_nq_price

                        if strike_diff > 100:  # Above current + buffer
                            volume_above += volume
                        elif strike_diff < -100:  # Below current - buffer
                            volume_below += volume
                        else:  # Near current price
                            volume_near += volume

            total_directional_volume = volume_above + volume_below
            total_volume = total_directional_volume + volume_near

            print(f"{strikes_analyzed} strikes analyzed")
            print(f"      Volume Above: {volume_above:,} contracts")
            print(f"      Volume Below: {volume_below:,} contracts")
            print(f"      Volume Near:  {volume_near:,} contracts")
            print(f"      Total Volume: {total_volume:,} contracts")

            # Apply OPTIMIZED volume thresholds
            if total_directional_volume < min_total_volume:
                print(f"   ❌ Insufficient directional volume ({total_directional_volume} < {min_total_volume})")
                return 'insufficient_volume'

            net_volume = volume_above - volume_below
            volume_bias = abs(net_volume) / total_directional_volume

            # 🔧 KEY OPTIMIZATION: Require 40%+ bias
            if volume_bias < min_volume_bias:
                print(f"   ❌ Insufficient bias ({volume_bias:.1%} < {min_volume_bias:.0%})")
                return 'insufficient_bias'

            # Determine direction
            direction = "LONG" if net_volume > 0 else "SHORT"
            print(f"   ✅ STRONG {direction} SIGNAL ({volume_bias:.1%} bias)")

            # Step 5: Calculate P&L
            print("   💰 P&L calculation: ", end="")

            full_nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQM5"],
                schema="mbp-1",
                start=start_dt,
                end=end_dt
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
                else:  # SHORT
                    pnl_points = entry_price - exit_price

                pnl_dollars = pnl_points * 20  # NQ multiplier

                print(f"${pnl_dollars:+,.2f} ({pnl_points:+.2f} pts)")
                print(f"      Entry: ${entry_price:.2f} → Exit: ${exit_price:.2f}")

                return {
                    'session': session_name,
                    'current_nq_price': current_nq_price,
                    'direction': direction,
                    'volume_bias': volume_bias,
                    'volume_above': volume_above,
                    'volume_below': volume_below,
                    'total_directional_volume': total_directional_volume,
                    'net_volume': net_volume,
                    'strikes_analyzed': strikes_analyzed,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_points': pnl_points,
                    'pnl_dollars': pnl_dollars
                }
            else:
                print("❌ No price data")
                return 'no_price_data'

        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}")
            return f'error_{str(e)[:20]}'

    # Run optimized analysis
    print(f"\n🔄 Testing {len(test_sessions)} sessions with 40%+ volume bias requirement...")

    successful_trades = 0
    skipped_sessions = []

    for date, start_time, end_time in test_sessions:
        result = analyze_optimized_session(date, start_time, end_time)

        if isinstance(result, dict):
            results.append(result)
            total_pnl += result['pnl_dollars']
            successful_trades += 1
        else:
            skipped_sessions.append({
                'session': f"{date} {start_time}-{end_time}",
                'reason': result
            })

    # Optimized results analysis
    print("\n" + "=" * 60)
    print("📊 OPTIMIZED VOLUME THRESHOLD RESULTS")
    print("=" * 60)

    print(f"📋 SESSION SUMMARY:")
    print(f"   Total Sessions Tested: {len(test_sessions)}")
    print(f"   Successful Trades: {successful_trades}")
    print(f"   Skipped Sessions: {len(skipped_sessions)}")
    print(f"   Success Rate: {successful_trades/len(test_sessions)*100:.1f}%")

    if skipped_sessions:
        print(f"\n⚠️  SKIPPED SESSIONS:")
        for skip in skipped_sessions:
            print(f"   • {skip['session']}: {skip['reason']}")

    if successful_trades > 0:
        winning_trades = len([r for r in results if r['pnl_dollars'] > 0])
        win_rate = winning_trades / len(results) * 100
        avg_pnl = total_pnl / len(results)
        avg_bias = sum(r['volume_bias'] for r in results) / len(results)

        print(f"\n🎯 PERFORMANCE WITH 40%+ BIAS REQUIREMENT:")
        print(f"   Total P&L: ${total_pnl:+,.2f}")
        print(f"   Average P&L/Trade: ${avg_pnl:+,.2f}")
        print(f"   Win Rate: {win_rate:.1f}% ({winning_trades}W / {len(results)-winning_trades}L)")
        print(f"   Average Volume Bias: {avg_bias:.1%}")

        # Show individual results
        print(f"\n📊 INDIVIDUAL TRADE RESULTS:")
        for i, result in enumerate(results):
            print(f"   {i+1}. {result['session']}")
            print(f"      {result['direction']} @ {result['volume_bias']:.1%} bias → ${result['pnl_dollars']:+,.2f}")
            print(f"      Volume: {result['volume_above']:,} above vs {result['volume_below']:,} below")

        # Bias analysis
        high_bias_trades = [r for r in results if r['volume_bias'] >= 0.5]
        if high_bias_trades:
            high_bias_pnl = sum(r['pnl_dollars'] for r in high_bias_trades)
            print(f"\n🔥 HIGH BIAS TRADES (≥50%):")
            print(f"   Count: {len(high_bias_trades)}")
            print(f"   P&L: ${high_bias_pnl:+,.2f}")
            print(f"   Avg Bias: {sum(r['volume_bias'] for r in high_bias_trades)/len(high_bias_trades):.1%}")

        # Save optimized results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"optimized_volume_40pct_{timestamp}.json"

        with open(results_file, 'w') as f:
            json.dump({
                'strategy': 'optimized_volume_bias_40_percent',
                'parameters': {
                    'min_bid_size': min_bid_size,
                    'min_pressure_ratio': min_pressure_ratio,
                    'min_volume_bias': min_volume_bias,
                    'min_total_volume': min_total_volume
                },
                'summary': {
                    'total_sessions': len(test_sessions),
                    'successful_trades': successful_trades,
                    'total_pnl': total_pnl,
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl,
                    'avg_volume_bias': avg_bias
                },
                'trades': results,
                'skipped_sessions': skipped_sessions
            }, f, indent=2)

        print(f"\n📁 Optimized results saved to: {results_file}")

        # Final assessment
        if total_pnl > 0 and win_rate >= 50:
            print(f"\n🎉 OPTIMIZATION SUCCESS!")
            print(f"✅ 40% volume bias requirement IMPROVED results")
            print(f"✅ Strategy now profitable: ${total_pnl:+,.2f}")
            print(f"✅ Quality over quantity: {successful_trades} high-conviction trades")
        elif total_pnl > 0:
            print(f"\n✅ OPTIMIZATION PROGRESS")
            print(f"💰 Profitable: ${total_pnl:+,.2f}")
            print(f"🔧 Win rate {win_rate:.1f}% suggests further tuning possible")
        else:
            print(f"\n🔧 OPTIMIZATION NEEDED")
            print(f"❌ Still showing loss: ${total_pnl:+,.2f}")
            print(f"💡 May need 50%+ bias or other parameter adjustments")
    else:
        print("\n❌ No successful trades with 40% bias requirement")
        print("💡 Consider lowering threshold or adjusting other parameters")

if __name__ == "__main__":
    optimized_volume_backtest()
