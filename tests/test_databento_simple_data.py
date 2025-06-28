#!/usr/bin/env python3
"""
Simple Databento Data Test
Test basic functionality with available datasets
"""

import os
import sys
import json
from datetime import datetime, timedelta, timezone
from utils.timezone_utils import get_eastern_time, get_utc_time

sys.path.append('.')

try:
    import databento as db
except ImportError:
    print("❌ Databento not available")
    sys.exit(1)

def test_simple_data_access():
    print("📊 Testing Databento Basic Data Access")
    print("=" * 50)
    
    api_key = os.getenv('DATABENTO_API_KEY')
    client = db.Historical(api_key)
    
    results = {
        "test_timestamp": get_eastern_time().isoformat(),
        "tests_performed": [],
        "successful_datasets": [],
        "failed_datasets": []
    }
    
    # Test different datasets and schemas
    test_configs = [
        # Basic equity data (often available in trials)
        {"dataset": "XNAS.ITCH", "symbols": ["AAPL"], "schema": "trades"},
        {"dataset": "DBEQ.BASIC", "symbols": ["SPY"], "schema": "trades"},
        {"dataset": "XNAS.BASIC", "symbols": ["QQQ"], "schema": "trades"},
        # Options data (what we really want)
        {"dataset": "OPRA.PILLAR", "symbols": ["AAPL"], "schema": "trades"},
        {"dataset": "GLBX.MDP3", "symbols": ["NQ"], "schema": "trades"},
    ]
    
    # Use a time window from yesterday to avoid "future" issues
    end_time = datetime.now(timezone.utc).replace(hour=20, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start_time = end_time - timedelta(minutes=1)
    
    print(f"Testing data from {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%H:%M')} UTC\n")
    
    for config in test_configs:
        dataset = config["dataset"]
        symbols = config["symbols"]
        schema = config["schema"]
        
        print(f"Testing {dataset} - {symbols[0]} ({schema})...")
        
        test_result = {
            "dataset": dataset,
            "symbol": symbols[0],
            "schema": schema,
            "success": False,
            "records_received": 0,
            "error": None
        }
        
        try:
            # Try to fetch data
            data = client.timeseries.get_range(
                dataset=dataset,
                symbols=symbols,
                schema=schema,
                start=start_time,
                end=end_time,
                limit=10  # Just get a few records
            )
            
            # Count records
            record_count = 0
            first_record = None
            for record in data:
                if record_count == 0:
                    first_record = record
                record_count += 1
            
            test_result["success"] = True
            test_result["records_received"] = record_count
            
            if record_count > 0:
                print(f"   ✅ Success! Received {record_count} records")
                results["successful_datasets"].append(dataset)
            else:
                print(f"   ⚠️ No data received (market may have been closed)")
                
        except Exception as e:
            error_msg = str(e)
            test_result["error"] = error_msg
            results["failed_datasets"].append(dataset)
            
            if "no_dataset_entitlement" in error_msg:
                print(f"   ❌ No access to {dataset}")
            elif "not found" in error_msg.lower():
                print(f"   ❌ Symbol not found in {dataset}")
            else:
                print(f"   ❌ Error: {error_msg[:100]}...")
        
        results["tests_performed"].append(test_result)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print(f"   Total tests: {len(test_configs)}")
    print(f"   Successful: {len(results['successful_datasets'])}")
    print(f"   Failed: {len(results['failed_datasets'])}")
    
    if results["successful_datasets"]:
        print(f"\n✅ Available datasets: {', '.join(results['successful_datasets'])}")
    else:
        print("\n⚠️ No datasets accessible with current API key")
        print("   This may be a trial key with limited access")
        print("   Contact Databento for GLBX.MDP3 access for NQ options")
    
    # Save results
    output_file = "outputs/live_trading_tests/databento_simple_data_test.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: {output_file}")
    
    return len(results["successful_datasets"]) > 0

if __name__ == "__main__":
    success = test_simple_data_access()
    sys.exit(0 if success else 1)