#!/usr/bin/env python3
"""
Test hypothesis: Symbol mapping data is already in our stream but we're filtering it out
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import databento as db
from collections import defaultdict

# Load environment variables
load_dotenv()

def test_symbol_mapping_hypothesis():
    """Test if SymbolMappingMsg records are in our data stream"""

    print("🔍 TESTING SYMBOL MAPPING HYPOTHESIS")
    print("=" * 80)
    print("Theory: Symbol mapping data exists but we're filtering it out")
    print("-" * 80)

    # Initialize Databento client
    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Use smaller time window for focused testing
    start_date = "2025-06-17T14:30:00"
    end_date = "2025-06-17T14:35:00"  # Just 5 minutes

    print(f"📊 Testing with focused data: {start_date} to {end_date}")
    print()

    # Track all record types and their attributes
    record_types = defaultdict(int)
    symbol_mappings = {}
    sample_records = {}

    try:
        data = client.timeseries.get_range(
            dataset="GLBX.MDP3",
            symbols=["NQ.OPT"],
            schema="mbp-1",
            start=start_date,
            end=end_date,
            stype_in="parent"
        )

        print("🔄 Processing ALL record types (not just quotes)...")
        total_records = 0

        for record in data:
            total_records += 1
            record_type = type(record).__name__
            record_types[record_type] += 1

            # Store first sample of each record type
            if record_type not in sample_records:
                sample_records[record_type] = record

            # Look for symbol mapping specifically
            if hasattr(record, 'stype_out_symbol'):
                instrument_id = getattr(record, 'instrument_id', 'unknown')
                symbol = str(record.stype_out_symbol)
                symbol_mappings[instrument_id] = symbol
                print(f"✅ SYMBOL MAPPING FOUND: {instrument_id} → {symbol}")

            # Also check for other symbol-related attributes
            symbol_attrs = []
            for attr in ['symbol', 'raw_symbol', 'stype_out_symbol', 'stype_in_symbol']:
                if hasattr(record, attr):
                    symbol_attrs.append(f"{attr}={getattr(record, attr)}")

            if symbol_attrs and total_records <= 10:  # Show first 10 with symbol attrs
                print(f"📋 Record {total_records}: {record_type} - {', '.join(symbol_attrs)}")

            # Stop after reasonable sample to avoid timeout
            if total_records >= 10000:
                print(f"⏸️  Stopping after {total_records} records for analysis...")
                break

        print("\n" + "=" * 80)
        print("📊 RECORD TYPE ANALYSIS:")
        print("-" * 80)

        for record_type, count in sorted(record_types.items()):
            print(f"{record_type}: {count:,} records")

        print(f"\nTotal Records Processed: {total_records:,}")
        print(f"Symbol Mappings Found: {len(symbol_mappings)}")

        if symbol_mappings:
            print("\n✅ HYPOTHESIS CONFIRMED: Symbol mappings exist!")
            print("-" * 80)
            print("📋 Sample Symbol Mappings:")
            for instrument_id, symbol in list(symbol_mappings.items())[:10]:
                print(f"  {instrument_id} → {symbol}")
        else:
            print("\n❌ HYPOTHESIS PARTIALLY REJECTED: No stype_out_symbol found")
            print("-" * 80)
            print("🔍 Let's examine record attributes more deeply...")

            # Deep dive into record attributes
            for record_type, sample in sample_records.items():
                print(f"\n📋 {record_type} attributes:")
                attrs = [attr for attr in dir(sample) if not attr.startswith('_')]
                for attr in attrs[:10]:  # First 10 attributes
                    try:
                        value = getattr(sample, attr)
                        if not callable(value):
                            print(f"  {attr}: {str(value)[:50]}...")
                    except:
                        print(f"  {attr}: <error accessing>")

        print("\n" + "=" * 80)
        print("🎯 NEXT STEPS ANALYSIS:")
        print("-" * 80)

        if symbol_mappings:
            print("✅ SUCCESS: We can build the symbol dictionary!")
            print("📝 Implementation: Modify main script to capture these mappings")
        else:
            print("🔍 INVESTIGATION NEEDED: Check alternative approaches")
            print("📝 Options: Different schema, separate API call, or attribute names")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        print("\n🌐 Let me search for Databento symbol mapping documentation...")
        return False

    return len(symbol_mappings) > 0

if __name__ == "__main__":
    success = test_symbol_mapping_hypothesis()

    if not success:
        print("\n🔍 SEARCHING DATABENTO DOCUMENTATION...")
        print("Need to understand how symbol resolution works in Databento API")
