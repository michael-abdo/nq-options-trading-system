#!/usr/bin/env python3
"""
Test Data Source Availability
Generate comprehensive report on all data source status
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'tasks', 'options_trading_system'))
sys.path.insert(0, os.path.join(parent_dir, 'tasks', 'options_trading_system', 'data_ingestion'))

def test_source_availability():
    print("📊 Data Source Availability Report")
    print("=" * 60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {
        "report_timestamp": datetime.now().isoformat(),
        "sources": {},
        "summary": {
            "total_sources": 0,
            "available_sources": 0,
            "configured_sources": 0,
            "priority_order": []
        }
    }
    
    # Import registry
    try:
        from sources_registry import get_sources_registry, get_sources_by_priority
    except ImportError:
        print("❌ Failed to import sources_registry")
        return 1
    
    registry = get_sources_registry()
    
    # Get sources in priority order
    priority_order = get_sources_by_priority(only_available=False)
    results["summary"]["priority_order"] = priority_order
    
    print("🔍 Checking Data Sources by Priority:")
    print()
    
    for idx, source_name in enumerate(priority_order, 1):
        print(f"{idx}. {source_name.upper()}")
        source_info = {
            "priority": idx,
            "available": False,
            "configured": False,
            "status": "UNKNOWN",
            "details": {},
            "test_results": {}
        }
        
        # Check if source is available in registry
        try:
            if registry.is_source_available(source_name):
                source_info["available"] = True
                info = registry.get_source_info(source_name)
                source_info["details"] = {
                    "type": info.get("type", "unknown"),
                    "description": info.get("description", ""),
                    "required_config": info.get("required_config", [])
                }
                print(f"   ✅ Available: {info['description']}")
            else:
                print(f"   ❌ Not Available")
        except Exception as e:
            print(f"   ❌ Error checking availability: {e}")
            source_info["test_results"]["availability_error"] = str(e)
        
        # Check configuration
        print(f"   📋 Configuration:")
        
        # Check environment variables
        if source_name == "databento":
            api_key = os.getenv("DATABENTO_API_KEY")
            if api_key:
                source_info["configured"] = True
                source_info["test_results"]["api_key"] = f"{api_key[:10]}..."
                print(f"      ✅ API key configured")
            else:
                print(f"      ❌ API key missing")
                
            # Special check for Databento access
            if api_key:
                try:
                    import databento as db
                    client = db.Historical(api_key)
                    # Test GLBX.MDP3 access
                    try:
                        from datetime import timezone, timedelta
                        test_end = datetime.now(timezone.utc) - timedelta(days=1)
                        test_start = test_end - timedelta(minutes=1)
                        test_response = client.timeseries.get_range(
                            dataset="GLBX.MDP3",
                            symbols=["NQ"],
                            schema="trades",
                            start=test_start,
                            end=test_end,
                            limit=1
                        )
                        source_info["status"] = "READY"
                        source_info["test_results"]["dataset_access"] = "GLBX.MDP3 accessible"
                        print(f"      ✅ GLBX.MDP3 dataset accessible")
                    except Exception as e:
                        if "no_dataset_entitlement" in str(e) or "403" in str(e):
                            source_info["status"] = "NO_ACCESS"
                            source_info["test_results"]["dataset_access"] = "No GLBX.MDP3 entitlement"
                            print(f"      ❌ No GLBX.MDP3 access (subscription required)")
                        else:
                            source_info["status"] = "ERROR"
                            source_info["test_results"]["dataset_error"] = str(e)
                            print(f"      ⚠️ Dataset test error: {e}")
                except ImportError:
                    source_info["status"] = "NOT_INSTALLED"
                    print(f"      ❌ Databento package not installed")
                    
        elif source_name == "polygon":
            api_key = os.getenv("POLYGON_API_KEY")
            if api_key:
                source_info["configured"] = True
                source_info["test_results"]["api_key"] = f"{api_key[:10]}..."
                source_info["status"] = "READY"
                print(f"      ✅ API key configured")
            else:
                source_info["status"] = "NOT_CONFIGURED"
                print(f"      ❌ API key missing")
                
        elif source_name == "barchart" or source_name == "barchart_live":
            source_info["configured"] = True
            source_info["status"] = "READY"
            source_info["test_results"]["method"] = "Web scraping (no API key required)"
            print(f"      ✅ No configuration required (web scraping)")
            
        elif source_name == "tradovate":
            cid = os.getenv("TRADOVATE_CID")
            secret = os.getenv("TRADOVATE_SECRET")
            if cid and secret:
                source_info["configured"] = True
                source_info["status"] = "DEMO_MODE"
                source_info["test_results"]["mode"] = "Demo"
                print(f"      ✅ Demo credentials configured")
            else:
                source_info["status"] = "NOT_CONFIGURED"
                print(f"      ❌ Credentials missing")
        
        # Overall status
        print(f"   📊 Status: {source_info['status']}")
        print()
        
        results["sources"][source_name] = source_info
    
    # Summary statistics
    results["summary"]["total_sources"] = len(results["sources"])
    results["summary"]["available_sources"] = sum(1 for s in results["sources"].values() if s["available"])
    results["summary"]["configured_sources"] = sum(1 for s in results["sources"].values() if s["configured"])
    
    print("📈 Summary Statistics:")
    print(f"   Total Sources: {results['summary']['total_sources']}")
    print(f"   Available: {results['summary']['available_sources']}")
    print(f"   Configured: {results['summary']['configured_sources']}")
    print(f"   Ready to Use: {sum(1 for s in results['sources'].values() if s['status'] in ['READY', 'DEMO_MODE'])}")
    
    # Recommendations
    print("\n💡 Recommendations:")
    
    databento_status = results["sources"].get("databento", {}).get("status", "UNKNOWN")
    if databento_status == "NO_ACCESS":
        print("   1. Databento: Contact sales for GLBX.MDP3 access")
    elif databento_status == "NOT_CONFIGURED":
        print("   1. Databento: Add DATABENTO_API_KEY to .env file")
    
    if results["sources"].get("polygon", {}).get("status") == "NOT_CONFIGURED":
        print("   2. Polygon: Add POLYGON_API_KEY to .env file")
    
    if results["sources"].get("barchart", {}).get("status") == "READY":
        print("   ✅ Barchart is ready as primary data source")
    
    # Save results
    output_dir = Path("outputs/live_trading_tests")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"source_availability_report_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Full report saved to: {output_file}")
    
    # Return status code
    ready_sources = sum(1 for s in results['sources'].values() if s['status'] in ['READY', 'DEMO_MODE'])
    return 0 if ready_sources > 0 else 1

if __name__ == "__main__":
    sys.exit(test_source_availability())