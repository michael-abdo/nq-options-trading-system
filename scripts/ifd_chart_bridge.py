#!/usr/bin/env python3
"""
IFD Chart Bridge - Signal Aggregation for 5-Minute Charts

This module bridges real-time IFD v3.0 signals with 5-minute chart data by:
- Aggregating irregular real-time signals into aligned 5-minute windows
- Providing efficient time-range queries for chart rendering
- Maintaining signal quality through intelligent prioritization
- Ensuring thread-safe access for real-time updates

Architecture:
- Uses same 5-minute boundary logic as OHLCV data for perfect alignment
- Prioritizes signals by confidence and strength within each window
- Supports both historical queries and real-time updates
- Maintains recent signal cache for performance
"""

import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
from pathlib import Path
import json

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import existing components
from data_aggregation import MinuteToFiveMinuteAggregator
from utils.timezone_utils import get_eastern_time, get_utc_time

# Import IFD v3.0 components
try:
    from tasks.options_trading_system.analysis_engine.institutional_flow_v3.solution import (
        InstitutionalSignalV3, IFDv3Engine, create_ifd_v3_analyzer
    )
    IFD_V3_AVAILABLE = True
except ImportError as e:
    logging.warning(f"IFD v3.0 not available: {e}")
    IFD_V3_AVAILABLE = False

    # Create stub for development
    @dataclass
    class InstitutionalSignalV3:
        strike: float
        option_type: str
        timestamp: datetime
        final_confidence: float
        signal_strength: str
        recommended_action: str

logger = logging.getLogger(__name__)

@dataclass
class IFDAggregatedSignal:
    """
    Aggregated IFD signal for 5-minute chart windows

    Represents the strongest/most significant institutional signal
    within a 5-minute window, with supporting metadata.
    """
    # Window Identification
    window_timestamp: datetime        # 5-minute boundary timestamp (aligned with OHLCV)

    # Primary Signal Data
    primary_signal: InstitutionalSignalV3  # Strongest signal in window
    signal_count: int                # Total signals in window

    # Aggregated Metrics
    avg_confidence: float            # Average confidence across all signals
    max_confidence: float            # Peak confidence in window
    min_confidence: float            # Lowest confidence in window

    # Signal Classification
    dominant_action: str             # Primary recommended action
    window_strength: str             # Aggregated strength assessment
    confidence_trend: str            # INCREASING, DECREASING, STABLE

    # Timing Information
    first_signal_time: datetime      # Earliest signal in window
    last_signal_time: datetime       # Latest signal in window
    window_duration: float           # Seconds between first and last signal

    # Chart Visualization Data
    chart_y_position: Optional[float] = None  # Y-coordinate for chart placement
    chart_color: Optional[str] = None         # Color for chart rendering
    chart_size: Optional[float] = None        # Size factor for chart markers

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        d = asdict(self)
        # Convert datetime objects to ISO format
        d['window_timestamp'] = self.window_timestamp.isoformat()
        d['first_signal_time'] = self.first_signal_time.isoformat()
        d['last_signal_time'] = self.last_signal_time.isoformat()
        d['primary_signal'] = self.primary_signal.to_dict()
        return d

