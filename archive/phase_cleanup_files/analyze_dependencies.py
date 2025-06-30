#!/usr/bin/env python3
"""
Analyze dependencies for deduplication targets
"""

import re
import os
from pathlib import Path
from collections import defaultdict

def find_function_dependencies(function_name, search_dir="."):
    """Find all files that use a specific function"""
    
    print(f"Analyzing dependencies for: {function_name}")
    print("="*60)
    
    dependencies = defaultdict(list)
    definitions = []
    
    # Patterns to search for
    patterns = [
        # Direct calls
        rf"{function_name}\s*\(",
        # Method calls
        rf"\.{function_name}\s*\(",
        # Imports
        rf"from .* import .*{function_name}",
        rf"import .*{function_name}",
        # Definitions
        rf"def {function_name}\s*\(",
        rf"class {function_name}\s*[\(:]",
    ]
    
    for root, dirs, files in os.walk(search_dir):
        # Skip test directories and hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        for pattern in patterns:
                            if re.search(pattern, line):
                                # Check if it's a definition
                                if re.search(rf"def {function_name}\s*\(", line):
                                    definitions.append({
                                        'file': str(filepath),
                                        'line': i,
                                        'content': line.strip(),
                                        'type': 'definition'
                                    })
                                else:
                                    dependencies[str(filepath)].append({
                                        'line': i,
                                        'content': line.strip(),
                                        'type': 'usage'
                                    })
                                break
                
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return definitions, dict(dependencies)


def analyze_symbol_generation():
    """Analyze symbol generation function dependencies"""
    
    # Find get_eod_contract_symbol
    defs, deps = find_function_dependencies("get_eod_contract_symbol")
    
    print("\n## DEFINITIONS FOUND:")
    for d in defs:
        print(f"\n{d['file']}:{d['line']}")
        print(f"  {d['content']}")
    
    print("\n\n## DEPENDENCIES FOUND:")
    print(f"Total files with dependencies: {len(deps)}")
    
    # Group by directory
    by_dir = defaultdict(list)
    for file, usages in deps.items():
        dir_path = os.path.dirname(file)
        by_dir[dir_path].append((file, usages))
    
    for dir_path, files in sorted(by_dir.items()):
        print(f"\n### {dir_path or 'root'}/")
        for file, usages in files:
            print(f"\n  {os.path.basename(file)}: {len(usages)} usage(s)")
            for usage in usages[:3]:  # Show first 3
                print(f"    Line {usage['line']}: {usage['content']}")
            if len(usages) > 3:
                print(f"    ... and {len(usages) - 3} more")
    
    # Analyze which definition to keep
    print("\n\n## DEDUPLICATION ANALYSIS:")
    print("\nCurrent implementations:")
    
    impl_count = 0
    for d in defs:
        if 'symbol_generator.py' in d['file']:
            print(f"  1. CANONICAL: {d['file']} (dedicated module)")
            impl_count += 1
        elif 'solution.py' in d['file'] and 'return' not in d['content']:
            print(f"  2. DUPLICATE: {d['file']} (delegates to symbol_generator)")
            impl_count += 1
    
    print(f"\nRecommendation: Keep symbol_generator.py implementation")
    print(f"Remove: Wrapper in solution.py (already delegates)")
    
    # Check for other potential duplicates
    print("\n\n## OTHER SYMBOL GENERATION FUNCTIONS:")
    other_symbol_funcs = [
        "generate_symbol",
        "create_symbol", 
        "build_symbol",
        "get_symbol",
        "format_symbol"
    ]
    
    for func in other_symbol_funcs:
        defs2, deps2 = find_function_dependencies(func)
        if defs2:
            print(f"\n{func}: {len(defs2)} definition(s) found")
            for d in defs2:
                print(f"  - {d['file']}:{d['line']}")


def create_migration_plan():
    """Create a migration plan for deduplication"""
    
    print("\n\n## MIGRATION PLAN:")
    print("="*60)
    
    print("\n1. Target: get_eod_contract_symbol in BarchartAPIComparator")
    print("   File: tasks/.../barchart_web_scraper/solution.py")
    print("   Action: Remove method (already delegates to symbol_generator)")
    
    print("\n2. Update all callers to use symbol_generator directly:")
    print("   - Import BarchartSymbolGenerator instead of BarchartAPIComparator")
    print("   - Change comparator.get_eod_contract_symbol() to symbol_generator.get_eod_contract_symbol()")
    
    print("\n3. Test files to update:")
    test_files = [
        "test_symbol_generator.py",
        "validate_deduplication.py",
        "robust_symbol_validator.py"
    ]
    
    for tf in test_files:
        print(f"   - {tf}")
    
    print("\n4. Validation steps:")
    print("   - Run validate_deduplication.py before changes")
    print("   - Make changes")
    print("   - Run validate_deduplication.py after changes")
    print("   - Ensure all tests pass")


if __name__ == "__main__":
    analyze_symbol_generation()
    create_migration_plan()