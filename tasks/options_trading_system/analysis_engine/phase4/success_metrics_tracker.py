#!/usr/bin/env python3
"""
Success Metrics Tracker for IFD v3.0

This module tracks the specific success metrics outlined in the Phase 4 requirements:
- Accuracy improvement: >75% (vs 65% for v1.0)
- Cost per signal: <$5 target
- ROI improvement: >25% vs current v1.0 system
- Win/loss ratio: >1.8 (vs 1.5 for v1.0)
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlgorithmVersion(Enum):
    """Algorithm versions for comparison"""
    V1_0 = "v1.0"
    V3_0 = "v3.0"


@dataclass
class SignalMetrics:
    """Performance metrics for a single signal"""
    signal_id: str
    timestamp: datetime
    algorithm_version: AlgorithmVersion

    # Signal details
    strike: float
    signal_type: str  # "institutional_flow", "volatility_crush", etc.
    confidence: float

    # Execution
    executed: bool = False
    execution_price: Optional[float] = None
    execution_time: Optional[datetime] = None

    # Outcome tracking
    correct_prediction: Optional[bool] = None  # True/False/None (pending)
    outcome_measured_at: Optional[datetime] = None

    # Financial metrics
    entry_cost: float = 0.0
    data_cost: float = 0.0  # Cost of data used for this signal
    execution_cost: float = 0.0  # Trading fees
    total_cost: float = 0.0

    # Results
    pnl: Optional[float] = None
    roi: Optional[float] = None  # Return on investment

    # Risk metrics
    max_drawdown: Optional[float] = None
    time_to_outcome: Optional[float] = None  # Hours to resolution


@dataclass
class PerformanceSnapshot:
    """Performance snapshot for a time period"""
    period_start: datetime
    period_end: datetime
    algorithm_version: AlgorithmVersion

    # Accuracy metrics
    total_signals: int = 0
    correct_predictions: int = 0
    accuracy_rate: float = 0.0
    false_positive_rate: float = 0.0

    # Financial metrics
    total_cost: float = 0.0
    total_pnl: float = 0.0
    avg_cost_per_signal: float = 0.0
    roi: float = 0.0

    # Win/Loss metrics
    winning_trades: int = 0
    losing_trades: int = 0
    win_loss_ratio: float = 0.0

    # Efficiency metrics
    avg_time_to_outcome: float = 0.0  # Hours
    signal_frequency: float = 0.0  # Signals per day

    # Targets achieved
    meets_accuracy_target: bool = False  # >75%
    meets_cost_target: bool = False  # <$5 per signal
    meets_roi_target: bool = False  # >25% vs v1.0


@dataclass
class ComparisonMetrics:
    """Comparison between v1.0 and v3.0 performance"""
    comparison_date: datetime
    period_days: int

    # v1.0 metrics
    v1_accuracy: float
    v1_cost_per_signal: float
    v1_roi: float
    v1_win_loss_ratio: float

    # v3.0 metrics
    v3_accuracy: float
    v3_cost_per_signal: float
    v3_roi: float
    v3_win_loss_ratio: float

    # Improvement calculations
    accuracy_improvement: float  # Percentage points
    cost_improvement: float  # Percentage change
    roi_improvement: float  # Percentage change
    win_loss_improvement: float  # Ratio change

    # Target achievement
    accuracy_target_met: bool  # >75%
    cost_target_met: bool  # <$5
    roi_target_met: bool  # >25% improvement
    win_loss_target_met: bool  # >1.8


class MetricsDatabase:
    """Database for storing performance metrics"""

    def __init__(self, db_path: str = "outputs/performance_metrics.db"):
        """Initialize metrics database"""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Signal metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signal_metrics (
                    signal_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    algorithm_version TEXT NOT NULL,
                    strike REAL NOT NULL,
                    signal_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    executed BOOLEAN DEFAULT 0,
                    execution_price REAL,
                    execution_time TEXT,
                    correct_prediction BOOLEAN,
                    outcome_measured_at TEXT,
                    entry_cost REAL DEFAULT 0.0,
                    data_cost REAL DEFAULT 0.0,
                    execution_cost REAL DEFAULT 0.0,
                    total_cost REAL DEFAULT 0.0,
                    pnl REAL,
                    roi REAL,
                    max_drawdown REAL,
                    time_to_outcome REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Performance snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    algorithm_version TEXT NOT NULL,
                    total_signals INTEGER DEFAULT 0,
                    correct_predictions INTEGER DEFAULT 0,
                    accuracy_rate REAL DEFAULT 0.0,
                    false_positive_rate REAL DEFAULT 0.0,
                    total_cost REAL DEFAULT 0.0,
                    total_pnl REAL DEFAULT 0.0,
                    avg_cost_per_signal REAL DEFAULT 0.0,
                    roi REAL DEFAULT 0.0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    win_loss_ratio REAL DEFAULT 0.0,
                    avg_time_to_outcome REAL DEFAULT 0.0,
                    signal_frequency REAL DEFAULT 0.0,
                    meets_accuracy_target BOOLEAN DEFAULT 0,
                    meets_cost_target BOOLEAN DEFAULT 0,
                    meets_roi_target BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Comparison metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comparison_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comparison_date TEXT NOT NULL,
                    period_days INTEGER NOT NULL,
                    v1_accuracy REAL,
                    v1_cost_per_signal REAL,
                    v1_roi REAL,
                    v1_win_loss_ratio REAL,
                    v3_accuracy REAL,
                    v3_cost_per_signal REAL,
                    v3_roi REAL,
                    v3_win_loss_ratio REAL,
                    accuracy_improvement REAL,
                    cost_improvement REAL,
                    roi_improvement REAL,
                    win_loss_improvement REAL,
                    accuracy_target_met BOOLEAN DEFAULT 0,
                    cost_target_met BOOLEAN DEFAULT 0,
                    roi_target_met BOOLEAN DEFAULT 0,
                    win_loss_target_met BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_timestamp ON signal_metrics(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_version ON signal_metrics(algorithm_version)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_period ON performance_snapshots(period_start, period_end)")

            conn.commit()

    def store_signal_metrics(self, metrics: SignalMetrics):
        """Store signal performance metrics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO signal_metrics
                (signal_id, timestamp, algorithm_version, strike, signal_type, confidence,
                 executed, execution_price, execution_time, correct_prediction, outcome_measured_at,
                 entry_cost, data_cost, execution_cost, total_cost, pnl, roi,
                 max_drawdown, time_to_outcome)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.signal_id,
                metrics.timestamp.isoformat(),
                metrics.algorithm_version.value,
                metrics.strike,
                metrics.signal_type,
                metrics.confidence,
                metrics.executed,
                metrics.execution_price,
                metrics.execution_time.isoformat() if metrics.execution_time else None,
                metrics.correct_prediction,
                metrics.outcome_measured_at.isoformat() if metrics.outcome_measured_at else None,
                metrics.entry_cost,
                metrics.data_cost,
                metrics.execution_cost,
                metrics.total_cost,
                metrics.pnl,
                metrics.roi,
                metrics.max_drawdown,
                metrics.time_to_outcome
            ))

            conn.commit()

    def get_signals(self, start_date: datetime, end_date: datetime,
                   algorithm_version: Optional[AlgorithmVersion] = None) -> List[SignalMetrics]:
        """Get signals for a time period"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            query = """
                SELECT * FROM signal_metrics
                WHERE timestamp >= ? AND timestamp <= ?
            """
            params = [start_date.isoformat(), end_date.isoformat()]

            if algorithm_version:
                query += " AND algorithm_version = ?"
                params.append(algorithm_version.value)

            query += " ORDER BY timestamp"

            cursor.execute(query, params)

            signals = []
            for row in cursor.fetchall():
                columns = [desc[0] for desc in cursor.description]
                data = dict(zip(columns, row))

                # Convert timestamps
                data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                if data['execution_time']:
                    data['execution_time'] = datetime.fromisoformat(data['execution_time'])
                if data['outcome_measured_at']:
                    data['outcome_measured_at'] = datetime.fromisoformat(data['outcome_measured_at'])

                # Convert algorithm version
                data['algorithm_version'] = AlgorithmVersion(data['algorithm_version'])

                # Remove non-field columns
                data.pop('created_at', None)

                signals.append(SignalMetrics(**data))

            return signals


class SuccessMetricsTracker:
    """
    Main success metrics tracking system

    Features:
    - Real-time signal tracking
    - Performance comparison with v1.0
    - Target achievement monitoring
    - ROI and cost analysis
    """

    def __init__(self, db_path: str = "outputs/performance_metrics.db"):
        """Initialize success metrics tracker"""
        self.database = MetricsDatabase(db_path)

        # Performance targets from requirements
        self.targets = {
            'accuracy_target': 0.75,  # >75%
            'accuracy_baseline_v1': 0.65,  # v1.0 baseline
            'cost_per_signal_target': 5.0,  # <$5
            'roi_improvement_target': 0.25,  # >25% vs v1.0
            'win_loss_target': 1.8,  # >1.8
            'win_loss_baseline_v1': 1.5  # v1.0 baseline
        }

        # Current tracking
        self.active_signals: Dict[str, SignalMetrics] = {}

        logger.info("Success metrics tracker initialized with performance targets")

    def track_signal(self, signal_id: str, strike: float, signal_type: str,
                    confidence: float, algorithm_version: AlgorithmVersion,
                    data_cost: float = 0.0) -> SignalMetrics:
        """
        Start tracking a new signal

        Args:
            signal_id: Unique signal identifier
            strike: Strike price
            signal_type: Type of signal detected
            confidence: Signal confidence level
            algorithm_version: Algorithm version
            data_cost: Cost of data used for this signal

        Returns:
            SignalMetrics object
        """
        metrics = SignalMetrics(
            signal_id=signal_id,
            timestamp=datetime.now(timezone.utc),
            algorithm_version=algorithm_version,
            strike=strike,
            signal_type=signal_type,
            confidence=confidence,
            data_cost=data_cost,
            total_cost=data_cost
        )

        self.active_signals[signal_id] = metrics
        self.database.store_signal_metrics(metrics)

        logger.info(f"Tracking new {algorithm_version.value} signal: {signal_id}")
        return metrics

    def update_signal_execution(self, signal_id: str, executed: bool,
                              execution_price: float = None,
                              execution_cost: float = 0.0,
                              entry_cost: float = 0.0):
        """Update signal execution details"""
        if signal_id not in self.active_signals:
            logger.warning(f"Signal {signal_id} not found in active tracking")
            return

        metrics = self.active_signals[signal_id]
        metrics.executed = executed
        metrics.execution_price = execution_price
        metrics.execution_time = datetime.now(timezone.utc)
        metrics.execution_cost = execution_cost
        metrics.entry_cost = entry_cost
        metrics.total_cost = metrics.data_cost + execution_cost + entry_cost

        self.database.store_signal_metrics(metrics)
        logger.info(f"Updated execution for signal {signal_id}: executed={executed}")

    def update_signal_outcome(self, signal_id: str, correct_prediction: bool,
                            pnl: float = None, max_drawdown: float = None):
        """Update signal outcome and calculate metrics"""
        if signal_id not in self.active_signals:
            logger.warning(f"Signal {signal_id} not found in active tracking")
            return

        metrics = self.active_signals[signal_id]
        metrics.correct_prediction = correct_prediction
        metrics.outcome_measured_at = datetime.now(timezone.utc)
        metrics.pnl = pnl
        metrics.max_drawdown = max_drawdown

        # Calculate time to outcome
        if metrics.execution_time:
            time_diff = metrics.outcome_measured_at - metrics.execution_time
            metrics.time_to_outcome = time_diff.total_seconds() / 3600  # Hours

        # Calculate ROI
        if pnl is not None and metrics.total_cost > 0:
            metrics.roi = pnl / metrics.total_cost

        self.database.store_signal_metrics(metrics)

        # Remove from active tracking
        del self.active_signals[signal_id]

        logger.info(f"Signal {signal_id} outcome: correct={correct_prediction}, "
                   f"PnL=${pnl:.2f}, ROI={metrics.roi:.1%}")

    def calculate_performance_snapshot(self, start_date: datetime, end_date: datetime,
                                     algorithm_version: AlgorithmVersion) -> PerformanceSnapshot:
        """Calculate performance snapshot for a period"""
        signals = self.database.get_signals(start_date, end_date, algorithm_version)

        if not signals:
            return PerformanceSnapshot(
                period_start=start_date,
                period_end=end_date,
                algorithm_version=algorithm_version
            )

        # Filter completed signals (with outcomes)
        completed_signals = [s for s in signals if s.correct_prediction is not None]
        executed_signals = [s for s in completed_signals if s.executed]

        # Accuracy metrics
        total_signals = len(completed_signals)
        correct_predictions = sum(1 for s in completed_signals if s.correct_prediction)
        accuracy_rate = correct_predictions / total_signals if total_signals > 0 else 0
        false_positive_rate = 1 - accuracy_rate

        # Financial metrics
        total_cost = sum(s.total_cost for s in signals)
        total_pnl = sum(s.pnl for s in executed_signals if s.pnl is not None)
        avg_cost_per_signal = total_cost / len(signals) if signals else 0
        roi = total_pnl / total_cost if total_cost > 0 else 0

        # Win/Loss metrics
        profitable_trades = [s for s in executed_signals if s.pnl and s.pnl > 0]
        losing_trades = [s for s in executed_signals if s.pnl and s.pnl <= 0]
        winning_trades = len(profitable_trades)
        losing_count = len(losing_trades)
        win_loss_ratio = winning_trades / losing_count if losing_count > 0 else float('inf')

        # Efficiency metrics
        outcome_times = [s.time_to_outcome for s in completed_signals if s.time_to_outcome]
        avg_time_to_outcome = np.mean(outcome_times) if outcome_times else 0

        period_days = (end_date - start_date).days
        signal_frequency = len(signals) / period_days if period_days > 0 else 0

        # Target achievement
        meets_accuracy_target = accuracy_rate >= self.targets['accuracy_target']
        meets_cost_target = avg_cost_per_signal <= self.targets['cost_per_signal_target']
        meets_roi_target = False  # Need comparison with v1.0

        snapshot = PerformanceSnapshot(
            period_start=start_date,
            period_end=end_date,
            algorithm_version=algorithm_version,
            total_signals=total_signals,
            correct_predictions=correct_predictions,
            accuracy_rate=accuracy_rate,
            false_positive_rate=false_positive_rate,
            total_cost=total_cost,
            total_pnl=total_pnl,
            avg_cost_per_signal=avg_cost_per_signal,
            roi=roi,
            winning_trades=winning_trades,
            losing_trades=losing_count,
            win_loss_ratio=win_loss_ratio,
            avg_time_to_outcome=avg_time_to_outcome,
            signal_frequency=signal_frequency,
            meets_accuracy_target=meets_accuracy_target,
            meets_cost_target=meets_cost_target,
            meets_roi_target=meets_roi_target
        )

        return snapshot

    def compare_versions(self, start_date: datetime, end_date: datetime) -> ComparisonMetrics:
        """Compare v1.0 vs v3.0 performance"""
        v1_snapshot = self.calculate_performance_snapshot(start_date, end_date, AlgorithmVersion.V1_0)
        v3_snapshot = self.calculate_performance_snapshot(start_date, end_date, AlgorithmVersion.V3_0)

        # Calculate improvements
        accuracy_improvement = v3_snapshot.accuracy_rate - v1_snapshot.accuracy_rate

        cost_improvement = 0.0
        if v1_snapshot.avg_cost_per_signal > 0:
            cost_improvement = (v1_snapshot.avg_cost_per_signal - v3_snapshot.avg_cost_per_signal) / v1_snapshot.avg_cost_per_signal

        roi_improvement = 0.0
        if v1_snapshot.roi > 0:
            roi_improvement = (v3_snapshot.roi - v1_snapshot.roi) / v1_snapshot.roi

        win_loss_improvement = v3_snapshot.win_loss_ratio - v1_snapshot.win_loss_ratio

        # Target achievement
        accuracy_target_met = v3_snapshot.accuracy_rate >= self.targets['accuracy_target']
        cost_target_met = v3_snapshot.avg_cost_per_signal <= self.targets['cost_per_signal_target']
        roi_target_met = roi_improvement >= self.targets['roi_improvement_target']
        win_loss_target_met = v3_snapshot.win_loss_ratio >= self.targets['win_loss_target']

        comparison = ComparisonMetrics(
            comparison_date=datetime.now(timezone.utc),
            period_days=(end_date - start_date).days,
            v1_accuracy=v1_snapshot.accuracy_rate,
            v1_cost_per_signal=v1_snapshot.avg_cost_per_signal,
            v1_roi=v1_snapshot.roi,
            v1_win_loss_ratio=v1_snapshot.win_loss_ratio,
            v3_accuracy=v3_snapshot.accuracy_rate,
            v3_cost_per_signal=v3_snapshot.avg_cost_per_signal,
            v3_roi=v3_snapshot.roi,
            v3_win_loss_ratio=v3_snapshot.win_loss_ratio,
            accuracy_improvement=accuracy_improvement,
            cost_improvement=cost_improvement,
            roi_improvement=roi_improvement,
            win_loss_improvement=win_loss_improvement,
            accuracy_target_met=accuracy_target_met,
            cost_target_met=cost_target_met,
            roi_target_met=roi_target_met,
            win_loss_target_met=win_loss_target_met
        )

        return comparison

    def get_success_metrics_report(self, days_back: int = 30) -> Dict[str, Any]:
        """Generate comprehensive success metrics report"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)

        # Get comparison
        comparison = self.compare_versions(start_date, end_date)

        # Overall targets status
        targets_met = {
            'accuracy_target': comparison.accuracy_target_met,
            'cost_target': comparison.cost_target_met,
            'roi_target': comparison.roi_target_met,
            'win_loss_target': comparison.win_loss_target_met
        }

        overall_success = all(targets_met.values())

        report = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days_back
            },
            'v3_performance': {
                'accuracy': comparison.v3_accuracy,
                'cost_per_signal': comparison.v3_cost_per_signal,
                'roi': comparison.v3_roi,
                'win_loss_ratio': comparison.v3_win_loss_ratio
            },
            'improvements': {
                'accuracy_improvement': comparison.accuracy_improvement,
                'cost_improvement': comparison.cost_improvement,
                'roi_improvement': comparison.roi_improvement,
                'win_loss_improvement': comparison.win_loss_improvement
            },
            'target_achievement': targets_met,
            'overall_success': overall_success,
            'targets': self.targets,
            'recommendations': self._generate_recommendations(comparison)
        }

        return report

    def _generate_recommendations(self, comparison: ComparisonMetrics) -> List[str]:
        """Generate recommendations based on performance"""
        recommendations = []

        if not comparison.accuracy_target_met:
            recommendations.append(
                f"Accuracy ({comparison.v3_accuracy:.1%}) below 75% target. "
                "Consider tuning detection thresholds or improving signal quality."
            )

        if not comparison.cost_target_met:
            recommendations.append(
                f"Cost per signal (${comparison.v3_cost_per_signal:.2f}) above $5 target. "
                "Optimize data usage and implement more aggressive caching."
            )

        if not comparison.roi_target_met:
            recommendations.append(
                f"ROI improvement ({comparison.roi_improvement:.1%}) below 25% target. "
                "Focus on reducing false positives and improving signal precision."
            )

        if not comparison.win_loss_target_met:
            recommendations.append(
                f"Win/loss ratio ({comparison.v3_win_loss_ratio:.2f}) below 1.8 target. "
                "Review risk management and position sizing strategies."
            )

        if not recommendations:
            recommendations.append("All targets achieved! System performing optimally.")

        return recommendations


