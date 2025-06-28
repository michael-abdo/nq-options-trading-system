#!/usr/bin/env python3
"""
Test full integration with Databento API
"""

import os
import sys
import json
from datetime import datetime
from utils.timezone_utils import get_eastern_time, get_utc_time

# Add project paths (now in tests subdirectory)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'tasks', 'options_trading_system'))

from tasks.options_trading_system.data_ingestion.integration import create_data_ingestion_pipeline

def test_databento_integration():
    """Test full pipeline with Databento integration"""
    
    print("=== Testing Databento Integration in Full Pipeline ===\n")
    
    # Configuration for pipeline with Databento only
    config = {
        "databento": {
            "api_key": os.getenv("DATABENTO_API_KEY"),
            "symbols": ["NQ"],
            "use_cache": True,
            "cache_dir": "outputs/databento_cache"
        }
    }
    
    # Create pipeline
    print("1. Creating data ingestion pipeline...")
    pipeline = create_data_ingestion_pipeline(config)
    
    # Load all sources
    print("\n2. Loading data from all sources...")
    load_results = pipeline.load_all_sources()
    
    print("\n3. Source Loading Results:")
    for source, result in load_results.items():
        if result["status"] == "success":
            print(f"   ✓ {source}: {result['contracts']} contracts")
        else:
            print(f"   ✗ {source}: {result.get('error', 'Unknown error')}")
    
    # Normalize data
    print("\n4. Normalizing data across all sources...")
    try:
        normalized = pipeline.normalize_pipeline_data()
        
        total_contracts = normalized["normalized_data"]["summary"]["total_contracts"]
        sources_count = normalized["normalized_data"]["summary"]["sources_count"]
        
        print(f"   ✓ Normalized {total_contracts} contracts from {sources_count} sources")
        
        # Show breakdown by source
        by_source = normalized["normalized_data"]["summary"]["by_source"]
        for source, counts in by_source.items():
            print(f"     - {source}: {counts['total']} contracts ({counts['calls']} calls, {counts['puts']} puts)")
        
    except Exception as e:
        print(f"   ✗ Normalization failed: {e}")
        return False
    
    # Get pipeline summary
    print("\n5. Pipeline Summary:")
    try:
        summary = pipeline.get_pipeline_summary()
        print(f"   Sources loaded: {summary['sources_loaded']}")
        print(f"   Sources failed: {summary['sources_failed']}")
        print(f"   Total contracts: {summary['total_contracts']}")
        
        # Save results
        output_dir = f"outputs/{get_eastern_time().strftime('%Y%m%d')}"
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = f"{output_dir}/databento_integration_test_{get_eastern_time().strftime('%H%M%S')}.json"
        
        # Clean up load_results to remove non-serializable objects
        clean_load_results = {}
        for source, result in load_results.items():
            clean_result = {
                "status": result.get("status"),
                "contracts": result.get("contracts", 0)
            }
            if "error" in result:
                clean_result["error"] = result["error"]
            if "quality" in result:
                clean_result["quality"] = result["quality"]
            clean_load_results[source] = clean_result
        
        with open(output_file, 'w') as f:
            json.dump({
                "test_time": get_eastern_time().isoformat(),
                "load_results": clean_load_results,
                "summary": summary,
                "sample_contracts": normalized["normalized_data"]["contracts"][:5]  # First 5 contracts
            }, f, indent=2)
        
        print(f"\n   Results saved to: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Summary generation failed: {e}")
        return False

def main():
    """Run integration test"""
    success = test_databento_integration()
    
    if success:
        print("\n✅ Databento integration test PASSED!")
    else:
        print("\n❌ Databento integration test FAILED!")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())