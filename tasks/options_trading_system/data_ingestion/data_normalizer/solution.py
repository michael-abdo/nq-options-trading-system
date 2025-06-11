#!/usr/bin/env python3
"""
TASK: data_normalizer
TYPE: Leaf Task
PURPOSE: Normalize data from different sources into standard format
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

# Import sibling tasks
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from barchart_saved_data.solution import load_barchart_saved_data
from tradovate_api_data.solution import load_tradovate_api_data


class DataNormalizer:
    """Normalize options data from various sources into standard format"""
    
    def __init__(self):
        """Initialize the data normalizer"""
        self.sources = {}
        self.normalized_data = None
        self.metadata = {
            "normalizer_version": "1.0",
            "normalized_at": None
        }
    
    def load_barchart_data(self, file_path: str) -> Dict[str, Any]:
        """Load data from Barchart source"""
        result = load_barchart_saved_data(file_path)
        self.sources['barchart'] = result
        return result
    
    def load_tradovate_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Load data from Tradovate source"""
        result = load_tradovate_api_data(config)
        self.sources['tradovate'] = result
        return result
    
    def add_loaded_source(self, source_name: str, source_data: Dict[str, Any]) -> None:
        """
        Add already loaded source data
        
        Args:
            source_name: Name of the source
            source_data: Already loaded data from that source
        """
        self.sources[source_name] = source_data
    
    def normalize_contract(self, contract_data: Dict, source: str, contract_type: str, underlying_price: Optional[float] = None) -> Dict[str, Any]:
        """
        Normalize a single contract to standard format
        
        Args:
            contract_data: Raw contract data
            source: Data source name
            contract_type: 'call' or 'put'
            underlying_price: Price of underlying asset
            
        Returns:
            Normalized contract dict
        """
        normalized = {
            "source": source,
            "type": contract_type,
            "symbol": None,
            "strike": None,
            "expiration": None,
            "volume": None,
            "open_interest": None,
            "last_price": None,
            "bid": None,
            "ask": None,
            "underlying_price": underlying_price,
            "timestamp": datetime.now().isoformat()
        }
        
        if source == "barchart":
            # Extract from Barchart format
            raw = contract_data.get('raw', {})
            normalized.update({
                "symbol": contract_data.get('symbol', ''),
                "strike": float(raw.get('strike', 0)),
                "expiration": "2025-06-30",  # Default for now
                "volume": raw.get('volume'),
                "open_interest": raw.get('openInterest'),
                "last_price": raw.get('lastPrice'),
                "underlying_price": underlying_price or 21376.75  # From saved data
            })
            
        elif source == "tradovate":
            # Extract from Tradovate format
            normalized.update({
                "symbol": contract_data.get('symbol', ''),
                "strike": contract_data.get('strike'),
                "expiration": contract_data.get('expiration'),
                "volume": contract_data.get('volume'),
                "open_interest": contract_data.get('openInterest'),
                "last_price": contract_data.get('lastPrice'),
                "bid": contract_data.get('bid'),
                "ask": contract_data.get('ask')
            })
            
        elif source == "polygon":
            # Extract from Polygon format
            normalized.update({
                "symbol": contract_data.get('contract_symbol', ''),
                "strike": contract_data.get('strike_price', 0),
                "expiration": contract_data.get('expiration_date', ''),
                "volume": contract_data.get('volume', 0),
                "open_interest": contract_data.get('open_interest', 0),
                "last_price": contract_data.get('close', contract_data.get('last_quote', {}).get('last', 0)),
                "bid": contract_data.get('last_quote', {}).get('bid', 0),
                "ask": contract_data.get('last_quote', {}).get('ask', 0)
            })
            
        elif source == "databento":
            # Extract from Databento format
            normalized.update({
                "symbol": contract_data.get('symbol', ''),
                "strike": contract_data.get('strike', 0),
                "expiration": contract_data.get('expiration', ''),
                "volume": contract_data.get('volume', 0),
                "open_interest": contract_data.get('open_interest', 0),
                "last_price": contract_data.get('avg_price', contract_data.get('last_price', 0)),
                "bid": contract_data.get('bid', 0),
                "ask": contract_data.get('ask', 0)
            })
        
        else:
            # Generic extraction for unknown sources
            # Try common field names
            normalized.update({
                "symbol": contract_data.get('symbol', contract_data.get('contract_symbol', '')),
                "strike": float(contract_data.get('strike', contract_data.get('strike_price', 0))),
                "expiration": contract_data.get('expiration', contract_data.get('expiration_date', '')),
                "volume": contract_data.get('volume', 0),
                "open_interest": contract_data.get('open_interest', contract_data.get('openInterest', 0)),
                "last_price": contract_data.get('last_price', contract_data.get('lastPrice', 0)),
                "bid": contract_data.get('bid', contract_data.get('bid_price', 0)),
                "ask": contract_data.get('ask', contract_data.get('ask_price', 0))
            })
        
        return normalized
    
    def normalize_all_sources(self) -> Dict[str, Any]:
        """
        Normalize data from all loaded sources
        
        Returns:
            Dict with normalized data from all sources
        """
        if not self.sources:
            raise ValueError("No data sources loaded")
        
        normalized = {
            "sources": [],
            "contracts": [],
            "summary": {
                "total_contracts": 0,
                "sources_count": 0,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Process each source
        for source_name, source_data in self.sources.items():
            normalized["sources"].append(source_name)
            
            # Get options data from various possible locations
            options_data = None
            
            if source_name in ["barchart", "tradovate"]:
                # Legacy sources with loader pattern
                loader = source_data.get('loader')
                if loader and hasattr(loader, 'get_options_data'):
                    options_data = loader.get_options_data()
                else:
                    # Try direct options_summary
                    options_data = source_data.get('options_summary', {})
            else:
                # New sources (polygon, databento) use options_summary directly
                options_data = source_data.get('options_summary', {})
            
            if not options_data:
                continue
            
            # Get underlying price if available
            underlying_price = None
            if 'metadata' in source_data:
                underlying_price = source_data['metadata'].get('underlying_price')
            
            # Process calls
            calls = options_data.get('calls', [])
            for call in calls:
                norm_contract = self.normalize_contract(call, source_name, "call", underlying_price)
                if norm_contract['strike'] > 0:  # Valid contract
                    normalized["contracts"].append(norm_contract)
            
            # Process puts
            puts = options_data.get('puts', [])
            for put in puts:
                norm_contract = self.normalize_contract(put, source_name, "put", underlying_price)
                if norm_contract['strike'] > 0:  # Valid contract
                    normalized["contracts"].append(norm_contract)
        
        # Update summary
        normalized["summary"]["total_contracts"] = len(normalized["contracts"])
        normalized["summary"]["sources_count"] = len(normalized["sources"])
        
        # Group by source for summary
        by_source = {}
        for contract in normalized["contracts"]:
            source = contract["source"]
            if source not in by_source:
                by_source[source] = {"calls": 0, "puts": 0, "total": 0}
            
            by_source[source]["total"] += 1
            if contract["type"] == "call":
                by_source[source]["calls"] += 1
            else:
                by_source[source]["puts"] += 1
        
        normalized["summary"]["by_source"] = by_source
        
        self.normalized_data = normalized
        self.metadata["normalized_at"] = datetime.now().isoformat()
        
        return normalized
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """Calculate quality metrics for normalized data"""
        if not self.normalized_data:
            raise ValueError("No normalized data available")
        
        contracts = self.normalized_data["contracts"]
        total = len(contracts)
        
        # Count contracts with data
        with_volume = sum(1 for c in contracts if c["volume"] is not None and c["volume"] > 0)
        with_oi = sum(1 for c in contracts if c["open_interest"] is not None and c["open_interest"] > 0)
        with_price = sum(1 for c in contracts if c["last_price"] is not None and c["last_price"] > 0)
        
        # Calculate metrics by source
        source_metrics = {}
        for source in self.normalized_data["sources"]:
            source_contracts = [c for c in contracts if c["source"] == source]
            source_total = len(source_contracts)
            
            if source_total > 0:
                source_metrics[source] = {
                    "total": source_total,
                    "volume_coverage": sum(1 for c in source_contracts if c["volume"] and c["volume"] > 0) / source_total,
                    "oi_coverage": sum(1 for c in source_contracts if c["open_interest"] and c["open_interest"] > 0) / source_total,
                    "price_coverage": sum(1 for c in source_contracts if c["last_price"] and c["last_price"] > 0) / source_total
                }
        
        return {
            "total_contracts": total,
            "overall_volume_coverage": with_volume / total if total > 0 else 0,
            "overall_oi_coverage": with_oi / total if total > 0 else 0,
            "overall_price_coverage": with_price / total if total > 0 else 0,
            "by_source": source_metrics,
            "sources": list(source_metrics.keys())
        }


# Module-level function for easy integration
def normalize_options_data(sources_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize options data from configured sources
    
    Args:
        sources_config: Dict with source configurations
        
    Returns:
        Dict with normalized data and metrics
    """
    normalizer = DataNormalizer()
    
    # Load data from each configured source
    if "barchart" in sources_config:
        normalizer.load_barchart_data(sources_config["barchart"]["file_path"])
    
    if "tradovate" in sources_config:
        normalizer.load_tradovate_data(sources_config["tradovate"])
    
    # Normalize all data
    normalized = normalizer.normalize_all_sources()
    
    # Get quality metrics
    quality_metrics = normalizer.get_quality_metrics()
    
    return {
        "normalizer": normalizer,
        "normalized_data": normalized,
        "quality_metrics": quality_metrics,
        "metadata": normalizer.metadata
    }

def normalize_loaded_data(loaded_sources: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize already loaded options data from multiple sources
    
    Args:
        loaded_sources: Dict with already loaded source data from integration.py
                       Format: {source_name: {"data": source_data, "status": "success"}}
        
    Returns:
        Dict with normalized data and metrics
    """
    normalizer = DataNormalizer()
    
    # Add each loaded source to normalizer
    for source_name, source_result in loaded_sources.items():
        if source_result.get("status") == "success" and "data" in source_result:
            normalizer.add_loaded_source(source_name, source_result["data"])
    
    # Normalize all data
    normalized = normalizer.normalize_all_sources()
    
    # Get quality metrics
    quality_metrics = normalizer.get_quality_metrics()
    
    return {
        "normalizer": normalizer,
        "normalized_data": normalized,
        "quality_metrics": quality_metrics,
        "metadata": normalizer.metadata
    }