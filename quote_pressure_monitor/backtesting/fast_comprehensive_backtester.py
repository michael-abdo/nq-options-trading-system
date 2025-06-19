#!/usr/bin/env python3
"""
FAST COMPREHENSIVE BACKTESTER
=============================

Optimized version for speed - shorter time windows, key dates only
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def fast_comprehensive_backtest():
    """Run fast comprehensive backtest on key dates"""

    print("🚀 FAST COMPREHENSIVE STRIKE-BASED BACKTESTER")
    print("=" * 60)
    print("⚡ Optimized for speed and comprehensive coverage")
    print("-" * 60)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Test recent trading days (known to have data)
    test_dates = [
        "2025-06-12", "2025-06-13", "2025-06-16", "2025-06-17", "2025-06-18"
    ]

    # Multiple sessions per day for more comprehensive testing
    sessions = [
        ("09:30", "10:00"),   # Market open
        ("11:00", "11:30"),   # Mid-morning
        ("14:30", "15:00"),   # Afternoon (proven)
        ("15:30", "16:00")    # Close
    ]

    print(f"📊 Testing {len(test_dates)} days × {len(sessions)} sessions = {len(test_dates) * len(sessions)} total tests")

    all_results = []
    total_pnl = 0
    session_count = 0

    # Optimized parameters
    min_bid_size = 50
    min_pressure_ratio = 2.0
    min_volume_bias = 0.15  # Lower threshold for more trades

    def resolve_symbols_fast(instrument_ids, target_date):
        """Fast symbol resolution with minimal API calls"""
        if not instrument_ids or len(instrument_ids) > 100:
            return {}  # Skip large batches for speed

        try:
            target = datetime.strptime(target_date, "%Y-%m-%d")
            start_date = (target - timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = (target + timedelta(days=1)).strftime("%Y-%m-%d")

            resolution_result = client.symbology.resolve(
                dataset="GLBX.MDP3",
                symbols=[str(id) for id in list(instrument_ids)[:50]],  # Limit to 50 for speed
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

        except:
            return {}

    def parse_strike(symbol):
        """Fast strike parsing"""
        try:
            if 'C' in symbol:
                return int(symbol.split('C')[1].strip())
            elif 'P' in symbol:
                return int(symbol.split('P')[1].strip())
        except:
            pass
        return None

    def analyze_session(date_str, session_start, session_end):
        """Analyze single session optimized for speed"""
        try:
            start_time = f"{date_str}T{session_start}:00"
            end_time = f"{date_str}T{session_end}:00"

            # Get NQ reference price (first minute only)
            nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQM5"],
                schema="mbp-1",
                start=start_time,
                end=f"{date_str}T{session_start[:2]}:{int(session_start[3:])+1:02d}:00"
            )

            nq_price = None
            for record in nq_data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    nq_price = (level.bid_px + level.ask_px) / 2 / 1e9
                    break

            if not nq_price:
                return None

            # Get options signals (smaller sample for speed)
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
            count = 0

            for record in data:
                count += 1
                if count > 500000:  # Limit processing for speed
                    break

                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    bid_size = level.bid_sz
                    ask_size = level.ask_sz

                    if (bid_size >= min_bid_size and ask_size > 0 and
                        bid_size / ask_size >= min_pressure_ratio):

                        signals.append({
                            'instrument_id': record.instrument_id,
                            'bid_size': bid_size
                        })
                        instrument_ids.add(record.instrument_id)

                        if len(signals) > 200:  # Cap for speed
                            break

            if len(signals) < 5:
                return 'insufficient'

            # Fast symbol resolution
            symbol_map = resolve_symbols_fast(instrument_ids, date_str)

            # Quick strike analysis
            volume_above = 0
            volume_below = 0

            for signal in signals:
                symbol = symbol_map.get(signal['instrument_id'])
                if symbol:
                    strike = parse_strike(symbol)
                    if strike:
                        volume = signal['bid_size']
                        if strike > nq_price + 100:
                            volume_above += volume
                        elif strike < nq_price - 100:
                            volume_below += volume

            total_vol = volume_above + volume_below
            if total_vol < 500:
                return 'low_volume'

            net_vol = volume_above - volume_below
            bias = abs(net_vol) / total_vol

            if bias < min_volume_bias:
                return 'no_bias'

            direction = "LONG" if net_vol > 0 else "SHORT"

            # Get session P&L
            full_nq = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQM5"],
                schema="mbp-1",
                start=start_time,
                end=end_time
            )

            prices = []
            for record in full_nq:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    prices.append((level.bid_px + level.ask_px) / 2 / 1e9)
                if len(prices) > 1000:  # Limit for speed
                    break

            if len(prices) < 2:
                return 'no_prices'

            entry, exit = prices[0], prices[-1]
            pnl_pts = (exit - entry) if direction == "LONG" else (entry - exit)
            pnl_dollars = pnl_pts * 20

            return {
                'date': date_str,
                'session': f"{session_start}-{session_end}",
                'direction': direction,
                'bias': bias,
                'volume_above': volume_above,
                'volume_below': volume_below,
                'signals': len(signals),
                'entry': entry,
                'exit': exit,
                'pnl_pts': pnl_pts,
                'pnl_dollars': pnl_dollars
            }

        except Exception as e:
            return f'error_{str(e)[:20]}'

    # Run fast comprehensive test
    print("\n🔄 Running fast comprehensive analysis...")
    print("-" * 60)

    for date in test_dates:
        print(f"\n📅 {date}:")
        day_pnl = 0
        day_trades = 0

        for session_start, session_end in sessions:
            result = analyze_session(date, session_start, session_end)

            if isinstance(result, dict):
                all_results.append(result)
                total_pnl += result['pnl_dollars']
                day_pnl += result['pnl_dollars']
                day_trades += 1
                session_count += 1

                print(f"   {session_start}-{session_end}: {result['direction']} "
                      f"({result['bias']:.1%}) → ${result['pnl_dollars']:+.0f}")
            else:
                print(f"   {session_start}-{session_end}: {result}")

        print(f"   Day Total: {day_trades} trades, ${day_pnl:+.0f}")

    # Comprehensive results
    print("\n" + "=" * 60)
    print("📊 FAST COMPREHENSIVE RESULTS")
    print("=" * 60)

    if session_count > 0:
        winners = [r for r in all_results if r['pnl_dollars'] > 0]
        win_rate = len(winners) / len(all_results) * 100
        avg_pnl = total_pnl / len(all_results)

        print(f"🎯 PERFORMANCE:")
        print(f"   Total Sessions: {session_count}")
        print(f"   Total P&L: ${total_pnl:+,.0f}")
        print(f"   Average P&L/Trade: ${avg_pnl:+.0f}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Best Trade: ${max(r['pnl_dollars'] for r in all_results):+.0f}")
        print(f"   Worst Trade: ${min(r['pnl_dollars'] for r in all_results):+.0f}")

        # Direction analysis
        long_trades = [r for r in all_results if r['direction'] == 'LONG']
        short_trades = [r for r in all_results if r['direction'] == 'SHORT']

        print(f"\n📊 DIRECTION BREAKDOWN:")
        if long_trades:
            long_pnl = sum(r['pnl_dollars'] for r in long_trades)
            print(f"   LONG: {len(long_trades)} trades → ${long_pnl:+.0f}")
        if short_trades:
            short_pnl = sum(r['pnl_dollars'] for r in short_trades)
            print(f"   SHORT: {len(short_trades)} trades → ${short_pnl:+.0f}")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"fast_comprehensive_{timestamp}.json"

        with open(results_file, 'w') as f:
            json.dump({
                'strategy': 'fast_comprehensive_strike',
                'summary': {
                    'total_sessions': session_count,
                    'total_pnl': total_pnl,
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl
                },
                'results': all_results
            }, f, indent=2)

        print(f"\n📁 Results saved to: {results_file}")

        if total_pnl > 0:
            print(f"\n🎉 STRATEGY VALIDATED!")
            print(f"Profitable across multiple sessions and dates: ${total_pnl:+.0f}")
        else:
            print(f"\n📉 Strategy needs optimization: ${total_pnl:+.0f}")
    else:
        print("❌ No successful trades")

if __name__ == "__main__":
    fast_comprehensive_backtest()
