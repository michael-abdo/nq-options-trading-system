#!/usr/bin/env python3
"""
MBO Event Stream Processor with Bid/Ask Pressure Derivation

This module processes raw MBO events from the WebSocket stream and:
- Derives trade initiation direction (buy/sell pressure)
- Aggregates pressure metrics by strike and time window
- Handles NQ options contract mapping
- Provides real-time pressure ratio calculations
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProcessedMBOEvent:
    """Processed MBO event with derived fields"""
    # Timing
    timestamp: datetime
    exchange_timestamp: datetime
    
    # Contract identification
    symbol: str
    instrument_id: int
    contract_type: str  # 'C' or 'P'
    strike_price: float
    expiration_date: str
    
    # Event details
    action: str  # 'A'dd, 'M'odify, 'C'ancel, 'T'rade
    side: str    # 'B'id, 'A'sk, 'T'rade
    price: float
    size: int
    
    # Derived fields
    trade_direction: Optional[str] = None  # 'BUY' or 'SELL'
    aggressor_side: Optional[str] = None
    price_level: Optional[str] = None  # 'BID', 'MID', 'ASK'
    
    # Market context
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    spread: Optional[float] = None
    
    # Sequence tracking
    sequence_number: int = 0
    order_id: Optional[int] = None


@dataclass
class StrikePressureMetrics:
    """Aggregated pressure metrics for a specific strike"""
    strike_price: float
    contract_type: str
    time_window_start: datetime
    time_window_end: datetime
    
    # Volume metrics
    buy_volume: int = 0      # Volume hitting ask
    sell_volume: int = 0     # Volume hitting bid
    neutral_volume: int = 0  # Volume at mid or unclear
    total_volume: int = 0
    
    # Trade counts
    buy_trades: int = 0
    sell_trades: int = 0
    total_trades: int = 0
    
    # Pressure metrics
    buy_pressure_ratio: float = 0.0
    net_pressure: int = 0  # buy_volume - sell_volume
    pressure_score: float = 0.0  # -1 to 1, normalized
    
    # Trade size analysis
    avg_buy_size: float = 0.0
    avg_sell_size: float = 0.0
    large_buy_trades: int = 0   # Trades > 100 contracts
    large_sell_trades: int = 0
    
    # Market context
    avg_spread: float = 0.0
    total_spread_samples: int = 0


class ContractMapper:
    """Maps instrument IDs to NQ options contracts"""
    
    def __init__(self):
        self.instrument_cache = {}
        self.symbol_pattern_cache = {}
        self._lock = threading.Lock()
    
    def parse_option_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Parse option symbol to extract strike and type
        
        Example: NQH5 C21000 -> March 2025 21000 Call
        """
        try:
            # Check cache first
            if symbol in self.symbol_pattern_cache:
                return self.symbol_pattern_cache[symbol]
            
            # Basic parsing for CME options format
            parts = symbol.split()
            if len(parts) >= 2:
                # Extract contract type and strike
                contract_part = parts[1]
                contract_type = contract_part[0]  # 'C' or 'P'
                strike_str = contract_part[1:]
                
                # Parse expiration from base symbol
                base_symbol = parts[0]
                if len(base_symbol) >= 4:
                    underlying = base_symbol[:2]  # 'NQ'
                    month_code = base_symbol[2]   # Month code
                    year_digit = base_symbol[3]   # Year digit
                    
                    result = {
                        'underlying': underlying,
                        'contract_type': contract_type,
                        'strike': float(strike_str),
                        'month_code': month_code,
                        'year_digit': year_digit,
                        'symbol': symbol
                    }
                    
                    # Cache result
                    with self._lock:
                        self.symbol_pattern_cache[symbol] = result
                    
                    return result
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to parse symbol {symbol}: {e}")
            return None
    
    def get_contract_info(self, instrument_id: int, symbol: str) -> Optional[Dict[str, Any]]:
        """Get contract information from instrument ID and symbol"""
        # Check cache
        if instrument_id in self.instrument_cache:
            return self.instrument_cache[instrument_id]
        
        # Parse symbol
        info = self.parse_option_symbol(symbol)
        if info:
            info['instrument_id'] = instrument_id
            
            # Cache by instrument ID
            with self._lock:
                self.instrument_cache[instrument_id] = info
        
        return info


