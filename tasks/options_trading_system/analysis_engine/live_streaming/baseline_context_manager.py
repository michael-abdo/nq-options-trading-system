#!/usr/bin/env python3
"""
Real-time Baseline Context Manager for IFD v3.0

This module provides real-time baseline context updates for institutional flow detection,
enabling dynamic baseline calculation and anomaly detection as new data arrives.

Key Features:
- Real-time baseline updates with sliding windows
- Incremental statistics calculation for efficiency
- Multi-strike baseline management
- Historical baseline persistence
- Anomaly detection with dynamic thresholds
- Memory-efficient storage with automatic cleanup

Architecture:
Live Pressure Metrics → Incremental Baseline Updates → Anomaly Detection → Updated Context
"""

import os
import sys
import logging
import threading
import time
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
import statistics
import json
import math

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(current_dir)))

from utils.timezone_utils import get_eastern_time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BaselineStats:
    """Statistical baseline for a specific strike and option type"""
    strike: float
    option_type: str

    # Core statistics
    mean_pressure: float
    std_pressure: float
    min_pressure: float
    max_pressure: float

    # Percentiles
    percentile_25: float
    percentile_50: float
    percentile_75: float
    percentile_90: float
    percentile_95: float

    # Data quality
    sample_count: int
    data_quality: float
    last_updated: datetime

    # Incremental calculation state
    sum_pressure: float = 0.0
    sum_squared: float = 0.0
    observations: List[float] = field(default_factory=list)

