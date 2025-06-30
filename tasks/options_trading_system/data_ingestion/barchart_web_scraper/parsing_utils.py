#!/usr/bin/env python3
"""
Unified parsing utilities for OCR and data processing.
Consolidates duplicate parsing logic from multiple modules.
"""

from typing import Optional, Union
import re


class ParsingUtils:
    """Centralized parsing utilities for options data."""
    
    @staticmethod
    def parse_price(value: str) -> Optional[float]:
        """Parse price value, handling N/A and various formats.
        
        Args:
            value: Price string (e.g., "19,244.75", "N/A", "+84.50")
            
        Returns:
            Parsed float value or None for N/A
        """
        if not value or value == 'N/A':
            return None
            
        # Remove 's' suffix (settlement indicator) and +/- prefix
        cleaned = value.rstrip('s').lstrip('+-')
        
        try:
            return float(cleaned.replace(',', ''))
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    def parse_strike(value: str) -> Optional[float]:
        """Parse strike price, removing commas and option type suffixes.
        
        Args:
            value: Strike string (e.g., "3,500.00C", "20,000.00P")
            
        Returns:
            Parsed strike price as float
        """
        if not value or value == 'N/A':
            return None
            
        # Remove commas and C/P suffixes
        cleaned = value.replace(',', '').replace('C', '').replace('P', '')
        
        try:
            return float(cleaned)
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    def parse_volume_or_oi(value: str) -> Optional[int]:
        """Parse volume or open interest value.
        
        Args:
            value: Volume/OI string (e.g., "150", "N/A", "1,250")
            
        Returns:
            Parsed integer value or None for N/A
        """
        if not value or value == 'N/A':
            return None
            
        try:
            return int(value.replace(',', ''))
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    def clean_contract_field(value: str) -> str:
        """Clean contract field value for consistent processing.
        
        Args:
            value: Raw field value
            
        Returns:
            Cleaned string value
        """
        if not value:
            return "N/A"
            
        return str(value).strip()
    
    @staticmethod
    def extract_option_type(strike_str: str) -> str:
        """Extract option type (Call/Put) from strike string.
        
        Args:
            strike_str: Strike string with type suffix (e.g., "3,500.00C")
            
        Returns:
            "Call" or "Put"
        """
        if not strike_str:
            return "Call"
            
        return "Call" if strike_str.endswith('C') else "Put"
    
    @staticmethod
    def format_strike_with_type(strike: float, option_type: str) -> str:
        """Format strike price with option type suffix.
        
        Args:
            strike: Strike price as float
            option_type: "Call" or "Put"
            
        Returns:
            Formatted string (e.g., "3,500.00C")
        """
        suffix = "C" if option_type == "Call" else "P"
        return f"{strike:,.2f}{suffix}"
    
    @staticmethod
    def is_valid_price(value: Union[str, float, None]) -> bool:
        """Check if a value represents a valid price.
        
        Args:
            value: Price value to validate
            
        Returns:
            True if valid price, False otherwise
        """
        if value is None or value == "N/A":
            return True  # N/A is valid
            
        try:
            price = float(str(value).replace(',', ''))
            return price >= 0
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def normalize_contract_data(raw_data: dict) -> dict:
        """Normalize raw contract data to standard format.
        
        Args:
            raw_data: Raw contract data dictionary
            
        Returns:
            Normalized contract data
        """
        return {
            "strike": ParsingUtils.parse_strike(raw_data.get("strike", "")),
            "optionType": ParsingUtils.extract_option_type(raw_data.get("strike", "")),
            "lastPrice": ParsingUtils.parse_price(raw_data.get("lastPrice", "")),
            "bidPrice": ParsingUtils.parse_price(raw_data.get("bidPrice", "")),
            "askPrice": ParsingUtils.parse_price(raw_data.get("askPrice", "")),
            "volume": ParsingUtils.parse_volume_or_oi(raw_data.get("volume", "")),
            "openInterest": ParsingUtils.parse_volume_or_oi(raw_data.get("openInterest", "")),
            "premium": ParsingUtils.parse_price(raw_data.get("premium", ""))
        }


# Backward compatibility - module-level functions
parse_price = ParsingUtils.parse_price
parse_strike = ParsingUtils.parse_strike  
parse_volume = ParsingUtils.parse_volume_or_oi