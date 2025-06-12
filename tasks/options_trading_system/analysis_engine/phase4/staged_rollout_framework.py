#!/usr/bin/env python3
"""
Staged Rollout Validation Framework for IFD v3.0

This module implements a comprehensive staged rollout system for safely deploying
new algorithm versions with controlled testing, performance validation, and
automatic rollback capabilities.

Key Features:
- A/B testing framework with statistical significance testing
- Multi-stage rollout with configurable traffic allocation
- Real-time performance monitoring and comparison
- Automatic rollback on performance degradation
- Champion/Challenger testing methodology
- Comprehensive rollout analytics and reporting

Rollout Stages:
1. Shadow Mode (0% live traffic)
2. Canary Deployment (5% traffic)
3. Limited Rollout (25% traffic)
4. Full Rollout (100% traffic)
"""

import os
import json
import logging
import sqlite3
import threading
import time
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple, Callable, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import statistics
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing scipy for statistical tests
try:
    from scipy import stats
    import scipy.stats as scipy_stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("SciPy not available - using basic statistical tests")

# Try importing success metrics tracker
try:
    from .success_metrics_tracker import SuccessMetricsTracker, SignalMetrics, AlgorithmVersion
    METRICS_AVAILABLE = True
except ImportError:
    logger.warning("Success metrics tracker not available")
    METRICS_AVAILABLE = False


class RolloutStage(Enum):
    """Rollout deployment stages"""
    SHADOW = "shadow"           # 0% traffic, logging only
    CANARY = "canary"          # 5% traffic
    LIMITED = "limited"        # 25% traffic
    STAGED = "staged"          # 50% traffic
    FULL = "full"             # 100% traffic
    ROLLBACK = "rollback"      # Emergency rollback


class RolloutStatus(Enum):
    """Current rollout status"""
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ValidationResult(Enum):
    """Validation test results"""
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    PENDING = "pending"


@dataclass
class RolloutConfiguration:
    """Configuration for a staged rollout"""
    rollout_id: str
    champion_version: str
    challenger_version: str

    # Traffic allocation by stage
    stage_traffic_allocation: Dict[RolloutStage, float]

    # Validation criteria
    min_sample_size: int = 100
    confidence_level: float = 0.95
    min_improvement_threshold: float = 0.05  # 5% improvement required
    max_degradation_threshold: float = 0.02  # 2% degradation triggers rollback

    # Timing
    stage_duration_hours: Dict[RolloutStage, int] = None
    max_rollout_duration_hours: int = 168  # 1 week

    # Monitoring
    performance_check_interval: int = 300  # 5 minutes
    statistical_test_interval: int = 3600   # 1 hour

    def __post_init__(self):
        if self.stage_traffic_allocation is None:
            self.stage_traffic_allocation = {
                RolloutStage.SHADOW: 0.0,
                RolloutStage.CANARY: 0.05,
                RolloutStage.LIMITED: 0.25,
                RolloutStage.STAGED: 0.50,
                RolloutStage.FULL: 1.0
            }

        if self.stage_duration_hours is None:
            self.stage_duration_hours = {
                RolloutStage.SHADOW: 4,
                RolloutStage.CANARY: 12,
                RolloutStage.LIMITED: 24,
                RolloutStage.STAGED: 48,
                RolloutStage.FULL: 0  # Indefinite
            }


@dataclass
class PerformanceMetrics:
    """Performance metrics for rollout validation"""
    version: str
    timestamp: datetime
    stage: RolloutStage

    # Core metrics
    accuracy: float
    cost_per_signal: float
    roi: float
    win_loss_ratio: float
    signal_volume: int

    # Quality metrics
    false_positive_rate: float
    false_negative_rate: float
    precision: float
    recall: float

    # Operational metrics
    processing_latency: float
    error_rate: float
    uptime: float

    # Business metrics
    total_pnl: float
    sharpe_ratio: float
    max_drawdown: float


@dataclass
class ValidationTest:
    """Statistical validation test results"""
    test_id: str
    timestamp: datetime
    metric_name: str

    champion_mean: float
    challenger_mean: float
    champion_std: float
    challenger_std: float
    champion_n: int
    challenger_n: int

    # Statistical test results
    test_statistic: float
    p_value: float
    confidence_interval: Tuple[float, float]
    effect_size: float

    # Interpretation
    result: ValidationResult
    significance_level: float
    is_statistically_significant: bool
    practical_significance: bool

    # Decision
    recommendation: str  # "PROCEED", "PAUSE", "ROLLBACK"
    reason: str


@dataclass
class RolloutState:
    """Current state of a rollout"""
    rollout_id: str
    configuration: RolloutConfiguration

    # Current state
    current_stage: RolloutStage
    status: RolloutStatus
    started_at: datetime
    current_stage_started_at: datetime

    # Traffic allocation
    current_traffic_percentage: float
    total_requests: int
    challenger_requests: int

    # Performance tracking
    champion_metrics: List[PerformanceMetrics]
    challenger_metrics: List[PerformanceMetrics]

    # Validation results
    validation_tests: List[ValidationTest]
    last_validation: Optional[datetime] = None

    # Decision history
    decision_log: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.decision_log is None:
            self.decision_log = []


