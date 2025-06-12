#!/usr/bin/env python3
"""
Performance Tracking and Metrics Collection for IFD A/B Testing

This module provides comprehensive performance tracking capabilities for
monitoring and comparing the performance of different algorithm versions
in real-time and historical scenarios.

Features:
- Real-time performance metrics collection
- Signal accuracy measurement over time
- Win rate and false positive tracking
- Processing performance monitoring
- Cost analysis and optimization tracking
- Historical performance trends
"""

import json
import os
import time
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
import statistics
import threading


@dataclass
class SignalPerformance:
    """Individual signal performance tracking"""
    signal_id: str
    timestamp: datetime
    algorithm_version: str

    # Signal Characteristics
    symbol: str
    strike: float
    option_type: str
    confidence: float
    direction: str

    # Prediction Accuracy
    predicted_direction: str
    actual_direction: Optional[str] = None
    prediction_correct: Optional[bool] = None

    # Outcome Tracking
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None

    # Performance Metrics
    signal_accuracy: Optional[float] = None
    processing_time: float = 0.0
    false_positive: bool = False


@dataclass
class TimeWindowMetrics:
    """Performance metrics for a specific time window"""
    window_start: datetime
    window_end: datetime
    window_duration_minutes: int

    # Signal Statistics
    total_signals: int = 0
    accurate_signals: int = 0
    false_positives: int = 0

    # Performance Metrics
    accuracy_rate: float = 0.0
    false_positive_rate: float = 0.0
    average_confidence: float = 0.0

    # Processing Performance
    average_processing_time: float = 0.0
    max_processing_time: float = 0.0
    total_processing_time: float = 0.0

    # Trading Performance
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0

    # Resource Usage
    avg_cpu_usage: float = 0.0
    avg_memory_usage: float = 0.0
    peak_memory_usage: float = 0.0


@dataclass
class AlgorithmPerformance:
    """Comprehensive algorithm performance tracking"""
    algorithm_version: str
    tracking_start: datetime
    last_updated: datetime

    # Overall Statistics
    total_signals_generated: int = 0
    total_signals_validated: int = 0
    total_trades_executed: int = 0

    # Performance Metrics
    overall_accuracy: float = 0.0
    overall_win_rate: float = 0.0
    overall_false_positive_rate: float = 0.0

    # Time-based Performance
    hourly_metrics: List[TimeWindowMetrics] = field(default_factory=list)
    daily_metrics: List[TimeWindowMetrics] = field(default_factory=list)

    # Processing Performance
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0
    processing_time_trend: List[float] = field(default_factory=list)

    # Trading Performance
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0

    # Resource Usage
    peak_memory_usage: float = 0.0
    average_cpu_usage: float = 0.0

    # Cost Tracking
    api_calls_made: int = 0
    total_cost: float = 0.0
    cost_per_signal: float = 0.0


