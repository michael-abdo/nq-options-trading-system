#!/usr/bin/env python3
"""
Working approach: Fix date range and try multiple methods to get symbol mappings
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import databento as db

# Load environment variables
load_dotenv()

def test_working_symbol_resolution():
    """Test multiple approaches to get working symbol resolution"""

    print("🔍 TESTING WORKING SYMBOL RESOLUTION APPROACHES")
    print("=" * 80)

    # Initialize Databento client
    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Get sample instrument IDs first
    print("📊 Step 1: Get sample instrument IDs...")

    data = client.timeseries.get_range(
        dataset="GLBX.MDP3",
        symbols=["NQ.OPT"],
        schema="mbp-1",
        start="2025-06-17T14:30:00",
        end="2025-06-17T14:31:00",
        stype_in="parent"
    )

    instrument_ids = []
    for record in data:
        if hasattr(record, 'levels') and len(record.levels) > 0:
            instrument_ids.append(str(record.instrument_id))
            if len(instrument_ids) >= 5:  # Just get first 5
                break

    print(f"✅ Found sample IDs: {instrument_ids}")

    # Method 1: Fix date range for symbology resolution
    print("\n🔄 Method 1: Symbology resolution with correct date range...")
    try:
        resolution_result = client.symbology.resolve(
            dataset="GLBX.MDP3",
            symbols=instrument_ids,
            stype_in="instrument_id",
            stype_out="raw_symbol",
            start_date="2025-06-16",  # Day before
            end_date="2025-06-18"     # Day after
        )

        print("✅ Symbology resolution successful!")
        if 'result' in resolution_result:
            mappings = resolution_result['result']
            print(f"📋 MAPPINGS FOUND:")
            for instrument_id, mapping_list in mappings.items():
                if mapping_list:
                    symbol = mapping_list[0].get('s', 'UNKNOWN')
                    date_range = f"{mapping_list[0].get('d0', 'N/A')} to {mapping_list[0].get('d1', 'N/A')}"
                    print(f"  {instrument_id} → {symbol} ({date_range})")

            if mappings:
                return True, mappings

    except Exception as e:
        print(f"❌ Method 1 failed: {e}")

    # Method 2: Try definition schema at midnight
    print("\n🔄 Method 2: Definition schema at UTC midnight...")
    try:
        def_data = client.timeseries.get_range(
            dataset="GLBX.MDP3",
            symbols=["NQ.OPT"],
            schema="definition",
            start="2025-06-17T00:00:00",  # UTC midnight
            end="2025-06-17T23:59:59",
            stype_in="parent"
        )

        def_count = 0
        symbol_map = {}

        for record in def_data:
            def_count += 1
            # Look for symbol-related attributes
            if hasattr(record, 'instrument_id'):
                instrument_id = record.instrument_id

                # Check various symbol attributes
                for attr in ['symbol', 'raw_symbol', 'stype_out_symbol']:
                    if hasattr(record, attr):
                        symbol = getattr(record, attr)
                        symbol_map[instrument_id] = str(symbol)
                        print(f"✅ Definition mapping: {instrument_id} → {symbol}")
                        break

            if def_count >= 100:  # Limit for testing
                break

        print(f"📊 Definition records processed: {def_count}")
        if symbol_map:
            return True, symbol_map

    except Exception as e:
        print(f"❌ Method 2 failed: {e}")

    # Method 3: Try to get symbol from record attributes after symbology insert
    print("\n🔄 Method 3: Enhanced symbology insertion...")
    try:
        # Get fresh data
        fresh_data = client.timeseries.get_range(
            dataset="GLBX.MDP3",
            symbols=["NQ.OPT"],
            schema="mbp-1",
            start="2025-06-17T14:30:00",
            end="2025-06-17T14:31:00",
            stype_in="parent"
        )

        # Try symbology request and insertion
        symbology = fresh_data.request_symbology(client)
        print(f"📊 Symbology data type: {type(symbology)}")
        print(f"📊 Symbology content preview: {str(symbology)[:200]}...")

        fresh_data.insert_symbology_json(symbology, clear_existing=True)

        # Check if symbols are now available
        symbol_map = {}
        for record in fresh_data:
            if hasattr(record, 'levels') and len(record.levels) > 0:
                instrument_id = record.instrument_id

                # Check all possible symbol attributes
                for attr in ['symbol', 'raw_symbol', 'stype_out_symbol', 'pretty_symbol']:
                    if hasattr(record, attr):
                        symbol = getattr(record, attr)
                        if not str(symbol).startswith('UNMAPPED'):
                            symbol_map[instrument_id] = str(symbol)
                            print(f"✅ Enhanced mapping: {instrument_id} → {symbol}")
                            break

                if len(symbol_map) >= 5:
                    break

        if symbol_map:
            return True, symbol_map

    except Exception as e:
        print(f"❌ Method 3 failed: {e}")

    # Method 4: Use known NQ option format and reverse engineer
    print("\n🔄 Method 4: Price-based symbol inference...")
    try:
        # Get current NQ futures price for context
        nq_data = client.timeseries.get_range(
            dataset="GLBX.MDP3",
            symbols=["NQ"],  # NQ futures
            schema="mbp-1",
            start="2025-06-17T14:30:00",
            end="2025-06-17T14:31:00"
        )

        nq_price = None
        for record in nq_data:
            if hasattr(record, 'levels') and len(record.levels) > 0:
                level = record.levels[0]
                nq_price = (level.bid_px + level.ask_px) / 2 / 1e9  # Average in dollars
                break

        print(f"📊 Current NQ futures price: ${nq_price:.2f}" if nq_price else "❌ Could not get NQ price")

        # Now infer option strikes from option prices
        inferred_map = {}
        for record in data:
            if hasattr(record, 'levels') and len(record.levels) > 0:
                level = record.levels[0]
                option_price = (level.bid_px + level.ask_px) / 2 / 1e9

                # Infer likely strike based on option price and underlying price
                if nq_price and option_price > 0:
                    # For calls: strike ≈ underlying_price - option_price (rough estimate)
                    # For puts: strike ≈ underlying_price + option_price (rough estimate)

                    estimated_call_strike = round((nq_price - option_price) / 100) * 100
                    estimated_put_strike = round((nq_price + option_price) / 100) * 100

                    # Choose more likely one based on option price
                    if option_price < nq_price * 0.1:  # Low premium suggests OTM call
                        inferred_symbol = f"NQ_CALL_{int(estimated_call_strike)}"
                    else:  # Higher premium suggests ITM or put
                        inferred_symbol = f"NQ_PUT_{int(estimated_put_strike)}"

                    inferred_map[record.instrument_id] = inferred_symbol
                    print(f"🎯 Inferred: {record.instrument_id} → {inferred_symbol} (price: ${option_price:.2f})")

        if inferred_map:
            return True, inferred_map

    except Exception as e:
        print(f"❌ Method 4 failed: {e}")

    return False, {}

if __name__ == "__main__":
    success, symbol_map = test_working_symbol_resolution()

    if success:
        print(f"\n🎉 SUCCESS: Found {len(symbol_map)} symbol mappings!")
        print("📋 Ready to integrate into quote pressure monitor")
    else:
        print("\n❌ All methods failed - may need direct Databento support")
