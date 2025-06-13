#!/usr/bin/env python3
"""
Call/Put Coordination Detector for IFD v3.0

This module detects coordinated institutional activity between calls and puts:
- Same-strike call/put pressure coordination
- Butterfly and condor pattern detection
- Synthetic position identification
- Cross-strike coordination analysis
"""

import logging
from datetime import datetime, timedelta, timezone
from utils.timezone_utils import get_eastern_time, get_utc_time
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import numpy as np
from scipy import stats

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CoordinationType(Enum):
    """Types of call/put coordination patterns"""
    SAME_STRIKE_HEDGE = "SAME_STRIKE_HEDGE"        # Protective collar at same strike
    SYNTHETIC_LONG = "SYNTHETIC_LONG"              # Buy call + sell put
    SYNTHETIC_SHORT = "SYNTHETIC_SHORT"            # Sell call + buy put
    BUTTERFLY = "BUTTERFLY"                        # 3-strike butterfly
    CONDOR = "CONDOR"                             # 4-strike condor
    STRANGLE = "STRANGLE"                          # OTM call + OTM put
    STRADDLE = "STRADDLE"                          # ATM call + ATM put
    RISK_REVERSAL = "RISK_REVERSAL"               # Buy OTM call + sell OTM put
    CONVERSION = "CONVERSION"                       # Complex arbitrage pattern


@dataclass
class StrikeActivity:
    """Activity metrics for a single strike"""
    strike: float
    timestamp: datetime

    # Call metrics
    call_volume: int = 0
    call_buy_volume: int = 0
    call_sell_volume: int = 0
    call_pressure_ratio: float = 0.0
    call_avg_size: float = 0.0

    # Put metrics
    put_volume: int = 0
    put_buy_volume: int = 0
    put_sell_volume: int = 0
    put_pressure_ratio: float = 0.0
    put_avg_size: float = 0.0

    # Coordination metrics
    volume_ratio: float = 0.0  # call_volume / put_volume
    pressure_correlation: float = 0.0
    time_correlation: float = 0.0

    def calculate_coordination_score(self) -> float:
        """Calculate coordination score for this strike"""
        if self.call_volume == 0 or self.put_volume == 0:
            return 0.0

        # Volume balance factor (closer to 1:1 is better)
        volume_balance = 1.0 - abs(self.volume_ratio - 1.0) / max(self.volume_ratio, 1.0)

        # Pressure alignment (both buying or both selling)
        pressure_alignment = abs(self.call_pressure_ratio - self.put_pressure_ratio)

        # Size similarity
        size_ratio = min(self.call_avg_size, self.put_avg_size) / max(self.call_avg_size, self.put_avg_size) \
                    if max(self.call_avg_size, self.put_avg_size) > 0 else 0

        # Combined score
        score = (volume_balance * 0.4 +
                (1 - pressure_alignment) * 0.4 +
                size_ratio * 0.2)

        return score


@dataclass
class CoordinationPattern:
    """Detected coordination pattern"""
    pattern_type: CoordinationType
    confidence: float
    timestamp: datetime

    # Pattern details
    strikes: List[float]
    legs: List[Dict[str, Any]]  # Leg details

    # Metrics
    total_volume: int = 0
    net_premium: float = 0.0
    risk_score: float = 0.0

    # Context
    underlying_price: float = 0.0
    volatility_level: float = 0.0
    time_to_expiry: float = 0.0

    # Detection metadata
    detection_method: str = ""
    supporting_evidence: List[str] = field(default_factory=list)


@dataclass
class CoordinationAlert:
    """Alert for significant coordination pattern"""
    alert_id: str
    timestamp: datetime
    severity: str  # HIGH, MEDIUM, LOW

    pattern: CoordinationPattern
    message: str

    # Impact assessment
    expected_move: Optional[float] = None
    hedged_exposure: Optional[float] = None
    institutional_confidence: float = 0.0

    # Historical context
    similar_patterns_30d: int = 0
    historical_success_rate: float = 0.0


