#!/usr/bin/env python3
"""
Base data source implementation with common functionality
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.interfaces import DataSourceInterface
from core.data_models import OptionsChain
from utils.logging_config import get_logger


class BaseDataSource(DataSourceInterface):
    """Base implementation with common data source functionality"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = get_logger(f"datasource.{self.name}")
        
    def log_data_quality(self, chain: OptionsChain):
        """Log data quality metrics"""
        quality = chain.data_quality_metrics
        self.logger.info(f"📊 Data quality for {chain.underlying_symbol}:")
        self.logger.info(f"  Total contracts: {quality['total_contracts']}")
        self.logger.info(f"  Volume coverage: {quality['volume_coverage']:.1%}")
        self.logger.info(f"  OI coverage: {quality['oi_coverage']:.1%}")
        self.logger.info(f"  Price coverage: {quality['price_coverage']:.1%}")
        self.logger.info(f"  Calls/Puts: {quality['call_count']}/{quality['put_count']}")
        self.logger.info(f"  Expirations: {quality['expiration_count']}")
        self.logger.info(f"  Strikes: {quality['strike_count']}")
    
    def save_raw_data(self, data: Any, filename: str = None):
        """Save raw data for debugging"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.name.lower()}_raw_{timestamp}.json"
        
        # Save to data/raw directory
        import json
        raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "raw")
        os.makedirs(raw_dir, exist_ok=True)
        
        filepath = os.path.join(raw_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        self.logger.debug(f"💾 Saved raw data to: {filepath}")
        return filepath