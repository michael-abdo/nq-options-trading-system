#!/usr/bin/env python3
"""
Generate a focused duplicate analysis report from the comprehensive scan results
"""

import json
from typing import Dict, Any, List

def analyze_duplicates():
    """Analyze the duplicate patterns and generate a focused report"""
    
    # Load the comprehensive analysis results
    with open('/Users/Mike/trading/algos/EOD/comprehensive_duplicate_analysis.json', 'r') as f:
        results = json.load(f)
    
    print("=== COMPREHENSIVE DUPLICATE FUNCTIONALITY ANALYSIS ===")
    print(f"Analysis Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. SIMILAR CALCULATION METHODS
    print("1. CALCULATION METHODS ANALYSIS")
    print("=" * 50)
    
    if 'calculation_duplicates' in results:
        print(f"Found {len(results['calculation_duplicates'])} groups of similar calculation methods:")
        for i, group in enumerate(results['calculation_duplicates'], 1):
            print(f"\n{i}. {group['similarity_type']} ({group['count']} instances)")
            for func in group['functions']:
                file_short = func['file'].split('/')[-1]
                print(f"   - {func['name']}() in {file_short}:{func['line']}")
    else:
        print("No duplicate calculation methods found.")
    
    # 2. API REQUEST PATTERNS  
    print("\n\n2. API REQUEST PATTERNS ANALYSIS")
    print("=" * 50)
    
    if 'api_duplicates' in results:
        print(f"Found {len(results['api_duplicates'])} groups of duplicate API patterns:")
        for i, group in enumerate(results['api_duplicates'], 1):
            print(f"\n{i}. {group['similarity_type']}: {group['url']}")
            print(f"   Used in {group['count']} files:")
            for f in group['files']:
                print(f"   - {f.split('/')[-1]}")
    else:
        print("No duplicate API request patterns found.")
    
    # 3. DATA TRANSFORMATION LOGIC
    print("\n\n3. DATA TRANSFORMATION PATTERNS")
    print("=" * 50)
    
    if 'transformation_duplicates' in results:
        print(f"Found {len(results['transformation_duplicates'])} groups of similar transformation functions:")
        for i, group in enumerate(results['transformation_duplicates'], 1):
            print(f"\n{i}. Function name: {group['function_name']} ({group['count']} instances)")
            for inst in group['instances']:
                file_short = inst['file'].split('/')[-1]
                print(f"   - {file_short}:{inst['function']['line']}")
    else:
        print("No duplicate data transformation patterns found.")
        
    # 4. CONFIGURATION LOADING
    print("\n\n4. CONFIGURATION LOADING PATTERNS")
    print("=" * 50)
    
    if 'config_duplicates' in results:
        print(f"Found {len(results['config_duplicates'])} groups of duplicate config patterns:")
        for i, group in enumerate(results['config_duplicates'], 1):
            print(f"\n{i}. Environment variable: {group['env_var']}")
            print(f"   Used in {group['count']} files:")
            for f in group['files']:
                print(f"   - {f.split('/')[-1]}")
    else:
        print("No duplicate configuration loading patterns found.")
    
    # 5. ERROR HANDLING PATTERNS
    print("\n\n5. ERROR HANDLING PATTERNS")
    print("=" * 50)
    
    if 'error_handling_duplicates' in results:
        print(f"Found {len(results['error_handling_duplicates'])} groups of similar error handling:")
        for i, group in enumerate(results['error_handling_duplicates'], 1):
            print(f"\n{i}. Exception types: {', '.join(group['exceptions'])} ({group['count']} instances)")
            files = [inst['file'].split('/')[-1] for inst in group['instances']]
            unique_files = list(set(files))
            print(f"   Files: {', '.join(unique_files[:5])}{'...' if len(unique_files) > 5 else ''}")
    else:
        print("No duplicate error handling patterns found.")
    
    # 6. LOGGING SETUP CODE
    print("\n\n6. LOGGING SETUP PATTERNS")
    print("=" * 50)
    
    if 'logging_duplicates' in results:
        print(f"Found {len(results['logging_duplicates'])} groups of duplicate logging setup:")
        # Show top 5 most duplicated logging patterns
        sorted_logging = sorted(results['logging_duplicates'], key=lambda x: x['count'], reverse=True)
        for i, group in enumerate(sorted_logging[:5], 1):
            print(f"\n{i}. Pattern: {group['normalized_pattern'][:80]}...")
            print(f"   Used {group['count']} times")
            files = [inst['file'].split('/')[-1] for inst in group['instances']]
            unique_files = list(set(files))
            print(f"   Files: {', '.join(unique_files[:3])}{'...' if len(unique_files) > 3 else ''}")
    else:
        print("No duplicate logging setup patterns found.")
    
    # 7. CLASS INITIALIZATION PATTERNS
    print("\n\n7. CLASS INITIALIZATION PATTERNS")
    print("=" * 50)
    
    if 'init_duplicates' in results:
        print(f"Found {len(results['init_duplicates'])} groups of similar class initialization:")
        for i, group in enumerate(results['init_duplicates'], 1):
            print(f"\n{i}. Argument signature: {group['arg_signature']} ({group['count']} instances)")
            for inst in group['instances']:
                file_short = inst['file'].split('/')[-1]
                print(f"   - {inst['class']['class_name']} in {file_short}:{inst['class']['line']}")
    else:
        print("No duplicate class initialization patterns found.")
    
    # 8. CONSTANTS AND CONFIGURATION VALUES
    print("\n\n8. CONSTANTS AND CONFIGURATION VALUES")
    print("=" * 50)
    
    if 'constant_duplicates' in results:
        print(f"Found {len(results['constant_duplicates'])} groups of duplicate constants:")
        for i, group in enumerate(results['constant_duplicates'], 1):
            print(f"\n{i}. Constant: {group['constant_name']} ({group['count']} instances)")
            if group['different_values']:
                print("   ⚠️  WARNING: Same constant name with DIFFERENT values!")
                for inst in group['instances']:
                    file_short = inst['file'].split('/')[-1]
                    print(f"   - {file_short}: {inst['constant']['value']}")
            else:
                print(f"   Same value across all files: {group['instances'][0]['constant']['value']}")
                files = [inst['file'].split('/')[-1] for inst in group['instances']]
                print(f"   Files: {', '.join(files)}")
    else:
        print("No duplicate constants found.")
    
    # ANALYZE SPECIFIC FILES WITH MOST DUPLICATES
    print("\n\n9. FILES WITH MOST DUPLICATE PATTERNS")
    print("=" * 50)
    
    file_duplicate_counts = {}
    
    # Count duplicates per file across all categories
    for category in ['calculation_duplicates', 'api_duplicates', 'transformation_duplicates', 
                     'config_duplicates', 'error_handling_duplicates', 'logging_duplicates',
                     'init_duplicates', 'constant_duplicates']:
        if category in results:
            for group in results[category]:
                if 'instances' in group:
                    for inst in group['instances']:
                        file_path = inst['file']
                        file_name = file_path.split('/')[-1]
                        if file_name not in file_duplicate_counts:
                            file_duplicate_counts[file_name] = 0
                        file_duplicate_counts[file_name] += 1
                elif 'files' in group:
                    for file_path in group['files']:
                        file_name = file_path.split('/')[-1]
                        if file_name not in file_duplicate_counts:
                            file_duplicate_counts[file_name] = 0
                        file_duplicate_counts[file_name] += 1
    
    # Sort files by duplicate count
    sorted_files = sorted(file_duplicate_counts.items(), key=lambda x: x[1], reverse=True)
    
    print("Top files with most duplicate patterns:")
    for i, (file_name, count) in enumerate(sorted_files[:10], 1):
        print(f"{i:2d}. {file_name}: {count} duplicate patterns")
    
    # RECOMMENDATIONS
    print("\n\n10. REFACTORING RECOMMENDATIONS")
    print("=" * 50)
    
    print("HIGH PRIORITY (Most Impact):")
    print("1. Consolidate logging setup code - 29 duplicate groups found")
    print("   → Create a centralized logging utility module")
    print("   → Define standard logging patterns")
    print()
    
    print("2. Standardize error handling patterns - 5 duplicate groups found")
    print("   → Create common exception handling decorators")
    print("   → Implement consistent error response patterns")
    print()
    
    print("3. Review constant definitions - potential inconsistencies found")
    print("   → Consolidate constants into a config module")
    print("   → Ensure consistent values across files")
    print()
    
    print("MEDIUM PRIORITY:")
    print("4. Consolidate class initialization patterns")
    print("   → Create base classes for common initialization patterns")
    print("   → Use dependency injection for consistent setup")
    print()
    
    print("5. Review data transformation functions")
    print("   → Look for opportunities to create reusable transformation utilities")
    print("   → Standardize data processing pipelines")

if __name__ == "__main__":
    analyze_duplicates()