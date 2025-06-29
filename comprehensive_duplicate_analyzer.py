#!/usr/bin/env python3
"""
Comprehensive Semantic Duplicate Analyzer
Detects true duplicates by analyzing logic, side-effects, inputs, and outputs
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
import hashlib
import json
from typing import Dict, List, Tuple, Any


class SemanticDuplicateAnalyzer(ast.NodeVisitor):
    """Analyzes Python code for semantic duplicates beyond simple text matching"""
    
    def __init__(self):
        self.functions = defaultdict(list)
        self.classes = defaultdict(list)
        self.current_file = None
        self.imports = defaultdict(set)
        self.semantic_signatures = defaultdict(list)
        
    def visit_Import(self, node):
        """Track imports to understand dependencies"""
        for alias in node.names:
            self.imports[self.current_file].add(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Track from imports"""
        if node.module:
            self.imports[self.current_file].add(node.module)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """Analyze class definitions"""
        class_info = {
            'file': self.current_file,
            'name': node.name,
            'line': node.lineno,
            'methods': [],
            'bases': [base.id if hasattr(base, 'id') else str(base) for base in node.bases],
            'decorators': [d.id if hasattr(d, 'id') else str(d) for d in node.decorator_list]
        }
        
        # Extract methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                class_info['methods'].append(item.name)
        
        self.classes[node.name].append(class_info)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        """Analyze function definitions with semantic understanding"""
        # Extract semantic signature
        semantic_sig = self._extract_semantic_signature(node)
        
        func_info = {
            'file': self.current_file,
            'name': node.name,
            'line': node.lineno,
            'args': [arg.arg for arg in node.args.args],
            'returns': self._extract_return_type(node),
            'calls': self._extract_function_calls(node),
            'operations': self._extract_operations(node),
            'side_effects': self._detect_side_effects(node),
            'semantic_hash': semantic_sig['hash'],
            'body_lines': len(node.body),
            'docstring': ast.get_docstring(node),
            'decorators': [d.id if hasattr(d, 'id') else str(d) for d in node.decorator_list]
        }
        
        self.functions[node.name].append(func_info)
        self.semantic_signatures[semantic_sig['pattern']].append(func_info)
        self.generic_visit(node)
    
    def _extract_semantic_signature(self, node):
        """Extract semantic pattern ignoring variable names"""
        # Normalize the AST by replacing names with placeholders
        normalized = self._normalize_ast(node)
        
        # Extract key patterns
        patterns = {
            'input_pattern': self._get_input_pattern(node),
            'output_pattern': self._get_output_pattern(node),
            'operation_sequence': self._get_operation_sequence(node),
            'control_flow': self._get_control_flow_pattern(node)
        }
        
        # Create hash of semantic pattern
        pattern_str = json.dumps(patterns, sort_keys=True)
        pattern_hash = hashlib.md5(pattern_str.encode()).hexdigest()
        
        return {
            'pattern': pattern_str,
            'hash': pattern_hash,
            'details': patterns
        }
    
    def _normalize_ast(self, node):
        """Normalize AST by replacing specific names with generic placeholders"""
        class NameNormalizer(ast.NodeTransformer):
            def __init__(self):
                self.name_map = {}
                self.counter = 0
            
            def visit_Name(self, node):
                if node.id not in self.name_map:
                    self.name_map[node.id] = f"var{self.counter}"
                    self.counter += 1
                node.id = self.name_map[node.id]
                return node
        
        normalizer = NameNormalizer()
        return normalizer.visit(ast.parse(ast.unparse(node)))
    
    def _get_input_pattern(self, node):
        """Extract input pattern (args, kwargs, defaults)"""
        args = node.args
        return {
            'arg_count': len(args.args),
            'has_varargs': args.vararg is not None,
            'has_kwargs': args.kwarg is not None,
            'default_count': len(args.defaults),
            'kwonly_count': len(args.kwonlyargs)
        }
    
    def _get_output_pattern(self, node):
        """Extract output pattern"""
        returns = []
        for n in ast.walk(node):
            if isinstance(n, ast.Return):
                if n.value:
                    returns.append(type(n.value).__name__)
                else:
                    returns.append('None')
        return returns
    
    def _get_operation_sequence(self, node):
        """Extract sequence of operations"""
        ops = []
        for n in ast.walk(node):
            if isinstance(n, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                ops.append(type(n).__name__)
            elif isinstance(n, ast.Call):
                if hasattr(n.func, 'id'):
                    ops.append(f"Call_{n.func.id}")
                elif hasattr(n.func, 'attr'):
                    ops.append(f"Call_{n.func.attr}")
        return ops
    
    def _get_control_flow_pattern(self, node):
        """Extract control flow pattern"""
        flow = []
        for n in ast.walk(node):
            if isinstance(n, ast.If):
                flow.append('If')
            elif isinstance(n, ast.For):
                flow.append('For')
            elif isinstance(n, ast.While):
                flow.append('While')
            elif isinstance(n, ast.Try):
                flow.append('Try')
            elif isinstance(n, ast.With):
                flow.append('With')
        return flow
    
    def _extract_return_type(self, node):
        """Extract return type annotation or inferred type"""
        if node.returns:
            return ast.unparse(node.returns)
        
        # Try to infer from return statements
        for n in ast.walk(node):
            if isinstance(n, ast.Return) and n.value:
                return type(n.value).__name__
        return None
    
    def _extract_function_calls(self, node):
        """Extract all function calls made within this function"""
        calls = []
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                if hasattr(n.func, 'id'):
                    calls.append(n.func.id)
                elif hasattr(n.func, 'attr'):
                    calls.append(f"{n.func.value.id if hasattr(n.func.value, 'id') else '?'}.{n.func.attr}")
        return calls
    
    def _extract_operations(self, node):
        """Extract mathematical and logical operations"""
        ops = defaultdict(int)
        for n in ast.walk(node):
            if isinstance(n, ast.BinOp):
                ops[type(n.op).__name__] += 1
            elif isinstance(n, ast.Compare):
                for op in n.ops:
                    ops[type(op).__name__] += 1
            elif isinstance(n, ast.BoolOp):
                ops[type(n.op).__name__] += 1
        return dict(ops)
    
    def _detect_side_effects(self, node):
        """Detect potential side effects"""
        side_effects = []
        
        for n in ast.walk(node):
            # File I/O
            if isinstance(n, ast.Call) and hasattr(n.func, 'id'):
                if n.func.id in ['open', 'write', 'read']:
                    side_effects.append('file_io')
            
            # Attribute assignment (modifies object state)
            if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store):
                side_effects.append('state_modification')
            
            # Global/nonlocal modifications
            if isinstance(n, (ast.Global, ast.Nonlocal)):
                side_effects.append('scope_modification')
            
            # Print statements
            if isinstance(n, ast.Call) and hasattr(n.func, 'id') and n.func.id == 'print':
                side_effects.append('console_output')
        
        return list(set(side_effects))