class StatisticalValidator:
    """Performs statistical validation of rollout performance"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.significance_level = config.get('significance_level', 0.05)
        self.min_effect_size = config.get('min_effect_size', 0.1)
        self.min_sample_size = config.get('min_sample_size', 50)

    def validate_metric_comparison(self,
                                 champion_values: List[float],
                                 challenger_values: List[float],
                                 metric_name: str,
                                 higher_is_better: bool = True) -> ValidationTest:
        """
        Perform statistical validation of metric comparison

        Args:
            champion_values: Champion algorithm metric values
            challenger_values: Challenger algorithm metric values
            metric_name: Name of the metric being tested
            higher_is_better: Whether higher values are better for this metric

        Returns:
            ValidationTest with statistical analysis results
        """

        test_id = f"{metric_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.now(timezone.utc)

        # Check sample sizes
        if len(champion_values) < self.min_sample_size or len(challenger_values) < self.min_sample_size:
            return ValidationTest(
                test_id=test_id,
                timestamp=timestamp,
                metric_name=metric_name,
                champion_mean=statistics.mean(champion_values) if champion_values else 0.0,
                challenger_mean=statistics.mean(challenger_values) if challenger_values else 0.0,
                champion_std=statistics.stdev(champion_values) if len(champion_values) > 1 else 0.0,
                challenger_std=statistics.stdev(challenger_values) if len(challenger_values) > 1 else 0.0,
                champion_n=len(champion_values),
                challenger_n=len(challenger_values),
                test_statistic=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0),
                effect_size=0.0,
                result=ValidationResult.INCONCLUSIVE,
                significance_level=self.significance_level,
                is_statistically_significant=False,
                practical_significance=False,
                recommendation="PAUSE",
                reason="Insufficient sample size for statistical testing"
            )

        # Calculate basic statistics
        champion_mean = statistics.mean(champion_values)
        challenger_mean = statistics.mean(challenger_values)
        champion_std = statistics.stdev(champion_values) if len(champion_values) > 1 else 0.0
        challenger_std = statistics.stdev(challenger_values) if len(challenger_values) > 1 else 0.0

        # Perform statistical test
        if SCIPY_AVAILABLE:
            test_stat, p_value = self._scipy_test(champion_values, challenger_values)
            effect_size = self._calculate_effect_size(champion_values, challenger_values)
            confidence_interval = self._calculate_confidence_interval(
                champion_values, challenger_values, higher_is_better
            )
        else:
            test_stat, p_value = self._basic_t_test(champion_values, challenger_values)
            effect_size = abs(challenger_mean - champion_mean) / max(champion_std, challenger_std, 0.1)
            confidence_interval = (challenger_mean - 2*challenger_std, challenger_mean + 2*challenger_std)

        # Determine significance
        is_statistically_significant = p_value < self.significance_level
        practical_significance = abs(effect_size) >= self.min_effect_size

        # Determine improvement/degradation
        if higher_is_better:
            improvement = (challenger_mean - champion_mean) / max(champion_mean, 0.001)
        else:
            improvement = (champion_mean - challenger_mean) / max(champion_mean, 0.001)

        # Make decision
        result, recommendation, reason = self._make_validation_decision(
            improvement, is_statistically_significant, practical_significance, p_value
        )

        return ValidationTest(
            test_id=test_id,
            timestamp=timestamp,
            metric_name=metric_name,
            champion_mean=champion_mean,
            challenger_mean=challenger_mean,
            champion_std=champion_std,
            challenger_std=challenger_std,
            champion_n=len(champion_values),
            challenger_n=len(challenger_values),
            test_statistic=test_stat,
            p_value=p_value,
            confidence_interval=confidence_interval,
            effect_size=effect_size,
            result=result,
            significance_level=self.significance_level,
            is_statistically_significant=is_statistically_significant,
            practical_significance=practical_significance,
            recommendation=recommendation,
            reason=reason
        )

    def _scipy_test(self, champion_values: List[float], challenger_values: List[float]) -> Tuple[float, float]:
        """Perform statistical test using SciPy"""
        try:
            # Use Welch's t-test (unequal variances)
            statistic, p_value = stats.ttest_ind(challenger_values, champion_values, equal_var=False)
            return float(statistic), float(p_value)
        except Exception as e:
            logger.warning(f"SciPy test failed, using basic test: {e}")
            return self._basic_t_test(champion_values, challenger_values)

    def _basic_t_test(self, champion_values: List[float], challenger_values: List[float]) -> Tuple[float, float]:
        """Basic t-test implementation when SciPy not available"""

        n1, n2 = len(champion_values), len(challenger_values)
        mean1, mean2 = statistics.mean(champion_values), statistics.mean(challenger_values)

        if n1 <= 1 or n2 <= 1:
            return 0.0, 1.0

        var1 = statistics.variance(champion_values)
        var2 = statistics.variance(challenger_values)

        # Pooled standard error
        pooled_se = ((var1/n1) + (var2/n2)) ** 0.5

        if pooled_se == 0:
            return 0.0, 1.0

        # T-statistic
        t_stat = (mean2 - mean1) / pooled_se

        # Degrees of freedom (Welch-Satterthwaite equation)
        df = ((var1/n1) + (var2/n2))**2 / ((var1/n1)**2/(n1-1) + (var2/n2)**2/(n2-1))

        # Approximate p-value (simplified)
        p_value = 2 * (1 - abs(t_stat) / (abs(t_stat) + df**0.5))
        p_value = max(0.001, min(0.999, p_value))  # Bound p-value

        return float(t_stat), float(p_value)

    def _calculate_effect_size(self, champion_values: List[float], challenger_values: List[float]) -> float:
        """Calculate Cohen's d effect size"""

        if len(champion_values) <= 1 or len(challenger_values) <= 1:
            return 0.0

        mean1, mean2 = statistics.mean(champion_values), statistics.mean(challenger_values)
        var1, var2 = statistics.variance(champion_values), statistics.variance(challenger_values)
        n1, n2 = len(champion_values), len(challenger_values)

        # Pooled standard deviation
        pooled_std = ((((n1-1)*var1) + ((n2-1)*var2)) / (n1+n2-2)) ** 0.5

        if pooled_std == 0:
            return 0.0

        # Cohen's d
        cohens_d = (mean2 - mean1) / pooled_std
        return float(cohens_d)

    def _calculate_confidence_interval(self, champion_values: List[float],
                                     challenger_values: List[float],
                                     higher_is_better: bool) -> Tuple[float, float]:
        """Calculate confidence interval for the difference"""

        if not SCIPY_AVAILABLE:
            # Simple approximation
            challenger_mean = statistics.mean(challenger_values)
            challenger_std = statistics.stdev(challenger_values) if len(challenger_values) > 1 else 0.0
            margin = 1.96 * challenger_std  # 95% CI approximation
            return (challenger_mean - margin, challenger_mean + margin)

        try:
            # Calculate confidence interval for difference using SciPy
            diff = np.array(challenger_values).mean() - np.array(champion_values).mean()
            se_diff = (np.array(challenger_values).var()/len(challenger_values) +
                      np.array(champion_values).var()/len(champion_values)) ** 0.5

            margin = 1.96 * se_diff  # 95% CI
            return (diff - margin, diff + margin)

        except Exception:
            # Fallback
            challenger_mean = statistics.mean(challenger_values)
            challenger_std = statistics.stdev(challenger_values) if len(challenger_values) > 1 else 0.0
            margin = 1.96 * challenger_std
            return (challenger_mean - margin, challenger_mean + margin)

    def _make_validation_decision(self, improvement: float, is_significant: bool,
                                practical_significance: bool, p_value: float) -> Tuple[ValidationResult, str, str]:
        """Make validation decision based on statistical analysis"""

        # Rollback thresholds
        rollback_threshold = -0.05  # 5% degradation
        proceed_threshold = 0.02    # 2% improvement

        if improvement < rollback_threshold and is_significant:
            return ValidationResult.FAIL, "ROLLBACK", f"Significant degradation: {improvement:.1%}"

        elif improvement > proceed_threshold and is_significant and practical_significance:
            return ValidationResult.PASS, "PROCEED", f"Significant improvement: {improvement:.1%}"

        elif improvement > proceed_threshold and is_significant:
            return ValidationResult.PASS, "PROCEED", f"Statistically significant improvement: {improvement:.1%}"

        elif abs(improvement) < 0.01:  # Less than 1% change
            return ValidationResult.INCONCLUSIVE, "PROCEED", "No meaningful difference detected"

        elif not is_significant:
            return ValidationResult.INCONCLUSIVE, "PAUSE", f"Not statistically significant (p={p_value:.3f})"

        else:
            return ValidationResult.PENDING, "PAUSE", "Need more data for conclusive results"


