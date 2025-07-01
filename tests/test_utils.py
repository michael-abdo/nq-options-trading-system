#!/usr/bin/env python3
"""
Common test utilities to avoid code duplication across test files
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List


class BaseTestValidator:
    """Base class to eliminate duplicate test validation patterns"""
    
    def __init__(self, task_name: str):
        self.task_name = task_name
        self.validation_results = {
            "task": task_name,
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "status": "FAILED",
            "evidence": {}
        }
    
    def start_validation(self):
        """Standard validation header"""
        print(f"EXECUTING VALIDATION: {self.task_name}")
        print("-" * 50)
    
    def add_test_result(self, name: str, passed: bool, details: Any = None, error: str = None):
        """Add a test result to validation results"""
        test_result = {
            "name": name,
            "passed": passed
        }
        
        if details is not None:
            test_result["details"] = details
        if error is not None:
            test_result["error"] = error
            
        self.validation_results["tests"].append(test_result)
    
    def add_evidence(self, key: str, value: Any):
        """Add evidence to validation results"""
        self.validation_results["evidence"][key] = value
    
    def complete_validation(self) -> Dict[str, Any]:
        """Finalize validation and determine status"""
        all_passed = all(test['passed'] for test in self.validation_results['tests'])
        self.validation_results['status'] = "VALIDATED" if all_passed else "FAILED"
        
        # Summary
        print("\n" + "-" * 50)
        print(f"VALIDATION COMPLETE: {self.validation_results['status']}")
        print(f"Tests passed: {sum(1 for t in self.validation_results['tests'] if t['passed'])}/{len(self.validation_results['tests'])}")
        
        return self.validation_results
    
    def run_test(self, test_name: str, test_func, *args, **kwargs):
        """Run a single test with standardized error handling"""
        print(f"\n{len(self.validation_results['tests']) + 1}. Testing {test_name}...")
        
        try:
            result = test_func(*args, **kwargs)
            if isinstance(result, tuple) and len(result) == 2:
                passed, details = result
                self.add_test_result(test_name, passed, details)
                print(f"   {'✓' if passed else '✗'} {details}")
            else:
                self.add_test_result(test_name, True, result)
                print(f"   ✓ {test_name} completed")
        except Exception as e:
            self.add_test_result(test_name, False, error=str(e))
            print(f"   ✗ Error: {e}")
            
        return self.validation_results['tests'][-1]['passed']


def save_evidence(validation_results):
    """Save validation evidence to evidence.json
    
    This function is used across all test validation files to save
    validation results in a consistent format.
    
    Args:
        validation_results: Dict containing validation results to save
        
    The evidence.json file is saved in the same directory as the calling module.
    """
    # Get the calling module's directory
    import inspect
    frame = inspect.currentframe()
    caller_frame = frame.f_back
    caller_file = caller_frame.f_globals.get('__file__', '.')
    evidence_path = os.path.join(os.path.dirname(caller_file), "evidence.json")
    
    with open(evidence_path, 'w') as f:
        json.dump(validation_results, f, indent=2)