#!/usr/bin/env python3
"""
Base components for the options trading system
Provides common functionality to reduce duplication
"""

from typing import Dict, Any


class ConfigurableComponent:
    """Base class for components that accept configuration"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize component with configuration
        
        Args:
            config: Configuration dictionary for the component
        """
        self.config = config
        self._initialize_results()
    
    def _initialize_results(self):
        """Initialize results storage - override in subclasses"""
        pass