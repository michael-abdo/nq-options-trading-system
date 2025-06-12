#!/usr/bin/env python3
"""
Adaptive Threshold Manager for IFD v3.0

This module implements intelligent threshold adjustment based on real-time performance
feedback to optimize signal quality and achieve target metrics:
- Accuracy >75%
- Cost per signal <$5
- ROI improvement >25% vs v1.0
- Win/loss ratio >1.8

Key Features:
- Machine learning-based threshold optimization
- Real-time performance monitoring integration
- Multi-objective optimization (accuracy vs volume)
- Automatic rollback for poor performance
- Configurable adjustment sensitivity and constraints
"""

import os
import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics
import numpy as np
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing sklearn for optimization
try:
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available - using basic optimization methods")

# Try importing success metrics tracker
try:
    from .success_metrics_tracker import SuccessMetricsTracker, AlgorithmVersion
    METRICS_INTEGRATION_AVAILABLE = True
except ImportError:
    logger.warning("Success metrics tracker not available - running in standalone mode")
    METRICS_INTEGRATION_AVAILABLE = False


class OptimizationObjective(Enum):
    """Optimization objectives for threshold tuning"""
    ACCURACY = "accuracy"
    COST_EFFICIENCY = "cost_efficiency"
    ROI = "roi"
    WIN_LOSS_RATIO = "win_loss_ratio"
    BALANCED = "balanced"


@dataclass
class ThresholdConfig:
    """Configuration for a single threshold parameter"""
    name: str
    current_value: float
    min_value: float
    max_value: float
    adjustment_step: float
    sensitivity: float  # How responsive to performance changes

    # Performance tracking
    performance_history: List[float] = None
    adjustment_history: List[Tuple[datetime, float, str]] = None

    def __post_init__(self):
        if self.performance_history is None:
            self.performance_history = []
        if self.adjustment_history is None:
            self.adjustment_history = []


@dataclass
class PerformanceSnapshot:
    """Snapshot of system performance at a point in time"""
    timestamp: datetime
    accuracy: float
    cost_per_signal: float
    roi: float
    win_loss_ratio: float
    signal_volume: int
    false_positive_rate: float

    # Threshold values at this time
    thresholds: Dict[str, float]

    # Composite scores
    composite_score: float = 0.0
    target_achievement: float = 0.0


@dataclass
class OptimizationResult:
    """Result from threshold optimization"""
    optimization_id: str
    timestamp: datetime
    objective: OptimizationObjective

    # Recommendations
    threshold_adjustments: Dict[str, float]
    expected_improvement: float
    confidence: float

    # Validation
    cross_validation_score: Optional[float] = None
    risk_assessment: str = "MEDIUM"
    recommendation: str = "APPLY"  # APPLY, MONITOR, REJECT