class RolloutDatabase:
    """Database for tracking rollout state and performance"""

    def __init__(self, db_path: str = "outputs/staged_rollouts.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Rollout configurations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rollout_configs (
                    rollout_id TEXT PRIMARY KEY,
                    champion_version TEXT NOT NULL,
                    challenger_version TEXT NOT NULL,
                    configuration TEXT NOT NULL,  -- JSON
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)

            # Rollout state tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rollout_states (
                    rollout_id TEXT PRIMARY KEY,
                    current_stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    current_stage_started_at TEXT NOT NULL,
                    current_traffic_percentage REAL NOT NULL,
                    total_requests INTEGER DEFAULT 0,
                    challenger_requests INTEGER DEFAULT 0,
                    last_updated TEXT NOT NULL,
                    FOREIGN KEY (rollout_id) REFERENCES rollout_configs (rollout_id)
                )
            """)

            # Performance metrics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rollout_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    accuracy REAL,
                    cost_per_signal REAL,
                    roi REAL,
                    win_loss_ratio REAL,
                    signal_volume INTEGER,
                    false_positive_rate REAL,
                    false_negative_rate REAL,
                    precision_score REAL,
                    recall_score REAL,
                    processing_latency REAL,
                    error_rate REAL,
                    uptime REAL,
                    total_pnl REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (rollout_id) REFERENCES rollout_configs (rollout_id)
                )
            """)

            # Validation tests
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS validation_tests (
                    test_id TEXT PRIMARY KEY,
                    rollout_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    champion_mean REAL NOT NULL,
                    challenger_mean REAL NOT NULL,
                    champion_std REAL NOT NULL,
                    challenger_std REAL NOT NULL,
                    champion_n INTEGER NOT NULL,
                    challenger_n INTEGER NOT NULL,
                    test_statistic REAL NOT NULL,
                    p_value REAL NOT NULL,
                    confidence_interval_lower REAL NOT NULL,
                    confidence_interval_upper REAL NOT NULL,
                    effect_size REAL NOT NULL,
                    result TEXT NOT NULL,
                    significance_level REAL NOT NULL,
                    is_statistically_significant BOOLEAN NOT NULL,
                    practical_significance BOOLEAN NOT NULL,
                    recommendation TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (rollout_id) REFERENCES rollout_configs (rollout_id)
                )
            """)

            # Decision log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rollout_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rollout_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    decision_type TEXT NOT NULL,  -- STAGE_ADVANCE, PAUSE, ROLLBACK
                    from_stage TEXT,
                    to_stage TEXT,
                    reason TEXT NOT NULL,
                    automatic BOOLEAN DEFAULT 1,
                    decision_data TEXT,  -- JSON
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (rollout_id) REFERENCES rollout_configs (rollout_id)
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_rollout_time ON performance_metrics(rollout_id, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tests_rollout ON validation_tests(rollout_id, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_rollout ON rollout_decisions(rollout_id, timestamp)")

            conn.commit()

    def save_rollout_configuration(self, rollout_id: str, config: RolloutConfiguration):
        """Save rollout configuration"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO rollout_configs
                (rollout_id, champion_version, challenger_version, configuration, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                rollout_id,
                config.champion_version,
                config.challenger_version,
                json.dumps(asdict(config)),
                datetime.now(timezone.utc).isoformat(),
                "active"
            ))
            conn.commit()

    def save_rollout_state(self, state: RolloutState):
        """Save current rollout state"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO rollout_states
                (rollout_id, current_stage, status, started_at, current_stage_started_at,
                 current_traffic_percentage, total_requests, challenger_requests, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                state.rollout_id,
                state.current_stage.value,
                state.status.value,
                state.started_at.isoformat(),
                state.current_stage_started_at.isoformat(),
                state.current_traffic_percentage,
                state.total_requests,
                state.challenger_requests,
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()

    def record_performance_metrics(self, rollout_id: str, metrics: PerformanceMetrics):
        """Record performance metrics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO performance_metrics
                (rollout_id, version, timestamp, stage, accuracy, cost_per_signal, roi,
                 win_loss_ratio, signal_volume, false_positive_rate, false_negative_rate,
                 precision_score, recall_score, processing_latency, error_rate, uptime,
                 total_pnl, sharpe_ratio, max_drawdown)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rollout_id, metrics.version, metrics.timestamp.isoformat(), metrics.stage.value,
                metrics.accuracy, metrics.cost_per_signal, metrics.roi, metrics.win_loss_ratio,
                metrics.signal_volume, metrics.false_positive_rate, metrics.false_negative_rate,
                metrics.precision, metrics.recall, metrics.processing_latency, metrics.error_rate,
                metrics.uptime, metrics.total_pnl, metrics.sharpe_ratio, metrics.max_drawdown
            ))
            conn.commit()

    def record_validation_test(self, rollout_id: str, test: ValidationTest):
        """Record validation test results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO validation_tests
                (test_id, rollout_id, timestamp, metric_name, champion_mean, challenger_mean,
                 champion_std, challenger_std, champion_n, challenger_n, test_statistic,
                 p_value, confidence_interval_lower, confidence_interval_upper, effect_size,
                 result, significance_level, is_statistically_significant, practical_significance,
                 recommendation, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test.test_id, rollout_id, test.timestamp.isoformat(), test.metric_name,
                test.champion_mean, test.challenger_mean, test.champion_std, test.challenger_std,
                test.champion_n, test.challenger_n, test.test_statistic, test.p_value,
                test.confidence_interval[0], test.confidence_interval[1], test.effect_size,
                test.result.value, test.significance_level, test.is_statistically_significant,
                test.practical_significance, test.recommendation, test.reason
            ))
            conn.commit()


class StagedRolloutManager:
    """
    Main staged rollout management system

    Features:
    - A/B testing with statistical validation
    - Multi-stage rollout progression
    - Automatic rollback on performance degradation
    - Real-time monitoring and alerting
    - Comprehensive rollout analytics
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize staged rollout manager

        Args:
            config: Rollout configuration
        """
        self.config = config
        self.database = RolloutDatabase(config.get('db_path', 'outputs/staged_rollouts.db'))
        self.validator = StatisticalValidator(config.get('validation', {}))

        # Active rollouts
        self.active_rollouts: Dict[str, RolloutState] = {}
        self.rollout_lock = threading.Lock()

        # Monitoring
        self.monitoring_active = False
        self.monitor_thread = None

        # Traffic routing
        self.traffic_router = TrafficRouter()

        # Callbacks
        self.on_stage_change: Optional[Callable[[str, RolloutStage, RolloutStage], None]] = None
        self.on_rollback: Optional[Callable[[str, str], None]] = None
        self.on_completion: Optional[Callable[[str, bool], None]] = None

        logger.info("Staged Rollout Manager initialized")

    def create_rollout(self,
                      rollout_id: str,
                      champion_version: str,
                      challenger_version: str,
                      config: Optional[RolloutConfiguration] = None) -> bool:
        """
        Create a new staged rollout

        Args:
            rollout_id: Unique identifier for rollout
            champion_version: Current production version
            challenger_version: New version to test
            config: Optional custom configuration

        Returns:
            True if rollout created successfully
        """

        if rollout_id in self.active_rollouts:
            logger.error(f"Rollout {rollout_id} already exists")
            return False

        # Create default configuration if not provided
        if config is None:
            config = RolloutConfiguration(
                rollout_id=rollout_id,
                champion_version=champion_version,
                challenger_version=challenger_version
            )

        # Create initial rollout state
        now = datetime.now(timezone.utc)
        state = RolloutState(
            rollout_id=rollout_id,
            configuration=config,
            current_stage=RolloutStage.SHADOW,
            status=RolloutStatus.RUNNING,
            started_at=now,
            current_stage_started_at=now,
            current_traffic_percentage=0.0,
            total_requests=0,
            challenger_requests=0,
            champion_metrics=[],
            challenger_metrics=[],
            validation_tests=[]
        )

        # Save to database
        try:
            self.database.save_rollout_configuration(rollout_id, config)
            self.database.save_rollout_state(state)

            # Add to active rollouts
            with self.rollout_lock:
                self.active_rollouts[rollout_id] = state

            # Log decision
            self._log_decision(rollout_id, "ROLLOUT_START", None, RolloutStage.SHADOW,
                             "Rollout initiated", automatic=False)

            logger.info(f"Created rollout {rollout_id}: {champion_version} vs {challenger_version}")
            return True

        except Exception as e:
            logger.error(f"Failed to create rollout {rollout_id}: {e}")
            return False

    def start_monitoring(self):
        """Start automatic monitoring of active rollouts"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="RolloutMonitor"
        )
        self.monitor_thread.start()

        logger.info("Rollout monitoring started")

    def stop_monitoring(self):
        """Stop rollout monitoring"""
        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        logger.info("Rollout monitoring stopped")

    def route_request(self, rollout_id: str) -> str:
        """
        Route a request to champion or challenger based on rollout configuration

        Args:
            rollout_id: Rollout to route for

        Returns:
            Version to route to ("champion" or "challenger")
        """

        if rollout_id not in self.active_rollouts:
            return "champion"  # Default to champion

        state = self.active_rollouts[rollout_id]

        # Update request count
        state.total_requests += 1

        # Route based on traffic percentage
        if random.random() < state.current_traffic_percentage:
            state.challenger_requests += 1
            return "challenger"
        else:
            return "champion"

    def record_performance(self, rollout_id: str, version: str, metrics: PerformanceMetrics):
        """
        Record performance metrics for a version

        Args:
            rollout_id: Rollout ID
            version: "champion" or "challenger"
            metrics: Performance metrics
        """

        if rollout_id not in self.active_rollouts:
            return

        state = self.active_rollouts[rollout_id]

        # Set version and stage
        metrics.version = version
        metrics.stage = state.current_stage

        # Store metrics
        if version == "champion":
            state.champion_metrics.append(metrics)
        else:
            state.challenger_metrics.append(metrics)

        # Limit history size
        max_metrics = 1000
        if len(state.champion_metrics) > max_metrics:
            state.champion_metrics = state.champion_metrics[-max_metrics//2:]
        if len(state.challenger_metrics) > max_metrics:
            state.challenger_metrics = state.challenger_metrics[-max_metrics//2:]

        # Save to database
        self.database.record_performance_metrics(rollout_id, metrics)

        logger.debug(f"Recorded {version} performance for {rollout_id}: "
                    f"accuracy={metrics.accuracy:.3f}, cost=${metrics.cost_per_signal:.2f}")

    def manual_advance_stage(self, rollout_id: str) -> bool:
        """Manually advance rollout to next stage"""

        if rollout_id not in self.active_rollouts:
            logger.error(f"Rollout {rollout_id} not found")
            return False

        state = self.active_rollouts[rollout_id]

        if state.status != RolloutStatus.RUNNING:
            logger.error(f"Rollout {rollout_id} not in running state: {state.status}")
            return False

        next_stage = self._get_next_stage(state.current_stage)
        if next_stage is None:
            logger.info(f"Rollout {rollout_id} already at final stage")
            return False

        return self._advance_to_stage(rollout_id, next_stage, "Manual advancement")

    def manual_rollback(self, rollout_id: str, reason: str = "Manual rollback") -> bool:
        """Manually trigger rollback"""

        if rollout_id not in self.active_rollouts:
            logger.error(f"Rollout {rollout_id} not found")
            return False

        return self._trigger_rollback(rollout_id, reason, automatic=False)

    def pause_rollout(self, rollout_id: str, reason: str = "Manual pause") -> bool:
        """Pause a rollout"""

        if rollout_id not in self.active_rollouts:
            logger.error(f"Rollout {rollout_id} not found")
            return False

        state = self.active_rollouts[rollout_id]
        state.status = RolloutStatus.PAUSED

        self.database.save_rollout_state(state)
        self._log_decision(rollout_id, "PAUSE", state.current_stage, state.current_stage,
                         reason, automatic=False)

        logger.info(f"Paused rollout {rollout_id}: {reason}")
        return True

    def resume_rollout(self, rollout_id: str, reason: str = "Manual resume") -> bool:
        """Resume a paused rollout"""

        if rollout_id not in self.active_rollouts:
            logger.error(f"Rollout {rollout_id} not found")
            return False

        state = self.active_rollouts[rollout_id]

        if state.status != RolloutStatus.PAUSED:
            logger.error(f"Rollout {rollout_id} not paused: {state.status}")
            return False

        state.status = RolloutStatus.RUNNING

        self.database.save_rollout_state(state)
        self._log_decision(rollout_id, "RESUME", state.current_stage, state.current_stage,
                         reason, automatic=False)

        logger.info(f"Resumed rollout {rollout_id}: {reason}")
        return True

    def _monitoring_loop(self):
        """Main monitoring loop"""

        while self.monitoring_active:
            try:
                with self.rollout_lock:
                    active_rollouts = list(self.active_rollouts.keys())

                for rollout_id in active_rollouts:
                    self._monitor_rollout(rollout_id)

                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(30)  # Short sleep on error

    def _monitor_rollout(self, rollout_id: str):
        """Monitor individual rollout"""

        if rollout_id not in self.active_rollouts:
            return

        state = self.active_rollouts[rollout_id]

        if state.status != RolloutStatus.RUNNING:
            return

        # Check stage duration
        now = datetime.now(timezone.utc)
        stage_duration = (now - state.current_stage_started_at).total_seconds() / 3600
        max_stage_duration = state.configuration.stage_duration_hours.get(state.current_stage, 24)

        # Check for automatic stage advancement
        if stage_duration >= max_stage_duration and state.current_stage != RolloutStage.FULL:
            if self._should_advance_stage(rollout_id):
                next_stage = self._get_next_stage(state.current_stage)
                if next_stage:
                    self._advance_to_stage(rollout_id, next_stage, "Automatic stage advancement")

        # Check for rollback conditions
        if self._should_rollback(rollout_id):
            self._trigger_rollback(rollout_id, "Automatic rollback due to performance degradation")

        # Run statistical validation
        validation_interval = state.configuration.statistical_test_interval
        if (not state.last_validation or
            (now - state.last_validation).total_seconds() >= validation_interval):
            self._run_statistical_validation(rollout_id)
            state.last_validation = now

    def _should_advance_stage(self, rollout_id: str) -> bool:
        """Check if rollout should advance to next stage"""

        state = self.active_rollouts[rollout_id]

        # Need minimum sample size
        min_samples = state.configuration.min_sample_size
        if (len(state.champion_metrics) < min_samples or
            len(state.challenger_metrics) < min_samples):
            return False

        # Check recent validation results
        recent_tests = [t for t in state.validation_tests
                       if (datetime.now(timezone.utc) - t.timestamp).total_seconds() < 3600]

        if not recent_tests:
            return False

        # All recent tests should be PASS or INCONCLUSIVE
        critical_failures = [t for t in recent_tests
                           if t.result == ValidationResult.FAIL and t.recommendation == "ROLLBACK"]

        return len(critical_failures) == 0

    def _should_rollback(self, rollout_id: str) -> bool:
        """Check if rollout should be rolled back"""

        state = self.active_rollouts[rollout_id]

        # Check recent validation results
        recent_tests = [t for t in state.validation_tests
                       if (datetime.now(timezone.utc) - t.timestamp).total_seconds() < 1800]  # 30 min

        # Any recent critical failures trigger rollback
        critical_failures = [t for t in recent_tests
                           if t.result == ValidationResult.FAIL and t.recommendation == "ROLLBACK"]

        return len(critical_failures) > 0

    def _run_statistical_validation(self, rollout_id: str):
        """Run statistical validation tests"""

        state = self.active_rollouts[rollout_id]

        if (len(state.champion_metrics) < 10 or len(state.challenger_metrics) < 10):
            return  # Need minimum data

        # Get recent metrics (last hour)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

        recent_champion = [m for m in state.champion_metrics[-50:] if m.timestamp >= recent_cutoff]
        recent_challenger = [m for m in state.challenger_metrics[-50:] if m.timestamp >= recent_cutoff]

        if len(recent_champion) < 5 or len(recent_challenger) < 5:
            return

        # Test key metrics
        metrics_to_test = [
            ('accuracy', [m.accuracy for m in recent_champion], [m.accuracy for m in recent_challenger], True),
            ('cost_per_signal', [m.cost_per_signal for m in recent_champion], [m.cost_per_signal for m in recent_challenger], False),
            ('roi', [m.roi for m in recent_champion], [m.roi for m in recent_challenger], True),
            ('win_loss_ratio', [m.win_loss_ratio for m in recent_champion], [m.win_loss_ratio for m in recent_challenger], True)
        ]

        for metric_name, champion_values, challenger_values, higher_is_better in metrics_to_test:
            try:
                test_result = self.validator.validate_metric_comparison(
                    champion_values, challenger_values, metric_name, higher_is_better
                )

                state.validation_tests.append(test_result)
                self.database.record_validation_test(rollout_id, test_result)

                logger.debug(f"Validation test {rollout_id} {metric_name}: {test_result.result.value} "
                           f"({test_result.recommendation})")

            except Exception as e:
                logger.error(f"Validation test failed for {metric_name}: {e}")

    def _advance_to_stage(self, rollout_id: str, next_stage: RolloutStage, reason: str) -> bool:
        """Advance rollout to next stage"""

        state = self.active_rollouts[rollout_id]
        old_stage = state.current_stage

        # Update stage
        state.current_stage = next_stage
        state.current_stage_started_at = datetime.now(timezone.utc)
        state.current_traffic_percentage = state.configuration.stage_traffic_allocation[next_stage]

        # Save state
        self.database.save_rollout_state(state)

        # Log decision
        self._log_decision(rollout_id, "STAGE_ADVANCE", old_stage, next_stage, reason)

        logger.info(f"Advanced rollout {rollout_id} from {old_stage.value} to {next_stage.value}: {reason}")

        # Trigger callback
        if self.on_stage_change:
            self.on_stage_change(rollout_id, old_stage, next_stage)

        # Check if completed
        if next_stage == RolloutStage.FULL:
            self._complete_rollout(rollout_id, success=True)

        return True

    def _trigger_rollback(self, rollout_id: str, reason: str, automatic: bool = True) -> bool:
        """Trigger rollout rollback"""

        state = self.active_rollouts[rollout_id]
        old_stage = state.current_stage

        # Set rollback state
        state.current_stage = RolloutStage.ROLLBACK
        state.status = RolloutStatus.ROLLED_BACK
        state.current_traffic_percentage = 0.0  # Route all traffic to champion

        # Save state
        self.database.save_rollout_state(state)

        # Log decision
        self._log_decision(rollout_id, "ROLLBACK", old_stage, RolloutStage.ROLLBACK,
                         reason, automatic=automatic)

        logger.warning(f"Rolled back rollout {rollout_id} from {old_stage.value}: {reason}")

        # Trigger callback
        if self.on_rollback:
            self.on_rollback(rollout_id, reason)

        # Complete rollout as failed
        self._complete_rollout(rollout_id, success=False)

        return True

    def _complete_rollout(self, rollout_id: str, success: bool):
        """Complete a rollout"""

        state = self.active_rollouts[rollout_id]

        if success:
            state.status = RolloutStatus.COMPLETED
            logger.info(f"Rollout {rollout_id} completed successfully")
        else:
            state.status = RolloutStatus.FAILED
            logger.warning(f"Rollout {rollout_id} failed")

        # Save final state
        self.database.save_rollout_state(state)

        # Log completion
        self._log_decision(rollout_id, "COMPLETION", state.current_stage, state.current_stage,
                         "Rollout completed", automatic=True,
                         decision_data={"success": success})

        # Trigger callback
        if self.on_completion:
            self.on_completion(rollout_id, success)

    def _get_next_stage(self, current_stage: RolloutStage) -> Optional[RolloutStage]:
        """Get next stage in rollout progression"""

        stage_progression = [
            RolloutStage.SHADOW,
            RolloutStage.CANARY,
            RolloutStage.LIMITED,
            RolloutStage.STAGED,
            RolloutStage.FULL
        ]

        try:
            current_index = stage_progression.index(current_stage)
            if current_index < len(stage_progression) - 1:
                return stage_progression[current_index + 1]
        except ValueError:
            pass

        return None

    def _log_decision(self, rollout_id: str, decision_type: str, from_stage: Optional[RolloutStage],
                     to_stage: Optional[RolloutStage], reason: str, automatic: bool = True,
                     decision_data: Optional[Dict] = None):
        """Log rollout decision"""

        # Add to state decision log
        if rollout_id in self.active_rollouts:
            decision = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'decision_type': decision_type,
                'from_stage': from_stage.value if from_stage else None,
                'to_stage': to_stage.value if to_stage else None,
                'reason': reason,
                'automatic': automatic,
                'decision_data': decision_data
            }
            self.active_rollouts[rollout_id].decision_log.append(decision)

    def get_rollout_status(self, rollout_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive rollout status"""

        if rollout_id not in self.active_rollouts:
            return None

        state = self.active_rollouts[rollout_id]
        now = datetime.now(timezone.utc)

        # Calculate recent performance
        recent_champion = [m for m in state.champion_metrics[-20:]]
        recent_challenger = [m for m in state.challenger_metrics[-20:]]

        champion_performance = {}
        challenger_performance = {}

        if recent_champion:
            champion_performance = {
                'accuracy': statistics.mean([m.accuracy for m in recent_champion]),
                'cost_per_signal': statistics.mean([m.cost_per_signal for m in recent_champion]),
                'roi': statistics.mean([m.roi for m in recent_champion]),
                'win_loss_ratio': statistics.mean([m.win_loss_ratio for m in recent_champion]),
                'sample_size': len(recent_champion)
            }

        if recent_challenger:
            challenger_performance = {
                'accuracy': statistics.mean([m.accuracy for m in recent_challenger]),
                'cost_per_signal': statistics.mean([m.cost_per_signal for m in recent_challenger]),
                'roi': statistics.mean([m.roi for m in recent_challenger]),
                'win_loss_ratio': statistics.mean([m.win_loss_ratio for m in recent_challenger]),
                'sample_size': len(recent_challenger)
            }

        # Recent validation results
        recent_validations = [t for t in state.validation_tests
                            if (now - t.timestamp).total_seconds() < 3600]

        validation_summary = {}
        if recent_validations:
            validation_summary = {
                'total_tests': len(recent_validations),
                'pass_count': len([t for t in recent_validations if t.result == ValidationResult.PASS]),
                'fail_count': len([t for t in recent_validations if t.result == ValidationResult.FAIL]),
                'inconclusive_count': len([t for t in recent_validations if t.result == ValidationResult.INCONCLUSIVE]),
                'latest_recommendations': [t.recommendation for t in recent_validations[-3:]]
            }

        return {
            'rollout_id': rollout_id,
            'champion_version': state.configuration.champion_version,
            'challenger_version': state.configuration.challenger_version,
            'current_stage': state.current_stage.value,
            'status': state.status.value,
            'started_at': state.started_at.isoformat(),
            'current_stage_started_at': state.current_stage_started_at.isoformat(),
            'current_traffic_percentage': state.current_traffic_percentage,
            'total_requests': state.total_requests,
            'challenger_requests': state.challenger_requests,
            'champion_performance': champion_performance,
            'challenger_performance': challenger_performance,
            'validation_summary': validation_summary,
            'decision_log': state.decision_log[-5:],  # Last 5 decisions
            'runtime_hours': (now - state.started_at).total_seconds() / 3600
        }


class TrafficRouter:
    """Simple traffic router for A/B testing"""

    def __init__(self):
        self.routing_seed = random.Random()

    def route_traffic(self, traffic_percentage: float) -> bool:
        """Route traffic based on percentage (True = challenger, False = champion)"""
        return self.routing_seed.random() < traffic_percentage


def create_staged_rollout_manager(config: Optional[Dict] = None) -> StagedRolloutManager:
    """Factory function to create staged rollout manager"""

    if config is None:
        config = {
            'db_path': 'outputs/staged_rollouts.db',
            'validation': {
                'significance_level': 0.05,
                'min_effect_size': 0.1,
                'min_sample_size': 50
            }
        }

    return StagedRolloutManager(config)


if __name__ == "__main__":
    # Example usage
    manager = create_staged_rollout_manager()

    def on_stage_change(rollout_id: str, from_stage: RolloutStage, to_stage: RolloutStage):
        print(f"🚀 Rollout {rollout_id}: {from_stage.value} → {to_stage.value}")

    def on_rollback(rollout_id: str, reason: str):
        print(f"🚨 Rollback {rollout_id}: {reason}")

    def on_completion(rollout_id: str, success: bool):
        print(f"✅ Completed {rollout_id}: {'SUCCESS' if success else 'FAILED'}")

    manager.on_stage_change = on_stage_change
    manager.on_rollback = on_rollback
    manager.on_completion = on_completion

    # Create test rollout
    rollout_id = "test_ifd_v3_1"
    success = manager.create_rollout(
        rollout_id=rollout_id,
        champion_version="IFD_v3.0",
        challenger_version="IFD_v3.1"
    )

    if success:
        print(f"✓ Created rollout: {rollout_id}")

        # Start monitoring
        manager.start_monitoring()
        print("✓ Monitoring started")

        # Simulate some traffic and performance data
        print("Simulating traffic and performance...")

        for i in range(20):
            # Route some requests
            version = "champion" if manager.route_request(rollout_id) == "champion" else "challenger"

            # Create mock performance metrics
            accuracy = 0.72 + random.uniform(-0.05, 0.05)
            if version == "challenger":
                accuracy += 0.03  # Challenger slightly better

            metrics = PerformanceMetrics(
                version=version,
                timestamp=datetime.now(timezone.utc),
                stage=RolloutStage.SHADOW,
                accuracy=accuracy,
                cost_per_signal=4.0 + random.uniform(-0.5, 0.5),
                roi=0.18 + random.uniform(-0.02, 0.02),
                win_loss_ratio=1.6 + random.uniform(-0.1, 0.1),
                signal_volume=random.randint(20, 30),
                false_positive_rate=0.28 - accuracy + 1.0,
                false_negative_rate=0.15,
                precision=accuracy,
                recall=accuracy - 0.05,
                processing_latency=80 + random.uniform(-10, 10),
                error_rate=0.01,
                uptime=99.5,
                total_pnl=100 + random.uniform(-20, 20),
                sharpe_ratio=1.2,
                max_drawdown=0.05
            )

            manager.record_performance(rollout_id, version, metrics)
            time.sleep(1)

        # Show status
        status = manager.get_rollout_status(rollout_id)
        if status:
            print(f"\nRollout Status:")
            print(f"  Stage: {status['current_stage']}")
            print(f"  Status: {status['status']}")
            print(f"  Traffic %: {status['current_traffic_percentage']:.1%}")
            print(f"  Total Requests: {status['total_requests']}")
            print(f"  Champion Performance: {status['champion_performance']}")
            print(f"  Challenger Performance: {status['challenger_performance']}")

        manager.stop_monitoring()
        print("✓ Monitoring stopped")

    else:
        print("✗ Failed to create rollout")