class CoordinationDetector:
    """
    Main coordination detection engine

    Features:
    - Real-time pattern detection
    - Multi-strike analysis
    - Temporal correlation tracking
    - Historical pattern matching
    """

    def __init__(self, lookback_minutes: int = 30,
                 correlation_threshold: float = 0.7):
        """
        Initialize coordination detector

        Args:
            lookback_minutes: Time window for correlation analysis
            correlation_threshold: Minimum correlation for coordination
        """
        self.lookback_minutes = lookback_minutes
        self.correlation_threshold = correlation_threshold

        # Activity tracking
        self.strike_activity: Dict[float, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        self.recent_patterns: deque = deque(maxlen=1000)

        # Pattern detection thresholds
        self.thresholds = {
            'min_volume': 100,
            'min_coordination_score': 0.6,
            'butterfly_tolerance': 0.02,  # 2% strike spacing tolerance
            'time_correlation_window': 300  # 5 minutes
        }

        # Statistics tracking
        self.pattern_counts = defaultdict(int)
        self.alert_history = deque(maxlen=100)

        logger.info(f"Coordination detector initialized with {lookback_minutes}min lookback")

    def process_strike_activity(self, activity: StrikeActivity) -> Optional[CoordinationPattern]:
        """
        Process new strike activity and detect patterns

        Args:
            activity: Strike activity data

        Returns:
            Detected pattern if found
        """
        # Store activity
        self.strike_activity[activity.strike].append(activity)

        # Check for same-strike coordination
        pattern = self._check_same_strike_coordination(activity)
        if pattern:
            self._record_pattern(pattern)
            return pattern

        # Check for multi-strike patterns
        if len(self.strike_activity) >= 3:
            # Check for butterflies and condors
            pattern = self._check_multi_strike_patterns()
            if pattern:
                self._record_pattern(pattern)
                return pattern

        # Check for synthetic positions
        pattern = self._check_synthetic_positions(activity)
        if pattern:
            self._record_pattern(pattern)
            return pattern

        return None

    def _check_same_strike_coordination(self, activity: StrikeActivity) -> Optional[CoordinationPattern]:
        """Check for coordination at the same strike"""
        # Need significant volume on both sides
        if (activity.call_volume < self.thresholds['min_volume'] or
            activity.put_volume < self.thresholds['min_volume']):
            return None

        # Calculate coordination score
        coord_score = activity.calculate_coordination_score()
        if coord_score < self.thresholds['min_coordination_score']:
            return None

        # Determine pattern type based on pressure
        if activity.call_pressure_ratio > 0.7 and activity.put_pressure_ratio < 0.3:
            # Buying calls, selling puts = Synthetic Long
            pattern_type = CoordinationType.SYNTHETIC_LONG
            confidence = coord_score * 0.9

        elif activity.call_pressure_ratio < 0.3 and activity.put_pressure_ratio > 0.7:
            # Selling calls, buying puts = Synthetic Short
            pattern_type = CoordinationType.SYNTHETIC_SHORT
            confidence = coord_score * 0.9

        elif abs(activity.call_pressure_ratio - activity.put_pressure_ratio) < 0.2:
            # Similar pressure = Straddle/Strangle
            pattern_type = CoordinationType.STRADDLE
            confidence = coord_score * 0.8

        else:
            # General hedge
            pattern_type = CoordinationType.SAME_STRIKE_HEDGE
            confidence = coord_score * 0.7

        # Create pattern
        pattern = CoordinationPattern(
            pattern_type=pattern_type,
            confidence=confidence,
            timestamp=activity.timestamp,
            strikes=[activity.strike],
            legs=[
                {
                    'strike': activity.strike,
                    'type': 'C',
                    'volume': activity.call_volume,
                    'pressure': activity.call_pressure_ratio,
                    'action': 'BUY' if activity.call_pressure_ratio > 0.5 else 'SELL'
                },
                {
                    'strike': activity.strike,
                    'type': 'P',
                    'volume': activity.put_volume,
                    'pressure': activity.put_pressure_ratio,
                    'action': 'BUY' if activity.put_pressure_ratio > 0.5 else 'SELL'
                }
            ],
            total_volume=activity.call_volume + activity.put_volume,
            detection_method='same_strike_coordination',
            supporting_evidence=[
                f"Coordination score: {coord_score:.2f}",
                f"Volume ratio: {activity.volume_ratio:.2f}",
                f"Call pressure: {activity.call_pressure_ratio:.2f}",
                f"Put pressure: {activity.put_pressure_ratio:.2f}"
            ]
        )

        return pattern

    def _check_multi_strike_patterns(self) -> Optional[CoordinationPattern]:
        """Check for butterfly, condor, and other multi-strike patterns"""
        # Get current strikes with recent activity
        active_strikes = []
        current_time = datetime.now(timezone.utc)
        cutoff_time = current_time - timedelta(minutes=5)

        for strike, activities in self.strike_activity.items():
            if activities and activities[-1].timestamp > cutoff_time:
                # Check if both calls and puts are active
                latest = activities[-1]
                if latest.call_volume > 50 and latest.put_volume > 50:
                    active_strikes.append(strike)

        active_strikes.sort()

        # Need at least 3 strikes for butterfly
        if len(active_strikes) < 3:
            return None

        # Check for butterfly pattern (1:2:1 ratio)
        for i in range(len(active_strikes) - 2):
            strikes = active_strikes[i:i+3]

            # Check strike spacing
            spacing1 = strikes[1] - strikes[0]
            spacing2 = strikes[2] - strikes[1]

            if abs(spacing1 - spacing2) / min(spacing1, spacing2) < self.thresholds['butterfly_tolerance']:
                # Check volume pattern
                pattern = self._validate_butterfly_pattern(strikes)
                if pattern:
                    return pattern

        # Check for condor pattern (4 strikes)
        if len(active_strikes) >= 4:
            for i in range(len(active_strikes) - 3):
                strikes = active_strikes[i:i+4]
                pattern = self._validate_condor_pattern(strikes)
                if pattern:
                    return pattern

        return None

    def _validate_butterfly_pattern(self, strikes: List[float]) -> Optional[CoordinationPattern]:
        """Validate butterfly pattern with 3 strikes"""
        # Get latest activity for each strike
        activities = []
        for strike in strikes:
            if self.strike_activity[strike]:
                activities.append(self.strike_activity[strike][-1])
            else:
                return None

        # Check volume ratios (approximately 1:2:1)
        outer_volume = activities[0].call_volume + activities[2].call_volume
        middle_volume = activities[1].call_volume

        if middle_volume < outer_volume * 1.5:
            return None

        # Check timing correlation
        time_spread = max(a.timestamp for a in activities) - min(a.timestamp for a in activities)
        if time_spread.total_seconds() > self.thresholds['time_correlation_window']:
            return None

        # Calculate confidence based on volume and timing
        volume_ratio_score = 1.0 - abs(2.0 - middle_volume / max(outer_volume, 1)) / 2.0
        timing_score = 1.0 - time_spread.total_seconds() / self.thresholds['time_correlation_window']
        confidence = (volume_ratio_score + timing_score) / 2.0

        if confidence < 0.5:
            return None

        # Create butterfly pattern
        pattern = CoordinationPattern(
            pattern_type=CoordinationType.BUTTERFLY,
            confidence=confidence,
            timestamp=max(a.timestamp for a in activities),
            strikes=strikes,
            legs=[
                {'strike': strikes[0], 'type': 'C', 'volume': activities[0].call_volume, 'action': 'BUY'},
                {'strike': strikes[1], 'type': 'C', 'volume': activities[1].call_volume, 'action': 'SELL'},
                {'strike': strikes[2], 'type': 'C', 'volume': activities[2].call_volume, 'action': 'BUY'}
            ],
            total_volume=sum(a.call_volume for a in activities),
            detection_method='butterfly_pattern',
            supporting_evidence=[
                f"Strike spacing: {strikes[1]-strikes[0]:.0f}",
                f"Volume ratio: 1:{middle_volume/outer_volume:.1f}:1",
                f"Time correlation: {time_spread.total_seconds():.0f}s"
            ]
        )

        return pattern

    def _validate_condor_pattern(self, strikes: List[float]) -> Optional[CoordinationPattern]:
        """Validate condor pattern with 4 strikes"""
        # Get latest activity for each strike
        activities = []
        for strike in strikes:
            if self.strike_activity[strike]:
                activities.append(self.strike_activity[strike][-1])
            else:
                return None

        # Check volume pattern (outer strikes similar, inner strikes similar)
        outer_volume = activities[0].call_volume + activities[3].call_volume
        inner_volume = activities[1].call_volume + activities[2].call_volume

        # Inner volume should be roughly equal to outer volume
        volume_ratio = inner_volume / max(outer_volume, 1)
        if not (0.7 < volume_ratio < 1.3):
            return None

        # Check timing
        time_spread = max(a.timestamp for a in activities) - min(a.timestamp for a in activities)
        if time_spread.total_seconds() > self.thresholds['time_correlation_window']:
            return None

        # Calculate confidence
        volume_score = 1.0 - abs(1.0 - volume_ratio)
        timing_score = 1.0 - time_spread.total_seconds() / self.thresholds['time_correlation_window']
        confidence = (volume_score + timing_score) / 2.0

        if confidence < 0.5:
            return None

        # Create condor pattern
        pattern = CoordinationPattern(
            pattern_type=CoordinationType.CONDOR,
            confidence=confidence,
            timestamp=max(a.timestamp for a in activities),
            strikes=strikes,
            legs=[
                {'strike': strikes[0], 'type': 'C', 'volume': activities[0].call_volume, 'action': 'BUY'},
                {'strike': strikes[1], 'type': 'C', 'volume': activities[1].call_volume, 'action': 'SELL'},
                {'strike': strikes[2], 'type': 'C', 'volume': activities[2].call_volume, 'action': 'SELL'},
                {'strike': strikes[3], 'type': 'C', 'volume': activities[3].call_volume, 'action': 'BUY'}
            ],
            total_volume=sum(a.call_volume for a in activities),
            detection_method='condor_pattern',
            supporting_evidence=[
                f"Strike range: {strikes[0]:.0f}-{strikes[3]:.0f}",
                f"Volume balance: {volume_ratio:.2f}",
                f"Time correlation: {time_spread.total_seconds():.0f}s"
            ]
        )

        return pattern

    def _check_synthetic_positions(self, activity: StrikeActivity) -> Optional[CoordinationPattern]:
        """Check for synthetic long/short positions"""
        # Look for coordinated activity across nearby strikes
        strike = activity.strike
        nearby_range = 200  # Check strikes within 200 points

        # Find nearby strikes with recent activity
        nearby_activities = []
        current_time = activity.timestamp

        for other_strike, activities in self.strike_activity.items():
            if abs(other_strike - strike) <= nearby_range and other_strike != strike:
                # Get recent activity
                recent = [a for a in activities
                         if (current_time - a.timestamp).total_seconds() < 300]
                if recent:
                    nearby_activities.extend(recent)

        if not nearby_activities:
            return None

        # Look for risk reversal pattern
        # Buy OTM call at higher strike, sell OTM put at lower strike
        for nearby in nearby_activities:
            if nearby.strike > strike:
                # Check if buying calls at higher strike
                if (nearby.call_pressure_ratio > 0.7 and
                    activity.put_pressure_ratio < 0.3 and
                    activity.put_volume > self.thresholds['min_volume']):

                    # Risk reversal detected
                    pattern = CoordinationPattern(
                        pattern_type=CoordinationType.RISK_REVERSAL,
                        confidence=0.8,
                        timestamp=max(activity.timestamp, nearby.timestamp),
                        strikes=[strike, nearby.strike],
                        legs=[
                            {
                                'strike': nearby.strike,
                                'type': 'C',
                                'volume': nearby.call_volume,
                                'action': 'BUY'
                            },
                            {
                                'strike': strike,
                                'type': 'P',
                                'volume': activity.put_volume,
                                'action': 'SELL'
                            }
                        ],
                        total_volume=nearby.call_volume + activity.put_volume,
                        detection_method='synthetic_position',
                        supporting_evidence=[
                            f"Call strike: {nearby.strike} (pressure: {nearby.call_pressure_ratio:.2f})",
                            f"Put strike: {strike} (pressure: {activity.put_pressure_ratio:.2f})",
                            "Bullish risk reversal pattern"
                        ]
                    )

                    return pattern

        return None

    def _record_pattern(self, pattern: CoordinationPattern):
        """Record detected pattern for analysis"""
        self.recent_patterns.append(pattern)
        self.pattern_counts[pattern.pattern_type] += 1

        # Generate alert if high confidence
        if pattern.confidence > 0.8:
            alert = self._generate_alert(pattern)
            if alert:
                self.alert_history.append(alert)
                logger.info(f"Coordination alert: {alert.message}")

    def _generate_alert(self, pattern: CoordinationPattern) -> Optional[CoordinationAlert]:
        """Generate alert for significant patterns"""
        # Determine severity based on volume and confidence
        if pattern.total_volume > 1000 and pattern.confidence > 0.9:
            severity = "HIGH"
        elif pattern.total_volume > 500 or pattern.confidence > 0.8:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        # Create alert message
        message = f"{pattern.pattern_type.value} detected at strikes {pattern.strikes} "
        message += f"with {pattern.total_volume} total volume"

        # Calculate historical context
        similar_patterns = sum(1 for p in self.recent_patterns
                             if p.pattern_type == pattern.pattern_type)

        alert = CoordinationAlert(
            alert_id=f"coord_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}",
            timestamp=pattern.timestamp,
            severity=severity,
            pattern=pattern,
            message=message,
            institutional_confidence=pattern.confidence,
            similar_patterns_30d=similar_patterns
        )

        return alert

    def get_active_patterns(self, minutes: int = 30) -> List[CoordinationPattern]:
        """Get currently active coordination patterns"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)

        active_patterns = [
            p for p in self.recent_patterns
            if p.timestamp > cutoff_time
        ]

        # Sort by confidence and recency
        active_patterns.sort(key=lambda p: (p.confidence, p.timestamp), reverse=True)

        return active_patterns

    def get_strike_correlations(self, strikes: List[float],
                               window_minutes: int = 30) -> Dict[Tuple[float, float], float]:
        """Calculate correlation between strike activities"""
        correlations = {}
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        # Get time series for each strike
        strike_series = {}
        for strike in strikes:
            activities = [a for a in self.strike_activity[strike]
                         if a.timestamp > cutoff_time]

            if len(activities) > 5:
                # Create volume time series
                volumes = [a.call_volume + a.put_volume for a in activities]
                strike_series[strike] = volumes

        # Calculate pairwise correlations
        for i, strike1 in enumerate(strikes):
            for strike2 in strikes[i+1:]:
                if strike1 in strike_series and strike2 in strike_series:
                    series1 = strike_series[strike1]
                    series2 = strike_series[strike2]

                    # Align series lengths
                    min_len = min(len(series1), len(series2))
                    if min_len > 5:
                        corr = np.corrcoef(series1[-min_len:], series2[-min_len:])[0, 1]
                        correlations[(strike1, strike2)] = corr

        return correlations

    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics"""
        return {
            'patterns_detected': sum(self.pattern_counts.values()),
            'pattern_breakdown': dict(self.pattern_counts),
            'active_strikes': len([s for s, a in self.strike_activity.items() if a]),
            'alerts_generated': len(self.alert_history),
            'most_common_pattern': max(self.pattern_counts.items(),
                                      key=lambda x: x[1])[0].value if self.pattern_counts else None,
            'high_confidence_patterns': sum(1 for p in self.recent_patterns if p.confidence > 0.8)
        }


def create_coordination_detector(lookback_minutes: int = 30) -> CoordinationDetector:
    """
    Factory function to create coordination detector

    Args:
        lookback_minutes: Time window for analysis

    Returns:
        Configured CoordinationDetector instance
    """
    return CoordinationDetector(lookback_minutes=lookback_minutes)


if __name__ == "__main__":
    # Example usage
    detector = create_coordination_detector()

    # Simulate coordinated activity
    activity = StrikeActivity(
        strike=21000,
        timestamp=datetime.now(timezone.utc),
        call_volume=500,
        call_buy_volume=400,
        call_sell_volume=100,
        call_pressure_ratio=0.8,
        call_avg_size=25,
        put_volume=450,
        put_buy_volume=50,
        put_sell_volume=400,
        put_pressure_ratio=0.11,
        put_avg_size=22
    )

    # Process activity
    pattern = detector.process_strike_activity(activity)

    if pattern:
        print(f"\n🎯 Coordination Pattern Detected!")
        print(f"Type: {pattern.pattern_type.value}")
        print(f"Confidence: {pattern.confidence:.2%}")
        print(f"Strikes: {pattern.strikes}")
        print(f"Total Volume: {pattern.total_volume}")
        print(f"Evidence: {pattern.supporting_evidence}")

    # Simulate butterfly pattern
    print("\n\nSimulating butterfly pattern...")

    # Create activities for butterfly (21000, 21100, 21200)
    activities = [
        StrikeActivity(
            strike=21000,
            timestamp=datetime.now(timezone.utc),
            call_volume=200,
            call_buy_volume=150,
            call_pressure_ratio=0.75
        ),
        StrikeActivity(
            strike=21100,
            timestamp=datetime.now(timezone.utc) + timedelta(seconds=30),
            call_volume=400,
            call_buy_volume=100,
            call_pressure_ratio=0.25
        ),
        StrikeActivity(
            strike=21200,
            timestamp=datetime.now(timezone.utc) + timedelta(seconds=60),
            call_volume=180,
            call_buy_volume=140,
            call_pressure_ratio=0.78
        )
    ]

    for act in activities:
        act.put_volume = act.call_volume  # Add put activity
        act.put_pressure_ratio = act.call_pressure_ratio
        pattern = detector.process_strike_activity(act)
        if pattern and pattern.pattern_type == CoordinationType.BUTTERFLY:
            print(f"\n🦋 Butterfly Pattern Detected!")
            print(f"Confidence: {pattern.confidence:.2%}")
            print(f"Strikes: {pattern.strikes}")

    # Get statistics
    stats = detector.get_statistics()
    print(f"\n📊 Detector Statistics:")
    print(f"Total patterns: {stats['patterns_detected']}")
    print(f"Pattern breakdown: {stats['pattern_breakdown']}")
    print(f"Active strikes: {stats['active_strikes']}")
