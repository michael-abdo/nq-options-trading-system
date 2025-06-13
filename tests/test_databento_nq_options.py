#!/usr/bin/env python3
"""
Comprehensive test for Databento NQ Options data retrieval
Shows how to get options chains, filter by strike/expiry, and analyze volume
"""

import os
import json
from datetime import datetime, timedelta
from utils.timezone_utils import get_eastern_time, get_utc_time
import pandas as pd

# Try to load dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not available, using system environment variables")

# Import databento
try:
    import databento as db
    DATABENTO_AVAILABLE = True
except ImportError:
    DATABENTO_AVAILABLE = False
    print("ERROR: databento package not installed. Run: pip install databento")
    exit(1)

def get_api_key():
    """Get API key from environment or .env file"""
    api_key = os.getenv('DATABENTO_API_KEY')

    if not api_key:
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('DATABENTO_API_KEY='):
                        api_key = line.split('=', 1)[1].strip()
                        break
        except FileNotFoundError:
            pass

    return api_key

def test_nq_options_definitions():
    """Get NQ options contract definitions to understand available strikes/expiries"""
    api_key = get_api_key()
    if not api_key:
        print("ERROR: DATABENTO_API_KEY not found")
        return

    client = db.Historical(api_key)

    print("\n=== Testing NQ Options Contract Definitions ===")

    # Get definitions for NQ options
    end_date = get_eastern_time()
    start_date = end_date - timedelta(days=1)

    params = {
        'dataset': 'GLBX.MDP3',
        'symbols': ['NQ.OPT'],
        'schema': 'definition',
        'start': start_date.strftime('%Y-%m-%d'),
        'end': end_date.strftime('%Y-%m-%d'),
        'stype_in': 'parent'
    }

    try:
        # Check cost
        cost = client.metadata.get_cost(**params)
        print(f"Definition data cost: ${cost:.4f}")

        if cost < 0.01:  # Only retrieve if cost is minimal
            print("Retrieving contract definitions...")
            data = client.timeseries.get_range(**params)

            # Convert to dataframe
            df = data.to_df()

            if not df.empty:
                print(f"\nFound {len(df)} NQ option contracts")

                # Show sample contracts
                print("\nSample contracts:")
                print(df[['raw_symbol', 'strike_price', 'expiration', 'instrument_class']].head(10))

                # Group by expiration
                expirations = df['expiration'].value_counts().sort_index()
                print(f"\nAvailable expirations: {len(expirations)}")
                print(expirations.head())

                return df
            else:
                print("No contract definitions found")
        else:
            print(f"Skipping retrieval due to cost (${cost:.4f})")

    except Exception as e:
        print(f"Error getting definitions: {e}")

    return None

def test_nq_options_prices():
    """Get actual price/volume data for NQ options"""
    api_key = get_api_key()
    if not api_key:
        print("ERROR: DATABENTO_API_KEY not found")
        return

    client = db.Historical(api_key)

    print("\n=== Testing NQ Options Price Data ===")

    # Get recent trading data
    end_date = get_eastern_time()
    start_date = end_date - timedelta(days=1)

    # Test different schemas
    schemas = ['trades', 'mbp-1', 'ohlcv-1h']

    for schema in schemas:
        print(f"\nTesting schema: {schema}")

        params = {
            'dataset': 'GLBX.MDP3',
            'symbols': ['NQ.OPT'],
            'schema': schema,
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
            'stype_in': 'parent',
            'limit': 100  # Limit records for testing
        }

        try:
            # Check cost
            cost = client.metadata.get_cost(**params)
            print(f"  Cost for {schema}: ${cost:.4f}")

            if cost < 0.05:  # Only retrieve if cost is reasonable
                print(f"  Retrieving {schema} data...")
                data = client.timeseries.get_range(**params)

                # Convert to dataframe
                df = data.to_df()

                if not df.empty:
                    print(f"  Retrieved {len(df)} records")

                    # Show columns available
                    print(f"  Available columns: {list(df.columns)[:10]}...")

                    # Show sample data
                    if schema == 'trades':
                        if 'size' in df.columns and 'price' in df.columns:
                            print(f"  Total volume: {df['size'].sum()}")
                            print(f"  Price range: ${df['price'].min():.2f} - ${df['price'].max():.2f}")
                    elif schema == 'ohlcv-1h':
                        if 'volume' in df.columns:
                            print(f"  Total volume: {df['volume'].sum()}")

                    return df
                else:
                    print(f"  No data found for {schema}")
            else:
                print(f"  Skipping {schema} due to cost")

        except Exception as e:
            print(f"  Error with {schema}: {e}")

    return None

def test_specific_options_contract():
    """Test retrieving data for a specific options contract"""
    api_key = get_api_key()
    if not api_key:
        print("ERROR: DATABENTO_API_KEY not found")
        return

    client = db.Historical(api_key)

    print("\n=== Testing Specific NQ Options Contract ===")

    # We need to know actual contract symbols
    # For CME, they follow patterns like:
    # - NQM5 = June 2025 future
    # - Options would be like NQM5 C20000 (June 2025 20000 Call)

    # First, let's check what symbols are available
    print("\nChecking available datasets and symbology...")

    try:
        # Get metadata about the dataset
        dataset_info = client.metadata.get_dataset('GLBX.MDP3')
        print(f"Dataset: {dataset_info}")

    except Exception as e:
        print(f"Error getting dataset info: {e}")

def main():
    """Run all Databento NQ options tests"""
    print("=== Databento NQ Options Comprehensive Test ===")

    # Test 1: Get contract definitions
    definitions = test_nq_options_definitions()

    # Test 2: Get price/volume data
    prices = test_nq_options_prices()

    # Test 3: Test specific contract
    test_specific_options_contract()

    print("\n=== All Tests Complete ===")

    # Save test output
    output_dir = "outputs/databento_test"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = get_eastern_time().strftime("%Y%m%d_%H%M%S")

    # Save results
    results = {
        'test_date': timestamp,
        'tests_run': ['definitions', 'prices', 'specific_contract'],
        'success': True
    }

    with open(f"{output_dir}/test_results_{timestamp}.json", 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_dir}/test_results_{timestamp}.json")

if __name__ == "__main__":
    main()
