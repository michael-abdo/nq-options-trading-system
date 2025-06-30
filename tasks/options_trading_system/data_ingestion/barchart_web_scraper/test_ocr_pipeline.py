#!/usr/bin/env python3
"""
Test OCR Pipeline
Tests the complete OCR validation flow without Selenium
"""

import json
from pathlib import Path
from ocr_extractor import OCRExtractor
from screenshot_data_normalizer import ScreenshotDataNormalizer
from screenshot_comparator import ScreenshotComparator


def test_ocr_pipeline():
    """Test the OCR pipeline with existing files"""
    
    print("🧪 Testing OCR Validation Pipeline")
    print("=" * 60)
    
    # Find latest screenshot and API data
    screenshots_dir = Path("outputs/screenshots/validation/20250630")
    api_dir = Path("outputs/20250630/api_data")
    
    # Get latest files
    screenshots = list(screenshots_dir.glob("MQ6M25*.png"))
    api_files = list(api_dir.glob("barchart_api_MQ6M25*.json"))
    
    if not screenshots:
        print("❌ No screenshots found")
        return
    
    if not api_files:
        print("❌ No API files found")
        return
    
    screenshot_path = str(screenshots[-1])
    api_file = str(api_files[-1])
    
    print(f"📸 Screenshot: {screenshot_path}")
    print(f"📄 API File: {api_file}")
    print()
    
    # Step 1: Extract text from screenshot
    print("🔤 Step 1: OCR Text Extraction")
    print("-" * 40)
    
    extractor = OCRExtractor()
    ocr_result = extractor.extract_text_from_screenshot(screenshot_path)
    
    if ocr_result["success"]:
        print(f"✅ Extracted {len(ocr_result['contracts'])} contracts using {ocr_result['method']}")
        print(f"   First contract: Strike {ocr_result['contracts'][0]['strike']} "
              f"Last: {ocr_result['contracts'][0]['last']}")
    else:
        print(f"❌ OCR failed: {ocr_result['error']}")
        return
    
    # Step 2: Normalize data
    print("\n📊 Step 2: Data Normalization")
    print("-" * 40)
    
    normalizer = ScreenshotDataNormalizer()
    normalized = normalizer.normalize_screenshot_data(ocr_result['contracts'], "MQ6M25")
    
    print(f"✅ Normalized {normalized['total']} contracts")
    print(f"   Calls: {len(normalized['data']['Call'])}")
    print(f"   Puts: {len(normalized['data']['Put'])}")
    
    # Extract stats
    stats = normalizer.extract_summary_stats(normalized)
    print(f"\n📈 Summary Statistics:")
    print(f"   Total Contracts: {stats['total_contracts']}")
    print(f"   Contracts with Data: {stats['contracts_with_data']}")
    print(f"   Call Premium Total: ${stats['call_premium_total']:,.2f}")
    print(f"   Put Premium Total: ${stats['put_premium_total']:,.2f}")
    
    # Step 3: Load API data
    print("\n📄 Step 3: Load API Data")
    print("-" * 40)
    
    with open(api_file, 'r') as f:
        api_data = json.load(f)
    
    print(f"✅ Loaded API data: {api_data['total']} contracts")
    
    # Step 4: Compare data
    print("\n🔍 Step 4: Compare Screenshot vs API")
    print("-" * 40)
    
    comparator = ScreenshotComparator(tolerance=0.02)
    comparison = comparator.compare_data(normalized, api_data)
    
    # Print comparison report
    report = comparator.format_comparison_report(comparison)
    print(report)
    
    # Save results
    output_file = Path("outputs/20250630/ocr_test_results.json")
    results = {
        "screenshot": screenshot_path,
        "api_file": api_file,
        "ocr_result": ocr_result,
        "normalized_data": normalized,
        "comparison": comparison
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    test_ocr_pipeline()