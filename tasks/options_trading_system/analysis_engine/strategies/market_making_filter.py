#!/usr/bin/env python3
"""
Market Making Activity Filter for IFD v3.0

This module identifies and filters market making activity:
- Quote-based market making patterns
- High-frequency quote updates
- Spread maintenance behavior
- Two-sided quote patterns
- Market maker inventory management
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import numpy as np
from scipy import stats

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketMakerBehavior(Enum):
    """Types of market maker behaviors"""
    QUOTE_MAINTENANCE = "QUOTE_MAINTENANCE"          # Maintaining bid/ask spreads
    INVENTORY_BALANCING = "INVENTORY_BALANCING"      # Adjusting position inventory
    SPREAD_WIDENING = "SPREAD_WIDENING"             # Risk management via wider spreads
    QUOTE_STUFFING = "QUOTE_STUFFING"               # High-frequency quote updates
    LAYERING = "LAYERING"                           # Multiple price levels
    PEGGING = "PEGGING"                             # Following underlying price
    WITHDRAWAL = "WITHDRAWAL"                        # Pulling quotes in uncertainty
    AGGRESSIVE_QUOTING = "AGGRESSIVE_QUOTING"        # Tightening spreads for volume


@dataclass
class QuoteUpdate:
    """Individual quote update event"""
    timestamp: datetime
    instrument_id: int
    strike: float

    # Quote details
    bid_price: float
    bid_size: int
    ask_price: float
    ask_size: int

    # Derived metrics
    spread: float = 0.0
    mid_price: float = 0.0

    # Update characteristics
    update_type: str = ""  # NEW, MODIFY, CANCEL
    previous_bid: Optional[float] = None
    previous_ask: Optional[float] = None

    def __post_init__(self):
        """Calculate derived fields"""
        self.spread = self.ask_price - self.bid_price
        self.mid_price = (self.bid_price + self.ask_price) / 2


@dataclass
class MarketMakerProfile:
    """Profile of market maker behavior"""
    participant_id: str  # Could be derived from order patterns

    # Activity metrics
    quote_update_frequency: float  # Updates per minute
    average_spread: float
    spread_volatility: float

    # Quote characteristics
    typical_bid_size: float
    typical_ask_size: float
    size_symmetry: float  # How balanced bid/ask sizes are

    # Behavior patterns
    quote_persistence: float  # Average time quotes stay active
    fill_rate: float  # Percentage of quotes that trade
    inventory_bias: float  # Tendency to be long/short

    # Time patterns
    active_hours: List[int] = field(default_factory=list)
    quote_intensity_profile: Dict[int, float] = field(default_factory=dict)


@dataclass
class MarketMakingPattern:
    """Detected market making pattern"""
    pattern_type: MarketMakerBehavior
    confidence: float
    timestamp: datetime

    # Pattern details
    strike: float
    duration_seconds: float
    quote_count: int

    # Metrics
    average_spread: float
    spread_range: Tuple[float, float]
    update_frequency: float  # Updates per second

    # Volume metrics
    bid_volume: int
    ask_volume: int
    traded_volume: int

    # Classification
    is_market_maker: bool
    mm_probability: float
    participant_profile: Optional[MarketMakerProfile] = None

    # Evidence
    supporting_evidence: List[str] = field(default_factory=list)


@dataclass
class MarketQualityMetrics:
    """Market quality assessment"""
    timestamp: datetime
    strike: float

    # Liquidity metrics
    average_spread: float
    effective_spread: float  # Trade-weighted
    quoted_depth: float  # Average size at best bid/ask

    # Market maker presence
    mm_participation_rate: float  # % of quotes from MMs
    mm_volume_share: float  # % of volume from MMs

    # Quality scores
    liquidity_score: float  # 0-100
    stability_score: float  # Based on quote persistence
    efficiency_score: float  # Price discovery efficiency

    # Market conditions
    volatility_regime: str  # LOW, NORMAL, HIGH
    quote_intensity: float  # Quotes per minute
    trade_intensity: float  # Trades per minute


class QuoteAnalyzer:
    """Analyzes quote patterns for market making detection"""

    def __init__(self, window_seconds: int = 300):
        """
        Initialize quote analyzer

        Args:
            window_seconds: Analysis window (default 5 minutes)
        """
        self.window_seconds = window_seconds
        self.quote_history: Dict[float, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Pattern detection thresholds
        self.thresholds = {
            'min_updates_for_mm': 20,  # Minimum quote updates to classify as MM
            'update_frequency_threshold': 0.5,  # Updates per second
            'spread_consistency_threshold': 0.8,  # Spread coefficient of variation
            'size_symmetry_threshold': 0.7,  # Bid/ask size ratio
            'quote_persistence_ms': 100,  # Minimum quote lifetime
            'stuffing_frequency': 5.0,  # Updates per second for stuffing
            'layering_levels': 3  # Minimum price levels for layering
        }

        # Market maker identification
        self.identified_mm_patterns: Dict[str, MarketMakerProfile] = {}
        self.mm_detection_confidence: Dict[str, float] = defaultdict(float)

    def analyze_quote_pattern(self, quotes: List[QuoteUpdate]) -> MarketMakingPattern:
        """
        Analyze a sequence of quotes for market making patterns

        Args:
            quotes: List of quote updates

        Returns:
            Detected market making pattern
        """
        if len(quotes) < 2:
            return None

        strike = quotes[0].strike

        # Calculate metrics
        duration = (quotes[-1].timestamp - quotes[0].timestamp).total_seconds()
        if duration == 0:
            return None

        update_frequency = len(quotes) / duration

        # Spread analysis
        spreads = [q.spread for q in quotes if q.spread > 0]
        avg_spread = np.mean(spreads) if spreads else 0
        spread_std = np.std(spreads) if len(spreads) > 1 else 0
        spread_cv = spread_std / avg_spread if avg_spread > 0 else 1.0

        # Size analysis
        bid_sizes = [q.bid_size for q in quotes]
        ask_sizes = [q.ask_size for q in quotes]
        avg_bid_size = np.mean(bid_sizes)
        avg_ask_size = np.mean(ask_sizes)
        size_symmetry = min(avg_bid_size, avg_ask_size) / max(avg_bid_size, avg_ask_size) \
                       if max(avg_bid_size, avg_ask_size) > 0 else 0

        # Quote persistence analysis
        quote_lifetimes = []
        for i in range(1, len(quotes)):
            if quotes[i].update_type == 'MODIFY' or quotes[i].update_type == 'CANCEL':
                lifetime = (quotes[i].timestamp - quotes[i-1].timestamp).total_seconds() * 1000
                quote_lifetimes.append(lifetime)

        avg_persistence = np.mean(quote_lifetimes) if quote_lifetimes else 0

        # Detect specific behaviors
        behavior = self._classify_behavior(
            quotes, update_frequency, spread_cv, size_symmetry, avg_persistence
        )

        # Calculate MM probability
        mm_probability = self._calculate_mm_probability(
            update_frequency, spread_cv, size_symmetry, avg_persistence
        )

        # Create pattern
        pattern = MarketMakingPattern(
            pattern_type=behavior,
            confidence=mm_probability,
            timestamp=quotes[-1].timestamp,
            strike=strike,
            duration_seconds=duration,
            quote_count=len(quotes),
            average_spread=avg_spread,
            spread_range=(min(spreads), max(spreads)) if spreads else (0, 0),
            update_frequency=update_frequency,
            bid_volume=sum(bid_sizes),
            ask_volume=sum(ask_sizes),
            traded_volume=0,  # Would need trade data
            is_market_maker=mm_probability > 0.7,
            mm_probability=mm_probability,
            supporting_evidence=self._generate_evidence(
                update_frequency, spread_cv, size_symmetry, avg_persistence
            )
        )

        return pattern

    def _classify_behavior(self, quotes: List[QuoteUpdate],
                          update_freq: float, spread_cv: float,
                          size_symmetry: float, persistence: float) -> MarketMakerBehavior:
        """Classify the type of market making behavior"""
        # Quote stuffing detection
        if update_freq > self.thresholds['stuffing_frequency']:
            return MarketMakerBehavior.QUOTE_STUFFING

        # Check for spread widening
        spreads = [q.spread for q in quotes]
        if len(spreads) > 10:
            recent_spread = np.mean(spreads[-5:])
            older_spread = np.mean(spreads[-20:-10])
            if recent_spread > older_spread * 1.5:
                return MarketMakerBehavior.SPREAD_WIDENING

        # Check for inventory balancing (asymmetric sizes)
        if size_symmetry < 0.5:
            return MarketMakerBehavior.INVENTORY_BALANCING

        # Check for aggressive quoting (tight spreads)
        if len(spreads) > 0 and np.mean(spreads) < np.percentile(spreads, 10):
            return MarketMakerBehavior.AGGRESSIVE_QUOTING

        # Default to quote maintenance
        return MarketMakerBehavior.QUOTE_MAINTENANCE

    def _calculate_mm_probability(self, update_freq: float, spread_cv: float,
                                 size_symmetry: float, persistence: float) -> float:
        """Calculate probability that activity is from market maker"""
        score = 0.0

        # High update frequency
        if update_freq > self.thresholds['update_frequency_threshold']:
            score += 0.3 * min(1.0, update_freq / 2.0)

        # Consistent spreads
        if spread_cv < self.thresholds['spread_consistency_threshold']:
            score += 0.2 * (1.0 - spread_cv)

        # Symmetric sizes
        if size_symmetry > self.thresholds['size_symmetry_threshold']:
            score += 0.2 * size_symmetry

        # Quick quote updates
        if persistence < 1000:  # Less than 1 second
            score += 0.3 * (1.0 - min(1.0, persistence / 1000))

        return min(1.0, score)

    def _generate_evidence(self, update_freq: float, spread_cv: float,
                          size_symmetry: float, persistence: float) -> List[str]:
        """Generate evidence for market making classification"""
        evidence = []

        if update_freq > self.thresholds['update_frequency_threshold']:
            evidence.append(f"High quote frequency: {update_freq:.1f} updates/sec")

        if spread_cv < self.thresholds['spread_consistency_threshold']:
            evidence.append(f"Consistent spreads: CV={spread_cv:.2f}")

        if size_symmetry > self.thresholds['size_symmetry_threshold']:
            evidence.append(f"Symmetric bid/ask sizes: {size_symmetry:.2f}")

        if persistence < 1000:
            evidence.append(f"Rapid quote updates: {persistence:.0f}ms average")

        return evidence


class MarketMakingFilter:
    """
    Main market making detection and filtering system

    Features:
    - Real-time MM pattern detection
    - Quote pattern analysis
    - Market quality assessment
    - Institutional vs MM flow separation
    """

    def __init__(self, detection_window: int = 300):
        """
        Initialize market making filter

        Args:
            detection_window: Detection window in seconds
        """
        self.detection_window = detection_window
        self.quote_analyzer = QuoteAnalyzer(detection_window)

        # Quote tracking by strike
        self.quote_streams: Dict[float, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.detected_patterns: deque = deque(maxlen=1000)

        # Market quality tracking
        self.quality_history: Dict[float, deque] = defaultdict(lambda: deque(maxlen=100))

        # Statistics
        self.stats = {
            'quotes_processed': 0,
            'mm_patterns_detected': 0,
            'institutional_flow_detected': 0,
            'quote_stuffing_events': 0
        }

        logger.info(f"Market making filter initialized with {detection_window}s window")

    def process_quote(self, quote: QuoteUpdate) -> Tuple[bool, Optional[MarketMakingPattern]]:
        """
        Process quote and determine if it's market making

        Args:
            quote: Quote update to process

        Returns:
            Tuple of (is_market_maker, pattern)
        """
        self.stats['quotes_processed'] += 1

        # Store quote
        self.quote_streams[quote.strike].append(quote)

        # Get recent quotes for analysis
        recent_quotes = self._get_recent_quotes(quote.strike, seconds=30)

        if len(recent_quotes) >= self.quote_analyzer.thresholds['min_updates_for_mm']:
            # Analyze pattern
            pattern = self.quote_analyzer.analyze_quote_pattern(recent_quotes)

            if pattern:
                self.detected_patterns.append(pattern)

                if pattern.is_market_maker:
                    self.stats['mm_patterns_detected'] += 1
                    logger.debug(f"MM pattern detected at {quote.strike}: "
                               f"{pattern.pattern_type.value} ({pattern.confidence:.1%})")

                    if pattern.pattern_type == MarketMakerBehavior.QUOTE_STUFFING:
                        self.stats['quote_stuffing_events'] += 1

                    return True, pattern
                else:
                    self.stats['institutional_flow_detected'] += 1
                    return False, pattern

        # Not enough data to classify
        return False, None

    def _get_recent_quotes(self, strike: float, seconds: int) -> List[QuoteUpdate]:
        """Get quotes from recent time window"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        return [q for q in self.quote_streams[strike] if q.timestamp > cutoff_time]

    def filter_market_making(self, quotes: List[QuoteUpdate]) -> List[QuoteUpdate]:
        """
        Filter out market making quotes, keeping institutional

        Args:
            quotes: List of quotes to filter

        Returns:
            Filtered list with market making removed
        """
        institutional_quotes = []

        for quote in quotes:
            is_mm, pattern = self.process_quote(quote)

            if not is_mm:
                # Keep non-MM quotes
                institutional_quotes.append(quote)
            elif pattern and pattern.pattern_type == MarketMakerBehavior.AGGRESSIVE_QUOTING:
                # Keep aggressive MM quotes as they may indicate competition
                institutional_quotes.append(quote)

        return institutional_quotes

    def assess_market_quality(self, strike: float) -> MarketQualityMetrics:
        """
        Assess current market quality for a strike

        Args:
            strike: Strike price to assess

        Returns:
            Market quality metrics
        """
        recent_quotes = self._get_recent_quotes(strike, seconds=300)

        if len(recent_quotes) < 10:
            return None

        # Calculate spreads
        spreads = [q.spread for q in recent_quotes if q.spread > 0]
        avg_spread = np.mean(spreads) if spreads else 0

        # Quote depth
        bid_depths = [q.bid_size for q in recent_quotes]
        ask_depths = [q.ask_size for q in recent_quotes]
        avg_depth = (np.mean(bid_depths) + np.mean(ask_depths)) / 2

        # Market maker participation
        mm_quote_count = 0
        for i in range(0, len(recent_quotes), 10):
            batch = recent_quotes[i:i+10]
            if len(batch) >= 5:
                pattern = self.quote_analyzer.analyze_quote_pattern(batch)
                if pattern and pattern.is_market_maker:
                    mm_quote_count += len(batch)

        mm_participation = mm_quote_count / len(recent_quotes) if recent_quotes else 0

        # Quote intensity
        time_span = (recent_quotes[-1].timestamp - recent_quotes[0].timestamp).total_seconds() / 60
        quote_intensity = len(recent_quotes) / time_span if time_span > 0 else 0

        # Calculate quality scores
        liquidity_score = self._calculate_liquidity_score(avg_spread, avg_depth)
        stability_score = self._calculate_stability_score(spreads)
        efficiency_score = self._calculate_efficiency_score(recent_quotes)

        # Determine volatility regime
        spread_volatility = np.std(spreads) / avg_spread if avg_spread > 0 else 0
        if spread_volatility < 0.2:
            volatility_regime = "LOW"
        elif spread_volatility < 0.5:
            volatility_regime = "NORMAL"
        else:
            volatility_regime = "HIGH"

        metrics = MarketQualityMetrics(
            timestamp=datetime.now(timezone.utc),
            strike=strike,
            average_spread=avg_spread,
            effective_spread=avg_spread,  # Simplified - would use trade data
            quoted_depth=avg_depth,
            mm_participation_rate=mm_participation,
            mm_volume_share=0.0,  # Would need trade data
            liquidity_score=liquidity_score,
            stability_score=stability_score,
            efficiency_score=efficiency_score,
            volatility_regime=volatility_regime,
            quote_intensity=quote_intensity,
            trade_intensity=0.0  # Would need trade data
        )

        # Store quality metrics
        self.quality_history[strike].append(metrics)

        return metrics

    def _calculate_liquidity_score(self, spread: float, depth: float) -> float:
        """Calculate liquidity score (0-100)"""
        # Lower spread and higher depth = better liquidity
        spread_score = max(0, 100 - spread * 1000)  # Assumes spread in dollars
        depth_score = min(100, depth / 10)  # Assumes 1000 contracts is excellent

        return (spread_score + depth_score) / 2

    def _calculate_stability_score(self, spreads: List[float]) -> float:
        """Calculate market stability score (0-100)"""
        if len(spreads) < 2:
            return 50.0

        # Lower volatility = higher stability
        spread_cv = np.std(spreads) / np.mean(spreads) if np.mean(spreads) > 0 else 1.0

        return max(0, 100 * (1 - spread_cv))

    def _calculate_efficiency_score(self, quotes: List[QuoteUpdate]) -> float:
        """Calculate price discovery efficiency (0-100)"""
        if len(quotes) < 10:
            return 50.0

        # Check how quickly prices converge after changes
        mid_prices = [q.mid_price for q in quotes]

        # Autocorrelation as proxy for efficiency
        if len(mid_prices) > 1:
            autocorr = np.corrcoef(mid_prices[:-1], mid_prices[1:])[0, 1]
            # High autocorr = slow price discovery
            efficiency = max(0, 100 * (1 - abs(autocorr)))
        else:
            efficiency = 50.0

        return efficiency

    def identify_market_maker(self, quotes: List[QuoteUpdate],
                            participant_id: Optional[str] = None) -> MarketMakerProfile:
        """
        Build profile of market maker from quote patterns

        Args:
            quotes: Historical quotes from participant
            participant_id: Optional participant identifier

        Returns:
            Market maker profile
        """
        if len(quotes) < 50:
            return None

        # Calculate update frequency
        time_span = (quotes[-1].timestamp - quotes[0].timestamp).total_seconds()
        update_frequency = len(quotes) / (time_span / 60) if time_span > 0 else 0

        # Spread statistics
        spreads = [q.spread for q in quotes if q.spread > 0]
        avg_spread = np.mean(spreads) if spreads else 0
        spread_vol = np.std(spreads) if len(spreads) > 1 else 0

        # Size analysis
        bid_sizes = [q.bid_size for q in quotes]
        ask_sizes = [q.ask_size for q in quotes]

        # Quote persistence
        persistence_times = []
        for i in range(1, len(quotes)):
            if quotes[i].previous_bid is not None:
                persistence = (quotes[i].timestamp - quotes[i-1].timestamp).total_seconds()
                persistence_times.append(persistence)

        avg_persistence = np.mean(persistence_times) if persistence_times else 0

        # Active hours
        active_hours = list(set(q.timestamp.hour for q in quotes))

        # Create profile
        profile = MarketMakerProfile(
            participant_id=participant_id or f"MM_{hash(str(quotes[0].instrument_id))}",
            quote_update_frequency=update_frequency,
            average_spread=avg_spread,
            spread_volatility=spread_vol,
            typical_bid_size=np.median(bid_sizes),
            typical_ask_size=np.median(ask_sizes),
            size_symmetry=min(np.mean(bid_sizes), np.mean(ask_sizes)) /
                         max(np.mean(bid_sizes), np.mean(ask_sizes))
                         if max(np.mean(bid_sizes), np.mean(ask_sizes)) > 0 else 0,
            quote_persistence=avg_persistence,
            fill_rate=0.0,  # Would need trade data
            inventory_bias=(np.mean(bid_sizes) - np.mean(ask_sizes)) /
                          (np.mean(bid_sizes) + np.mean(ask_sizes))
                          if (np.mean(bid_sizes) + np.mean(ask_sizes)) > 0 else 0,
            active_hours=sorted(active_hours)
        )

        return profile

    def get_market_maker_activity(self, lookback_minutes: int = 60) -> Dict[str, Any]:
        """Get summary of market maker activity"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)

        recent_patterns = [p for p in self.detected_patterns if p.timestamp > cutoff_time]
        mm_patterns = [p for p in recent_patterns if p.is_market_maker]

        # Group by behavior type
        behavior_counts = defaultdict(int)
        for pattern in mm_patterns:
            behavior_counts[pattern.pattern_type.value] += 1

        # Calculate metrics
        total_quotes = sum(p.quote_count for p in recent_patterns)
        mm_quotes = sum(p.quote_count for p in mm_patterns)

        return {
            'period_minutes': lookback_minutes,
            'total_patterns': len(recent_patterns),
            'mm_patterns': len(mm_patterns),
            'mm_quote_share': mm_quotes / total_quotes if total_quotes > 0 else 0,
            'behavior_breakdown': dict(behavior_counts),
            'quote_stuffing_events': sum(1 for p in mm_patterns
                                       if p.pattern_type == MarketMakerBehavior.QUOTE_STUFFING),
            'average_mm_confidence': np.mean([p.confidence for p in mm_patterns]) if mm_patterns else 0
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get filter statistics"""
        return {
            'quotes_processed': self.stats['quotes_processed'],
            'mm_patterns_detected': self.stats['mm_patterns_detected'],
            'institutional_flow_detected': self.stats['institutional_flow_detected'],
            'quote_stuffing_events': self.stats['quote_stuffing_events'],
            'mm_detection_rate': self.stats['mm_patterns_detected'] /
                               (self.stats['mm_patterns_detected'] +
                                self.stats['institutional_flow_detected'])
                               if (self.stats['mm_patterns_detected'] +
                                   self.stats['institutional_flow_detected']) > 0 else 0,
            'active_strikes': len([s for s, q in self.quote_streams.items() if q])
        }


