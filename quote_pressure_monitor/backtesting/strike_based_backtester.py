#!/usr/bin/env python3
"""
STRIKE-BASED DIRECTIONAL BACKTESTER
===================================

NEW STRATEGY LOGIC:
- If institutional flow at strikes ABOVE current NQ price → GO LONG
- If institutional flow at strikes BELOW current NQ price → GO SHORT

This makes intuitive sense - institutions position where they expect price to go!
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def strike_based_backtest():
    """Run backtesting using strike-based directional logic"""

    print("🚀 STRIKE-BASED DIRECTIONAL BACKTESTER")
    print("=" * 60)
    print("🎯 Strategy: If institutions position at higher strikes → LONG")
    print("🎯          If institutions position at lower strikes → SHORT")
    print("-" * 60)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Test on known good dates
    test_dates = [
        "2025-06-16",
        "2025-06-17",
        "2025-06-18",
    ]

    # Strategy parameters
    min_bid_size = 50
    min_pressure_ratio = 2.0

    all_results = []
    total_pnl = 0

    # Symbol resolution cache
    symbol_cache = {}

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
                        symbol = mapping_list[0].get('s', f'UNMAPPED_{instrument_id}')
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

    for date_str in test_dates:
        print(f"\n📊 Testing {date_str}")
        print("-" * 30)

        start_time = f"{date_str}T14:30:00"
        end_time = f"{date_str}T15:00:00"

        try:
            # Step 1: Get current NQ price at start of session
            print("   📈 Getting current NQ price...")

            nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQM5"],
                schema="mbp-1",
                start=start_time,
                end=f"{date_str}T14:31:00"  # Just first minute
            )

            current_nq_price = None
            for record in nq_data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    current_nq_price = (level.bid_px + level.ask_px) / 2 / 1e9
                    break

            if not current_nq_price:
                print("   ❌ Could not get current NQ price")
                continue

            print(f"   💰 Current NQ Price: ${current_nq_price:,.2f}")

            # Step 2: Detect institutional signals and resolve symbols
            print("   🔍 Detecting institutional flow...")

            data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_time,
                end=end_time,
                stype_in="parent"
            )

            # Collect raw signals
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
                            'bid_size': bid_size,
                            'pressure_ratio': pressure_ratio
                        })
                        instrument_ids.add(record.instrument_id)

            print(f"   📊 Processed: {processed:,} quotes")
            print(f"   🎯 Raw signals: {len(raw_signals)}")

            if not raw_signals:
                print("   📭 No institutional flow detected")
                continue

            # Step 3: Resolve symbols to get strikes
            print("   🔄 Resolving option symbols...")
            symbol_map = resolve_symbols_batch(list(instrument_ids), date_str)

            # Step 4: Analyze strikes vs current price
            strike_signals = []

            for signal in raw_signals:
                symbol = symbol_map.get(signal['instrument_id'])
                if symbol:
                    strike = parse_option_strike(symbol)
                    if strike:
                        signal['symbol'] = symbol
                        signal['strike'] = strike
                        signal['strike_vs_current'] = strike - current_nq_price
                        strike_signals.append(signal)

            print(f"   ✅ Resolved {len(strike_signals)} signals with strikes")

            if not strike_signals:
                print("   ❌ No valid strike data")
                continue

            # Step 5: Calculate strike-weighted direction
            total_volume_above = 0
            total_volume_below = 0
            total_volume_at = 0

            strikes_above = []
            strikes_below = []
            strikes_at = []

            for signal in strike_signals:
                volume = signal['bid_size']
                strike_diff = signal['strike_vs_current']

                if strike_diff > 100:  # More than $100 above current
                    total_volume_above += volume
                    strikes_above.append(signal)
                elif strike_diff < -100:  # More than $100 below current
                    total_volume_below += volume
                    strikes_below.append(signal)
                else:  # Near current price (within $100)
                    total_volume_at += volume
                    strikes_at.append(signal)

            print(f"   📊 Volume Above: {total_volume_above} contracts ({len(strikes_above)} signals)")
            print(f"   📊 Volume Below: {total_volume_below} contracts ({len(strikes_below)} signals)")
            print(f"   📊 Volume Near:  {total_volume_at} contracts ({len(strikes_at)} signals)")

            # Step 6: Determine direction based on volume-weighted strikes
            net_volume = total_volume_above - total_volume_below
            total_directional_volume = total_volume_above + total_volume_below

            if total_directional_volume == 0:
                print("   ⚠️  No directional signal - all volume near current price")
                continue

            # Require meaningful volume bias (at least 20% edge in one direction)
            volume_ratio = abs(net_volume) / total_directional_volume

            if volume_ratio < 0.2:
                print(f"   ⚠️  Insufficient directional bias ({volume_ratio:.1%}) - skipping")
                continue

            # Determine trade direction
            if net_volume > 0:
                direction = "LONG"
                print(f"   🐂 BULLISH SIGNAL: {total_volume_above} vs {total_volume_below} (net +{net_volume})")
            else:
                direction = "SHORT"
                print(f"   🐻 BEARISH SIGNAL: {total_volume_below} vs {total_volume_above} (net {net_volume})")

            # Step 7: Calculate P&L for this direction
            print("   💰 Calculating P&L...")

            # Get full session NQ prices
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

                # Calculate P&L based on direction
                if direction == "LONG":
                    pnl_points = exit_price - entry_price
                else:  # SHORT
                    pnl_points = entry_price - exit_price

                pnl_dollars = pnl_points * 20  # NQ multiplier

                result = {
                    'date': date_str,
                    'current_nq_price': current_nq_price,
                    'direction': direction,
                    'volume_above': total_volume_above,
                    'volume_below': total_volume_below,
                    'net_volume': net_volume,
                    'volume_ratio': volume_ratio,
                    'total_signals': len(strike_signals),
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_points': pnl_points,
                    'pnl_dollars': pnl_dollars
                }

                all_results.append(result)
                total_pnl += pnl_dollars

                print(f"   📈 Entry: ${entry_price:.2f} → Exit: ${exit_price:.2f}")
                print(f"   💰 {direction} P&L: {pnl_points:+.2f} pts = ${pnl_dollars:+,.2f}")

            else:
                print("   ❌ Insufficient NQ price data")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue

    # Final results
    print("\n" + "=" * 60)
    print("📊 STRIKE-BASED BACKTEST RESULTS")
    print("=" * 60)

    if all_results:
        winning_days = len([r for r in all_results if r['pnl_dollars'] > 0])
        win_rate = winning_days / len(all_results) * 100
        avg_pnl = total_pnl / len(all_results)

        print(f"🎯 PERFORMANCE:")
        print(f"   Days Tested: {len(all_results)}")
        print(f"   Total P&L: ${total_pnl:+,.2f}")
        print(f"   Average P&L/Day: ${avg_pnl:+,.2f}")
        print(f"   Win Rate: {win_rate:.1f}%")

        print(f"\n📅 DETAILED RESULTS:")
        for result in all_results:
            print(f"   {result['date']}: {result['direction']} ({result['volume_ratio']:.1%} bias)")
            print(f"      Volume: {result['volume_above']} above vs {result['volume_below']} below")
            print(f"      P&L: ${result['pnl_dollars']:+,.2f} ({result['pnl_points']:+.2f} pts)")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"strike_based_backtest_{timestamp}.json"

        with open(results_file, 'w') as f:
            json.dump({
                'strategy': 'strike_based_directional',
                'summary': {
                    'days_tested': len(all_results),
                    'total_pnl': total_pnl,
                    'avg_pnl_per_day': avg_pnl,
                    'win_rate': win_rate
                },
                'daily_results': all_results
            }, f, indent=2)

        print(f"\n📁 Results saved to: {results_file}")

        # Strategy verdict
        if total_pnl > 0:
            print(f"\n🎉 STRIKE-BASED STRATEGY IS PROFITABLE!")
            print(f"Following institutional strike positioning: ${total_pnl:+,.2f}")
            print(f"This approach shows {avg_pnl:+.2f} average daily returns")
        else:
            print(f"\n📉 Strategy still shows loss: ${total_pnl:,.2f}")
            print("May need further refinement of volume thresholds")
    else:
        print("❌ No valid results generated")

if __name__ == "__main__":
    strike_based_backtest()
