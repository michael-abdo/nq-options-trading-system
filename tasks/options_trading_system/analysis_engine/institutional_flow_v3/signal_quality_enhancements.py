"""
Signal Quality Enhancements for IFD v3.0

Improvements to increase signal accuracy:
- Volume-weighted confidence scoring
- Adaptive threshold adjustment
- Cross-strike coordination detection
- Time decay for stale signals
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from utils.timezone_utils import get_eastern_time, get_utc_time
from dataclasses import dataclass
import statistics
from collections import defaultdict

from .solution import (
    PressureMetrics, InstitutionalSignalV3, BaselineContext,
    PressureAnalysis, MarketMakingAnalysis
)

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Metrics for signal quality assessment"""
    volume_weight: float
    time_relevance: float
    strike_coordination: float
    baseline_strength: float
    overall_quality: float


class SignalQualityEnhancer:
    """
    Enhanced signal quality scoring with adaptive improvements
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize signal quality enhancer

        Args:
            config: Configuration with quality enhancement parameters
        """
        self.config = config

        # Enhancement parameters
        self.use_volume_weighted = config.get('use_volume_weighted_confidence', True)
        self.adaptive_thresholds = config.get('adaptive_thresholds', True)
        self.cross_strike_coordination = config.get('cross_strike_coordination', True)
        self.time_decay_factor = config.get('time_decay_factor', 0.95)

        # Tracking for adaptive adjustments
        self.signal_history = defaultdict(list)
        self.threshold_adjustments = defaultdict(float)

        # OPTIMIZATION: Cache for fast strike lookups
        self._sorted_signals_cache = []
        self._cache_needs_refresh = True

    def enhance_signal_quality(self,
                             signal: InstitutionalSignalV3,
                             pressure_metrics: PressureMetrics,
                             baseline_context: BaselineContext,
                             nearby_signals: Optional[List[InstitutionalSignalV3]] = None) -> Tuple[InstitutionalSignalV3, QualityMetrics]:
        """
        Enhance signal quality with advanced scoring

        Args:
            signal: Original institutional signal
            pressure_metrics: Associated pressure metrics
            baseline_context: Baseline statistical context
            nearby_signals: Signals from nearby strikes (optional)

        Returns:
            Enhanced signal and quality metrics
        """
        # Calculate quality components
        volume_weight = self._calculate_volume_weight(pressure_metrics)
        time_relevance = self._calculate_time_relevance(pressure_metrics.time_window)
        strike_coordination = self._calculate_strike_coordination(signal, nearby_signals)
        baseline_strength = self._calculate_baseline_strength(baseline_context)

        # Calculate overall quality score
        overall_quality = self._calculate_overall_quality(
            volume_weight, time_relevance, strike_coordination, baseline_strength
        )

        # Apply adaptive threshold adjustments if enabled
        if self.adaptive_thresholds:
            adjusted_confidence = self._apply_adaptive_adjustments(
                signal.final_confidence, signal.strike, overall_quality
            )
        else:
            adjusted_confidence = signal.final_confidence

        # Create enhanced signal
        enhanced_signal = InstitutionalSignalV3(
            timestamp=signal.timestamp,
            strike=signal.strike,
            option_type=signal.option_type,
            expected_direction=signal.expected_direction,
            raw_confidence=signal.raw_confidence,
            baseline_confidence=signal.baseline_confidence,
            market_making_penalty=signal.market_making_penalty,
            coordination_bonus=signal.coordination_bonus,
            final_confidence=adjusted_confidence * overall_quality,  # Apply quality adjustment
            signal_strength=signal.signal_strength,
            pressure_ratio=signal.pressure_ratio,
            pressure_percentile=signal.pressure_percentile,
            pressure_zscore=signal.pressure_zscore,
            recent_pressure_trend=signal.recent_pressure_trend,
            market_making_probability=signal.market_making_probability,
            institutional_probability=signal.institutional_probability,
            recommended_action=self._adjust_recommended_action(signal.recommended_action, overall_quality),
            position_size_multiplier=signal.position_size_multiplier * overall_quality,
            confidence_factors=signal.confidence_factors
        )

        # Track signal for adaptive learning
        self._track_signal_quality(enhanced_signal, overall_quality)

        quality_metrics = QualityMetrics(
            volume_weight=volume_weight,
            time_relevance=time_relevance,
            strike_coordination=strike_coordination,
            baseline_strength=baseline_strength,
            overall_quality=overall_quality
        )

        return enhanced_signal, quality_metrics

    def _calculate_volume_weight(self, pressure_metrics: PressureMetrics) -> float:
        """
        Calculate volume-based confidence weight

        Higher volume = higher confidence in signal
        """
        total_volume = pressure_metrics.bid_volume + pressure_metrics.ask_volume

        # Volume thresholds (can be made configurable)
        low_volume = 100
        high_volume = 5000

        if total_volume <= low_volume:
            return 0.5  # Low confidence for low volume
        elif total_volume >= high_volume:
            return 1.0  # Full confidence for high volume
        else:
            # Linear interpolation
            return 0.5 + 0.5 * (total_volume - low_volume) / (high_volume - low_volume)

    def _calculate_time_relevance(self, signal_time: datetime) -> float:
        """
        Calculate time-based relevance with exponential decay

        Newer signals are more relevant
        """
        time_since_signal = (get_eastern_time() - signal_time).total_seconds()

        # Apply exponential decay (half-life of 5 minutes)
        half_life_seconds = 300
        decay_rate = 0.693 / half_life_seconds  # ln(2) / half_life

        relevance = self.time_decay_factor ** (time_since_signal * decay_rate)

        return max(relevance, 0.1)  # Minimum 10% relevance

    def _calculate_strike_coordination(self,
                                     signal: InstitutionalSignalV3,
                                     nearby_signals: Optional[List[InstitutionalSignalV3]]) -> float:
        """
        Calculate cross-strike coordination score

        Coordinated activity across strikes = higher confidence
        """
        if not self.cross_strike_coordination or not nearby_signals:
            return 1.0  # Neutral if not using coordination

        # OPTIMIZATION: Use optimized strike lookup to avoid O(n) iteration
        # This reduces the cross-strike coordination from O(n²) to O(n log n)
        coordinated_signals = self._fast_strike_lookup(signal, nearby_signals)

        if not coordinated_signals:
            return 0.8  # Slight penalty for isolated activity

        # Calculate coordination strength
        coordination_count = len(coordinated_signals)
        avg_confidence = statistics.mean([s.final_confidence for s in coordinated_signals])

        # More coordinated strikes = higher score
        if coordination_count >= 3:
            coordination_score = 1.2  # Bonus for strong coordination
        elif coordination_count >= 2:
            coordination_score = 1.1
        else:
            coordination_score = 0.9

        # Weight by average confidence of coordinated signals
        return coordination_score * (0.5 + 0.5 * avg_confidence)

    def _fast_strike_lookup(self, signal: InstitutionalSignalV3,
                           nearby_signals: List[InstitutionalSignalV3]) -> List[InstitutionalSignalV3]:
        """
        OPTIMIZED: Fast lookup for coordinated signals using spatial indexing

        Instead of O(n) linear search, this uses sorting + binary search for O(log n) per signal
        Overall complexity: O(n log n) instead of O(n²)
        """
        # Cache sorted signals by strike for this batch (if not already sorted)
        if not hasattr(self, '_sorted_signals_cache') or self._cache_needs_refresh:
            # Sort signals by strike for binary search O(n log n) once per batch
            self._sorted_signals_cache = sorted(nearby_signals, key=lambda s: s.strike)
            self._cache_needs_refresh = False

        sorted_signals = self._sorted_signals_cache
        target_strike = signal.strike
        target_direction = signal.expected_direction
        strike_range = 50  # 50 points range

        # Binary search for lower bound (target_strike - 50)
        left = self._binary_search_lower_bound(sorted_signals, target_strike - strike_range)
        # Binary search for upper bound (target_strike + 50)
        right = self._binary_search_upper_bound(sorted_signals, target_strike + strike_range)

        # Filter candidates in the strike range
        coordinated_signals = []
        for i in range(left, min(right + 1, len(sorted_signals))):
            other_signal = sorted_signals[i]
            if (other_signal.strike != target_strike and
                other_signal.expected_direction == target_direction):
                coordinated_signals.append(other_signal)

        return coordinated_signals

    def _binary_search_lower_bound(self, sorted_signals: List[InstitutionalSignalV3], target: float) -> int:
        """Binary search for lower bound - O(log n)"""
        left, right = 0, len(sorted_signals)
        while left < right:
            mid = (left + right) // 2
            if sorted_signals[mid].strike < target:
                left = mid + 1
            else:
                right = mid
        return left

    def _binary_search_upper_bound(self, sorted_signals: List[InstitutionalSignalV3], target: float) -> int:
        """Binary search for upper bound - O(log n)"""
        left, right = 0, len(sorted_signals)
        while left < right:
            mid = (left + right) // 2
            if sorted_signals[mid].strike <= target:
                left = mid + 1
            else:
                right = mid
        return left - 1

    def _calculate_baseline_strength(self, baseline_context: BaselineContext) -> float:
        """
        Calculate strength of baseline anomaly

        Stronger anomalies = higher confidence
        """
        if baseline_context.zscore_from_mean == 0:
            return 0.5  # No anomaly

        # Convert z-score to confidence (sigmoid function)
        import math
        zscore_abs = abs(baseline_context.zscore_from_mean)

        # Sigmoid centered at z=2.0
        strength = 1 / (1 + math.exp(-2 * (zscore_abs - 2.0)))

        return max(strength, 0.3)  # Minimum 30% strength

    def _calculate_overall_quality(self,
                                 volume_weight: float,
                                 time_relevance: float,
                                 strike_coordination: float,
                                 baseline_strength: float) -> float:
        """
        Calculate overall signal quality score
        """
        # Weighted average of quality components
        weights = {
            'volume': 0.3,
            'time': 0.2,
            'coordination': 0.3,
            'baseline': 0.2
        }

        quality_score = (
            weights['volume'] * volume_weight +
            weights['time'] * time_relevance +
            weights['coordination'] * strike_coordination +
            weights['baseline'] * baseline_strength
        )

        return max(min(quality_score, 1.5), 0.5)  # Clamp between 0.5 and 1.5

    def _apply_adaptive_adjustments(self,
                                  confidence: float,
                                  strike: float,
                                  quality: float) -> float:
        """
        Apply adaptive threshold adjustments based on historical performance
        """
        # Get historical adjustment for this strike
        strike_key = f"{strike}"
        historical_adjustment = self.threshold_adjustments.get(strike_key, 0.0)

        # Apply adjustment with quality weighting
        adjusted_confidence = confidence * (1.0 + historical_adjustment * quality)

        return max(min(adjusted_confidence, 1.0), 0.0)

    def _adjust_recommended_action(self, action: str, quality: float) -> str:
        """
        Adjust recommended action based on quality score
        """
        if quality < 0.7:
            # Downgrade action for low quality
            if action == "STRONG_BUY":
                return "BUY"
            elif action == "BUY":
                return "MONITOR"
            else:
                return action
        elif quality > 1.2:
            # Upgrade action for high quality
            if action == "BUY":
                return "STRONG_BUY"
            elif action == "MONITOR":
                return "BUY"
            else:
                return action
        else:
            return action

    def _track_signal_quality(self, signal: InstitutionalSignalV3, quality: float):
        """
        Track signal quality for adaptive learning
        """
        strike_key = f"{signal.strike}"

        # Store signal with quality score
        self.signal_history[strike_key].append({
            'timestamp': signal.timestamp,
            'confidence': signal.final_confidence,
            'quality': quality
        })

        # Limit history size
        if len(self.signal_history[strike_key]) > 100:
            self.signal_history[strike_key] = self.signal_history[strike_key][-100:]

    def update_adaptive_thresholds(self, performance_feedback: Dict[str, float]):
        """
        Update adaptive thresholds based on performance feedback

        Args:
            performance_feedback: Dict of strike -> performance score (-1 to 1)
        """
        for strike_key, performance in performance_feedback.items():
            # Update threshold adjustment based on performance
            current_adjustment = self.threshold_adjustments.get(strike_key, 0.0)

            # Learning rate
            learning_rate = 0.1

            # Update adjustment (positive performance = lower thresholds)
            if performance > 0:
                # Good performance, can be slightly more aggressive
                new_adjustment = current_adjustment + learning_rate * performance * 0.1
            else:
                # Poor performance, be more conservative
                new_adjustment = current_adjustment + learning_rate * performance * 0.2

            # Clamp adjustment to reasonable range
            self.threshold_adjustments[strike_key] = max(min(new_adjustment, 0.2), -0.2)

            logger.info(f"Updated adaptive threshold for {strike_key}: {new_adjustment:.3f}")


