#!/usr/bin/env python3
"""
Base strategy implementation with common functionality
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.interfaces import StrategyInterface
from core.data_models import OptionsChain, AnalysisResult
from utils.logging_config import get_logger


class BaseStrategy(StrategyInterface):
    """Base implementation with common strategy functionality"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = get_logger(f"strategy.{self.name}")
        
    def create_result(self, data: OptionsChain) -> AnalysisResult:
        """Create a new analysis result with basic info"""
        return AnalysisResult(
            strategy_name=self.name,
            timestamp=datetime.now(),
            underlying_symbol=data.underlying_symbol,
            underlying_price=data.underlying_price
        )
    
    def filter_contracts(self, contracts: List, **criteria) -> List:
        """Filter contracts based on criteria"""
        filtered = contracts
        
        # Filter by expiration
        if 'expiration' in criteria:
            target_exp = criteria['expiration']
            filtered = [c for c in filtered if c.expiration == target_exp]
        
        # Filter by strike range
        if 'strike_min' in criteria:
            filtered = [c for c in filtered if c.strike >= criteria['strike_min']]
        if 'strike_max' in criteria:
            filtered = [c for c in filtered if c.strike <= criteria['strike_max']]
        
        # Filter by moneyness
        if 'moneyness_min' in criteria:
            filtered = [c for c in filtered if c.moneyness >= criteria['moneyness_min']]
        if 'moneyness_max' in criteria:
            filtered = [c for c in filtered if c.moneyness <= criteria['moneyness_max']]
        
        # Filter by data availability
        if 'require_volume' in criteria and criteria['require_volume']:
            filtered = [c for c in filtered if c.volume is not None and c.volume > 0]
        if 'require_oi' in criteria and criteria['require_oi']:
            filtered = [c for c in filtered if c.open_interest is not None and c.open_interest > 0]
        if 'require_price' in criteria and criteria['require_price']:
            filtered = [c for c in filtered if c.last_price is not None or c.mid_price is not None]
        
        return filtered
    
    def log_analysis_start(self, data: OptionsChain):
        """Log start of analysis"""
        quality = data.data_quality_metrics
        self.logger.info(f"🧮 Starting {self.name} analysis on {data.underlying_symbol}")
        self.logger.info(f"  Data: {quality['total_contracts']} contracts, "
                        f"{quality['volume_coverage']:.1%} vol, {quality['oi_coverage']:.1%} OI")
    
    def log_analysis_complete(self, result: AnalysisResult):
        """Log completion of analysis"""
        self.logger.info(f"✅ {self.name} complete: {len(result.signals)} signals, "
                        f"{len(result.metrics)} metrics")
        
        # Log any warnings
        for warning in result.warnings:
            self.logger.warning(f"⚠️ {warning}")
    
    def calculate_pcr_ratio(self, calls: List, puts: List, method: str = "volume") -> float:
        """Calculate Put/Call ratio using specified method"""
        if method == "volume":
            call_volume = sum(c.volume or 0 for c in calls)
            put_volume = sum(p.volume or 0 for p in puts)
            return put_volume / call_volume if call_volume > 0 else 0
        
        elif method == "open_interest":
            call_oi = sum(c.open_interest or 0 for c in calls)
            put_oi = sum(p.open_interest or 0 for p in puts)
            return put_oi / call_oi if call_oi > 0 else 0
        
        elif method == "premium":
            call_premium = sum((c.last_price or 0) * (c.open_interest or 0) for c in calls)
            put_premium = sum((p.last_price or 0) * (p.open_interest or 0) for p in puts)
            return put_premium / call_premium if call_premium > 0 else 0
        
        else:
            raise ValueError(f"Unknown PCR method: {method}")
    
    def find_max_pain(self, contracts: List, expiration: datetime = None) -> float:
        """Calculate max pain strike (strike with minimum total premium loss)"""
        if expiration:
            contracts = [c for c in contracts if c.expiration == expiration]
        
        if not contracts:
            return 0
        
        strikes = sorted(set(c.strike for c in contracts))
        min_pain = float('inf')
        max_pain_strike = strikes[0]
        
        for strike in strikes:
            total_pain = 0
            
            for contract in contracts:
                if contract.open_interest and contract.open_interest > 0:
                    intrinsic = contract.intrinsic_value
                    pain = intrinsic * contract.open_interest
                    total_pain += pain
            
            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = strike
        
        return max_pain_strike