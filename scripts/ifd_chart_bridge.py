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
        with self._lock:
            # Update metrics
            self.total_signals_processed += 1
            self.last_update_time = datetime.now(timezone.utc)
            
            # Add to raw buffer
            self.raw_signal_buffer.append(signal)
            
            # Check signal quality
            if signal.final_confidence < self.config['aggregation']['min_signal_confidence']:
                logger.debug(f"Signal below confidence threshold: {signal.final_confidence:.3f}")
                return None
            
            # Get window boundary for this signal
            window_start = self._get_5min_boundary(signal.timestamp)
            
            # Check if we've crossed into a new window
            completed_signal = None
            if self.current_window_start and window_start > self.current_window_start:
                # Complete the previous window
                if self.current_window_signals:
                    completed_signal = self._aggregate_window_signals(
                        self.current_window_start, self.current_window_signals
                    )
                    if completed_signal:
                        self.aggregated_signals[self.current_window_start] = completed_signal
                        self.total_windows_created += 1
                
                # Start new window
                self.current_window_start = window_start
                self.current_window_signals = [signal]
            else:
                # Add to current window
                if self.current_window_start is None:
                    self.current_window_start = window_start
                    self.current_window_signals = []
                
                self.current_window_signals.append(signal)
                
                # Check window signal limit
                max_signals = self.config['aggregation']['max_signals_per_window']
                if len(self.current_window_signals) > max_signals:
                    self.current_window_signals = self.current_window_signals[-max_signals:]
            
            # Cleanup old signals periodically
            self._cleanup_old_signals()
            
            return completed_signal
    
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
        if not signals:
            return None
        
        # Sort signals by confidence (highest first)
        sorted_signals = sorted(signals, key=lambda s: s.final_confidence, reverse=True)
        
        # Select primary signal based on strategy
        strategy = self.config['aggregation']['strategy']
        if strategy == 'highest_confidence':
            primary_signal = sorted_signals[0]
        elif strategy == 'latest':
            primary_signal = max(signals, key=lambda s: s.timestamp)
        else:  # Default to highest confidence
            primary_signal = sorted_signals[0]
        
        # Calculate aggregated metrics
        confidences = [s.final_confidence for s in signals]
        avg_confidence = sum(confidences) / len(confidences)
        max_confidence = max(confidences)
        min_confidence = min(confidences)
        
        # Determine dominant action
        actions = [s.recommended_action for s in signals]
        action_counts = defaultdict(int)
        for action in actions:
            action_counts[action] += 1
        dominant_action = max(action_counts.items(), key=lambda x: x[1])[0]
        
        # Assess window strength
        window_strength = self._assess_window_strength(signals)
        
        # Calculate confidence trend
        confidence_trend = self._calculate_confidence_trend(signals)
        
        # Timing information
        timestamps = [s.timestamp for s in signals]
        first_signal_time = min(timestamps)
        last_signal_time = max(timestamps)
        window_duration = (last_signal_time - first_signal_time).total_seconds()
        
        # Chart visualization data
        chart_color = self._get_chart_color(primary_signal)
        chart_size = self._get_chart_size(primary_signal)
        
        return IFDAggregatedSignal(
            window_timestamp=window_start,
            primary_signal=primary_signal,
            signal_count=len(signals),
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