@dataclass
class BaselineContext:
    """Current baseline context for anomaly detection"""
    baseline: BaselineStats
    current_pressure: float

    # Anomaly indicators
    z_score: float
    percentile_rank: float
    anomaly_detected: bool
    anomaly_severity: str  # 'none', 'mild', 'moderate', 'severe', 'extreme'

    # Context metrics
    confidence: float
    trend_direction: str  # 'up', 'down', 'stable'
    volatility_regime: str  # 'low', 'normal', 'high'

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class IncrementalStatsCalculator:
    """Efficiently calculates statistics incrementally as new data arrives"""

    def __init__(self, max_observations: int = 2000):
        """Initialize incremental stats calculator

        Args:
            max_observations: Maximum observations to keep in memory
        """
        self.max_observations = max_observations
        self.observations = deque(maxlen=max_observations)

        # Running statistics
        self.count = 0
        self.sum_x = 0.0
        self.sum_x2 = 0.0
        self.min_val = float('inf')
        self.max_val = float('-inf')

    def add_observation(self, value: float):
        """Add new observation and update statistics"""
        # Handle case where we're replacing an old observation
        if len(self.observations) == self.max_observations:
            old_value = self.observations[0]
            self.sum_x -= old_value
            self.sum_x2 -= old_value * old_value
            self.count -= 1

        # Add new observation
        self.observations.append(value)
        self.sum_x += value
        self.sum_x2 += value * value
        self.count += 1

        # Update min/max
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)

        # Recalculate min/max if we just removed the extreme value
        if len(self.observations) == self.max_observations:
            self.min_val = min(self.observations)
            self.max_val = max(self.observations)

    def get_statistics(self) -> Dict[str, float]:
        """Get current statistics"""
        if self.count == 0:
            return {
                'mean': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0,
                'count': 0
            }

        mean = self.sum_x / self.count

        if self.count > 1:
            variance = (self.sum_x2 - (self.sum_x * self.sum_x) / self.count) / (self.count - 1)
            std = math.sqrt(max(variance, 0))
        else:
            std = 0.0

        return {
            'mean': mean,
            'std': std,
            'min': self.min_val if self.min_val != float('inf') else 0.0,
            'max': self.max_val if self.max_val != float('-inf') else 0.0,
            'count': self.count
        }

    def get_percentiles(self) -> Dict[int, float]:
        """Calculate percentiles from current observations"""
        if len(self.observations) < 5:
            # Not enough data for meaningful percentiles
            obs_list = list(self.observations)
            if not obs_list:
                return {25: 0.0, 50: 0.0, 75: 0.0, 90: 0.0, 95: 0.0}

            # Use available data
            sorted_obs = sorted(obs_list)
            return {
                25: sorted_obs[len(sorted_obs) // 4] if len(sorted_obs) > 1 else sorted_obs[0],
                50: sorted_obs[len(sorted_obs) // 2],
                75: sorted_obs[3 * len(sorted_obs) // 4] if len(sorted_obs) > 3 else sorted_obs[-1],
                90: sorted_obs[9 * len(sorted_obs) // 10] if len(sorted_obs) > 9 else sorted_obs[-1],
                95: sorted_obs[19 * len(sorted_obs) // 20] if len(sorted_obs) > 19 else sorted_obs[-1]
            }

        # Calculate percentiles using quantiles
        sorted_obs = sorted(self.observations)
        n = len(sorted_obs)

        percentiles = {}
        for p in [25, 50, 75, 90, 95]:
            index = (p / 100.0) * (n - 1)
            lower_index = int(index)
            upper_index = min(lower_index + 1, n - 1)

            if lower_index == upper_index:
                percentiles[p] = sorted_obs[lower_index]
            else:
                # Linear interpolation
                fraction = index - lower_index
                percentiles[p] = (sorted_obs[lower_index] * (1 - fraction) +
                                sorted_obs[upper_index] * fraction)

        return percentiles

class BaselineDatabase:
    """Efficient database operations for baseline persistence"""

    def __init__(self, db_path: str):
        """Initialize baseline database

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database schema for baseline storage"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Baseline statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS baseline_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strike REAL NOT NULL,
                    option_type TEXT NOT NULL,
                    mean_pressure REAL NOT NULL,
                    std_pressure REAL NOT NULL,
                    min_pressure REAL NOT NULL,
                    max_pressure REAL NOT NULL,
                    percentile_25 REAL NOT NULL,
                    percentile_50 REAL NOT NULL,
                    percentile_75 REAL NOT NULL,
                    percentile_90 REAL NOT NULL,
                    percentile_95 REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    data_quality REAL NOT NULL,
                    last_updated TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(strike, option_type)
                )
            """)

            # Historical pressure observations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pressure_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strike REAL NOT NULL,
                    option_type TEXT NOT NULL,
                    pressure_ratio REAL NOT NULL,
                    volume REAL NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    date_key TEXT NOT NULL
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_baseline_strike ON baseline_statistics(strike, option_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_strike_date ON pressure_observations(strike, option_type, date_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_timestamp ON pressure_observations(timestamp)")

            conn.commit()

    def save_baseline(self, baseline: BaselineStats):
        """Save baseline statistics to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO baseline_statistics
                (strike, option_type, mean_pressure, std_pressure, min_pressure, max_pressure,
                 percentile_25, percentile_50, percentile_75, percentile_90, percentile_95,
                 sample_count, data_quality, last_updated, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                baseline.strike, baseline.option_type,
                baseline.mean_pressure, baseline.std_pressure,
                baseline.min_pressure, baseline.max_pressure,
                baseline.percentile_25, baseline.percentile_50, baseline.percentile_75,
                baseline.percentile_90, baseline.percentile_95,
                baseline.sample_count, baseline.data_quality,
                baseline.last_updated.isoformat(),
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()

    def load_baseline(self, strike: float, option_type: str) -> Optional[BaselineStats]:
        """Load baseline statistics from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT mean_pressure, std_pressure, min_pressure, max_pressure,
                       percentile_25, percentile_50, percentile_75, percentile_90, percentile_95,
                       sample_count, data_quality, last_updated
                FROM baseline_statistics
                WHERE strike = ? AND option_type = ?
            """, (strike, option_type))

            row = cursor.fetchone()
            if not row:
                return None

            return BaselineStats(
                strike=strike,
                option_type=option_type,
                mean_pressure=row[0],
                std_pressure=row[1],
                min_pressure=row[2],
                max_pressure=row[3],
                percentile_25=row[4],
                percentile_50=row[5],
                percentile_75=row[6],
                percentile_90=row[7],
                percentile_95=row[8],
                sample_count=row[9],
                data_quality=row[10],
                last_updated=datetime.fromisoformat(row[11])
            )

    def save_observation(self, strike: float, option_type: str, pressure_ratio: float,
                        volume: float, confidence: float, timestamp: datetime):
        """Save pressure observation for historical context"""
        date_key = timestamp.strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pressure_observations
                (strike, option_type, pressure_ratio, volume, confidence, timestamp, date_key)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (strike, option_type, pressure_ratio, volume, confidence,
                  timestamp.isoformat(), date_key))
            conn.commit()

    def cleanup_old_observations(self, days_to_keep: int = 30):
        """Clean up old observations to manage database size"""
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pressure_observations WHERE date_key < ?", (cutoff_date,))
            deleted_count = cursor.rowcount
            conn.commit()

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old pressure observations")

class RealTimeBaselineManager:
    """Manages real-time baseline context updates for multiple strikes"""

    def __init__(self, db_path: str, lookback_days: int = 20):
        """Initialize real-time baseline manager

        Args:
            db_path: Path to baseline database
            lookback_days: Days of history for baseline calculation
        """
        self.db_path = db_path
        self.lookback_days = lookback_days

        # Database and components
        self.database = BaselineDatabase(db_path)

        # Incremental calculators per strike
        self.calculators = defaultdict(lambda: IncrementalStatsCalculator())

        # Baseline cache
        self.baseline_cache = {}
        self.cache_expiry = timedelta(hours=1)

        # Recent observations for trend analysis
        self.recent_observations = defaultdict(lambda: deque(maxlen=20))

        # Threading
        self.lock = threading.RLock()

        # Performance tracking
        self.updates_processed = 0
        self.anomalies_detected = 0

        # Load existing baselines
        self._initialize_baselines()

        logger.info(f"Real-time baseline manager initialized with {lookback_days} days lookback")

    def _initialize_baselines(self):
        """Initialize baselines from existing database"""
        # This would load recent baselines from database
        # For now, we'll initialize with empty calculators
        logger.info("Baseline manager initialized with empty state")

    def update_baseline(self, strike: float, option_type: str, pressure_ratio: float,
                       volume: float, confidence: float, timestamp: datetime) -> BaselineContext:
        """
        Update baseline with new pressure observation and return context

        Args:
            strike: Option strike price
            option_type: 'C' for calls, 'P' for puts
            pressure_ratio: New pressure ratio observation
            volume: Associated volume
            confidence: Confidence in the observation
            timestamp: Observation timestamp

        Returns:
            Updated baseline context with anomaly detection
        """
        with self.lock:
            self.updates_processed += 1

            # Get or create calculator for this strike
            key = f"{strike}_{option_type}"
            calculator = self.calculators[key]

            # Add observation to incremental calculator
            calculator.add_observation(pressure_ratio)

            # Add to recent observations for trend analysis
            self.recent_observations[key].append({
                'pressure': pressure_ratio,
                'timestamp': timestamp,
                'volume': volume,
                'confidence': confidence
            })

            # Calculate updated baseline statistics
            stats = calculator.get_statistics()
            percentiles = calculator.get_percentiles()

            # Create baseline stats object
            baseline = BaselineStats(
                strike=strike,
                option_type=option_type,
                mean_pressure=stats['mean'],
                std_pressure=stats['std'],
                min_pressure=stats['min'],
                max_pressure=stats['max'],
                percentile_25=percentiles[25],
                percentile_50=percentiles[50],
                percentile_75=percentiles[75],
                percentile_90=percentiles[90],
                percentile_95=percentiles[95],
                sample_count=stats['count'],
                data_quality=confidence,  # Use current confidence as quality proxy
                last_updated=timestamp
            )

            # Calculate baseline context
            context = self._calculate_baseline_context(baseline, pressure_ratio, key)

            # Save to database (periodic saves to avoid overhead)
            if self.updates_processed % 10 == 0:  # Save every 10 updates
                self.database.save_baseline(baseline)
                self.database.save_observation(strike, option_type, pressure_ratio,
                                             volume, confidence, timestamp)

            # Update cache
            self.baseline_cache[key] = (baseline, timestamp)

            return context

    def _calculate_baseline_context(self, baseline: BaselineStats, current_pressure: float,
                                  key: str) -> BaselineContext:
        """Calculate baseline context with anomaly detection"""

        # Calculate z-score
        if baseline.std_pressure > 0:
            z_score = (current_pressure - baseline.mean_pressure) / baseline.std_pressure
        else:
            z_score = 0.0

        # Calculate percentile rank
        percentile_rank = self._calculate_percentile_rank(current_pressure, baseline)

        # Detect anomaly and severity
        anomaly_detected, severity = self._detect_anomaly(z_score, percentile_rank)

        if anomaly_detected:
            self.anomalies_detected += 1

        # Calculate trend direction
        trend_direction = self._calculate_trend(key)

        # Calculate volatility regime
        volatility_regime = self._calculate_volatility_regime(baseline)

        # Calculate confidence based on sample size and data quality
        confidence = self._calculate_context_confidence(baseline)

        return BaselineContext(
            baseline=baseline,
            current_pressure=current_pressure,
            z_score=z_score,
            percentile_rank=percentile_rank,
            anomaly_detected=anomaly_detected,
            anomaly_severity=severity,
            confidence=confidence,
            trend_direction=trend_direction,
            volatility_regime=volatility_regime,
            timestamp=baseline.last_updated
        )

    def _calculate_percentile_rank(self, value: float, baseline: BaselineStats) -> float:
        """Calculate percentile rank of current value against baseline"""
        if value <= baseline.percentile_25:
            return 25.0
        elif value <= baseline.percentile_50:
            return 50.0
        elif value <= baseline.percentile_75:
            return 75.0
        elif value <= baseline.percentile_90:
            return 90.0
        elif value <= baseline.percentile_95:
            return 95.0
        else:
            return 99.0

    def _detect_anomaly(self, z_score: float, percentile_rank: float) -> Tuple[bool, str]:
        """Detect anomaly and determine severity"""
        abs_z = abs(z_score)

        if abs_z >= 3.0 or percentile_rank >= 99.0:
            return True, 'extreme'
        elif abs_z >= 2.5 or percentile_rank >= 95.0:
            return True, 'severe'
        elif abs_z >= 2.0 or percentile_rank >= 90.0:
            return True, 'moderate'
        elif abs_z >= 1.5 or percentile_rank >= 75.0:
            return True, 'mild'
        else:
            return False, 'none'

    def _calculate_trend(self, key: str) -> str:
        """Calculate trend direction from recent observations"""
        observations = self.recent_observations[key]
        if len(observations) < 3:
            return 'stable'

        # Calculate simple trend over recent observations
        recent_pressures = [obs['pressure'] for obs in list(observations)[-5:]]

        if len(recent_pressures) >= 3:
            # Linear regression slope
            n = len(recent_pressures)
            x_mean = (n - 1) / 2
            y_mean = statistics.mean(recent_pressures)

            numerator = sum((i - x_mean) * (p - y_mean) for i, p in enumerate(recent_pressures))
            denominator = sum((i - x_mean) ** 2 for i in range(n))

            if denominator > 0:
                slope = numerator / denominator
                if slope > 0.1:
                    return 'up'
                elif slope < -0.1:
                    return 'down'

        return 'stable'

    def _calculate_volatility_regime(self, baseline: BaselineStats) -> str:
        """Determine volatility regime based on baseline statistics"""
        if baseline.sample_count < 10:
            return 'normal'

        # Use coefficient of variation as volatility measure
        if baseline.mean_pressure > 0:
            cv = baseline.std_pressure / baseline.mean_pressure

            if cv > 0.5:
                return 'high'
            elif cv < 0.2:
                return 'low'
            else:
                return 'normal'
        else:
            return 'normal'

    def _calculate_context_confidence(self, baseline: BaselineStats) -> float:
        """Calculate confidence in baseline context"""
        # Base confidence on sample size
        sample_confidence = min(baseline.sample_count / 100.0, 1.0)

        # Adjust for data quality
        quality_confidence = baseline.data_quality

        # Combine with weights
        confidence = sample_confidence * 0.6 + quality_confidence * 0.4

        return min(max(confidence, 0.0), 1.0)

    def get_baseline_context(self, strike: float, option_type: str) -> Optional[BaselineContext]:
        """Get current baseline context for a strike without updating"""
        key = f"{strike}_{option_type}"

        with self.lock:
            if key in self.baseline_cache:
                baseline, timestamp = self.baseline_cache[key]

                # Check if cache is still valid
                if datetime.now(timezone.utc) - timestamp < self.cache_expiry:
                    # Create context with cached baseline
                    return self._calculate_baseline_context(baseline, baseline.mean_pressure, key)

            # Try loading from database
            baseline = self.database.load_baseline(strike, option_type)
            if baseline:
                return self._calculate_baseline_context(baseline, baseline.mean_pressure, key)

        return None

    def get_manager_stats(self) -> Dict[str, Any]:
        """Get comprehensive manager statistics"""
        with self.lock:
            active_baselines = len(self.baseline_cache)
            total_observations = sum(calc.count for calc in self.calculators.values())

            return {
                'updates_processed': self.updates_processed,
                'anomalies_detected': self.anomalies_detected,
                'active_baselines': active_baselines,
                'total_observations': total_observations,
                'cache_size': len(self.baseline_cache),
                'lookback_days': self.lookback_days,
                'anomaly_rate': self.anomalies_detected / max(self.updates_processed, 1)
            }

    def cleanup_old_data(self):
        """Clean up old data and optimize memory usage"""
        with self.lock:
            # Clean up database
            self.database.cleanup_old_observations(self.lookback_days)

            # Clean up old cache entries
            current_time = datetime.now(timezone.utc)
            expired_keys = []

            for key, (baseline, timestamp) in self.baseline_cache.items():
                if current_time - timestamp > timedelta(hours=24):
                    expired_keys.append(key)

            for key in expired_keys:
                del self.baseline_cache[key]

            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

# Factory function for easy integration
def create_baseline_manager(db_path: str = "outputs/baseline_context.db",
                          lookback_days: int = 20) -> RealTimeBaselineManager:
    """Create baseline manager with standard configuration"""
    return RealTimeBaselineManager(db_path, lookback_days)

# Example usage and testing
if __name__ == "__main__":
    print("=== Real-time Baseline Manager Test ===")

    # Create manager
    manager = create_baseline_manager("test_baseline.db")

    # Simulate pressure updates
    test_strikes = [21900.0, 21950.0, 22000.0]

    for i in range(50):
        for strike in test_strikes:
            # Simulate varying pressure ratios
            base_pressure = 2.0 + (i % 10) * 0.1
            noise = (i % 7) * 0.05 - 0.15  # Add some noise
            pressure_ratio = base_pressure + noise

            # Add occasional anomalies
            if i % 15 == 0:
                pressure_ratio *= 3.0  # Create anomaly

            timestamp = datetime.now(timezone.utc)

            context = manager.update_baseline(
                strike=strike,
                option_type='C',
                pressure_ratio=pressure_ratio,
                volume=100 + i * 10,
                confidence=0.8 + (i % 5) * 0.04,
                timestamp=timestamp
            )

            if context.anomaly_detected:
                print(f"🚨 Anomaly: {strike}C pressure={pressure_ratio:.2f} "
                      f"z-score={context.z_score:.2f} severity={context.anomaly_severity}")

    # Get comprehensive stats
    stats = manager.get_manager_stats()
    print("\n📊 Manager Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test context retrieval
    context = manager.get_baseline_context(21900.0, 'C')
    if context:
        print(f"\n📈 Baseline Context for 21900C:")
        print(f"  Mean pressure: {context.baseline.mean_pressure:.2f}")
        print(f"  Std pressure: {context.baseline.std_pressure:.2f}")
        print(f"  Sample count: {context.baseline.sample_count}")
        print(f"  Trend: {context.trend_direction}")
        print(f"  Volatility: {context.volatility_regime}")
        print(f"  Confidence: {context.confidence:.2f}")

    print("\n✅ Real-time baseline manager test completed")
