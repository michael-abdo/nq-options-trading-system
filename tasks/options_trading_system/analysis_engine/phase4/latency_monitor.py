#!/usr/bin/env python3
"""
Latency Monitoring System for IFD v3.0

This module provides comprehensive latency monitoring to ensure the system
meets the <100ms processing target specified in Phase 4 requirements.

Key Features:
- End-to-end latency measurement from data ingestion to signal generation
- Component-level latency breakdown
- Real-time latency alerts and notifications
- Latency trend analysis and statistics
- Performance degradation detection
- Latency SLA compliance monitoring

Monitoring Points:
1. Data Ingestion Latency: Raw data to processed events
2. Analysis Latency: Events to institutional signals
3. Decision Latency: Signals to trading decisions
4. End-to-End Latency: Complete processing pipeline
"""

import os
import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Callable, NamedTuple, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import statistics
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing plotting for latency charts
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    logger.warning("Matplotlib not available - charts disabled")


class LatencyComponent(Enum):
    """Different system components for latency measurement"""
    DATA_INGESTION = "data_ingestion"
    DATA_PROCESSING = "data_processing"
    PRESSURE_ANALYSIS = "pressure_analysis"
    BASELINE_LOOKUP = "baseline_lookup"
    MARKET_MAKING_DETECTION = "market_making_detection"
    CONFIDENCE_SCORING = "confidence_scoring"
    SIGNAL_GENERATION = "signal_generation"
    DECISION_MAKING = "decision_making"
    END_TO_END = "end_to_end"


class LatencyThreshold(Enum):
    """Latency threshold levels"""
    TARGET = "target"      # <100ms target
    WARNING = "warning"    # 80ms warning level
    CRITICAL = "critical"  # 150ms critical level
    SEVERE = "severe"      # 300ms severe level


@dataclass
class LatencyMeasurement:
    """Individual latency measurement"""
    measurement_id: str
    timestamp: datetime
    component: LatencyComponent
    latency_ms: float

    # Context information
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    data_size: Optional[int] = None

    # Associated metadata
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LatencyAlert:
    """Latency threshold alert"""
    alert_id: str
    timestamp: datetime
    component: LatencyComponent
    threshold: LatencyThreshold

    # Measurements
    current_latency: float
    threshold_value: float
    breach_duration: float  # How long threshold has been breached

    # Context
    recent_measurements: List[float]
    trend: str  # "increasing", "decreasing", "stable"
    severity: str  # "low", "medium", "high", "critical"

    # Alert status
    acknowledged: bool = False
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class LatencyStatistics:
    """Statistical summary of latency measurements"""
    component: LatencyComponent
    period_start: datetime
    period_end: datetime

    # Basic statistics
    count: int
    mean: float
    median: float
    p95: float
    p99: float
    min_latency: float
    max_latency: float
    std_dev: float

    # SLA compliance
    target_latency: float
    measurements_under_target: int
    sla_compliance_percentage: float

    # Trend analysis
    trend_direction: str  # "improving", "degrading", "stable"
    trend_confidence: float

    # Performance indicators
    performance_grade: str  # "A", "B", "C", "D", "F"
    recommendations: List[str]


