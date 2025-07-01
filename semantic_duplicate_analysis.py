#!/usr/bin/env python3
"""
Semantic Duplicate Analysis
Identifies true semantic duplicates across the codebase based on function behavior patterns
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict


class SemanticDuplicateAnalyzer:
    """Analyze semantic duplicates by function behavior patterns"""
    
    def __init__(self, inventory_path: str):
        with open(inventory_path, 'r') as f:
            self.inventory = json.load(f)
        
        # Semantic patterns for common behaviors
        self.semantic_patterns = {
            "parsing": {
                "keywords": ["parse", "extract", "clean", "normalize", "format", "convert"],
                "descriptions": ["parse", "extract", "clean", "normalize", "format", "convert"]
            },
            "file_io": {
                "keywords": ["save", "load", "read", "write", "open", "close"],
                "descriptions": ["save", "load", "read", "write", "file", "json", "pickle"]
            },
            "validation": {
                "keywords": ["validate", "verify", "check", "is_valid", "ensure"],
                "descriptions": ["valid", "check", "verify", "ensure", "validate"]
            },
            "datetime": {
                "keywords": ["time", "date", "timestamp", "format", "parse"],
                "descriptions": ["time", "date", "timestamp", "format", "parse", "datetime"]
            },
            "data_transformation": {
                "keywords": ["transform", "convert", "map", "filter", "process"],
                "descriptions": ["transform", "convert", "process", "data", "structure"]
            },
            "api_calls": {
                "keywords": ["fetch", "get", "post", "api", "request", "call"],
                "descriptions": ["api", "request", "fetch", "http", "endpoint"]
            },
            "symbol_generation": {
                "keywords": ["symbol", "generate", "create", "build"],
                "descriptions": ["symbol", "contract", "option", "ticker"]
            },
            "risk_calculation": {
                "keywords": ["risk", "calculate", "analyze", "compute"],
                "descriptions": ["risk", "calculate", "analysis", "metric", "value"]
            }
        }
    
    def extract_all_functions(self) -> List[Dict[str, Any]]:
        """Extract all functions and methods from inventory"""
        all_functions = []
        
        for module_path, module_info in self.inventory["modules"].items():
            # Module-level functions
            for func in module_info["functions"]:
                all_functions.append({
                    "name": func["name"],
                    "module": module_path,
                    "type": "function",
                    "class": None,
                    "args": [arg["name"] for arg in func["arguments"]],
                    "docstring": func.get("docstring", ""),
                    "line": func["line"],
                    "decorators": func.get("decorators", [])
                })
            
            # Class methods
            for cls in module_info["classes"]:
                for method in cls["methods"]:
                    all_functions.append({
                        "name": method["name"],
                        "module": module_path,
                        "type": "method",
                        "class": cls["name"],
                        "args": [arg["name"] for arg in method["arguments"]],
                        "docstring": method.get("docstring", ""),
                        "line": method["line"],
                        "decorators": method.get("decorators", []),
                        "is_static": method.get("is_static", False),
                        "is_property": method.get("is_property", False)
                    })
        
        return all_functions
    
    def categorize_by_semantic_pattern(self, functions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize functions by semantic patterns"""
        categorized = defaultdict(list)
        
        for func in functions:
            name = func["name"].lower()
            docstring = (func.get("docstring") or "").lower()
            
            # Check each semantic pattern
            for pattern_name, pattern_info in self.semantic_patterns.items():
                # Check name keywords
                name_match = any(keyword in name for keyword in pattern_info["keywords"])
                
                # Check docstring descriptions
                desc_match = any(desc in docstring for desc in pattern_info["descriptions"])
                
                if name_match or desc_match:
                    categorized[pattern_name].append(func)
        
        return dict(categorized)
    
    def find_duplicate_implementations(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find functions that likely implement the same behavior"""
        duplicates = []
        
        # Group by normalized function signature
        signature_groups = defaultdict(list)
        
        for func in functions:
            # Create signature based on name pattern and args
            normalized_name = self.normalize_function_name(func["name"])
            arg_pattern = self.get_arg_pattern(func["args"])
            signature = f"{normalized_name}:{arg_pattern}"
            
            signature_groups[signature].append(func)
        
        # Find groups with multiple implementations
        for signature, group in signature_groups.items():
            if len(group) > 1:
                # Check if they're actually different (not just copies)
                modules = set(f["module"] for f in group)
                if len(modules) > 1:  # Same function in different modules
                    duplicates.append({
                        "signature": signature,
                        "functions": group,
                        "confidence": self.calculate_duplicate_confidence(group)
                    })
        
        return duplicates
    
    def normalize_function_name(self, name: str) -> str:
        """Normalize function name for comparison"""
        # Remove common prefixes/suffixes
        prefixes = ["get_", "set_", "is_", "has_", "can_", "should_", "_"]
        suffixes = ["_data", "_value", "_result", "_info", "_utils", "_helper", "_"]
        
        normalized = name.lower()
        
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        
        return normalized
    
    def get_arg_pattern(self, args: List[str]) -> str:
        """Get argument pattern for signature matching"""
        if not args:
            return "no_args"
        
        # Remove 'self' and 'cls'
        filtered_args = [arg for arg in args if arg not in ["self", "cls"]]
        
        if not filtered_args:
            return "no_args"
        
        # Create pattern based on arg count and common names
        count = len(filtered_args)
        
        # Check for common patterns
        common_args = set(filtered_args)
        
        if {"data", "filepath"} <= common_args:
            return f"data_file_{count}"
        elif {"data"} <= common_args:
            return f"data_{count}"
        elif {"filepath", "path"} & common_args:
            return f"file_{count}"
        else:
            return f"args_{count}"
    
    def calculate_duplicate_confidence(self, functions: List[Dict[str, Any]]) -> float:
        """Calculate confidence that functions are semantic duplicates"""
        # Base confidence
        confidence = 0.5
        
        # Same argument patterns boost confidence
        arg_patterns = set(self.get_arg_pattern(f["args"]) for f in functions)
        if len(arg_patterns) == 1:
            confidence += 0.2
        
        # Similar docstrings boost confidence
        docstrings = [f.get("docstring", "") for f in functions if f.get("docstring")]
        if len(docstrings) > 1:
            # Simple similarity check
            words = set()
            for doc in docstrings:
                words.update(doc.lower().split())
            
            if len(words) > 3:  # Non-trivial docstrings
                confidence += 0.1
        
        # Different modules but similar names = likely duplicates
        modules = set(f["module"] for f in functions)
        if len(modules) == len(functions):  # All in different modules
            confidence += 0.2
        
        return min(1.0, confidence)
    
    def find_parsing_duplicates(self) -> List[Dict[str, Any]]:
        """Find specific parsing function duplicates"""
        all_functions = self.extract_all_functions()
        parsing_functions = [f for f in all_functions if self.is_parsing_function(f)]
        
        # Group by parsing type
        parsing_groups = defaultdict(list)
        
        for func in parsing_functions:
            parsing_type = self.identify_parsing_type(func)
            parsing_groups[parsing_type].append(func)
        
        duplicates = []
        for parsing_type, funcs in parsing_groups.items():
            if len(funcs) > 1:
                duplicates.append({
                    "type": parsing_type,
                    "functions": funcs,
                    "severity": "high" if len(funcs) > 2 else "medium"
                })
        
        return duplicates
    
    def is_parsing_function(self, func: Dict[str, Any]) -> bool:
        """Check if function is a parsing function"""
        name = func["name"].lower()
        docstring = (func.get("docstring") or "").lower()
        
        parsing_indicators = ["parse", "extract", "clean", "normalize", "format", "convert"]
        
        return any(indicator in name or indicator in docstring for indicator in parsing_indicators)
    
    def identify_parsing_type(self, func: Dict[str, Any]) -> str:
        """Identify what type of parsing this function does"""
        name = func["name"].lower()
        docstring = (func.get("docstring") or "").lower()
        args = func.get("args", [])
        
        # Price parsing
        if any(keyword in name for keyword in ["price", "strike", "premium"]):
            return "price_parsing"
        
        # Volume/OI parsing
        if any(keyword in name for keyword in ["volume", "oi", "interest"]):
            return "volume_parsing"
        
        # Date/time parsing
        if any(keyword in name for keyword in ["date", "time", "timestamp"]):
            return "datetime_parsing"
        
        # Contract/symbol parsing
        if any(keyword in name for keyword in ["contract", "symbol", "option"]):
            return "contract_parsing"
        
        # General data parsing
        if "data" in name or "normalize" in name:
            return "data_parsing"
        
        return "general_parsing"
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive semantic duplicate report"""
        all_functions = self.extract_all_functions()
        
        # Categorize by semantic patterns
        categorized = self.categorize_by_semantic_pattern(all_functions)
        
        # Find duplicate implementations
        general_duplicates = self.find_duplicate_implementations(all_functions)
        
        # Find parsing-specific duplicates
        parsing_duplicates = self.find_parsing_duplicates()
        
        # Statistics
        stats = {
            "total_functions": len(all_functions),
            "total_modules": len(self.inventory["modules"]),
            "functions_by_category": {cat: len(funcs) for cat, funcs in categorized.items()},
            "potential_duplicates": len(general_duplicates),
            "parsing_duplicates": len(parsing_duplicates)
        }
        
        # High-confidence duplicates
        high_confidence = [d for d in general_duplicates if d["confidence"] > 0.7]
        
        return {
            "summary": stats,
            "categorized_functions": categorized,
            "potential_duplicates": general_duplicates,
            "parsing_duplicates": parsing_duplicates,
            "high_confidence_duplicates": high_confidence,
            "recommendations": self.generate_recommendations(high_confidence, parsing_duplicates)
        }
    
    def generate_recommendations(self, high_confidence: List[Dict], parsing_duplicates: List[Dict]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if high_confidence:
            recommendations.append(f"🔥 Found {len(high_confidence)} high-confidence duplicate function groups")
            recommendations.append("→ Consider consolidating these into shared utility modules")
        
        if parsing_duplicates:
            high_severity = [p for p in parsing_duplicates if p["severity"] == "high"]
            if high_severity:
                recommendations.append(f"⚠️  Found {len(high_severity)} critical parsing function duplicates")
                recommendations.append("→ The parsing_utils.py module should be the single source of truth")
        
        # Check for file I/O duplicates
        file_io_count = sum(1 for d in high_confidence if "save" in str(d) or "load" in str(d))
        if file_io_count:
            recommendations.append(f"📁 Found {file_io_count} file I/O duplicates")
            recommendations.append("→ Consolidate into file_io_utils.py")
        
        return recommendations


def main():
    """Run semantic duplicate analysis"""
    inventory_path = "/Users/Mike/trading/algos/EOD/codebase_inventory.json"
    analyzer = SemanticDuplicateAnalyzer(inventory_path)
    
    report = analyzer.generate_report()
    
    # Save detailed report
    output_path = Path("/Users/Mike/trading/algos/EOD/semantic_duplicate_analysis.json")
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print("🔍 Semantic Duplicate Analysis Complete")
    print(f"📊 Total Functions Analyzed: {report['summary']['total_functions']}")
    print(f"🎯 Potential Duplicates Found: {report['summary']['potential_duplicates']}")
    print(f"⚠️  High-Confidence Duplicates: {len(report['high_confidence_duplicates'])}")
    print(f"🔧 Parsing Duplicates: {report['summary']['parsing_duplicates']}")
    
    print("\n💡 Recommendations:")
    for rec in report["recommendations"]:
        print(f"   {rec}")
    
    print(f"\n📝 Detailed report saved to: {output_path}")


if __name__ == "__main__":
    main()