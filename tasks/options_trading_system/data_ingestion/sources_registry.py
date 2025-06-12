#!/usr/bin/env python3
"""
Data Sources Registry
Central registry for all available data sources and their loader functions
"""

import logging
from typing import Dict, Callable, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Import all available source loaders
try:
    from barchart_saved_data.solution import load_barchart_saved_data
    BARCHART_SAVED_AVAILABLE = True
except ImportError:
    BARCHART_SAVED_AVAILABLE = False
    logger.warning("Barchart saved data loader not available")

try:
    from tradovate_api_data.solution import load_tradovate_api_data
    TRADOVATE_AVAILABLE = True
except ImportError:
    TRADOVATE_AVAILABLE = False
    logger.warning("Tradovate API loader not available")

try:
    from polygon_api.solution import load_polygon_api_data
    POLYGON_AVAILABLE = True
except ImportError:
    POLYGON_AVAILABLE = False
    logger.warning("Polygon API loader not available")

try:
    from databento_api.solution import load_databento_api_data
    DATABENTO_AVAILABLE = True
except ImportError:
    DATABENTO_AVAILABLE = False
    logger.warning("Databento API loader not available")

# Import live API components
try:
    from barchart_web_scraper.hybrid_scraper import HybridBarchartScraper
    from barchart_web_scraper.solution import BarchartAPIComparator
    BARCHART_LIVE_AVAILABLE = True
except ImportError:
    BARCHART_LIVE_AVAILABLE = False
    logger.warning("Barchart live API components not available")