class LatencyTracker:
    """Tracks latency for individual requests through the system"""

    def __init__(self):
        # Active request tracking
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

        # Component timing checkpoints
        self.checkpoints: Dict[str, List[Tuple[LatencyComponent, datetime]]] = defaultdict(list)

    def start_request(self, request_id: str, metadata: Optional[Dict] = None) -> str:
        """
        Start tracking a new request

        Args:
            request_id: Unique request identifier
            metadata: Optional request metadata

        Returns:
            Request ID for tracking
        """
        with self.lock:
            self.active_requests[request_id] = {
                'start_time': datetime.now(timezone.utc),
                'checkpoints': [],
                'metadata': metadata or {}
            }

        logger.debug(f"Started latency tracking for request {request_id}")
        return request_id

    def checkpoint(self, request_id: str, component: LatencyComponent) -> float:
        """
        Record a checkpoint for a component

        Args:
            request_id: Request being tracked
            component: Component that completed processing

        Returns:
            Latency since last checkpoint (or start)
        """
        checkpoint_time = datetime.now(timezone.utc)

        with self.lock:
            if request_id not in self.active_requests:
                logger.warning(f"Request {request_id} not found for checkpoint")
                return 0.0

            request_data = self.active_requests[request_id]

            # Calculate latency since last checkpoint or start
            if request_data['checkpoints']:
                last_checkpoint_time = request_data['checkpoints'][-1][1]
                latency_ms = (checkpoint_time - last_checkpoint_time).total_seconds() * 1000
            else:
                start_time = request_data['start_time']
                latency_ms = (checkpoint_time - start_time).total_seconds() * 1000

            # Record checkpoint
            request_data['checkpoints'].append((component, checkpoint_time))

            logger.debug(f"Checkpoint {component.value} for request {request_id}: {latency_ms:.2f}ms")
            return latency_ms

    def finish_request(self, request_id: str) -> List[LatencyMeasurement]:
        """
        Finish tracking a request and return all measurements

        Args:
            request_id: Request to finish

        Returns:
            List of latency measurements for the request
        """
        with self.lock:
            if request_id not in self.active_requests:
                logger.warning(f"Request {request_id} not found for completion")
                return []

            request_data = self.active_requests[request_id]
            start_time = request_data['start_time']
            checkpoints = request_data['checkpoints']
            metadata = request_data['metadata']

            # Remove from active tracking
            del self.active_requests[request_id]

        # Generate measurements
        measurements = []
        previous_time = start_time

        for i, (component, checkpoint_time) in enumerate(checkpoints):
            latency_ms = (checkpoint_time - previous_time).total_seconds() * 1000

            measurement = LatencyMeasurement(
                measurement_id=f"{request_id}_{component.value}_{i}",
                timestamp=checkpoint_time,
                component=component,
                latency_ms=latency_ms,
                request_id=request_id,
                metadata=metadata.copy()
            )

            measurements.append(measurement)
            previous_time = checkpoint_time

        # Add end-to-end measurement
        if checkpoints:
            end_time = checkpoints[-1][1]
            end_to_end_latency = (end_time - start_time).total_seconds() * 1000

            e2e_measurement = LatencyMeasurement(
                measurement_id=f"{request_id}_end_to_end",
                timestamp=end_time,
                component=LatencyComponent.END_TO_END,
                latency_ms=end_to_end_latency,
                request_id=request_id,
                metadata=metadata.copy()
            )

            measurements.append(e2e_measurement)

        logger.debug(f"Completed latency tracking for request {request_id}: "
                    f"{len(measurements)} measurements")

        return measurements

    def get_active_request_count(self) -> int:
        """Get number of active requests being tracked"""
        with self.lock:
            return len(self.active_requests)


