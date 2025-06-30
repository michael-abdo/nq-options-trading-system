#!/usr/bin/env python3
"""
Filter semantic duplicates by similarity score and size to identify best refactoring candidates.
"""

import json
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Any
from collections import defaultdict

def count_lines(node: ast.AST) -> int:
    """Count lines of code in an AST node."""
    if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
        return node.end_lineno - node.lineno + 1
    return 0

def load_enhanced_results() -> Dict[str, Any]:
    """Load results from duplicate scanner."""
    try:
        # Try enhanced results first
        with open('enhanced_duplicate_analysis.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fall back to basic duplicate scanner results
        try:
            with open('duplicate_analysis.json', 'r') as f:
                data = json.load(f)
                # Convert to expected format
                return {
                    'semantic_groups': data.get('semantic_duplicates', {}),
                    'similarity_scores': {}  # Basic scanner doesn't have scores
                }
        except FileNotFoundError:
            print("❌ No duplicate analysis found. Run duplicate_scanner.py first.")
            return {}

def filter_high_value_duplicates(
    min_similarity: float = 0.8,
    max_line_diff: int = 10,
    min_occurrences: int = 3
) -> Dict[str, List[Dict]]:
    """
    Filter duplicates to find high-value refactoring candidates.
    
    Args:
        min_similarity: Minimum similarity score (0-1)
        max_line_diff: Maximum line count difference between functions
        min_occurrences: Minimum number of duplicate occurrences
    
    Returns:
        Dict of pattern types to candidate groups
    """
    results = load_enhanced_results()
    if not results:
        return {}
    
    filtered_groups = defaultdict(list)
    
    for group_id, functions in results.get('semantic_groups', {}).items():
        
        # Skip small groups
        if len(functions) < min_occurrences:
            continue
        
        # Check similarity scores if available
        similarities = []
        if results.get('similarity_scores'):
            for i, func1 in enumerate(functions):
                for j, func2 in enumerate(functions[i+1:], i+1):
                    sim_key = f"{func1['id']}__{func2['id']}"
                    similarity = results.get('similarity_scores', {}).get(sim_key, 0)
                    similarities.append(similarity)
            
            if not similarities:
                continue
                
            avg_similarity = sum(similarities) / len(similarities)
            if avg_similarity < min_similarity:
                continue
        else:
            # Without scores, assume they're similar if grouped
            avg_similarity = 0.85  # Default assumption
        
        # Check line count variance (estimate from complexity if lines not available)
        line_counts = [func.get('lines', func.get('complexity', 5) * 5) for func in functions]
        if line_counts and max(line_counts) - min(line_counts) > max_line_diff:
            continue
        
        # Categorize by pattern type
        pattern_type = categorize_pattern(functions[0])
        
        # Get signature from first function
        first_func = functions[0]
        signature = f"[{', '.join(first_func.get('args', []))}] -> {first_func.get('returns', 'None')}"
        
        filtered_groups[pattern_type].append({
            'group_id': group_id,
            'functions': functions,
            'avg_similarity': avg_similarity,
            'occurrences': len(functions),
            'avg_lines': sum(line_counts) / len(line_counts) if line_counts else 0,
            'signature': signature
        })
    
    # Sort groups by potential impact (occurrences * avg_lines)
    for pattern_type in filtered_groups:
        filtered_groups[pattern_type].sort(
            key=lambda g: g['occurrences'] * g['avg_lines'],
            reverse=True
        )
    
    return dict(filtered_groups)

def categorize_pattern(func: Dict[str, Any]) -> str:
    """Categorize function by its pattern type."""
    name = func['name'].lower()
    file_path = func['file']
    
    # Test patterns
    if 'test' in file_path or name.startswith('test_'):
        if name in ['setup', 'teardown']:
            return 'test_fixture'
        return 'test_assertion'
    
    # Validation patterns
    if 'validate' in name or 'check' in name or 'verify' in name:
        return 'validation'
    
    # Calculation patterns
    if 'calculate' in name or 'compute' in name or 'get_' in name:
        return 'calculation'
    
    # Conversion patterns
    if 'convert' in name or 'parse' in name or 'format' in name:
        return 'conversion'
    
    # Initialization patterns
    if name in ['__init__', 'initialize', 'setup']:
        return 'initialization'
    
    # I/O patterns
    if 'save' in name or 'load' in name or 'read' in name or 'write' in name:
        return 'io_operation'
    
    return 'other'

def generate_refactoring_report(filtered_groups: Dict[str, List[Dict]]) -> None:
    """Generate a report of refactoring candidates."""
    total_candidates = sum(len(groups) for groups in filtered_groups.values())
    total_functions = sum(
        sum(g['occurrences'] for g in groups) 
        for groups in filtered_groups.values()
    )
    
    print("\n📊 SEMANTIC DUPLICATE REFACTORING CANDIDATES")
    print("=" * 50)
    print(f"Total candidate groups: {total_candidates}")
    print(f"Total duplicate functions: {total_functions}")
    print(f"Pattern types found: {len(filtered_groups)}")
    
    for pattern_type, groups in filtered_groups.items():
        print(f"\n🔍 {pattern_type.upper()} PATTERNS ({len(groups)} groups)")
        print("-" * 40)
        
        for i, group in enumerate(groups[:3]):  # Show top 3 per category
            print(f"\nGroup {i+1}: {group['signature']}")
            print(f"  Occurrences: {group['occurrences']}")
            print(f"  Avg similarity: {group['avg_similarity']:.1%}")
            print(f"  Avg lines: {group['avg_lines']:.0f}")
            print(f"  Impact score: {group['occurrences'] * group['avg_lines']:.0f}")
            print(f"  Functions:")
            for func in group['functions'][:3]:  # Show first 3 functions
                print(f"    - {func['file']}:{func['line']} ({func['name']})")
            if len(group['functions']) > 3:
                print(f"    ... and {len(group['functions']) - 3} more")
    
    # Save detailed results
    with open('semantic_refactoring_candidates.json', 'w') as f:
        json.dump({
            'filters': {
                'min_similarity': 0.8,
                'max_line_diff': 10,
                'min_occurrences': 3
            },
            'summary': {
                'total_groups': total_candidates,
                'total_functions': total_functions,
                'pattern_types': list(filtered_groups.keys())
            },
            'candidates': filtered_groups
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to semantic_refactoring_candidates.json")

if __name__ == "__main__":
    print("🔍 Filtering semantic duplicates for refactoring...")
    
    # Filter with strict criteria
    filtered = filter_high_value_duplicates(
        min_similarity=0.8,
        max_line_diff=10,
        min_occurrences=3
    )
    
    if filtered:
        generate_refactoring_report(filtered)
    else:
        print("❌ No high-value refactoring candidates found with current criteria")