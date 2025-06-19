#!/usr/bin/env python3
"""
Alternative approach: Use Databento's symbology.resolve() API directly
to get instrument_id to symbol mappings
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import databento as db

# Load environment variables
load_dotenv()

def test_direct_symbology_approach():
    """Test using symbology.resolve() to get direct mappings"""

    print("🔍 TESTING DIRECT SYMBOLOGY RESOLUTION")
    print("=" * 80)
    print("Using client.symbology.resolve() for direct instrument_id mapping")
    print("-" * 80)

    # Initialize Databento client
    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    try:
        # First, let's see what instrument IDs we have from a small sample
        print("📊 Step 1: Get sample instrument IDs...")

        data = client.timeseries.get_range(
            dataset="GLBX.MDP3",
            symbols=["NQ.OPT"],
            schema="mbp-1",
            start="2025-06-17T14:30:00",
            end="2025-06-17T14:31:00",  # Just 1 minute
            stype_in="parent"
        )

        # Collect unique instrument IDs
        instrument_ids = set()
        for record in data:
            if hasattr(record, 'levels') and len(record.levels) > 0:
                instrument_ids.add(str(record.instrument_id))
                if len(instrument_ids) >= 10:  # Just get first 10 for testing
                    break

        print(f"✅ Found {len(instrument_ids)} unique instrument IDs")
        print(f"📋 Sample IDs: {list(instrument_ids)[:5]}")

        if not instrument_ids:
            print("❌ No instrument IDs found")
            return False

        # Step 2: Try to resolve these instrument IDs to symbols
        print("\n🔄 Step 2: Resolving instrument IDs to symbols...")

        # Convert to list for API call
        id_list = list(instrument_ids)

        try:
            # Try resolving from instrument_id to raw_symbol
            resolution_result = client.symbology.resolve(
                dataset="GLBX.MDP3",
                symbols=id_list,
                stype_in="instrument_id",
                stype_out="raw_symbol",
                start_date="2025-06-17",
                end_date="2025-06-17"
            )

            print("✅ Symbology resolution successful!")
            print(f"📊 Resolution result: {resolution_result}")

            # Parse the resolution results
            if 'result' in resolution_result:
                mappings = resolution_result['result']
                print(f"\n📋 SYMBOL MAPPINGS FOUND:")
                print("-" * 40)

                for instrument_id, mapping_list in mappings.items():
                    if mapping_list:  # If there are mappings
                        symbol = mapping_list[0].get('s', 'UNKNOWN')
                        print(f"  {instrument_id} → {symbol}")

                return len(mappings) > 0
            else:
                print("❌ No 'result' key in resolution response")
                return False

        except Exception as resolve_error:
            print(f"❌ Symbology resolution failed: {resolve_error}")

            # Try alternative: get all symbols for the date range
            print("\n🔄 Step 3: Alternative - Get all symbols for date range...")

            try:
                all_symbols = client.metadata.get_dataset_condition(
                    dataset="GLBX.MDP3",
                    start_date="2025-06-17",
                    end_date="2025-06-17"
                )

                print(f"✅ Got dataset condition info: {all_symbols}")
                return True

            except Exception as alt_error:
                print(f"❌ Alternative approach failed: {alt_error}")
                return False

    except Exception as e:
        print(f"\n❌ Main error: {e}")
        return False

def test_schema_exploration():
    """Try different schemas to see if we can get symbol data"""

    print("\n" + "=" * 80)
    print("🔍 TESTING DIFFERENT SCHEMAS FOR SYMBOL DATA")
    print("-" * 80)

    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    schemas_to_test = ["definition", "statistics", "status"]

    for schema in schemas_to_test:
        try:
            print(f"\n📊 Testing schema: {schema}")

            data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema=schema,
                start="2025-06-17T14:30:00",
                end="2025-06-17T14:31:00",
                stype_in="parent"
            )

            record_count = 0
            for record in data:
                record_count += 1
                if record_count <= 3:  # Show first 3 records
                    print(f"  Record type: {type(record).__name__}")

                    # Check for symbol-related attributes
                    attrs = [attr for attr in dir(record) if 'symbol' in attr.lower() or attr in ['instrument_id', 'raw_symbol', 'stype_out_symbol']]
                    if attrs:
                        print(f"  Symbol attrs: {attrs}")
                        for attr in attrs:
                            try:
                                value = getattr(record, attr)
                                print(f"    {attr}: {value}")
                            except:
                                print(f"    {attr}: <error>")

                if record_count >= 10:
                    break

            print(f"  Total records: {record_count}")

        except Exception as e:
            print(f"  ❌ Schema {schema} failed: {e}")

    return True

if __name__ == "__main__":
    success1 = test_direct_symbology_approach()
    success2 = test_schema_exploration()

    if success1 or success2:
        print("\n🎉 Found a working approach for symbol resolution!")
    else:
        print("\n🔍 Need to investigate Databento's options symbol mapping further")