def create_success_metrics_tracker() -> SuccessMetricsTracker:
    """Factory function to create success metrics tracker"""
    return SuccessMetricsTracker()


if __name__ == "__main__":
    # Example usage
    tracker = create_success_metrics_tracker()

    # Simulate tracking signals
    print("Simulating signal tracking...")

    # Track v3.0 signals
    for i in range(10):
        signal_id = f"v3_signal_{i}"
        metrics = tracker.track_signal(
            signal_id=signal_id,
            strike=21000 + i * 100,
            signal_type="institutional_flow",
            confidence=0.8 + (i % 3) * 0.05,
            algorithm_version=AlgorithmVersion.V3_0,
            data_cost=2.50
        )

        # Simulate execution
        tracker.update_signal_execution(
            signal_id=signal_id,
            executed=True,
            execution_price=100.0 + i,
            execution_cost=0.50,
            entry_cost=1.00
        )

        # Simulate outcome (80% accuracy)
        correct = i < 8
        pnl = 50.0 if correct else -20.0

        tracker.update_signal_outcome(
            signal_id=signal_id,
            correct_prediction=correct,
            pnl=pnl
        )

    # Track some v1.0 signals for comparison
    for i in range(10):
        signal_id = f"v1_signal_{i}"
        metrics = tracker.track_signal(
            signal_id=signal_id,
            strike=21000 + i * 100,
            signal_type="institutional_flow",
            confidence=0.7 + (i % 3) * 0.03,
            algorithm_version=AlgorithmVersion.V1_0,
            data_cost=1.00  # Lower data cost but worse performance
        )

        tracker.update_signal_execution(
            signal_id=signal_id,
            executed=True,
            execution_price=100.0 + i,
            execution_cost=0.50,
            entry_cost=1.00
        )

        # Simulate v1.0 outcome (65% accuracy)
        correct = i < 6.5
        pnl = 40.0 if correct else -25.0  # Lower wins, higher losses

        tracker.update_signal_outcome(
            signal_id=signal_id,
            correct_prediction=correct,
            pnl=pnl
        )

    # Generate report
    report = tracker.get_success_metrics_report(days_back=30)

    print("\n📊 SUCCESS METRICS REPORT")
    print("=" * 60)
    print(f"Period: {report['period']['days']} days")
    print(f"\nv3.0 Performance:")
    print(f"  Accuracy: {report['v3_performance']['accuracy']:.1%}")
    print(f"  Cost/Signal: ${report['v3_performance']['cost_per_signal']:.2f}")
    print(f"  ROI: {report['v3_performance']['roi']:.1%}")
    print(f"  Win/Loss: {report['v3_performance']['win_loss_ratio']:.2f}")

    print(f"\nTarget Achievement:")
    for target, achieved in report['target_achievement'].items():
        status = "✓" if achieved else "✗"
        print(f"  {status} {target}: {achieved}")

    print(f"\nOverall Success: {'✓ PASS' if report['overall_success'] else '✗ FAIL'}")

    print(f"\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  - {rec}")
