#!/usr/bin/env python3
"""
Volatility Crush Pattern Detector for IFD v3.0

This module detects volatility-related patterns and events:
- Pre-earnings volatility expansion
- Post-event volatility crush
- Term structure anomalies
- Skew changes indicating directional bets
- Volatility regime transitions
"""

import logging
from datetime import datetime, timedelta, timezone
from utils.timezone_utils import get_eastern_time, get_utc_time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import numpy as np
from scipy import stats
from scipy.interpolate import interp1d

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VolatilityEventType(Enum):
    """Types of volatility events"""
    PRE_EARNINGS_EXPANSION = "PRE_EARNINGS_EXPANSION"
    POST_EARNINGS_CRUSH = "POST_EARNINGS_CRUSH"
    FOMC_VOLATILITY = "FOMC_VOLATILITY"
    ECONOMIC_DATA_RELEASE = "ECONOMIC_DATA_RELEASE"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    VOLATILITY_COLLAPSE = "VOLATILITY_COLLAPSE"
    TERM_STRUCTURE_INVERSION = "TERM_STRUCTURE_INVERSION"
    SKEW_SHIFT = "SKEW_SHIFT"
    REGIME_CHANGE = "REGIME_CHANGE"


@dataclass
class ImpliedVolatilityPoint:
    """IV data point for a specific strike and time"""
    timestamp: datetime
    strike: float
    expiration: datetime

    # IV metrics
    implied_volatility: float
    iv_bid: float
    iv_ask: float

    # Greeks
    vega: float
    delta: float
    gamma: float

    # Volume and OI
    volume: int
    open_interest: int

    # Calculated fields
    moneyness: float = 0.0  # strike / underlying
    time_to_expiry: float = 0.0  # in years

    def __post_init__(self):
        """Calculate derived fields"""
        if self.time_to_expiry == 0.0:
            self.time_to_expiry = (self.expiration - self.timestamp).total_seconds() / (365.25 * 24 * 3600)


@dataclass
class VolatilityPattern:
    """Detected volatility pattern"""
    pattern_type: VolatilityEventType
    confidence: float
    timestamp: datetime

    # Pattern details
    affected_strikes: List[float]
    affected_expirations: List[datetime]

    # Metrics
    iv_change_magnitude: float  # Percentage change
    average_iv_before: float
    average_iv_after: float

    # Volume indicators
    volume_surge_ratio: float  # Current vs average
    vega_exposure: float  # Total vega in contracts

    # Market context
    underlying_price: float
    historical_volatility: float
    iv_percentile: float  # Current IV vs historical

    # Additional evidence
    supporting_metrics: Dict[str, float] = field(default_factory=dict)
    detection_notes: List[str] = field(default_factory=list)


@dataclass
class VolatilityCrushAlert:
    """Alert for significant volatility event"""
    alert_id: str
    timestamp: datetime
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    event_type: VolatilityEventType

    # Event details
    expected_event_time: Optional[datetime]
    current_iv_level: float
    expected_iv_change: float  # Percentage

    # Affected contracts
    primary_strikes: List[float]
    primary_expiration: datetime

    # Trading implications
    suggested_action: str
    risk_level: str
    estimated_pnl_impact: Optional[float]

    # Historical context
    similar_events_count: int
    average_historical_move: float
    success_rate: float