class LatencyDatabase:
    """Database for storing latency measurements and statistics"""

    def __init__(self, db_path: str = "outputs/latency_monitoring.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Latency measurements table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS latency_measurements (
                    measurement_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    component TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    request_id TEXT,
                    session_id TEXT,
                    data_size INTEGER,
                    metadata TEXT,  -- JSON
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Latency alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS latency_alerts (
                    alert_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    component TEXT NOT NULL,
                    threshold_type TEXT NOT NULL,
                    current_latency REAL NOT NULL,
                    threshold_value REAL NOT NULL,
                    breach_duration REAL NOT NULL,
                    severity TEXT NOT NULL,
                    acknowledged BOOLEAN DEFAULT 0,
                    resolved BOOLEAN DEFAULT 0,
                    resolution_time TEXT,
                    trend TEXT,
                    recent_measurements TEXT,  -- JSON array
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Latency statistics snapshots
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS latency_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    count INTEGER NOT NULL,
                    mean REAL NOT NULL,
                    median REAL NOT NULL,
                    p95 REAL NOT NULL,
                    p99 REAL NOT NULL,
                    min_latency REAL NOT NULL,
                    max_latency REAL NOT NULL,
                    std_dev REAL NOT NULL,
                    target_latency REAL NOT NULL,
                    measurements_under_target INTEGER NOT NULL,
                    sla_compliance_percentage REAL NOT NULL,
                    trend_direction TEXT,
                    trend_confidence REAL,
                    performance_grade TEXT,
                    recommendations TEXT,  -- JSON array
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # SLA compliance tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sla_compliance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    component TEXT NOT NULL,
                    total_measurements INTEGER NOT NULL,
                    measurements_under_100ms INTEGER NOT NULL,
                    compliance_percentage REAL NOT NULL,
                    avg_latency REAL NOT NULL,
                    p95_latency REAL NOT NULL,
                    worst_latency REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, component)
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_measurements_timestamp ON latency_measurements(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_measurements_component ON latency_measurements(component)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON latency_alerts(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_statistics_component_period ON latency_statistics(component, period_start)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sla_date_component ON sla_compliance(date, component)")

            conn.commit()

    def store_measurement(self, measurement: LatencyMeasurement):
        """Store latency measurement"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO latency_measurements
                (measurement_id, timestamp, component, latency_ms, request_id,
                 session_id, data_size, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                measurement.measurement_id,
                measurement.timestamp.isoformat(),
                measurement.component.value,
                measurement.latency_ms,
                measurement.request_id,
                measurement.session_id,
                measurement.data_size,
                json.dumps(measurement.metadata) if measurement.metadata else None
            ))
            conn.commit()

    def store_alert(self, alert: LatencyAlert):
        """Store latency alert"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO latency_alerts
                (alert_id, timestamp, component, threshold_type, current_latency,
                 threshold_value, breach_duration, severity, acknowledged, resolved,
                 resolution_time, trend, recent_measurements)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                alert.timestamp.isoformat(),
                alert.component.value,
                alert.threshold.value,
                alert.current_latency,
                alert.threshold_value,
                alert.breach_duration,
                alert.severity,
                alert.acknowledged,
                alert.resolved,
                alert.resolution_time.isoformat() if alert.resolution_time else None,
                alert.trend,
                json.dumps(alert.recent_measurements)
            ))
            conn.commit()

    def get_recent_measurements(self, component: LatencyComponent,
                               hours: int = 1) -> List[LatencyMeasurement]:
        """Get recent measurements for a component"""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT measurement_id, timestamp, component, latency_ms, request_id,
                       session_id, data_size, metadata
                FROM latency_measurements
                WHERE component = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (component.value, since.isoformat()))

            measurements = []
            for row in cursor.fetchall():
                metadata = json.loads(row[7]) if row[7] else {}

                measurement = LatencyMeasurement(
                    measurement_id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    component=LatencyComponent(row[2]),
                    latency_ms=row[3],
                    request_id=row[4],
                    session_id=row[5],
                    data_size=row[6],
                    metadata=metadata
                )
                measurements.append(measurement)

            return measurements


