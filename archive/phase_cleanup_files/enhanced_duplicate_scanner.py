#!/usr/bin/env python3
"""
Enhanced Duplicate Scanner with Similarity Scoring
Detects exact matches, near-duplicates, and pattern similarities
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
import hashlib
import json
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Any
import re

class EnhancedSemanticAnalyzer(ast.NodeVisitor):
    """Enhanced analyzer with similarity scoring capabilities"""
    
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
        # Extract comprehensive function metadata
        func_info = {
            'file': self.current_file,
            'class': self.current_class,
            'name': node.name,
            'line': node.lineno,
            'args': [arg.arg for arg in node.args.args],
            'body_ast': node,
            'body_text': ast.unparse(node) if hasattr(ast, 'unparse') else ast.dump(node),
            'calls': self._extract_calls(node),
            'returns': self._has_return(node),
            'side_effects': self._detect_side_effects(node),
            'complexity': self._calculate_complexity(node),
            'patterns': self._extract_patterns(node),
            'normalized_body': self._normalize_for_comparison(node)
        }
        
        # Create hashes for different comparison levels
        func_info['exact_hash'] = hashlib.md5(func_info['body_text'].encode()).hexdigest()[:8]
        func_info['structure_hash'] = hashlib.md5(self._get_structure_string(node).encode()).hexdigest()[:8]
        func_info['semantic_hash'] = self._create_semantic_hash(func_info)
        
        self.functions.append(func_info)
        self.generic_visit(node)
    
    def _calculate_complexity(self, node):
        """Calculate cyclomatic complexity"""
        complexity = 1
        for n in ast.walk(node):
            if isinstance(n, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(n, ast.BoolOp):
                complexity += len(n.values) - 1
        return complexity
    
    def _extract_patterns(self, node):
        """Extract common code patterns"""
        patterns = []
        for n in ast.walk(node):
            if isinstance(n, ast.Try):
                patterns.append('try-except')
            elif isinstance(n, ast.With):
                patterns.append('context-manager')
            elif isinstance(n, ast.ListComp):
                patterns.append('list-comprehension')
            elif isinstance(n, ast.DictComp):
                patterns.append('dict-comprehension')
            elif isinstance(n, ast.Lambda):
                patterns.append('lambda')
        return patterns
    
    def _normalize_for_comparison(self, node):
        """Normalize AST for similarity comparison"""
        class Normalizer(ast.NodeTransformer):
            def visit_Name(self, node):
                # Keep common names, normalize others
                if node.id in ['self', 'cls', 'True', 'False', 'None']:
                    return node
                node.id = f"VAR_{len(node.id)}"
                return node
            
            def visit_Constant(self, node):
                # Normalize constants by type
                if isinstance(node.value, str):
                    node.value = f"STR_{len(node.value)}"
                elif isinstance(node.value, (int, float)):
                    node.value = "NUM"
                return node
        
        import copy
        normalized = copy.deepcopy(node)
        return ast.unparse(Normalizer().visit(normalized)) if hasattr(ast, 'unparse') else ""
    
    def _get_structure_string(self, node):
        """Get structure string for comparison"""
        structure_parts = []
        for n in ast.walk(node):
            if isinstance(n, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                structure_parts.append(type(n).__name__)
            elif isinstance(n, ast.Call):
                structure_parts.append(f"Call({len(n.args)})")
        return "_".join(structure_parts)
    
    def _create_semantic_hash(self, func_info):
        """Create semantic hash based on function characteristics"""
        semantic_key = (
            f"{len(func_info['args'])}_"
            f"{func_info['returns']}_"
            f"{len(func_info['calls'])}_"
            f"{func_info['side_effects']}_"
            f"{func_info['complexity']}_"
            f"{'_'.join(sorted(func_info['patterns']))}"
        )
        return hashlib.md5(semantic_key.encode()).hexdigest()[:8]
    
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
            if isinstance(n, ast.Return) and n.value is not None:
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
            # File operations or prints
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name) and n.func.id in ['open', 'print', 'write']:
                    return True
        return False


class DuplicateDetector:
    """Enhanced duplicate detection with similarity scoring"""
    
    def __init__(self, functions: List[Dict]):
        self.functions = functions
        self.exact_duplicates = defaultdict(list)
        self.near_duplicates = defaultdict(list)
        self.pattern_duplicates = defaultdict(list)
        self.similarity_scores = {}
        
    def calculate_similarity(self, func1: Dict, func2: Dict) -> float:
        """Calculate similarity score between two functions (0-1)"""
        scores = []
        
        # 1. Exact match (weight: 40%)
        if func1['exact_hash'] == func2['exact_hash']:
            scores.append((1.0, 0.4))
        else:
            # Text similarity
            text_sim = SequenceMatcher(None, func1['body_text'], func2['body_text']).ratio()
            scores.append((text_sim, 0.4))
        
        # 2. Structure similarity (weight: 20%)
        if func1['structure_hash'] == func2['structure_hash']:
            scores.append((1.0, 0.2))
        else:
            struct_sim = SequenceMatcher(None, 
                                       func1.get('normalized_body', ''), 
                                       func2.get('normalized_body', '')).ratio()
            scores.append((struct_sim, 0.2))
        
        # 3. Semantic similarity (weight: 20%)
        semantic_sim = 0.0
        if func1['semantic_hash'] == func2['semantic_hash']:
            semantic_sim = 1.0
        else:
            # Compare individual aspects
            if len(func1['args']) == len(func2['args']):
                semantic_sim += 0.25
            if func1['returns'] == func2['returns']:
                semantic_sim += 0.25
            if func1['side_effects'] == func2['side_effects']:
                semantic_sim += 0.25
            if abs(func1['complexity'] - func2['complexity']) <= 1:
                semantic_sim += 0.25
        scores.append((semantic_sim, 0.2))
        
        # 4. Call pattern similarity (weight: 10%)
        if func1['calls'] and func2['calls']:
            call_sim = len(set(func1['calls']) & set(func2['calls'])) / len(set(func1['calls']) | set(func2['calls']))
        else:
            call_sim = 1.0 if func1['calls'] == func2['calls'] else 0.0
        scores.append((call_sim, 0.1))
        
        # 5. Pattern similarity (weight: 10%)
        if func1['patterns'] and func2['patterns']:
            pattern_sim = len(set(func1['patterns']) & set(func2['patterns'])) / len(set(func1['patterns']) | set(func2['patterns']))
        else:
            pattern_sim = 1.0 if func1['patterns'] == func2['patterns'] else 0.0
        scores.append((pattern_sim, 0.1))
        
        # Calculate weighted score
        total_score = sum(score * weight for score, weight in scores)
        return total_score
    
    def find_all_duplicates(self):
        """Find all types of duplicates with similarity scores"""
        
        # Compare all function pairs (with optimization for large codebases)
        total_comparisons = 0
        max_comparisons = 10000  # Limit to prevent timeout
        
        for i, func1 in enumerate(self.functions):
            if total_comparisons >= max_comparisons:
                print(f"Reached comparison limit ({max_comparisons})")
                break
                
            for j, func2 in enumerate(self.functions[i+1:], i+1):
                if total_comparisons >= max_comparisons:
                    break
                    
                # Skip if different number of arguments (quick filter)
                if abs(len(func1['args']) - len(func2['args'])) > 2:
                    continue
                    
                similarity = self.calculate_similarity(func1, func2)
                total_comparisons += 1
                
                if similarity >= 0.95:  # Exact or near-exact
                    self.exact_duplicates[func1['exact_hash']].append((func1, func2, similarity))
                elif similarity >= 0.80:  # Near duplicate
                    key = f"{func1['file']}:{func1['name']}"
                    self.near_duplicates[key].append((func1, func2, similarity))
                elif similarity >= 0.60:  # Pattern duplicate
                    pattern_key = f"{func1['semantic_hash']}_{len(func1['args'])}"
                    self.pattern_duplicates[pattern_key].append((func1, func2, similarity))
                
                # Store similarity score
                pair_key = (f"{func1['file']}:{func1['line']}", f"{func2['file']}:{func2['line']}")
                self.similarity_scores[pair_key] = similarity
    
    def get_duplicate_report(self) -> Dict:
        """Generate comprehensive duplicate report"""
        report = {
            'summary': {
                'total_functions': len(self.functions),
                'exact_duplicate_pairs': sum(len(v) for v in self.exact_duplicates.values()),
                'near_duplicate_pairs': sum(len(v) for v in self.near_duplicates.values()),
                'pattern_duplicate_pairs': sum(len(v) for v in self.pattern_duplicates.values()),
            },
            'exact_duplicates': [],
            'near_duplicates': [],
            'pattern_duplicates': [],
            'top_similarities': []
        }
        
        # Process exact duplicates
        for hash_val, pairs in self.exact_duplicates.items():
            if pairs:
                funcs = set()
                for f1, f2, score in pairs:
                    funcs.add((f1['file'], f1['line'], f1['name']))
                    funcs.add((f2['file'], f2['line'], f2['name']))
                
                report['exact_duplicates'].append({
                    'hash': hash_val,
                    'functions': list(funcs),
                    'similarity': max(score for _, _, score in pairs)
                })
        
        # Process near duplicates
        for key, pairs in self.near_duplicates.items():
            if pairs:
                report['near_duplicates'].append({
                    'base_function': key,
                    'similar_functions': [(f2['file'], f2['line'], f2['name'], score) 
                                        for _, f2, score in pairs],
                    'avg_similarity': sum(score for _, _, score in pairs) / len(pairs)
                })
        
        # Get top similarity pairs
        top_pairs = sorted(self.similarity_scores.items(), key=lambda x: x[1], reverse=True)[:20]
        report['top_similarities'] = [
            {'func1': k[0], 'func2': k[1], 'similarity': v}
            for k, v in top_pairs if v < 0.95  # Exclude exact matches
        ]
        
        return report


def scan_codebase_enhanced():
    """Enhanced codebase scanning"""
    analyzer = EnhancedSemanticAnalyzer()
    
    # Focus on core modules first to reduce processing time
    key_dirs = ['tasks/options_trading_system', 'scripts/utilities']
    
    for dir_name in key_dirs:
        if not os.path.exists(dir_name):
            continue
            
        for root, dirs, files in os.walk(dir_name):
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
                        pass
    
    return analyzer.functions


def main():
    """Run enhanced duplicate analysis"""
    print("🔍 Enhanced Duplicate Scanner with Similarity Scoring")
    print("="*80)
    
    functions = scan_codebase_enhanced()
    print(f"✓ Analyzed {len(functions)} functions")
    
    detector = DuplicateDetector(functions)
    detector.find_all_duplicates()
    
    report = detector.get_duplicate_report()
    
    print(f"\n📊 Duplicate Analysis Summary:")
    print(f"  - Exact duplicate pairs: {report['summary']['exact_duplicate_pairs']}")
    print(f"  - Near duplicate pairs: {report['summary']['near_duplicate_pairs']}")
    print(f"  - Pattern duplicate pairs: {report['summary']['pattern_duplicate_pairs']}")
    
    # Save detailed report
    with open('enhanced_duplicate_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n💾 Detailed report saved to enhanced_duplicate_report.json")
    
    # Print top similarities
    print(f"\n🎯 Top Function Similarities (excluding exact matches):")
    for item in report['top_similarities'][:10]:
        print(f"  {item['similarity']:.2%}: {item['func1']} ↔ {item['func2']}")


if __name__ == "__main__":
    main()