def analyze_codebase():
    """Analyze entire codebase for semantic duplicates"""
    analyzer = SemanticDuplicateAnalyzer()
    
    # Walk through all Python files
    for root, dirs, files in os.walk('.'):
        # Skip virtual environments and other non-project directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in 
                   ['__pycache__', 'node_modules', 'venv', 'env', 'dashboard_env', 'testing_env']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                analyzer.current_file = str(filepath)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())
                    analyzer.visit(tree)
                except Exception as e:
                    print(f"Error analyzing {filepath}: {e}")
    
    return analyzer


def find_semantic_duplicates(analyzer):
    """Find true semantic duplicates based on behavior, not just syntax"""
    duplicates = []
    
    # Find functions with identical semantic signatures
    for pattern, functions in analyzer.semantic_signatures.items():
        if len(functions) > 1:
            # Group by exact implementation
            impl_groups = defaultdict(list)
            
            for func in functions:
                # Create implementation signature
                impl_sig = {
                    'calls': sorted(func['calls']),
                    'operations': func['operations'],
                    'side_effects': sorted(func['side_effects']),
                    'returns': func['returns']
                }
                impl_key = json.dumps(impl_sig, sort_keys=True)
                impl_groups[impl_key].append(func)
            
            # Report groups with multiple identical implementations
            for impl_key, impl_funcs in impl_groups.items():
                if len(impl_funcs) > 1:
                    duplicates.append({
                        'type': 'semantic_duplicate',
                        'functions': impl_funcs,
                        'pattern': pattern,
                        'count': len(impl_funcs),
                        'total_lines': sum(f['body_lines'] for f in impl_funcs)
                    })
    
    # Find similar function names that might be duplicates
    for name, functions in analyzer.functions.items():
        if len(functions) > 1:
            # Check if they have similar behavior
            similar_groups = defaultdict(list)
            
            for func in functions:
                behavior_key = f"{len(func['args'])}_{func['returns']}_{len(func['calls'])}"
                similar_groups[behavior_key].append(func)
            
            for behavior_key, similar_funcs in similar_groups.items():
                if len(similar_funcs) > 1:
                    duplicates.append({
                        'type': 'name_duplicate',
                        'name': name,
                        'functions': similar_funcs,
                        'count': len(similar_funcs),
                        'total_lines': sum(f['body_lines'] for f in similar_funcs)
                    })
    
    return duplicates


