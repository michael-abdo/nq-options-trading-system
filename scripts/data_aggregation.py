#!/usr/bin/env python3
"""
Data aggregation module for converting 1-minute bars to 5-minute bars
Uses Databento 1-minute OHLCV data as input
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import logging
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from utils.timezone_utils import get_eastern_time

logger = logging.getLogger(__name__)

class TimeBar:
    """Represents a single OHLCV bar with timestamp"""

    def __init__(self, timestamp: datetime, open_price: float, high_price: float,
                 low_price: float, close_price: float, volume: int):
        self.timestamp = timestamp
        self.open = open_price
        self.high = high_price
        self.low = low_price
        self.close = close_price
        self.volume = volume

    def to_dict(self) -> Dict:
        """Convert to dictionary for DataFrame creation"""
        return {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume
        }

    def __repr__(self):
        return f"TimeBar({self.timestamp.strftime('%H:%M')}, O:{self.open:.2f}, H:{self.high:.2f}, L:{self.low:.2f}, C:{self.close:.2f}, V:{self.volume})"

class MinuteToFiveMinuteAggregator:
    """Aggregates 1-minute bars into 5-minute bars"""

    def __init__(self):
        self.buffer: List[Dict] = []  # Buffer for incoming 1-minute bars
        self.completed_bars: List[TimeBar] = []  # Completed 5-minute bars

    def _get_5min_boundary(self, timestamp: datetime) -> datetime:
        """Get the 5-minute boundary for a given timestamp"""
        # Round down to nearest 5-minute mark
        minute = timestamp.minute
        rounded_minute = (minute // 5) * 5
        return timestamp.replace(minute=rounded_minute, second=0, microsecond=0)

    def _aggregate_buffer(self, bars: List[Dict]) -> Optional[TimeBar]:
        """Aggregate a list of 1-minute bars into a single 5-minute bar"""
        if not bars:
            return None

        # Sort by timestamp to ensure correct order
        bars = sorted(bars, key=lambda x: x['timestamp'])

        # Create 5-minute bar
        timestamp = self._get_5min_boundary(bars[0]['timestamp'])
        open_price = bars[0]['open']
        close_price = bars[-1]['close']
        high_price = max(bar['high'] for bar in bars)
        low_price = min(bar['low'] for bar in bars)
        volume = sum(bar['volume'] for bar in bars)

        return TimeBar(timestamp, open_price, high_price, low_price, close_price, volume)

    def add_1min_bar(self, bar_data: Dict) -> Optional[TimeBar]:
        """
        Add a 1-minute bar and return completed 5-minute bar if ready

        Args:
            bar_data: Dict with keys: timestamp, open, high, low, close, volume

        Returns:
            Completed 5-minute TimeBar if a boundary is crossed, None otherwise
        """
        # Add to buffer
        self.buffer.append(bar_data)

        # Check if we've crossed a 5-minute boundary
        if len(self.buffer) >= 2:
            current_boundary = self._get_5min_boundary(self.buffer[-1]['timestamp'])
            previous_boundary = self._get_5min_boundary(self.buffer[-2]['timestamp'])

            if current_boundary > previous_boundary:
                # We've crossed a boundary - aggregate previous period
                bars_to_aggregate = [b for b in self.buffer[:-1]
                                   if self._get_5min_boundary(b['timestamp']) == previous_boundary]

                if bars_to_aggregate:
                    completed_bar = self._aggregate_buffer(bars_to_aggregate)
                    if completed_bar:
                        self.completed_bars.append(completed_bar)

                        # Remove aggregated bars from buffer
                        self.buffer = [b for b in self.buffer
                                     if self._get_5min_boundary(b['timestamp']) > previous_boundary]

                        return completed_bar

        return None

    def flush(self) -> Optional[TimeBar]:
        """Force aggregation of remaining buffer data"""
        if self.buffer:
            completed_bar = self._aggregate_buffer(self.buffer)
            if completed_bar:
                self.completed_bars.append(completed_bar)
                self.buffer = []
                return completed_bar
        return None

    def get_all_completed_bars(self) -> List[TimeBar]:
        """Get all completed 5-minute bars"""
        return self.completed_bars.copy()

    def to_dataframe(self) -> pd.DataFrame:
        """Convert all completed bars to pandas DataFrame"""
        if not self.completed_bars:
            return pd.DataFrame()

        data = [bar.to_dict() for bar in self.completed_bars]
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df

def aggregate_1min_to_5min(one_minute_data: pd.DataFrame) -> pd.DataFrame:
    """
    Utility function to aggregate 1-minute OHLCV data to 5-minute bars

    Args:
        one_minute_data: DataFrame with columns: open, high, low, close, volume
                        and datetime index

    Returns:
        DataFrame with 5-minute OHLCV bars
    """
    # Ensure we have a datetime index
    if not isinstance(one_minute_data.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have a DatetimeIndex")

    # Resample to 5-minute bars
    aggregation_rules = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }

    five_minute_data = one_minute_data.resample('5min').agg(aggregation_rules)

    # Remove any rows with NaN values (incomplete periods)
    five_minute_data = five_minute_data.dropna()

    return five_minute_data

def test_aggregation():
    """Test the aggregation functionality"""
    print("🧪 Testing 1-minute to 5-minute aggregation...")

    # Create sample 1-minute data starting at market open (Eastern Time)
    start_time = get_eastern_time().replace(hour=9, minute=30, second=0, microsecond=0)
    one_min_bars = []

    base_price = 21800
    for i in range(15):  # 15 minutes of data = 3 five-minute bars
        timestamp = start_time + timedelta(minutes=i)
        open_price = base_price + np.random.normal(0, 2)
        high_price = open_price + abs(np.random.normal(1, 1))
        low_price = open_price - abs(np.random.normal(1, 1))
        close_price = open_price + np.random.normal(0, 0.5)
        volume = np.random.randint(100, 300)

        one_min_bars.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })

        base_price = close_price

    # Test streaming aggregation
    print("\n📊 Testing streaming aggregation:")
    aggregator = MinuteToFiveMinuteAggregator()

    for bar in one_min_bars:
        completed_bar = aggregator.add_1min_bar(bar)
        if completed_bar:
            print(f"  ✅ Completed 5-min bar: {completed_bar}")

    # Flush remaining
    final_bar = aggregator.flush()
    if final_bar:
        print(f"  ✅ Final 5-min bar: {final_bar}")

    # Test batch aggregation
    print("\n📊 Testing batch aggregation:")
    df_1min = pd.DataFrame(one_min_bars)
    df_1min.set_index('timestamp', inplace=True)

    df_5min = aggregate_1min_to_5min(df_1min)
    print(f"  Input: {len(df_1min)} 1-minute bars")
    print(f"  Output: {len(df_5min)} 5-minute bars")
    print("\nResulting 5-minute bars:")
    print(df_5min)

    return aggregator, df_5min

if __name__ == "__main__":
    test_aggregation()
