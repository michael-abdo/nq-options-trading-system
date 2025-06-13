#!/usr/bin/env python3
"""
Institutional Flow Detection v3.0 - Enhanced Real-time Analysis

This module implements advanced institutional flow detection using real-time
MBO pressure analysis, historical baselines, and market making detection to
significantly improve signal quality and reduce false positives.

Key Features:
- Real-time bid/ask pressure analysis from MBO streaming
- 20-day historical baseline context for anomaly detection
- Market making pattern detection for false positive filtering
- Enhanced multi-factor confidence scoring
- Cross-strike coordination analysis
- Risk-adjusted signal classification

Architecture Integration:
- Consumes PressureMetrics from Phase 1 MBO streaming
- Applies sophisticated analysis layers
- Generates InstitutionalSignalV3 with enhanced confidence
- Maintains backward compatibility with existing pipeline
"""

import os
import sys
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import statistics
from collections import defaultdict, deque

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import MBO pressure metrics from Phase 1
try:
    from data_ingestion.databento_api.solution import PressureMetrics, MBODatabase
    MBO_INTEGRATION_AVAILABLE = True
    logger.info("Successfully imported MBO streaming integration")
except ImportError as e:
    logger.warning(f"MBO integration not available: {e}")
    MBO_INTEGRATION_AVAILABLE = False

    # Define fallback PressureMetrics for standalone operation
    @dataclass
    class PressureMetrics:
        strike: float
        option_type: str
        time_window: datetime
        bid_volume: int
        ask_volume: int
        pressure_ratio: float
        total_trades: int
        avg_trade_size: float
        dominant_side: str
        confidence: float

@dataclass
class InstitutionalSignalV3:
    """Enhanced v3.0 institutional signal with comprehensive analysis"""

    # Core identification
    strike: float
    option_type: str
    timestamp: datetime

    # v3.0 Pressure Analysis
    pressure_ratio: float
    bid_volume: int
    ask_volume: int
    dominant_side: str
    pressure_confidence: float

    # Historical Context
    baseline_pressure_ratio: float
    pressure_zscore: float
    percentile_rank: float
    anomaly_detected: bool

    # Market Making Analysis
    market_making_probability: float
    straddle_coordination: bool
    volatility_crush_detected: bool

    # Enhanced Confidence
    raw_confidence: float
    baseline_confidence: float
    market_making_penalty: float
    coordination_bonus: float
    final_confidence: float

    # Signal Classification
    signal_strength: str  # 'EXTREME', 'VERY_HIGH', 'HIGH', 'MODERATE'
    institutional_probability: float
    recommended_action: str  # 'STRONG_BUY', 'BUY', 'MONITOR', 'IGNORE'

    # Risk Assessment
    risk_score: float
    position_size_multiplier: float
    max_position_risk: float

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d

@dataclass
class BaselineContext:
    """Historical baseline data for pressure analysis"""
    strike: float
    option_type: str
    lookback_days: int

    mean_pressure_ratio: float
    pressure_std: float
    pressure_percentiles: Dict[int, float]

    current_zscore: float
    percentile_rank: float
    anomaly_detected: bool

    data_quality: float
    confidence: float

@dataclass
class MarketMakingAnalysis:
    """Market making detection results"""

    # Straddle Detection
    straddle_call_volume: int
    straddle_put_volume: int
    straddle_time_coordination: float
    straddle_probability: float

    # Volatility Crush Detection
    call_price_decline: float
    put_price_decline: float
    both_sides_declining: bool
    volatility_crush_probability: float

    # Overall Assessment
    market_making_score: float
    institutional_likelihood: float
    filter_recommendation: str

@dataclass
class PressureAnalysis:
    """Real-time pressure analysis results"""
    pressure_significance: float
    trend_strength: float
    cluster_coordination: float
    volume_concentration: float
    time_persistence: float

