#!/usr/bin/env python3
"""
Market Relevance Window Tracker - Signal Timing and Market Relevance Analysis

This module tracks how long signals remain relevant and actionable in the market,
providing critical feedback for shadow trading validation and signal optimization.
"""

import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SignalEvent:
    """Individual signal event tracking"""
    signal_id: str
    timestamp: datetime
    signal_type: str           # call_buying, put_buying, etc.
    strike: float
    confidence: float
    expected_value: float
    market_conditions: Dict[str, Any]

    # Tracking fields
    generated_at: datetime
    first_actionable: Optional[datetime] = None
    last_actionable: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None

    # Relevance metrics
    relevance_score: float = 0.0
    actionable_duration_seconds: float = 0.0
    market_movement_correlation: float = 0.0
    timing_score: float = 0.0


@dataclass
class RelevanceWindow:
    """Market relevance window analysis"""
    window_start: datetime
    window_end: datetime
    duration_seconds: float

    # Signal characteristics during window
    signals_count: int
    avg_confidence: float
    avg_expected_value: float

    # Market characteristics
    market_volatility: float
    volume_activity: float
    price_movement: float

    # Relevance metrics
    signals_executed: int
    execution_rate: float
    avg_time_to_execution: float
    success_rate: float

    # Market correlation
    correlation_score: float
    timing_quality: float


@dataclass
class RelevanceStats:
    """Overall relevance statistics"""
    total_signals: int
    avg_relevance_duration: float
    median_relevance_duration: float
    peak_relevance_hours: List[str]

    # Execution timing
    avg_time_to_execution: float
    execution_rate: float

    # Market correlation
    strong_correlation_pct: float  # % of signals with strong market correlation
    timing_score: float

    # Quality metrics
    actionable_signals_pct: float
    expired_signals_pct: float
    optimal_timing_pct: float      # % of signals with optimal timing