def load_barchart_live_data(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load live Barchart options data wrapper for registry
    """
    if not BARCHART_LIVE_AVAILABLE:
        raise ImportError("Live API components not available")
    
    futures_symbol = config.get("futures_symbol", "NQM25")
    headless = config.get("headless", True)
    target_symbol = config.get("target_symbol")
    
    try:
        # Get target symbol (either specified or today's EOD)
        if target_symbol:
            eod_symbol = target_symbol
            print(f"🎯 Using specified target symbol: {eod_symbol}")
        else:
            comparator = BarchartAPIComparator()
            eod_symbol = comparator.get_eod_contract_symbol()
            print(f"📅 Calculated EOD symbol: {eod_symbol}")
        
        # Use hybrid scraper to get live data
        use_cache = config.get("use_cache", True)
        scraper = HybridBarchartScraper(headless=headless, use_cache=use_cache)
        
        # Authenticate and fetch data
        if not scraper.authenticate(futures_symbol):
            raise Exception("Failed to authenticate with Barchart")
        
        api_data = scraper.fetch_options_data(eod_symbol, futures_symbol)
        
        if not api_data or api_data.get('total', 0) == 0:
            # Try monthly options as fallback
            print(f"⚠️  EOD contract {eod_symbol} not available, trying monthly option MC6M25")
            api_data = scraper.fetch_options_data("MC6M25", futures_symbol)
            
            if not api_data or api_data.get('total', 0) == 0:
                raise Exception(f"❌ No live options data available for {eod_symbol} or MC6M25. Market may be closed or contracts not listed.")
        
        result = {
            "raw_data": api_data,
            "source": "barchart_live_api",
            "symbol": eod_symbol if api_data.get('total', 0) > 0 else "MC6M25",
            "timestamp": datetime.now().isoformat(),
            "total_contracts": api_data.get('total', 0)
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Live API failed: {e}")
        raise e
    finally:
        # Clean up scraper resources
        if 'scraper' in locals():
            scraper.cleanup()


class DataSourcesRegistry:
    """
    Registry for all available data sources and their configuration
    """
    
    def __init__(self):
        """Initialize the registry with all available sources"""
        self._sources = {}
        self._source_priorities = {
            "barchart": 1,      # Primary - free web scraping
            "barchart_live": 1, # Same as barchart
            "polygon": 2,       # Secondary - free tier with limits
            "tradovate": 3,     # Tertiary - demo mode
            "databento": 4,     # Last - no GLBX.MDP3 access
            "barchart_saved": 5 # Fallback - offline data
        }
        self._register_all_sources()
    
    def _register_all_sources(self):
        """Register all available data sources"""
        
        # Barchart sources
        if BARCHART_SAVED_AVAILABLE:
            self._sources["barchart_saved"] = {
                "loader": lambda config: load_barchart_saved_data(config["file_path"]),
                "available": True,
                "type": "file_based",
                "description": "Barchart saved data files",
                "required_config": ["file_path"]
            }
        
        if BARCHART_LIVE_AVAILABLE:
            self._sources["barchart_live"] = {
                "loader": load_barchart_live_data,
                "available": True,
                "type": "api",
                "description": "Barchart live API with web scraping",
                "required_config": [],
                "optional_config": ["futures_symbol", "headless", "target_symbol"]
            }
        
        # Legacy "barchart" source that chooses between live and saved
        if BARCHART_SAVED_AVAILABLE or BARCHART_LIVE_AVAILABLE:
            self._sources["barchart"] = {
                "loader": self._load_barchart_hybrid,
                "available": True,
                "type": "hybrid",
                "description": "Barchart hybrid (live API with saved fallback)",
                "required_config": [],
                "optional_config": ["use_live_api", "file_path", "futures_symbol", "headless", "target_symbol"]
            }
        
        # Other API sources
        if TRADOVATE_AVAILABLE:
            self._sources["tradovate"] = {
                "loader": load_tradovate_api_data,
                "available": True,
                "type": "api",
                "description": "Tradovate futures/options API",
                "required_config": ["mode", "cid", "secret"]
            }
        
        if POLYGON_AVAILABLE:
            self._sources["polygon"] = {
                "loader": load_polygon_api_data,
                "available": True,
                "type": "api", 
                "description": "Polygon.io options data API",
                "required_config": ["api_key"]
            }
        
        if DATABENTO_AVAILABLE:
            self._sources["databento"] = {
                "loader": load_databento_api_data,
                "available": True,
                "type": "api",
                "description": "Databento market data API",
                "required_config": ["api_key"],
                "optional_config": ["symbols", "use_cache", "cache_dir"]
            }
    
    def _load_barchart_hybrid(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Load Barchart data using hybrid approach (live API with saved fallback)"""
        use_live_api = config.get("use_live_api", True)
        
        if use_live_api and BARCHART_LIVE_AVAILABLE:
            try:
                return load_barchart_live_data(config)
            except Exception as e:
                if config.get("file_path"):
                    print(f"⚠️ Live API failed, falling back to saved data: {e}")
                    return load_barchart_saved_data(config["file_path"])
                else:
                    raise e
        elif config.get("file_path") and BARCHART_SAVED_AVAILABLE:
            return load_barchart_saved_data(config["file_path"])
        else:
            raise ValueError("No valid Barchart configuration provided")
    
    def get_available_sources(self) -> List[str]:
        """Get list of all available source names"""
        return list(self._sources.keys())
    
    def get_sources_by_priority(self, only_available: bool = True) -> List[str]:
        """Get sources sorted by priority (lower number = higher priority)"""
        sources = self.get_available_sources() if only_available else list(self._sources.keys())
        # Sort by priority, defaulting to 999 for sources without explicit priority
        return sorted(sources, key=lambda x: self._source_priorities.get(x, 999))
    
    def load_first_available(self, config_by_source: Dict[str, Dict[str, Any]], 
                           log_attempts: bool = True) -> Dict[str, Any]:
        """
        Try to load data from sources in priority order, returning first successful result
        
        Args:
            config_by_source: Dict mapping source names to their configs
            log_attempts: Whether to log loading attempts
            
        Returns:
            Data from first successful source
            
        Raises:
            Exception if all sources fail
        """
        sources_to_try = self.get_sources_by_priority(only_available=True)
        errors = []
        
        for source_name in sources_to_try:
            if source_name not in config_by_source:
                continue
                
            if not config_by_source[source_name].get('enabled', True):
                if log_attempts:
                    print(f"⏭️  Skipping {source_name} (disabled in config)")
                continue
            
            try:
                if log_attempts:
                    priority = self._source_priorities.get(source_name, 999)
                    print(f"🔍 Trying {source_name} (priority {priority})...")
                
                result = self.load_source(source_name, config_by_source[source_name])
                
                # Check for data in different formats
                has_data = False
                if result:
                    # Standard format
                    if result.get('options_summary', {}).get('total_contracts', 0) > 0:
                        has_data = True
                    # Live API format (barchart)
                    elif result.get('total_contracts', 0) > 0:
                        has_data = True
                    # Check raw_data
                    elif result.get('raw_data', {}).get('total', 0) > 0:
                        has_data = True
                
                if has_data:
                    if log_attempts:
                        print(f"✅ Successfully loaded data from {source_name}")
                    return result
                else:
                    if log_attempts:
                        print(f"⚠️  {source_name} returned no data")
                    
            except Exception as e:
                error_msg = str(e)
                errors.append(f"{source_name}: {error_msg}")
                
                # Special handling for Databento access issues
                if source_name == "databento" and "GLBX.MDP3" in error_msg:
                    if log_attempts:
                        print(f"🚫 {source_name}: No GLBX.MDP3 access (subscription required)")
                else:
                    if log_attempts:
                        print(f"❌ {source_name} failed: {error_msg}")
        
        # All sources failed
        raise Exception(f"All data sources failed:\n" + "\n".join(errors))
    
    def get_source_info(self, source_name: str) -> Dict[str, Any]:
        """Get information about a specific source"""
        if source_name not in self._sources:
            raise ValueError(f"Unknown source: {source_name}")
        return self._sources[source_name].copy()
    
    def is_source_available(self, source_name: str) -> bool:
        """Check if a source is available"""
        return source_name in self._sources and self._sources[source_name]["available"]
    
    def load_source(self, source_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Load data from a specific source"""
        if not self.is_source_available(source_name):
            raise ValueError(f"Source not available: {source_name}")
        
        source_info = self._sources[source_name]
        
        # Validate required config
        required_config = source_info.get("required_config", [])
        for required_field in required_config:
            if required_field not in config:
                raise ValueError(f"Missing required config for {source_name}: {required_field}")
        
        # Load the data
        try:
            print(f"🔄 Loading data from {source_name}...")
            loader = source_info["loader"]
            return loader(config)
        except Exception as e:
            print(f"❌ Failed to load from {source_name}: {e}")
            raise e
    
    def get_registry_summary(self) -> Dict[str, Any]:
        """Get summary of the entire registry"""
        return {
            "total_sources": len(self._sources),
            "available_sources": self.get_available_sources(),
            "source_types": {
                source_name: info["type"] 
                for source_name, info in self._sources.items()
            },
            "source_descriptions": {
                source_name: info["description"]
                for source_name, info in self._sources.items()
            }
        }


# Global registry instance
_registry = None

def get_sources_registry() -> DataSourcesRegistry:
    """Get the global sources registry instance"""
    global _registry
    if _registry is None:
        _registry = DataSourcesRegistry()
    return _registry


# Convenience functions
def get_available_sources() -> List[str]:
    """Get list of all available source names"""
    return get_sources_registry().get_available_sources()

def get_sources_by_priority(only_available: bool = True) -> List[str]:
    """Get sources sorted by priority"""
    return get_sources_registry().get_sources_by_priority(only_available)

def is_source_available(source_name: str) -> bool:
    """Check if a source is available"""
    return get_sources_registry().is_source_available(source_name)

def load_source_data(source_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Load data from a specific source"""
    return get_sources_registry().load_source(source_name, config)

def load_first_available_source(config_by_source: Dict[str, Dict[str, Any]], 
                               log_attempts: bool = True) -> Dict[str, Any]:
    """Try to load data from sources in priority order"""
    return get_sources_registry().load_first_available(config_by_source, log_attempts)