class HistoricalBaselineManager:
    """
    Manages 20-day historical baselines for pressure ratio context analysis

    Responsibilities:
    - Maintain rolling 20-day pressure statistics per strike
    - Calculate z-scores and percentile rankings
    - Detect statistical anomalies
    - Provide confidence metrics for baseline quality
    """

    def __init__(self, db_path: str, lookback_days: int = 20):
        """
        Initialize baseline manager

        Args:
            db_path: Path to SQLite database for baselines
            lookback_days: Number of days for baseline calculation
        """
        self.db_path = db_path
        self.lookback_days = lookback_days
        self._init_database()

        # Cache for recent calculations
        self.baseline_cache = {}
        self.cache_expiry = timedelta(hours=1)

    def _init_database(self):
        """Initialize baseline database schema"""
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Historical pressure data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historical_pressure (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strike REAL NOT NULL,
                    option_type TEXT NOT NULL,
                    date TEXT NOT NULL,
                    pressure_ratio REAL NOT NULL,
                    volume_total INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(strike, option_type, date)
                )
            """)

            # Baseline statistics cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS baseline_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strike REAL NOT NULL,
                    option_type TEXT NOT NULL,
                    lookback_days INTEGER NOT NULL,
                    mean_pressure REAL NOT NULL,
                    std_pressure REAL NOT NULL,
                    percentiles TEXT NOT NULL,  -- JSON string
                    data_quality REAL NOT NULL,
                    last_updated TEXT NOT NULL,
                    UNIQUE(strike, option_type, lookback_days)
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pressure_strike_date ON historical_pressure(strike, option_type, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_baseline_lookup ON baseline_stats(strike, option_type)")

            conn.commit()

    def update_historical_data(self, pressure_metrics: PressureMetrics):
        """
        Update historical pressure data with new metrics

        Args:
            pressure_metrics: New pressure metrics to add to history
        """
        date_str = pressure_metrics.time_window.strftime('%Y-%m-%d')
        total_volume = pressure_metrics.bid_volume + pressure_metrics.ask_volume

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO historical_pressure
                (strike, option_type, date, pressure_ratio, volume_total, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pressure_metrics.strike,
                pressure_metrics.option_type,
                date_str,
                pressure_metrics.pressure_ratio,
                total_volume,
                pressure_metrics.confidence,
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()

    def get_baseline_context(self, strike: float, option_type: str) -> BaselineContext:
        """
        Get baseline context for pressure analysis

        Args:
            strike: Option strike price
            option_type: 'C' for calls, 'P' for puts

        Returns:
            BaselineContext with statistical analysis
        """
        cache_key = f"{strike}_{option_type}"

        # Check cache first
        if cache_key in self.baseline_cache:
            cached_data, cache_time = self.baseline_cache[cache_key]
            if datetime.now() - cache_time < self.cache_expiry:
                return cached_data

        # Calculate baseline from database
        baseline = self._calculate_baseline_stats(strike, option_type)

        # Cache result
        self.baseline_cache[cache_key] = (baseline, datetime.now())

        return baseline

    def _calculate_baseline_stats(self, strike: float, option_type: str) -> BaselineContext:
        """Calculate baseline statistics from historical data"""
        # Get recent historical data
        cutoff_date = (datetime.now() - timedelta(days=self.lookback_days)).strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pressure_ratio, volume_total, confidence
                FROM historical_pressure
                WHERE strike = ? AND option_type = ? AND date >= ?
                ORDER BY date ASC
            """, (strike, option_type, cutoff_date))

            rows = cursor.fetchall()

        if len(rows) < 5:  # Minimum data requirement
            # Return default baseline for insufficient data
            return BaselineContext(
                strike=strike,
                option_type=option_type,
                lookback_days=self.lookback_days,
                mean_pressure_ratio=1.5,  # Neutral default
                pressure_std=0.5,
                pressure_percentiles={50: 1.5, 75: 2.0, 90: 3.0, 95: 4.0, 99: 6.0},
                current_zscore=0.0,
                percentile_rank=50.0,
                anomaly_detected=False,
                data_quality=0.0,
                confidence=0.0
            )

        # Extract pressure ratios and calculate statistics
        pressure_ratios = [row[0] for row in rows]
        volumes = [row[1] for row in rows]
        confidences = [row[2] for row in rows]

        # Basic statistics
        mean_pressure = statistics.mean(pressure_ratios)
        std_pressure = statistics.stdev(pressure_ratios) if len(pressure_ratios) > 1 else 0.5

        # Percentiles
        percentiles = {}
        for p in [10, 25, 50, 75, 90, 95, 99]:
            try:
                percentiles[p] = statistics.quantiles(pressure_ratios, n=100)[p-1]
            except (IndexError, statistics.StatisticsError):
                percentiles[p] = mean_pressure

        # Data quality assessment
        expected_days = min(self.lookback_days, (datetime.now() - datetime.now().replace(day=1)).days)
        data_quality = len(rows) / max(expected_days, 1)
        data_quality = min(data_quality, 1.0)

        # Confidence based on volume and data quality
        avg_volume = statistics.mean(volumes) if volumes else 100
        avg_confidence = statistics.mean(confidences) if confidences else 0.5
        baseline_confidence = min(data_quality * avg_confidence * (avg_volume / 1000), 1.0)

        return BaselineContext(
            strike=strike,
            option_type=option_type,
            lookback_days=self.lookback_days,
            mean_pressure_ratio=mean_pressure,
            pressure_std=std_pressure,
            pressure_percentiles=percentiles,
            current_zscore=0.0,  # Will be calculated when compared to current data
            percentile_rank=50.0,  # Will be calculated when compared to current data
            anomaly_detected=False,  # Will be determined based on current pressure
            data_quality=data_quality,
            confidence=baseline_confidence
        )

    def calculate_pressure_context(self, current_pressure: float, baseline: BaselineContext) -> BaselineContext:
        """
        Calculate current pressure context against baseline

        Args:
            current_pressure: Current pressure ratio to analyze
            baseline: Historical baseline context

        Returns:
            Updated baseline context with current pressure analysis
        """
        # Calculate z-score
        if baseline.pressure_std > 0:
            zscore = (current_pressure - baseline.mean_pressure_ratio) / baseline.pressure_std
        else:
            zscore = 0.0

        # Calculate percentile rank
        percentile_rank = 50.0  # Default
        for p in sorted(baseline.pressure_percentiles.keys()):
            if current_pressure <= baseline.pressure_percentiles[p]:
                percentile_rank = p
                break
        else:
            percentile_rank = 99.0  # Above 99th percentile

        # Detect anomaly (2+ standard deviations or >95th percentile)
        anomaly_detected = abs(zscore) >= 2.0 or percentile_rank >= 95.0

        # Update baseline context
        baseline.current_zscore = zscore
        baseline.percentile_rank = percentile_rank
        baseline.anomaly_detected = anomaly_detected

        return baseline

