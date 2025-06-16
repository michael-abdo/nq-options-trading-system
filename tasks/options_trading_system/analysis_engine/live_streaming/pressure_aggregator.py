#!/usr/bin/env python3
"""
Real-time Pressure Metrics Aggregation for IFD v3.0

This module provides enhanced real-time pressure metrics aggregation from raw MBO data
with optimizations for live streaming performance and memory efficiency.

Key Features:
- Multi-timeframe aggregation (1m, 5m, 15m windows)
- Memory-efficient sliding windows
- Real-time pressure ratio calculation
- Trade direction classification
- Volume-weighted analysis
- Performance monitoring and auto-cleanup

Architecture:
Raw MBO Events → Trade Classification → Window Aggregation → Pressure Metrics → IFD Analysis
"""

import os
import sys
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Callable, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
import statistics

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(current_dir)))

from utils.timezone_utils import get_eastern_time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradeEvent:
    """Individual trade event with direction classification"""
    timestamp: datetime
    strike: float
    option_type: str  # 'C' or 'P'
    trade_price: float
    trade_size: int
    side: str  # 'BUY', 'SELL', 'UNKNOWN'
    bid_price: float
    ask_price: float
    confidence: float  # Confidence in side classification

@dataclass
class PressureMetrics:
    """Enhanced pressure metrics with multiple timeframes"""
    strike: float
    option_type: str
    time_window: datetime
    window_duration: int  # minutes

    # Volume analysis
    bid_volume: int
    ask_volume: int
    total_volume: int
    pressure_ratio: float

    # Trade characteristics
    total_trades: int
    avg_trade_size: float
    dominant_side: str

    # Enhanced metrics
    volume_weighted_price: float
    price_momentum: float  # Price change within window
    trade_intensity: float  # Trades per minute

    # Quality metrics
    confidence: float
    data_quality: float

@dataclass
class WindowConfig:
    """Configuration for aggregation windows"""
    duration_minutes: int = 5
    min_trades: int = 3
    min_volume: int = 50
    max_windows: int = 1000  # Memory limit
    cleanup_interval: int = 100  # Cleanup every N new windows

class TradeClassifier:
    """Classifies trade direction from price and market data"""

    def __init__(self):
        """Initialize trade classifier"""
        self.price_history = defaultdict(lambda: deque(maxlen=10))

    def classify_trade(self, trade_price: float, bid_price: float, ask_price: float,
                      strike: float, option_type: str) -> Tuple[str, float]:
        """
        Classify trade direction with confidence score

        Args:
            trade_price: Executed trade price
            bid_price: Current bid price
            ask_price: Current ask price
            strike: Option strike price
            option_type: Option type ('C' or 'P')

        Returns:
            Tuple of (side, confidence) where side is 'BUY', 'SELL', or 'UNKNOWN'
        """
        if bid_price <= 0 or ask_price <= 0 or trade_price <= 0:
            return 'UNKNOWN', 0.0

        # Basic tick test
        mid_price = (bid_price + ask_price) / 2
        spread = ask_price - bid_price

        # Distance from mid
        distance_from_mid = abs(trade_price - mid_price)
        relative_position = (trade_price - bid_price) / spread if spread > 0 else 0.5

        # Classification logic
        if relative_position >= 0.8:  # Close to ask
            side = 'BUY'
            confidence = min(0.9, 0.6 + relative_position * 0.4)
        elif relative_position <= 0.2:  # Close to bid
            side = 'SELL'
            confidence = min(0.9, 0.6 + (1 - relative_position) * 0.4)
        else:
            # Check price momentum for tie-breaking
            key = f"{strike}_{option_type}"
            history = self.price_history[key]

            if len(history) >= 2:
                recent_trend = trade_price - statistics.mean(history)
                if recent_trend > 0:
                    side = 'BUY'
                    confidence = 0.6
                elif recent_trend < 0:
                    side = 'SELL'
                    confidence = 0.6
                else:
                    side = 'UNKNOWN'
                    confidence = 0.3
            else:
                side = 'UNKNOWN'
                confidence = 0.3

        # Update price history
        self.price_history[key].append(trade_price)

        return side, confidence

