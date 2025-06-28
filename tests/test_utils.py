#!/usr/bin/env python3
"""
Common test utilities to avoid code duplication across test files
"""

import os
import json


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