class PressureRatioAnalyzer:
    """
    Analyzes real-time pressure ratios for institutional activity patterns

    Responsibilities:
    - Validate pressure significance against thresholds
    - Detect trends across multiple time windows
    - Identify volume concentration patterns
    - Measure signal persistence over time
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize pressure analyzer

        Args:
            config: Configuration with analysis parameters
        """
        self.config = config

        # Analysis thresholds
        self.min_pressure_ratio = config.get('min_pressure_ratio', 2.0)
        self.min_total_volume = config.get('min_total_volume', 100)
        self.min_confidence = config.get('min_confidence', 0.8)
        self.lookback_windows = config.get('lookback_windows', 3)

        # Recent pressure history for trend analysis
        self.pressure_history = defaultdict(lambda: deque(maxlen=self.lookback_windows))

    def analyze_pressure_signal(self, metrics: PressureMetrics) -> PressureAnalysis:
        """
        Analyze pressure metrics for institutional activity indicators

        Args:
            metrics: Real-time pressure metrics from MBO streaming

        Returns:
            PressureAnalysis with significance scores
        """
        # Key for history tracking
        history_key = f"{metrics.strike}_{metrics.option_type}"

        # Add to history
        self.pressure_history[history_key].append(metrics)

        # Calculate analysis components
        pressure_significance = self._calculate_pressure_significance(metrics)
        trend_strength = self._calculate_trend_strength(history_key)
        cluster_coordination = self._calculate_cluster_coordination(metrics)
        volume_concentration = self._calculate_volume_concentration(metrics)
        time_persistence = self._calculate_time_persistence(history_key)

        return PressureAnalysis(
            pressure_significance=pressure_significance,
            trend_strength=trend_strength,
            cluster_coordination=cluster_coordination,
            volume_concentration=volume_concentration,
            time_persistence=time_persistence
        )

    def _calculate_pressure_significance(self, metrics: PressureMetrics) -> float:
        """
        Calculate how significant the pressure is based on ratio and volume

        Returns:
            Significance score 0-1 (1 = most significant)
        """
        # Pressure ratio significance
        ratio_score = min(metrics.pressure_ratio / 10.0, 1.0)  # Cap at 10:1 ratio

        # Volume significance
        total_volume = metrics.bid_volume + metrics.ask_volume
        volume_score = min(total_volume / 1000.0, 1.0)  # Cap at 1000 volume

        # Confidence in measurement
        confidence_score = metrics.confidence

        # Combined significance
        significance = (ratio_score * 0.5 + volume_score * 0.3 + confidence_score * 0.2)

        return min(significance, 1.0)

    def _calculate_trend_strength(self, history_key: str) -> float:
        """
        Calculate trend strength across recent windows

        Returns:
            Trend strength 0-1 (1 = strongest trend)
        """
        history = self.pressure_history[history_key]

        if len(history) < 2:
            return 0.5  # Neutral for insufficient data

        # Calculate trend in pressure ratios
        ratios = [m.pressure_ratio for m in history]

        # Simple linear trend calculation
        if len(ratios) >= 3:
            # Calculate slope of best fit line
            x_values = list(range(len(ratios)))
            n = len(ratios)
            sum_x = sum(x_values)
            sum_y = sum(ratios)
            sum_xy = sum(x * y for x, y in zip(x_values, ratios))
            sum_x2 = sum(x * x for x in x_values)

            if n * sum_x2 - sum_x * sum_x != 0:
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                # Normalize slope to 0-1 range
                trend_strength = min(abs(slope), 1.0)
            else:
                trend_strength = 0.0
        else:
            # For 2 points, just compare ratios
            trend_strength = abs(ratios[-1] - ratios[0]) / max(ratios[0], 1.0)
            trend_strength = min(trend_strength, 1.0)

        return trend_strength

    def _calculate_cluster_coordination(self, metrics: PressureMetrics) -> float:
        """
        Calculate coordination with nearby strikes (simplified for now)

        Returns:
            Coordination score 0-1 (1 = highest coordination)
        """
        # Future enhancement: Cross-strike coordination analysis for Phase 5
        # For now, return moderate coordination as placeholder
        return 0.6

    def _calculate_volume_concentration(self, metrics: PressureMetrics) -> float:
        """
        Calculate how concentrated the volume is on one side

        Returns:
            Concentration score 0-1 (1 = most concentrated)
        """
        total_volume = metrics.bid_volume + metrics.ask_volume
        if total_volume == 0:
            return 0.0

        # Calculate how concentrated volume is on dominant side
        if metrics.dominant_side == 'BUY':
            concentration = metrics.ask_volume / total_volume
        elif metrics.dominant_side == 'SELL':
            concentration = metrics.bid_volume / total_volume
        else:
            concentration = 0.5  # Neutral

        # Convert to concentration score (0.5 = neutral, 1.0 = fully concentrated)
        concentration_score = (concentration - 0.5) * 2.0
        return max(concentration_score, 0.0)

    def _calculate_time_persistence(self, history_key: str) -> float:
        """
        Calculate how persistent the pressure is over time

        Returns:
            Persistence score 0-1 (1 = most persistent)
        """
        history = self.pressure_history[history_key]

        if len(history) < 2:
            return 0.5  # Neutral for insufficient data

        # Check if pressure consistently above threshold
        consistent_windows = 0
        for metrics in history:
            if metrics.pressure_ratio >= self.min_pressure_ratio:
                consistent_windows += 1

        persistence = consistent_windows / len(history)
        return persistence