class MultiTimeframeAggregator:
    """Aggregates pressure metrics across multiple timeframes"""

    def __init__(self, window_configs: List[WindowConfig]):
        """Initialize multi-timeframe aggregator

        Args:
            window_configs: List of window configurations for different timeframes
        """
        self.window_configs = {config.duration_minutes: config for config in window_configs}
        self.active_windows = defaultdict(lambda: defaultdict(dict))
        self.trade_classifier = TradeClassifier()

        # Performance tracking
        self.windows_created = 0
        self.windows_completed = 0
        self.last_cleanup = time.time()

        # Callbacks
        self.pressure_callbacks = []

        # Threading
        self.lock = threading.RLock()

    def add_trade_event(self, trade_data: Dict[str, Any]) -> List[PressureMetrics]:
        """
        Add trade event and return completed pressure metrics

        Args:
            trade_data: Raw trade data from MBO stream

        Returns:
            List of completed pressure metrics (multiple timeframes)
        """
        # Convert to TradeEvent
        trade_event = self._create_trade_event(trade_data)
        if not trade_event:
            return []

        completed_metrics = []

        with self.lock:
            # Process each timeframe
            for duration, config in self.window_configs.items():
                metrics = self._process_timeframe(trade_event, duration, config)
                if metrics:
                    completed_metrics.append(metrics)

            # Check for expired windows across all timeframes
            for duration in self.window_configs:
                expired = self._check_expired_windows(trade_event.timestamp, duration)
                completed_metrics.extend(expired)

            # Periodic cleanup
            if time.time() - self.last_cleanup > 60:  # Every minute
                self._cleanup_old_windows()
                self.last_cleanup = time.time()

        # Notify callbacks
        for metrics in completed_metrics:
            self._notify_callbacks(metrics)

        return completed_metrics

    def _create_trade_event(self, trade_data: Dict[str, Any]) -> Optional[TradeEvent]:
        """Create TradeEvent from raw data"""
        try:
            # Extract basic fields
            timestamp = trade_data.get('timestamp', datetime.now(timezone.utc))
            trade_price = float(trade_data.get('trade_price', 0))
            trade_size = int(trade_data.get('trade_size', 0))
            bid_price = float(trade_data.get('bid_price', 0))
            ask_price = float(trade_data.get('ask_price', 0))

            # Get instrument info
            strike = float(trade_data.get('strike', 21900.0))
            option_type = trade_data.get('option_type', 'C')

            # Skip invalid trades
            if trade_size <= 0 or trade_price <= 0:
                return None

            # Classify trade direction
            side, confidence = self.trade_classifier.classify_trade(
                trade_price, bid_price, ask_price, strike, option_type
            )

            return TradeEvent(
                timestamp=timestamp,
                strike=strike,
                option_type=option_type,
                trade_price=trade_price,
                trade_size=trade_size,
                side=side,
                bid_price=bid_price,
                ask_price=ask_price,
                confidence=confidence
            )

        except (ValueError, TypeError) as e:
            logger.debug(f"Invalid trade data: {e}")
            return None

    def _process_timeframe(self, trade_event: TradeEvent, duration: int,
                          config: WindowConfig) -> Optional[PressureMetrics]:
        """Process trade event for specific timeframe"""

        # Get window start time
        window_start = self._get_window_start(trade_event.timestamp, duration)

        # Create window key
        window_key = f"{trade_event.strike}_{trade_event.option_type}_{window_start.isoformat()}"

        # Initialize window if new
        if window_key not in self.active_windows[duration]:
            self.active_windows[duration][window_key] = {
                'start_time': window_start,
                'end_time': window_start + timedelta(minutes=duration),
                'trades': [],
                'bid_volume': 0,
                'ask_volume': 0,
                'total_volume': 0,
                'buy_volume': 0,
                'sell_volume': 0,
                'vwap_sum': 0.0,
                'vwap_volume': 0,
                'first_price': trade_event.trade_price,
                'last_price': trade_event.trade_price
            }
            self.windows_created += 1

        window = self.active_windows[duration][window_key]

        # Add trade to window
        window['trades'].append(trade_event)
        window['total_volume'] += trade_event.trade_size
        window['last_price'] = trade_event.trade_price

        # Update VWAP
        window['vwap_sum'] += trade_event.trade_price * trade_event.trade_size
        window['vwap_volume'] += trade_event.trade_size

        # Update side-specific volumes
        if trade_event.side == 'BUY':
            window['buy_volume'] += trade_event.trade_size
            window['ask_volume'] += trade_event.trade_size  # Buy hits ask
        elif trade_event.side == 'SELL':
            window['sell_volume'] += trade_event.trade_size
            window['bid_volume'] += trade_event.trade_size  # Sell hits bid

        # Check if window is complete
        if trade_event.timestamp >= window['end_time']:
            # Window is complete - finalize it
            metrics = self._finalize_window(trade_event.strike, trade_event.option_type,
                                          window, duration)
            del self.active_windows[duration][window_key]
            self.windows_completed += 1
            return metrics

        return None

    def _get_window_start(self, timestamp: datetime, duration_minutes: int) -> datetime:
        """Get window start time for given timestamp and duration"""
        # Round down to nearest window interval
        minutes = (timestamp.minute // duration_minutes) * duration_minutes
        return timestamp.replace(minute=minutes, second=0, microsecond=0)

    def _finalize_window(self, strike: float, option_type: str, window: Dict[str, Any],
                        duration: int) -> PressureMetrics:
        """Finalize completed window and create pressure metrics"""

        trades = window['trades']
        total_volume = window['total_volume']

        # Calculate pressure ratio
        bid_volume = window['bid_volume']
        ask_volume = window['ask_volume']

        if bid_volume > 0:
            pressure_ratio = ask_volume / bid_volume
        else:
            pressure_ratio = float('inf') if ask_volume > 0 else 1.0

        # Determine dominant side
        if total_volume > 0:
            buy_percentage = window['buy_volume'] / total_volume
            if buy_percentage > 0.6:
                dominant_side = 'BUY'
            elif buy_percentage < 0.4:
                dominant_side = 'SELL'
            else:
                dominant_side = 'NEUTRAL'
        else:
            dominant_side = 'NEUTRAL'

        # Calculate enhanced metrics
        vwap = window['vwap_sum'] / window['vwap_volume'] if window['vwap_volume'] > 0 else 0
        price_momentum = (window['last_price'] - window['first_price']) / window['first_price'] if window['first_price'] > 0 else 0
        trade_intensity = len(trades) / duration  # Trades per minute

        # Calculate confidence
        avg_confidence = statistics.mean([t.confidence for t in trades]) if trades else 0.0
        volume_confidence = min(total_volume / 200.0, 1.0)  # Confidence based on volume
        trade_confidence = min(len(trades) / 10.0, 1.0)     # Confidence based on trade count

        confidence = (avg_confidence * 0.4 + volume_confidence * 0.3 + trade_confidence * 0.3)

        # Data quality assessment
        valid_trades = sum(1 for t in trades if t.confidence > 0.5)
        data_quality = valid_trades / len(trades) if trades else 0.0

        return PressureMetrics(
            strike=strike,
            option_type=option_type,
            time_window=window['start_time'],
            window_duration=duration,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            total_volume=total_volume,
            pressure_ratio=pressure_ratio,
            total_trades=len(trades),
            avg_trade_size=total_volume / len(trades) if trades else 0,
            dominant_side=dominant_side,
            volume_weighted_price=vwap,
            price_momentum=price_momentum,
            trade_intensity=trade_intensity,
            confidence=confidence,
            data_quality=data_quality
        )

    def _check_expired_windows(self, current_time: datetime, duration: int) -> List[PressureMetrics]:
        """Check for and complete any expired windows"""
        completed_metrics = []

        # Find windows that should be completed
        windows_to_complete = []
        for window_key, window_data in self.active_windows[duration].items():
            if current_time >= window_data['end_time'] and len(window_data['trades']) > 0:
                windows_to_complete.append(window_key)

        # Complete expired windows
        for window_key in windows_to_complete:
            # Parse window key
            parts = window_key.split('_')
            strike = float(parts[0])
            option_type = parts[1]

            window = self.active_windows[duration][window_key]
            metrics = self._finalize_window(strike, option_type, window, duration)
            completed_metrics.append(metrics)

            # Remove completed window
            del self.active_windows[duration][window_key]
            self.windows_completed += 1

        return completed_metrics

    def _cleanup_old_windows(self):
        """Clean up old windows to prevent memory leaks"""
        current_time = datetime.now(timezone.utc)
        cleanup_threshold = current_time - timedelta(hours=1)  # Keep last hour

        total_cleaned = 0

        for duration in self.active_windows:
            keys_to_remove = []
            for window_key, window_data in self.active_windows[duration].items():
                if window_data['end_time'] < cleanup_threshold:
                    keys_to_remove.append(window_key)

            for key in keys_to_remove:
                del self.active_windows[duration][key]
                total_cleaned += 1

        if total_cleaned > 0:
            logger.debug(f"🧹 Cleaned up {total_cleaned} old windows")

    def register_pressure_callback(self, callback: Callable[[PressureMetrics], None]):
        """Register callback for completed pressure metrics"""
        self.pressure_callbacks.append(callback)

    def _notify_callbacks(self, metrics: PressureMetrics):
        """Notify all callbacks of new pressure metrics"""
        for callback in self.pressure_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                logger.error(f"Pressure callback error: {e}")

    def get_aggregation_stats(self) -> Dict[str, Any]:
        """Get aggregation performance statistics"""
        total_active = sum(len(windows) for windows in self.active_windows.values())

        return {
            'windows_created': self.windows_created,
            'windows_completed': self.windows_completed,
            'active_windows': total_active,
            'timeframes': list(self.window_configs.keys()),
            'completion_rate': self.windows_completed / max(self.windows_created, 1),
            'memory_usage': {
                duration: len(windows) for duration, windows in self.active_windows.items()
            }
        }

class RealTimePressureEngine:
    """Main engine for real-time pressure metrics aggregation"""

    def __init__(self, timeframes: List[int] = None):
        """Initialize real-time pressure engine

        Args:
            timeframes: List of timeframe durations in minutes (default: [1, 5, 15])
        """
        if timeframes is None:
            timeframes = [1, 5, 15]

        # Create window configurations
        configs = [
            WindowConfig(duration_minutes=tf, min_trades=max(1, tf), min_volume=tf * 20)
            for tf in timeframes
        ]

        self.aggregator = MultiTimeframeAggregator(configs)
        self.timeframes = timeframes

        # Performance tracking
        self.events_processed = 0
        self.metrics_generated = 0
        self.start_time = datetime.now(timezone.utc)

        logger.info(f"Real-time pressure engine initialized with timeframes: {timeframes}")

    def process_mbo_event(self, mbo_data: Dict[str, Any]) -> List[PressureMetrics]:
        """
        Process MBO event and return completed pressure metrics

        Args:
            mbo_data: Raw MBO event data

        Returns:
            List of completed pressure metrics across timeframes
        """
        self.events_processed += 1

        # Process through aggregator
        metrics_list = self.aggregator.add_trade_event(mbo_data)
        self.metrics_generated += len(metrics_list)

        return metrics_list

    def register_pressure_callback(self, callback: Callable[[PressureMetrics], None]):
        """Register callback for pressure metrics"""
        self.aggregator.register_pressure_callback(callback)

    def get_engine_stats(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics"""
        runtime = (datetime.now(timezone.utc) - self.start_time).total_seconds()

        stats = {
            'runtime_seconds': runtime,
            'events_processed': self.events_processed,
            'metrics_generated': self.metrics_generated,
            'processing_rate': self.events_processed / max(runtime, 1),
            'metrics_rate': self.metrics_generated / max(runtime, 1),
            'timeframes': self.timeframes
        }

        # Add aggregator stats
        stats['aggregation'] = self.aggregator.get_aggregation_stats()

        return stats

# Factory functions for different use cases
def create_high_frequency_engine() -> RealTimePressureEngine:
    """Create engine optimized for high-frequency analysis"""
    return RealTimePressureEngine(timeframes=[1, 3, 5])

def create_standard_engine() -> RealTimePressureEngine:
    """Create engine with standard timeframes"""
    return RealTimePressureEngine(timeframes=[1, 5, 15])

def create_institutional_engine() -> RealTimePressureEngine:
    """Create engine optimized for institutional flow detection"""
    return RealTimePressureEngine(timeframes=[5, 15, 30])

# Example usage and testing
if __name__ == "__main__":
    print("=== Real-time Pressure Engine Test ===")

    # Create engine
    engine = create_standard_engine()

    # Test callback
    def test_pressure_callback(metrics: PressureMetrics):
        print(f"📊 Pressure: {metrics.strike}{metrics.option_type} "
              f"{metrics.window_duration}m ratio={metrics.pressure_ratio:.2f} "
              f"confidence={metrics.confidence:.2f}")

    engine.register_pressure_callback(test_pressure_callback)

    # Simulate MBO events
    for i in range(20):
        test_event = {
            'timestamp': datetime.now(timezone.utc),
            'strike': 21900.0,
            'option_type': 'C',
            'trade_price': 100 + i * 0.5,
            'trade_size': 10 + i,
            'bid_price': 99 + i * 0.5,
            'ask_price': 101 + i * 0.5
        }

        metrics_list = engine.process_mbo_event(test_event)
        time.sleep(0.1)

    # Get stats
    stats = engine.get_engine_stats()
    print("\n📈 Engine Stats:")
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")

    print("\n✅ Real-time pressure engine test completed")
