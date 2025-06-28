#!/usr/bin/env python3
"""
Test Available Databento Datasets
Check which datasets this API key has access to
"""

import os
import sys
import json
from datetime import datetime
from utils.timezone_utils import get_eastern_time, get_utc_time

sys.path.append('.')

try:
    import databento as db
except ImportError:
    print("❌ Databento not available")
    sys.exit(1)

def test_available_datasets():
    api_key = os.getenv('DATABENTO_API_KEY')
    client = db.Historical(api_key)
    
    print("🔍 Checking available datasets...")
    print("=" * 50)
    
    try:
        # Get list of all datasets
        datasets = client.metadata.list_datasets()
        
        print(f"✅ Found {len(datasets)} datasets:\n")
        
        available_datasets = []
        for dataset in datasets:
            # Dataset might be a string or object
            if isinstance(dataset, str):
                dataset_name = dataset
            else:
                dataset_name = str(dataset)
            
            available_datasets.append(dataset_name)
            print(f"   - {dataset_name}")
        
        # Check specific datasets for NQ options
        print("\n🎯 Checking NQ options data availability...")
        
        # Try to get schema for common datasets
        test_datasets = ["GLBX.MDP3", "XNAS.ITCH", "OPRA.PILLAR", "DBEQ.BASIC"]
        
        for test_dataset in test_datasets:
            print(f"\n   Testing {test_dataset}:")
            try:
                # Try to get available schemas
                schemas = client.metadata.list_schemas(dataset=test_dataset)
                print(f"   ✅ Access granted - Available schemas: {[s.schema for s in schemas]}")
            except Exception as e:
                if "no_dataset_entitlement" in str(e):
                    print(f"   ❌ No access - Requires subscription")
                else:
                    print(f"   ❌ Error: {e}")
        
        # Save results
        results = {
            "test_timestamp": get_eastern_time().isoformat(),
            "api_key_prefix": api_key[:10] + "...",
            "total_datasets": len(datasets),
            "available_datasets": available_datasets,
            "dataset_access": {},
            "recommendation": "Use a dataset you have access to"
        }
        
        output_file = "outputs/live_trading_tests/databento_datasets_test.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Results saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error checking datasets: {e}")

if __name__ == "__main__":
    test_available_datasets()