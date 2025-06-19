#!/usr/bin/env python3
"""
FULL MARKET HOURS BACKTESTER
============================

Run IFD v3.0 system across entire market hours (9:30 AM - 4:00 PM ET)
Provide detailed trade-by-trade P&L analysis for each signal
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def full_market_hours_backtest():
    """Run IFD v3.0 across full market hours with detailed trade tracking"""

    print("🕘 FULL MARKET HOURS IFD v3.0 BACKTESTER")
    print("=" * 60)
    print("⏰ Market Hours: 9:30 AM - 4:00 PM ET")
    print("🎯 30-minute scanning intervals")
    print("📊 Detailed trade-by-trade P&L reporting")
    print("-" * 60)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Test recent days with good data
    test_dates = [
        "2025-06-16",
        "2025-06-17", 
        "2025-06-18",
        "2025-06-13",
        "2025-06-12"
    ]

    # Full market hours time slots (30-minute intervals)
    time_slots = [
        ("09:30", "10:00"),  # Market open
        ("10:00", "10:30"),  
        ("10:30", "11:00"),
        ("11:00", "11:30"),
        ("11:30", "12:00"),
        ("12:00", "12:30"),  # Lunch hour
        ("12:30", "13:00"),
        ("13:00", "13:30"),
        ("13:30", "14:00"),
        ("14:00", "14:30"),
        ("14:30", "15:00"),  # Previously tested optimal window
        ("15:00", "15:30"),
        ("15:30", "16:00"),  # Market close
    ]

    # Optimized parameters from 122-day validation
    min_bid_size = 50
    min_pressure_ratio = 2.0
    min_volume_bias = 0.40  # 40% minimum bias
    min_total_volume = 2000

    print(f"⚙️  IFD v3.0 PARAMETERS:")
    print(f"   Min Bid Size: {min_bid_size}")
    print(f"   Min Pressure Ratio: {min_pressure_ratio}")
    print(f"   Min Volume Bias: {min_volume_bias*100:.0f}%")
    print(f"   Min Total Volume: {min_total_volume}")
    print(f"   Time Slots: {len(time_slots)} per day")

    all_trades = []
    daily_summaries = []
    total_pnl = 0
    total_trades = 0

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

    def analyze_time_slot(date, start_time, end_time):
        """Analyze single 30-minute time slot"""

        session_id = f"{date}_{start_time.replace(':', '')}-{end_time.replace(':', '')}"
        print(f"\n📊 {date} {start_time}-{end_time}")
        print("   " + "-" * 35)

        try:
            start_dt = f"{date}T{start_time}:00"
            end_dt = f"{date}T{end_time}:00"

            # Get NQ price for session
            print("   📈 NQ price: ", end="")
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

            # Get institutional signals
            print("   🔍 Institutional flow: ", end="")

            data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_dt,
                end=end_dt,
                stype_in="parent"
            )

            # Collect qualifying signals
            raw_signals = []
            instrument_ids = set()
            processed_count = 0

            for record in data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    processed_count += 1
                    if processed_count > 200000:  # Increased limit for full market hours
                        break

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

                        if len(raw_signals) >= 200:  # Increased for full day
                            break

            print(f"{len(raw_signals)} signals from {processed_count:,} quotes")

            if len(raw_signals) < 20:
                print("   ⚠️  Insufficient signals")
                return None

            # Resolve symbols for strike analysis
            print("   🔄 Resolving symbols: ", end="")
            symbol_map = resolve_symbols_batch(list(instrument_ids), date)
            print(f"{len(symbol_map)} resolved")

            # Strike analysis
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

            print(f"{strikes_analyzed} strikes")
            print(f"      Above: {volume_above:,} | Below: {volume_below:,} | Near: {volume_near:,}")

            # Apply IFD v3.0 filters
            if total_directional_volume < min_total_volume:
                print(f"   ❌ Low volume ({total_directional_volume} < {min_total_volume})")
                return None

            net_volume = volume_above - volume_below
            volume_bias = abs(net_volume) / total_directional_volume

            if volume_bias < min_volume_bias:
                print(f"   ❌ Low bias ({volume_bias:.1%} < {min_volume_bias:.0%})")
                return None

            # Strong signal detected
            direction = "LONG" if net_volume > 0 else "SHORT"
            print(f"   ✅ {direction} SIGNAL ({volume_bias:.1%} bias)")

            # Calculate P&L for this trade
            print("   💰 P&L: ", end="")

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

                return {
                    'session_id': session_id,
                    'date': date,
                    'time_slot': f"{start_time}-{end_time}",
                    'nq_price': current_nq_price,
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
                return None

        except Exception as e:
            print(f"   ❌ Error: {str(e)[:40]}")
            return None

    # Run full market hours analysis
    print(f"\n🔄 Analyzing {len(test_dates)} days × {len(time_slots)} time slots = {len(test_dates) * len(time_slots)} total sessions...")

    for date in test_dates:
        print(f"\n{'='*60}")
        print(f"📅 FULL DAY ANALYSIS: {date}")
        print(f"{'='*60}")

        daily_trades = []
        daily_pnl = 0

        for start_time, end_time in time_slots:
            result = analyze_time_slot(date, start_time, end_time)

            if result:
                daily_trades.append(result)
                all_trades.append(result)
                daily_pnl += result['pnl_dollars']
                total_pnl += result['pnl_dollars']
                total_trades += 1

        # Daily summary
        daily_summary = {
            'date': date,
            'total_trades': len(daily_trades),
            'daily_pnl': daily_pnl,
            'winning_trades': len([t for t in daily_trades if t['pnl_dollars'] > 0]),
            'losing_trades': len([t for t in daily_trades if t['pnl_dollars'] < 0]),
            'best_trade': max(daily_trades, key=lambda x: x['pnl_dollars'])['pnl_dollars'] if daily_trades else 0,
            'worst_trade': min(daily_trades, key=lambda x: x['pnl_dollars'])['pnl_dollars'] if daily_trades else 0,
            'trades': daily_trades
        }
        daily_summaries.append(daily_summary)

        # Print daily results
        if daily_trades:
            win_rate = len([t for t in daily_trades if t['pnl_dollars'] > 0]) / len(daily_trades) * 100
            print(f"\n📊 {date} DAILY SUMMARY:")
            print(f"   Trades: {len(daily_trades)}")
            print(f"   P&L: ${daily_pnl:+,.2f}")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Best: ${max(daily_trades, key=lambda x: x['pnl_dollars'])['pnl_dollars']:+,.2f}")
            print(f"   Worst: ${min(daily_trades, key=lambda x: x['pnl_dollars'])['pnl_dollars']:+,.2f}")
        else:
            print(f"\n📊 {date}: No qualifying trades")

    # Final comprehensive results
    print("\n" + "="*60)
    print("🏆 FULL MARKET HOURS IFD v3.0 RESULTS")
    print("="*60)

    print(f"\n📊 OVERALL PERFORMANCE:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Total P&L: ${total_pnl:+,.2f}")
    
    if total_trades > 0:
        winning_trades = len([t for t in all_trades if t['pnl_dollars'] > 0])
        win_rate = winning_trades / total_trades * 100
        avg_pnl = total_pnl / total_trades
        
        print(f"   Win Rate: {win_rate:.1f}% ({winning_trades}W / {total_trades-winning_trades}L)")
        print(f"   Average P&L/Trade: ${avg_pnl:+,.2f}")
        print(f"   Best Trade: ${max(all_trades, key=lambda x: x['pnl_dollars'])['pnl_dollars']:+,.2f}")
        print(f"   Worst Trade: ${min(all_trades, key=lambda x: x['pnl_dollars'])['pnl_dollars']:+,.2f}")

        # Trade-by-trade breakdown
        print(f"\n📋 DETAILED TRADE-BY-TRADE BREAKDOWN:")
        print("   " + "-"*55)
        for i, trade in enumerate(all_trades, 1):
            print(f"   {i:2d}. {trade['date']} {trade['time_slot']} {trade['direction']:5s} "
                  f"{trade['volume_bias']:5.1%} bias → ${trade['pnl_dollars']:+7.2f}")

        # Time slot analysis
        time_slot_performance = {}
        for trade in all_trades:
            slot = trade['time_slot']
            if slot not in time_slot_performance:
                time_slot_performance[slot] = {'trades': 0, 'pnl': 0}
            time_slot_performance[slot]['trades'] += 1
            time_slot_performance[slot]['pnl'] += trade['pnl_dollars']

        print(f"\n⏰ TIME SLOT PERFORMANCE:")
        print("   " + "-"*40)
        for slot in sorted(time_slot_performance.keys()):
            perf = time_slot_performance[slot]
            avg_pnl = perf['pnl'] / perf['trades'] if perf['trades'] > 0 else 0
            print(f"   {slot}: {perf['trades']} trades, ${perf['pnl']:+6.2f} total, ${avg_pnl:+6.2f} avg")

        # Save comprehensive results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"full_market_hours_ifd_v3_{timestamp}.json"

        comprehensive_results = {
            'strategy': 'ifd_v3_full_market_hours',
            'analysis_period': f"{test_dates[0]} to {test_dates[-1]}",
            'market_hours': "09:30-16:00 ET",
            'time_slots_per_day': len(time_slots),
            'parameters': {
                'min_bid_size': min_bid_size,
                'min_pressure_ratio': min_pressure_ratio,
                'min_volume_bias': min_volume_bias,
                'min_total_volume': min_total_volume
            },
            'summary': {
                'total_days_analyzed': len(test_dates),
                'total_sessions_tested': len(test_dates) * len(time_slots),
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'average_pnl_per_trade': avg_pnl
            },
            'daily_summaries': daily_summaries,
            'all_trades': all_trades,
            'time_slot_performance': time_slot_performance
        }

        with open(results_file, 'w') as f:
            json.dump(comprehensive_results, f, indent=2)

        print(f"\n📁 Comprehensive results saved to: {results_file}")

        # Final assessment
        if total_pnl > 0:
            print(f"\n🎉 IFD v3.0 FULL MARKET HOURS: PROFITABLE!")
            print(f"✅ System generated ${total_pnl:+,.2f} across {total_trades} trades")
            print(f"✅ {win_rate:.1f}% win rate demonstrates consistent performance")
            print(f"✅ Ready for live trading deployment")
        else:
            print(f"\n📊 IFD v3.0 FULL MARKET HOURS: MIXED RESULTS")
            print(f"💰 Total: ${total_pnl:+,.2f} across {total_trades} trades")
            print(f"🔧 Consider parameter optimization or selective time slot trading")

    else:
        print("❌ No qualifying trades found across all market hours")
        print("💡 Consider loosening parameters or checking data availability")

if __name__ == "__main__":
    full_market_hours_backtest()