class MarketRelevanceTracker:
    """
    Tracks signal relevance windows and market timing for shadow trading validation

    This component monitors:
    - How long signals remain actionable in the market
    - Correlation between signal timing and market movements
    - Optimal execution windows for different signal types
    - Market condition impact on signal relevance
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize market relevance tracker

        Args:
            config: Configuration parameters
        """
        self.config = config or {}

        # Configuration parameters
        self.relevance_window_minutes = self.config.get('relevance_window_minutes', 30)
        self.min_confidence_threshold = self.config.get('min_confidence_threshold', 0.65)
        self.correlation_threshold = self.config.get('correlation_threshold', 0.7)
        self.max_tracking_hours = self.config.get('max_tracking_hours', 8)

        # Tracking data structures
        self.active_signals: Dict[str, SignalEvent] = {}
        self.completed_signals: List[SignalEvent] = []
        self.relevance_windows: List[RelevanceWindow] = []

        # Market data cache
        self.market_data_history: deque = deque(maxlen=1000)
        self.volume_history: deque = deque(maxlen=1000)
        self.price_history: deque = deque(maxlen=1000)

        # Performance tracking
        self.stats_cache = None
        self.last_stats_update = None

        logger.info("Market Relevance Tracker initialized")

    def track_signal(self, signal: Dict[str, Any], market_data: Dict[str, Any] = None) -> str:
        """
        Start tracking a new signal for relevance analysis

        Args:
            signal: Signal data to track
            market_data: Current market conditions

        Returns:
            Signal tracking ID
        """
        signal_id = signal.get('id', f"signal_{int(time.time())}")

        # Create signal event
        signal_event = SignalEvent(
            signal_id=signal_id,
            timestamp=datetime.now(timezone.utc),
            signal_type=signal.get('signal_type', 'unknown'),
            strike=signal.get('strike', 0.0),
            confidence=signal.get('confidence', 0.0),
            expected_value=signal.get('expected_value', 0.0),
            market_conditions=market_data or {},
            generated_at=datetime.now(timezone.utc)
        )

        # Add to active tracking
        self.active_signals[signal_id] = signal_event

        # Update market data history
        if market_data:
            self.market_data_history.append({
                'timestamp': datetime.now(timezone.utc),
                'data': market_data
            })

        logger.debug(f"Started tracking signal {signal_id}")
        return signal_id

    def update_signal_status(self, signal_id: str, status: str,
                           market_data: Dict[str, Any] = None) -> bool:
        """
        Update signal status during tracking

        Args:
            signal_id: Signal to update
            status: New status (actionable, executed, expired)
            market_data: Current market conditions

        Returns:
            True if updated successfully
        """
        if signal_id not in self.active_signals:
            logger.warning(f"Signal {signal_id} not found in active tracking")
            return False

        signal_event = self.active_signals[signal_id]
        current_time = datetime.now(timezone.utc)

        if status == 'actionable':
            if signal_event.first_actionable is None:
                signal_event.first_actionable = current_time
            signal_event.last_actionable = current_time

        elif status == 'executed':
            signal_event.executed_at = current_time
            signal_event.last_actionable = current_time

            # Calculate metrics
            self._calculate_signal_metrics(signal_event, market_data)

            # Move to completed
            self.completed_signals.append(signal_event)
            del self.active_signals[signal_id]

        elif status == 'expired':
            signal_event.expired_at = current_time

            # Calculate metrics
            self._calculate_signal_metrics(signal_event, market_data)

            # Move to completed
            self.completed_signals.append(signal_event)
            del self.active_signals[signal_id]

        # Update market data
        if market_data:
            self.market_data_history.append({
                'timestamp': current_time,
                'data': market_data
            })

        return True

    def _calculate_signal_metrics(self, signal_event: SignalEvent,
                                market_data: Dict[str, Any] = None):
        """Calculate relevance and timing metrics for a signal"""

        # Calculate actionable duration
        if signal_event.first_actionable and signal_event.last_actionable:
            duration = signal_event.last_actionable - signal_event.first_actionable
            signal_event.actionable_duration_seconds = duration.total_seconds()

        # Calculate relevance score
        signal_event.relevance_score = self._calculate_relevance_score(signal_event)

        # Calculate market movement correlation
        signal_event.market_movement_correlation = self._calculate_market_correlation(
            signal_event, market_data
        )

        # Calculate timing score
        signal_event.timing_score = self._calculate_timing_score(signal_event)

    def _calculate_relevance_score(self, signal_event: SignalEvent) -> float:
        """Calculate overall relevance score for a signal"""
        score = 0.0

        # Base score from confidence
        score += signal_event.confidence * 0.3

        # Duration factor (longer actionable duration = higher relevance)
        if signal_event.actionable_duration_seconds > 0:
            # Normalize to 0-1 scale (30 minutes = 1.0)
            duration_score = min(signal_event.actionable_duration_seconds / 1800, 1.0)
            score += duration_score * 0.3

        # Execution factor
        if signal_event.executed_at:
            score += 0.4  # Successfully executed
        elif signal_event.expired_at:
            score += 0.1  # Expired without execution

        return min(score, 1.0)

    def _calculate_market_correlation(self, signal_event: SignalEvent,
                                    market_data: Dict[str, Any] = None) -> float:
        """Calculate correlation between signal and market movements"""

        if not self.market_data_history or len(self.market_data_history) < 2:
            return 0.0

        # Get market data around signal time
        signal_time = signal_event.generated_at

        # Find market data points before and after signal
        before_data = None
        after_data = None

        for entry in self.market_data_history:
            entry_time = entry['timestamp']
            if entry_time <= signal_time:
                before_data = entry['data']
            elif entry_time >= signal_time and after_data is None:
                after_data = entry['data']
                break

        if not before_data or not after_data:
            return 0.0

        # Calculate market movement
        before_price = before_data.get('price', 0.0)
        after_price = after_data.get('price', 0.0)

        if before_price == 0:
            return 0.0

        price_change_pct = (after_price - before_price) / before_price

        # Determine expected direction based on signal type
        expected_direction = 1.0  # Default: expect price increase
        if 'put' in signal_event.signal_type.lower():
            expected_direction = -1.0

        # Calculate correlation
        actual_direction = 1.0 if price_change_pct > 0 else -1.0
        correlation = expected_direction * actual_direction

        # Scale by magnitude of movement
        movement_magnitude = abs(price_change_pct) * 100  # Convert to percentage points
        correlation_score = correlation * min(movement_magnitude / 2.0, 1.0)  # 2% movement = max score

        return max(0.0, correlation_score)

    def _calculate_timing_score(self, signal_event: SignalEvent) -> float:
        """Calculate timing quality score"""

        if not signal_event.executed_at:
            return 0.0

        # Time from generation to execution
        time_to_execution = signal_event.executed_at - signal_event.generated_at
        execution_seconds = time_to_execution.total_seconds()

        # Optimal execution timing (5-30 minutes typically optimal)
        optimal_min_seconds = 300   # 5 minutes
        optimal_max_seconds = 1800  # 30 minutes

        if optimal_min_seconds <= execution_seconds <= optimal_max_seconds:
            timing_score = 1.0
        elif execution_seconds < optimal_min_seconds:
            # Too fast - may be impulsive
            timing_score = execution_seconds / optimal_min_seconds
        else:
            # Too slow - may have lost relevance
            timing_score = max(0.1, optimal_max_seconds / execution_seconds)

        return timing_score

    def analyze_relevance_window(self, start_time: datetime,
                               end_time: datetime) -> RelevanceWindow:
        """
        Analyze signal relevance for a specific time window

        Args:
            start_time: Window start time
            end_time: Window end time

        Returns:
            RelevanceWindow analysis
        """
        # Find signals in window
        window_signals = []
        for signal in self.completed_signals:
            if start_time <= signal.generated_at <= end_time:
                window_signals.append(signal)

        if not window_signals:
            return RelevanceWindow(
                window_start=start_time,
                window_end=end_time,
                duration_seconds=(end_time - start_time).total_seconds(),
                signals_count=0,
                avg_confidence=0.0,
                avg_expected_value=0.0,
                market_volatility=0.0,
                volume_activity=0.0,
                price_movement=0.0,
                signals_executed=0,
                execution_rate=0.0,
                avg_time_to_execution=0.0,
                success_rate=0.0,
                correlation_score=0.0,
                timing_quality=0.0
            )

        # Calculate window metrics
        signals_count = len(window_signals)
        avg_confidence = statistics.mean(s.confidence for s in window_signals)
        avg_expected_value = statistics.mean(s.expected_value for s in window_signals)

        executed_signals = [s for s in window_signals if s.executed_at]
        signals_executed = len(executed_signals)
        execution_rate = signals_executed / signals_count

        # Timing metrics
        if executed_signals:
            execution_times = []
            for signal in executed_signals:
                time_diff = signal.executed_at - signal.generated_at
                execution_times.append(time_diff.total_seconds())
            avg_time_to_execution = statistics.mean(execution_times)
        else:
            avg_time_to_execution = 0.0

        # Correlation and timing quality
        correlation_scores = [s.market_movement_correlation for s in window_signals if s.market_movement_correlation > 0]
        correlation_score = statistics.mean(correlation_scores) if correlation_scores else 0.0

        timing_scores = [s.timing_score for s in window_signals if s.timing_score > 0]
        timing_quality = statistics.mean(timing_scores) if timing_scores else 0.0

        # Market characteristics (simplified - would use actual market data)
        market_volatility = self._estimate_market_volatility(start_time, end_time)
        volume_activity = self._estimate_volume_activity(start_time, end_time)
        price_movement = self._estimate_price_movement(start_time, end_time)

        # Success rate (based on profitable signals)
        profitable_signals = sum(1 for s in window_signals if s.market_movement_correlation > 0.5)
        success_rate = profitable_signals / signals_count if signals_count > 0 else 0.0

        window = RelevanceWindow(
            window_start=start_time,
            window_end=end_time,
            duration_seconds=(end_time - start_time).total_seconds(),
            signals_count=signals_count,
            avg_confidence=avg_confidence,
            avg_expected_value=avg_expected_value,
            market_volatility=market_volatility,
            volume_activity=volume_activity,
            price_movement=price_movement,
            signals_executed=signals_executed,
            execution_rate=execution_rate,
            avg_time_to_execution=avg_time_to_execution,
            success_rate=success_rate,
            correlation_score=correlation_score,
            timing_quality=timing_quality
        )

        self.relevance_windows.append(window)
        return window

    def _estimate_market_volatility(self, start_time: datetime, end_time: datetime) -> float:
        """Estimate market volatility for time window"""
        # Simplified implementation - would use actual market data
        return 0.25  # Placeholder

    def _estimate_volume_activity(self, start_time: datetime, end_time: datetime) -> float:
        """Estimate volume activity for time window"""
        # Simplified implementation - would use actual volume data
        return 0.8  # Placeholder

    def _estimate_price_movement(self, start_time: datetime, end_time: datetime) -> float:
        """Estimate price movement for time window"""
        # Simplified implementation - would use actual price data
        return 0.02  # 2% movement placeholder

    def get_relevance_statistics(self) -> RelevanceStats:
        """Get comprehensive relevance statistics"""

        if not self.completed_signals:
            return RelevanceStats(
                total_signals=0,
                avg_relevance_duration=0.0,
                median_relevance_duration=0.0,
                peak_relevance_hours=[],
                avg_time_to_execution=0.0,
                execution_rate=0.0,
                strong_correlation_pct=0.0,
                timing_score=0.0,
                actionable_signals_pct=0.0,
                expired_signals_pct=0.0,
                optimal_timing_pct=0.0
            )

        total_signals = len(self.completed_signals)

        # Duration statistics
        durations = [s.actionable_duration_seconds for s in self.completed_signals if s.actionable_duration_seconds > 0]
        avg_relevance_duration = statistics.mean(durations) if durations else 0.0
        median_relevance_duration = statistics.median(durations) if durations else 0.0

        # Execution statistics
        executed_signals = [s for s in self.completed_signals if s.executed_at]
        execution_rate = len(executed_signals) / total_signals

        execution_times = []
        for signal in executed_signals:
            time_diff = signal.executed_at - signal.generated_at
            execution_times.append(time_diff.total_seconds())
        avg_time_to_execution = statistics.mean(execution_times) if execution_times else 0.0

        # Correlation statistics
        strong_correlations = sum(1 for s in self.completed_signals if s.market_movement_correlation > self.correlation_threshold)
        strong_correlation_pct = strong_correlations / total_signals

        # Timing quality
        timing_scores = [s.timing_score for s in self.completed_signals if s.timing_score > 0]
        timing_score = statistics.mean(timing_scores) if timing_scores else 0.0

        # Signal quality metrics
        actionable_signals = sum(1 for s in self.completed_signals if s.first_actionable is not None)
        actionable_signals_pct = actionable_signals / total_signals

        expired_signals = sum(1 for s in self.completed_signals if s.expired_at is not None)
        expired_signals_pct = expired_signals / total_signals

        optimal_timing_signals = sum(1 for s in self.completed_signals if s.timing_score > 0.8)
        optimal_timing_pct = optimal_timing_signals / total_signals

        # Peak relevance hours analysis
        peak_relevance_hours = self._analyze_peak_hours()

        stats = RelevanceStats(
            total_signals=total_signals,
            avg_relevance_duration=avg_relevance_duration,
            median_relevance_duration=median_relevance_duration,
            peak_relevance_hours=peak_relevance_hours,
            avg_time_to_execution=avg_time_to_execution,
            execution_rate=execution_rate,
            strong_correlation_pct=strong_correlation_pct,
            timing_score=timing_score,
            actionable_signals_pct=actionable_signals_pct,
            expired_signals_pct=expired_signals_pct,
            optimal_timing_pct=optimal_timing_pct
        )

        # Cache results
        self.stats_cache = stats
        self.last_stats_update = datetime.now(timezone.utc)

        return stats

    def _analyze_peak_hours(self) -> List[str]:
        """Analyze peak relevance hours"""
        hour_relevance = defaultdict(list)

        for signal in self.completed_signals:
            hour = signal.generated_at.hour
            hour_relevance[hour].append(signal.relevance_score)

        # Calculate average relevance by hour
        hour_avg_relevance = {}
        for hour, scores in hour_relevance.items():
            hour_avg_relevance[hour] = statistics.mean(scores)

        # Find top 3 hours
        top_hours = sorted(hour_avg_relevance.items(), key=lambda x: x[1], reverse=True)[:3]

        return [f"{hour:02d}:00-{hour+1:02d}:00" for hour, _ in top_hours]

    def get_signal_relevance_report(self, signal_id: str) -> Dict[str, Any]:
        """Get detailed relevance report for a specific signal"""

        # Find signal in completed signals
        signal_event = None
        for signal in self.completed_signals:
            if signal.signal_id == signal_id:
                signal_event = signal
                break

        if not signal_event:
            # Check active signals
            signal_event = self.active_signals.get(signal_id)

        if not signal_event:
            return {'error': f'Signal {signal_id} not found'}

        report = {
            'signal_id': signal_id,
            'signal_type': signal_event.signal_type,
            'generated_at': signal_event.generated_at.isoformat(),
            'strike': signal_event.strike,
            'confidence': signal_event.confidence,
            'expected_value': signal_event.expected_value,

            'relevance_metrics': {
                'relevance_score': signal_event.relevance_score,
                'actionable_duration_seconds': signal_event.actionable_duration_seconds,
                'market_movement_correlation': signal_event.market_movement_correlation,
                'timing_score': signal_event.timing_score
            },

            'timing_analysis': {
                'first_actionable': signal_event.first_actionable.isoformat() if signal_event.first_actionable else None,
                'last_actionable': signal_event.last_actionable.isoformat() if signal_event.last_actionable else None,
                'executed_at': signal_event.executed_at.isoformat() if signal_event.executed_at else None,
                'expired_at': signal_event.expired_at.isoformat() if signal_event.expired_at else None
            },

            'market_conditions': signal_event.market_conditions,
            'status': 'completed' if signal_event in self.completed_signals else 'active'
        }

        return report

    def cleanup_old_signals(self, max_age_hours: int = 24):
        """Clean up old completed signals to manage memory"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        # Remove old completed signals
        initial_count = len(self.completed_signals)
        self.completed_signals = [
            signal for signal in self.completed_signals
            if signal.generated_at > cutoff_time
        ]

        removed_count = initial_count - len(self.completed_signals)

        # Remove old active signals that are stale
        stale_signals = [
            signal_id for signal_id, signal in self.active_signals.items()
            if signal.generated_at < cutoff_time
        ]

        for signal_id in stale_signals:
            del self.active_signals[signal_id]

        logger.info(f"Cleaned up {removed_count} old completed signals and {len(stale_signals)} stale active signals")


# Factory function
def create_market_relevance_tracker(config: Dict[str, Any] = None) -> MarketRelevanceTracker:
    """
    Create market relevance tracker with configuration

    Args:
        config: Configuration parameters

    Returns:
        Configured MarketRelevanceTracker instance
    """
    return MarketRelevanceTracker(config)


if __name__ == "__main__":
    # Example usage
    tracker = create_market_relevance_tracker({
        'relevance_window_minutes': 30,
        'correlation_threshold': 0.7
    })

    # Example signal tracking
    signal = {
        'id': 'test_signal_1',
        'signal_type': 'call_buying',
        'strike': 21000,
        'confidence': 0.75,
        'expected_value': 25.0
    }

    market_data = {
        'price': 21050,
        'volume': 15000,
        'volatility': 0.25
    }

    # Start tracking
    signal_id = tracker.track_signal(signal, market_data)

    # Update status
    time.sleep(1)
    tracker.update_signal_status(signal_id, 'actionable', market_data)

    time.sleep(1)
    tracker.update_signal_status(signal_id, 'executed', market_data)

    # Get statistics
    stats = tracker.get_relevance_statistics()
    print(f"Relevance Statistics: {stats}")

    # Get detailed report
    report = tracker.get_signal_relevance_report(signal_id)
    print(f"Signal Report: {report}")