class MarketMakingDetector:
    """
    Detects market making activity patterns to filter false positives

    Responsibilities:
    - Detect straddle coordination (simultaneous call/put activity)
    - Identify volatility crush patterns (declining prices both sides)
    - Calculate market making probability scores
    - Recommend signal filtering actions
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize market making detector

        Args:
            config: Configuration with detection parameters
        """
        self.config = config

        # Detection parameters
        self.straddle_time_window = config.get('straddle_time_window', 300)  # 5 minutes
        self.volatility_crush_threshold = config.get('volatility_crush_threshold', -5.0)  # 5% decline
        self.max_market_making_probability = config.get('max_market_making_probability', 0.3)

        # Recent activity tracking
        self.recent_activity = defaultdict(lambda: deque(maxlen=10))

    def detect_market_making_patterns(self,
                                    current_metrics: PressureMetrics,
                                    strike_activity: Optional[List[PressureMetrics]] = None) -> MarketMakingAnalysis:
        """
        Analyze current activity for market making patterns

        Args:
            current_metrics: Current pressure metrics
            strike_activity: Recent activity for same strike (optional)

        Returns:
            MarketMakingAnalysis with detection results
        """
        # Store recent activity
        self.recent_activity[current_metrics.strike].append(current_metrics)

        # Get recent activity for analysis
        if strike_activity is None:
            strike_activity = list(self.recent_activity[current_metrics.strike])

        # Analyze straddle coordination
        straddle_analysis = self._analyze_straddle_activity(current_metrics, strike_activity)

        # Analyze volatility crush patterns
        volatility_analysis = self._analyze_volatility_crush(current_metrics, strike_activity)

        # Calculate overall market making score
        market_making_score = self._calculate_market_making_score(straddle_analysis, volatility_analysis)

        # Determine filter recommendation
        if market_making_score > self.max_market_making_probability:
            filter_rec = 'REJECT'
        elif market_making_score > self.max_market_making_probability * 0.7:
            filter_rec = 'MONITOR'
        else:
            filter_rec = 'ACCEPT'

        return MarketMakingAnalysis(
            straddle_call_volume=straddle_analysis['call_volume'],
            straddle_put_volume=straddle_analysis['put_volume'],
            straddle_time_coordination=straddle_analysis['time_coordination'],
            straddle_probability=straddle_analysis['probability'],
            call_price_decline=volatility_analysis['call_decline'],
            put_price_decline=volatility_analysis['put_decline'],
            both_sides_declining=volatility_analysis['both_declining'],
            volatility_crush_probability=volatility_analysis['probability'],
            market_making_score=market_making_score,
            institutional_likelihood=1.0 - market_making_score,
            filter_recommendation=filter_rec
        )

    def _analyze_straddle_activity(self, current_metrics: PressureMetrics, activity: List[PressureMetrics]) -> Dict:
        """Analyze for straddle coordination patterns"""

        # Separate call and put activity for same strike
        call_activity = [m for m in activity if m.option_type == 'C']
        put_activity = [m for m in activity if m.option_type == 'P']

        # Calculate volumes
        call_volume = sum(m.bid_volume + m.ask_volume for m in call_activity)
        put_volume = sum(m.bid_volume + m.ask_volume for m in put_activity)

        # Calculate time coordination
        if call_activity and put_activity:
            # Find closest call/put events
            current_time = current_metrics.time_window
            call_times = [abs((m.time_window - current_time).total_seconds()) for m in call_activity]
            put_times = [abs((m.time_window - current_time).total_seconds()) for m in put_activity]

            min_call_time = min(call_times) if call_times else float('inf')
            min_put_time = min(put_times) if put_times else float('inf')

            time_coordination = abs(min_call_time - min_put_time)
        else:
            time_coordination = float('inf')

        # Calculate straddle probability
        volume_balance = 0.0
        if call_volume > 0 and put_volume > 0:
            total_volume = call_volume + put_volume
            balance = min(call_volume, put_volume) / total_volume
            volume_balance = balance * 2.0  # 0-1 scale where 1 = perfect balance

        time_coordination_score = 1.0 - min(time_coordination / self.straddle_time_window, 1.0)

        straddle_probability = (volume_balance * 0.7 + time_coordination_score * 0.3)

        return {
            'call_volume': call_volume,
            'put_volume': put_volume,
            'time_coordination': time_coordination,
            'probability': straddle_probability
        }

    def _analyze_volatility_crush(self, current_metrics: PressureMetrics, activity: List[PressureMetrics]) -> Dict:
        """Analyze for volatility crush patterns"""

        # Future enhancement: Price decline analysis for volatility crush detection
        # For now, return placeholder analysis

        return {
            'call_decline': 0.0,
            'put_decline': 0.0,
            'both_declining': False,
            'probability': 0.1  # Low probability placeholder
        }

    def _calculate_market_making_score(self, straddle_analysis: Dict, volatility_analysis: Dict) -> float:
        """Calculate overall market making probability"""

        # Weight different indicators
        straddle_weight = 0.7
        volatility_weight = 0.3

        market_making_score = (
            straddle_analysis['probability'] * straddle_weight +
            volatility_analysis['probability'] * volatility_weight
        )

        return min(market_making_score, 1.0)

