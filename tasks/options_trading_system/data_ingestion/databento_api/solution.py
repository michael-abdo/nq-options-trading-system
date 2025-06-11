#!/usr/bin/env python3
"""
Databento API Data Ingestion for NQ Options

This module provides data ingestion from Databento API for NQ future options,
following the standard data ingestion interface pattern.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import sqlite3

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing databento
try:
    import databento as db
    import pandas as pd
    DATABENTO_AVAILABLE = True
except ImportError:
    DATABENTO_AVAILABLE = False
    # Create dummy objects for type hints
    pd = None
    db = None
    logger.warning("Databento package not available. Install with: pip install databento")

class DatabentoAPIClient:
    """
    Client for interacting with Databento API for options data retrieval
    """
    
    def __init__(self, api_key: str, cache_dir: Optional[str] = None):
        """
        Initialize Databento API client
        
        Args:
            api_key: Databento API key
            cache_dir: Directory for caching API responses
        """
        if not DATABENTO_AVAILABLE:
            raise ImportError("Databento package not installed")
        
        self.api_key = api_key
        self.client = db.Historical(api_key)
        self.cache_dir = Path(cache_dir) if cache_dir else Path("outputs/databento_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize cache database
        self.cache_db = self.cache_dir / "databento_cache.db"
        self._init_cache_db()
        
        logger.info(f"Databento client initialized with cache at {self.cache_dir}")
    
    def _init_cache_db(self):
        """Initialize SQLite cache database"""
        with sqlite3.connect(self.cache_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp TEXT,
                    cost REAL
                )
            """)
            conn.commit()
    
    def _get_cache_key(self, dataset: str, symbols: List[str], schema: str, date: str) -> str:
        """Generate cache key for API request"""
        symbols_str = "_".join(sorted(symbols))
        return f"{dataset}_{symbols_str}_{schema}_{date}"
    
    def _check_cache(self, cache_key: str, max_age_hours: int = 24) -> Optional[Dict]:
        """Check if valid cached data exists"""
        with sqlite3.connect(self.cache_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data, timestamp FROM api_cache WHERE cache_key = ?",
                (cache_key,)
            )
            row = cursor.fetchone()
            
            if row:
                data_str, timestamp_str = row
                cached_time = datetime.fromisoformat(timestamp_str)
                
                # Check if cache is still valid
                if datetime.now() - cached_time < timedelta(hours=max_age_hours):
                    logger.info(f"Using cached data for {cache_key}")
                    return json.loads(data_str)
                else:
                    logger.info(f"Cache expired for {cache_key}")
            
            return None
    
    def _save_cache(self, cache_key: str, data: Dict, cost: float):
        """Save data to cache"""
        with sqlite3.connect(self.cache_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO api_cache (cache_key, data, timestamp, cost)
                VALUES (?, ?, ?, ?)
            """, (cache_key, json.dumps(data), datetime.now().isoformat(), cost))
            conn.commit()
    
    def get_nq_options_chain(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get NQ options chain data for a specific date
        
        Args:
            date: Date to get options for (default: today)
            
        Returns:
            Dictionary with options chain data
        """
        if not date:
            date = datetime.now()
        
        date_str = date.strftime('%Y-%m-%d')
        
        # Check cache first
        cache_key = self._get_cache_key('GLBX.MDP3', ['NQ.OPT'], 'definition', date_str)
        cached_data = self._check_cache(cache_key)
        if cached_data:
            return cached_data
        
        logger.info(f"Fetching NQ options chain for {date_str}")
        
        try:
            # Get contract definitions
            # For single day, use next day as end to avoid start==end error
            end_date = date + timedelta(days=1)
            params = {
                'dataset': 'GLBX.MDP3',
                'symbols': ['NQ.OPT'],
                'schema': 'definition',
                'start': date_str,
                'end': end_date.strftime('%Y-%m-%d'),
                'stype_in': 'parent'
            }
            
            # Check cost
            cost = self.client.metadata.get_cost(**params)
            logger.info(f"Definition data cost: ${cost:.4f}")
            
            if cost > 1.0:  # Safety check
                logger.warning(f"Cost too high (${cost:.4f}), skipping retrieval")
                return {"error": f"Cost too high: ${cost:.4f}"}
            
            # Retrieve data
            data = self.client.timeseries.get_range(**params)
            df = data.to_df()
            
            # Process into options chain format
            options_chain = self._process_options_chain(df, date_str)
            
            # Cache the result
            self._save_cache(cache_key, options_chain, cost)
            
            return options_chain
            
        except Exception as e:
            logger.error(f"Error fetching options chain: {e}")
            return {"error": str(e)}
    
    def _process_options_chain(self, df: "pd.DataFrame", date_str: str) -> Dict[str, Any]:
        """Process raw definition data into structured options chain"""
        if df.empty:
            return {"calls": [], "puts": [], "total_contracts": 0}
        
        calls = []
        puts = []
        
        for idx, row in df.iterrows():
            contract = {
                "symbol": row.get('raw_symbol', ''),
                "strike": float(row.get('strike_price', 0)) / 1000,  # Databento uses multiplied values
                "expiration": row.get('expiration', '').isoformat() if pd.notna(row.get('expiration')) else '',
                "instrument_id": row.get('instrument_id', ''),
                "underlying_symbol": "NQ"
            }
            
            if row.get('instrument_class') == 'C':
                calls.append(contract)
            elif row.get('instrument_class') == 'P':
                puts.append(contract)
        
        return {
            "calls": calls,
            "puts": puts,
            "total_contracts": len(calls) + len(puts),
            "date": date_str,
            "underlying": "NQ"
        }
    
    def get_options_trades(self, date: Optional[datetime] = None, limit: int = 10000) -> Dict[str, Any]:
        """
        Get options trade data for volume analysis
        
        Args:
            date: Date to get trades for
            limit: Maximum number of trades to retrieve
            
        Returns:
            Dictionary with trade data
        """
        if not date:
            date = datetime.now()
        
        date_str = date.strftime('%Y-%m-%d')
        
        # Check cache
        cache_key = self._get_cache_key('GLBX.MDP3', ['NQ.OPT'], f'trades_{limit}', date_str)
        cached_data = self._check_cache(cache_key, max_age_hours=1)  # Shorter cache for trades
        if cached_data:
            return cached_data
        
        logger.info(f"Fetching NQ options trades for {date_str}")
        
        try:
            # For single day, use next day as end to avoid start==end error
            end_date = date + timedelta(days=1)
            params = {
                'dataset': 'GLBX.MDP3',
                'symbols': ['NQ.OPT'],
                'schema': 'trades',
                'start': date_str,
                'end': end_date.strftime('%Y-%m-%d'),
                'stype_in': 'parent',
                'limit': limit
            }
            
            # Check cost
            cost = self.client.metadata.get_cost(**params)
            logger.info(f"Trade data cost: ${cost:.4f}")
            
            if cost > 5.0:  # Higher limit for trade data
                logger.warning(f"Cost too high (${cost:.4f}), reducing limit")
                params['limit'] = 1000
                cost = self.client.metadata.get_cost(**params)
            
            # Retrieve data
            data = self.client.timeseries.get_range(**params)
            df = data.to_df()
            
            # Process trades
            trades_summary = self._process_trades(df, date_str)
            
            # Cache result
            self._save_cache(cache_key, trades_summary, cost)
            
            return trades_summary
            
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return {"error": str(e)}
    
    def _process_trades(self, df: "pd.DataFrame", date_str: str) -> Dict[str, Any]:
        """Process trade data into volume summary"""
        if df.empty:
            return {"trades": [], "total_volume": 0, "date": date_str}
        
        # Aggregate by instrument
        volume_by_instrument = {}
        
        for idx, row in df.iterrows():
            instrument_id = row.get('instrument_id', '')
            size = int(row.get('size', 0))
            price = float(row.get('price', 0))
            
            if instrument_id not in volume_by_instrument:
                volume_by_instrument[instrument_id] = {
                    'volume': 0,
                    'trades': 0,
                    'avg_price': 0,
                    'prices': []
                }
            
            volume_by_instrument[instrument_id]['volume'] += size
            volume_by_instrument[instrument_id]['trades'] += 1
            volume_by_instrument[instrument_id]['prices'].append(price)
        
        # Calculate averages
        for inst_id, data in volume_by_instrument.items():
            if data['prices']:
                data['avg_price'] = sum(data['prices']) / len(data['prices'])
            del data['prices']  # Remove raw prices to save space
        
        return {
            "volume_by_instrument": volume_by_instrument,
            "total_volume": sum(d['volume'] for d in volume_by_instrument.values()),
            "total_trades": len(df),
            "date": date_str
        }

class DatabentoDataIngestion:
    """
    Main class for Databento data ingestion following standard interface
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Databento data ingestion
        
        Args:
            config: Configuration dictionary with:
                - api_key: Databento API key
                - symbols: List of symbols to fetch (default: ['NQ'])
                - cache_dir: Cache directory path
                - use_cache: Whether to use caching (default: True)
        """
        self.config = config
        self.api_key = self._get_api_key(config)
        self.symbols = config.get('symbols', ['NQ'])
        self.use_cache = config.get('use_cache', True)
        
        if not self.api_key:
            raise ValueError("Databento API key not found in config or environment")
        
        cache_dir = config.get('cache_dir') if self.use_cache else None
        self.client = DatabentoAPIClient(self.api_key, cache_dir)
        
        logger.info("DatabentoDataIngestion initialized")
    
    def _get_api_key(self, config: Dict[str, Any]) -> Optional[str]:
        """Get API key from config or environment"""
        # Check config first
        api_key = config.get('api_key')
        
        # Check environment
        if not api_key:
            api_key = os.getenv('DATABENTO_API_KEY')
        
        # Check .env file
        if not api_key:
            try:
                with open('.env', 'r') as f:
                    for line in f:
                        if line.startswith('DATABENTO_API_KEY='):
                            api_key = line.split('=', 1)[1].strip()
                            break
            except FileNotFoundError:
                pass
        
        return api_key
    
    def load_options_data(self) -> Dict[str, Any]:
        """
        Load options data following standard interface
        
        Returns:
            Dictionary with standard format including:
            - options_summary
            - quality_metrics
            - strike_range
            - raw_data_available
        """
        logger.info("Loading Databento options data")
        
        # Get options chain
        chain_data = self.client.get_nq_options_chain()
        
        if "error" in chain_data:
            logger.error(f"Failed to load options chain: {chain_data['error']}")
            return self._empty_result(chain_data['error'])
        
        # Get trade data for volume
        trades_data = self.client.get_options_trades()
        
        # Combine data
        return self._format_standard_response(chain_data, trades_data)
    
    def _format_standard_response(self, chain_data: Dict, trades_data: Dict) -> Dict[str, Any]:
        """Format Databento data into standard response format"""
        calls = chain_data.get('calls', [])
        puts = chain_data.get('puts', [])
        
        # Calculate strike range
        all_strikes = [c['strike'] for c in calls] + [p['strike'] for p in puts]
        strike_range = {
            'min': min(all_strikes) if all_strikes else 0,
            'max': max(all_strikes) if all_strikes else 0,
            'count': len(set(all_strikes))
        }
        
        # Add volume data if available
        if 'volume_by_instrument' in trades_data:
            volume_map = trades_data['volume_by_instrument']
            
            # Enhance calls and puts with volume data
            for contract in calls + puts:
                inst_id = contract.get('instrument_id')
                if inst_id and inst_id in volume_map:
                    contract['volume'] = volume_map[inst_id]['volume']
                    contract['trades'] = volume_map[inst_id]['trades']
                    contract['avg_price'] = volume_map[inst_id]['avg_price']
        
        # Calculate quality metrics
        total_contracts = len(calls) + len(puts)
        contracts_with_volume = sum(1 for c in calls + puts if c.get('volume', 0) > 0)
        
        quality_metrics = {
            'total_contracts': total_contracts,
            'volume_coverage': contracts_with_volume / total_contracts if total_contracts > 0 else 0,
            'oi_coverage': 0.0,  # Databento doesn't provide OI in trades
            'data_source': 'databento',
            'timestamp': datetime.now().isoformat()
        }
        
        return {
            'loader': self,
            'metadata': {
                'source': 'databento',
                'dataset': 'GLBX.MDP3',
                'symbols': self.symbols,
                'date': chain_data.get('date', datetime.now().strftime('%Y-%m-%d'))
            },
            'options_summary': {
                'total_contracts': total_contracts,
                'calls': calls,
                'puts': puts,
                'underlying': 'NQ',
                'total_volume': trades_data.get('total_volume', 0)
            },
            'quality_metrics': quality_metrics,
            'strike_range': strike_range,
            'raw_data_available': True
        }
    
    def _empty_result(self, error_msg: str) -> Dict[str, Any]:
        """Return empty result with error"""
        return {
            'loader': self,
            'metadata': {'source': 'databento', 'error': error_msg},
            'options_summary': {'total_contracts': 0, 'calls': [], 'puts': []},
            'quality_metrics': {
                'total_contracts': 0,
                'volume_coverage': 0.0,
                'oi_coverage': 0.0,
                'data_source': 'databento'
            },
            'strike_range': {'min': 0, 'max': 0, 'count': 0},
            'raw_data_available': False
        }

def load_databento_api_data(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standard interface function for loading Databento data
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary with standard data ingestion format
    """
    try:
        loader = DatabentoDataIngestion(config)
        return loader.load_options_data()
    except Exception as e:
        logger.error(f"Failed to load Databento data: {e}")
        return {
            'loader': None,
            'metadata': {'source': 'databento', 'error': str(e)},
            'options_summary': {'total_contracts': 0, 'calls': [], 'puts': []},
            'quality_metrics': {
                'total_contracts': 0,
                'volume_coverage': 0.0,
                'oi_coverage': 0.0,
                'data_source': 'databento'
            },
            'strike_range': {'min': 0, 'max': 0, 'count': 0},
            'raw_data_available': False
        }

# Factory function
def create_databento_loader(config: Optional[Dict] = None) -> DatabentoDataIngestion:
    """Factory function to create Databento loader instance"""
    if config is None:
        config = {}
    
    return DatabentoDataIngestion(config)