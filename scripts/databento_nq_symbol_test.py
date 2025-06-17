#!/usr/bin/env python3
"""
Test Different NQ Symbol Formats with Databento
Find the correct symbol to use for NQ futures
"""

import databento as db
import os
from datetime import date, timedelta

# API key from environment
api_key = os.getenv('DATABENTO_API_KEY')
if not api_key:
    print("❌ DATABENTO_API_KEY environment variable not set")
    exit(1)
dataset = 'GLBX.MDP3'

print("🔍 DATABENTO NQ SYMBOL FORMAT TEST")
print("="*50)

# Test different symbol formats
test_symbols = [
    'NQ.c.0',       # Continuous contract
    'NQ.FUT',       # Generic futures
    'NQZ4',         # December 2024 contract
    'NQH5',         # March 2025 contract
    'NQM5',         # June 2025 contract
    'NQU5',         # September 2025 contract
    'NQZ5',         # December 2025 contract
    'ESM5',         # S&P 500 for comparison
    'NQ1!',         # Front month
    'NQ'            # Base symbol
]

try:
    print("🔐 Creating historical client...")
    client = db.Historical(key=api_key)

    print("📊 Testing symbol availability...")

    for symbol in test_symbols:
        print(f"\n🧪 Testing symbol: {symbol}")

        try:
            # Try to get recent data
            yesterday = date.today() - timedelta(days=1)
            today = date.today()

            data = client.timeseries.get_range(
                dataset=dataset,
                symbols=[symbol],
                schema='trades',
                start=yesterday,
                end=today,
                limit=1
            )

            # Handle different data types
            if data is not None:
                # Convert DBNStore to DataFrame if possible
                try:
                    df = data.to_df()
                    if not df.empty:
                        price = df.iloc[0]['price'] / 1_000_000_000
                        print(f"✅ {symbol}: FOUND! Price: ${price:,.2f}")
                    else:
                        print(f"⚠️ {symbol}: No data (valid symbol but no recent trades)")
                except Exception as conv_error:
                    print(f"⚠️ {symbol}: Data found but conversion failed: {conv_error}")
            else:
                print(f"⚠️ {symbol}: No data returned")

        except Exception as e:
            error_msg = str(e)
            if "symbology_invalid_request" in error_msg:
                print(f"❌ {symbol}: Invalid symbol format")
            elif "422" in error_msg:
                print(f"⚠️ {symbol}: {error_msg}")
            else:
                print(f"❌ {symbol}: {error_msg}")

    # Try to get dataset info
    print(f"\n📋 Checking dataset information for {dataset}...")
    try:
        # Get dataset metadata
        datasets = client.metadata.list_datasets()
        glbx_datasets = [d for d in datasets if 'GLBX' in str(d)]

        print(f"✅ Found {len(glbx_datasets)} GLBX datasets:")
        for ds in glbx_datasets:
            print(f"   - {ds}")

    except Exception as e:
        print(f"❌ Dataset info failed: {e}")

    # Try to resolve symbols
    print(f"\n🔍 Trying symbol resolution...")
    try:
        # Try to resolve some symbols
        resolution_symbols = ['NQZ4', 'NQM5', 'NQU5']

        for symbol in resolution_symbols:
            try:
                resolved = client.symbology.resolve(
                    dataset=dataset,
                    symbols=[symbol],
                    stype_in='continuous',
                    stype_out='instrument_id'
                )
                print(f"✅ {symbol} resolved: {resolved}")
            except Exception as e:
                print(f"❌ {symbol} resolution failed: {e}")

    except Exception as e:
        print(f"❌ Symbol resolution failed: {e}")

    print(f"\n✅ Symbol test complete!")

except Exception as e:
    print(f"❌ Test failed: {e}")