def create_market_making_filter(detection_window: int = 300) -> MarketMakingFilter:
    """
    Factory function to create market making filter

    Args:
        detection_window: Detection window in seconds

    Returns:
        Configured MarketMakingFilter instance
    """
    return MarketMakingFilter(detection_window=detection_window)


if __name__ == "__main__":
    # Example usage
    filter_system = create_market_making_filter()

    # Simulate market maker quote stream
    print("Simulating market maker quote pattern...")

    base_time = datetime.now(timezone.utc)
    strike = 21000

    # Generate rapid quote updates (market maker behavior)
    mm_quotes = []
    for i in range(50):
        quote = QuoteUpdate(
            timestamp=base_time + timedelta(milliseconds=i * 200),  # 5 updates/second
            instrument_id=12345,
            strike=strike,
            bid_price=100.50 + (i % 3) * 0.05,  # Small price variations
            bid_size=10 + (i % 5),
            ask_price=100.60 + (i % 3) * 0.05,
            ask_size=10 + (i % 5),
            update_type='MODIFY' if i > 0 else 'NEW'
        )
        mm_quotes.append(quote)

    # Process quotes
    for quote in mm_quotes:
        is_mm, pattern = filter_system.process_quote(quote)

        if pattern and is_mm:
            print(f"\n🤖 Market Maker Detected!")
            print(f"Pattern: {pattern.pattern_type.value}")
            print(f"Confidence: {pattern.mm_probability:.1%}")
            print(f"Update frequency: {pattern.update_frequency:.1f} updates/sec")
            print(f"Average spread: ${pattern.average_spread:.2f}")
            print(f"Evidence: {pattern.supporting_evidence}")
            break

    # Simulate institutional order (slower, larger)
    print("\n\nSimulating institutional quote pattern...")

    inst_quotes = []
    for i in range(10):
        quote = QuoteUpdate(
            timestamp=base_time + timedelta(seconds=i * 5),  # Slower updates
            instrument_id=12346,
            strike=21100,
            bid_price=105.00 - i * 0.10,  # Directional movement
            bid_size=100,  # Larger size
            ask_price=105.50 - i * 0.10,
            ask_size=100,
            update_type='MODIFY' if i > 0 else 'NEW'
        )
        inst_quotes.append(quote)

    # Process institutional quotes
    for quote in inst_quotes:
        is_mm, pattern = filter_system.process_quote(quote)

    # Check market quality
    quality = filter_system.assess_market_quality(strike)
    if quality:
        print(f"\n📊 Market Quality for strike {strike}:")
        print(f"Liquidity Score: {quality.liquidity_score:.1f}/100")
        print(f"Stability Score: {quality.stability_score:.1f}/100")
        print(f"MM Participation: {quality.mm_participation_rate:.1%}")
        print(f"Volatility Regime: {quality.volatility_regime}")

    # Get activity summary
    activity = filter_system.get_market_maker_activity(lookback_minutes=10)
    print(f"\n📈 Market Maker Activity Summary:")
    print(f"Total patterns: {activity['total_patterns']}")
    print(f"MM patterns: {activity['mm_patterns']}")
    print(f"MM quote share: {activity['mm_quote_share']:.1%}")
    print(f"Behavior breakdown: {activity['behavior_breakdown']}")

    # Get statistics
    stats = filter_system.get_statistics()
    print(f"\n📊 Filter Statistics:")
    print(f"Quotes processed: {stats['quotes_processed']}")
    print(f"MM patterns: {stats['mm_patterns_detected']}")
    print(f"Institutional flow: {stats['institutional_flow_detected']}")
    print(f"MM detection rate: {stats['mm_detection_rate']:.1%}")