def prioritize_duplicates(duplicates):
    """Prioritize duplicates by impact and safety"""
    for dup in duplicates:
        score = 0
        
        # Prefer larger savings
        score += dup['total_lines'] * 2
        
        # Prefer more instances
        score += dup['count'] * 10
        
        # Prefer functions without side effects
        has_side_effects = any(f['side_effects'] for f in dup['functions'])
        if not has_side_effects:
            score += 20
        
        # Prefer non-test code
        in_tests = all('test' in f['file'] for f in dup['functions'])
        if not in_tests:
            score += 15
        
        # Prefer simpler functions
        avg_calls = sum(len(f['calls']) for f in dup['functions']) / len(dup['functions'])
        if avg_calls < 5:
            score += 10
        
        dup['priority_score'] = score
    
    return sorted(duplicates, key=lambda x: x['priority_score'], reverse=True)


def generate_report(duplicates, analyzer):
    """Generate comprehensive duplicate report"""
    print("COMPREHENSIVE SEMANTIC DUPLICATE ANALYSIS")
    print("=" * 80)
    
    # Summary statistics
    total_functions = sum(len(funcs) for funcs in analyzer.functions.values())
    total_classes = sum(len(classes) for classes in analyzer.classes.values())
    total_duplicate_lines = sum(d['total_lines'] - (d['total_lines'] / d['count']) for d in duplicates)
    
    print(f"\nCodebase Statistics:")
    print(f"  Total functions analyzed: {total_functions}")
    print(f"  Total classes analyzed: {total_classes}")
    print(f"  Duplicate groups found: {len(duplicates)}")
    print(f"  Potential lines to save: {int(total_duplicate_lines)}")
    
    print("\n\nTOP PRIORITY DUPLICATES:")
    print("-" * 80)
    
    for i, dup in enumerate(duplicates[:15], 1):
        print(f"\n{i}. Priority Score: {dup.get('priority_score', 0)}")
        
        if dup['type'] == 'semantic_duplicate':
            print(f"   Type: Semantic Duplicate (identical behavior)")
        else:
            print(f"   Type: Name Duplicate (function '{dup.get('name', 'unknown')}')")
        
        print(f"   Instances: {dup['count']}")
        print(f"   Total lines: {dup['total_lines']} (save ~{int(dup['total_lines'] - dup['total_lines']/dup['count'])} lines)")
        
        print("   Locations:")
        for func in dup['functions'][:5]:
            side_effects = f" [side effects: {', '.join(func['side_effects'])}]" if func['side_effects'] else ""
            print(f"     - {func['file']}:{func['line']} ({func['name']}) - {func['body_lines']} lines{side_effects}")
        
        if len(dup['functions']) > 5:
            print(f"     ... and {len(dup['functions']) - 5} more")
        
        # Show semantic details for semantic duplicates
        if dup['type'] == 'semantic_duplicate' and dup['functions']:
            func = dup['functions'][0]
            print(f"   Behavior: {len(func['args'])} args, calls {len(func['calls'])} functions, returns {func['returns']}")
            if func['calls'][:3]:
                print(f"   Key calls: {', '.join(func['calls'][:3])}")
    
    return duplicates


def main():
    """Main analysis entry point"""
    print("Starting comprehensive semantic duplicate analysis...")
    
    # Analyze codebase
    analyzer = analyze_codebase()
    
    # Find duplicates
    duplicates = find_semantic_duplicates(analyzer)
    
    # Prioritize by impact and safety
    prioritized = prioritize_duplicates(duplicates)
    
    # Generate report
    generate_report(prioritized, analyzer)
    
    # Save detailed results
    with open('semantic_duplicates.json', 'w') as f:
        json.dump({
            'summary': {
                'total_functions': sum(len(funcs) for funcs in analyzer.functions.values()),
                'duplicate_groups': len(prioritized),
                'potential_line_savings': sum(d['total_lines'] - (d['total_lines'] / d['count']) for d in prioritized)
            },
            'duplicates': prioritized
        }, f, indent=2, default=str)
    
    print("\n\nDetailed results saved to semantic_duplicates.json")
    
    return prioritized


if __name__ == "__main__":
    main()