class BidAskTracker:
    """Tracks current bid/ask prices for each instrument"""
    
    def __init__(self):
        self.bid_prices = {}  # instrument_id -> price
        self.ask_prices = {}  # instrument_id -> price
        self.bid_sizes = {}   # instrument_id -> size
        self.ask_sizes = {}   # instrument_id -> size
        self._lock = threading.Lock()
    
    def update_bid(self, instrument_id: int, price: float, size: int):
        """Update bid price and size"""
        with self._lock:
            if price > 0:
                self.bid_prices[instrument_id] = price
                self.bid_sizes[instrument_id] = size
    
    def update_ask(self, instrument_id: int, price: float, size: int):
        """Update ask price and size"""
        with self._lock:
            if price > 0:
                self.ask_prices[instrument_id] = price
                self.ask_sizes[instrument_id] = size
    
    def get_bid_ask(self, instrument_id: int) -> Tuple[Optional[float], Optional[float]]:
        """Get current bid/ask prices"""
        with self._lock:
            bid = self.bid_prices.get(instrument_id)
            ask = self.ask_prices.get(instrument_id)
            return bid, ask
    
    def get_spread(self, instrument_id: int) -> Optional[float]:
        """Get current bid/ask spread"""
        bid, ask = self.get_bid_ask(instrument_id)
        if bid and ask and ask > bid:
            return ask - bid
        return None


