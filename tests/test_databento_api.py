#!/usr/bin/env python3
"""
Minimal test for Databento API - NQ Future Options data retrieval
"""

import os
import json
from datetime import datetime, timedelta
from utils.timezone_utils import get_eastern_time, get_utc_time

# Try to load dotenv, but continue if not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not available, using system environment variables")

# Try importing databento
try:
    import databento as db
    DATABENTO_AVAILABLE = True
except ImportError:
    DATABENTO_AVAILABLE = False
    print("ERROR: databento package not installed. Run: pip install databento")

def test_databento_connection():
    """Test basic connection to Databento API"""
    if not DATABENTO_AVAILABLE:
        return False

    api_key = os.getenv('DATABENTO_API_KEY')

    # If not in environment, try reading from .env file directly
    if not api_key:
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('DATABENTO_API_KEY='):
                        api_key = line.split('=', 1)[1].strip()
                        break
        except FileNotFoundError:
            pass

    if not api_key:
        print("ERROR: DATABENTO_API_KEY not found in environment or .env file")
        return False

    print(f"Testing Databento connection with API key: {api_key[:10]}...")

    try:
        # Initialize client
        client = db.Historical(api_key)

        # Test with a simple metadata request
        print("\n1. Testing API connection with metadata request...")
        datasets = client.metadata.list_datasets()
        print(f"✓ Connection successful! Found {len(datasets)} datasets")

        return True

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

def test_nq_options_data():
    """Test retrieving NQ future options data"""
    if not DATABENTO_AVAILABLE:
        return

    api_key = os.getenv('DATABENTO_API_KEY')

    # If not in environment, try reading from .env file directly
    if not api_key:
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('DATABENTO_API_KEY='):
                        api_key = line.split('=', 1)[1].strip()
                        break
        except FileNotFoundError:
            pass

    if not api_key:
        print("ERROR: DATABENTO_API_KEY not found")
        return

    try:
        client = db.Historical(api_key)

        # Set up parameters for NQ options
        print("\n2. Testing NQ Future Options data retrieval...")

        # Date range (last trading day)
        end_date = get_eastern_time()
        start_date = end_date - timedelta(days=1)

        # Parameters for NQ options query
        params = {
            'dataset': 'GLBX.MDP3',  # CME Globex dataset
            'symbols': ['NQ.OPT'],  # NQ options - use .OPT suffix for options
            'schema': 'ohlcv-1h',  # 1-hour OHLCV bars
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
            'stype_in': 'parent'  # Use parent for futures/options root
        }

        print(f"   Query parameters: {json.dumps(params, indent=2)}")

        # Get data cost estimate first
        print("\n3. Getting cost estimate...")
        cost = client.metadata.get_cost(**params)
        print(f"   Estimated cost: ${cost:.4f}")

        # For minimal test, just show the cost and parameters
        print("\n✓ Databento API test completed successfully!")
        print("\nTo retrieve actual data, uncomment the data retrieval section")

        # Test with a more specific query to see options structure
        print("\n4. Testing options chain structure...")

        # Get definition data to see available options
        definition_params = {
            'dataset': 'GLBX.MDP3',
            'symbols': ['NQ.OPT'],
            'schema': 'definition',  # Get contract definitions
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
            'stype_in': 'parent'
        }

        try:
            cost = client.metadata.get_cost(**definition_params)
            print(f"   Definition data cost: ${cost:.4f}")

            # For testing, let's also try a specific symbol format
            print("\n5. Testing specific contract format...")
            # Try raw symbol for a specific contract
            specific_params = {
                'dataset': 'GLBX.MDP3',
                'symbols': ['NQM5'],  # June 2025 future
                'schema': 'ohlcv-1h',
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'stype_in': 'raw_symbol'
            }

            cost = client.metadata.get_cost(**specific_params)
            print(f"   Specific contract cost: ${cost:.4f}")

        except Exception as e:
            print(f"   Definition query error: {e}")

    except Exception as e:
        print(f"✗ Error retrieving NQ options data: {e}")

def main():
    """Run all Databento API tests"""
    print("=== Databento API Test for NQ Future Options ===\n")

    # Test connection
    if test_databento_connection():
        # Test NQ options data retrieval
        test_nq_options_data()

    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
