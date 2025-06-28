#!/usr/bin/env python3
"""
Common Options Data Models
Standardized data structures for options contracts and chains
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class OptionType(Enum):
    """Option type enumeration"""
    CALL = "call"
    PUT = "put"


class ContractType(Enum):
    """Contract type enumeration"""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    FRIDAY = "friday"
    DAILY = "daily"
    ZERODTR = "0dte"


@dataclass
class OptionGreeks:
    """Option Greeks data"""
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None


@dataclass
class OptionsContract:
    """
    Standard options contract data structure
    Used across all data sources (Barchart, Tradovate, IB, etc.)
    """
    # Key identifiers
    strike: float
    expiration_date: str
    contract_type: Optional[str] = None  # weekly, monthly, etc.
    
    # Call data
    call_symbol: Optional[str] = None
    call_last: Optional[float] = None
    call_change: Optional[float] = None
    call_bid: Optional[float] = None
    call_ask: Optional[float] = None
    call_volume: Optional[int] = None
    call_open_interest: Optional[int] = None
    call_implied_volatility: Optional[float] = None
    call_greeks: Optional[OptionGreeks] = None
    
    # Put data
    put_symbol: Optional[str] = None
    put_last: Optional[float] = None
    put_change: Optional[float] = None
    put_bid: Optional[float] = None
    put_ask: Optional[float] = None
    put_volume: Optional[int] = None
    put_open_interest: Optional[int] = None
    put_implied_volatility: Optional[float] = None
    put_greeks: Optional[OptionGreeks] = None
    
    # Metadata
    underlying_symbol: Optional[str] = None
    underlying_price: Optional[float] = None
    source: str = "unknown"  # 'barchart_web', 'barchart_api', 'tradovate', etc.
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = asdict(self)
        # Convert datetime to ISO format
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data
    
    def get_moneyness(self, underlying_price: Optional[float] = None) -> Optional[float]:
        """Calculate moneyness (strike/underlying)"""
        price = underlying_price or self.underlying_price
        if price and price > 0:
            return self.strike / price
        return None
    
    def is_itm(self, option_type: OptionType, underlying_price: Optional[float] = None) -> Optional[bool]:
        """Check if option is in the money"""
        price = underlying_price or self.underlying_price
        if not price:
            return None
        
        if option_type == OptionType.CALL:
            return self.strike < price
        else:  # PUT
            return self.strike > price
    
    def get_bid_ask_spread(self, option_type: OptionType) -> Optional[float]:
        """Calculate bid-ask spread"""
        if option_type == OptionType.CALL:
            if self.call_bid is not None and self.call_ask is not None:
                return self.call_ask - self.call_bid
        else:  # PUT
            if self.put_bid is not None and self.put_ask is not None:
                return self.put_ask - self.put_bid
        return None
    
    def get_mid_price(self, option_type: OptionType) -> Optional[float]:
        """Calculate mid price"""
        if option_type == OptionType.CALL:
            if self.call_bid is not None and self.call_ask is not None:
                return (self.call_bid + self.call_ask) / 2
        else:  # PUT
            if self.put_bid is not None and self.put_ask is not None:
                return (self.put_bid + self.put_ask) / 2
        return None


@dataclass
class OptionsChainData:
    """
    Standard options chain data structure
    Contains all contracts for a specific expiration
    """
    underlying_symbol: str
    expiration_date: str
    contracts: List[OptionsContract]
    
    # Optional fields
    underlying_price: Optional[float] = None
    total_contracts: Optional[int] = None
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post initialization processing"""
        if self.total_contracts is None:
            self.total_contracts = len(self.contracts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'underlying_symbol': self.underlying_symbol,
            'expiration_date': self.expiration_date,
            'underlying_price': self.underlying_price,
            'total_contracts': self.total_contracts,
            'source': self.source,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'metadata': self.metadata,
            'contracts': [c.to_dict() for c in self.contracts]
        }
    
    def get_strikes(self) -> List[float]:
        """Get sorted list of unique strikes"""
        strikes = sorted(set(c.strike for c in self.contracts))
        return strikes
    
    def get_contract_by_strike(self, strike: float) -> Optional[OptionsContract]:
        """Find contract by strike price"""
        for contract in self.contracts:
            if contract.strike == strike:
                return contract
        return None
    
    def filter_by_moneyness(self, min_moneyness: float = 0.9, max_moneyness: float = 1.1) -> List[OptionsContract]:
        """Filter contracts by moneyness range"""
        filtered = []
        for contract in self.contracts:
            moneyness = contract.get_moneyness()
            if moneyness and min_moneyness <= moneyness <= max_moneyness:
                filtered.append(contract)
        return filtered
    
    def get_total_volume(self) -> Dict[str, int]:
        """Calculate total volume for calls and puts"""
        call_volume = sum(c.call_volume or 0 for c in self.contracts)
        put_volume = sum(c.put_volume or 0 for c in self.contracts)
        return {'calls': call_volume, 'puts': put_volume, 'total': call_volume + put_volume}
    
    def get_total_open_interest(self) -> Dict[str, int]:
        """Calculate total open interest for calls and puts"""
        call_oi = sum(c.call_open_interest or 0 for c in self.contracts)
        put_oi = sum(c.put_open_interest or 0 for c in self.contracts)
        return {'calls': call_oi, 'puts': put_oi, 'total': call_oi + put_oi}


@dataclass
class NormalizedOptionsData:
    """
    Normalized options data structure for cross-source compatibility
    Used by data_normalizer to standardize different data sources
    """
    contracts: List[Dict[str, Any]]
    summary: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_options_chain(self) -> OptionsChainData:
        """Convert to OptionsChainData format"""
        # Extract underlying info from summary
        underlying_symbol = self.summary.get('underlying_symbol', 'UNKNOWN')
        expiration_date = self.summary.get('expiration_date', '')
        underlying_price = self.summary.get('underlying_price')
        
        # Convert contracts
        options_contracts = []
        for contract_dict in self.contracts:
            # Map normalized fields to OptionsContract
            contract = OptionsContract(
                strike=contract_dict.get('strike', 0),
                expiration_date=contract_dict.get('expiration', expiration_date),
                call_last=contract_dict.get('call_last_price'),
                call_bid=contract_dict.get('call_bid'),
                call_ask=contract_dict.get('call_ask'),
                call_volume=contract_dict.get('call_volume'),
                call_open_interest=contract_dict.get('call_open_interest'),
                put_last=contract_dict.get('put_last_price'),
                put_bid=contract_dict.get('put_bid'),
                put_ask=contract_dict.get('put_ask'),
                put_volume=contract_dict.get('put_volume'),
                put_open_interest=contract_dict.get('put_open_interest'),
                underlying_symbol=underlying_symbol,
                underlying_price=underlying_price,
                source=self.metadata.get('source', 'normalized')
            )
            options_contracts.append(contract)
        
        return OptionsChainData(
            underlying_symbol=underlying_symbol,
            expiration_date=expiration_date,
            underlying_price=underlying_price,
            contracts=options_contracts,
            source=self.metadata.get('source', 'normalized'),
            metadata=self.metadata
        )