class MBOEventStreamProcessor:
    """
    Main processor for MBO event streams
    
    Implements the bid/ask pressure derivation logic:
    - trade_price == ask_price → BUY initiation
    - trade_price == bid_price → SELL initiation
    - Aggregates by strike for pressure ratios
    """
    
    def __init__(self, window_minutes: int = 5):
        """
        Initialize MBO event processor
        
        Args:
            window_minutes: Time window for pressure aggregation
        """
        self.window_minutes = window_minutes
        self.contract_mapper = ContractMapper()
        self.bid_ask_tracker = BidAskTracker()
        
        # Pressure aggregation
        self.active_windows = defaultdict(lambda: defaultdict(list))
        self.completed_metrics = deque(maxlen=1000)
        
        # Stats
        self.events_processed = 0
        self.trades_processed = 0
        self.errors = 0
        
        self._lock = threading.Lock()
        
        logger.info(f"MBO processor initialized with {window_minutes}-minute windows")
    
    def process_event(self, raw_event: Dict[str, Any]) -> Optional[ProcessedMBOEvent]:
        """
        Process raw MBO event and derive trade direction
        
        Args:
            raw_event: Raw event from WebSocket stream
            
        Returns:
            ProcessedMBOEvent with derived fields or None
        """
        try:
            # Skip if no symbol or instrument ID
            symbol = raw_event.get('symbol')
            instrument_id = raw_event.get('instrument_id')
            
            if not symbol or not instrument_id:
                return None
            
            # Get contract info
            contract_info = self.contract_mapper.get_contract_info(instrument_id, symbol)
            if not contract_info:
                return None
            
            # Parse timestamps
            ts_event = raw_event.get('ts_event', 0)
            if ts_event:
                exchange_timestamp = datetime.fromtimestamp(ts_event / 1_000_000_000, tz=timezone.utc)
            else:
                exchange_timestamp = datetime.now(timezone.utc)
            
            # Create base event
            event = ProcessedMBOEvent(
                timestamp=datetime.now(timezone.utc),
                exchange_timestamp=exchange_timestamp,
                symbol=symbol,
                instrument_id=instrument_id,
                contract_type=contract_info['contract_type'],
                strike_price=contract_info['strike'],
                expiration_date=f"{contract_info['month_code']}{contract_info['year_digit']}",
                action=raw_event.get('action', ''),
                side=raw_event.get('side', ''),
                price=float(raw_event.get('price', 0)) if raw_event.get('price') else 0,
                size=int(raw_event.get('size', 0)) if raw_event.get('size') else 0,
                sequence_number=raw_event.get('sequence', 0),
                order_id=raw_event.get('order_id')
            )
            
            # Update bid/ask tracking
            if event.action in ['A', 'M']:  # Add or Modify
                if event.side == 'B':
                    self.bid_ask_tracker.update_bid(instrument_id, event.price, event.size)
                elif event.side == 'A':
                    self.bid_ask_tracker.update_ask(instrument_id, event.price, event.size)
            
            # Get current bid/ask
            bid, ask = self.bid_ask_tracker.get_bid_ask(instrument_id)
            event.bid_price = bid
            event.ask_price = ask
            event.spread = self.bid_ask_tracker.get_spread(instrument_id)
            
            # Process trades to derive direction
            if event.action == 'T':  # Trade
                self.trades_processed += 1
                event.trade_direction = self._derive_trade_direction(
                    event.price, bid, ask
                )
                
                # Determine price level
                if bid and ask:
                    mid = (bid + ask) / 2
                    if abs(event.price - bid) < 0.01:
                        event.price_level = 'BID'
                        event.aggressor_side = 'SELL'
                    elif abs(event.price - ask) < 0.01:
                        event.price_level = 'ASK'
                        event.aggressor_side = 'BUY'
                    elif abs(event.price - mid) < 0.01:
                        event.price_level = 'MID'
                    else:
                        # Price outside bid/ask
                        if event.price < bid:
                            event.price_level = 'BELOW_BID'
                        elif event.price > ask:
                            event.price_level = 'ABOVE_ASK'
            
            self.events_processed += 1
            return event
            
        except Exception as e:
            self.errors += 1
            logger.error(f"Error processing MBO event: {e}")
            return None
    
    def _derive_trade_direction(self, trade_price: float, 
                               bid_price: Optional[float], 
                               ask_price: Optional[float]) -> str:
        """
        Derive trade initiation direction based on price
        
        Logic:
        - trade_price == ask_price → BUY initiation (buyer aggressor)
        - trade_price == bid_price → SELL initiation (seller aggressor)
        - trade_price between bid/ask → NEUTRAL
        """
        if not bid_price or not ask_price:
            return 'UNKNOWN'
        
        # Allow small tolerance for price matching (0.01 = 1 cent)
        tolerance = 0.01
        
        if abs(trade_price - ask_price) <= tolerance:
            return 'BUY'  # Buyer lifted the ask
        elif abs(trade_price - bid_price) <= tolerance:
            return 'SELL'  # Seller hit the bid
        elif bid_price < trade_price < ask_price:
            return 'NEUTRAL'  # Traded inside spread
        else:
            return 'UNKNOWN'  # Outside normal range
    
    def aggregate_trade(self, event: ProcessedMBOEvent) -> Optional[StrikePressureMetrics]:
        """
        Aggregate trade event into pressure metrics
        
        Returns completed window metrics if window time has passed
        """
        if event.action != 'T' or not event.trade_direction:
            return None
        
        # Check for completed windows first
        completed = self._check_completed_windows()
        
        # Get window key
        window_start = self._get_window_start(event.exchange_timestamp)
        window_key = (event.strike_price, event.contract_type, window_start)
        
        with self._lock:
            # Add trade to window
            self.active_windows[window_key]['trades'].append(event)
            
            # Update volume based on direction
            if event.trade_direction == 'BUY':
                self.active_windows[window_key]['buy_volume'] += event.size
                self.active_windows[window_key]['buy_trades'] += 1
                if event.size > 100:
                    self.active_windows[window_key]['large_buy_trades'] += 1
                    
            elif event.trade_direction == 'SELL':
                self.active_windows[window_key]['sell_volume'] += event.size
                self.active_windows[window_key]['sell_trades'] += 1
                if event.size > 100:
                    self.active_windows[window_key]['large_sell_trades'] += 1
                    
            else:  # NEUTRAL or UNKNOWN
                self.active_windows[window_key]['neutral_volume'] += event.size
            
            # Track spread
            if event.spread:
                self.active_windows[window_key]['spreads'].append(event.spread)
        
        return completed
    
    def _get_window_start(self, timestamp: datetime) -> datetime:
        """Get the start time for the window containing this timestamp"""
        minutes = (timestamp.minute // self.window_minutes) * self.window_minutes
        return timestamp.replace(minute=minutes, second=0, microsecond=0)
    
    def _check_completed_windows(self) -> Optional[StrikePressureMetrics]:
        """Check for and finalize completed time windows"""
        current_time = datetime.now(timezone.utc)
        completed = None
        
        with self._lock:
            # Check each active window
            for window_key in list(self.active_windows.keys()):
                strike_price, contract_type, window_start = window_key
                window_end = window_start + timedelta(minutes=self.window_minutes)
                
                # If window has ended
                if current_time >= window_end + timedelta(seconds=30):  # 30s grace period
                    # Finalize metrics
                    window_data = self.active_windows[window_key]
                    
                    metrics = StrikePressureMetrics(
                        strike_price=strike_price,
                        contract_type=contract_type,
                        time_window_start=window_start,
                        time_window_end=window_end,
                        buy_volume=window_data.get('buy_volume', 0),
                        sell_volume=window_data.get('sell_volume', 0),
                        neutral_volume=window_data.get('neutral_volume', 0),
                        buy_trades=window_data.get('buy_trades', 0),
                        sell_trades=window_data.get('sell_trades', 0),
                        large_buy_trades=window_data.get('large_buy_trades', 0),
                        large_sell_trades=window_data.get('large_sell_trades', 0)
                    )
                    
                    # Calculate derived metrics
                    metrics.total_volume = metrics.buy_volume + metrics.sell_volume + metrics.neutral_volume
                    metrics.total_trades = metrics.buy_trades + metrics.sell_trades
                    metrics.net_pressure = metrics.buy_volume - metrics.sell_volume
                    
                    # Buy pressure ratio
                    if metrics.total_volume > 0:
                        metrics.buy_pressure_ratio = metrics.buy_volume / (metrics.buy_volume + metrics.sell_volume) \
                                                   if (metrics.buy_volume + metrics.sell_volume) > 0 else 0.5
                    
                    # Normalized pressure score (-1 to 1)
                    if metrics.total_volume > 0:
                        metrics.pressure_score = metrics.net_pressure / metrics.total_volume
                    
                    # Average trade sizes
                    if metrics.buy_trades > 0:
                        metrics.avg_buy_size = metrics.buy_volume / metrics.buy_trades
                    if metrics.sell_trades > 0:
                        metrics.avg_sell_size = metrics.sell_volume / metrics.sell_trades
                    
                    # Average spread
                    spreads = window_data.get('spreads', [])
                    if spreads:
                        metrics.avg_spread = sum(spreads) / len(spreads)
                        metrics.total_spread_samples = len(spreads)
                    
                    # Store completed metrics
                    self.completed_metrics.append(metrics)
                    
                    # Remove from active windows
                    del self.active_windows[window_key]
                    
                    # Return the first completed (could batch later)
                    if not completed:
                        completed = metrics
        
        return completed
    
    def get_recent_pressure(self, strike: float, lookback_minutes: int = 30) -> List[StrikePressureMetrics]:
        """Get recent pressure metrics for a specific strike"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
        
        recent = []
        for metrics in self.completed_metrics:
            if (metrics.strike_price == strike and 
                metrics.time_window_start >= cutoff_time):
                recent.append(metrics)
        
        return sorted(recent, key=lambda m: m.time_window_start)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        return {
            'events_processed': self.events_processed,
            'trades_processed': self.trades_processed,
            'errors': self.errors,
            'active_windows': len(self.active_windows),
            'completed_windows': len(self.completed_metrics),
            'cached_instruments': len(self.contract_mapper.instrument_cache),
            'tracked_instruments': len(self.bid_ask_tracker.bid_prices)
        }


def create_mbo_processor(window_minutes: int = 5) -> MBOEventStreamProcessor:
    """
    Factory function to create MBO event processor
    
    Args:
        window_minutes: Time window for pressure aggregation
        
    Returns:
        Configured MBOEventStreamProcessor instance
    """
    return MBOEventStreamProcessor(window_minutes)


if __name__ == "__main__":
    # Example usage and testing
    processor = create_mbo_processor(window_minutes=5)
    
    # Example MBO events
    test_events = [
        {
            'symbol': 'NQH5 C21000',
            'instrument_id': 12345,
            'ts_event': int(datetime.now(timezone.utc).timestamp() * 1e9),
            'action': 'A',  # Add order
            'side': 'B',    # Bid
            'price': 100.50,
            'size': 10,
            'sequence': 1
        },
        {
            'symbol': 'NQH5 C21000',
            'instrument_id': 12345,
            'ts_event': int(datetime.now(timezone.utc).timestamp() * 1e9),
            'action': 'A',  # Add order
            'side': 'A',    # Ask
            'price': 101.00,
            'size': 15,
            'sequence': 2
        },
        {
            'symbol': 'NQH5 C21000',
            'instrument_id': 12345,
            'ts_event': int(datetime.now(timezone.utc).timestamp() * 1e9),
            'action': 'T',  # Trade
            'side': 'T',
            'price': 101.00,  # Trade at ask = BUY
            'size': 5,
            'sequence': 3
        }
    ]
    
    # Process events
    for event_data in test_events:
        event = processor.process_event(event_data)
        if event:
            print(f"Processed: {event.action} - {event.side} - "
                  f"Price: {event.price} - Size: {event.size}")
            
            if event.action == 'T':
                print(f"  Trade Direction: {event.trade_direction}")
                print(f"  Price Level: {event.price_level}")
                
                # Aggregate trade
                metrics = processor.aggregate_trade(event)
                if metrics:
                    print(f"\nCompleted Window Metrics:")
                    print(f"  Strike: {metrics.strike_price}")
                    print(f"  Buy Pressure: {metrics.buy_pressure_ratio:.2%}")
                    print(f"  Net Pressure: {metrics.net_pressure}")
    
    print(f"\nProcessor Stats: {processor.get_stats()}")