#!/usr/bin/env python3
"""
Comprehensive Duplicate Code Analyzer
Detects semantic duplicates by analyzing:
1. Function bodies (normalized)
2. Import patterns
3. Class structures
4. Common patterns
"""

import ast
import os
import hashlib
import json
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field
import difflib

@dataclass
class FunctionInfo:
    name: str
    file_path: str
    line_start: int
    line_end: int
    args: List[str]
    returns: Optional[str]
    body_hash: str
    normalized_body: str
    imports_used: Set[str] = field(default_factory=set)
    calls_made: Set[str] = field(default_factory=set)
    complexity: int = 0

@dataclass
class ClassInfo:
    name: str
    file_path: str
    line_start: int
    line_end: int
    bases: List[str]
    methods: List[str]
    attributes: List[str]

class ComprehensiveDuplicateAnalyzer:
    def __init__(self):
        self.functions: Dict[str, List[FunctionInfo]] = defaultdict(list)
        self.classes: Dict[str, List[ClassInfo]] = defaultdict(list)
        self.imports: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        self.semantic_groups: Dict[str, List[FunctionInfo]] = defaultdict(list)
        
    def normalize_ast(self, node: ast.AST) -> str:
        """Normalize AST to detect semantic equivalence"""
        # Remove docstrings
        if isinstance(node, ast.FunctionDef):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                node.body = node.body[1:]
        
        # Normalize variable names
        class VarNormalizer(ast.NodeTransformer):
            def __init__(self):
                self.var_map = {}
                self.counter = 0
                
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    if node.id not in self.var_map:
                        self.var_map[node.id] = f"var{self.counter}"
                        self.counter += 1
                    node.id = self.var_map[node.id]
                elif isinstance(node.ctx, ast.Load) and node.id in self.var_map:
                    node.id = self.var_map[node.id]
                return node
        
        normalizer = VarNormalizer()
        normalized = normalizer.visit(node)
        return ast.unparse(normalized)
    
    def extract_function_info(self, node: ast.FunctionDef, file_path: str) -> FunctionInfo:
        """Extract comprehensive function information"""
        # Get arguments
        args = [arg.arg for arg in node.args.args]
        
        # Get return type
        returns = ast.unparse(node.returns) if node.returns else None
        
        # Get normalized body
        body_copy = ast.FunctionDef(
            name=node.name,
            args=node.args,
            body=node.body[:],
            decorator_list=[],
            returns=node.returns
        )
        normalized_body = self.normalize_ast(body_copy)
        body_hash = hashlib.md5(normalized_body.encode()).hexdigest()[:8]
        
        # Extract calls and imports
        calls_made = set()
        imports_used = set()
        complexity = 0
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls_made.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls_made.add(f"{ast.unparse(child.func.value)}.{child.func.attr}")
            
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                complexity += 1
        
        return FunctionInfo(
            name=node.name,
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            args=args,
            returns=returns,
            body_hash=body_hash,
            normalized_body=normalized_body,
            calls_made=calls_made,
            complexity=complexity
        )
    
    def extract_class_info(self, node: ast.ClassDef, file_path: str) -> ClassInfo:
        """Extract class information"""
        bases = [ast.unparse(base) for base in node.bases]
        methods = []
        attributes = []
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.append(target.id)
        
        return ClassInfo(
            name=node.name,
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            bases=bases,
            methods=methods,
            attributes=attributes
        )
    
    def analyze_file(self, file_path: str):
        """Analyze a Python file for duplicates"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.imports[alias.name].append((file_path, node.lineno))
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        import_name = f"{module}.{alias.name}" if module else alias.name
                        self.imports[import_name].append((file_path, node.lineno))
            
            # Extract functions and classes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = self.extract_function_info(node, file_path)
                    self.functions[func_info.name].append(func_info)
                    
                    # Group by semantic hash
                    self.semantic_groups[func_info.body_hash].append(func_info)
                    
                elif isinstance(node, ast.ClassDef):
                    class_info = self.extract_class_info(node, file_path)
                    self.classes[class_info.name].append(class_info)
                    
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def find_semantic_duplicates(self) -> Dict[str, List[FunctionInfo]]:
        """Find semantically equivalent functions"""
        duplicates = {}
        
        for hash_key, funcs in self.semantic_groups.items():
            if len(funcs) > 1:
                # Verify they're actually similar
                if self._verify_similarity(funcs):
                    duplicates[hash_key] = funcs
        
        return duplicates
    
    def _verify_similarity(self, funcs: List[FunctionInfo]) -> bool:
        """Verify functions are actually similar"""
        if len(funcs) < 2:
            return False
        
        # Check if normalized bodies are similar
        base = funcs[0].normalized_body
        for func in funcs[1:]:
            similarity = difflib.SequenceMatcher(None, base, func.normalized_body).ratio()
            if similarity < 0.85:  # 85% similarity threshold
                return False
        
        return True
    
    def find_near_duplicates(self, threshold: float = 0.80) -> List[Tuple[FunctionInfo, FunctionInfo, float]]:
        """Find functions that are similar but not identical"""
        near_duplicates = []
        processed = set()
        
        all_funcs = []
        for func_list in self.functions.values():
            all_funcs.extend(func_list)
        
        for i, func1 in enumerate(all_funcs):
            for j, func2 in enumerate(all_funcs[i+1:], i+1):
                pair = tuple(sorted([id(func1), id(func2)]))
                if pair in processed:
                    continue
                processed.add(pair)
                
                # Skip if already in exact duplicates
                if func1.body_hash == func2.body_hash:
                    continue
                
                similarity = self._calculate_similarity(func1, func2)
                if similarity >= threshold:
                    near_duplicates.append((func1, func2, similarity))
        
        return sorted(near_duplicates, key=lambda x: x[2], reverse=True)
    
    def _calculate_similarity(self, func1: FunctionInfo, func2: FunctionInfo) -> float:
        """Calculate similarity between two functions"""
        scores = []
        
        # Body similarity
        body_sim = difflib.SequenceMatcher(None, func1.normalized_body, func2.normalized_body).ratio()
        scores.append(body_sim * 2)  # Weight body similarity higher
        
        # Argument similarity
        args1 = set(func1.args)
        args2 = set(func2.args)
        if args1 or args2:
            arg_sim = len(args1 & args2) / max(len(args1), len(args2))
            scores.append(arg_sim)
        
        # Call similarity
        if func1.calls_made or func2.calls_made:
            call_sim = len(func1.calls_made & func2.calls_made) / max(len(func1.calls_made), len(func2.calls_made))
            scores.append(call_sim)
        
        # Complexity similarity
        if func1.complexity > 0 or func2.complexity > 0:
            comp_sim = 1 - abs(func1.complexity - func2.complexity) / max(func1.complexity, func2.complexity)
            scores.append(comp_sim)
        
        return sum(scores) / len(scores) if scores else 0
    
    def find_common_patterns(self) -> Dict[str, List[str]]:
        """Find common code patterns that could be refactored"""
        patterns = defaultdict(list)
        
        # Find common import combinations
        import_combinations = defaultdict(list)
        for func_list in self.functions.values():
            for func in func_list:
                if func.calls_made:
                    key = tuple(sorted(func.calls_made))
                    import_combinations[key].append(func.file_path)
        
        for combo, files in import_combinations.items():
            if len(files) > 3:
                patterns['common_imports'].append({
                    'imports': list(combo),
                    'files': list(set(files))[:5],
                    'count': len(set(files))
                })
        
        return patterns

def main():
    analyzer = ComprehensiveDuplicateAnalyzer()
    
    print("🔍 Comprehensive Duplicate Analysis Starting...")
    print("=" * 80)
    
    # Analyze project files
    for root, dirs, files in os.walk('./tasks'):
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git']]
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                analyzer.analyze_file(file_path)
    
    # Find exact semantic duplicates
    print("\n📊 EXACT SEMANTIC DUPLICATES:")
    print("-" * 80)
    duplicates = analyzer.find_semantic_duplicates()
    
    for hash_key, funcs in duplicates.items():
        print(f"\n🔴 Duplicate group ({len(funcs)} instances):")
        # Choose canonical (most complete version)
        canonical = max(funcs, key=lambda f: len(f.normalized_body))
        print(f"   📌 CANONICAL: {canonical.name} in {os.path.relpath(canonical.file_path)}")
        
        for func in funcs:
            if func != canonical:
                print(f"   ❌ REMOVE: {func.name} in {os.path.relpath(func.file_path)}:{func.line_start}")
    
    # Find near duplicates
    print("\n🔎 NEAR DUPLICATES (>80% similar):")
    print("-" * 80)
    near_dupes = analyzer.find_near_duplicates()
    
    for func1, func2, similarity in near_dupes[:10]:  # Top 10
        print(f"\n🟡 {similarity:.0%} similar:")
        print(f"   1. {func1.name} in {os.path.relpath(func1.file_path)}:{func1.line_start}")
        print(f"   2. {func2.name} in {os.path.relpath(func2.file_path)}:{func2.line_start}")
        print(f"   Calls in common: {func1.calls_made & func2.calls_made}")
    
    # Find patterns
    print("\n🎯 COMMON PATTERNS:")
    print("-" * 80)
    patterns = analyzer.find_common_patterns()
    
    for pattern_type, instances in patterns.items():
        if instances:
            print(f"\n{pattern_type}:")
            for instance in instances[:3]:
                print(f"   Used in {instance['count']} files")
                print(f"   Example files: {', '.join(os.path.relpath(f) for f in instance['files'][:3])}")
    
    # Summary
    print("\n📈 SUMMARY:")
    print("-" * 80)
    print(f"Total functions analyzed: {sum(len(f) for f in analyzer.functions.values())}")
    print(f"Exact duplicate groups: {len(duplicates)}")
    print(f"Near duplicate pairs: {len(near_dupes)}")
    print(f"Total lines that could be removed: ~{sum(len(funcs)-1 for funcs in duplicates.values()) * 10}")

if __name__ == '__main__':
    main()