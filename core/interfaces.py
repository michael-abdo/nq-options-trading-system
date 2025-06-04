#!/usr/bin/env python3
"""
Abstract interfaces for the modular trading analysis system
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from .data_models import OptionsChain, DataRequirements, AnalysisResult


class DataSourceInterface(ABC):
    """Abstract base class for all data sources"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration"""
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def fetch_data(self) -> OptionsChain:
        """
        Fetch raw data and return in standardized format
        
        Returns:
            OptionsChain: Standardized options data
            
        Raises:
            DataSourceError: If data cannot be fetched
        """
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Test if the data source is accessible
        
        Returns:
            bool: True if connection is valid
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about this data source
        
        Returns:
            Dict containing source metadata
        """
        return {
            "name": self.name,
            "config": {k: v for k, v in self.config.items() if "secret" not in k.lower()}
        }


class StrategyInterface(ABC):
    """Abstract base class for all analysis strategies"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration"""
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def analyze(self, data: OptionsChain) -> AnalysisResult:
        """
        Perform analysis on options chain data
        
        Args:
            data: Standardized options chain data
            
        Returns:
            AnalysisResult: Analysis results and signals
            
        Raises:
            StrategyError: If analysis cannot be performed
        """
        pass
    
    @abstractmethod
    def get_requirements(self) -> DataRequirements:
        """
        Get data requirements for this strategy
        
        Returns:
            DataRequirements: What data this strategy needs
        """
        pass
    
    def validate_data(self, data: OptionsChain) -> tuple[bool, List[str]]:
        """
        Validate if data meets strategy requirements
        
        Args:
            data: Options chain data to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        requirements = self.get_requirements()
        return requirements.validate_data(data)
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about this strategy
        
        Returns:
            Dict containing strategy metadata
        """
        return {
            "name": self.name,
            "requirements": self.get_requirements(),
            "config": self.config
        }


class OutputInterface(ABC):
    """Abstract base class for output formatters"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration"""
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def format_results(self, results: List[AnalysisResult], metadata: Dict[str, Any] = None) -> str:
        """
        Format analysis results for output
        
        Args:
            results: List of analysis results from strategies
            metadata: Additional metadata to include
            
        Returns:
            str: Formatted output
        """
        pass
    
    @abstractmethod
    def save_results(self, results: List[AnalysisResult], filename: str = None) -> str:
        """
        Save analysis results to file
        
        Args:
            results: List of analysis results
            filename: Optional filename (auto-generated if None)
            
        Returns:
            str: Path to saved file
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """Get information about this output formatter"""
        return {
            "name": self.name,
            "config": self.config
        }


# Custom exceptions
class DataSourceError(Exception):
    """Raised when data source operations fail"""
    pass


class StrategyError(Exception):
    """Raised when strategy analysis fails"""
    pass


class OutputError(Exception):
    """Raised when output formatting fails"""
    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid"""
    pass