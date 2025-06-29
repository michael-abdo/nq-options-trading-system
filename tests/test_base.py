"""
Base test class for common test patterns in the options trading system.

This module provides a flexible BaseTestCase that eliminates duplicate setUp
boilerplate while allowing customization for specific test needs.
"""

import unittest
from typing import Dict, Any, List, Tuple, Optional, Type
import time
from unittest.mock import Mock, patch


class BaseTestCase(unittest.TestCase):
    """
    Base test class that provides flexible setUp patterns.
    
    Subclasses can configure their test fixtures using class attributes:
    - solution_classes: List of (attr_name, class, args_dict) tuples
    - mock_patches: List of patch strings to apply
    - test_data: Dict of test data to set as attributes
    """
    
    # Class attributes that subclasses should override
    solution_classes: List[Tuple[str, Type, Dict[str, Any]]] = []
    mock_patches: List[str] = []
    test_data: Dict[str, Any] = {}
    
    def setUp(self):
        """Common setUp that instantiates configured classes and applies patches."""
        # Apply any mock patches
        self.patches = []
        for patch_target in self.mock_patches:
            patcher = patch(patch_target)
            self.patches.append(patcher)
            patcher.start()
        
        # Instantiate solution classes
        for attr_name, cls, kwargs in self.solution_classes:
            try:
                instance = cls(**kwargs)
                setattr(self, attr_name, instance)
            except Exception as e:
                # Allow conditional instantiation (e.g., API availability)
                if hasattr(self, f'skip_if_{attr_name}_fails'):
                    self.skipTest(f"Could not instantiate {cls.__name__}: {e}")
                else:
                    raise
        
        # Set any test data attributes
        for key, value in self.test_data.items():
            setattr(self, key, value)
    
    def tearDown(self):
        """Stop all patches."""
        for patcher in self.patches:
            patcher.stop()


class OptionsAnalysisTestCase(BaseTestCase):
    """Base class for options analysis component tests."""
    
    def assert_analysis_valid(self, result: Dict[str, Any], min_setups: int = 1):
        """Common assertion for analysis results."""
        self.assertIsInstance(result, dict)
        self.assertIn('setups', result)
        self.assertGreaterEqual(len(result.get('setups', [])), min_setups)
    
    def create_sample_contracts(self, count: int = 5) -> List[Dict[str, Any]]:
        """Create sample options contracts for testing."""
        contracts = []
        base_strike = 15000
        for i in range(count):
            contracts.append({
                'strike': base_strike + (i * 25),
                'call_oi': 1000 + (i * 500),
                'put_oi': 800 + (i * 300),
                'volume': 100 + (i * 50)
            })
        return contracts


class DataIngestionTestCase(BaseTestCase):
    """Base class for data ingestion component tests."""
    
    def assert_data_quality(self, data: Dict[str, Any], min_coverage: float = 0.8):
        """Common assertion for data quality metrics."""
        self.assertIn('quality', data)
        quality = data['quality']
        self.assertGreaterEqual(quality.get('coverage', 0), min_coverage)
    
    def create_mock_response(self, status_code: int = 200, 
                           data: Optional[Dict] = None) -> Mock:
        """Create a mock HTTP response."""
        response = Mock()
        response.status_code = status_code
        response.json.return_value = data or {'status': 'ok'}
        return response


class RealTimeTestCase(BaseTestCase):
    """Base class for real-time component tests with timing utilities."""
    
    def measure_latency(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure execution latency of a function."""
        start = time.time()
        result = func(*args, **kwargs)
        latency = (time.time() - start) * 1000  # Convert to ms
        return result, latency
    
    def assert_latency_under(self, func, max_ms: float, *args, **kwargs):
        """Assert that function executes within latency threshold."""
        result, latency = self.measure_latency(func, *args, **kwargs)
        self.assertLess(latency, max_ms, 
                       f"Latency {latency:.2f}ms exceeds max {max_ms}ms")
        return result