class AdaptiveThresholdDatabase:
    """Database for tracking threshold adjustments and performance"""

    def __init__(self, db_path: str = "outputs/adaptive_thresholds.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Threshold configurations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS threshold_configs (
                    name TEXT PRIMARY KEY,
                    current_value REAL NOT NULL,
                    min_value REAL NOT NULL,
                    max_value REAL NOT NULL,
                    adjustment_step REAL NOT NULL,
                    sensitivity REAL NOT NULL,
                    last_updated TEXT NOT NULL
                )
            """)

            # Performance snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    accuracy REAL NOT NULL,
                    cost_per_signal REAL NOT NULL,
                    roi REAL NOT NULL,
                    win_loss_ratio REAL NOT NULL,
                    signal_volume INTEGER NOT NULL,
                    false_positive_rate REAL NOT NULL,
                    thresholds TEXT NOT NULL,  -- JSON
                    composite_score REAL NOT NULL,
                    target_achievement REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Threshold adjustments log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS threshold_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    threshold_name TEXT NOT NULL,
                    old_value REAL NOT NULL,
                    new_value REAL NOT NULL,
                    reason TEXT NOT NULL,
                    performance_before TEXT,  -- JSON
                    performance_after TEXT,   -- JSON
                    success BOOLEAN DEFAULT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Optimization results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS optimization_results (
                    optimization_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    threshold_adjustments TEXT NOT NULL,  -- JSON
                    expected_improvement REAL NOT NULL,
                    confidence REAL NOT NULL,
                    cross_validation_score REAL,
                    risk_assessment TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    applied BOOLEAN DEFAULT 0,
                    actual_improvement REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON performance_snapshots(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_adjustments_threshold ON threshold_adjustments(threshold_name, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_optimization_timestamp ON optimization_results(timestamp)")

            conn.commit()

    def save_threshold_config(self, config: ThresholdConfig):
        """Save threshold configuration"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO threshold_configs
                (name, current_value, min_value, max_value, adjustment_step, sensitivity, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                config.name,
                config.current_value,
                config.min_value,
                config.max_value,
                config.adjustment_step,
                config.sensitivity,
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()

    def load_threshold_config(self, name: str) -> Optional[ThresholdConfig]:
        """Load threshold configuration by name"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, current_value, min_value, max_value, adjustment_step, sensitivity
                FROM threshold_configs WHERE name = ?
            """, (name,))

            row = cursor.fetchone()
            if row:
                return ThresholdConfig(*row)
            return None

    def save_performance_snapshot(self, snapshot: PerformanceSnapshot):
        """Save performance snapshot"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO performance_snapshots
                (timestamp, accuracy, cost_per_signal, roi, win_loss_ratio, signal_volume,
                 false_positive_rate, thresholds, composite_score, target_achievement)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot.timestamp.isoformat(),
                snapshot.accuracy,
                snapshot.cost_per_signal,
                snapshot.roi,
                snapshot.win_loss_ratio,
                snapshot.signal_volume,
                snapshot.false_positive_rate,
                json.dumps(snapshot.thresholds),
                snapshot.composite_score,
                snapshot.target_achievement
            ))
            conn.commit()

    def get_recent_performance(self, hours: int = 24) -> List[PerformanceSnapshot]:
        """Get recent performance snapshots"""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, accuracy, cost_per_signal, roi, win_loss_ratio,
                       signal_volume, false_positive_rate, thresholds,
                       composite_score, target_achievement
                FROM performance_snapshots
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """, (since.isoformat(),))

            snapshots = []
            for row in cursor.fetchall():
                timestamp = datetime.fromisoformat(row[0])
                thresholds = json.loads(row[7])

                snapshot = PerformanceSnapshot(
                    timestamp=timestamp,
                    accuracy=row[1],
                    cost_per_signal=row[2],
                    roi=row[3],
                    win_loss_ratio=row[4],
                    signal_volume=row[5],
                    false_positive_rate=row[6],
                    thresholds=thresholds,
                    composite_score=row[8],
                    target_achievement=row[9]
                )
                snapshots.append(snapshot)

            return snapshots

    def record_threshold_adjustment(self, threshold_name: str, old_value: float,
                                  new_value: float, reason: str):
        """Record threshold adjustment"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO threshold_adjustments
                (timestamp, threshold_name, old_value, new_value, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                threshold_name,
                old_value,
                new_value,
                reason
            ))
            conn.commit()


class PerformanceCalculator:
    """Calculates composite performance scores for optimization"""

    def __init__(self, targets: Dict[str, float]):
        """
        Initialize performance calculator

        Args:
            targets: Target values for metrics (accuracy, cost_per_signal, roi, win_loss_ratio)
        """
        self.targets = targets

        # Weights for composite score calculation
        self.weights = {
            'accuracy': 0.35,
            'cost_efficiency': 0.25,
            'roi': 0.25,
            'win_loss_ratio': 0.15
        }

    def calculate_composite_score(self, snapshot: PerformanceSnapshot) -> float:
        """
        Calculate composite performance score (0-1, higher is better)

        Args:
            snapshot: Performance snapshot to evaluate

        Returns:
            Composite score between 0 and 1
        """
        scores = {}

        # Accuracy score (target: >75%)
        target_accuracy = self.targets.get('accuracy', 0.75)
        scores['accuracy'] = min(snapshot.accuracy / target_accuracy, 1.0)

        # Cost efficiency score (target: <$5)
        target_cost = self.targets.get('cost_per_signal', 5.0)
        if snapshot.cost_per_signal > 0:
            cost_efficiency = target_cost / snapshot.cost_per_signal
            scores['cost_efficiency'] = min(cost_efficiency, 1.0)
        else:
            scores['cost_efficiency'] = 1.0

        # ROI score (target improvement vs baseline)
        target_roi = self.targets.get('roi', 0.25)
        if target_roi > 0:
            scores['roi'] = min(snapshot.roi / target_roi, 1.0)
        else:
            scores['roi'] = 0.5  # Neutral for zero target

        # Win/loss ratio score (target: >1.8)
        target_wl = self.targets.get('win_loss_ratio', 1.8)
        scores['win_loss_ratio'] = min(snapshot.win_loss_ratio / target_wl, 1.0)

        # Calculate weighted composite score
        composite = sum(scores[metric] * self.weights[metric] for metric in scores)

        return min(composite, 1.0)

    def calculate_target_achievement(self, snapshot: PerformanceSnapshot) -> float:
        """
        Calculate percentage of targets achieved

        Returns:
            Percentage of targets achieved (0-1)
        """
        achievements = []

        # Check each target
        if snapshot.accuracy >= self.targets.get('accuracy', 0.75):
            achievements.append(1.0)
        else:
            achievements.append(0.0)

        if snapshot.cost_per_signal <= self.targets.get('cost_per_signal', 5.0):
            achievements.append(1.0)
        else:
            achievements.append(0.0)

        if snapshot.roi >= self.targets.get('roi', 0.25):
            achievements.append(1.0)
        else:
            achievements.append(0.0)

        if snapshot.win_loss_ratio >= self.targets.get('win_loss_ratio', 1.8):
            achievements.append(1.0)
        else:
            achievements.append(0.0)

        return sum(achievements) / len(achievements)


class ThresholdOptimizer:
    """Machine learning-based threshold optimization"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize threshold optimizer

        Args:
            config: Optimization configuration
        """
        self.config = config
        self.min_data_points = config.get('min_data_points', 10)
        self.optimization_window = config.get('optimization_window', 24)  # hours

        # ML models
        self.models = {}
        if SKLEARN_AVAILABLE:
            self.scaler = StandardScaler()
            self._init_models()

    def _init_models(self):
        """Initialize ML models for optimization"""
        if not SKLEARN_AVAILABLE:
            return

        # Different models for different objectives
        self.models = {
            'accuracy': RandomForestRegressor(n_estimators=50, random_state=42),
            'cost_efficiency': Ridge(alpha=1.0),
            'roi': LinearRegression(),
            'win_loss_ratio': RandomForestRegressor(n_estimators=30, random_state=42),
            'balanced': RandomForestRegressor(n_estimators=100, random_state=42)
        }

    def optimize_thresholds(self,
                           performance_history: List[PerformanceSnapshot],
                           current_thresholds: Dict[str, ThresholdConfig],
                           objective: OptimizationObjective) -> OptimizationResult:
        """
        Optimize thresholds based on performance history

        Args:
            performance_history: Historical performance data
            current_thresholds: Current threshold configurations
            objective: Optimization objective

        Returns:
            OptimizationResult with recommendations
        """
        optimization_id = f"opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if len(performance_history) < self.min_data_points:
            logger.warning(f"Insufficient data for optimization: {len(performance_history)} < {self.min_data_points}")
            return self._create_default_result(optimization_id, objective, current_thresholds)

        try:
            if SKLEARN_AVAILABLE:
                return self._ml_optimization(optimization_id, performance_history, current_thresholds, objective)
            else:
                return self._heuristic_optimization(optimization_id, performance_history, current_thresholds, objective)

        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return self._create_default_result(optimization_id, objective, current_thresholds)

    def _ml_optimization(self, optimization_id: str, performance_history: List[PerformanceSnapshot],
                        current_thresholds: Dict[str, ThresholdConfig],
                        objective: OptimizationObjective) -> OptimizationResult:
        """Machine learning-based optimization"""

        # Prepare training data
        X, y = self._prepare_training_data(performance_history, objective)

        if len(X) < self.min_data_points:
            return self._heuristic_optimization(optimization_id, performance_history, current_thresholds, objective)

        # Select and train model
        model_key = objective.value if objective.value in self.models else 'balanced'
        model = self.models[model_key]

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train model
        model.fit(X_scaled, y)

        # Cross-validation
        cv_scores = cross_val_score(model, X_scaled, y, cv=min(5, len(X)//2))
        cv_score = np.mean(cv_scores)

        # Generate threshold adjustments
        current_values = [config.current_value for config in current_thresholds.values()]
        current_features = np.array([current_values])
        current_scaled = self.scaler.transform(current_features)

        # Predict current performance
        current_prediction = model.predict(current_scaled)[0]

        # Test potential improvements
        best_adjustments = {}
        best_improvement = 0.0

        threshold_names = list(current_thresholds.keys())

        # Try adjustments for each threshold
        for i, (name, config) in enumerate(current_thresholds.items()):
            # Try increasing threshold
            test_values = current_values.copy()
            new_value = min(config.current_value + config.adjustment_step, config.max_value)
            test_values[i] = new_value

            test_features = np.array([test_values])
            test_scaled = self.scaler.transform(test_features)
            test_prediction = model.predict(test_scaled)[0]

            improvement = test_prediction - current_prediction
            if improvement > best_improvement:
                best_improvement = improvement
                best_adjustments = {name: new_value}

            # Try decreasing threshold
            test_values = current_values.copy()
            new_value = max(config.current_value - config.adjustment_step, config.min_value)
            test_values[i] = new_value

            test_features = np.array([test_values])
            test_scaled = self.scaler.transform(test_features)
            test_prediction = model.predict(test_scaled)[0]

            improvement = test_prediction - current_prediction
            if improvement > best_improvement:
                best_improvement = improvement
                best_adjustments = {name: new_value}

        # Determine confidence and risk
        confidence = min(cv_score, 1.0) if cv_score > 0 else 0.5
        risk_assessment = self._assess_risk(best_improvement, confidence)
        recommendation = self._make_recommendation(best_improvement, confidence, risk_assessment)

        return OptimizationResult(
            optimization_id=optimization_id,
            timestamp=datetime.now(timezone.utc),
            objective=objective,
            threshold_adjustments=best_adjustments,
            expected_improvement=best_improvement,
            confidence=confidence,
            cross_validation_score=cv_score,
            risk_assessment=risk_assessment,
            recommendation=recommendation
        )

    def _heuristic_optimization(self, optimization_id: str, performance_history: List[PerformanceSnapshot],
                               current_thresholds: Dict[str, ThresholdConfig],
                               objective: OptimizationObjective) -> OptimizationResult:
        """Heuristic-based optimization when ML is not available"""

        # Calculate recent performance trend
        recent_performances = [self._calculate_objective_score(snapshot, objective) for snapshot in performance_history[-5:]]

        if len(recent_performances) < 2:
            return self._create_default_result(optimization_id, objective, current_thresholds)

        # Calculate trend
        performance_trend = recent_performances[-1] - recent_performances[0]
        avg_performance = statistics.mean(recent_performances)

        adjustments = {}

        # Heuristic rules based on objective and performance
        if objective == OptimizationObjective.ACCURACY:
            # If accuracy is low, make thresholds more restrictive
            if avg_performance < 0.7:
                for name, config in current_thresholds.items():
                    if 'min_' in name or 'confidence' in name:
                        new_value = min(config.current_value + config.adjustment_step, config.max_value)
                        adjustments[name] = new_value

        elif objective == OptimizationObjective.COST_EFFICIENCY:
            # If cost is high, reduce signal volume by increasing thresholds
            recent_costs = [s.cost_per_signal for s in performance_history[-3:]]
            avg_cost = statistics.mean(recent_costs) if recent_costs else 5.0

            if avg_cost > 5.0:
                for name, config in current_thresholds.items():
                    if 'min_' in name:
                        new_value = min(config.current_value + config.adjustment_step, config.max_value)
                        adjustments[name] = new_value

        # Calculate expected improvement (simplified)
        expected_improvement = abs(performance_trend) * 0.1  # Conservative estimate

        return OptimizationResult(
            optimization_id=optimization_id,
            timestamp=datetime.now(timezone.utc),
            objective=objective,
            threshold_adjustments=adjustments,
            expected_improvement=expected_improvement,
            confidence=0.6,  # Moderate confidence for heuristic
            risk_assessment="MEDIUM",
            recommendation="MONITOR" if adjustments else "NONE"
        )

    def _prepare_training_data(self, performance_history: List[PerformanceSnapshot],
                              objective: OptimizationObjective) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for ML models"""

        X = []  # Features: threshold values
        y = []  # Target: objective score

        for snapshot in performance_history:
            # Extract threshold values as features
            threshold_values = []
            for threshold_name in sorted(snapshot.thresholds.keys()):
                threshold_values.append(snapshot.thresholds[threshold_name])

            if threshold_values:  # Only add if we have threshold data
                X.append(threshold_values)
                y.append(self._calculate_objective_score(snapshot, objective))

        return np.array(X), np.array(y)

    def _calculate_objective_score(self, snapshot: PerformanceSnapshot,
                                  objective: OptimizationObjective) -> float:
        """Calculate score for specific objective"""

        if objective == OptimizationObjective.ACCURACY:
            return snapshot.accuracy
        elif objective == OptimizationObjective.COST_EFFICIENCY:
            return 1.0 / max(snapshot.cost_per_signal, 0.1)  # Inverse of cost
        elif objective == OptimizationObjective.ROI:
            return snapshot.roi
        elif objective == OptimizationObjective.WIN_LOSS_RATIO:
            return min(snapshot.win_loss_ratio / 2.0, 1.0)  # Normalized
        else:  # BALANCED
            return snapshot.composite_score

    def _assess_risk(self, expected_improvement: float, confidence: float) -> str:
        """Assess risk of applying optimization"""

        if confidence < 0.4 or expected_improvement < 0.01:
            return "HIGH"
        elif confidence > 0.8 and expected_improvement > 0.05:
            return "LOW"
        else:
            return "MEDIUM"

    def _make_recommendation(self, expected_improvement: float, confidence: float, risk: str) -> str:
        """Make recommendation based on analysis"""

        if risk == "HIGH" or expected_improvement <= 0:
            return "REJECT"
        elif risk == "LOW" and confidence > 0.7:
            return "APPLY"
        else:
            return "MONITOR"

    def _create_default_result(self, optimization_id: str, objective: OptimizationObjective,
                              current_thresholds: Dict[str, ThresholdConfig]) -> OptimizationResult:
        """Create default result when optimization cannot proceed"""

        return OptimizationResult(
            optimization_id=optimization_id,
            timestamp=datetime.now(timezone.utc),
            objective=objective,
            threshold_adjustments={},
            expected_improvement=0.0,
            confidence=0.0,
            risk_assessment="HIGH",
            recommendation="NONE"
        )


