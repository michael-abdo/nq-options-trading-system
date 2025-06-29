#!/usr/bin/env python3
"""
Comprehensive Duplicate Scanner - Detects semantic duplicates across codebase
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
import hashlib
import json

class SemanticAnalyzer(ast.NodeVisitor):
    """Analyzes Python code for semantic duplicates"""
    
    def __init__(self):
        self.functions = []
        self.current_file = None
        self.current_class = None
        
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node):
        # Extract semantic signature
        func_info = {
            'file': self.current_file,
            'class': self.current_class,
            'name': node.name,
            'line': node.lineno,
            'args': [arg.arg for arg in node.args.args],
            'body_ast': self._normalize_ast(node),
            'calls': self._extract_calls(node),
            'returns': self._has_return(node),
            'side_effects': self._detect_side_effects(node),
            'complexity': len(node.body)
        }
        
        # Create semantic hash
        semantic_key = f"{len(func_info['args'])}_{func_info['returns']}_{len(func_info['calls'])}_{func_info['side_effects']}"
        func_info['semantic_hash'] = hashlib.md5(semantic_key.encode()).hexdigest()[:8]
        
        # Create body hash for exact duplicate detection
        body_str = ast.dump(func_info['body_ast'])
        func_info['body_hash'] = hashlib.md5(body_str.encode()).hexdigest()[:8]
        
        self.functions.append(func_info)
        self.generic_visit(node)
    
    def _normalize_ast(self, node):
        """Normalize AST by removing names and literals"""
        class Normalizer(ast.NodeTransformer):
            def visit_Name(self, node):
                node.id = "VAR"
                return node
            def visit_Constant(self, node):
                node.value = "CONST"
                return node
            def visit_Str(self, node):
                node.s = "STR"
                return node
            def visit_Num(self, node):
                node.n = 0
                return node
        
        import copy
        normalized = copy.deepcopy(node)
        return Normalizer().visit(normalized)
    
    def _extract_calls(self, node):
        """Extract all function calls"""
        calls = []
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name):
                    calls.append(n.func.id)
                elif isinstance(n.func, ast.Attribute):
                    calls.append(n.func.attr)
        return calls
    
    def _has_return(self, node):
        """Check if function has return statements"""
        for n in ast.walk(node):
            if isinstance(n, ast.Return):
                return True
        return False
    
    def _detect_side_effects(self, node):
        """Detect if function has side effects"""
        for n in ast.walk(node):
            # Attribute assignment
            if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store):
                return True
            # Global/nonlocal
            if isinstance(n, (ast.Global, ast.Nonlocal)):
                return True
            # File operations
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name) and n.func.id in ['open', 'print']:
                    return True
        return False


def scan_codebase():
    """Scan all Python files in the codebase"""
    analyzer = SemanticAnalyzer()
    
    # Focus on key directories to reduce scan time
    key_dirs = ['tasks', 'scripts', 'tests']
    
    for dir_name in key_dirs:
        if not os.path.exists(dir_name):
            continue
            
        for root, dirs, files in os.walk(dir_name):
            # Skip virtual environments and cache
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'venv', 'env', 
                                                     'node_modules', '.pytest_cache', 'outputs'}]
            
            for file in files:
                if file.endswith('.py'):
                    filepath = Path(root) / file
                    analyzer.current_file = str(filepath)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            tree = ast.parse(f.read())
                        analyzer.visit(tree)
                    except:
                        pass  # Skip files with syntax errors
    
    return analyzer.functions


def find_duplicates(functions):
    """Group functions by similarity"""
    # Group by exact body match
    exact_duplicates = defaultdict(list)
    for func in functions:
        exact_duplicates[func['body_hash']].append(func)
    
    # Group by semantic similarity
    semantic_duplicates = defaultdict(list)
    for func in functions:
        semantic_duplicates[func['semantic_hash']].append(func)
    
    # Find near-duplicates by function name patterns
    name_patterns = defaultdict(list)
    for func in functions:
        # Extract base name (remove prefixes/suffixes)
        base_name = func['name'].strip('_').lower()
        for prefix in ['get_', 'set_', 'is_', 'has_', 'check_', 'validate_', 'test_']:
            if base_name.startswith(prefix):
                base_name = base_name[len(prefix):]
                break
        name_patterns[base_name].append(func)
    
    return exact_duplicates, semantic_duplicates, name_patterns


def analyze_duplicates():
    """Main analysis function"""
    print("🔍 Scanning codebase for duplicates...")
    functions = scan_codebase()
    print(f"✓ Found {len(functions)} functions")
    
    exact_dups, semantic_dups, name_dups = find_duplicates(functions)
    
    # Filter out single instances
    exact_dups = {k: v for k, v in exact_dups.items() if len(v) > 1}
    semantic_dups = {k: v for k, v in semantic_dups.items() if len(v) > 1}
    name_dups = {k: v for k, v in name_dups.items() if len(v) > 1}
    
    print(f"\n📊 Duplicate Analysis:")
    print(f"  - Exact duplicates: {len(exact_dups)} groups")
    print(f"  - Semantic duplicates: {len(semantic_dups)} groups")
    print(f"  - Name pattern duplicates: {len(name_dups)} groups")
    
    # Report exact duplicates
    if exact_dups:
        print("\n🎯 EXACT DUPLICATES (identical implementation):")
        for i, (hash_val, funcs) in enumerate(exact_dups.items(), 1):
            if len(funcs) > 1:
                print(f"\n{i}. Group with {len(funcs)} identical functions:")
                for func in funcs:
                    location = f"{func['file']}:{func['line']}"
                    if func['class']:
                        location += f" ({func['class']}.{func['name']})"
                    else:
                        location += f" ({func['name']})"
                    print(f"   - {location}")
    
    # Report semantic duplicates
    print("\n🔄 SEMANTIC DUPLICATES (similar behavior):")
    for hash_val, funcs in semantic_dups.items():
        if len(funcs) > 2:  # Only show groups with 3+ functions
            print(f"\nGroup with {len(funcs)} similar functions:")
            print(f"  Pattern: {funcs[0]['args']} args, returns: {funcs[0]['returns']}, "
                  f"side effects: {funcs[0]['side_effects']}")
            for func in funcs[:5]:  # Show first 5
                print(f"  - {func['file']}:{func['line']} ({func['name']})")
            if len(funcs) > 5:
                print(f"  ... and {len(funcs)-5} more")
    
    # Save detailed results
    results = {
        'summary': {
            'total_functions': len(functions),
            'exact_duplicate_groups': len(exact_dups),
            'semantic_duplicate_groups': len(semantic_dups),
            'name_pattern_groups': len(name_dups)
        },
        'exact_duplicates': {k: [f for f in v] for k, v in exact_dups.items()},
        'semantic_duplicates': {k: [f for f in v] for k, v in semantic_dups.items()}
    }
    
    with open('duplicate_analysis.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\n💾 Detailed results saved to duplicate_analysis.json")
    return results


if __name__ == "__main__":
    analyze_duplicates()