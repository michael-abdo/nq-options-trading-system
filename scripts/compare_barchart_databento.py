#!/usr/bin/env python3
"""
Deep comparison between Barchart and Databento data sources
Analyze if they provide the same underlying NQ options data
"""

import os
import sys
import json
from datetime import datetime
from collections import defaultdict

# Add project paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tasks', 'options_trading_system'))

from tasks.options_trading_system.data_ingestion.integration import create_data_ingestion_pipeline

def compare_data_sources():
    """Compare Barchart and Databento data sources"""

    print("=== DEEP COMPARISON: Barchart vs Databento ===\n")

    # Configuration for both sources
    # First, let's try with saved Barchart data to avoid API issues
    config = {
        "barchart": {
            "use_live_api": False,  # Use saved data first
            "file_path": "tasks/options_trading_system/data_ingestion/barchart_web_scraper/outputs/20250608/api_data/barchart_api_data_20250608_220140.json"
        },
        "databento": {
            "api_key": os.getenv("DATABENTO_API_KEY"),
            "symbols": ["NQ"],
            "use_cache": True,
            "cache_dir": "outputs/databento_cache"
        }
    }

    # Create pipeline and load both sources
    print("1. Loading data from both sources...")
    pipeline = create_data_ingestion_pipeline(config)
    load_results = pipeline.load_all_sources()

    # Check if both sources loaded successfully
    barchart_success = load_results.get("barchart", {}).get("status") == "success"
    databento_success = load_results.get("databento", {}).get("status") == "success"

    print(f"   Barchart: {'✓' if barchart_success else '✗'} {load_results.get('barchart', {}).get('contracts', 0)} contracts")
    print(f"   Databento: {'✓' if databento_success else '✗'} {load_results.get('databento', {}).get('contracts', 0)} contracts")

    if not (barchart_success and databento_success):
        print("\n❌ Cannot compare - one or both sources failed to load")
        return

    # Get raw data from both sources
    barchart_data = load_results["barchart"]["data"]
    databento_data = load_results["databento"]["data"]

    print(f"\n2. Raw Data Analysis:")
    analyze_raw_data(barchart_data, databento_data)

    # Normalize and compare
    print(f"\n3. Normalizing data for comparison...")
    normalized = pipeline.normalize_pipeline_data()

    print(f"\n4. Normalized Data Comparison:")
    analyze_normalized_data(normalized)

    # Deep contract comparison
    print(f"\n5. Contract-Level Comparison:")
    compare_contracts(normalized)

    # Volume and pricing comparison
    print(f"\n6. Volume & Pricing Analysis:")
    compare_volume_pricing(barchart_data, databento_data)

    # Save detailed comparison
    save_detailed_comparison(barchart_data, databento_data, normalized)

def analyze_raw_data(barchart_data, databento_data):
    """Analyze raw data structure and content"""

    print(f"   Barchart Structure:")
    print(f"     - Source: {barchart_data.get('metadata', {}).get('source', 'unknown')}")
    print(f"     - Options Summary: {barchart_data.get('options_summary', {}).get('total_contracts', 0)} contracts")
    print(f"     - Has raw_data: {'raw_data' in barchart_data}")

    print(f"   Databento Structure:")
    print(f"     - Source: {databento_data.get('metadata', {}).get('source', 'unknown')}")
    print(f"     - Options Summary: {databento_data.get('options_summary', {}).get('total_contracts', 0)} contracts")
    print(f"     - Dataset: {databento_data.get('metadata', {}).get('dataset', 'unknown')}")

    # Compare totals
    bc_calls = len(barchart_data.get('options_summary', {}).get('calls', []))
    bc_puts = len(barchart_data.get('options_summary', {}).get('puts', []))
    db_calls = len(databento_data.get('options_summary', {}).get('calls', []))
    db_puts = len(databento_data.get('options_summary', {}).get('puts', []))

    print(f"   Contract Breakdown:")
    print(f"     Barchart: {bc_calls} calls, {bc_puts} puts")
    print(f"     Databento: {db_calls} calls, {db_puts} puts")

def analyze_normalized_data(normalized):
    """Analyze normalized data across sources"""

    contracts = normalized["normalized_data"]["contracts"]
    by_source = defaultdict(lambda: {"calls": 0, "puts": 0, "strikes": set()})

    for contract in contracts:
        source = contract["source"]
        contract_type = contract["type"]
        strike = contract["strike"]

        by_source[source][contract_type + "s"] += 1
        by_source[source]["strikes"].add(strike)

    print(f"   Normalized Contract Summary:")
    for source, data in by_source.items():
        print(f"     {source}: {data['calls']} calls, {data['puts']} puts, {len(data['strikes'])} unique strikes")

def compare_contracts(normalized):
    """Deep comparison of individual contracts"""

    contracts = normalized["normalized_data"]["contracts"]

    # Group by source
    barchart_contracts = [c for c in contracts if c["source"] == "barchart"]
    databento_contracts = [c for c in contracts if c["source"] == "databento"]

    # Create strike/type mappings for comparison
    bc_strikes = defaultdict(list)
    db_strikes = defaultdict(list)

    for contract in barchart_contracts:
        key = f"{contract['strike']}_{contract['type']}"
        bc_strikes[key].append(contract)

    for contract in databento_contracts:
        key = f"{contract['strike']}_{contract['type']}"
        db_strikes[key].append(contract)

    # Find overlaps and differences
    bc_keys = set(bc_strikes.keys())
    db_keys = set(db_strikes.keys())

    overlap = bc_keys & db_keys
    bc_only = bc_keys - db_keys
    db_only = db_keys - bc_keys

    print(f"   Contract Overlap Analysis:")
    print(f"     Common contracts: {len(overlap)}")
    print(f"     Barchart-only: {len(bc_only)}")
    print(f"     Databento-only: {len(db_only)}")

    if len(overlap) > 0:
        print(f"   Sample overlapping contracts:")
        for i, key in enumerate(sorted(overlap)[:5]):
            bc_contract = bc_strikes[key][0]
            db_contract = db_strikes[key][0]
            print(f"     {key}: BC={bc_contract['symbol']} vs DB={db_contract['symbol']}")

    if len(bc_only) > 0:
        print(f"   Sample Barchart-only contracts:")
        for key in sorted(bc_only)[:3]:
            contract = bc_strikes[key][0]
            print(f"     {key}: {contract['symbol']}")

    if len(db_only) > 0:
        print(f"   Sample Databento-only contracts:")
        for key in sorted(db_only)[:3]:
            contract = db_strikes[key][0]
            print(f"     {key}: {contract['symbol']}")

