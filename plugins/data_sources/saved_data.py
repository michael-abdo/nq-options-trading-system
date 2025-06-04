#!/usr/bin/env python3
"""
Data source plugin for saved JSON data files
Converts existing saved data to standardized format
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.interfaces import DataSourceError
from core.data_models import OptionsChain, OptionsContract, OptionType
from plugins.data_sources.base import BaseDataSource


class SavedDataSource(BaseDataSource):
    """Data source for saved JSON files (e.g., Barchart API responses)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.file_path = config.get("file_path")
        if not self.file_path:
            raise DataSourceError("file_path is required in config")
    
    def validate_connection(self) -> bool:
        """Check if file exists and is readable"""
        try:
            return os.path.exists(self.file_path) and os.access(self.file_path, os.R_OK)
        except Exception:
            return False
    
    def fetch_data(self) -> OptionsChain:
        """Load and convert saved JSON data to standardized format"""
        self.logger.info(f"📁 Loading saved data from: {self.file_path}")
        
        try:
            with open(self.file_path, 'r') as f:
                raw_data = json.load(f)
            
            # Save raw data for debugging
            self.save_raw_data(raw_data)
            
            # Convert to standardized format
            chain = self._convert_barchart_data(raw_data)
            
            # Log quality metrics
            self.log_data_quality(chain)
            
            return chain
            
        except FileNotFoundError:
            raise DataSourceError(f"File not found: {self.file_path}")
        except json.JSONDecodeError as e:
            raise DataSourceError(f"Invalid JSON in file: {e}")
        except Exception as e:
            raise DataSourceError(f"Failed to load data: {e}")
    
    def _convert_barchart_data(self, data: Dict[str, Any]) -> OptionsChain:
        """Convert Barchart API format to standardized format"""
        self.logger.info("🔄 Converting Barchart data to standard format...")
        
        # Extract basic info
        timestamp = datetime.now()  # Use current time since saved data doesn't have timestamp
        
        # Get calls and puts
        calls_data = data.get('data', {}).get('Call', [])
        puts_data = data.get('data', {}).get('Put', [])
        
        contracts = []
        underlying_price = 21376.75  # Default - should be extracted from data if available
        
        # Process calls
        for call_data in calls_data:
            contract = self._convert_contract(call_data, OptionType.CALL, underlying_price, timestamp)
            if contract:
                contracts.append(contract)
        
        # Process puts
        for put_data in puts_data:
            contract = self._convert_contract(put_data, OptionType.PUT, underlying_price, timestamp)
            if contract:
                contracts.append(contract)
        
        # Create options chain
        chain = OptionsChain(
            underlying_symbol="NQ",
            underlying_price=underlying_price,
            timestamp=timestamp,
            contracts=contracts,
            metadata={
                "source": "barchart_saved",
                "file_path": self.file_path,
                "raw_calls": len(calls_data),
                "raw_puts": len(puts_data)
            }
        )
        
        return chain
    
    def _convert_contract(self, contract_data: Dict, option_type: OptionType, 
                         underlying_price: float, timestamp: datetime) -> OptionsContract:
        """Convert individual contract data"""
        try:
            # Get data from 'raw' section (contains actual numeric values)
            raw = contract_data.get('raw', {})
            
            # Extract basic contract info
            strike = float(raw.get('strike', 0))
            if strike <= 0:
                return None
            
            # Create symbol
            symbol = contract_data.get('symbol', f"NQ{strike}")
            
            # Parse expiration (default to end of current month if not available)
            expiration = datetime(2025, 6, 30)  # Default expiration
            
            # Extract market data
            volume = raw.get('volume')
            if volume is not None:
                volume = int(volume)
            
            open_interest = raw.get('openInterest')
            if open_interest is not None:
                open_interest = int(open_interest)
            
            last_price = raw.get('lastPrice')
            if last_price is not None:
                last_price = float(last_price)
            
            # Create contract
            contract = OptionsContract(
                symbol=symbol,
                strike=strike,
                expiration=expiration,
                option_type=option_type,
                underlying_price=underlying_price,
                timestamp=timestamp,
                volume=volume,
                open_interest=open_interest,
                last_price=last_price,
                metadata={
                    "source": "barchart",
                    "raw_data": raw
                }
            )
            
            return contract
            
        except Exception as e:
            self.logger.debug(f"Failed to convert contract: {e}")
            return None