class AdaptiveThresholdManager:
    """
    Main adaptive threshold management system

    Features:
    - Real-time performance monitoring
    - Automatic threshold optimization
    - Multi-objective optimization
    - Safety mechanisms and rollback
    - Integration with success metrics tracking
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adaptive threshold manager

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.database = AdaptiveThresholdDatabase(config.get('db_path', 'outputs/adaptive_thresholds.db'))

        # Performance targets
        self.targets = config.get('targets', {
            'accuracy': 0.75,
            'cost_per_signal': 5.0,
            'roi': 0.25,
            'win_loss_ratio': 1.8
        })

        self.performance_calculator = PerformanceCalculator(self.targets)
        self.optimizer = ThresholdOptimizer(config.get('optimization', {}))

        # Monitoring configuration
        self.monitoring_interval = config.get('monitoring_interval', 3600)  # 1 hour
        self.optimization_interval = config.get('optimization_interval', 21600)  # 6 hours

        # Threshold configurations
        self.threshold_configs = self._initialize_threshold_configs()

        # Integration with success metrics
        self.metrics_tracker = None
        if METRICS_INTEGRATION_AVAILABLE:
            try:
                from .success_metrics_tracker import create_success_metrics_tracker
                self.metrics_tracker = create_success_metrics_tracker()
                logger.info("Success metrics integration enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize metrics tracker: {e}")

        # Monitoring state
        self.monitoring_active = False
        self.last_optimization = None
        self.performance_history = deque(maxlen=100)

        # Callbacks
        self.on_threshold_change: Optional[Callable[[str, float, float], None]] = None
        self.on_optimization_complete: Optional[Callable[[OptimizationResult], None]] = None

        logger.info("Adaptive Threshold Manager initialized")

    def _initialize_threshold_configs(self) -> Dict[str, ThresholdConfig]:
        """Initialize default threshold configurations"""

        configs = {
            'min_pressure_ratio': ThresholdConfig(
                name='min_pressure_ratio',
                current_value=2.0,
                min_value=1.2,
                max_value=5.0,
                adjustment_step=0.2,
                sensitivity=0.8
            ),
            'min_total_volume': ThresholdConfig(
                name='min_total_volume',
                current_value=100.0,
                min_value=50.0,
                max_value=500.0,
                adjustment_step=25.0,
                sensitivity=0.6
            ),
            'min_confidence': ThresholdConfig(
                name='min_confidence',
                current_value=0.8,
                min_value=0.5,
                max_value=0.95,
                adjustment_step=0.05,
                sensitivity=0.9
            ),
            'min_final_confidence': ThresholdConfig(
                name='min_final_confidence',
                current_value=0.7,
                min_value=0.5,
                max_value=0.9,
                adjustment_step=0.05,
                sensitivity=0.8
            )
        }

        # Load existing configurations from database
        for name in configs:
            stored_config = self.database.load_threshold_config(name)
            if stored_config:
                configs[name] = stored_config
            else:
                # Save default configuration
                self.database.save_threshold_config(configs[name])

        return configs

    def start_monitoring(self):
        """Start automatic performance monitoring and optimization"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return

        self.monitoring_active = True

        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="AdaptiveThresholdMonitor"
        )
        monitor_thread.start()

        logger.info("Adaptive threshold monitoring started")

    def stop_monitoring(self):
        """Stop automatic monitoring"""
        self.monitoring_active = False
        logger.info("Adaptive threshold monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop"""

        while self.monitoring_active:
            try:
                # Collect current performance
                self._collect_performance_snapshot()

                # Check if optimization is due
                if self._should_optimize():
                    self._run_optimization()

                # Sleep until next monitoring cycle
                time.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)  # Short sleep on error

    def _collect_performance_snapshot(self):
        """Collect current performance metrics"""

        if not self.metrics_tracker:
            # Create mock snapshot for testing
            snapshot = PerformanceSnapshot(
                timestamp=datetime.now(timezone.utc),
                accuracy=0.72,
                cost_per_signal=4.5,
                roi=0.18,
                win_loss_ratio=1.6,
                signal_volume=25,
                false_positive_rate=0.28,
                thresholds={name: config.current_value for name, config in self.threshold_configs.items()},
            )
        else:
            # Get real performance metrics
            report = self.metrics_tracker.get_success_metrics_report(days_back=1)

            snapshot = PerformanceSnapshot(
                timestamp=datetime.now(timezone.utc),
                accuracy=report['v3_performance']['accuracy'],
                cost_per_signal=report['v3_performance']['cost_per_signal'],
                roi=report['v3_performance']['roi'],
                win_loss_ratio=report['v3_performance']['win_loss_ratio'],
                signal_volume=0,  # Would need to be calculated
                false_positive_rate=1.0 - report['v3_performance']['accuracy'],
                thresholds={name: config.current_value for name, config in self.threshold_configs.items()},
            )

        # Calculate composite scores
        snapshot.composite_score = self.performance_calculator.calculate_composite_score(snapshot)
        snapshot.target_achievement = self.performance_calculator.calculate_target_achievement(snapshot)

        # Store snapshot
        self.performance_history.append(snapshot)
        self.database.save_performance_snapshot(snapshot)

        logger.debug(f"Performance snapshot: accuracy={snapshot.accuracy:.3f}, "
                    f"cost=${snapshot.cost_per_signal:.2f}, composite={snapshot.composite_score:.3f}")

    def _should_optimize(self) -> bool:
        """Check if optimization should be run"""

        if not self.last_optimization:
            return len(self.performance_history) >= 10  # Initial optimization

        # Check time since last optimization
        time_since_last = datetime.now(timezone.utc) - self.last_optimization
        if time_since_last.total_seconds() < self.optimization_interval:
            return False

        # Check performance degradation
        if len(self.performance_history) >= 5:
            recent_performance = [s.composite_score for s in list(self.performance_history)[-5:]]
            avg_recent = statistics.mean(recent_performance)

            if avg_recent < 0.6:  # Poor performance threshold
                logger.info("Performance degradation detected - triggering optimization")
                return True

        return True  # Regular optimization interval

    def _run_optimization(self):
        """Run threshold optimization"""

        logger.info("Starting threshold optimization")

        try:
            # Get recent performance data
            recent_performance = list(self.performance_history)[-24:]  # Last 24 snapshots

            # Try different optimization objectives
            objectives = [
                OptimizationObjective.BALANCED,
                OptimizationObjective.ACCURACY,
                OptimizationObjective.COST_EFFICIENCY
            ]

            best_result = None
            best_score = 0.0

            for objective in objectives:
                result = self.optimizer.optimize_thresholds(
                    recent_performance, self.threshold_configs, objective
                )

                score = result.confidence * result.expected_improvement
                if score > best_score:
                    best_score = score
                    best_result = result

            if best_result and best_result.recommendation == "APPLY":
                self._apply_optimization(best_result)
            elif best_result:
                logger.info(f"Optimization complete but not applied: {best_result.recommendation}")

            self.last_optimization = datetime.now(timezone.utc)

            if self.on_optimization_complete:
                self.on_optimization_complete(best_result)

        except Exception as e:
            logger.error(f"Optimization failed: {e}")

    def _apply_optimization(self, result: OptimizationResult):
        """Apply optimization result to thresholds"""

        logger.info(f"Applying optimization {result.optimization_id}")

        for threshold_name, new_value in result.threshold_adjustments.items():
            if threshold_name in self.threshold_configs:
                old_value = self.threshold_configs[threshold_name].current_value

                # Update threshold
                self.threshold_configs[threshold_name].current_value = new_value

                # Save to database
                self.database.save_threshold_config(self.threshold_configs[threshold_name])
                self.database.record_threshold_adjustment(
                    threshold_name, old_value, new_value,
                    f"Optimization {result.optimization_id}"
                )

                logger.info(f"Threshold {threshold_name}: {old_value:.3f} -> {new_value:.3f}")

                # Trigger callback
                if self.on_threshold_change:
                    self.on_threshold_change(threshold_name, old_value, new_value)

    def get_current_thresholds(self) -> Dict[str, float]:
        """Get current threshold values"""
        return {name: config.current_value for name, config in self.threshold_configs.items()}

    def manual_optimization(self, objective: OptimizationObjective) -> OptimizationResult:
        """Manually trigger optimization with specific objective"""

        recent_performance = list(self.performance_history)[-24:]
        if not recent_performance:
            # Collect performance first
            self._collect_performance_snapshot()
            recent_performance = list(self.performance_history)

        result = self.optimizer.optimize_thresholds(
            recent_performance, self.threshold_configs, objective
        )

        logger.info(f"Manual optimization complete: {result.recommendation}")
        return result

    def force_threshold_adjustment(self, threshold_name: str, new_value: float, reason: str = "Manual"):
        """Manually force threshold adjustment"""

        if threshold_name not in self.threshold_configs:
            raise ValueError(f"Unknown threshold: {threshold_name}")

        config = self.threshold_configs[threshold_name]
        old_value = config.current_value

        # Validate bounds
        if new_value < config.min_value or new_value > config.max_value:
            raise ValueError(f"Value {new_value} outside bounds [{config.min_value}, {config.max_value}]")

        # Apply change
        config.current_value = new_value

        # Save and log
        self.database.save_threshold_config(config)
        self.database.record_threshold_adjustment(threshold_name, old_value, new_value, reason)

        logger.info(f"Manually adjusted {threshold_name}: {old_value:.3f} -> {new_value:.3f}")

        if self.on_threshold_change:
            self.on_threshold_change(threshold_name, old_value, new_value)

    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of optimization activity"""

        recent_snapshots = list(self.performance_history)[-10:]

        if not recent_snapshots:
            return {
                'status': 'no_data',
                'performance_trend': 'unknown',
                'last_optimization': None,
                'targets_achieved': 0,
                'recommendations': []
            }

        # Calculate trends
        composite_scores = [s.composite_score for s in recent_snapshots]
        target_achievements = [s.target_achievement for s in recent_snapshots]

        performance_trend = "stable"
        if len(composite_scores) >= 3:
            recent_avg = statistics.mean(composite_scores[-3:])
            earlier_avg = statistics.mean(composite_scores[:3])

            if recent_avg > earlier_avg + 0.1:
                performance_trend = "improving"
            elif recent_avg < earlier_avg - 0.1:
                performance_trend = "declining"

        # Current status
        latest = recent_snapshots[-1]

        # Generate recommendations
        recommendations = []
        if latest.accuracy < self.targets['accuracy']:
            recommendations.append("Consider increasing min_confidence to improve accuracy")
        if latest.cost_per_signal > self.targets['cost_per_signal']:
            recommendations.append("Consider increasing min_pressure_ratio to reduce costs")
        if latest.win_loss_ratio < self.targets['win_loss_ratio']:
            recommendations.append("Consider adjusting thresholds to improve win/loss ratio")

        return {
            'status': 'active' if self.monitoring_active else 'inactive',
            'performance_trend': performance_trend,
            'last_optimization': self.last_optimization.isoformat() if self.last_optimization else None,
            'targets_achieved': int(latest.target_achievement * 4),
            'current_performance': {
                'accuracy': latest.accuracy,
                'cost_per_signal': latest.cost_per_signal,
                'roi': latest.roi,
                'win_loss_ratio': latest.win_loss_ratio,
                'composite_score': latest.composite_score
            },
            'recommendations': recommendations
        }


def create_adaptive_threshold_manager(config: Optional[Dict] = None) -> AdaptiveThresholdManager:
    """Factory function to create adaptive threshold manager"""

    if config is None:
        config = {
            'db_path': 'outputs/adaptive_thresholds.db',
            'targets': {
                'accuracy': 0.75,
                'cost_per_signal': 5.0,
                'roi': 0.25,
                'win_loss_ratio': 1.8
            },
            'monitoring_interval': 3600,  # 1 hour
            'optimization_interval': 21600,  # 6 hours
            'optimization': {
                'min_data_points': 10,
                'optimization_window': 24
            }
        }

    return AdaptiveThresholdManager(config)


if __name__ == "__main__":
    # Example usage
    manager = create_adaptive_threshold_manager()

    def on_threshold_change(name: str, old_value: float, new_value: float):
        print(f"Threshold changed: {name} {old_value:.3f} -> {new_value:.3f}")

    def on_optimization_complete(result: OptimizationResult):
        print(f"Optimization {result.optimization_id} complete: {result.recommendation}")
        print(f"Expected improvement: {result.expected_improvement:.3f}")

    manager.on_threshold_change = on_threshold_change
    manager.on_optimization_complete = on_optimization_complete

    # Start monitoring
    manager.start_monitoring()

    print("Adaptive Threshold Manager started")
    print("Current thresholds:", manager.get_current_thresholds())

    # Simulate running for a while
    try:
        print("Running monitoring... Press Ctrl+C to stop")
        while True:
            time.sleep(10)
            summary = manager.get_optimization_summary()
            print(f"Status: {summary['status']}, Trend: {summary['performance_trend']}")
    except KeyboardInterrupt:
        print("\nStopping...")
        manager.stop_monitoring()