class EnhancedConfidenceScorer:
    """
    Calculates enhanced confidence scores using multiple validation factors

    Responsibilities:
    - Combine pressure, baseline, market making factors
    - Apply risk adjustments and penalties
    - Calculate coordination bonuses
    - Generate final risk-adjusted confidence scores
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize confidence scorer

        Args:
            config: Configuration with scoring weights and parameters
        """
        self.config = config

        # Scoring weights
        self.pressure_weight = config.get('pressure_weight', 0.4)
        self.baseline_weight = config.get('baseline_weight', 0.3)
        self.market_making_weight = config.get('market_making_weight', 0.2)
        self.coordination_weight = config.get('coordination_weight', 0.1)

    def calculate_confidence(self,
                           pressure_analysis: PressureAnalysis,
                           baseline_context: BaselineContext,
                           market_making_analysis: MarketMakingAnalysis) -> Tuple[float, float, float, float, float]:
        """
        Calculate multi-factor confidence score

        Args:
            pressure_analysis: Real-time pressure analysis
            baseline_context: Historical baseline context
            market_making_analysis: Market making detection results

        Returns:
            Tuple of (raw_confidence, baseline_confidence, mm_penalty, coord_bonus, final_confidence)
        """
        # Raw confidence from pressure analysis
        raw_confidence = self._calculate_raw_confidence(pressure_analysis)

        # Baseline confidence adjustment
        baseline_confidence = self._calculate_baseline_confidence(baseline_context)

        # Market making penalty
        mm_penalty = self._calculate_market_making_penalty(market_making_analysis)

        # Coordination bonus
        coord_bonus = self._calculate_coordination_bonus(pressure_analysis)

        # Final weighted confidence
        final_confidence = self._calculate_final_confidence(
            raw_confidence, baseline_confidence, mm_penalty, coord_bonus
        )

        return raw_confidence, baseline_confidence, mm_penalty, coord_bonus, final_confidence

    def _calculate_raw_confidence(self, pressure_analysis: PressureAnalysis) -> float:
        """Calculate base confidence from pressure analysis"""
        components = [
            pressure_analysis.pressure_significance,
            pressure_analysis.trend_strength,
            pressure_analysis.volume_concentration,
            pressure_analysis.time_persistence
        ]

        # Weighted average of pressure components
        weights = [0.4, 0.3, 0.2, 0.1]
        raw_confidence = sum(c * w for c, w in zip(components, weights))

        return min(raw_confidence, 1.0)

    def _calculate_baseline_confidence(self, baseline_context: BaselineContext) -> float:
        """Calculate confidence boost from historical baseline context"""
        if not baseline_context.anomaly_detected:
            return 0.5  # Neutral if no anomaly

        # Higher confidence for stronger anomalies
        zscore_confidence = min(abs(baseline_context.current_zscore) / 4.0, 1.0)
        percentile_confidence = baseline_context.percentile_rank / 100.0
        data_quality_factor = baseline_context.data_quality

        baseline_confidence = (zscore_confidence * 0.5 + percentile_confidence * 0.5) * data_quality_factor

        return min(baseline_confidence, 1.0)

    def _calculate_market_making_penalty(self, market_making_analysis: MarketMakingAnalysis) -> float:
        """Calculate confidence penalty from market making probability"""
        # Higher market making score = higher penalty
        penalty = market_making_analysis.market_making_score

        return min(penalty, 1.0)

    def _calculate_coordination_bonus(self, pressure_analysis: PressureAnalysis) -> float:
        """Calculate confidence bonus from cross-strike coordination"""
        # Use cluster coordination as bonus factor
        bonus = pressure_analysis.cluster_coordination * 0.2  # Max 20% bonus

        return min(bonus, 0.2)

    def _calculate_final_confidence(self, raw_confidence: float, baseline_confidence: float,
                                  mm_penalty: float, coord_bonus: float) -> float:
        """Calculate final weighted confidence score"""

        # Weighted combination
        confidence = (
            raw_confidence * self.pressure_weight +
            baseline_confidence * self.baseline_weight
        )

        # Apply market making penalty
        confidence *= (1.0 - mm_penalty * self.market_making_weight)

        # Apply coordination bonus
        confidence += coord_bonus * self.coordination_weight

        return max(min(confidence, 1.0), 0.0)