class VolatilityTermStructure:
    """Manages volatility term structure analysis"""

    def __init__(self):
        self.iv_surface: Dict[datetime, Dict[float, float]] = defaultdict(dict)
        self.atm_term_structure: Dict[datetime, float] = {}

    def update_surface(self, iv_point: ImpliedVolatilityPoint):
        """Update IV surface with new data point"""
        self.iv_surface[iv_point.expiration][iv_point.strike] = iv_point.implied_volatility

        # Update ATM term structure (simplified - using closest to money)
        if iv_point.moneyness is not None and 0.95 < iv_point.moneyness < 1.05:
            current_atm = self.atm_term_structure.get(iv_point.expiration, iv_point.implied_volatility)
            # Weighted average if multiple near-ATM strikes
            self.atm_term_structure[iv_point.expiration] = (current_atm + iv_point.implied_volatility) / 2

    def get_term_structure_slope(self) -> Optional[float]:
        """Calculate term structure slope (front vs back month)"""
        if len(self.atm_term_structure) < 2:
            return None

        sorted_expiries = sorted(self.atm_term_structure.keys())
        front_month_iv = self.atm_term_structure[sorted_expiries[0]]
        back_month_iv = self.atm_term_structure[sorted_expiries[-1]]

        time_diff = (sorted_expiries[-1] - sorted_expiries[0]).total_seconds() / (365.25 * 24 * 3600)
        if time_diff > 0:
            return (back_month_iv - front_month_iv) / time_diff

        return None

    def detect_inversion(self) -> bool:
        """Detect term structure inversion (front > back)"""
        slope = self.get_term_structure_slope()
        return slope is not None and slope < -0.1  # Significant negative slope

    def get_skew(self, expiration: datetime,
                  delta_range: Tuple[float, float] = (0.25, 0.75)) -> Optional[float]:
        """Calculate volatility skew for an expiration"""
        if expiration not in self.iv_surface:
            return None

        strikes = sorted(self.iv_surface[expiration].keys())
        if len(strikes) < 3:
            return None

        # Simple skew: (25 delta put IV - 25 delta call IV)
        # This is simplified - in practice would use actual deltas
        otm_put_strike = strikes[0]  # Lowest strike
        otm_call_strike = strikes[-1]  # Highest strike

        put_iv = self.iv_surface[expiration][otm_put_strike]
        call_iv = self.iv_surface[expiration][otm_call_strike]

        return put_iv - call_iv