class IFDChartBridge:
    """
    Bridge component for aggregating IFD v3.0 signals into 5-minute chart windows

    Key Features:
    - Thread-safe signal aggregation from real-time IFD engine
    - Perfect timestamp alignment with OHLCV 5-minute boundaries
    - Intelligent signal prioritization within windows
    - Efficient time-range queries for chart rendering
    - Configurable aggregation strategies
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize IFD Chart Bridge

        Args:
            config: Configuration dictionary with aggregation settings
        """
        self.config = config or self._get_default_config()

        # Thread-safe storage for aggregated signals
        self._lock = threading.RLock()
        self.aggregated_signals: Dict[datetime, IFDAggregatedSignal] = {}
        self.raw_signal_buffer: deque = deque(maxlen=1000)  # Last 1000 raw signals

        # Current window tracking
        self.current_window_start: Optional[datetime] = None
        self.current_window_signals: List[InstitutionalSignalV3] = []

        # Performance metrics
        self.total_signals_processed = 0
        self.total_windows_created = 0
        self.last_update_time: Optional[datetime] = None

        logger.info("IFD Chart Bridge initialized")

    def _get_default_config(self) -> Dict[str, Any]:
        """Default configuration for signal aggregation"""
        return {
            'aggregation': {
                'strategy': 'highest_confidence',  # 'highest_confidence', 'weighted_average', 'latest'
                'min_signal_confidence': 0.6,     # Minimum confidence to include in aggregation
                'window_minutes': 5,               # Window size (should stay 5 for chart alignment)
                'max_signals_per_window': 10       # Limit signals per window for performance
            },
            'cache': {
                'max_windows': 500,                # Maximum aggregated windows to keep in memory
                'cleanup_interval_hours': 4        # Hours after which to clean old signals
            },
            'chart': {
                'default_color_strong': 'green',
                'default_color_weak': 'orange',
                'default_color_neutral': 'gray',
                'size_multiplier': 1.0
            }
        }

    def _get_5min_boundary(self, timestamp: datetime) -> datetime:
        """
        Get 5-minute boundary timestamp for perfect OHLCV alignment

        Uses same logic as data_aggregation.py for consistency
        """
        minute = timestamp.minute
        rounded_minute = (minute // 5) * 5
        return timestamp.replace(minute=rounded_minute, second=0, microsecond=0)

    def add_signal(self, signal: InstitutionalSignalV3) -> Optional[IFDAggregatedSignal]:
        """
        Add a new IFD signal and return completed window if boundary crossed

        Args:
            signal: Real-time IFD v3.0 signal

        Returns:
            Completed aggregated signal if window boundary was crossed, None otherwise
        """
        try:
            with self._lock:
                # Input validation
                if signal is None:
                    logger.warning("Received None signal - ignoring")
                    return None

                if not hasattr(signal, 'final_confidence') or not hasattr(signal, 'timestamp'):
                    logger.warning("Invalid signal format - missing required attributes")
                    return None

                # Validate timestamp
                if signal.timestamp is None:
                    logger.warning("Signal has None timestamp - using current time")
                    signal.timestamp = datetime.now(timezone.utc)

                # Update metrics
                self.total_signals_processed += 1
                self.last_update_time = datetime.now(timezone.utc)

                # Add to raw buffer (with error handling)
                try:
                    self.raw_signal_buffer.append(signal)
                except Exception as e:
                    logger.warning(f"Failed to add signal to buffer: {e}")

                # Check signal quality with fallback
                min_confidence = self.config.get('aggregation', {}).get('min_signal_confidence', 0.6)
                if signal.final_confidence < min_confidence:
                    logger.debug(f"Signal below confidence threshold: {signal.final_confidence:.3f}")
                    return None

                # Get window boundary for this signal (with error handling)
                try:
                    window_start = self._get_5min_boundary(signal.timestamp)
                except Exception as e:
                    logger.error(f"Failed to calculate window boundary: {e}")
                    window_start = self._get_5min_boundary(datetime.now(timezone.utc))

                # Check if we've crossed into a new window
                completed_signal = None
                if self.current_window_start and window_start > self.current_window_start:
                    # Complete the previous window
                    if self.current_window_signals:
                        try:
                            completed_signal = self._aggregate_window_signals(
                                self.current_window_start, self.current_window_signals
                            )
                            if completed_signal:
                                self.aggregated_signals[self.current_window_start] = completed_signal
                                self.total_windows_created += 1
                        except Exception as e:
                            logger.error(f"Failed to aggregate window signals: {e}")

                    # Start new window
                    self.current_window_start = window_start
                    self.current_window_signals = [signal]
                else:
                    # Add to current window
                    if self.current_window_start is None:
                        self.current_window_start = window_start
                        self.current_window_signals = []

                    self.current_window_signals.append(signal)

                    # Check window signal limit with fallback
                    max_signals = self.config.get('aggregation', {}).get('max_signals_per_window', 10)
                    if len(self.current_window_signals) > max_signals:
                        self.current_window_signals = self.current_window_signals[-max_signals:]

                # Cleanup old signals periodically (with error handling)
                try:
                    self._cleanup_old_signals()
                except Exception as e:
                    logger.warning(f"Failed to cleanup old signals: {e}")

                return completed_signal

        except Exception as e:
            logger.error(f"Critical error in add_signal: {e}")
            return None  # Graceful degradation

    def _aggregate_window_signals(self, window_start: datetime,
                                 signals: List[InstitutionalSignalV3]) -> Optional[IFDAggregatedSignal]:
        """
        Aggregate multiple signals within a 5-minute window

        Args:
            window_start: 5-minute boundary timestamp
            signals: All signals within the window

        Returns:
            Aggregated signal representing the window
        """
        try:
            if not signals:
                return None

            # Validate signals have required attributes
            valid_signals = []
            for signal in signals:
                if hasattr(signal, 'final_confidence') and hasattr(signal, 'timestamp'):
                    valid_signals.append(signal)
                else:
                    logger.warning("Signal missing required attributes - skipping")

            if not valid_signals:
                logger.warning("No valid signals to aggregate")
                return None

            # Sort signals by confidence (highest first) with error handling
            try:
                sorted_signals = sorted(valid_signals, key=lambda s: getattr(s, 'final_confidence', 0.0), reverse=True)
            except Exception as e:
                logger.warning(f"Failed to sort signals by confidence: {e}")
                sorted_signals = valid_signals

            # Select primary signal based on strategy with fallback
            strategy = self.config.get('aggregation', {}).get('strategy', 'highest_confidence')
            try:
                if strategy == 'highest_confidence':
                    primary_signal = sorted_signals[0]
                elif strategy == 'latest':
                    primary_signal = max(valid_signals, key=lambda s: getattr(s, 'timestamp', datetime.min))
                else:  # Default to highest confidence
                    primary_signal = sorted_signals[0]
            except Exception as e:
                logger.error(f"Failed to select primary signal: {e}")
                primary_signal = valid_signals[0]  # Fallback to first valid signal

            # Calculate aggregated metrics with error handling
            try:
                confidences = [getattr(s, 'final_confidence', 0.0) for s in valid_signals]
                confidences = [c for c in confidences if isinstance(c, (int, float))]  # Filter valid numbers

                if confidences:
                    avg_confidence = sum(confidences) / len(confidences)
                    max_confidence = max(confidences)
                    min_confidence = min(confidences)
                else:
                    avg_confidence = max_confidence = min_confidence = 0.0
            except Exception as e:
                logger.warning(f"Failed to calculate confidence metrics: {e}")
                avg_confidence = max_confidence = min_confidence = 0.0

            # Determine dominant action with fallback
            try:
                actions = [getattr(s, 'recommended_action', 'MONITOR') for s in valid_signals]
                action_counts = defaultdict(int)
                for action in actions:
                    if action:  # Only count non-empty actions
                        action_counts[action] += 1

                if action_counts:
                    dominant_action = max(action_counts.items(), key=lambda x: x[1])[0]
                else:
                    dominant_action = 'MONITOR'  # Default fallback
            except Exception as e:
                logger.warning(f"Failed to determine dominant action: {e}")
                dominant_action = 'MONITOR'

            # Assess window strength with error handling
            try:
                window_strength = self._assess_window_strength(valid_signals)
            except Exception as e:
                logger.warning(f"Failed to assess window strength: {e}")
                window_strength = 'MODERATE'

            # Calculate confidence trend with error handling
            try:
                confidence_trend = self._calculate_confidence_trend(valid_signals)
            except Exception as e:
                logger.warning(f"Failed to calculate confidence trend: {e}")
                confidence_trend = 'STABLE'

            # Timing information with error handling
            try:
                timestamps = [getattr(s, 'timestamp', datetime.now(timezone.utc)) for s in valid_signals]
                timestamps = [t for t in timestamps if t is not None]  # Filter None timestamps

                if timestamps:
                    first_signal_time = min(timestamps)
                    last_signal_time = max(timestamps)
                    window_duration = (last_signal_time - first_signal_time).total_seconds()
                else:
                    first_signal_time = last_signal_time = window_start
                    window_duration = 0.0
            except Exception as e:
                logger.warning(f"Failed to calculate timing information: {e}")
                first_signal_time = last_signal_time = window_start
                window_duration = 0.0

            # Chart visualization data with error handling
            try:
                chart_color = self._get_chart_color(primary_signal)
                chart_size = self._get_chart_size(primary_signal)
            except Exception as e:
                logger.warning(f"Failed to get chart visualization data: {e}")
                chart_color = self.config.get('chart', {}).get('default_color_neutral', 'gray')
                chart_size = 1.0

            return IFDAggregatedSignal(
                window_timestamp=window_start,
                primary_signal=primary_signal,
                signal_count=len(valid_signals),
                avg_confidence=avg_confidence,
                max_confidence=max_confidence,
                min_confidence=min_confidence,
                dominant_action=dominant_action,
                window_strength=window_strength,
                confidence_trend=confidence_trend,
                first_signal_time=first_signal_time,
                last_signal_time=last_signal_time,
                window_duration=window_duration,
                chart_color=chart_color,
                chart_size=chart_size
            )

        except Exception as e:
            logger.error(f"Critical error in signal aggregation: {e}")
            return None  # Graceful degradation

    def _assess_window_strength(self, signals: List[InstitutionalSignalV3]) -> str:
        """Assess overall strength of signals in window"""
        if not signals:
            return 'NONE'

        # Count signal strengths
        strength_counts = defaultdict(int)
        for signal in signals:
            strength_counts[signal.signal_strength] += 1

        # Prioritize stronger signals
        if strength_counts['EXTREME'] > 0:
            return 'EXTREME'
        elif strength_counts['VERY_HIGH'] > 0:
            return 'VERY_HIGH'
        elif strength_counts['HIGH'] > 0:
            return 'HIGH'
        else:
            return 'MODERATE'

    def _calculate_confidence_trend(self, signals: List[InstitutionalSignalV3]) -> str:
        """Calculate confidence trend across signals in window"""
        if len(signals) < 2:
            return 'STABLE'

        # Sort by timestamp
        sorted_signals = sorted(signals, key=lambda s: s.timestamp)
        confidences = [s.final_confidence for s in sorted_signals]

        # Simple trend analysis
        first_half_avg = sum(confidences[:len(confidences)//2]) / (len(confidences)//2)
        second_half_avg = sum(confidences[len(confidences)//2:]) / (len(confidences) - len(confidences)//2)

        if second_half_avg > first_half_avg + 0.1:
            return 'INCREASING'
        elif second_half_avg < first_half_avg - 0.1:
            return 'DECREASING'
        else:
            return 'STABLE'

    def _get_chart_color(self, signal: InstitutionalSignalV3) -> str:
        """Determine chart color based on signal characteristics"""
        if signal.final_confidence >= 0.8:
            return self.config['chart']['default_color_strong']
        elif signal.final_confidence >= 0.6:
            return self.config['chart']['default_color_weak']
        else:
            return self.config['chart']['default_color_neutral']

    def _get_chart_size(self, signal: InstitutionalSignalV3) -> float:
        """Determine chart marker size based on signal strength"""
        size_map = {
            'EXTREME': 2.0,
            'VERY_HIGH': 1.5,
            'HIGH': 1.2,
            'MODERATE': 1.0
        }
        base_size = size_map.get(signal.signal_strength, 1.0)
        return base_size * self.config['chart']['size_multiplier']

    def _cleanup_old_signals(self):
        """Remove old aggregated signals to manage memory"""
        cleanup_hours = self.config['cache']['cleanup_interval_hours']
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=cleanup_hours)

        # Remove old aggregated signals
        old_windows = [
            window_time for window_time in self.aggregated_signals.keys()
            if window_time < cutoff_time
        ]

        for window_time in old_windows:
            del self.aggregated_signals[window_time]

        if old_windows:
            logger.debug(f"Cleaned up {len(old_windows)} old signal windows")

    def get_signals_for_timerange(self, start_time: datetime,
                                 end_time: datetime) -> List[IFDAggregatedSignal]:
        """
        Get aggregated IFD signals for a specific time range (for chart rendering)

        Args:
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)

        Returns:
            List of aggregated signals within the time range, sorted by timestamp
        """
        with self._lock:
            # Find signals within time range
            matching_signals = []
            for window_time, signal in self.aggregated_signals.items():
                if start_time <= window_time <= end_time:
                    matching_signals.append(signal)

            # Sort by timestamp
            matching_signals.sort(key=lambda s: s.window_timestamp)

            logger.debug(f"Retrieved {len(matching_signals)} aggregated signals for range {start_time} to {end_time}")

            return matching_signals

    def get_ifd_signals_for_chart(self, start_time: datetime,
                                 end_time: datetime) -> List[IFDAggregatedSignal]:
        """
        Main API method for chart integration - alias for get_signals_for_timerange

        This is the primary method that chart components should use to retrieve
        IFD signals for visualization.

        Args:
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)

        Returns:
            List of aggregated IFD signals ready for chart display
        """
        try:
            return self.get_signals_for_timerange(start_time, end_time)
        except Exception as e:
            logger.error(f"Failed to retrieve IFD signals for chart: {e}")
            return []  # Return empty list on error to prevent chart crashes

    def get_latest_signals(self, count: int = 10) -> List[IFDAggregatedSignal]:
        """Get the most recent aggregated signals"""
        with self._lock:
            # Sort all signals by timestamp and take the latest
            all_signals = list(self.aggregated_signals.values())
            all_signals.sort(key=lambda s: s.window_timestamp, reverse=True)

            return all_signals[:count]

    def get_current_window_preview(self) -> Optional[Dict[str, Any]]:
        """Get preview of current incomplete window (for real-time display)"""
        with self._lock:
            if not self.current_window_signals:
                return None

            return {
                'window_start': self.current_window_start.isoformat() if self.current_window_start else None,
                'signal_count': len(self.current_window_signals),
                'max_confidence': max(s.final_confidence for s in self.current_window_signals),
                'latest_signal_time': max(s.timestamp for s in self.current_window_signals).isoformat()
            }

    def get_bridge_statistics(self) -> Dict[str, Any]:
        """Get statistics about bridge performance and signal processing"""
        with self._lock:
            return {
                'total_signals_processed': self.total_signals_processed,
                'total_windows_created': self.total_windows_created,
                'current_aggregated_signals': len(self.aggregated_signals),
                'current_window_signals': len(self.current_window_signals),
                'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
                'memory_usage': {
                    'aggregated_signals': len(self.aggregated_signals),
                    'raw_signal_buffer': len(self.raw_signal_buffer)
                }
            }

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status of the bridge for monitoring

        Returns:
            Health status with various metrics and diagnostics
        """
        try:
            with self._lock:
                now = datetime.now(timezone.utc)

                # Check last update recency
                if self.last_update_time:
                    time_since_update = (now - self.last_update_time).total_seconds()
                    update_status = 'healthy' if time_since_update < 300 else 'stale'  # 5 minutes
                else:
                    time_since_update = None
                    update_status = 'no_data'

                # Memory usage assessment
                memory_usage = len(self.aggregated_signals) + len(self.raw_signal_buffer)
                memory_status = 'healthy' if memory_usage < 1000 else 'high'

                # Signal processing rate
                processing_rate = self.total_signals_processed / max(1, (now - datetime(2024, 1, 1, tzinfo=timezone.utc)).total_seconds() / 3600)

                # Overall health assessment
                health_issues = []
                if update_status != 'healthy':
                    health_issues.append('stale_updates')
                if memory_status != 'healthy':
                    health_issues.append('high_memory_usage')

                overall_status = 'healthy' if not health_issues else 'degraded'

                return {
                    'overall_status': overall_status,
                    'issues': health_issues,
                    'update_status': update_status,
                    'time_since_last_update_seconds': time_since_update,
                    'memory_status': memory_status,
                    'memory_usage_total': memory_usage,
                    'processing_rate_per_hour': processing_rate,
                    'uptime_hours': (now - datetime(2024, 1, 1, tzinfo=timezone.utc)).total_seconds() / 3600,
                    'current_window_active': self.current_window_start is not None,
                    'current_window_signal_count': len(self.current_window_signals),
                    'total_windows_created': self.total_windows_created,
                    'total_signals_processed': self.total_signals_processed
                }

        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {
                'overall_status': 'error',
                'issues': ['health_check_failed'],
                'error': str(e)
            }

    def reset_bridge(self) -> bool:
        """
        Emergency reset of bridge state (for recovery from errors)

        Returns:
            True if reset successful, False otherwise
        """
        try:
            with self._lock:
                logger.warning("Performing emergency reset of IFD Chart Bridge")

                # Clear all data
                self.aggregated_signals.clear()
                self.raw_signal_buffer.clear()
                self.current_window_signals.clear()
                self.current_window_start = None

                # Reset metrics
                self.total_signals_processed = 0
                self.total_windows_created = 0
                self.last_update_time = None

                logger.info("IFD Chart Bridge reset completed successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to reset bridge: {e}")
            return False

# Factory function for easy integration
def create_ifd_chart_bridge(config: Optional[Dict[str, Any]] = None) -> IFDChartBridge:
    """
    Factory function to create IFD Chart Bridge instance

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured IFDChartBridge instance
    """
    return IFDChartBridge(config)

# Example usage and testing
if __name__ == "__main__":
    # Example configuration
    config = {
        'aggregation': {
            'strategy': 'highest_confidence',
            'min_signal_confidence': 0.6
        }
    }

    # Create bridge
    bridge = create_ifd_chart_bridge(config)

    print("=== IFD Chart Bridge Test ===")
    print(f"Bridge initialized with config: {bridge.config}")

    # Test with sample signals (if available)
    if IFD_V3_AVAILABLE:
        # Create sample signal
        from datetime import datetime, timezone

        sample_signal = InstitutionalSignalV3(
            strike=21900.0,
            option_type='C',
            timestamp=datetime.now(timezone.utc),
            pressure_ratio=3.0,
            bid_volume=100,
            ask_volume=300,
            dominant_side='BUY',
            pressure_confidence=0.85,
            baseline_pressure_ratio=1.5,
            pressure_zscore=2.8,
            percentile_rank=95.0,
            anomaly_detected=True,
            market_making_probability=0.15,
            straddle_coordination=False,
            volatility_crush_detected=False,
            raw_confidence=0.8,
            baseline_confidence=0.9,
            market_making_penalty=0.1,
            coordination_bonus=0.0,
            final_confidence=0.85,
            signal_strength='VERY_HIGH',
            institutional_probability=0.88,
            recommended_action='BUY',
            risk_score=0.3,
            position_size_multiplier=1.5,
            max_position_risk=0.05
        )

        # Add signal to bridge
        completed_window = bridge.add_signal(sample_signal)

        if completed_window:
            print(f"Completed window: {completed_window.window_timestamp}")
        else:
            print("Signal added to current window")

        # Show bridge statistics
        stats = bridge.get_bridge_statistics()
        print(f"Bridge stats: {stats}")
    else:
        print("IFD v3.0 not available - bridge created in standalone mode")