class IFDv3Engine:
    """
    Main IFD v3.0 analysis engine coordinating all components

    Responsibilities:
    - Consume MBO pressure metrics from Phase 1 streaming
    - Coordinate analysis through all v3.0 components
    - Generate enhanced institutional signals
    - Maintain analysis history and context
    - Provide pipeline integration interface
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize IFD v3.0 engine

        Args:
            config: Complete configuration for all components
        """
        self.config = config

        # Initialize component managers
        baseline_db_path = config.get('baseline_db_path', 'outputs/ifd_v3_baselines.db')
        self.baseline_manager = HistoricalBaselineManager(baseline_db_path)

        self.pressure_analyzer = PressureRatioAnalyzer(config.get('pressure_analysis', {}))
        self.market_making_detector = MarketMakingDetector(config.get('market_making_detection', {}))
        self.confidence_scorer = EnhancedConfidenceScorer(config.get('confidence_scoring', {}))

        # Analysis results storage
        self.recent_signals = deque(maxlen=100)

        logger.info("IFD v3.0 Engine initialized successfully")

    def analyze_pressure_event(self, pressure_metrics: PressureMetrics) -> Optional[InstitutionalSignalV3]:
        """
        Main analysis pipeline for MBO pressure events

        Args:
            pressure_metrics: Real-time pressure metrics from MBO streaming

        Returns:
            InstitutionalSignalV3 if signal detected, None otherwise
        """
        try:
            # Update historical baselines
            self.baseline_manager.update_historical_data(pressure_metrics)

            # Get baseline context
            baseline_context = self.baseline_manager.get_baseline_context(
                pressure_metrics.strike, pressure_metrics.option_type
            )

            # Calculate pressure context against baseline
            baseline_context = self.baseline_manager.calculate_pressure_context(
                pressure_metrics.pressure_ratio, baseline_context
            )

            # Analyze pressure patterns
            pressure_analysis = self.pressure_analyzer.analyze_pressure_signal(pressure_metrics)

            # Detect market making patterns
            market_making_analysis = self.market_making_detector.detect_market_making_patterns(pressure_metrics)

            # Calculate enhanced confidence
            raw_conf, baseline_conf, mm_penalty, coord_bonus, final_conf = self.confidence_scorer.calculate_confidence(
                pressure_analysis, baseline_context, market_making_analysis
            )

            # Check if signal meets minimum criteria
            min_confidence = self.config.get('min_final_confidence', 0.7)
            if final_conf < min_confidence:
                logger.debug(f"Signal below confidence threshold: {final_conf:.3f} < {min_confidence}")
                return None

            # Generate institutional signal
            signal = self._create_institutional_signal(
                pressure_metrics, baseline_context, market_making_analysis,
                raw_conf, baseline_conf, mm_penalty, coord_bonus, final_conf
            )

            # Store signal
            self.recent_signals.append(signal)

            logger.info(f"IFD v3.0 signal generated: {signal.strike}{signal.option_type} "
                       f"confidence={final_conf:.3f} strength={signal.signal_strength}")

            return signal

        except Exception as e:
            logger.error(f"Error in IFD v3.0 analysis: {e}")
            return None

    def _create_institutional_signal(self,
                                   pressure_metrics: PressureMetrics,
                                   baseline_context: BaselineContext,
                                   market_making_analysis: MarketMakingAnalysis,
                                   raw_conf: float, baseline_conf: float,
                                   mm_penalty: float, coord_bonus: float,
                                   final_conf: float) -> InstitutionalSignalV3:
        """Create complete institutional signal from analysis results"""

        # Classify signal strength
        if final_conf >= 0.9:
            signal_strength = 'EXTREME'
            recommended_action = 'STRONG_BUY'
            position_multiplier = 3.0
        elif final_conf >= 0.8:
            signal_strength = 'VERY_HIGH'
            recommended_action = 'BUY'
            position_multiplier = 2.0
        elif final_conf >= 0.7:
            signal_strength = 'HIGH'
            recommended_action = 'BUY'
            position_multiplier = 1.5
        else:
            signal_strength = 'MODERATE'
            recommended_action = 'MONITOR'
            position_multiplier = 1.0

        # Calculate risk metrics
        risk_score = 1.0 - final_conf  # Higher confidence = lower risk
        max_position_risk = 0.02 * position_multiplier  # Max 2% risk per position

        return InstitutionalSignalV3(
            # Core identification
            strike=pressure_metrics.strike,
            option_type=pressure_metrics.option_type,
            timestamp=pressure_metrics.time_window,

            # v3.0 Pressure Analysis
            pressure_ratio=pressure_metrics.pressure_ratio,
            bid_volume=pressure_metrics.bid_volume,
            ask_volume=pressure_metrics.ask_volume,
            dominant_side=pressure_metrics.dominant_side,
            pressure_confidence=pressure_metrics.confidence,

            # Historical Context
            baseline_pressure_ratio=baseline_context.mean_pressure_ratio,
            pressure_zscore=baseline_context.current_zscore,
            percentile_rank=baseline_context.percentile_rank,
            anomaly_detected=baseline_context.anomaly_detected,

            # Market Making Analysis
            market_making_probability=market_making_analysis.market_making_score,
            straddle_coordination=market_making_analysis.straddle_probability > 0.5,
            volatility_crush_detected=market_making_analysis.volatility_crush_probability > 0.5,

            # Enhanced Confidence
            raw_confidence=raw_conf,
            baseline_confidence=baseline_conf,
            market_making_penalty=mm_penalty,
            coordination_bonus=coord_bonus,
            final_confidence=final_conf,

            # Signal Classification
            signal_strength=signal_strength,
            institutional_probability=market_making_analysis.institutional_likelihood,
            recommended_action=recommended_action,

            # Risk Assessment
            risk_score=risk_score,
            position_size_multiplier=position_multiplier,
            max_position_risk=max_position_risk
        )

    def get_recent_signals(self, limit: int = 10) -> List[InstitutionalSignalV3]:
        """Get recent institutional signals"""
        return list(self.recent_signals)[-limit:]

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of recent analysis activity"""
        if not self.recent_signals:
            return {
                'total_signals': 0,
                'avg_confidence': 0.0,
                'signal_distribution': {},
                'recent_activity': []
            }

        signals = list(self.recent_signals)

        # Calculate summary statistics
        avg_confidence = sum(s.final_confidence for s in signals) / len(signals)

        signal_distribution = {}
        for signal in signals:
            strength = signal.signal_strength
            signal_distribution[strength] = signal_distribution.get(strength, 0) + 1

        recent_activity = [
            {
                'strike': s.strike,
                'type': s.option_type,
                'confidence': s.final_confidence,
                'strength': s.signal_strength,
                'timestamp': s.timestamp.isoformat()
            }
            for s in signals[-5:]  # Last 5 signals
        ]

        return {
            'total_signals': len(signals),
            'avg_confidence': avg_confidence,
            'signal_distribution': signal_distribution,
            'recent_activity': recent_activity
        }

# Pipeline Integration Functions
def create_ifd_v3_analyzer(config: Optional[Dict] = None) -> IFDv3Engine:
    """Factory function to create IFD v3.0 analyzer instance"""
    if config is None:
        config = {
            'baseline_db_path': 'outputs/ifd_v3_baselines.db',
            'pressure_analysis': {
                'min_pressure_ratio': 2.0,
                'min_total_volume': 100,
                'min_confidence': 0.8
            },
            'historical_baselines': {
                'lookback_days': 20
            },
            'market_making_detection': {
                'straddle_time_window': 300,
                'max_market_making_probability': 0.3
            },
            'confidence_scoring': {
                'pressure_weight': 0.4,
                'baseline_weight': 0.3,
                'market_making_weight': 0.2,
                'coordination_weight': 0.1
            },
            'min_final_confidence': 0.6  # Slightly lower for better signal generation
        }

    # Ensure baseline_db_path is set
    if 'baseline_db_path' not in config:
        config['baseline_db_path'] = 'outputs/ifd_v3_baselines.db'

    return IFDv3Engine(config)

def run_ifd_v3_analysis(pressure_data: List[PressureMetrics], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run IFD v3.0 analysis on pressure data

    Args:
        pressure_data: List of pressure metrics from MBO streaming
        config: Analysis configuration

    Returns:
        Analysis results with institutional signals
    """
    try:
        # Initialize analyzer
        analyzer = create_ifd_v3_analyzer(config)

        # Process each pressure event
        signals = []
        for pressure_metrics in pressure_data:
            signal = analyzer.analyze_pressure_event(pressure_metrics)
            if signal:
                signals.append(signal)

        # Get analysis summary
        summary = analyzer.get_analysis_summary()

        return {
            'status': 'success',
            'signals': [signal.to_dict() for signal in signals],
            'summary': summary,
            'total_events_processed': len(pressure_data),
            'signals_generated': len(signals),
            'signal_rate': len(signals) / max(len(pressure_data), 1)
        }

    except Exception as e:
        logger.error(f"IFD v3.0 analysis failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'signals': [],
            'summary': {},
            'total_events_processed': 0,
            'signals_generated': 0,
            'signal_rate': 0.0
        }

