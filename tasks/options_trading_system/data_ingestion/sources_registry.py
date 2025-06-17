#!/usr/bin/env python3
"""
Data Sources Registry
Central registry for all available data sources and their loader functions
"""

import logging
from typing import Dict, Callable, Any, List
from datetime import datetime
from utils.timezone_utils import get_eastern_time, get_utc_time

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
            "timestamp": get_eastern_time().isoformat(),
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
            "databento": 1,       # PRIMARY - VERIFIED LIVE CME data with closed-loop verification
            "tradovate": 2,       # REFERENCE - For closed-loop verification only
            "barchart": 3,        # BACKUP - Fallback for non-live operations
            "polygon": 4,         # OPTIONAL - Additional source when configured
            "barchart_live": 5,   # FALLBACK - Live API backup
            "barchart_saved": 6   # ARCHIVE - File-based historical data
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
        """DISABLED - NO FALLBACKS ALLOWED FOR TRADING SAFETY"""
        raise ValueError("Barchart data source is DISABLED. Only live Databento data is allowed for trading safety.")

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
        TRADING SAFETY: Only load from Databento. NO FALLBACKS ALLOWED.

        Args:
            config_by_source: Dict mapping source names to their configs
            log_attempts: Whether to log loading attempts

        Returns:
            Data from Databento only

        Raises:
            Exception if Databento fails - NO FALLBACKS
        """
        # CRITICAL: Only allow Databento for trading safety
        if 'databento' not in config_by_source:
            raise Exception("❌ CRITICAL: Databento configuration missing. NO OTHER DATA SOURCES ALLOWED.")

        databento_config = config_by_source['databento']
        if not databento_config.get('enabled', True):
            raise Exception("❌ CRITICAL: Databento is disabled. Cannot proceed without live data.")

        # Check for any other enabled sources - this is NOT allowed
        other_enabled = [name for name, config in config_by_source.items()
                        if name != 'databento' and config.get('enabled', False)]
        if other_enabled:
            raise Exception(f"❌ CRITICAL: Other data sources are enabled: {other_enabled}. " +
                          "Only Databento is allowed for trading safety. DISABLE ALL OTHER SOURCES.")

        if log_attempts:
            print("🔒 TRADING SAFETY MODE: Only live Databento data allowed")
            print("🎯 Loading from Databento (NO FALLBACKS)...")

        try:
            # Check for streaming mode
            if databento_config.get('streaming_mode', False):
                return self._load_databento_direct(databento_config, log_attempts)
            else:
                result = self.load_source('databento', databento_config)

                # Verify we got real data
                has_data = False
                if result:
                    if result.get('options_summary', {}).get('total_contracts', 0) > 0:
                        has_data = True
                    elif result.get('total_contracts', 0) > 0:
                        has_data = True
                    elif result.get('raw_data', {}).get('total', 0) > 0:
                        has_data = True

                if has_data:
                    if log_attempts:
                        print("✅ Successfully loaded LIVE data from Databento")
                    return result
                else:
                    raise Exception("Databento returned no data")

        except Exception as e:
            # NO FALLBACKS - fail immediately
            error_msg = f"❌ CRITICAL: Databento failed: {str(e)}\n" + \
                       "NO FALLBACK ALLOWED. Cannot proceed without live data."
            raise Exception(error_msg)

    def _load_databento_direct(self, config: Dict[str, Any], log_attempts: bool = True) -> Dict[str, Any]:
        """Load databento data directly without fallbacks for live streaming mode"""
        try:
            if log_attempts:
                print("🚀 Loading live databento MBO stream...")

            # Load directly using databento loader with no error tolerance
            result = self.load_source("databento", config)

            # For live streaming mode, don't require immediate data
            # The streaming client may take time to connect and start receiving data
            if config.get('streaming_mode', False):
                if log_attempts:
                    print("✅ Databento live streaming initialized")
                return result

            # For non-streaming mode, validate data presence
            has_data = False
            if result:
                if result.get('options_summary', {}).get('total_contracts', 0) > 0:
                    has_data = True
                elif result.get('streaming_active', False):
                    has_data = True
                elif result.get('raw_data_available', False):
                    has_data = True

            if has_data or config.get('streaming_mode', False):
                if log_attempts:
                    print("✅ Databento data loaded successfully")
                return result
            else:
                raise Exception("Databento returned no data and streaming not active")

        except Exception as e:
            if log_attempts:
                print(f"❌ Databento direct load failed: {e}")
            # In databento-only mode, we don't fall back - we fail fast
            raise Exception(f"Databento-only mode failed: {str(e)}")

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
