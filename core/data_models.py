#!/usr/bin/env python3
"""
Core data models for standardized options data
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class OptionType(Enum):
    CALL = "call"
    PUT = "put"


@dataclass
class OptionsContract:
    """Standardized options contract data"""
    symbol: str
    strike: float
    expiration: datetime
    option_type: OptionType
    underlying_price: float
    timestamp: datetime
    
    # Market data (may be None if not available)
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    last_price: Optional[float] = None
    
    # Greeks (may be None if not calculated)
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def mid_price(self) -> Optional[float]:
        """Calculate mid price from bid/ask"""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return self.last_price
    
    @property
    def moneyness(self) -> float:
        """Calculate moneyness (strike/underlying for calls, underlying/strike for puts)"""
        if self.option_type == OptionType.CALL:
            return self.strike / self.underlying_price
        else:
            return self.underlying_price / self.strike
    
    @property
    def intrinsic_value(self) -> float:
        """Calculate intrinsic value"""
        if self.option_type == OptionType.CALL:
            return max(0, self.underlying_price - self.strike)
        else:
            return max(0, self.strike - self.underlying_price)


@dataclass
class OptionsChain:
    """Complete options chain data"""
    underlying_symbol: str
    underlying_price: float
    timestamp: datetime
    contracts: List[OptionsContract]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and organize contracts"""
        # Sort contracts by expiration, then strike
        self.contracts.sort(key=lambda x: (x.expiration, x.strike))
    
    @property
    def calls(self) -> List[OptionsContract]:
        """Get all call options"""
        return [c for c in self.contracts if c.option_type == OptionType.CALL]
    
    @property
    def puts(self) -> List[OptionsContract]:
        """Get all put options"""
        return [c for c in self.contracts if c.option_type == OptionType.PUT]
    
    @property
    def expirations(self) -> List[datetime]:
        """Get unique expiration dates"""
        return sorted(list(set(c.expiration for c in self.contracts)))
    
    @property
    def strikes(self) -> List[float]:
        """Get unique strike prices"""
        return sorted(list(set(c.strike for c in self.contracts)))
    
    def get_contracts_by_expiration(self, expiration: datetime) -> List[OptionsContract]:
        """Get all contracts for a specific expiration"""
        return [c for c in self.contracts if c.expiration == expiration]
    
    def get_contracts_by_strike(self, strike: float) -> List[OptionsContract]:
        """Get all contracts for a specific strike"""
        return [c for c in self.contracts if c.strike == strike]
    
    def get_atm_contracts(self, tolerance: float = 0.02) -> List[OptionsContract]:
        """Get at-the-money contracts within tolerance"""
        atm_contracts = []
        for contract in self.contracts:
            moneyness = abs(contract.moneyness - 1.0)
            if moneyness <= tolerance:
                atm_contracts.append(contract)
        return atm_contracts
    
    @property
    def data_quality_metrics(self) -> Dict[str, float]:
        """Calculate data quality metrics"""
        total_contracts = len(self.contracts)
        if total_contracts == 0:
            return {}
        
        contracts_with_volume = sum(1 for c in self.contracts if c.volume is not None and c.volume > 0)
        contracts_with_oi = sum(1 for c in self.contracts if c.open_interest is not None and c.open_interest > 0)
        contracts_with_prices = sum(1 for c in self.contracts if c.last_price is not None or c.mid_price is not None)
        
        return {
            "total_contracts": total_contracts,
            "volume_coverage": contracts_with_volume / total_contracts,
            "oi_coverage": contracts_with_oi / total_contracts,
            "price_coverage": contracts_with_prices / total_contracts,
            "call_count": len(self.calls),
            "put_count": len(self.puts),
            "expiration_count": len(self.expirations),
            "strike_count": len(self.strikes)
        }


@dataclass
class DataRequirements:
    """Defines what data a strategy needs"""
    requires_volume: bool = False
    requires_open_interest: bool = False
    requires_prices: bool = False
    requires_greeks: bool = False
    min_contracts: int = 1
    max_age_hours: int = 24
    
    def validate_data(self, chain: OptionsChain) -> tuple[bool, List[str]]:
        """Validate if data meets requirements"""
        errors = []
        
        if len(chain.contracts) < self.min_contracts:
            errors.append(f"Insufficient contracts: {len(chain.contracts)} < {self.min_contracts}")
        
        if self.requires_volume:
            volume_count = sum(1 for c in chain.contracts if c.volume is not None and c.volume > 0)
            if volume_count == 0:
                errors.append("Volume data required but not available")
        
        if self.requires_open_interest:
            oi_count = sum(1 for c in chain.contracts if c.open_interest is not None and c.open_interest > 0)
            if oi_count == 0:
                errors.append("Open interest data required but not available")
        
        if self.requires_prices:
            price_count = sum(1 for c in chain.contracts if c.last_price is not None or c.mid_price is not None)
            if price_count == 0:
                errors.append("Price data required but not available")
        
        if self.requires_greeks:
            greek_count = sum(1 for c in chain.contracts if c.delta is not None)
            if greek_count == 0:
                errors.append("Greeks data required but not available")
        
        # Check age
        age_hours = (datetime.now() - chain.timestamp).total_seconds() / 3600
        if age_hours > self.max_age_hours:
            errors.append(f"Data too old: {age_hours:.1f} hours > {self.max_age_hours}")
        
        return len(errors) == 0, errors


@dataclass
class AnalysisResult:
    """Standard result format for all strategies"""
    strategy_name: str
    timestamp: datetime
    underlying_symbol: str
    underlying_price: float
    
    # Core results
    signals: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    
    def add_signal(self, signal_type: str, confidence: float, **kwargs):
        """Add a trading signal"""
        signal = {
            "type": signal_type,
            "confidence": confidence,
            "timestamp": datetime.now(),
            **kwargs
        }
        self.signals.append(signal)
    
    def add_metric(self, name: str, value: float):
        """Add a calculated metric"""
        self.metrics[name] = value
    
    def add_warning(self, message: str):
        """Add a warning message"""
        self.warnings.append(message)