# Example usage and testing
if __name__ == "__main__":
    # Example configuration
    config = {
        'pressure_analysis': {
            'min_pressure_ratio': 2.0,
            'min_total_volume': 100,
            'min_confidence': 0.8
        },
        'baseline_db_path': 'test_baselines.db'
    }

    # Create test pressure metrics
    test_pressure = PressureMetrics(
        strike=21900.0,
        option_type='C',
        time_window=datetime.now(timezone.utc),
        bid_volume=100,
        ask_volume=300,
        pressure_ratio=3.0,
        total_trades=20,
        avg_trade_size=20.0,
        dominant_side='BUY',
        confidence=0.85
    )

    # Initialize and test analyzer
    analyzer = create_ifd_v3_analyzer(config)

    print("=== IFD v3.0 Analysis Test ===")
    print(f"Test pressure: {test_pressure.strike}{test_pressure.option_type} "
          f"ratio={test_pressure.pressure_ratio} confidence={test_pressure.confidence}")

    # Analyze pressure event
    signal = analyzer.analyze_pressure_event(test_pressure)

    if signal:
        print(f"\nSignal Generated:")
        print(f"  Confidence: {signal.final_confidence:.3f}")
        print(f"  Strength: {signal.signal_strength}")
        print(f"  Action: {signal.recommended_action}")
        print(f"  Market Making Prob: {signal.market_making_probability:.3f}")
        print(f"  Baseline Z-score: {signal.pressure_zscore:.2f}")
    else:
        print("\nNo signal generated")

    # Show analysis summary
    summary = analyzer.get_analysis_summary()
    print(f"\nAnalysis Summary:")
    print(f"  Total Signals: {summary['total_signals']}")
    print(f"  Avg Confidence: {summary['avg_confidence']:.3f}")


# ============================================================================
# Import Aliases for Backward Compatibility
# ============================================================================
# These aliases allow dependent modules to import classes using expected names
# while preserving the original descriptive class names for clarity.

# Core analysis components
PressureAnalyzer = PressureRatioAnalyzer
ConfidenceScorer = EnhancedConfidenceScorer
IFDv3Analyzer = IFDv3Engine
BaselineManager = HistoricalBaselineManager
BaselineDatabase = HistoricalBaselineManager