class PerformanceTracker:
    """
    Comprehensive performance tracker for algorithm comparison

    Features:
    - Real-time performance monitoring
    - Historical trend analysis
    - Resource usage tracking
    - Cost analysis
    - Comparative analytics
    """

    def __init__(self, output_dir: str = "outputs/performance_tracking"):
        """
        Initialize performance tracker

        Args:
            output_dir: Directory for saving tracking data
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Performance data storage
        self.algorithm_performance: Dict[str, AlgorithmPerformance] = {}
        self.signal_history: List[SignalPerformance] = []
        self.resource_history: deque = deque(maxlen=1000)  # Last 1000 measurements

        # Real-time tracking
        self.tracking_active = False
        self.tracking_start_time: Optional[datetime] = None

        # Thread safety
        self._lock = threading.Lock()

        # Resource monitoring
        if PSUTIL_AVAILABLE:
            self.process = psutil.Process()
        else:
            self.process = None

    def start_tracking(self, algorithm_versions: List[str]):
        """
        Start performance tracking for specified algorithms

        Args:
            algorithm_versions: List of algorithm versions to track
        """
        with self._lock:
            self.tracking_active = True
            self.tracking_start_time = datetime.now()

            # Initialize algorithm performance tracking
            for version in algorithm_versions:
                if version not in self.algorithm_performance:
                    self.algorithm_performance[version] = AlgorithmPerformance(
                        algorithm_version=version,
                        tracking_start=self.tracking_start_time,
                        last_updated=self.tracking_start_time
                    )

        print(f"📊 Performance tracking started for: {algorithm_versions}")

        # Start resource monitoring thread
        resource_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        resource_thread.start()

    def stop_tracking(self) -> Dict[str, AlgorithmPerformance]:
        """
        Stop performance tracking and return final results

        Returns:
            Final performance data for all algorithms
        """
        with self._lock:
            self.tracking_active = False

            # Update final metrics
            for version, performance in self.algorithm_performance.items():
                performance.last_updated = datetime.now()
                self._update_overall_metrics(performance)

        print("🛑 Performance tracking stopped")

        # Save final results
        self._save_performance_data()

        return self.algorithm_performance.copy()

    def record_signal(self, algorithm_version: str, signal_data: Dict[str, Any],
                     processing_time: float) -> str:
        """
        Record a new signal for performance tracking

        Args:
            algorithm_version: Version of algorithm that generated signal
            signal_data: Signal data dictionary
            processing_time: Time taken to generate signal

        Returns:
            Signal ID for future updates
        """
        signal_id = f"{algorithm_version}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Extract signal information
        symbol = signal_data.get("symbol", "UNKNOWN")
        strike = signal_data.get("strike", 0.0)
        option_type = signal_data.get("option_type", "UNKNOWN")
        confidence = signal_data.get("confidence", 0.0)
        direction = signal_data.get("direction", "UNKNOWN")

        # Create signal performance record
        signal_perf = SignalPerformance(
            signal_id=signal_id,
            timestamp=datetime.now(),
            algorithm_version=algorithm_version,
            symbol=symbol,
            strike=strike,
            option_type=option_type,
            confidence=confidence,
            direction=direction,
            predicted_direction=direction,
            processing_time=processing_time
        )

        with self._lock:
            self.signal_history.append(signal_perf)

            # Update algorithm performance
            if algorithm_version in self.algorithm_performance:
                performance = self.algorithm_performance[algorithm_version]
                performance.total_signals_generated += 1
                performance.total_processing_time += processing_time
                performance.processing_time_trend.append(processing_time)

                # Update average processing time
                performance.average_processing_time = (
                    performance.total_processing_time / performance.total_signals_generated
                )

                performance.last_updated = datetime.now()

        return signal_id

    def update_signal_outcome(self, signal_id: str, actual_direction: str,
                            pnl: Optional[float] = None, trade_data: Optional[Dict[str, Any]] = None):
        """
        Update signal with actual outcome for accuracy tracking

        Args:
            signal_id: ID of signal to update
            actual_direction: Actual market direction
            pnl: Profit/loss if trade was executed
            trade_data: Additional trade information
        """
        with self._lock:
            # Find signal
            signal = None
            for s in self.signal_history:
                if s.signal_id == signal_id:
                    signal = s
                    break

            if not signal:
                print(f"Warning: Signal {signal_id} not found")
                return

            # Update outcome
            signal.actual_direction = actual_direction
            signal.prediction_correct = (signal.predicted_direction == actual_direction)

            if pnl is not None:
                signal.pnl = pnl

            if trade_data:
                signal.entry_time = trade_data.get("entry_time")
                signal.exit_time = trade_data.get("exit_time")
                signal.entry_price = trade_data.get("entry_price")
                signal.exit_price = trade_data.get("exit_price")

            # Check for false positive
            signal.false_positive = not signal.prediction_correct

            # Update algorithm performance
            performance = self.algorithm_performance[signal.algorithm_version]
            performance.total_signals_validated += 1

            if pnl is not None and trade_data:
                performance.total_trades_executed += 1
                performance.total_pnl += pnl

                if pnl > 0:
                    # Winning trade
                    pass  # Will be calculated in metrics update
                elif pnl < 0:
                    # Losing trade
                    pass  # Will be calculated in metrics update

            performance.last_updated = datetime.now()

            # Update overall metrics
            self._update_overall_metrics(performance)

    def _update_overall_metrics(self, performance: AlgorithmPerformance):
        """Update overall performance metrics for an algorithm"""

        # Get validated signals for this algorithm
        validated_signals = [s for s in self.signal_history
                           if s.algorithm_version == performance.algorithm_version
                           and s.prediction_correct is not None]

        if not validated_signals:
            return

        # Calculate accuracy metrics
        correct_predictions = [s for s in validated_signals if s.prediction_correct]
        false_positives = [s for s in validated_signals if s.false_positive]

        performance.overall_accuracy = len(correct_predictions) / len(validated_signals)
        performance.overall_false_positive_rate = len(false_positives) / len(validated_signals)

        # Calculate trading metrics
        trades = [s for s in validated_signals if s.pnl is not None]
        if trades:
            winning_trades = [s for s in trades if s.pnl > 0]
            losing_trades = [s for s in trades if s.pnl < 0]

            performance.overall_win_rate = len(winning_trades) / len(trades)

            # Calculate additional trading metrics
            if losing_trades:
                total_wins = sum(s.pnl for s in winning_trades)
                total_losses = abs(sum(s.pnl for s in losing_trades))

                if total_losses > 0:
                    performance.profit_factor = total_wins / total_losses

                # Calculate max drawdown (simplified)
                running_pnl = 0
                peak_pnl = 0
                max_drawdown = 0

                for trade in sorted(trades, key=lambda x: x.timestamp):
                    running_pnl += trade.pnl
                    peak_pnl = max(peak_pnl, running_pnl)
                    drawdown = peak_pnl - running_pnl
                    max_drawdown = max(max_drawdown, drawdown)

                performance.max_drawdown = max_drawdown

    def _monitor_resources(self):
        """Monitor system resource usage in background thread"""

        while self.tracking_active:
            try:
                if PSUTIL_AVAILABLE and self.process:
                    # Get current resource usage
                    cpu_percent = self.process.cpu_percent()
                    memory_info = self.process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024

                    resource_data = {
                        "timestamp": datetime.now(),
                        "cpu_percent": cpu_percent,
                        "memory_mb": memory_mb
                    }

                    self.resource_history.append(resource_data)

                    # Update algorithm performance with resource usage
                    with self._lock:
                        for performance in self.algorithm_performance.values():
                            performance.peak_memory_usage = max(performance.peak_memory_usage, memory_mb)

                            # Calculate average CPU usage (simplified)
                            if len(self.resource_history) > 0:
                                recent_cpu = [r["cpu_percent"] for r in list(self.resource_history)[-10:]]
                                performance.average_cpu_usage = statistics.mean(recent_cpu)
                else:
                    # Without psutil, just sleep and continue
                    pass

                time.sleep(5)  # Monitor every 5 seconds

            except Exception as e:
                print(f"Resource monitoring error: {e}")
                time.sleep(10)

    def get_performance_summary(self, algorithm_version: str) -> Dict[str, Any]:
        """
        Get performance summary for specific algorithm

        Args:
            algorithm_version: Algorithm version to summarize

        Returns:
            Performance summary dictionary
        """
        if algorithm_version not in self.algorithm_performance:
            return {"error": f"Algorithm {algorithm_version} not tracked"}

        performance = self.algorithm_performance[algorithm_version]

        # Get recent signals (last hour)
        recent_cutoff = datetime.now() - timedelta(hours=1)
        recent_signals = [s for s in self.signal_history
                         if s.algorithm_version == algorithm_version
                         and s.timestamp >= recent_cutoff]

        return {
            "algorithm_version": algorithm_version,
            "tracking_duration_hours": (performance.last_updated - performance.tracking_start).total_seconds() / 3600,
            "total_signals": performance.total_signals_generated,
            "validated_signals": performance.total_signals_validated,
            "recent_signals_1h": len(recent_signals),
            "overall_accuracy": performance.overall_accuracy,
            "overall_win_rate": performance.overall_win_rate,
            "false_positive_rate": performance.overall_false_positive_rate,
            "average_processing_time": performance.average_processing_time,
            "total_pnl": performance.total_pnl,
            "max_drawdown": performance.max_drawdown,
            "sharpe_ratio": performance.sharpe_ratio,
            "profit_factor": performance.profit_factor,
            "peak_memory_mb": performance.peak_memory_usage,
            "average_cpu_percent": performance.average_cpu_usage,
            "total_cost": performance.total_cost,
            "cost_per_signal": performance.cost_per_signal
        }

    def compare_algorithms(self, version1: str, version2: str) -> Dict[str, Any]:
        """
        Compare performance between two algorithms

        Args:
            version1: First algorithm version
            version2: Second algorithm version

        Returns:
            Comparison analysis
        """
        if version1 not in self.algorithm_performance or version2 not in self.algorithm_performance:
            return {"error": "One or both algorithms not tracked"}

        perf1 = self.algorithm_performance[version1]
        perf2 = self.algorithm_performance[version2]

        comparison = {
            "algorithm_1": version1,
            "algorithm_2": version2,
            "comparison_metrics": {
                "signals_generated": {
                    version1: perf1.total_signals_generated,
                    version2: perf2.total_signals_generated,
                    "winner": version1 if perf1.total_signals_generated > perf2.total_signals_generated else version2
                },
                "accuracy": {
                    version1: perf1.overall_accuracy,
                    version2: perf2.overall_accuracy,
                    "winner": version1 if perf1.overall_accuracy > perf2.overall_accuracy else version2
                },
                "processing_speed": {
                    version1: perf1.average_processing_time,
                    version2: perf2.average_processing_time,
                    "winner": version1 if perf1.average_processing_time < perf2.average_processing_time else version2
                },
                "profitability": {
                    version1: perf1.total_pnl,
                    version2: perf2.total_pnl,
                    "winner": version1 if perf1.total_pnl > perf2.total_pnl else version2
                }
            }
        }

        # Determine overall winner
        wins1 = sum(1 for metric in comparison["comparison_metrics"].values()
                   if metric["winner"] == version1)
        wins2 = sum(1 for metric in comparison["comparison_metrics"].values()
                   if metric["winner"] == version2)

        if wins1 > wins2:
            comparison["overall_winner"] = version1
        elif wins2 > wins1:
            comparison["overall_winner"] = version2
        else:
            comparison["overall_winner"] = "tie"

        return comparison

    def generate_hourly_report(self, algorithm_version: str) -> List[TimeWindowMetrics]:
        """Generate hourly performance report for algorithm"""

        if algorithm_version not in self.algorithm_performance:
            return []

        # Get signals for this algorithm
        signals = [s for s in self.signal_history if s.algorithm_version == algorithm_version]

        if not signals:
            return []

        # Group signals by hour
        hourly_groups = defaultdict(list)
        for signal in signals:
            hour_key = signal.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_groups[hour_key].append(signal)

        # Generate metrics for each hour
        hourly_metrics = []
        for hour, hour_signals in sorted(hourly_groups.items()):

            # Calculate metrics for this hour
            validated_signals = [s for s in hour_signals if s.prediction_correct is not None]
            correct_signals = [s for s in validated_signals if s.prediction_correct]
            false_positives = [s for s in validated_signals if s.false_positive]
            trades = [s for s in hour_signals if s.pnl is not None]
            winning_trades = [s for s in trades if s.pnl > 0]

            metrics = TimeWindowMetrics(
                window_start=hour,
                window_end=hour + timedelta(hours=1),
                window_duration_minutes=60,
                total_signals=len(hour_signals),
                accurate_signals=len(correct_signals),
                false_positives=len(false_positives),
                accuracy_rate=len(correct_signals) / len(validated_signals) if validated_signals else 0,
                false_positive_rate=len(false_positives) / len(validated_signals) if validated_signals else 0,
                average_confidence=statistics.mean([s.confidence for s in hour_signals]) if hour_signals else 0,
                average_processing_time=statistics.mean([s.processing_time for s in hour_signals]) if hour_signals else 0,
                max_processing_time=max([s.processing_time for s in hour_signals]) if hour_signals else 0,
                total_processing_time=sum([s.processing_time for s in hour_signals]),
                total_trades=len(trades),
                winning_trades=len(winning_trades),
                losing_trades=len(trades) - len(winning_trades),
                total_pnl=sum([s.pnl for s in trades if s.pnl]) if trades else 0,
                win_rate=len(winning_trades) / len(trades) if trades else 0
            )

            hourly_metrics.append(metrics)

        return hourly_metrics

    def _save_performance_data(self):
        """Save performance data to files"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save algorithm performance
        performance_file = os.path.join(self.output_dir, f"algorithm_performance_{timestamp}.json")
        performance_data = {version: asdict(perf) for version, perf in self.algorithm_performance.items()}

        with open(performance_file, 'w') as f:
            json.dump(performance_data, f, indent=2, default=str)

        # Save signal history
        signals_file = os.path.join(self.output_dir, f"signal_history_{timestamp}.json")
        signals_data = [asdict(signal) for signal in self.signal_history]

        with open(signals_file, 'w') as f:
            json.dump(signals_data, f, indent=2, default=str)

        print(f"💾 Performance data saved:")
        print(f"   Performance: {performance_file}")
        print(f"   Signals: {signals_file}")


