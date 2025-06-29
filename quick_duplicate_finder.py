#!/usr/bin/env python3
"""
Quick Duplicate Finder - Focuses on high-value duplicates
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
import json

class QuickDuplicateFinder:
    """Fast duplicate detection focusing on common patterns"""
    
    def __init__(self):
        self.exact_duplicates = defaultdict(list)
        self.init_methods = []
        self.test_methods = []
        self.utility_methods = []
        
    def scan_file(self, filepath):
        """Scan a single file for common duplicate patterns"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        'file': str(filepath),
                        'name': node.name,
                        'line': node.lineno,
                        'args': [arg.arg for arg in node.args.args],
                        'body_lines': content.split('\n')[node.lineno-1:node.end_lineno] if hasattr(node, 'end_lineno') else []
                    }
                    
                    # Quick categorization
                    if node.name == '__init__':
                        self.init_methods.append(func_info)
                    elif node.name.startswith('test_'):
                        self.test_methods.append(func_info)
                    elif node.name in ['setUp', 'tearDown', 'save_evidence', 'load_config', 'save_config']:
                        self.utility_methods.append(func_info)
                    
                    # Check for exact text duplicates (simple approach)
                    body_text = '\n'.join(func_info['body_lines'])
                    if len(body_text) > 10:  # Skip trivial functions
                        self.exact_duplicates[body_text].append(func_info)
                        
        except Exception as e:
            pass
    
    def find_duplicates(self):
        """Find duplicates in the codebase"""
        # Scan key directories
        for root, dirs, files in os.walk('tasks/options_trading_system'):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git'}]
            for file in files:
                if file.endswith('.py'):
                    self.scan_file(Path(root) / file)
        
        # Scan utilities
        if os.path.exists('scripts/utilities'):
            for file in Path('scripts/utilities').glob('*.py'):
                self.scan_file(file)
    
    def report_findings(self):
        """Generate a quick report of findings"""
        report = {
            'exact_duplicates': [],
            'similar_inits': [],
            'test_patterns': [],
            'utility_patterns': []
        }
        
        # Report exact duplicates
        for body, funcs in self.exact_duplicates.items():
            if len(funcs) > 1:
                report['exact_duplicates'].append({
                    'count': len(funcs),
                    'functions': [f"{f['file']}:{f['line']} ({f['name']})" for f in funcs],
                    'lines': len(body.split('\n'))
                })
        
        # Analyze __init__ patterns
        init_patterns = defaultdict(list)
        for init in self.init_methods:
            pattern = f"args:{len(init['args'])},lines:{len(init['body_lines'])}"
            init_patterns[pattern].append(f"{init['file']}:{init['line']}")
        
        for pattern, files in init_patterns.items():
            if len(files) > 1:
                report['similar_inits'].append({
                    'pattern': pattern,
                    'count': len(files),
                    'locations': files[:5]  # First 5
                })
        
        # Common test patterns
        test_patterns = defaultdict(int)
        for test in self.test_methods:
            if 'setUp' in '\n'.join(test['body_lines']):
                test_patterns['calls_setUp'] += 1
            if 'assertEqual' in '\n'.join(test['body_lines']):
                test_patterns['uses_assertEqual'] += 1
            if 'mock' in '\n'.join(test['body_lines']).lower():
                test_patterns['uses_mocking'] += 1
        
        report['test_patterns'] = dict(test_patterns)
        
        # Utility method duplicates
        util_groups = defaultdict(list)
        for util in self.utility_methods:
            util_groups[util['name']].append(f"{util['file']}:{util['line']}")
        
        for name, locations in util_groups.items():
            if len(locations) > 1:
                report['utility_patterns'].append({
                    'method': name,
                    'count': len(locations),
                    'locations': locations
                })
        
        return report


def main():
    finder = QuickDuplicateFinder()
    
    print("🔍 Quick Duplicate Finder")
    print("="*50)
    
    finder.find_duplicates()
    report = finder.report_findings()
    
    print(f"\n📊 Quick Analysis Results:")
    print(f"  - Exact duplicate groups: {len(report['exact_duplicates'])}")
    print(f"  - Similar __init__ patterns: {len(report['similar_inits'])}")
    print(f"  - Duplicate utility methods: {len(report['utility_patterns'])}")
    
    if report['exact_duplicates']:
        print(f"\n🎯 Top Exact Duplicates:")
        for dup in sorted(report['exact_duplicates'], key=lambda x: x['count'] * x['lines'], reverse=True)[:5]:
            print(f"  - {dup['count']} copies, {dup['lines']} lines each")
            for func in dup['functions'][:3]:
                print(f"    • {func}")
    
    if report['utility_patterns']:
        print(f"\n🔧 Duplicate Utility Methods:")
        for util in report['utility_patterns'][:5]:
            print(f"  - {util['method']}: {util['count']} copies")
            for loc in util['locations'][:3]:
                print(f"    • {loc}")
    
    # Save report
    with open('quick_duplicate_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Report saved to quick_duplicate_report.json")


if __name__ == "__main__":
    main()