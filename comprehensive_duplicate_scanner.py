#!/usr/bin/env python3
"""
Comprehensive Duplicate Functionality Scanner
Focuses on semantic duplicates across production code
"""

import os
import ast
import json
import re
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
import hashlib

class DuplicateScanner:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.results = {
            'calculation_methods': [],
            'api_request_patterns': [],
            'data_transformation': [],
            'config_loading': [],
            'error_handling': [],
            'logging_setup': [],
            'class_initialization': [],
            'constants_configs': [],
            'file_io_patterns': [],
            'validation_patterns': []
        }
        
    def scan_all(self) -> Dict[str, Any]:
        """Run comprehensive duplicate scan"""
        print("Starting comprehensive duplicate scan...")
        
        # Get all Python files excluding tests
        python_files = self._get_python_files()
        print(f"Found {len(python_files)} Python files to analyze")
        
        # Analyze each file
        for file_path in python_files:
            try:
                self._analyze_file(file_path)
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
                
        # Generate similarity reports
        self._generate_similarity_reports()
        
        return self.results
    
    def _get_python_files(self) -> List[str]:
        """Get all Python files excluding test files"""
        python_files = []
        exclude_patterns = [
            'test_', 'tests/', '/test', 'venv/', 'env/', 
            '__pycache__', '.git/', 'node_modules/',
            'archive/', 'legacy_', 'outputs/', 
            'cookies/', 'dashboard_env/', 'testing_env/'
        ]
        
        for root, dirs, files in os.walk(self.root_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    # Skip test files and excluded patterns
                    if not any(pattern in file_path for pattern in exclude_patterns):
                        python_files.append(file_path)
                        
        return python_files
    
    def _analyze_file(self, file_path: str):
        """Analyze a single Python file for duplicate patterns"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse AST
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return
                
            # Analyze different aspects
            self._analyze_calculations(file_path, tree, content)
            self._analyze_api_patterns(file_path, tree, content)
            self._analyze_data_transformation(file_path, tree, content)
            self._analyze_config_loading(file_path, tree, content)
            self._analyze_error_handling(file_path, tree, content)
            self._analyze_logging_setup(file_path, tree, content)
            self._analyze_class_initialization(file_path, tree, content)
            self._analyze_constants(file_path, tree, content)
            self._analyze_file_io(file_path, tree, content)
            self._analyze_validation_patterns(file_path, tree, content)
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    def _analyze_calculations(self, file_path: str, tree: ast.AST, content: str):
        """Find calculation methods and mathematical operations"""
        calculations = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Look for calculation keywords
                calc_keywords = ['calculate', 'compute', 'analyze', 'process', 'estimate', 'risk', 'expected_value', 'probability']
                
                if any(keyword in node.name.lower() for keyword in calc_keywords):
                    # Extract function signature and body
                    func_info = {
                        'name': node.name,
                        'args': [arg.arg for arg in node.args.args],
                        'line': node.lineno,
                        'body_lines': node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                    }
                    
                    # Get function body for similarity analysis
                    lines = content.split('\n')
                    if node.lineno <= len(lines):
                        func_body = '\n'.join(lines[node.lineno-1:node.end_lineno if hasattr(node, 'end_lineno') else node.lineno+10])
                        func_info['body_hash'] = hashlib.md5(func_body.encode()).hexdigest()
                        func_info['normalized_body'] = self._normalize_code(func_body)
                    
                    calculations.append(func_info)
        
        if calculations:
            self.results['calculation_methods'].append({
                'file': file_path,
                'functions': calculations
            })
    
    def _analyze_api_patterns(self, file_path: str, tree: ast.AST, content: str):
        """Find API request patterns"""
        api_patterns = []
        
        # Look for common API patterns
        api_keywords = ['requests.', 'urllib', 'httpx', 'aiohttp', 'get(', 'post(', 'put(', 'delete(']
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_str = ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
                
                if any(keyword in call_str for keyword in api_keywords):
                    api_patterns.append({
                        'line': node.lineno,
                        'call': call_str[:200],  # Truncate for readability
                        'type': self._classify_api_call(call_str)
                    })
        
        # Also look for URL patterns and headers
        url_patterns = re.findall(r'["\']https?://[^"\']+["\']', content)
        header_patterns = re.findall(r'headers\s*=\s*{[^}]+}', content)
        
        if api_patterns or url_patterns or header_patterns:
            self.results['api_request_patterns'].append({
                'file': file_path,
                'calls': api_patterns,
                'urls': url_patterns,
                'headers': header_patterns
            })
    
    def _analyze_data_transformation(self, file_path: str, tree: ast.AST, content: str):
        """Find data transformation and normalization patterns"""
        transformations = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                transform_keywords = ['transform', 'normalize', 'clean', 'process', 'convert', 'parse', 'format']
                
                if any(keyword in node.name.lower() for keyword in transform_keywords):
                    # Look for pandas operations
                    func_body = ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
                    pandas_ops = ['df[', '.drop(', '.fillna(', '.replace(', '.apply(', '.map(', '.groupby(']
                    
                    transformations.append({
                        'name': node.name,
                        'line': node.lineno,
                        'has_pandas': any(op in func_body for op in pandas_ops),
                        'normalized_body': self._normalize_code(func_body)
                    })
        
        if transformations:
            self.results['data_transformation'].append({
                'file': file_path,
                'functions': transformations
            })
    
    def _analyze_config_loading(self, file_path: str, tree: ast.AST, content: str):
        """Find configuration loading patterns"""
        config_patterns = []
        
        # Look for config loading patterns
        config_keywords = ['config', 'settings', 'env', 'load', 'read']
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if any(keyword in node.name.lower() for keyword in config_keywords):
                    config_patterns.append({
                        'name': node.name,
                        'line': node.lineno,
                        'type': 'function'
                    })
        
        # Look for environment variable access
        env_patterns = re.findall(r'os\.environ\[.*?\]|os\.getenv\(.*?\)', content)
        json_load_patterns = re.findall(r'json\.load\(.*?\)|json\.loads\(.*?\)', content)
        
        if config_patterns or env_patterns or json_load_patterns:
            self.results['config_loading'].append({
                'file': file_path,
                'functions': config_patterns,
                'env_vars': env_patterns,
                'json_loads': json_load_patterns
            })
    
    def _analyze_error_handling(self, file_path: str, tree: ast.AST, content: str):
        """Find error handling patterns"""
        error_patterns = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                handlers = []
                for handler in node.handlers:
                    exception_type = handler.type.id if hasattr(handler.type, 'id') else 'Unknown'
                    handlers.append(exception_type)
                
                error_patterns.append({
                    'line': node.lineno,
                    'exceptions': handlers,
                    'has_finally': bool(node.finalbody),
                    'has_else': bool(node.orelse)
                })
        
        if error_patterns:
            self.results['error_handling'].append({
                'file': file_path,
                'patterns': error_patterns
            })
    
    def _analyze_logging_setup(self, file_path: str, tree: ast.AST, content: str):
        """Find logging setup patterns"""
        logging_patterns = []
        
        # Look for logging setup
        logging_keywords = ['logging.', 'logger', 'getLogger', 'basicConfig', 'StreamHandler', 'FileHandler']
        
        for line_num, line in enumerate(content.split('\n'), 1):
            if any(keyword in line for keyword in logging_keywords):
                logging_patterns.append({
                    'line': line_num,
                    'content': line.strip(),
                    'type': self._classify_logging_line(line)
                })
        
        if logging_patterns:
            self.results['logging_setup'].append({
                'file': file_path,
                'patterns': logging_patterns
            })
    
    def _analyze_class_initialization(self, file_path: str, tree: ast.AST, content: str):
        """Find class initialization patterns"""
        init_patterns = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Find __init__ method
                init_method = None
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                        init_method = item
                        break
                
                if init_method:
                    init_info = {
                        'class_name': node.name,
                        'line': init_method.lineno,
                        'args': [arg.arg for arg in init_method.args.args],
                        'body_hash': hashlib.md5(ast.unparse(init_method).encode()).hexdigest() if hasattr(ast, 'unparse') else 'unknown'
                    }
                    init_patterns.append(init_info)
        
        if init_patterns:
            self.results['class_initialization'].append({
                'file': file_path,
                'classes': init_patterns
            })
    
    def _analyze_constants(self, file_path: str, tree: ast.AST, content: str):
        """Find constants and configuration values"""
        constants = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        value = ast.unparse(node.value) if hasattr(ast, 'unparse') else str(node.value)
                        constants.append({
                            'name': target.id,
                            'value': value,
                            'line': node.lineno
                        })
        
        if constants:
            self.results['constants_configs'].append({
                'file': file_path,
                'constants': constants
            })
    
    def _analyze_file_io(self, file_path: str, tree: ast.AST, content: str):
        """Find file I/O patterns"""
        io_patterns = []
        
        # Look for file operations
        io_keywords = ['open(', 'with open', 'read(', 'write(', 'json.load', 'json.dump', 'pickle.load', 'pickle.dump']
        
        for line_num, line in enumerate(content.split('\n'), 1):
            if any(keyword in line for keyword in io_keywords):
                io_patterns.append({
                    'line': line_num,
                    'content': line.strip(),
                    'type': self._classify_io_operation(line)
                })
        
        if io_patterns:
            self.results['file_io_patterns'].append({
                'file': file_path,
                'patterns': io_patterns
            })
    
    def _analyze_validation_patterns(self, file_path: str, tree: ast.AST, content: str):
        """Find validation patterns"""
        validation_patterns = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                validate_keywords = ['validate', 'check', 'verify', 'ensure', 'assert']
                
                if any(keyword in node.name.lower() for keyword in validate_keywords):
                    validation_patterns.append({
                        'name': node.name,
                        'line': node.lineno,
                        'args': [arg.arg for arg in node.args.args]
                    })
        
        if validation_patterns:
            self.results['validation_patterns'].append({
                'file': file_path,
                'functions': validation_patterns
            })
    
    def _normalize_code(self, code: str) -> str:
        """Normalize code for similarity comparison"""
        # Remove comments and docstrings
        lines = []
        for line in code.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('"""') and not line.startswith("'''"):
                # Remove variable names for better matching
                line = re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', 'VAR', line)
                lines.append(line)
        return '\n'.join(lines)
    
    def _classify_api_call(self, call_str: str) -> str:
        """Classify type of API call"""
        if 'get(' in call_str.lower():
            return 'GET'
        elif 'post(' in call_str.lower():
            return 'POST'
        elif 'put(' in call_str.lower():
            return 'PUT'
        elif 'delete(' in call_str.lower():
            return 'DELETE'
        else:
            return 'OTHER'
    
    def _classify_logging_line(self, line: str) -> str:
        """Classify type of logging line"""
        if 'getLogger' in line:
            return 'logger_creation'
        elif 'basicConfig' in line:
            return 'basic_config'
        elif 'Handler' in line:
            return 'handler_setup'
        else:
            return 'other'
    
    def _classify_io_operation(self, line: str) -> str:
        """Classify type of I/O operation"""
        if 'json.' in line:
            return 'json'
        elif 'pickle.' in line:
            return 'pickle'
        elif 'open(' in line:
            return 'file_open'
        else:
            return 'other'
    
    def _generate_similarity_reports(self):
        """Generate similarity reports for each category"""
        print("Generating similarity reports...")
        
        # Analyze calculation methods for similarity
        self._find_similar_calculations()
        self._find_similar_api_patterns()
        self._find_similar_transformations()
        self._find_similar_configs()
        self._find_similar_error_handling()
        self._find_similar_logging()
        self._find_similar_init_patterns()
        self._find_similar_constants()
        
    def _find_similar_calculations(self):
        """Find similar calculation methods"""
        all_calculations = []
        for file_data in self.results['calculation_methods']:
            for func in file_data['functions']:
                func['file'] = file_data['file']
                all_calculations.append(func)
        
        # Group by normalized body
        similarity_groups = defaultdict(list)
        for calc in all_calculations:
            if 'normalized_body' in calc:
                similarity_groups[calc['normalized_body']].append(calc)
        
        # Find duplicates
        duplicates = []
        for group in similarity_groups.values():
            if len(group) > 1:
                duplicates.append({
                    'similarity_type': 'calculation_method',
                    'functions': group,
                    'count': len(group)
                })
        
        self.results['calculation_duplicates'] = duplicates
    
    def _find_similar_api_patterns(self):
        """Find similar API request patterns"""
        # Group by URL patterns and request types
        url_groups = defaultdict(list)
        
        for file_data in self.results['api_request_patterns']:
            for url in file_data['urls']:
                url_groups[url].append(file_data['file'])
        
        duplicates = []
        for url, files in url_groups.items():
            if len(files) > 1:
                duplicates.append({
                    'similarity_type': 'api_url',
                    'url': url,
                    'files': files,
                    'count': len(files)
                })
        
        self.results['api_duplicates'] = duplicates
    
    def _find_similar_transformations(self):
        """Find similar data transformation patterns"""
        # Group by function name patterns
        name_groups = defaultdict(list)
        
        for file_data in self.results['data_transformation']:
            for func in file_data['functions']:
                name_groups[func['name']].append({
                    'file': file_data['file'],
                    'function': func
                })
        
        duplicates = []
        for name, instances in name_groups.items():
            if len(instances) > 1:
                duplicates.append({
                    'similarity_type': 'transformation_function',
                    'function_name': name,
                    'instances': instances,
                    'count': len(instances)
                })
        
        self.results['transformation_duplicates'] = duplicates
    
    def _find_similar_configs(self):
        """Find similar configuration loading patterns"""
        # Group by environment variables
        env_groups = defaultdict(list)
        
        for file_data in self.results['config_loading']:
            for env_var in file_data['env_vars']:
                env_groups[env_var].append(file_data['file'])
        
        duplicates = []
        for env_var, files in env_groups.items():
            if len(files) > 1:
                duplicates.append({
                    'similarity_type': 'env_variable',
                    'env_var': env_var,
                    'files': files,
                    'count': len(files)
                })
        
        self.results['config_duplicates'] = duplicates
    
    def _find_similar_error_handling(self):
        """Find similar error handling patterns"""
        pattern_groups = defaultdict(list)
        
        for file_data in self.results['error_handling']:
            for pattern in file_data['patterns']:
                key = tuple(sorted(pattern['exceptions']))
                pattern_groups[key].append({
                    'file': file_data['file'],
                    'pattern': pattern
                })
        
        duplicates = []
        for exceptions, instances in pattern_groups.items():
            if len(instances) > 1:
                duplicates.append({
                    'similarity_type': 'error_handling',
                    'exceptions': list(exceptions),
                    'instances': instances,
                    'count': len(instances)
                })
        
        self.results['error_handling_duplicates'] = duplicates
    
    def _find_similar_logging(self):
        """Find similar logging setup patterns"""
        pattern_groups = defaultdict(list)
        
        for file_data in self.results['logging_setup']:
            for pattern in file_data['patterns']:
                # Normalize the logging line
                normalized = re.sub(r'["\'].*?["\']', 'STRING', pattern['content'])
                pattern_groups[normalized].append({
                    'file': file_data['file'],
                    'pattern': pattern
                })
        
        duplicates = []
        for normalized, instances in pattern_groups.items():
            if len(instances) > 1:
                duplicates.append({
                    'similarity_type': 'logging_setup',
                    'normalized_pattern': normalized,
                    'instances': instances,
                    'count': len(instances)
                })
        
        self.results['logging_duplicates'] = duplicates
    
    def _find_similar_init_patterns(self):
        """Find similar class initialization patterns"""
        pattern_groups = defaultdict(list)
        
        for file_data in self.results['class_initialization']:
            for cls in file_data['classes']:
                # Group by argument signature
                arg_signature = tuple(cls['args'])
                pattern_groups[arg_signature].append({
                    'file': file_data['file'],
                    'class': cls
                })
        
        duplicates = []
        for signature, instances in pattern_groups.items():
            if len(instances) > 1:
                duplicates.append({
                    'similarity_type': 'class_init',
                    'arg_signature': list(signature),
                    'instances': instances,
                    'count': len(instances)
                })
        
        self.results['init_duplicates'] = duplicates
    
    def _find_similar_constants(self):
        """Find similar constants across files"""
        constant_groups = defaultdict(list)
        
        for file_data in self.results['constants_configs']:
            for const in file_data['constants']:
                constant_groups[const['name']].append({
                    'file': file_data['file'],
                    'constant': const
                })
        
        duplicates = []
        for name, instances in constant_groups.items():
            if len(instances) > 1:
                # Check if values are different (potential inconsistency)
                values = [inst['constant']['value'] for inst in instances]
                if len(set(values)) > 1:
                    duplicates.append({
                        'similarity_type': 'constant_inconsistency',
                        'constant_name': name,
                        'instances': instances,
                        'count': len(instances),
                        'different_values': True
                    })
                else:
                    duplicates.append({
                        'similarity_type': 'constant_duplicate',
                        'constant_name': name,
                        'instances': instances,
                        'count': len(instances),
                        'different_values': False
                    })
        
        self.results['constant_duplicates'] = duplicates

def main():
    """Run the comprehensive duplicate scan"""
    scanner = DuplicateScanner("/Users/Mike/trading/algos/EOD")
    results = scanner.scan_all()
    
    # Save results
    output_file = "/Users/Mike/trading/algos/EOD/comprehensive_duplicate_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nScan complete! Results saved to {output_file}")
    
    # Print summary
    print("\n=== DUPLICATE ANALYSIS SUMMARY ===")
    
    duplicate_categories = [
        'calculation_duplicates', 'api_duplicates', 'transformation_duplicates',
        'config_duplicates', 'error_handling_duplicates', 'logging_duplicates',
        'init_duplicates', 'constant_duplicates'
    ]
    
    total_duplicates = 0
    for category in duplicate_categories:
        if category in results and results[category]:
            count = len(results[category])
            total_duplicates += count
            print(f"{category}: {count} duplicate groups found")
    
    print(f"\nTotal duplicate groups found: {total_duplicates}")
    
    # Show top duplicates
    if total_duplicates > 0:
        print("\n=== TOP DUPLICATE PATTERNS ===")
        all_duplicates = []
        for category in duplicate_categories:
            if category in results:
                for dup in results[category]:
                    dup['category'] = category
                    all_duplicates.append(dup)
        
        # Sort by count (most duplicated first)
        all_duplicates.sort(key=lambda x: x['count'], reverse=True)
        
        for i, dup in enumerate(all_duplicates[:10]):  # Top 10
            print(f"{i+1}. {dup['category']}: {dup['count']} instances")
            if 'similarity_type' in dup:
                print(f"   Type: {dup['similarity_type']}")
            if 'instances' in dup:
                files = [inst['file'] for inst in dup['instances']]
                print(f"   Files: {', '.join(files[:3])}{'...' if len(files) > 3 else ''}")
            print()

if __name__ == "__main__":
    main()