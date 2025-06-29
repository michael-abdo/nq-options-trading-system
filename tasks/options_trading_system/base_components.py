#!/usr/bin/env python3
"""
Base components for the options trading system
Provides common functionality to reduce duplication
"""

from typing import Dict, Any


class ConfigurableComponent:
    """Base class for components that accept configuration"""
    
    # Class attribute that subclasses can override
    _results_attr_name: str = None
    
    def __init__(self, config: Dict[str, Any], results_attr_name: str = None):
        """
        Initialize component with configuration
        
        Args:
            config: Configuration dictionary for the component
            results_attr_name: Name of the results attribute to initialize (e.g., 'system_results')
                              If not provided, uses class attribute _results_attr_name
        """
        self.config = config
        
        # Use provided results_attr_name or fall back to class attribute
        attr_name = results_attr_name or getattr(self.__class__, '_results_attr_name', None)
        
        # Initialize results attribute if name provided
        if attr_name:
            setattr(self, attr_name, {})
        
        self._initialize_results()
    
    def _initialize_results(self):
        """Initialize results storage - override in subclasses if needed"""
        pass