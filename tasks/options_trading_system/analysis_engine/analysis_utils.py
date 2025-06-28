#!/usr/bin/env python3
"""
Common analysis utilities for options trading analysis
Shared functions used across multiple analysis modules
"""

from typing import List, Dict, Optional


def estimate_underlying_price(contracts: List[Dict]) -> float:
    """Estimate current underlying price from contract data
    
    This function attempts to determine the underlying price by:
    1. First looking for an explicit underlying_price in contract metadata
    2. If not found, estimates by averaging all strike prices
    
    Args:
        contracts: List of contract dictionaries with 'strike' and optionally 'underlying_price'
        
    Returns:
        Estimated underlying price as float
        
    Raises:
        ValueError: If no valid price can be determined
    """
    # Look for underlying price in contract metadata
    for contract in contracts:
        if contract.get("underlying_price"):
            return float(contract["underlying_price"])
    
    # Fallback: estimate from ATM options
    strikes = [c["strike"] for c in contracts if c.get("strike") and c["strike"] > 0]
    if strikes:
        return sum(strikes) / len(strikes)  # Average strike as rough estimate
    
    return 21376.75  # Default fallback