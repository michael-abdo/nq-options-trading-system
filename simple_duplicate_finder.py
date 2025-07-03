#!/usr/bin/env python3
"""
Simple but effective duplicate finder
"""

import os
import re
import hashlib
from collections import defaultdict
from typing import Dict, List, Tuple

def extract_functions(filepath: str) -> List[Dict]:
    """Extract function definitions from a Python file"""
    functions = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find function definitions
        func_pattern = r'^([ \t]*)def\s+(\w+)\s*\((.*?)\).*?:\s*\n((?:\1[ \t]+.*\n)*)'
        
        for match in re.finditer(func_pattern, content, re.MULTILINE):
            indent = match.group(1)
            name = match.group(2)
            params = match.group(3)
            body = match.group(4)
            
            # Normalize body by removing comments and docstrings
            body_lines = body.split('\n')
            clean_lines = []
            in_docstring = False
            
            for line in body_lines:
                stripped = line.strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    in_docstring = not in_docstring
                elif not in_docstring and stripped and not stripped.startswith('#'):
                    # Normalize whitespace
                    clean_lines.append(re.sub(r'\s+', ' ', stripped))
            
            clean_body = '\n'.join(clean_lines)
            body_hash = hashlib.md5(clean_body.encode()).hexdigest()[:8]
            
            functions.append({
                'name': name,
                'file': filepath,
                'params': params.strip(),
                'body': clean_body,
                'hash': body_hash,
                'line': content[:match.start()].count('\n') + 1
            })
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    
    return functions

def find_duplicates(root_dir: str) -> Dict[str, List[Dict]]:
    """Find duplicate functions in a directory"""
    all_functions = []
    
    # Collect all functions
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'test_outputs', 'outputs']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                functions = extract_functions(filepath)
                all_functions.extend(functions)
    
    # Group by hash
    hash_groups = defaultdict(list)
    for func in all_functions:
        if func['body']:  # Skip empty functions
            hash_groups[func['hash']].append(func)
    
    # Find duplicates
    duplicates = {}
    for hash_val, funcs in hash_groups.items():
        if len(funcs) > 1:
            duplicates[hash_val] = funcs
    
    return duplicates

def find_similar_names(root_dir: str) -> Dict[str, List[Dict]]:
    """Find functions with similar names that might be duplicates"""
    all_functions = []
    
    # Collect all functions
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'test_outputs', 'outputs']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                functions = extract_functions(filepath)
                all_functions.extend(functions)
    
    # Group by normalized name
    name_groups = defaultdict(list)
    for func in all_functions:
        # Normalize name (remove underscores, lowercase)
        normalized = func['name'].replace('_', '').lower()
        name_groups[normalized].append(func)
    
    # Find similar names
    similar = {}
    for norm_name, funcs in name_groups.items():
        if len(funcs) > 1:
            # Check if they have different original names
            names = set(f['name'] for f in funcs)
            if len(names) > 1:
                similar[norm_name] = funcs
    
    return similar

def main():
    print("🔍 Searching for duplicate functions...")
    print("=" * 80)
    
    # Find exact duplicates
    duplicates = find_duplicates('./tasks')
    
    print("\n📊 EXACT DUPLICATES FOUND:")
    print("-" * 80)
    
    total_duplicates = 0
    for hash_val, funcs in duplicates.items():
        total_duplicates += len(funcs) - 1
        print(f"\n🔴 Duplicate group ({len(funcs)} instances):")
        
        # Sort by file path to choose canonical
        funcs.sort(key=lambda x: (x['file'], x['line']))
        canonical = funcs[0]
        
        print(f"   📌 KEEP: {canonical['name']} in {os.path.relpath(canonical['file'])}:{canonical['line']}")
        
        for func in funcs[1:]:
            print(f"   ❌ REMOVE: {func['name']} in {os.path.relpath(func['file'])}:{func['line']}")
        
        # Show function signature
        print(f"   Signature: def {canonical['name']}({canonical['params']})")
        if len(canonical['body']) < 200:
            print(f"   Body preview: {canonical['body'][:100]}...")
    
    # Find similar names
    print("\n🔎 SIMILAR FUNCTION NAMES (possible duplicates):")
    print("-" * 80)
    
    similar = find_similar_names('./tasks')
    for norm_name, funcs in similar.items():
        print(f"\n🟡 Similar names for '{norm_name}':")
        for func in funcs:
            print(f"   - {func['name']} in {os.path.relpath(func['file'])}:{func['line']}")
    
    print("\n📈 SUMMARY:")
    print("-" * 80)
    print(f"Total duplicate functions to remove: {total_duplicates}")
    print(f"Duplicate groups found: {len(duplicates)}")
    print(f"Similar name groups: {len(similar)}")

if __name__ == '__main__':
    main()