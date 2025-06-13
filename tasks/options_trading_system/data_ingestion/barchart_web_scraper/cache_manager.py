#!/usr/bin/env python3
"""
Barchart Data Cache Manager
Optimizes API calls by caching frequently accessed data
"""

import os
import json
import time
from datetime import datetime, timedelta
from utils.timezone_utils import get_eastern_time, get_utc_time
from typing import Dict, Any, Optional, Tuple
import hashlib
import logging

logger = logging.getLogger(__name__)


class BarchartCacheManager:
    """Manages caching for Barchart options data to reduce API calls"""

    def __init__(self, cache_dir: str = "outputs/barchart_cache",
                 ttl_minutes: int = 5,
                 max_cache_size_mb: int = 100):
        """
        Initialize cache manager

        Args:
            cache_dir: Directory to store cache files
            ttl_minutes: Time-to-live for cache entries in minutes
            max_cache_size_mb: Maximum cache size in MB
        """
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_minutes * 60
        self.max_cache_size_bytes = max_cache_size_mb * 1024 * 1024

        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)

        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "saves": 0
        }

        # Load cache index
        self.index_file = os.path.join(self.cache_dir, ".cache_index.json")
        self.cache_index = self._load_index()

    def _load_index(self) -> Dict[str, Any]:
        """Load cache index from disk"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
        return {}

    def _save_index(self) -> None:
        """Save cache index to disk"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.cache_index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache index: {e}")

    def _get_cache_key(self, symbol: str, futures_symbol: str) -> str:
        """Generate cache key for symbol combination"""
        key_string = f"{symbol}_{futures_symbol}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> str:
        """Get file path for cache key"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid"""
        if "timestamp" not in cache_entry:
            return False

        cached_time = datetime.fromisoformat(cache_entry["timestamp"])
        age_seconds = (get_eastern_time() - cached_time).total_seconds()

        # During market hours (9:30 AM - 4:00 PM ET), use shorter TTL
        now = get_eastern_time()
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

        if market_open <= now <= market_close and now.weekday() < 5:
            # Market hours - use configured TTL
            return age_seconds < self.ttl_seconds
        else:
            # After hours - cache for longer (30 minutes)
            return age_seconds < (30 * 60)

    def get(self, symbol: str, futures_symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get data from cache if available and valid

        Returns:
            Cached data if available and valid, None otherwise
        """
        cache_key = self._get_cache_key(symbol, futures_symbol)

        if cache_key not in self.cache_index:
            self.stats["misses"] += 1
            return None

        cache_path = self._get_cache_path(cache_key)

        if not os.path.exists(cache_path):
            # Index entry exists but file is missing
            del self.cache_index[cache_key]
            self._save_index()
            self.stats["misses"] += 1
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_entry = json.load(f)

            if self._is_cache_valid(cache_entry):
                self.stats["hits"] += 1
                logger.info(f"Cache hit for {symbol} (age: {self._get_cache_age_str(cache_entry)})")
                return cache_entry["data"]
            else:
                # Cache expired
                self._evict_entry(cache_key)
                self.stats["misses"] += 1
                logger.info(f"Cache expired for {symbol}")
                return None

        except Exception as e:
            logger.error(f"Failed to read cache entry {cache_key}: {e}")
            self.stats["misses"] += 1
            return None

    def _get_cache_age_str(self, cache_entry: Dict[str, Any]) -> str:
        """Get human-readable cache age"""
        if "timestamp" not in cache_entry:
            return "unknown"

        cached_time = datetime.fromisoformat(cache_entry["timestamp"])
        age_seconds = (get_eastern_time() - cached_time).total_seconds()

        if age_seconds < 60:
            return f"{int(age_seconds)}s"
        elif age_seconds < 3600:
            return f"{int(age_seconds / 60)}m"
        else:
            return f"{int(age_seconds / 3600)}h"

    def save(self, symbol: str, futures_symbol: str, data: Dict[str, Any]) -> None:
        """
        Save data to cache

        Args:
            symbol: Options symbol
            futures_symbol: Futures symbol
            data: Data to cache
        """
        cache_key = self._get_cache_key(symbol, futures_symbol)
        cache_path = self._get_cache_path(cache_key)

        cache_entry = {
            "symbol": symbol,
            "futures_symbol": futures_symbol,
            "timestamp": get_eastern_time().isoformat(),
            "data": data
        }

        try:
            # Check cache size before saving
            self._enforce_size_limit()

            with open(cache_path, 'w') as f:
                json.dump(cache_entry, f)

            # Update index
            self.cache_index[cache_key] = {
                "symbol": symbol,
                "futures_symbol": futures_symbol,
                "timestamp": cache_entry["timestamp"],
                "size": os.path.getsize(cache_path)
            }
            self._save_index()

            self.stats["saves"] += 1
            logger.info(f"Cached data for {symbol}")

        except Exception as e:
            logger.error(f"Failed to save cache entry {cache_key}: {e}")

    def _enforce_size_limit(self) -> None:
        """Enforce cache size limit by evicting old entries"""
        total_size = sum(entry.get("size", 0) for entry in self.cache_index.values())

        if total_size > self.max_cache_size_bytes:
            # Sort entries by timestamp (oldest first)
            sorted_entries = sorted(
                self.cache_index.items(),
                key=lambda x: x[1].get("timestamp", ""),
                reverse=False
            )

            # Evict oldest entries until we're under the limit
            for cache_key, entry in sorted_entries:
                if total_size <= self.max_cache_size_bytes * 0.8:  # Keep 20% buffer
                    break

                self._evict_entry(cache_key)
                total_size -= entry.get("size", 0)

    def _evict_entry(self, cache_key: str) -> None:
        """Evict a cache entry"""
        cache_path = self._get_cache_path(cache_key)

        try:
            if os.path.exists(cache_path):
                os.remove(cache_path)

            if cache_key in self.cache_index:
                del self.cache_index[cache_key]
                self._save_index()

            self.stats["evictions"] += 1

        except Exception as e:
            logger.error(f"Failed to evict cache entry {cache_key}: {e}")

    def clear(self) -> None:
        """Clear all cache entries"""
        for cache_key in list(self.cache_index.keys()):
            self._evict_entry(cache_key)

        logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_size = sum(entry.get("size", 0) for entry in self.cache_index.values())

        hit_rate = 0
        if self.stats["hits"] + self.stats["misses"] > 0:
            hit_rate = self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": f"{hit_rate:.1%}",
            "saves": self.stats["saves"],
            "evictions": self.stats["evictions"],
            "entries": len(self.cache_index),
            "size_mb": round(total_size / (1024 * 1024), 2),
            "size_limit_mb": self.max_cache_size_bytes / (1024 * 1024)
        }

    def print_stats(self) -> None:
        """Print cache statistics"""
        stats = self.get_stats()
        print("\n📊 Barchart Cache Statistics:")
        print(f"  Hit Rate: {stats['hit_rate']}")
        print(f"  Hits: {stats['hits']}, Misses: {stats['misses']}")
        print(f"  Entries: {stats['entries']}")
        print(f"  Size: {stats['size_mb']}MB / {stats['size_limit_mb']}MB")
        print(f"  Saves: {stats['saves']}, Evictions: {stats['evictions']}")


# Global cache instance
_cache_manager = None

def get_cache_manager() -> BarchartCacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = BarchartCacheManager()
    return _cache_manager
