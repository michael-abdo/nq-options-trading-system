#!/usr/bin/env python3
"""
Find all imports and usages of symbol generation functions
This helps track deduplication progress and find any missed references
"""

import re
import os
from pathlib import Path
from collections import defaultdict

def find_symbol_generation_usage():
    """Find all references to symbol generation functions"""
    
    print("SYMBOL GENERATION USAGE ANALYSIS")
    print("="*60)
    
    # Track different types of usage
    usage_types = defaultdict(list)
    
    # Patterns to search for
    patterns = {
        'direct_call': re.compile(r'get_eod_contract_symbol\s*\('),
        'import_symbol_generator': re.compile(r'from.*symbol_generator.*import|import.*symbol_generator'),
        'import_comparator': re.compile(r'from.*BarchartAPIComparator.*import|import.*BarchartAPIComparator'),
        'instance_call': re.compile(r'\.get_eod_contract_symbol\s*\('),
        'definition': re.compile(r'def get_eod_contract_symbol\s*\('),
    }
    
    # Walk through all Python files
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        for pattern_name, pattern in patterns.items():
                            if pattern.search(line):
                                usage_types[pattern_name].append({
                                    'file': str(filepath),
                                    'line': i,
                                    'content': line.strip()
                                })
                
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    # Report findings
    print("\n## IMPORT ANALYSIS")
    print("\n### Files importing BarchartSymbolGenerator:")
    for usage in usage_types['import_symbol_generator']:
        print(f"{usage['file']}:{usage['line']}")
        print(f"  {usage['content']}")
    
    print(f"\nTotal: {len(usage_types['import_symbol_generator'])} files")
    
    print("\n### Files importing BarchartAPIComparator:")
    for usage in usage_types['import_comparator']:
        print(f"{usage['file']}:{usage['line']}")
        print(f"  {usage['content']}")
    
    print(f"\nTotal: {len(usage_types['import_comparator'])} files")
    
    print("\n## USAGE ANALYSIS")
    print("\n### Direct calls to get_eod_contract_symbol:")
    for usage in usage_types['instance_call'][:10]:  # Show first 10
        print(f"{usage['file']}:{usage['line']}")
        print(f"  {usage['content']}")
    
    if len(usage_types['instance_call']) > 10:
        print(f"  ... and {len(usage_types['instance_call']) - 10} more")
    
    print(f"\nTotal: {len(usage_types['instance_call'])} calls")
    
    print("\n### Function definitions:")
    for usage in usage_types['definition']:
        print(f"{usage['file']}:{usage['line']}")
        print(f"  {usage['content']}")
    
    print(f"\nTotal: {len(usage_types['definition'])} definitions")
    
    # Analyze which files might need updating
    print("\n## MIGRATION STATUS")
    
    # Files that import BarchartAPIComparator and call get_eod_contract_symbol
    files_needing_update = set()
    
    for usage in usage_types['import_comparator']:
        file_path = usage['file']
        
        # Check if this file also calls get_eod_contract_symbol
        has_call = any(u['file'] == file_path for u in usage_types['instance_call'])
        
        if has_call:
            # Check if it already imports symbol_generator
            has_symbol_generator = any(u['file'] == file_path for u in usage_types['import_symbol_generator'])
            
            if not has_symbol_generator:
                files_needing_update.add(file_path)
    
    if files_needing_update:
        print("\n### Files that may need updating:")
        for file in sorted(files_needing_update):
            print(f"  - {file}")
    else:
        print("\n✓ All files appear to be properly migrated!")
    
    return usage_types


if __name__ == "__main__":
    usage_data = find_symbol_generation_usage()
    
    # Create summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Symbol generator imports: {len(usage_data['import_symbol_generator'])}")
    print(f"API comparator imports: {len(usage_data['import_comparator'])}")
    print(f"Total function calls: {len(usage_data['instance_call'])}")
    print(f"Function definitions: {len(usage_data['definition'])}")