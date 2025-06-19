#!/usr/bin/env python3
"""
SOLUTION: Test the correct way to get symbol mappings from Databento
Using request_symbology() and insert_symbology_json() as documented
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import databento as db

# Load environment variables
load_dotenv()

def test_correct_symbol_resolution():
    """Test the documented Databento method for symbol resolution"""

    print("🔍 TESTING CORRECT SYMBOL RESOLUTION METHOD")
    print("=" * 80)
    print("Using Databento's request_symbology() + insert_symbology_json()")
    print("-" * 80)

    # Initialize Databento client
    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Use focused time window
    start_date = "2025-06-17T14:30:00"
    end_date = "2025-06-17T14:35:00"

    print(f"📊 Testing with data: {start_date} to {end_date}")
    print()

    try:
        # Step 1: Get the data (will have instrument_ids only)
        print("📈 Step 1: Requesting market data...")
        data = client.timeseries.get_range(
            dataset="GLBX.MDP3",
            symbols=["NQ.OPT"],  # Parent symbol for all NQ options
            schema="mbp-1",
            start=start_date,
            end=end_date,
            stype_in="parent"
        )

        print("✅ Market data received")

        # Step 2: Request symbology mappings
        print("🔄 Step 2: Requesting symbology mappings...")
        symbology = data.request_symbology(client)
        print("✅ Symbology data received")

        # Step 3: Insert symbology into data
        print("🔧 Step 3: Inserting symbology into data...")
        data.insert_symbology_json(symbology)
        print("✅ Symbology inserted")

        # Step 4: Test the mapping
        print("\n" + "=" * 80)
        print("🎯 TESTING SYMBOL RESOLUTION:")
        print("-" * 80)

        symbol_map = {}
        quote_samples = []

        for record in data:
            if hasattr(record, 'levels') and len(record.levels) > 0:
                instrument_id = record.instrument_id

                # Check if symbol attribute now exists
                symbol = getattr(record, 'symbol', f"UNMAPPED_{instrument_id}")
                symbol_map[instrument_id] = symbol

                # Collect sample quotes with symbols
                if len(quote_samples) < 5:
                    level = record.levels[0]
                    quote_samples.append({
                        'instrument_id': instrument_id,
                        'symbol': symbol,
                        'bid_size': level.bid_sz,
                        'ask_size': level.ask_sz,
                        'bid_price': level.bid_px / 1e9,
                        'ask_price': level.ask_px / 1e9
                    })

        print(f"📊 Total unique symbols mapped: {len(symbol_map)}")
        print()

        if symbol_map:
            print("✅ SUCCESS: Symbol mapping working!")
            print("-" * 40)
            print("📋 Sample Symbol Mappings:")
            for i, (instrument_id, symbol) in enumerate(list(symbol_map.items())[:10]):
                print(f"  {instrument_id} → {symbol}")

            print("\n📈 Sample Quotes with Real Symbols:")
            print("-" * 40)
            for quote in quote_samples:
                print(f"🎯 {quote['symbol']}")
                print(f"   Bid: {quote['bid_size']} @ ${quote['bid_price']:.2f}")
                print(f"   Ask: {quote['ask_size']} @ ${quote['ask_price']:.2f}")

                # Parse symbol if it's a real option symbol
                if not quote['symbol'].startswith('UNMAPPED_'):
                    symbol_parts = parse_option_symbol(quote['symbol'])
                    if symbol_parts:
                        print(f"   📋 Parsed: {symbol_parts}")
                print()

        else:
            print("❌ No symbols mapped - investigating further...")

            # Check what attributes are available after symbology insertion
            sample_record = next(iter(data))
            print(f"📋 Available attributes after symbology: {[attr for attr in dir(sample_record) if not attr.startswith('_')]}")

        return len(symbol_map) > 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"Error type: {type(e)}")
        return False

def parse_option_symbol(symbol):
    """Parse option symbol to extract components"""
    try:
        # Expected format: NQM25 C21000 or similar
        if 'C' in symbol or 'P' in symbol:
            # Find call/put indicator
            if 'C' in symbol:
                parts = symbol.split('C')
                option_type = 'Call'
            else:
                parts = symbol.split('P')
                option_type = 'Put'

            if len(parts) == 2:
                underlying_exp = parts[0].strip()
                strike = parts[1].strip()

                return {
                    'underlying': underlying_exp[:2],  # NQ
                    'expiration': underlying_exp[2:],  # M25
                    'type': option_type,
                    'strike': strike
                }
    except:
        pass

    return None

if __name__ == "__main__":
    success = test_correct_symbol_resolution()

    if success:
        print("\n🎉 BREAKTHROUGH: We can now map instrument_ids to real symbols!")
        print("🔧 Next: Integrate this into our quote pressure monitor")
    else:
        print("\n🔍 Need to investigate alternative approaches or API limitations")
