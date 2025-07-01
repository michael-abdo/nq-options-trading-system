#!/usr/bin/env python3
"""
Comprehensive Codebase Inventory Generator
Extracts structural information from all Python modules for semantic duplicate analysis
"""

import json
import ast
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CodeInventory:
    """Extracts structural information from Python files"""
    
    def __init__(self):
        self.inventory = {
            "generated_at": datetime.now().isoformat(),
            "modules": {},
            "analysis_metadata": {
                "total_modules": 0,
                "total_classes": 0,
                "total_functions": 0,
                "total_methods": 0
            }
        }
    
    def analyze_file(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """Analyze a single Python file and extract its structure"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            module_info = {
                "file_path": str(filepath),
                "relative_path": str(filepath.relative_to(Path.cwd())),
                "imports": self._extract_imports(tree),
                "classes": self._extract_classes(tree),
                "functions": self._extract_functions(tree),
                "constants": self._extract_constants(tree),
                "docstring": ast.get_docstring(tree),
                "line_count": len(content.splitlines()),
                "size_bytes": len(content.encode('utf-8'))
            }
            
            return module_info
            
        except Exception as e:
            logger.error(f"Failed to analyze {filepath}: {e}")
            return None
    
    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract import statements"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append({
                        "type": "from_import",
                        "module": node.module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })
        
        return imports
    
    def _extract_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract class definitions"""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "docstring": ast.get_docstring(node),
                    "base_classes": [self._get_name(base) for base in node.bases],
                    "methods": self._extract_methods(node),
                    "decorators": [self._get_decorator_name(d) for d in node.decorator_list]
                }
                classes.append(class_info)
        
        return classes
    
    def _extract_methods(self, class_node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Extract methods from a class"""
        methods = []
        
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                method_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "docstring": ast.get_docstring(node),
                    "arguments": self._extract_arguments(node),
                    "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                    "is_property": any(self._get_decorator_name(d) == "property" for d in node.decorator_list),
                    "is_static": any(self._get_decorator_name(d) == "staticmethod" for d in node.decorator_list),
                    "is_class": any(self._get_decorator_name(d) == "classmethod" for d in node.decorator_list)
                }
                methods.append(method_info)
        
        return methods
    
    def _extract_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract module-level function definitions"""
        functions = []
        
        # Only get top-level functions, not nested ones
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "docstring": ast.get_docstring(node),
                    "arguments": self._extract_arguments(node),
                    "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                    "return_annotation": self._get_annotation(node.returns) if node.returns else None
                }
                functions.append(func_info)
        
        return functions
    
    def _extract_arguments(self, func_node: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Extract function/method arguments"""
        args = []
        
        # Regular arguments
        for arg in func_node.args.args:
            args.append({
                "name": arg.arg,
                "annotation": self._get_annotation(arg.annotation) if arg.annotation else None,
                "type": "positional"
            })
        
        # Keyword-only arguments
        for arg in func_node.args.kwonlyargs:
            args.append({
                "name": arg.arg,
                "annotation": self._get_annotation(arg.annotation) if arg.annotation else None,
                "type": "keyword_only"
            })
        
        # Varargs (*args)
        if func_node.args.vararg:
            args.append({
                "name": func_node.args.vararg.arg,
                "annotation": self._get_annotation(func_node.args.vararg.annotation) if func_node.args.vararg.annotation else None,
                "type": "varargs"
            })
        
        # Keyword arguments (**kwargs)
        if func_node.args.kwarg:
            args.append({
                "name": func_node.args.kwarg.arg,
                "annotation": self._get_annotation(func_node.args.kwarg.annotation) if func_node.args.kwarg.annotation else None,
                "type": "kwargs"
            })
        
        return args
    
    def _extract_constants(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract module-level constants"""
        constants = []
        
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        constants.append({
                            "name": target.id,
                            "line": node.lineno,
                            "value": self._get_constant_value(node.value)
                        })
        
        return constants
    
    def _get_name(self, node: ast.AST) -> str:
        """Get name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        else:
            return str(node)
    
    def _get_decorator_name(self, decorator: ast.AST) -> str:
        """Get decorator name"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_name(decorator.value)}.{decorator.attr}"
        else:
            return str(decorator)
    
    def _get_annotation(self, annotation: ast.AST) -> str:
        """Get type annotation as string"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute):
            return f"{self._get_name(annotation.value)}.{annotation.attr}"
        elif isinstance(annotation, ast.Subscript):
            return f"{self._get_name(annotation.value)}[{self._get_name(annotation.slice)}]"
        else:
            return str(annotation)
    
    def _get_constant_value(self, value_node: ast.AST) -> Any:
        """Extract constant value from AST node"""
        try:
            if isinstance(value_node, ast.Constant):
                return value_node.value
            elif isinstance(value_node, ast.Str):
                return value_node.s
            elif isinstance(value_node, ast.Num):
                return value_node.n
            elif isinstance(value_node, ast.List):
                return [self._get_constant_value(item) for item in value_node.elts]
            elif isinstance(value_node, ast.Dict):
                return {
                    self._get_constant_value(k): self._get_constant_value(v)
                    for k, v in zip(value_node.keys, value_node.values)
                }
            else:
                return "<complex_value>"
        except:
            return "<unparseable>"
    
    def scan_codebase(self, root_path: Path, file_patterns: List[str]) -> Dict[str, Any]:
        """Scan entire codebase and build inventory"""
        logger.info(f"Scanning codebase at {root_path}")
        
        files_to_analyze = []
        for pattern in file_patterns:
            files_to_analyze.extend(root_path.rglob(pattern))
        
        # Filter out test files and virtual environments
        python_files = [
            f for f in files_to_analyze 
            if f.is_file() and 
            "test" not in f.name.lower() and
            "env" not in str(f) and
            "site-packages" not in str(f) and
            "__pycache__" not in str(f)
        ]
        
        logger.info(f"Found {len(python_files)} Python files to analyze")
        
        for filepath in sorted(python_files):
            logger.info(f"Analyzing {filepath.relative_to(root_path)}")
            module_info = self.analyze_file(filepath)
            
            if module_info:
                # Use relative path as key
                rel_path = str(filepath.relative_to(root_path))
                self.inventory["modules"][rel_path] = module_info
                
                # Update metadata
                self.inventory["analysis_metadata"]["total_classes"] += len(module_info["classes"])
                self.inventory["analysis_metadata"]["total_functions"] += len(module_info["functions"])
                self.inventory["analysis_metadata"]["total_methods"] += sum(
                    len(cls["methods"]) for cls in module_info["classes"]
                )
        
        self.inventory["analysis_metadata"]["total_modules"] = len(self.inventory["modules"])
        
        return self.inventory
    
    def identify_semantic_duplicates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Identify potential semantic duplicates based on function signatures and naming patterns"""
        duplicates = {
            "similar_function_names": [],
            "similar_class_names": [],
            "similar_method_names": [],
            "common_utilities": [],
            "parsing_functions": [],
            "data_transformation_functions": []
        }
        
        # Extract all functions/methods for comparison
        all_functions = []
        all_classes = []
        all_methods = []
        
        for module_path, module_info in self.inventory["modules"].items():
            # Module-level functions
            for func in module_info["functions"]:
                all_functions.append({
                    "name": func["name"],
                    "module": module_path,
                    "args": [arg["name"] for arg in func["arguments"]],
                    "docstring": func.get("docstring", "")
                })
            
            # Classes
            for cls in module_info["classes"]:
                all_classes.append({
                    "name": cls["name"],
                    "module": module_path,
                    "methods": [m["name"] for m in cls["methods"]],
                    "docstring": cls.get("docstring", "")
                })
                
                # Methods
                for method in cls["methods"]:
                    all_methods.append({
                        "name": method["name"],
                        "class": cls["name"],
                        "module": module_path,
                        "args": [arg["name"] for arg in method["arguments"]],
                        "docstring": method.get("docstring", "")
                    })
        
        # Find similar function names
        function_groups = {}
        for func in all_functions:
            base_name = func["name"].lower()
            # Group by normalized name patterns
            normalized = self._normalize_function_name(base_name)
            if normalized not in function_groups:
                function_groups[normalized] = []
            function_groups[normalized].append(func)
        
        for pattern, funcs in function_groups.items():
            if len(funcs) > 1:
                duplicates["similar_function_names"].append({
                    "pattern": pattern,
                    "functions": funcs
                })
        
        # Find parsing/utility patterns
        parsing_keywords = ["parse", "extract", "clean", "normalize", "format", "convert"]
        utility_keywords = ["save", "load", "read", "write", "get", "set", "find"]
        
        for func in all_functions:
            name_lower = func["name"].lower()
            if any(keyword in name_lower for keyword in parsing_keywords):
                duplicates["parsing_functions"].append(func)
            elif any(keyword in name_lower for keyword in utility_keywords):
                duplicates["common_utilities"].append(func)
        
        return duplicates
    
    def _normalize_function_name(self, name: str) -> str:
        """Normalize function name for similarity comparison"""
        # Remove common prefixes/suffixes
        prefixes = ["get_", "set_", "is_", "has_", "can_", "should_", "parse_", "extract_", "format_"]
        suffixes = ["_data", "_value", "_result", "_info", "_utils", "_helper"]
        
        normalized = name
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        
        return normalized
    
    def save_inventory(self, output_path: Path):
        """Save inventory to JSON file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.inventory, f, indent=2, default=str)
        
        logger.info(f"Inventory saved to {output_path}")
        
        # Also save duplicates analysis
        duplicates = self.identify_semantic_duplicates()
        duplicates_path = output_path.parent / f"{output_path.stem}_duplicates.json"
        
        with open(duplicates_path, 'w') as f:
            json.dump(duplicates, f, indent=2, default=str)
        
        logger.info(f"Duplicates analysis saved to {duplicates_path}")


def main():
    """Generate comprehensive codebase inventory"""
    root_path = Path("/Users/Mike/trading/algos/EOD")
    output_path = root_path / "codebase_inventory.json"
    
    inventory = CodeInventory()
    result = inventory.scan_codebase(root_path, ["*.py"])
    inventory.save_inventory(output_path)
    
    # Print summary
    metadata = result["analysis_metadata"]
    print(f"\nCodebase Inventory Complete:")
    print(f"  Modules analyzed: {metadata['total_modules']}")
    print(f"  Classes found: {metadata['total_classes']}")
    print(f"  Functions found: {metadata['total_functions']}")
    print(f"  Methods found: {metadata['total_methods']}")
    print(f"\nInventory saved to: {output_path}")


if __name__ == "__main__":
    main()