class VolatilityCrushDetector:
    """
    Main volatility pattern detection engine

    Features:
    - IV surface tracking
    - Term structure analysis
    - Event-driven volatility detection
    - Historical pattern matching
    """

    def __init__(self, lookback_days: int = 30,
                 crush_threshold: float = 0.20):
        """
        Initialize volatility crush detector

        Args:
            lookback_days: Historical window for analysis
            crush_threshold: Minimum IV drop for crush detection (20%)
        """
        self.lookback_days = lookback_days
        self.crush_threshold = crush_threshold

        # IV tracking
        self.iv_history: Dict[float, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.term_structure = VolatilityTermStructure()

        # Pattern detection
        self.detected_patterns: deque = deque(maxlen=500)
        self.active_alerts: List[VolatilityCrushAlert] = []

        # Historical statistics
        self.historical_iv_levels: deque = deque(maxlen=5000)
        self.event_history: Dict[VolatilityEventType, List[VolatilityPattern]] = defaultdict(list)

        # Thresholds
        self.thresholds = {
            'expansion_threshold': 0.15,  # 15% IV increase
            'crush_threshold': crush_threshold,
            'spike_threshold': 0.30,  # 30% sudden increase
            'volume_surge_ratio': 3.0,  # 3x normal volume
            'high_iv_percentile': 80,  # 80th percentile
            'low_iv_percentile': 20   # 20th percentile
        }

        # Known events (would be loaded from calendar)
        self.known_events = {
            'earnings': [],
            'fomc': [],
            'economic_data': []
        }

        logger.info(f"Volatility crush detector initialized with {lookback_days}d lookback")

    def process_iv_update(self, iv_point: ImpliedVolatilityPoint) -> Optional[VolatilityPattern]:
        """
        Process new IV data point and detect patterns

        Args:
            iv_point: New implied volatility data

        Returns:
            Detected pattern if found
        """
        # Store IV history
        self.iv_history[iv_point.strike].append(iv_point)
        self.historical_iv_levels.append(iv_point.implied_volatility)

        # Update term structure
        self.term_structure.update_surface(iv_point)

        # Check for various patterns
        patterns = []

        # 1. Check for volatility spike
        spike_pattern = self._check_volatility_spike(iv_point)
        if spike_pattern:
            patterns.append(spike_pattern)

        # 2. Check for volatility crush
        crush_pattern = self._check_volatility_crush(iv_point)
        if crush_pattern:
            patterns.append(crush_pattern)

        # 3. Check for term structure anomalies
        if self.term_structure.detect_inversion():
            inversion_pattern = self._create_term_structure_pattern()
            if inversion_pattern:
                patterns.append(inversion_pattern)

        # 4. Check for pre-event buildup
        buildup_pattern = self._check_pre_event_buildup(iv_point)
        if buildup_pattern:
            patterns.append(buildup_pattern)

        # Record patterns and generate alerts
        for pattern in patterns:
            self._record_pattern(pattern)
            self._generate_alert(pattern)

        # Return highest confidence pattern
        return max(patterns, key=lambda p: p.confidence) if patterns else None

    def _check_volatility_spike(self, iv_point: ImpliedVolatilityPoint) -> Optional[VolatilityPattern]:
        """Check for sudden volatility spike"""
        strike_history = list(self.iv_history[iv_point.strike])

        if len(strike_history) < 10:
            return None

        # Get recent IV average (exclude current)
        recent_ivs = [p.implied_volatility for p in strike_history[-11:-1]]
        avg_iv = np.mean(recent_ivs)
        std_iv = np.std(recent_ivs)

        # Check for significant spike
        iv_change = (iv_point.implied_volatility - avg_iv) / avg_iv

        if iv_change > self.thresholds['spike_threshold']:
            # Calculate z-score
            z_score = (iv_point.implied_volatility - avg_iv) / (std_iv + 0.001)

            # Check volume surge
            recent_volumes = [p.volume for p in strike_history[-11:-1]]
            avg_volume = np.mean(recent_volumes)
            volume_surge = iv_point.volume / (avg_volume + 1)

            confidence = min(0.95, 0.5 + min(0.45, z_score / 10))

            pattern = VolatilityPattern(
                pattern_type=VolatilityEventType.VOLATILITY_SPIKE,
                confidence=confidence,
                timestamp=iv_point.timestamp,
                affected_strikes=[iv_point.strike],
                affected_expirations=[iv_point.expiration],
                iv_change_magnitude=iv_change * 100,
                average_iv_before=avg_iv,
                average_iv_after=iv_point.implied_volatility,
                volume_surge_ratio=volume_surge,
                vega_exposure=iv_point.vega * iv_point.volume,
                underlying_price=iv_point.strike / iv_point.moneyness if iv_point.moneyness > 0 else 0,
                historical_volatility=std_iv,
                iv_percentile=self._calculate_iv_percentile(iv_point.implied_volatility),
                supporting_metrics={
                    'z_score': z_score,
                    'volume_surge': volume_surge,
                    'iv_change_pct': iv_change * 100
                },
                detection_notes=[
                    f"IV spiked {iv_change*100:.1f}% above recent average",
                    f"Volume surge: {volume_surge:.1f}x normal",
                    f"Z-score: {z_score:.2f}"
                ]
            )

            return pattern

        return None

    def _check_volatility_crush(self, iv_point: ImpliedVolatilityPoint) -> Optional[VolatilityPattern]:
        """Check for volatility crush pattern"""
        strike_history = list(self.iv_history[iv_point.strike])

        if len(strike_history) < 5:
            return None

        # Look for peak in recent history
        recent_ivs = [p.implied_volatility for p in strike_history[-10:]]
        peak_iv = max(recent_ivs[:-1])  # Exclude current
        peak_idx = recent_ivs[:-1].index(peak_iv)

        # Check if current IV is significantly lower than recent peak
        iv_drop = (peak_iv - iv_point.implied_volatility) / peak_iv

        if iv_drop > self.thresholds['crush_threshold']:
            # Verify it's a sustained drop (not just volatility)
            post_peak_ivs = recent_ivs[peak_idx+1:]
            if len(post_peak_ivs) > 2 and all(iv < peak_iv * 0.9 for iv in post_peak_ivs):

                confidence = min(0.9, 0.5 + iv_drop)

                pattern = VolatilityPattern(
                    pattern_type=VolatilityEventType.POST_EARNINGS_CRUSH,
                    confidence=confidence,
                    timestamp=iv_point.timestamp,
                    affected_strikes=[iv_point.strike],
                    affected_expirations=[iv_point.expiration],
                    iv_change_magnitude=-iv_drop * 100,
                    average_iv_before=peak_iv,
                    average_iv_after=iv_point.implied_volatility,
                    volume_surge_ratio=1.0,  # Would calculate if needed
                    vega_exposure=iv_point.vega * iv_point.volume,
                    underlying_price=iv_point.strike / iv_point.moneyness if iv_point.moneyness > 0 else 0,
                    historical_volatility=np.std(recent_ivs),
                    iv_percentile=self._calculate_iv_percentile(iv_point.implied_volatility),
                    supporting_metrics={
                        'peak_iv': peak_iv,
                        'current_iv': iv_point.implied_volatility,
                        'drop_percentage': iv_drop * 100,
                        'bars_since_peak': len(post_peak_ivs)
                    },
                    detection_notes=[
                        f"IV dropped {iv_drop*100:.1f}% from recent peak",
                        f"Peak IV: {peak_iv:.1%}, Current: {iv_point.implied_volatility:.1%}",
                        "Sustained decline suggests event volatility crush"
                    ]
                )

                return pattern

        return None

    def _check_pre_event_buildup(self, iv_point: ImpliedVolatilityPoint) -> Optional[VolatilityPattern]:
        """Check for pre-event volatility buildup"""
        # Check if near expiration (potential event)
        days_to_expiry = (iv_point.expiration - iv_point.timestamp).days

        if days_to_expiry > 7:  # Only check if expiration is within a week
            return None

        strike_history = list(self.iv_history[iv_point.strike])

        if len(strike_history) < 20:
            return None

        # Look for steady IV increase over past sessions
        lookback_points = strike_history[-20:]
        iv_series = [p.implied_volatility for p in lookback_points]

        # Calculate trend
        x = np.arange(len(iv_series))
        slope, intercept, r_value, _, _ = stats.linregress(x, iv_series)

        # Check for positive trend with good fit
        if slope > 0.001 and r_value > 0.7:
            # Calculate total IV expansion
            start_iv = iv_series[0]
            current_iv = iv_series[-1]
            expansion = (current_iv - start_iv) / start_iv

            if expansion > self.thresholds['expansion_threshold']:
                # Check for accelerating volume
                volumes = [p.volume for p in lookback_points]
                recent_vol_avg = np.mean(volumes[-5:])
                older_vol_avg = np.mean(volumes[-20:-10])
                vol_acceleration = recent_vol_avg / (older_vol_avg + 1)

                confidence = min(0.85, r_value * 0.9)

                pattern = VolatilityPattern(
                    pattern_type=VolatilityEventType.PRE_EARNINGS_EXPANSION,
                    confidence=confidence,
                    timestamp=iv_point.timestamp,
                    affected_strikes=[iv_point.strike],
                    affected_expirations=[iv_point.expiration],
                    iv_change_magnitude=expansion * 100,
                    average_iv_before=start_iv,
                    average_iv_after=current_iv,
                    volume_surge_ratio=vol_acceleration,
                    vega_exposure=iv_point.vega * iv_point.volume,
                    underlying_price=iv_point.strike / iv_point.moneyness if iv_point.moneyness > 0 else 0,
                    historical_volatility=np.std(iv_series),
                    iv_percentile=self._calculate_iv_percentile(current_iv),
                    supporting_metrics={
                        'trend_slope': slope,
                        'trend_r_squared': r_value ** 2,
                        'days_to_expiry': days_to_expiry,
                        'volume_acceleration': vol_acceleration
                    },
                    detection_notes=[
                        f"IV expanded {expansion*100:.1f}% over {len(iv_series)} periods",
                        f"Strong trend (R²={r_value**2:.2f})",
                        f"Volume acceleration: {vol_acceleration:.1f}x",
                        f"Event likely within {days_to_expiry} days"
                    ]
                )

                return pattern

        return None

    def _create_term_structure_pattern(self) -> Optional[VolatilityPattern]:
        """Create pattern for term structure inversion"""
        if not self.term_structure.atm_term_structure:
            return None

        sorted_expiries = sorted(self.term_structure.atm_term_structure.items())
        if len(sorted_expiries) < 2:
            return None

        front_exp, front_iv = sorted_expiries[0]
        back_exp, back_iv = sorted_expiries[-1]

        inversion_magnitude = (front_iv - back_iv) / back_iv

        pattern = VolatilityPattern(
            pattern_type=VolatilityEventType.TERM_STRUCTURE_INVERSION,
            confidence=min(0.9, abs(inversion_magnitude) * 2),
            timestamp=datetime.now(timezone.utc),
            affected_strikes=[],  # All ATM strikes
            affected_expirations=[front_exp, back_exp],
            iv_change_magnitude=inversion_magnitude * 100,
            average_iv_before=back_iv,
            average_iv_after=front_iv,
            volume_surge_ratio=1.0,
            vega_exposure=0.0,  # Would need to calculate
            underlying_price=0.0,  # Would need current price
            historical_volatility=0.0,
            iv_percentile=50.0,  # Placeholder
            supporting_metrics={
                'front_month_iv': front_iv,
                'back_month_iv': back_iv,
                'inversion_ratio': front_iv / back_iv
            },
            detection_notes=[
                f"Term structure inverted: Front {front_iv:.1%} > Back {back_iv:.1%}",
                f"Inversion magnitude: {inversion_magnitude*100:.1f}%",
                "Indicates near-term event risk"
            ]
        )

        return pattern

    def _calculate_iv_percentile(self, current_iv: float) -> float:
        """Calculate IV percentile rank"""
        if len(self.historical_iv_levels) < 100:
            return 50.0

        return stats.percentileofscore(list(self.historical_iv_levels), current_iv)

    def _record_pattern(self, pattern: VolatilityPattern):
        """Record detected pattern"""
        self.detected_patterns.append(pattern)
        self.event_history[pattern.pattern_type].append(pattern)

        logger.info(f"Volatility pattern detected: {pattern.pattern_type.value} "
                   f"with {pattern.confidence:.1%} confidence")

    def _generate_alert(self, pattern: VolatilityPattern) -> Optional[VolatilityCrushAlert]:
        """Generate alert for significant patterns"""
        # Only alert on high-confidence, significant patterns
        if pattern.confidence < 0.7 or abs(pattern.iv_change_magnitude) < 15:
            return None

        # Determine severity
        if abs(pattern.iv_change_magnitude) > 30 and pattern.confidence > 0.85:
            severity = "CRITICAL"
        elif abs(pattern.iv_change_magnitude) > 20 or pattern.confidence > 0.8:
            severity = "HIGH"
        else:
            severity = "MEDIUM"

        # Get historical context
        similar_events = self.event_history[pattern.pattern_type]
        historical_moves = [p.iv_change_magnitude for p in similar_events[-10:]]
        avg_historical_move = np.mean(historical_moves) if historical_moves else pattern.iv_change_magnitude

        # Create alert
        alert = VolatilityCrushAlert(
            alert_id=f"vol_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}",
            timestamp=pattern.timestamp,
            severity=severity,
            event_type=pattern.pattern_type,
            expected_event_time=None,  # Would be set based on event calendar
            current_iv_level=pattern.average_iv_after,
            expected_iv_change=pattern.iv_change_magnitude,
            primary_strikes=pattern.affected_strikes,
            primary_expiration=pattern.affected_expirations[0] if pattern.affected_expirations else None,
            suggested_action=self._get_suggested_action(pattern),
            risk_level="HIGH" if abs(pattern.iv_change_magnitude) > 25 else "MEDIUM",
            estimated_pnl_impact=None,  # Would calculate based on position
            similar_events_count=len(similar_events),
            average_historical_move=avg_historical_move,
            success_rate=0.0  # Would calculate from historical outcomes
        )

        self.active_alerts.append(alert)
        return alert

    def _get_suggested_action(self, pattern: VolatilityPattern) -> str:
        """Get suggested trading action for pattern"""
        if pattern.pattern_type == VolatilityEventType.PRE_EARNINGS_EXPANSION:
            return "Consider volatility selling strategies (iron condors, strangles)"
        elif pattern.pattern_type == VolatilityEventType.POST_EARNINGS_CRUSH:
            return "Close short volatility positions, consider directional plays"
        elif pattern.pattern_type == VolatilityEventType.VOLATILITY_SPIKE:
            return "Review hedges, consider vol selling if spike is excessive"
        elif pattern.pattern_type == VolatilityEventType.TERM_STRUCTURE_INVERSION:
            return "Focus on front-month strategies, prepare for event"
        else:
            return "Monitor closely for follow-through"

    def get_active_alerts(self) -> List[VolatilityCrushAlert]:
        """Get currently active alerts"""
        # Filter for recent alerts
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        return [a for a in self.active_alerts if a.timestamp > cutoff_time]

    def get_iv_surface_snapshot(self) -> Dict[str, Any]:
        """Get current IV surface snapshot"""
        snapshot = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'expirations': {},
            'term_structure': {},
            'statistics': {}
        }

        # Add term structure
        for exp, iv in self.term_structure.atm_term_structure.items():
            snapshot['term_structure'][exp.isoformat()] = iv

        # Add surface data
        for exp, strikes in self.term_structure.iv_surface.items():
            snapshot['expirations'][exp.isoformat()] = dict(strikes)

        # Add statistics
        if self.historical_iv_levels:
            snapshot['statistics'] = {
                'current_iv_percentile': self._calculate_iv_percentile(
                    list(self.historical_iv_levels)[-1]
                ),
                'iv_mean': np.mean(list(self.historical_iv_levels)),
                'iv_std': np.std(list(self.historical_iv_levels)),
                'patterns_detected_24h': len([p for p in self.detected_patterns
                                            if p.timestamp > datetime.now(timezone.utc) - timedelta(hours=24)])
            }

        return snapshot

    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics"""
        stats = {
            'total_patterns_detected': len(self.detected_patterns),
            'active_alerts': len(self.get_active_alerts()),
            'pattern_breakdown': {},
            'average_confidence': 0.0,
            'iv_levels': {}
        }

        # Pattern breakdown
        for event_type in VolatilityEventType:
            count = len(self.event_history[event_type])
            if count > 0:
                stats['pattern_breakdown'][event_type.value] = count

        # Average confidence
        if self.detected_patterns:
            stats['average_confidence'] = np.mean([p.confidence for p in self.detected_patterns])

        # Current IV levels
        if self.historical_iv_levels:
            current_iv = list(self.historical_iv_levels)[-1]
            stats['iv_levels'] = {
                'current': current_iv,
                'percentile': self._calculate_iv_percentile(current_iv),
                '30d_mean': np.mean(list(self.historical_iv_levels)),
                '30d_std': np.std(list(self.historical_iv_levels))
            }

        return stats


def create_volatility_detector(lookback_days: int = 30) -> VolatilityCrushDetector:
    """
    Factory function to create volatility crush detector

    Args:
        lookback_days: Historical window for analysis

    Returns:
        Configured VolatilityCrushDetector instance
    """
    return VolatilityCrushDetector(lookback_days=lookback_days)


if __name__ == "__main__":
    # Example usage
    detector = create_volatility_detector()

    # Simulate IV expansion pattern
    print("Simulating pre-earnings IV expansion...")

    base_iv = 0.25
    for i in range(20):
        # Gradually increase IV
        current_iv = base_iv * (1 + 0.02 * i)  # 2% increase per period

        iv_point = ImpliedVolatilityPoint(
            timestamp=datetime.now(timezone.utc) - timedelta(hours=20-i),
            strike=21000,
            expiration=datetime.now(timezone.utc) + timedelta(days=3),
            implied_volatility=current_iv,
            iv_bid=current_iv - 0.01,
            iv_ask=current_iv + 0.01,
            vega=50,
            delta=0.5,
            gamma=0.01,
            volume=100 + i * 10,  # Increasing volume
            open_interest=1000,
            moneyness=1.0
        )

        pattern = detector.process_iv_update(iv_point)

        if pattern and i == 19:  # Last point
            print(f"\n📈 Pattern Detected: {pattern.pattern_type.value}")
            print(f"Confidence: {pattern.confidence:.1%}")
            print(f"IV Change: {pattern.iv_change_magnitude:.1f}%")
            print(f"Detection Notes:")
            for note in pattern.detection_notes:
                print(f"  - {note}")

    # Simulate volatility crush
    print("\n\nSimulating post-earnings volatility crush...")

    # High IV before event
    for i in range(5):
        iv_point = ImpliedVolatilityPoint(
            timestamp=datetime.now(timezone.utc) - timedelta(hours=10-i),
            strike=21000,
            expiration=datetime.now(timezone.utc) + timedelta(days=7),
            implied_volatility=0.45,  # High IV
            iv_bid=0.44,
            iv_ask=0.46,
            vega=100,
            delta=0.5,
            gamma=0.02,
            volume=500,
            open_interest=2000,
            moneyness=1.0
        )
        detector.process_iv_update(iv_point)

    # Crush after event
    for i in range(5):
        current_iv = 0.45 * (1 - 0.1 * i)  # 10% drop per period

        iv_point = ImpliedVolatilityPoint(
            timestamp=datetime.now(timezone.utc) - timedelta(hours=5-i),
            strike=21000,
            expiration=datetime.now(timezone.utc) + timedelta(days=7),
            implied_volatility=current_iv,
            iv_bid=current_iv - 0.01,
            iv_ask=current_iv + 0.01,
            vega=100,
            delta=0.5,
            gamma=0.02,
            volume=300,
            open_interest=2000,
            moneyness=1.0
        )

        pattern = detector.process_iv_update(iv_point)

        if pattern and pattern.pattern_type == VolatilityEventType.POST_EARNINGS_CRUSH:
            print(f"\n💥 Volatility Crush Detected!")
            print(f"Confidence: {pattern.confidence:.1%}")
            print(f"IV Drop: {abs(pattern.iv_change_magnitude):.1f}%")
            print(f"Before: {pattern.average_iv_before:.1%}, After: {pattern.average_iv_after:.1%}")

    # Get statistics
    stats = detector.get_statistics()
    print(f"\n📊 Detector Statistics:")
    print(f"Total patterns: {stats['total_patterns_detected']}")
    print(f"Active alerts: {stats['active_alerts']}")
    print(f"Pattern breakdown: {stats['pattern_breakdown']}")

    # Get active alerts
    alerts = detector.get_active_alerts()
    if alerts:
        print(f"\n🚨 Active Alerts:")
        for alert in alerts:
            print(f"  - {alert.severity}: {alert.event_type.value}")
            print(f"    Suggested: {alert.suggested_action}")