def apply_signal_quality_enhancements(signals: List[InstitutionalSignalV3],
                                    pressure_metrics_map: Dict[str, PressureMetrics],
                                    baseline_contexts: Dict[str, BaselineContext],
                                    config: Dict[str, Any]) -> List[Tuple[InstitutionalSignalV3, QualityMetrics]]:
    """
    Apply quality enhancements to a batch of signals

    Args:
        signals: List of institutional signals
        pressure_metrics_map: Map of "strike_type" to pressure metrics
        baseline_contexts: Map of "strike_type" to baseline contexts
        config: Enhancement configuration

    Returns:
        List of (enhanced_signal, quality_metrics) tuples
    """
    enhancer = SignalQualityEnhancer(config)
    # OPTIMIZATION: Refresh cache for each new batch to ensure accuracy
    enhancer._cache_needs_refresh = True
    enhanced_signals = []

    # Group signals by time window for coordination detection
    time_grouped_signals = defaultdict(list)
    for signal in signals:
        time_key = signal.timestamp.replace(second=0, microsecond=0)  # Round to minute
        time_grouped_signals[time_key].append(signal)

    # Enhance each signal
    for signal in signals:
        # Get associated data
        key = f"{signal.strike}_{signal.option_type}"
        pressure_metrics = pressure_metrics_map.get(key)
        baseline_context = baseline_contexts.get(key)

        if pressure_metrics and baseline_context:
            # Get nearby signals for coordination
            time_key = signal.timestamp.replace(second=0, microsecond=0)
            nearby_signals = time_grouped_signals.get(time_key, [])

            # Enhance signal
            enhanced_signal, quality_metrics = enhancer.enhance_signal_quality(
                signal, pressure_metrics, baseline_context, nearby_signals
            )

            enhanced_signals.append((enhanced_signal, quality_metrics))

    return enhanced_signals
