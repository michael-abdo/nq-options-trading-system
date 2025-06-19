#!/usr/bin/env python3
"""
Quote Pressure to PressureMetrics Adapter
========================================

This adapter transforms real-time quote pressure data (bid_sz_00/ask_sz_00) into
the PressureMetrics format expected by IFD v3's analysis pipeline.

Key Challenges Addressed:
1. Quote data is snapshot-based, while PressureMetrics expects cumulative volume
2. Quote sizes represent standing orders, not executed trades
3. Need to simulate trade volume from quote pressure changes
4. Maintain time window aggregation for compatibility

Strategy:
- Track quote size changes as proxy for trading interest
- Aggregate quote pressure over time windows (default 5 minutes)
- Convert quote imbalances to simulated bid/ask volumes
- Calculate confidence based on quote stability and size
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

# Import PressureMetrics from IFD v3
try:
    from tasks.options_trading_system.data_ingestion.databento_api.solution import PressureMetrics
except ImportError:
    # Define local copy if import fails
    @dataclass
    class PressureMetrics:
        """Aggregated pressure metrics for a strike/time window"""
        strike: float
        option_type: str
        time_window: datetime
        bid_volume: int
        ask_volume: int
        pressure_ratio: float
        total_trades: int
        avg_trade_size: float
        dominant_side: str
        confidence: float

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QuotePressureSnapshot:
    """Raw quote pressure data from monitoring"""
    timestamp: datetime
    symbol: str
    strike: float
    option_type: str
    bid_size: int
    ask_size: int
    bid_price: float
    ask_price: float
    pressure_ratio: float


class QuotePressureAdapter:
    """
    Converts quote pressure data into PressureMetrics format for IFD v3

    This adapter handles the fundamental differences between:
    - Quote data: Standing orders at specific price levels
    - Trade volume: Actual executed transactions

    Approach:
    1. Track quote size changes as proxy for trading activity
    2. Aggregate changes over time windows
    3. Convert to simulated volume metrics
    4. Calculate confidence based on quote activity patterns
    """

    def __init__(self, window_minutes: int = 5, volume_multiplier: float = 10.0):
        """
        Initialize adapter with configuration

        Args:
            window_minutes: Time window for aggregation (default 5 min)
            volume_multiplier: Multiplier to convert quote changes to volume
        """
        self.window_minutes = window_minutes
        self.volume_multiplier = volume_multiplier

        # Track quote history by strike/type
        self.quote_history = defaultdict(lambda: deque(maxlen=100))

        # Active aggregation windows
        self.active_windows = defaultdict(lambda: {
            'start_time': None,
            'bid_volume_simulated': 0,
            'ask_volume_simulated': 0,
            'quote_changes': [],
            'total_quote_updates': 0,
            'max_bid_size': 0,
            'max_ask_size': 0,
            'pressure_samples': []
        })

        # Track last quote state for change detection
        self.last_quotes = {}

    def add_quote_snapshot(self, snapshot: QuotePressureSnapshot) -> Optional[PressureMetrics]:
        """
        Process a quote pressure snapshot and potentially return completed PressureMetrics

        Args:
            snapshot: Quote pressure data snapshot

        Returns:
            PressureMetrics if window completed, None otherwise
        """
        # First check for expired windows
        completed_metrics = self._check_and_complete_expired_windows(snapshot.timestamp)

        # Calculate window start
        window_start = self._get_window_start(snapshot.timestamp)

        # Create window key
        window_key = f"{snapshot.strike}_{snapshot.option_type}_{window_start.isoformat()}"

        # Initialize window if new
        if self.active_windows[window_key]['start_time'] is None:
            self.active_windows[window_key]['start_time'] = window_start

        # Process quote changes
        self._process_quote_changes(snapshot, window_key)

        # Update window statistics
        window_data = self.active_windows[window_key]
        window_data['total_quote_updates'] += 1
        window_data['max_bid_size'] = max(window_data['max_bid_size'], snapshot.bid_size)
        window_data['max_ask_size'] = max(window_data['max_ask_size'], snapshot.ask_size)
        window_data['pressure_samples'].append(snapshot.pressure_ratio)

        # Store in history
        history_key = f"{snapshot.strike}_{snapshot.option_type}"
        self.quote_history[history_key].append(snapshot)

        return completed_metrics

    def _process_quote_changes(self, snapshot: QuotePressureSnapshot, window_key: str):
        """Convert quote size changes into simulated volume"""

        # Create unique key for this strike/type
        quote_key = f"{snapshot.strike}_{snapshot.option_type}"

        # Get last quote state
        last_quote = self.last_quotes.get(quote_key)

        if last_quote:
            # Calculate size changes
            bid_change = snapshot.bid_size - last_quote.bid_size
            ask_change = snapshot.ask_size - last_quote.ask_size

            # Simulate volume from quote changes
            # Positive bid change = buying interest (simulated ask volume)
            # Positive ask change = selling interest (simulated bid volume)

            if bid_change > 0:
                # More bids = buying pressure
                simulated_ask_volume = int(abs(bid_change) * self.volume_multiplier)
                self.active_windows[window_key]['ask_volume_simulated'] += simulated_ask_volume

            elif bid_change < 0:
                # Fewer bids = reduced buying pressure
                simulated_bid_volume = int(abs(bid_change) * self.volume_multiplier * 0.5)
                self.active_windows[window_key]['bid_volume_simulated'] += simulated_bid_volume

            if ask_change > 0:
                # More asks = selling pressure
                simulated_bid_volume = int(abs(ask_change) * self.volume_multiplier)
                self.active_windows[window_key]['bid_volume_simulated'] += simulated_bid_volume

            elif ask_change < 0:
                # Fewer asks = reduced selling pressure
                simulated_ask_volume = int(abs(ask_change) * self.volume_multiplier * 0.5)
                self.active_windows[window_key]['ask_volume_simulated'] += simulated_ask_volume

            # Track significant changes
            if abs(bid_change) >= 10 or abs(ask_change) >= 10:
                self.active_windows[window_key]['quote_changes'].append({
                    'timestamp': snapshot.timestamp,
                    'bid_change': bid_change,
                    'ask_change': ask_change,
                    'bid_size': snapshot.bid_size,
                    'ask_size': snapshot.ask_size
                })

        # Update last quote state
        self.last_quotes[quote_key] = snapshot

    def _get_window_start(self, timestamp: datetime) -> datetime:
        """Get the start time for the window containing this timestamp"""
        minutes = (timestamp.minute // self.window_minutes) * self.window_minutes
        return timestamp.replace(minute=minutes, second=0, microsecond=0)

    def _check_and_complete_expired_windows(self, current_timestamp: datetime) -> Optional[PressureMetrics]:
        """Check for and complete any expired windows"""
        completed_metrics = None
        window_duration = timedelta(minutes=self.window_minutes)

        # Check all active windows
        for window_key, window_data in list(self.active_windows.items()):
            if window_data['start_time'] is None:
                continue

            window_end = window_data['start_time'] + window_duration

            # If window has expired, finalize it
            if current_timestamp >= window_end:
                # Parse window key
                parts = window_key.split('_')
                strike = float(parts[0])
                option_type = parts[1]

                # Create metrics
                completed_metrics = self._finalize_window(
                    window_key, strike, option_type, window_data['start_time']
                )

                # Only return the first completed window
                break

        return completed_metrics

    def _finalize_window(self, window_key: str, strike: float, option_type: str,
                        window_start: datetime) -> PressureMetrics:
        """Convert accumulated quote pressure into PressureMetrics"""

        window_data = self.active_windows[window_key]

        # Get simulated volumes
        bid_volume = window_data['bid_volume_simulated']
        ask_volume = window_data['ask_volume_simulated']

        # Calculate pressure ratio
        if bid_volume > 0:
            pressure_ratio = ask_volume / bid_volume
        else:
            pressure_ratio = float('inf') if ask_volume > 0 else 1.0

        # Determine dominant side
        total_volume = bid_volume + ask_volume
        if total_volume > 0:
            buy_percentage = ask_volume / total_volume
            if buy_percentage > 0.6:
                dominant_side = 'BUY'
            elif buy_percentage < 0.4:
                dominant_side = 'SELL'
            else:
                dominant_side = 'NEUTRAL'
        else:
            dominant_side = 'NEUTRAL'

        # Calculate confidence based on:
        # 1. Number of quote updates (activity level)
        # 2. Size of quote changes (significance)
        # 3. Consistency of pressure direction

        activity_confidence = min(window_data['total_quote_updates'] / 50.0, 1.0)

        # Calculate average quote sizes for significance
        avg_quote_size = (window_data['max_bid_size'] + window_data['max_ask_size']) / 2
        size_confidence = min(avg_quote_size / 100.0, 1.0)

        # Calculate pressure consistency
        if window_data['pressure_samples']:
            pressure_std = self._calculate_std(window_data['pressure_samples'])
            consistency_confidence = max(0, 1.0 - (pressure_std / 2.0))
        else:
            consistency_confidence = 0.5

        # Combined confidence
        confidence = (activity_confidence * 0.4 +
                     size_confidence * 0.3 +
                     consistency_confidence * 0.3)

        # Simulate trade count from significant quote changes
        significant_changes = len(window_data['quote_changes'])
        total_trades = max(significant_changes * 2, 1)  # Assume each change represents ~2 trades

        # Average trade size (simulated)
        avg_trade_size = total_volume / total_trades if total_trades > 0 else 0

        # Create PressureMetrics
        metrics = PressureMetrics(
            strike=strike,
            option_type=option_type,
            time_window=window_start,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            pressure_ratio=pressure_ratio,
            total_trades=total_trades,
            avg_trade_size=avg_trade_size,
            dominant_side=dominant_side,
            confidence=confidence
        )

        # Log conversion
        logger.info(f"Converted quote pressure to PressureMetrics: "
                   f"{option_type} {strike} @ {window_start.strftime('%H:%M')} - "
                   f"Bid Vol: {bid_volume}, Ask Vol: {ask_volume}, "
                   f"Ratio: {pressure_ratio:.2f}, Confidence: {confidence:.2f}")

        # Clean up completed window
        del self.active_windows[window_key]

        return metrics

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def force_complete_all_windows(self) -> List[PressureMetrics]:
        """Force completion of all active windows (useful at end of session)"""
        completed_metrics = []

        for window_key, window_data in list(self.active_windows.items()):
            if window_data['start_time'] is None:
                continue

            # Parse window key
            parts = window_key.split('_')
            strike = float(parts[0])
            option_type = parts[1]

            # Create metrics
            metrics = self._finalize_window(
                window_key, strike, option_type, window_data['start_time']
            )
            completed_metrics.append(metrics)

        return completed_metrics


# Example usage function
def create_quote_snapshot_from_monitor_data(monitor_data: dict) -> QuotePressureSnapshot:
    """
    Helper function to create QuotePressureSnapshot from quote monitor data

    Args:
        monitor_data: Dictionary from nq_options_quote_pressure.py

    Returns:
        QuotePressureSnapshot instance
    """
    # Extract option type from symbol
    symbol = monitor_data['symbol']
    if ' C' in symbol:
        option_type = 'C'
    elif ' P' in symbol:
        option_type = 'P'
    else:
        raise ValueError(f"Cannot determine option type from symbol: {symbol}")

    return QuotePressureSnapshot(
        timestamp=monitor_data.get('last_update', datetime.now(timezone.utc)),
        symbol=symbol,
        strike=monitor_data['strike'],
        option_type=option_type,
        bid_size=monitor_data['bid_size'],
        ask_size=monitor_data['ask_size'],
        bid_price=monitor_data['bid_price'],
        ask_price=monitor_data['ask_price'],
        pressure_ratio=monitor_data['pressure_ratio']
    )


if __name__ == "__main__":
    # Example usage
    print("Quote Pressure to PressureMetrics Adapter")
    print("=" * 60)

    # Create adapter
    adapter = QuotePressureAdapter(window_minutes=5, volume_multiplier=10.0)

    # Simulate some quote snapshots
    test_snapshots = [
        QuotePressureSnapshot(
            timestamp=datetime.now(timezone.utc),
            symbol="NQM5 C22000",
            strike=22000,
            option_type="C",
            bid_size=50,
            ask_size=30,
            bid_price=150.5,
            ask_price=151.0,
            pressure_ratio=1.67
        ),
        QuotePressureSnapshot(
            timestamp=datetime.now(timezone.utc) + timedelta(seconds=30),
            symbol="NQM5 C22000",
            strike=22000,
            option_type="C",
            bid_size=75,  # Increased bid size
            ask_size=25,  # Decreased ask size
            bid_price=150.75,
            ask_price=151.25,
            pressure_ratio=3.0
        )
    ]

    # Process snapshots
    for snapshot in test_snapshots:
        print(f"\nProcessing: {snapshot.symbol} - Bid: {snapshot.bid_size}, Ask: {snapshot.ask_size}")
        metrics = adapter.add_quote_snapshot(snapshot)
        if metrics:
            print(f"Completed window: {metrics}")

    print("\n✅ Adapter ready for integration with IFD v3")