# Module-level convenience functions
def create_performance_tracker() -> PerformanceTracker:
    """Create performance tracker instance"""
    return PerformanceTracker()


def track_algorithm_performance(algorithm_versions: List[str], duration_hours: float = 1.0) -> Dict[str, Any]:
    """
    Track algorithm performance for specified duration

    Args:
        algorithm_versions: Algorithms to track
        duration_hours: Tracking duration in hours

    Returns:
        Performance results
    """
    tracker = create_performance_tracker()

    # Start tracking
    tracker.start_tracking(algorithm_versions)

    print(f"Tracking performance for {duration_hours} hours...")

    # Wait for specified duration
    import time
    time.sleep(duration_hours * 3600)

    # Stop tracking and get results
    results = tracker.stop_tracking()

    return results


if __name__ == "__main__":
    # Example usage
    tracker = create_performance_tracker()

    # Start tracking
    tracker.start_tracking(["v1.0", "v3.0"])

    # Simulate some signals
    import time

    for i in range(5):
        # Simulate v1.0 signal
        signal_id_v1 = tracker.record_signal(
            "v1.0",
            {
                "symbol": "NQM25",
                "strike": 21350 + i * 25,
                "option_type": "CALL",
                "confidence": 0.7 + i * 0.05,
                "direction": "LONG"
            },
            processing_time=0.1 + i * 0.01
        )

        # Simulate v3.0 signal
        signal_id_v3 = tracker.record_signal(
            "v3.0",
            {
                "symbol": "NQM25",
                "strike": 21350 + i * 25,
                "option_type": "CALL",
                "confidence": 0.8 + i * 0.03,
                "direction": "LONG"
            },
            processing_time=0.15 + i * 0.01
        )

        time.sleep(1)

        # Update outcomes (simulate)
        tracker.update_signal_outcome(signal_id_v1, "LONG", pnl=10.0 + i * 5)
        tracker.update_signal_outcome(signal_id_v3, "LONG", pnl=15.0 + i * 3)

    time.sleep(2)

    # Get performance summaries
    v1_summary = tracker.get_performance_summary("v1.0")
    v3_summary = tracker.get_performance_summary("v3.0")

    print(f"v1.0 Performance: {v1_summary}")
    print(f"v3.0 Performance: {v3_summary}")

    # Compare algorithms
    comparison = tracker.compare_algorithms("v1.0", "v3.0")
    print(f"Comparison: {comparison}")

    # Stop tracking
    final_results = tracker.stop_tracking()
    print(f"Final results: {list(final_results.keys())}")
