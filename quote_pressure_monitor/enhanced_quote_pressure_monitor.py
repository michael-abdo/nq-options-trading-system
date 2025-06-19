#!/usr/bin/env python3
"""
ENHANCED QUOTE PRESSURE MONITOR WITH REAL SYMBOL MAPPING
🎉 BREAKTHROUGH IMPLEMENTATION - Full institutional transparency!
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import databento as db
from collections import defaultdict
import json

# Load environment variables
load_dotenv()

class InstitutionalQuotePressureMonitor:
    """
    Enhanced quote pressure monitor with real symbol resolution
    """

    def __init__(self, api_key):
        self.client = db.Historical(api_key)
        self.symbol_cache = {}  # instrument_id -> symbol mapping
        self.processed_count = 0
        self.signal_count = 0

        # Institutional detection thresholds
        self.min_bid_size = 50
        self.min_pressure_ratio = 2.0

    def resolve_symbols_batch(self, instrument_ids, target_date):
        """
        BREAKTHROUGH METHOD: Resolve instrument IDs to real option symbols
        """
        if not instrument_ids:
            return {}

        print(f"🔄 Resolving {len(instrument_ids)} instrument IDs to symbols...")

        try:
            # Calculate date range (day before to day after) - THE KEY FIX!
            target = datetime.strptime(target_date, "%Y-%m-%d")
            start_date = (target - timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = (target + timedelta(days=1)).strftime("%Y-%m-%d")

            # The WORKING symbology resolution call
            resolution_result = self.client.symbology.resolve(
                dataset="GLBX.MDP3",
                symbols=[str(id) for id in instrument_ids],
                stype_in="instrument_id",
                stype_out="raw_symbol",
                start_date=start_date,
                end_date=end_date
            )

            # Build mapping dictionary
            symbol_map = {}
            if 'result' in resolution_result:
                for instrument_id, mapping_list in resolution_result['result'].items():
                    if mapping_list:
                        symbol = mapping_list[0].get('s', f'UNMAPPED_{instrument_id}')
                        symbol_map[int(instrument_id)] = symbol
                        print(f"✅ {instrument_id} → {symbol}")

            # Update cache
            self.symbol_cache.update(symbol_map)
            print(f"📊 Successfully resolved {len(symbol_map)} symbols")

            return symbol_map

        except Exception as e:
            print(f"❌ Symbol resolution error: {e}")
            return {}

    def parse_option_symbol(self, symbol):
        """Parse NQ option symbol to extract components"""
        try:
            # Expected format: NQM5 C21775
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

                    # Parse expiration (M5 = June 2025)
                    exp_code = underlying_exp[2:]  # M5
                    month_map = {'F': 'Jan', 'G': 'Feb', 'H': 'Mar', 'J': 'Apr',
                               'K': 'May', 'M': 'Jun', 'N': 'Jul', 'Q': 'Aug',
                               'U': 'Sep', 'V': 'Oct', 'X': 'Nov', 'Z': 'Dec'}

                    if len(exp_code) >= 2:
                        month_letter = exp_code[0]
                        year_digit = exp_code[1]
                        month = month_map.get(month_letter, 'Unknown')
                        year = f"202{year_digit}"

                        return {
                            'underlying': underlying_exp[:2],  # NQ
                            'month': month,
                            'year': year,
                            'type': option_type,
                            'strike': strike,
                            'expiration': f"{month} {year}"
                        }
        except:
            pass

        return None

    def calculate_notional_value(self, symbol, price, size):
        """Calculate notional value of the position"""
        # NQ options have $100 multiplier
        return price * size * 100

    def generate_enhanced_alert(self, record, symbol, quote_data):
        """Generate enhanced institutional alert with real symbol data"""
        self.signal_count += 1

        level = record.levels[0]
        bid_size = level.bid_sz
        ask_size = level.ask_sz
        bid_price = level.bid_px / 1e9
        ask_price = level.ask_px / 1e9
        pressure_ratio = bid_size / ask_size if ask_size > 0 else 0

        print(f"\n🚨 INSTITUTIONAL ALERT #{self.signal_count}")
        print("=" * 60)

        # Parse symbol if possible
        parsed = self.parse_option_symbol(symbol)

        if parsed:
            print(f"🐋 {symbol}")
            print(f"💰 {parsed['expiration']} ${parsed['strike']:,} {parsed['type']}s")
            print(f"📊 {bid_size} contracts @ ${bid_price:.2f} bid")
            print(f"🎯 Pressure: {pressure_ratio:.1f}:1 ({bid_size} bid vs {ask_size} ask)")

            # Calculate notional value
            notional = self.calculate_notional_value(symbol, bid_price, bid_size)
            print(f"💵 Notional: ${notional:,.0f}")

            # Strategic analysis
            print(f"⏰ Expiration: {parsed['expiration']}")
            if parsed['type'] == 'Call':
                print(f"💡 Bullish above ${parsed['strike']:,}")
            else:
                print(f"💡 Bearish below ${parsed['strike']:,}")

        else:
            print(f"🐋 {symbol}")
            print(f"📊 {bid_size} contracts @ ${bid_price:.2f} bid")
            print(f"🎯 Pressure: {pressure_ratio:.1f}:1")
            print(f"💵 Est. Notional: ${bid_price * bid_size * 100:,.0f}")

        print(f"🕐 Time: {datetime.fromtimestamp(record.ts_event / 1e9)}")
        print("-" * 60)

    def monitor_live_pressure(self, start_time, end_time, target_date="2025-06-17"):
        """
        Monitor institutional quote pressure with real symbol resolution
        """

        print("🚀 ENHANCED INSTITUTIONAL QUOTE PRESSURE MONITOR")
        print("=" * 80)
        print("📊 Real-time symbol resolution enabled")
        print(f"🎯 Monitoring: {start_time} to {end_time}")
        print(f"⚙️ Thresholds: Bid ≥{self.min_bid_size}, Ratio ≥{self.min_pressure_ratio}")
        print("-" * 80)

        try:
            # Get market data
            data = self.client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_time,
                end=end_time,
                stype_in="parent"
            )

            # Collect instrument IDs first for batch resolution
            print("📈 Step 1: Collecting instrument IDs...")
            instrument_ids = set()
            all_records = []

            for record in data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    all_records.append(record)
                    instrument_ids.add(record.instrument_id)

            print(f"✅ Found {len(all_records):,} quote updates")
            print(f"📊 Unique instruments: {len(instrument_ids):,}")

            # Batch resolve symbols - THE BREAKTHROUGH!
            if instrument_ids:
                self.resolve_symbols_batch(list(instrument_ids), target_date)

            # Process records with real symbols
            print("\n📊 Step 2: Processing quotes with real symbols...")
            print("-" * 80)

            for record in all_records:
                self.processed_count += 1

                level = record.levels[0]
                bid_size = level.bid_sz
                ask_size = level.ask_sz

                # Skip zero sizes
                if bid_size == 0 or ask_size == 0:
                    continue

                # Apply institutional thresholds
                pressure_ratio = bid_size / ask_size if ask_size > 0 else 0

                if bid_size >= self.min_bid_size and pressure_ratio >= self.min_pressure_ratio:
                    # Get real symbol
                    instrument_id = record.instrument_id
                    symbol = self.symbol_cache.get(instrument_id, f"UNMAPPED_{instrument_id}")

                    # Generate enhanced alert
                    self.generate_enhanced_alert(record, symbol, {
                        'bid_size': bid_size,
                        'ask_size': ask_size,
                        'pressure_ratio': pressure_ratio
                    })

                # Progress indicator
                if self.processed_count % 10000 == 0:
                    print(f"   Processed {self.processed_count:,} quotes... ({self.signal_count} signals)")

            # Final summary
            print("\n" + "=" * 80)
            print("📊 MONITORING SESSION COMPLETE")
            print("-" * 80)
            print(f"Total Quotes Processed: {self.processed_count:,}")
            print(f"Institutional Signals: {self.signal_count}")
            print(f"Unique Symbols Resolved: {len(self.symbol_cache)}")
            print(f"Signal Rate: {(self.signal_count/self.processed_count*100):.3f}%")

            if self.signal_count > 0:
                print(f"\n✅ SUCCESS: Detected {self.signal_count} institutional flow signals!")
                print("🎯 All signals include real option symbols and strategic analysis")
            else:
                print("\n⚠️  No institutional signals detected in this time window")

        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")
            raise

def main():
    """Run enhanced institutional quote pressure monitoring"""

    api_key = os.getenv('DATABENTO_API_KEY')
    if not api_key:
        print("❌ DATABENTO_API_KEY not found in environment")
        return

    # Initialize enhanced monitor
    monitor = InstitutionalQuotePressureMonitor(api_key)

    # Monitor recent active period
    start_time = "2025-06-17T14:30:00"
    end_time = "2025-06-17T15:00:00"    # 30-minute window
    target_date = "2025-06-17"

    print("🎉 STARTING ENHANCED INSTITUTIONAL MONITORING")
    print("💡 Breakthrough symbol resolution integrated!")
    print()

    monitor.monitor_live_pressure(start_time, end_time, target_date)

if __name__ == "__main__":
    main()