def compare_volume_pricing(barchart_data, databento_data):
    """Compare volume and pricing data"""

    # Barchart volume analysis
    bc_calls = barchart_data.get('options_summary', {}).get('calls', [])
    bc_puts = barchart_data.get('options_summary', {}).get('puts', [])
    bc_all = bc_calls + bc_puts

    # Handle volume data safely (could be string "N/A" or numeric)
    bc_with_volume = []
    bc_total_volume = 0
    for c in bc_all:
        vol = c.get('volume', 0)
        if isinstance(vol, str):
            if vol != "N/A" and vol.replace(',', '').isdigit():
                vol = int(vol.replace(',', ''))
            else:
                vol = 0
        if vol > 0:
            bc_with_volume.append(c)
            bc_total_volume += vol

    # Databento volume analysis
    db_calls = databento_data.get('options_summary', {}).get('calls', [])
    db_puts = databento_data.get('options_summary', {}).get('puts', [])
    db_all = db_calls + db_puts

    db_with_volume = [c for c in db_all if c.get('volume', 0) > 0]
    db_total_volume = sum(c.get('volume', 0) for c in db_all)

    print(f"   Volume Comparison:")
    print(f"     Barchart: {len(bc_with_volume)}/{len(bc_all)} contracts with volume, total: {bc_total_volume}")
    print(f"     Databento: {len(db_with_volume)}/{len(db_all)} contracts with volume, total: {db_total_volume}")

    # Price comparison for overlapping contracts
    if bc_with_volume and db_with_volume:
        print(f"   Sample volume/price comparison:")

        print(f"   Sample high-volume contracts:")

        # Show top volume contracts from each source
        if bc_with_volume:
            top_bc = sorted(bc_with_volume, key=lambda x: int(str(x.get('volume', 0)).replace(',', '').replace('N/A', '0')), reverse=True)[:3]
            print(f"     Barchart top volume:")
            for contract in top_bc:
                vol = contract.get('volume', 'N/A')
                price = contract.get('last_price', 'N/A')
                symbol = contract.get('symbol', 'Unknown')
                print(f"       {symbol}: vol={vol}, price=${price}")

        if db_with_volume:
            top_db = sorted(db_with_volume, key=lambda x: x.get('volume', 0), reverse=True)[:3]
            print(f"     Databento top volume:")
            for contract in top_db:
                vol = contract.get('volume', 0)
                price = contract.get('avg_price', contract.get('last_price', 0))
                symbol = contract.get('symbol', 'Unknown')
                print(f"       {symbol}: vol={vol}, price=${price}")

def save_detailed_comparison(barchart_data, databento_data, normalized):
    """Save detailed comparison to file"""

    output_dir = f"outputs/{datetime.now().strftime('%Y%m%d')}"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%H%M%S')
    output_file = f"{output_dir}/barchart_databento_comparison_{timestamp}.json"

    comparison_data = {
        "comparison_time": datetime.now().isoformat(),
        "barchart_summary": {
            "total_contracts": barchart_data.get('options_summary', {}).get('total_contracts', 0),
            "calls": len(barchart_data.get('options_summary', {}).get('calls', [])),
            "puts": len(barchart_data.get('options_summary', {}).get('puts', [])),
            "source_type": "live_api" if "live_api" in str(barchart_data.get('metadata', {})) else "unknown"
        },
        "databento_summary": {
            "total_contracts": databento_data.get('options_summary', {}).get('total_contracts', 0),
            "calls": len(databento_data.get('options_summary', {}).get('calls', [])),
            "puts": len(databento_data.get('options_summary', {}).get('puts', [])),
            "dataset": databento_data.get('metadata', {}).get('dataset', 'unknown')
        },
        "normalized_summary": {
            "total_contracts": normalized["normalized_data"]["summary"]["total_contracts"],
            "by_source": normalized["normalized_data"]["summary"]["by_source"]
        },
        "sample_contracts": {
            "barchart": barchart_data.get('options_summary', {}).get('calls', [])[:3],
            "databento": databento_data.get('options_summary', {}).get('calls', [])[:3]
        }
    }

    with open(output_file, 'w') as f:
        json.dump(comparison_data, f, indent=2)

    print(f"\n7. Detailed comparison saved to: {output_file}")

def main():
    """Run the comparison"""

    try:
        compare_data_sources()

        print(f"\n=== CONCLUSION ===")
        print(f"✓ Comparison complete - check the analysis above")
        print(f"✓ Both sources provide NQ options data but may differ in:")
        print(f"  - Contract coverage (which strikes/expirations)")
        print(f"  - Volume data freshness and accuracy")
        print(f"  - Symbol naming conventions")
        print(f"  - Real-time vs delayed data")

        return 0

    except Exception as e:
        print(f"\n❌ Comparison failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
