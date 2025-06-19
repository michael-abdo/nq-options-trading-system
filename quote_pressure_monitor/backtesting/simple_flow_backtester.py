#!/usr/bin/env python3
"""
SIMPLE INSTITUTIONAL FLOW BACKTESTER
====================================

Strategy: If institutional flow detected, buy underlying in direction at average strike price

Rules:
1. Detect institutional calls → Go LONG NQ futures at average call strike
2. Detect institutional puts → Go SHORT NQ futures at average put strike
3. Hold for configurable time period
4. Calculate P&L vs simple buy-and-hold

Keep it EXTREMELY simple - just track entries, exits, and P&L
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

class SimpleFlowBacktester:
    """
    Super simple backtester - track institutional flow and calculate basic P&L
    """

    def __init__(self, api_key):
        self.client = db.Historical(api_key)
        self.symbol_cache = {}

        # Strategy parameters
        self.min_bid_size = 50
        self.min_pressure_ratio = 2.0
        self.hold_hours = 24  # Hold for 24 hours

        # Tracking
        self.positions = []
        self.current_signals = []
        self.nq_prices = {}  # timestamp -> NQ price

    def resolve_symbols_batch(self, instrument_ids, target_date):
        """Resolve instrument IDs to symbols (from main script)"""
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
            print(f"❌ Symbol resolution error: {e}")
            return {}

    def parse_option_symbol(self, symbol):
        """Parse NQ option symbol to extract components"""
        try:
            if 'C' in symbol or 'P' in symbol:
                if 'C' in symbol:
                    parts = symbol.split('C')
                    option_type = 'Call'
                else:
                    parts = symbol.split('P')
                    option_type = 'Put'

                if len(parts) == 2:
                    underlying_exp = parts[0].strip()
                    strike = int(parts[1].strip())

                    return {
                        'underlying': underlying_exp[:2],  # NQ
                        'type': option_type,
                        'strike': strike,
                        'direction': 'LONG' if option_type == 'Call' else 'SHORT'
                    }
        except:
            pass

        return None

    def get_nq_price(self, timestamp, date_str):
        """Get NQ futures price at specific timestamp"""
        if timestamp in self.nq_prices:
            return self.nq_prices[timestamp]

        try:
            # Get NQ futures price around this time
            time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%dT%H:%M:%S")
            start_time = (datetime.fromtimestamp(timestamp) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")
            end_time = (datetime.fromtimestamp(timestamp) + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")

            nq_data = self.client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ"],  # NQ futures
                schema="mbp-1",
                start=start_time,
                end=end_time
            )

            for record in nq_data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    nq_price = (level.bid_px + level.ask_px) / 2 / 1e9  # Mid price
                    self.nq_prices[timestamp] = nq_price
                    return nq_price

        except Exception as e:
            print(f"⚠️  Could not get NQ price at {timestamp}: {e}")

        return None

    def detect_institutional_signals(self, start_time, end_time, target_date):
        """
        Detect institutional flow and generate trading signals
        Returns: list of signals with direction and average strike
        """

        print(f"🔍 Detecting institutional flow: {start_time} to {end_time}")

        try:
            # Get options data
            data = self.client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_time,
                end=end_time,
                stype_in="parent"
            )

            # Collect instrument IDs and signals
            instrument_ids = set()
            raw_signals = []

            for record in data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    bid_size = level.bid_sz
                    ask_size = level.ask_sz

                    if bid_size == 0 or ask_size == 0:
                        continue

                    pressure_ratio = bid_size / ask_size

                    # Institutional flow detection
                    if bid_size >= self.min_bid_size and pressure_ratio >= self.min_pressure_ratio:
                        instrument_ids.add(record.instrument_id)

                        raw_signals.append({
                            'instrument_id': record.instrument_id,
                            'timestamp': record.ts_event / 1e9,
                            'bid_size': bid_size,
                            'ask_size': ask_size,
                            'pressure_ratio': pressure_ratio,
                            'bid_price': level.bid_px / 1e9,
                            'ask_price': level.ask_px / 1e9
                        })

            print(f"📊 Found {len(raw_signals)} institutional signals")

            if not raw_signals:
                print("   ⚠️  No institutional signals found - check thresholds")
                return []

            # Resolve symbols
            print("🔄 Resolving symbols...")
            self.resolve_symbols_batch(list(instrument_ids), target_date)

            # Process signals with real symbols
            processed_signals = []
            call_strikes = []
            put_strikes = []
            call_volume = 0
            put_volume = 0

            for signal in raw_signals:
                symbol = self.symbol_cache.get(signal['instrument_id'], 'UNKNOWN')
                parsed = self.parse_option_symbol(symbol)

                if parsed and parsed['underlying'] == 'NQ':
                    signal['symbol'] = symbol
                    signal['parsed'] = parsed
                    signal['strike'] = parsed['strike']
                    signal['type'] = parsed['type']
                    signal['direction'] = parsed['direction']

                    processed_signals.append(signal)

                    # Aggregate by type
                    if parsed['type'] == 'Call':
                        call_strikes.append(parsed['strike'])
                        call_volume += signal['bid_size']
                    else:
                        put_strikes.append(parsed['strike'])
                        put_volume += signal['bid_size']

            print(f"✅ Processed {len(processed_signals)} valid NQ option signals")

            # Generate trading signals
            trading_signals = []

            if call_strikes:
                avg_call_strike = sum(call_strikes) / len(call_strikes)
                trading_signals.append({
                    'direction': 'LONG',
                    'avg_strike': avg_call_strike,
                    'volume': call_volume,
                    'count': len(call_strikes),
                    'timestamp': processed_signals[0]['timestamp'],
                    'type': 'CALL_FLOW'
                })

            if put_strikes:
                avg_put_strike = sum(put_strikes) / len(put_strikes)
                trading_signals.append({
                    'direction': 'SHORT',
                    'avg_strike': avg_put_strike,
                    'volume': put_volume,
                    'count': len(put_strikes),
                    'timestamp': processed_signals[0]['timestamp'],
                    'type': 'PUT_FLOW'
                })

            return trading_signals

        except Exception as e:
            print(f"❌ Error detecting signals: {e}")
            return []

    def execute_backtest(self, start_date, end_date, time_window_hours=1):
        """
        Simple backtest: detect flow in time windows and track P&L
        """

        print("🚀 SIMPLE INSTITUTIONAL FLOW BACKTEST")
        print("=" * 60)
        print(f"📅 Period: {start_date} to {end_date}")
        print(f"⏰ Window: {time_window_hours} hour chunks")
        print(f"📊 Strategy: Follow institutional flow at average strikes")
        print("-" * 60)

        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        all_signals = []
        total_pnl = 0
        trade_count = 0

        while current < end:
            # Define time window (trading hours only)
            window_start = current.replace(hour=14, minute=30)  # 2:30 PM ET
            window_end = window_start + timedelta(hours=time_window_hours)

            if window_end.date() != current.date():
                # Don't cross midnight
                window_end = current.replace(hour=23, minute=59)

            date_str = current.strftime("%Y-%m-%d")
            start_str = window_start.strftime("%Y-%m-%dT%H:%M:%S")
            end_str = window_end.strftime("%Y-%m-%dT%H:%M:%S")

            print(f"\n📊 Analyzing {date_str} {window_start.strftime('%H:%M')} - {window_end.strftime('%H:%M')}")

            # Detect institutional signals
            signals = self.detect_institutional_signals(start_str, end_str, date_str)

            for signal in signals:
                print(f"🎯 {signal['type']}: {signal['direction']} at ${signal['avg_strike']:,.0f}")
                print(f"   Volume: {signal['volume']} contracts ({signal['count']} strikes)")

                # Get entry price (NQ futures at signal time)
                entry_price = self.get_nq_price(signal['timestamp'], date_str)

                if entry_price:
                    # Calculate theoretical exit after hold period
                    exit_time = signal['timestamp'] + (self.hold_hours * 3600)
                    exit_price = self.get_nq_price(exit_time, date_str)

                    if exit_price:
                        # Calculate P&L
                        if signal['direction'] == 'LONG':
                            pnl_points = exit_price - entry_price
                        else:
                            pnl_points = entry_price - exit_price

                        pnl_dollars = pnl_points * 20  # NQ multiplier
                        total_pnl += pnl_dollars
                        trade_count += 1

                        print(f"   📈 Entry: ${entry_price:,.2f} | Exit: ${exit_price:,.2f}")
                        print(f"   💰 P&L: {pnl_points:+.2f} pts = ${pnl_dollars:+,.2f}")

                        all_signals.append({
                            'date': date_str,
                            'type': signal['type'],
                            'direction': signal['direction'],
                            'avg_strike': signal['avg_strike'],
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl_points': pnl_points,
                            'pnl_dollars': pnl_dollars,
                            'volume': signal['volume']
                        })
                    else:
                        print(f"   ⚠️  Could not get exit price")
                else:
                    print(f"   ⚠️  Could not get entry price")

            if not signals:
                print("   📭 No institutional flow detected")

            # Move to next day
            current += timedelta(days=1)

        # Final summary
        print("\n" + "=" * 60)
        print("📊 BACKTEST RESULTS SUMMARY")
        print("-" * 60)
        print(f"Total Trades: {trade_count}")
        print(f"Total P&L: ${total_pnl:+,.2f}")
        print(f"Avg P&L per Trade: ${total_pnl/trade_count:+,.2f}" if trade_count > 0 else "No trades")
        print(f"Win Rate: {len([s for s in all_signals if s['pnl_dollars'] > 0])/len(all_signals)*100:.1f}%" if all_signals else "N/A")

        # Save results
        results_file = f"backtest_results_{start_date}_to_{end_date}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_trades': trade_count,
                    'total_pnl': total_pnl,
                    'avg_pnl': total_pnl/trade_count if trade_count > 0 else 0,
                    'win_rate': len([s for s in all_signals if s['pnl_dollars'] > 0])/len(all_signals) if all_signals else 0
                },
                'trades': all_signals
            }, f, indent=2)

        print(f"📁 Results saved to: {results_file}")

        return all_signals

def main():
    """Run simple institutional flow backtest"""

    api_key = os.getenv('DATABENTO_API_KEY')
    if not api_key:
        print("❌ DATABENTO_API_KEY not found")
        return

    backtester = SimpleFlowBacktester(api_key)

    # Test with recent date that we know has data
    start_date = "2025-06-17"
    end_date = "2025-06-17"  # Just one day for testing

    results = backtester.execute_backtest(start_date, end_date, time_window_hours=2)

    if results:
        print(f"\n🎉 Backtest complete! Found {len(results)} trades")
    else:
        print("\n⚠️  No trades generated - try different dates or adjust thresholds")

if __name__ == "__main__":
    main()
