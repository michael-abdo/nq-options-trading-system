#!/usr/bin/env python3
"""
Databento Documentation Validation Assessment
A practical validation of what content we actually have vs. what we claimed to download
"""

import os
import json
from pathlib import Path
from datetime import datetime

def validate_actual_content():
    """
    VALIDATE EVERYTHING - Core principle: Don't trust, verify
    """
    print("🔍 VALIDATION ASSESSMENT - What do we ACTUALLY have?")
    print("=" * 60)

    validation_results = {
        "timestamp": datetime.now().isoformat(),
        "validation_status": "UNKNOWN",
        "found_content": {},
        "missing_content": {},
        "actionable_recommendations": []
    }

    # 1. Check if the claimed directories exist
    expected_dirs = [
        "/Users/Mike/trading/algos/EOD/databento_docs/real_content",
        "/Users/Mike/trading/algos/EOD/databento_docs/clean_content",
        "/Users/Mike/trading/algos/EOD/databento_docs/databento_docs"
    ]

    print("📂 DIRECTORY VALIDATION:")
    for dir_path in expected_dirs:
        path = Path(dir_path)
        exists = path.exists()
        print(f"  {'✅' if exists else '❌'} {dir_path}: {'EXISTS' if exists else 'MISSING'}")

        if exists:
            files = list(path.glob("*"))
            validation_results["found_content"][dir_path] = {
                "exists": True,
                "file_count": len(files),
                "files": [f.name for f in files[:10]]  # First 10 files
            }
        else:
            validation_results["missing_content"][dir_path] = {"exists": False}

    print()

    # 2. Search for any actual databento HTML content anywhere in the EOD directory
    print("🔎 SEARCHING FOR ACTUAL DATABENTO CONTENT:")
    eod_path = Path("/Users/Mike/trading/algos/EOD")

    # Look for HTML files with databento in name
    databento_files = []
    for pattern in ["*databento*.html", "*quickstart*.html", "*api-reference*.html"]:
        matches = list(eod_path.rglob(pattern))
        databento_files.extend(matches)

    if databento_files:
        print(f"  ✅ Found {len(databento_files)} potential databento files:")
        for file in databento_files[:5]:  # Show first 5
            file_size = file.stat().st_size if file.exists() else 0
            print(f"     - {file} ({file_size} bytes)")
        validation_results["found_content"]["html_files"] = [str(f) for f in databento_files]
    else:
        print("  ❌ No databento HTML files found")
        validation_results["missing_content"]["html_files"] = "Not found"

    print()

    # 3. Check what we can actually validate right now
    print("📊 IMMEDIATE VALIDATION - What can we verify RIGHT NOW:")

    # Check the originally mentioned files from the task output
    original_files = [
        "nautilus_trader_integration.html",
        "python_tutorial_blog.html",
        "questdb_integration.html",
        "rust_api_documentation.html",
        "documentation_urls_list.md"
    ]

    found_original = []
    for filename in original_files:
        matches = list(eod_path.rglob(filename))
        if matches:
            found_original.append(str(matches[0]))
            print(f"  ✅ Found: {filename}")
        else:
            print(f"  ❌ Missing: {filename}")

    validation_results["found_content"]["original_files"] = found_original

    print()

    # 4. Reality check - what ACTUALLY works
    print("🎯 REALITY CHECK - What documentation do we ACTUALLY have access to:")

    # Check existing databento docs in the project
    existing_docs = list(eod_path.rglob("*databento*.md"))
    if existing_docs:
        print(f"  ✅ Found {len(existing_docs)} existing databento markdown docs:")
        for doc in existing_docs:
            print(f"     - {doc.name}")
        validation_results["found_content"]["existing_docs"] = [str(d) for d in existing_docs]

    # 5. Practical recommendations
    print()
    print("💡 PRACTICAL NEXT STEPS:")

    if not databento_files and not found_original:
        print("  📋 RECOMMENDATION: We need to re-run the scraper")
        print("     - The claimed download appears to be incomplete or in a different location")
        print("     - We should verify the scraper actually works before proceeding")
        validation_results["actionable_recommendations"].append("Re-run scraper with validation")
        validation_results["validation_status"] = "FAILED - No content found"

    elif len(found_original) >= 3:
        print("  📋 RECOMMENDATION: We have some alternative sources")
        print("     - Extract and validate content from found files")
        print("     - Use as fallback while fixing main scraper")
        validation_results["actionable_recommendations"].append("Use alternative sources")
        validation_results["validation_status"] = "PARTIAL - Some content available"

    else:
        print("  📋 RECOMMENDATION: Mixed results - need targeted approach")
        validation_results["actionable_recommendations"].append("Targeted content extraction")
        validation_results["validation_status"] = "MIXED"

    # 6. Save validation report
    report_path = Path("/Users/Mike/trading/algos/EOD/databento_docs/validation_report.json")
    with open(report_path, 'w') as f:
        json.dump(validation_results, f, indent=2)

    print(f"\n📄 Validation report saved: {report_path}")

    return validation_results

if __name__ == "__main__":
    results = validate_actual_content()
    print(f"\n🎯 VALIDATION STATUS: {results['validation_status']}")
