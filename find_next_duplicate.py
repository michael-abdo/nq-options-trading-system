#!/usr/bin/env python3
"""
Find the next best duplicate function to remove
Focus on safe, testable functions with clear boundaries
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
import hashlib

class DuplicateFinder(ast.NodeVisitor):
    def __init__(self):
        self.functions = defaultdict(list)
        self.current_file = None
        
    def visit_FunctionDef(self, node):
        # Create a signature for the function
        func_signature = self._get_function_signature(node)
        
        # Store function info
        self.functions[func_signature].append({
            'file': self.current_file,
            'name': node.name,
            'line': node.lineno,
            'body_hash': self._hash_function_body(node),
            'args': [arg.arg for arg in node.args.args],
            'returns': ast.dump(node.returns) if node.returns else None,
            'body_lines': len(node.body)
        })
        
        self.generic_visit(node)
    
    def _get_function_signature(self, node):
        """Create a signature based on function structure"""
        # Include function name pattern and argument count
        arg_count = len(node.args.args)
        has_return = node.returns is not None
        
        # Look for common patterns in function names
        name_pattern = "unknown"
        if "save" in node.name.lower() or "write" in node.name.lower():
            name_pattern = "file_write"
        elif "load" in node.name.lower() or "read" in node.name.lower():
            name_pattern = "file_read"
        elif "calculate" in node.name.lower() or "compute" in node.name.lower():
            name_pattern = "calculation"
        elif "validate" in node.name.lower() or "check" in node.name.lower():
            name_pattern = "validation"
        elif "fetch" in node.name.lower() or "get" in node.name.lower():
            name_pattern = "data_fetch"
        elif "normalize" in node.name.lower() or "convert" in node.name.lower():
            name_pattern = "data_transform"
            
        return f"{name_pattern}_{arg_count}_{has_return}"
    
    def _hash_function_body(self, node):
        """Create a hash of the function body for comparison"""
        # Remove line numbers and create normalized AST dump
        body_dump = []
        for stmt in node.body:
            # Normalize the AST by removing location info
            cleaned = self._clean_ast(stmt)
            body_dump.append(ast.dump(cleaned))
        
        body_str = "\n".join(body_dump)
        return hashlib.md5(body_str.encode()).hexdigest()
    
    def _clean_ast(self, node):
        """Remove location information from AST for comparison"""
        for field, value in ast.iter_fields(node):
            if field in ('lineno', 'col_offset', 'end_lineno', 'end_col_offset'):
                delattr(node, field)
        for child in ast.iter_child_nodes(node):
            self._clean_ast(child)
        return node


def analyze_duplicates():
    """Find and analyze duplicate functions"""
    
    finder = DuplicateFinder()
    
    # Scan Python files
    for root, dirs, files in os.walk('.'):
        # Skip certain directories INCLUDING virtual environments
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', 'dashboard_env', 'testing_env', 'env', 'lib', 'site-packages']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                finder.current_file = str(filepath)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())
                    finder.visit(tree)
                except Exception as e:
                    pass
    
    # Find actual duplicates
    duplicates = []
    
    for signature, functions in finder.functions.items():
        if len(functions) > 1:
            # Group by body hash to find exact duplicates
            by_hash = defaultdict(list)
            for func in functions:
                by_hash[func['body_hash']].append(func)
            
            # Check each group of identical functions
            for body_hash, identical_funcs in by_hash.items():
                if len(identical_funcs) > 1:
                    # Skip very small functions (likely wrappers)
                    if all(f['body_lines'] < 3 for f in identical_funcs):
                        continue
                        
                    duplicates.append({
                        'signature': signature,
                        'count': len(identical_funcs),
                        'total_lines': sum(f['body_lines'] for f in identical_funcs),
                        'functions': identical_funcs
                    })
    
    return duplicates


def find_safe_duplicates(duplicates):
    """Identify safe duplicates to remove"""
    
    safe_candidates = []
    
    for dup in duplicates:
        # Calculate safety score
        safety_score = 0
        
        # Prefer smaller functions (easier to test)
        avg_lines = dup['total_lines'] / dup['count']
        if avg_lines < 20:
            safety_score += 3
        elif avg_lines < 50:
            safety_score += 2
        else:
            safety_score += 1
        
        # Prefer functions with clear patterns
        if 'file_' in dup['signature']:
            safety_score += 2  # File I/O is usually straightforward
        elif 'validation' in dup['signature']:
            safety_score += 2  # Validation is usually pure
        elif 'calculation' in dup['signature']:
            safety_score += 2  # Calculations are usually pure
        
        # Prefer functions duplicated many times
        if dup['count'] >= 4:
            safety_score += 3
        elif dup['count'] >= 3:
            safety_score += 2
        else:
            safety_score += 1
        
        # Check if in test files (lower priority)
        has_test_file = any('test' in f['file'] for f in dup['functions'])
        if has_test_file:
            safety_score -= 1
        
        dup['safety_score'] = safety_score
        safe_candidates.append(dup)
    
    # Sort by safety score and total lines saved
    safe_candidates.sort(key=lambda x: (x['safety_score'], x['total_lines']), reverse=True)
    
    return safe_candidates


def main():
    print("ANALYZING CODEBASE FOR NEXT DEDUPLICATION TARGET")
    print("="*60)
    
    # Find all duplicates
    duplicates = analyze_duplicates()
    
    print(f"\nFound {len(duplicates)} groups of duplicate functions")
    
    # Find safe candidates
    safe_candidates = find_safe_duplicates(duplicates)
    
    print("\n\nTOP 10 DEDUPLICATION CANDIDATES:")
    print("-"*60)
    
    for i, candidate in enumerate(safe_candidates[:10], 1):
        print(f"\n{i}. {candidate['signature']} (Safety Score: {candidate['safety_score']})")
        print(f"   Duplicated {candidate['count']} times, {candidate['total_lines']} total lines")
        
        # Show the duplicated functions
        print("   Functions:")
        for func in candidate['functions'][:5]:  # Show first 5
            print(f"     - {func['name']} in {func['file']}:{func['line']} ({func['body_lines']} lines)")
        
        if len(candidate['functions']) > 5:
            print(f"     ... and {len(candidate['functions']) - 5} more")
    
    # Detailed analysis of top candidate
    if safe_candidates:
        print("\n\nDETAILED ANALYSIS OF TOP CANDIDATE:")
        print("="*60)
        
        top = safe_candidates[0]
        print(f"\nSignature: {top['signature']}")
        print(f"Safety Score: {top['safety_score']}")
        print(f"Total lines to save: {top['total_lines'] - (top['total_lines'] / top['count']):.0f}")
        
        print("\nAll instances:")
        for func in top['functions']:
            print(f"\n  {func['file']}:{func['line']}")
            print(f"  Function: {func['name']}")
            print(f"  Arguments: {', '.join(func['args'])}")
            print(f"  Lines: {func['body_lines']}")
    
    return safe_candidates[0] if safe_candidates else None


if __name__ == "__main__":
    top_candidate = main()