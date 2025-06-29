#!/usr/bin/env python3
"""
Base components for the options trading system
Provides common functionality to reduce duplication
"""

from typing import Dict, Any


class ConfigurableComponent:
    """Base class for components that accept configuration"""
    
    def __init__(self, config: Dict[str, Any], results_attr_name: str = None):
        """
        Initialize component with configuration
        
        Args:
            config: Configuration dictionary for the component
            results_attr_name: Name of the results attribute to initialize (e.g., 'system_results')
        """
        self.config = config
        
        # Initialize results attribute if name provided
        if results_attr_name:
            setattr(self, results_attr_name, {})
        
        self._initialize_results()
    
    def _initialize_results(self):
        """Initialize results storage - override in subclasses if needed"""
        pass