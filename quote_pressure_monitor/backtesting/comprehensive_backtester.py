#!/usr/bin/env python3
"""
COMPREHENSIVE INSTITUTIONAL FLOW BACKTESTER
===========================================

Run backtesting on ALL available data to validate the strategy
"""

import os
import sys
import json
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import databento as db

# Add parent directory for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

class ComprehensiveBacktester:
    """
    Run institutional flow backtesting across all available data
    """

    def __init__(self, api_key):
        self.client = db.Historical(api_key)
        self.symbol_cache = {}

        # Strategy parameters
        self.min_bid_size = 50
        self.min_pressure_ratio = 2.0
        self.hold_hours = 4  # Hold for 4 hours (more realistic than 24)

        # Results tracking
        self.all_trades = []
        self.daily_results = []

    def get_available_dates(self):
        """Check what dates have data available"""
        print("🔍 Checking available data dates...")

        # Check recent dates to find available data
        test_dates = []
        current = datetime(2025, 6, 15)  # Start a few days back

        for i in range(10):  # Check 10 days
            test_date = current + timedelta(days=i)
            test_dates.append(test_date.strftime("%Y-%m-%d"))

        available_dates = []

        for date_str in test_dates:
            try:
                # Quick test for data availability
                result = self.client.metadata.get_dataset_condition(
                    dataset="GLBX.MDP3",
                    start_date=date_str,
                    end_date=date_str
                )

                if result and len(result) > 0 and result[0].get('condition') == 'available':
                    available_dates.append(date_str)
                    print(f"   ✅ {date_str}: Available")
                else:
                    print(f"   ❌ {date_str}: Not available")

            except Exception as e:
                print(f"   ⚠️  {date_str}: Error checking - {e}")

        return available_dates

    def resolve_symbols_batch(self, instrument_ids, target_date):
        """Resolve instrument IDs to symbols"""
        if not instrument_ids:
            return {}

        try:
            target = datetime.strptime(target_date, "%Y-%m-%d")
            start_date = (target - timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = (target + timedelta(days=1)).strftime("%Y-%m-%d")

            resolution_result = self.client.symbology.resolve(
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

            self.symbol_cache.update(symbol_map)
            return symbol_map

        except Exception as e:
            print(f"   ⚠️  Symbol resolution error: {e}")
            return {}

    def parse_option_symbol(self, symbol):
        """Parse NQ option symbol to extract components"""
        try:
            if 'C' in symbol or 'P' in symbol:
                if 'C' in symbol:
                    parts = symbol.split('C')
                    option_type = 'Call'
                    direction = 'LONG'
                else:
                    parts = symbol.split('P')
                    option_type = 'Put'
                    direction = 'SHORT'

                if len(parts) == 2:
                    underlying_exp = parts[0].strip()
                    strike = int(parts[1].strip())

                    if underlying_exp.startswith('NQ'):
                        return {
                            'underlying': underlying_exp[:2],
                            'type': option_type,
                            'strike': strike,
                            'direction': direction
                        }
        except:
            pass

        return None

    def get_nq_price_range(self, start_time, end_time):
        """Get NQ futures price for entry and exit"""
        try:
            nq_data = self.client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQM5"],  # June 2025 contract
                schema="mbp-1",
                start=start_time,
                end=end_time
            )

            prices = []
            for record in nq_data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    mid_price = (level.bid_px + level.ask_px) / 2 / 1e9
                    prices.append({
                        'timestamp': record.ts_event / 1e9,
                        'price': mid_price
                    })

            if len(prices) >= 2:
                return prices[0]['price'], prices[-1]['price']  # Entry, Exit
            elif len(prices) == 1:
                return prices[0]['price'], prices[0]['price']
            else:
                return None, None

        except Exception as e:
            print(f"   ⚠️  Error getting NQ prices: {e}")
            return None, None

    def analyze_single_day(self, date_str):
        """Analyze institutional flow for a single day"""
        print(f"\n📊 Analyzing {date_str}")
        print("-" * 40)

        # Define trading sessions (multiple windows per day)
        sessions = [
            ("09:30", "11:30"),  # Morning session
            ("13:00", "15:00"),  # Afternoon session
            ("15:30", "16:00")   # Close session
        ]

        day_trades = []

        for session_start, session_end in sessions:
            start_time = f"{date_str}T{session_start}:00"
            end_time = f"{date_str}T{session_end}:00"

            print(f"   🕐 Session: {session_start} - {session_end}")

            try:
                # Get options data for this session
                data = self.client.timeseries.get_range(
                    dataset="GLBX.MDP3",
                    symbols=["NQ.OPT"],
                    schema="mbp-1",
                    start=start_time,
                    end=end_time,
                    stype_in="parent"
                )

                # Collect institutional signals
                signals = []
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

                        if bid_size >= self.min_bid_size and pressure_ratio >= self.min_pressure_ratio:
                            signals.append({
                                'instrument_id': record.instrument_id,
                                'timestamp': record.ts_event / 1e9,
                                'bid_size': bid_size,
                                'pressure_ratio': pressure_ratio
                            })
                            instrument_ids.add(record.instrument_id)

                print(f"      📈 Processed: {processed_count:,} quotes")
                print(f"      🎯 Signals: {len(signals)}")

                if not signals:
                    print(f"      📭 No institutional flow detected")
                    continue

                # Resolve symbols for this batch
                symbol_map = self.resolve_symbols_batch(list(instrument_ids), date_str)

                # Analyze flow direction
                call_signals = []
                put_signals = []

                for signal in signals:
                    symbol = symbol_map.get(signal['instrument_id'])
                    if symbol:
                        parsed = self.parse_option_symbol(symbol)
                        if parsed:
                            signal['symbol'] = symbol
                            signal['parsed'] = parsed

                            if parsed['type'] == 'Call':
                                call_signals.append(signal)
                            else:
                                put_signals.append(signal)

                # Generate trades based on flow
                if call_signals:
                    # Bullish flow detected - go LONG
                    avg_strike = sum(s['parsed']['strike'] for s in call_signals) / len(call_signals)
                    total_volume = sum(s['bid_size'] for s in call_signals)

                    # Get NQ prices for P&L
                    entry_price, exit_price = self.get_nq_price_range(start_time, end_time)

                    if entry_price and exit_price:
                        pnl_points = exit_price - entry_price
                        pnl_dollars = pnl_points * 20  # NQ multiplier

                        trade = {
                            'date': date_str,
                            'session': f"{session_start}-{session_end}",
                            'type': 'CALL_FLOW',
                            'direction': 'LONG',
                            'signal_count': len(call_signals),
                            'total_volume': total_volume,
                            'avg_strike': avg_strike,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl_points': pnl_points,
                            'pnl_dollars': pnl_dollars
                        }

                        day_trades.append(trade)
                        print(f"      🐂 LONG: {len(call_signals)} call signals, avg strike ${avg_strike:.0f}")
                        print(f"         Entry: ${entry_price:.2f} → Exit: ${exit_price:.2f}")
                        print(f"         P&L: {pnl_points:+.2f} pts = ${pnl_dollars:+,.2f}")

                if put_signals:
                    # Bearish flow detected - go SHORT
                    avg_strike = sum(s['parsed']['strike'] for s in put_signals) / len(put_signals)
                    total_volume = sum(s['bid_size'] for s in put_signals)

                    # Get NQ prices for P&L
                    entry_price, exit_price = self.get_nq_price_range(start_time, end_time)

                    if entry_price and exit_price:
                        pnl_points = entry_price - exit_price  # Short P&L
                        pnl_dollars = pnl_points * 20

                        trade = {
                            'date': date_str,
                            'session': f"{session_start}-{session_end}",
                            'type': 'PUT_FLOW',
                            'direction': 'SHORT',
                            'signal_count': len(put_signals),
                            'total_volume': total_volume,
                            'avg_strike': avg_strike,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl_points': pnl_points,
                            'pnl_dollars': pnl_dollars
                        }

                        day_trades.append(trade)
                        print(f"      🐻 SHORT: {len(put_signals)} put signals, avg strike ${avg_strike:.0f}")
                        print(f"         Entry: ${entry_price:.2f} → Exit: ${exit_price:.2f}")
                        print(f"         P&L: {pnl_points:+.2f} pts = ${pnl_dollars:+,.2f}")

            except Exception as e:
                print(f"      ❌ Session error: {e}")
                continue

        return day_trades

    def run_comprehensive_backtest(self):
        """Run backtest on all available data"""

        print("🚀 COMPREHENSIVE INSTITUTIONAL FLOW BACKTEST")
        print("=" * 80)

        # Get available dates
        available_dates = self.get_available_dates()

        if not available_dates:
            print("❌ No available data found")
            return

        print(f"\n📅 Found {len(available_dates)} available days:")
        for date in available_dates:
            print(f"   • {date}")

        print(f"\n🎯 Strategy Parameters:")
        print(f"   • Min bid size: {self.min_bid_size}")
        print(f"   • Min pressure ratio: {self.min_pressure_ratio}")
        print(f"   • Hold period: {self.hold_hours} hours")

        # Run backtest on each day
        for date_str in available_dates:
            day_trades = self.analyze_single_day(date_str)
            self.all_trades.extend(day_trades)

            # Daily summary
            day_pnl = sum(trade['pnl_dollars'] for trade in day_trades)
            self.daily_results.append({
                'date': date_str,
                'trades': len(day_trades),
                'pnl': day_pnl
            })

            print(f"   📊 Day Summary: {len(day_trades)} trades, ${day_pnl:+,.2f} P&L")

        # Final results
        self.generate_final_report()

    def generate_final_report(self):
        """Generate comprehensive backtest report"""

        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE BACKTEST RESULTS")
        print("=" * 80)

        if not self.all_trades:
            print("❌ No trades generated")
            return

        # Calculate statistics
        total_trades = len(self.all_trades)
        total_pnl = sum(trade['pnl_dollars'] for trade in self.all_trades)
        winning_trades = [t for t in self.all_trades if t['pnl_dollars'] > 0]
        losing_trades = [t for t in self.all_trades if t['pnl_dollars'] <= 0]

        win_rate = len(winning_trades) / total_trades * 100
        avg_win = sum(t['pnl_dollars'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl_dollars'] for t in losing_trades) / len(losing_trades) if losing_trades else 0

        # Display results
        print(f"🎯 PERFORMANCE SUMMARY:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Total P&L: ${total_pnl:+,.2f}")
        print(f"   Average P&L per Trade: ${total_pnl/total_trades:+,.2f}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Average Winner: ${avg_win:+,.2f}")
        print(f"   Average Loser: ${avg_loss:+,.2f}")
        print(f"   Profit Factor: {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "N/A")

        # Trade type breakdown
        call_trades = [t for t in self.all_trades if t['type'] == 'CALL_FLOW']
        put_trades = [t for t in self.all_trades if t['type'] == 'PUT_FLOW']

        print(f"\n📈 TRADE BREAKDOWN:")
        print(f"   Call Flow Trades: {len(call_trades)} (${sum(t['pnl_dollars'] for t in call_trades):+,.2f})")
        print(f"   Put Flow Trades: {len(put_trades)} (${sum(t['pnl_dollars'] for t in put_trades):+,.2f})")

        # Daily results
        print(f"\n📅 DAILY RESULTS:")
        for day_result in self.daily_results:
            print(f"   {day_result['date']}: {day_result['trades']} trades, ${day_result['pnl']:+,.2f}")

        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"comprehensive_backtest_{timestamp}.json"

        with open(results_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_trades': total_trades,
                    'total_pnl': total_pnl,
                    'win_rate': win_rate,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'profit_factor': abs(avg_win/avg_loss) if avg_loss != 0 else None
                },
                'daily_results': self.daily_results,
                'all_trades': self.all_trades
            }, f, indent=2)

        print(f"\n📁 Detailed results saved to: {results_file}")

        # Final verdict
        if total_pnl > 0:
            print(f"\n🎉 STRATEGY IS PROFITABLE! +${total_pnl:,.2f} across {total_trades} trades")
        else:
            print(f"\n📉 Strategy shows loss: ${total_pnl:,.2f} across {total_trades} trades")

def main():
    """Run comprehensive backtesting"""

    api_key = os.getenv('DATABENTO_API_KEY')
    if not api_key:
        print("❌ DATABENTO_API_KEY not found")
        return

    backtester = ComprehensiveBacktester(api_key)
    backtester.run_comprehensive_backtest()

if __name__ == "__main__":
    main()
