#!/usr/bin/env python3
"""
Test Full Page Screenshot with OCR
"""

import sys
import json
from pathlib import Path
from screenshot_validator import BarchartScreenshotValidator


def test_full_page_screenshot():
    """Test full page screenshot and OCR"""
    
    print("🧪 Testing Full Page Screenshot with OCR")
    print("=" * 60)
    
    # Initialize validator with OCR enabled
    validator = BarchartScreenshotValidator(headless=True, enable_ocr=True)
    
    try:
        # Take full page screenshot
        symbol = "MQ6M25"
        print(f"\n📸 Taking full page screenshot of {symbol}...")
        
        result = validator.take_options_screenshot(symbol, full_page=True)
        
        if result["success"]:
            print(f"✅ Screenshot saved: {result['screenshot_path']}")
            
            # Check page data
            if "page_data" in result:
                page = result["page_data"]
                print(f"\n📄 Page Data:")
                print(f"   Title: {page.get('page_title', 'N/A')}")
                print(f"   Has Options Table: {'Yes' if page.get('has_options_table') else 'No'}")
                print(f"   Visible Contracts: {page.get('contract_count', 0)}")
            
            # Check OCR results
            if "ocr_validation" in result:
                ocr = result["ocr_validation"]
                if ocr.get("success"):
                    print(f"\n🔤 OCR Results:")
                    print(f"   Method: {ocr.get('method')}")
                    print(f"   Contracts Extracted: {ocr.get('contracts_found', 0)}")
                    
                    # Show summary stats
                    if "summary_stats" in ocr:
                        stats = ocr["summary_stats"]
                        print(f"\n📊 OCR Statistics:")
                        print(f"   Total Contracts: {stats.get('total_contracts', 0)}")
                        print(f"   Contracts with Data: {stats.get('contracts_with_data', 0)}")
                        
                        if stats.get('call_premium_total') or stats.get('put_premium_total'):
                            print(f"   Call Premium Total: ${stats.get('call_premium_total', 0):,.2f}")
                            print(f"   Put Premium Total: ${stats.get('put_premium_total', 0):,.2f}")
                    
                    # Show first few contracts
                    if "raw_ocr_result" in ocr and "contracts" in ocr["raw_ocr_result"]:
                        contracts = ocr["raw_ocr_result"]["contracts"]
                        print(f"\n📋 First 3 Contracts:")
                        for i, contract in enumerate(contracts[:3]):
                            print(f"\n   Contract {i+1}:")
                            print(f"     Strike: {contract.get('strike')}")
                            print(f"     Type: {contract.get('type')}")
                            print(f"     Last: {contract.get('last')}")
                            print(f"     Bid: {contract.get('bid')}")
                            print(f"     Ask: {contract.get('ask')}")
                else:
                    print(f"\n❌ OCR failed: {ocr.get('error')}")
            
            # Compare with API if available
            api_dir = Path("outputs/20250630/api_data")
            api_files = list(api_dir.glob(f"*{symbol}*.json"))
            
            if api_files:
                print(f"\n🔍 Comparing with API data...")
                validation = validator.validate_with_screenshot(str(api_files[-1]))
                
                if "ocr_comparison" in validation:
                    comparison = validation["ocr_comparison"]
                    if comparison.get("success"):
                        match_rate = comparison.get("match_stats", {}).get("overall", {}).get("match_rate", 0)
                        print(f"   Match Rate: {match_rate:.1%}")
                        print(f"   Validation: {'✅ PASSED' if comparison.get('validation_passed') else '❌ FAILED'}")
            
        else:
            print(f"❌ Screenshot failed: {result.get('error')}")
    
    finally:
        # Cleanup
        validator.cleanup()
        print("\n🧹 Cleanup complete")


if __name__ == "__main__":
    # Run in activated venv
    import subprocess
    import os
    
    # Check if we're in venv
    if 'VIRTUAL_ENV' not in os.environ:
        print("⚠️  Not in virtual environment, activating venv...")
        # Run this script in venv
        venv_python = Path(__file__).parent.parent.parent.parent.parent / "venv" / "bin" / "python3"
        if venv_python.exists():
            subprocess.run([str(venv_python), __file__])
        else:
            print("❌ Could not find venv")
    else:
        # We're in venv, run the test
        test_full_page_screenshot()