class LatencyAnalyzer:
    """Analyzes latency trends and generates statistics"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Latency thresholds (in milliseconds)
        self.thresholds = {
            LatencyThreshold.TARGET: config.get('target_latency', 100.0),
            LatencyThreshold.WARNING: config.get('warning_latency', 80.0),
            LatencyThreshold.CRITICAL: config.get('critical_latency', 150.0),
            LatencyThreshold.SEVERE: config.get('severe_latency', 300.0)
        }

        # Analysis parameters
        self.min_sample_size = config.get('min_sample_size', 30)
        self.trend_window = config.get('trend_window_hours', 6)

    def analyze_component_latency(self, measurements: List[LatencyMeasurement]) -> LatencyStatistics:
        """
        Analyze latency for a specific component

        Args:
            measurements: List of measurements to analyze

        Returns:
            LatencyStatistics with analysis results
        """

        if not measurements:
            # Return empty statistics
            return LatencyStatistics(
                component=LatencyComponent.END_TO_END,
                period_start=datetime.now(timezone.utc),
                period_end=datetime.now(timezone.utc),
                count=0,
                mean=0.0,
                median=0.0,
                p95=0.0,
                p99=0.0,
                min_latency=0.0,
                max_latency=0.0,
                std_dev=0.0,
                target_latency=self.thresholds[LatencyThreshold.TARGET],
                measurements_under_target=0,
                sla_compliance_percentage=0.0,
                trend_direction="unknown",
                trend_confidence=0.0,
                performance_grade="F",
                recommendations=["No data available"]
            )

        # Extract latency values
        latencies = [m.latency_ms for m in measurements]
        component = measurements[0].component

        # Basic statistics
        count = len(latencies)
        mean_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        std_dev = statistics.stdev(latencies) if count > 1 else 0.0

        # Percentiles
        sorted_latencies = sorted(latencies)
        p95 = self._percentile(sorted_latencies, 95)
        p99 = self._percentile(sorted_latencies, 99)

        # SLA compliance
        target_latency = self.thresholds[LatencyThreshold.TARGET]
        measurements_under_target = len([l for l in latencies if l <= target_latency])
        sla_compliance = (measurements_under_target / count) * 100 if count > 0 else 0.0

        # Trend analysis
        trend_direction, trend_confidence = self._analyze_trend(latencies)

        # Performance grading
        performance_grade = self._calculate_performance_grade(mean_latency, p95, sla_compliance)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            component, mean_latency, p95, sla_compliance, trend_direction
        )

        # Time period
        period_start = min(m.timestamp for m in measurements)
        period_end = max(m.timestamp for m in measurements)

        return LatencyStatistics(
            component=component,
            period_start=period_start,
            period_end=period_end,
            count=count,
            mean=mean_latency,
            median=median_latency,
            p95=p95,
            p99=p99,
            min_latency=min_latency,
            max_latency=max_latency,
            std_dev=std_dev,
            target_latency=target_latency,
            measurements_under_target=measurements_under_target,
            sla_compliance_percentage=sla_compliance,
            trend_direction=trend_direction,
            trend_confidence=trend_confidence,
            performance_grade=performance_grade,
            recommendations=recommendations
        )

    def check_threshold_breaches(self, measurements: List[LatencyMeasurement]) -> List[LatencyAlert]:
        """Check for threshold breaches and generate alerts"""

        if len(measurements) < 5:  # Need minimum measurements
            return []

        alerts = []
        recent_latencies = [m.latency_ms for m in measurements[-10:]]  # Last 10 measurements
        avg_recent_latency = statistics.mean(recent_latencies)

        component = measurements[0].component

        # Check each threshold
        for threshold_type, threshold_value in self.thresholds.items():
            if avg_recent_latency > threshold_value:
                # Calculate breach duration (simplified)
                breach_duration = 0.0
                for i in range(len(measurements) - 1, -1, -1):
                    if measurements[i].latency_ms <= threshold_value:
                        break
                    breach_duration += 1.0  # Count measurements above threshold

                # Determine severity
                severity = self._determine_severity(avg_recent_latency, threshold_value, threshold_type)

                # Analyze trend
                trend = self._analyze_trend(recent_latencies)[0]

                alert = LatencyAlert(
                    alert_id=f"{component.value}_{threshold_type.value}_{int(time.time())}",
                    timestamp=datetime.now(timezone.utc),
                    component=component,
                    threshold=threshold_type,
                    current_latency=avg_recent_latency,
                    threshold_value=threshold_value,
                    breach_duration=breach_duration,
                    recent_measurements=recent_latencies,
                    trend=trend,
                    severity=severity
                )

                alerts.append(alert)

        return alerts

    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile of sorted values"""
        if not sorted_values:
            return 0.0

        index = (percentile / 100) * (len(sorted_values) - 1)

        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            fraction = index - int(index)
            return lower + fraction * (upper - lower)

    def _analyze_trend(self, latencies: List[float]) -> Tuple[str, float]:
        """Analyze latency trend"""

        if len(latencies) < 3:
            return "unknown", 0.0

        # Simple linear trend analysis
        n = len(latencies)
        x = list(range(n))

        # Calculate slope using least squares
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(latencies)

        numerator = sum((x[i] - x_mean) * (latencies[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable", 0.0

        slope = numerator / denominator

        # Determine trend direction
        if abs(slope) < 0.5:  # Less than 0.5ms change per measurement
            direction = "stable"
        elif slope > 0:
            direction = "degrading"
        else:
            direction = "improving"

        # Confidence based on R-squared
        y_pred = [y_mean + slope * (x[i] - x_mean) for i in range(n)]
        ss_res = sum((latencies[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((latencies[i] - y_mean) ** 2 for i in range(n))

        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        confidence = max(min(r_squared, 1.0), 0.0)

        return direction, confidence

    def _calculate_performance_grade(self, mean_latency: float, p95: float,
                                   sla_compliance: float) -> str:
        """Calculate performance grade A-F"""

        target = self.thresholds[LatencyThreshold.TARGET]

        # Grade based on multiple factors
        grade_score = 0

        # Mean latency factor (40% weight)
        if mean_latency <= target * 0.5:
            grade_score += 40
        elif mean_latency <= target * 0.7:
            grade_score += 35
        elif mean_latency <= target:
            grade_score += 25
        elif mean_latency <= target * 1.5:
            grade_score += 15
        else:
            grade_score += 0

        # P95 latency factor (35% weight)
        if p95 <= target:
            grade_score += 35
        elif p95 <= target * 1.2:
            grade_score += 25
        elif p95 <= target * 1.5:
            grade_score += 15
        else:
            grade_score += 0

        # SLA compliance factor (25% weight)
        if sla_compliance >= 95:
            grade_score += 25
        elif sla_compliance >= 90:
            grade_score += 20
        elif sla_compliance >= 80:
            grade_score += 15
        elif sla_compliance >= 70:
            grade_score += 10
        else:
            grade_score += 0

        # Convert to letter grade
        if grade_score >= 90:
            return "A"
        elif grade_score >= 80:
            return "B"
        elif grade_score >= 70:
            return "C"
        elif grade_score >= 60:
            return "D"
        else:
            return "F"

    def _determine_severity(self, current_latency: float, threshold_value: float,
                          threshold_type: LatencyThreshold) -> str:
        """Determine alert severity"""

        breach_ratio = current_latency / threshold_value

        if threshold_type == LatencyThreshold.SEVERE or breach_ratio > 3.0:
            return "critical"
        elif threshold_type == LatencyThreshold.CRITICAL or breach_ratio > 2.0:
            return "high"
        elif threshold_type == LatencyThreshold.WARNING or breach_ratio > 1.5:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(self, component: LatencyComponent, mean_latency: float,
                                p95: float, sla_compliance: float, trend: str) -> List[str]:
        """Generate performance recommendations"""

        recommendations = []
        target = self.thresholds[LatencyThreshold.TARGET]

        if mean_latency > target:
            recommendations.append(f"Mean latency ({mean_latency:.1f}ms) exceeds target ({target}ms)")

        if p95 > target * 1.2:
            recommendations.append(f"P95 latency ({p95:.1f}ms) indicates performance issues")

        if sla_compliance < 95:
            recommendations.append(f"SLA compliance ({sla_compliance:.1f}%) below target (95%)")

        if trend == "degrading":
            recommendations.append("Latency trend is degrading - investigate performance issues")

        # Component-specific recommendations
        if component == LatencyComponent.DATA_INGESTION:
            if mean_latency > 30:
                recommendations.append("Consider optimizing data ingestion pipeline")
        elif component == LatencyComponent.PRESSURE_ANALYSIS:
            if mean_latency > 40:
                recommendations.append("Optimize pressure analysis algorithms")
        elif component == LatencyComponent.BASELINE_LOOKUP:
            if mean_latency > 20:
                recommendations.append("Consider caching baseline calculations")
        elif component == LatencyComponent.END_TO_END:
            if mean_latency > target:
                recommendations.append("End-to-end latency exceeds target - review entire pipeline")

        if not recommendations:
            recommendations.append("Performance is meeting targets")

        return recommendations


class LatencyMonitor:
    """
    Main latency monitoring system

    Features:
    - Real-time latency tracking
    - Threshold monitoring and alerting
    - Performance analysis and reporting
    - SLA compliance monitoring
    - Integration with other monitoring systems
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize latency monitor

        Args:
            config: Monitor configuration
        """
        self.config = config
        self.database = LatencyDatabase(config.get('db_path', 'outputs/latency_monitoring.db'))
        self.analyzer = LatencyAnalyzer(config.get('analysis', {}))
        self.tracker = LatencyTracker()

        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread = None

        # Alert management
        self.active_alerts: Dict[str, LatencyAlert] = {}
        self.alert_lock = threading.Lock()

        # Statistics cache
        self.stats_cache: Dict[LatencyComponent, LatencyStatistics] = {}
        self.cache_expiry = timedelta(minutes=5)
        self.last_cache_update = {}

        # Callbacks
        self.on_threshold_breach: Optional[Callable[[LatencyAlert], None]] = None
        self.on_performance_degradation: Optional[Callable[[LatencyComponent, str], None]] = None

        logger.info("Latency Monitor initialized")

    def start_monitoring(self):
        """Start latency monitoring"""
        if self.monitoring_active:
            logger.warning("Latency monitoring already active")
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="LatencyMonitor"
        )
        self.monitor_thread.start()

        logger.info("Latency monitoring started")

    def stop_monitoring(self):
        """Stop latency monitoring"""
        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        logger.info("Latency monitoring stopped")

    def track_request(self, request_id: str, metadata: Optional[Dict] = None) -> str:
        """Start tracking latency for a request"""
        return self.tracker.start_request(request_id, metadata)

    def checkpoint(self, request_id: str, component: LatencyComponent) -> float:
        """Record a component checkpoint"""
        latency = self.tracker.checkpoint(request_id, component)

        # Store measurement immediately for real-time monitoring
        measurement = LatencyMeasurement(
            measurement_id=f"{request_id}_{component.value}_{int(time.time() * 1000)}",
            timestamp=datetime.now(timezone.utc),
            component=component,
            latency_ms=latency,
            request_id=request_id
        )

        self.database.store_measurement(measurement)

        # Check for immediate threshold breaches
        self._check_immediate_breach(measurement)

        return latency

    def finish_request(self, request_id: str) -> List[LatencyMeasurement]:
        """Finish tracking a request"""
        measurements = self.tracker.finish_request(request_id)

        # Store all measurements
        for measurement in measurements:
            self.database.store_measurement(measurement)

        return measurements

    def get_component_statistics(self, component: LatencyComponent,
                                hours: int = 1, force_refresh: bool = False) -> LatencyStatistics:
        """Get statistics for a component"""

        # Check cache first
        if not force_refresh and component in self.stats_cache:
            if component in self.last_cache_update:
                age = datetime.now(timezone.utc) - self.last_cache_update[component]
                if age < self.cache_expiry:
                    return self.stats_cache[component]

        # Get recent measurements
        measurements = self.database.get_recent_measurements(component, hours)

        # Analyze
        statistics = self.analyzer.analyze_component_latency(measurements)

        # Cache results
        self.stats_cache[component] = statistics
        self.last_cache_update[component] = datetime.now(timezone.utc)

        return statistics

    def get_system_overview(self) -> Dict[str, Any]:
        """Get overview of system latency performance"""

        overview = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'components': {},
            'overall_status': 'unknown',
            'active_alerts': len(self.active_alerts),
            'active_requests': self.tracker.get_active_request_count()
        }

        # Get statistics for all components
        overall_grades = []
        for component in LatencyComponent:
            try:
                stats = self.get_component_statistics(component, hours=1)
                overview['components'][component.value] = {
                    'mean_latency': stats.mean,
                    'p95_latency': stats.p95,
                    'sla_compliance': stats.sla_compliance_percentage,
                    'performance_grade': stats.performance_grade,
                    'trend': stats.trend_direction
                }

                # Track grades for overall status
                grade_scores = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'F': 1}
                overall_grades.append(grade_scores.get(stats.performance_grade, 1))

            except Exception as e:
                logger.warning(f"Failed to get statistics for {component.value}: {e}")
                overview['components'][component.value] = {
                    'error': str(e)
                }

        # Calculate overall status
        if overall_grades:
            avg_grade = statistics.mean(overall_grades)
            if avg_grade >= 4.5:
                overview['overall_status'] = 'excellent'
            elif avg_grade >= 3.5:
                overview['overall_status'] = 'good'
            elif avg_grade >= 2.5:
                overview['overall_status'] = 'fair'
            elif avg_grade >= 1.5:
                overview['overall_status'] = 'poor'
            else:
                overview['overall_status'] = 'critical'

        return overview

    def _monitoring_loop(self):
        """Main monitoring loop"""

        while self.monitoring_active:
            try:
                # Analyze recent performance for each component
                for component in LatencyComponent:
                    try:
                        measurements = self.database.get_recent_measurements(component, hours=1)

                        if len(measurements) >= 10:  # Need minimum measurements
                            # Check for threshold breaches
                            alerts = self.analyzer.check_threshold_breaches(measurements)

                            for alert in alerts:
                                self._handle_alert(alert)

                    except Exception as e:
                        logger.error(f"Error monitoring component {component.value}: {e}")

                # Sleep until next monitoring cycle
                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(30)  # Short sleep on error

    def _check_immediate_breach(self, measurement: LatencyMeasurement):
        """Check for immediate threshold breach"""

        target_latency = self.analyzer.thresholds[LatencyThreshold.TARGET]

        if measurement.latency_ms > target_latency:
            logger.warning(f"Immediate latency breach: {measurement.component.value} "
                          f"{measurement.latency_ms:.1f}ms > {target_latency}ms")

    def _handle_alert(self, alert: LatencyAlert):
        """Handle a latency alert"""

        with self.alert_lock:
            # Check if this is a new alert or update to existing
            existing_alert_key = f"{alert.component.value}_{alert.threshold.value}"

            if existing_alert_key not in self.active_alerts:
                # New alert
                self.active_alerts[existing_alert_key] = alert
                self.database.store_alert(alert)

                logger.warning(f"Latency alert: {alert.component.value} "
                              f"{alert.current_latency:.1f}ms > {alert.threshold_value}ms "
                              f"({alert.severity})")

                # Trigger callback
                if self.on_threshold_breach:
                    self.on_threshold_breach(alert)

            else:
                # Update existing alert
                existing_alert = self.active_alerts[existing_alert_key]
                existing_alert.current_latency = alert.current_latency
                existing_alert.breach_duration = alert.breach_duration
                existing_alert.recent_measurements = alert.recent_measurements
                existing_alert.trend = alert.trend

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge a latency alert"""

        with self.alert_lock:
            for alert in self.active_alerts.values():
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    self.database.store_alert(alert)
                    logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                    return True

        return False

    def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report"""

        report = {
            'report_timestamp': datetime.now(timezone.utc).isoformat(),
            'report_period_hours': hours,
            'components': {},
            'summary': {},
            'recommendations': []
        }

        all_stats = []

        # Analyze each component
        for component in LatencyComponent:
            try:
                stats = self.get_component_statistics(component, hours, force_refresh=True)

                report['components'][component.value] = asdict(stats)
                all_stats.append(stats)

            except Exception as e:
                logger.error(f"Failed to analyze component {component.value}: {e}")
                report['components'][component.value] = {'error': str(e)}

        # Generate summary
        if all_stats:
            end_to_end_stats = [s for s in all_stats if s.component == LatencyComponent.END_TO_END]

            if end_to_end_stats:
                e2e = end_to_end_stats[0]
                report['summary'] = {
                    'overall_mean_latency': e2e.mean,
                    'overall_p95_latency': e2e.p95,
                    'overall_sla_compliance': e2e.sla_compliance_percentage,
                    'overall_performance_grade': e2e.performance_grade,
                    'target_latency': e2e.target_latency,
                    'measurements_analyzed': e2e.count
                }

            # Collect all recommendations
            all_recommendations = []
            for stats in all_stats:
                all_recommendations.extend(stats.recommendations)

            # Deduplicate and prioritize
            unique_recommendations = list(set(all_recommendations))
            report['recommendations'] = unique_recommendations

        return report


def create_latency_monitor(config: Optional[Dict] = None) -> LatencyMonitor:
    """Factory function to create latency monitor"""

    if config is None:
        config = {
            'db_path': 'outputs/latency_monitoring.db',
            'analysis': {
                'target_latency': 100.0,    # <100ms target
                'warning_latency': 80.0,    # 80ms warning
                'critical_latency': 150.0,  # 150ms critical
                'severe_latency': 300.0,    # 300ms severe
                'min_sample_size': 30,
                'trend_window_hours': 6
            }
        }

    return LatencyMonitor(config)


if __name__ == "__main__":
    # Example usage
    monitor = create_latency_monitor()

    def on_threshold_breach(alert: LatencyAlert):
        print(f"🚨 Latency Alert: {alert.component.value} {alert.current_latency:.1f}ms "
              f"({alert.severity} - {alert.trend})")

    def on_performance_degradation(component: LatencyComponent, description: str):
        print(f"⚠️ Performance Degradation: {component.value} - {description}")

    monitor.on_threshold_breach = on_threshold_breach
    monitor.on_performance_degradation = on_performance_degradation

    # Start monitoring
    monitor.start_monitoring()
    print("✓ Latency monitoring started")

    # Simulate some requests with latency tracking
    print("\nSimulating request processing...")

    for i in range(10):
        request_id = f"test_request_{i}"

        # Start tracking
        monitor.track_request(request_id, {'test_run': i})

        # Simulate processing through components
        time.sleep(0.01)  # 10ms
        monitor.checkpoint(request_id, LatencyComponent.DATA_INGESTION)

        time.sleep(0.03)  # 30ms
        monitor.checkpoint(request_id, LatencyComponent.PRESSURE_ANALYSIS)

        time.sleep(0.02)  # 20ms
        monitor.checkpoint(request_id, LatencyComponent.BASELINE_LOOKUP)

        time.sleep(0.015)  # 15ms
        monitor.checkpoint(request_id, LatencyComponent.CONFIDENCE_SCORING)

        time.sleep(0.01)  # 10ms
        monitor.checkpoint(request_id, LatencyComponent.SIGNAL_GENERATION)

        # Finish tracking
        measurements = monitor.finish_request(request_id)

        if measurements:
            e2e = [m for m in measurements if m.component == LatencyComponent.END_TO_END]
            if e2e:
                print(f"  Request {i}: {e2e[0].latency_ms:.1f}ms end-to-end")

    # Wait a moment for monitoring
    time.sleep(5)

    # Get system overview
    overview = monitor.get_system_overview()
    print(f"\nSystem Overview:")
    print(f"  Overall Status: {overview['overall_status']}")
    print(f"  Active Alerts: {overview['active_alerts']}")

    for component, stats in overview['components'].items():
        if 'mean_latency' in stats:
            print(f"  {component}: {stats['mean_latency']:.1f}ms avg, "
                  f"P95: {stats['p95_latency']:.1f}ms, "
                  f"Grade: {stats['performance_grade']}")

    # Generate performance report
    report = monitor.generate_performance_report(hours=1)

    if report['summary']:
        print(f"\nPerformance Summary:")
        summary = report['summary']
        print(f"  Mean Latency: {summary.get('overall_mean_latency', 0):.1f}ms")
        print(f"  P95 Latency: {summary.get('overall_p95_latency', 0):.1f}ms")
        print(f"  SLA Compliance: {summary.get('overall_sla_compliance', 0):.1f}%")
        print(f"  Performance Grade: {summary.get('overall_performance_grade', 'N/A')}")

    if report['recommendations']:
        print(f"\nRecommendations:")
        for rec in report['recommendations'][:3]:  # Top 3
            print(f"  - {rec}")

    monitor.stop_monitoring()
    print("✓ Latency monitoring stopped")
