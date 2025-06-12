#!/usr/bin/env python3
"""
Signal Validation Engine for Shadow Trading

This module provides comprehensive signal validation and false positive detection
mechanisms to ensure high-quality signals in the shadow trading system.
"""

import logging
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of signal validation"""
    signal_id: str
    timestamp: str
    overall_score: float
    is_valid: bool
    confidence_adjustment: float
    validation_flags: List[str]
    false_positive_probability: float
    historical_correlation: float
    market_context_score: float
    timing_score: float
    technical_score: float
    reasoning: List[str]


@dataclass
class HistoricalPattern:
    """Historical signal pattern for validation"""
    algorithm_version: str
    signal_type: str
    market_conditions: Dict[str, Any]
    confidence_range: Tuple[float, float]
    success_rate: float
    average_hold_time: float
    avg_profit_loss: float
    sample_size: int
    last_updated: str


class MarketContextAnalyzer:
    """Analyzes current market context for signal validation"""

    def __init__(self):
        self.market_hours = {
            'market_open': '09:30',
            'market_close': '16:00',
            'optimal_start': '10:00',
            'optimal_end': '15:30'
        }

    def analyze_market_timing(self, signal_timestamp: str) -> Dict[str, Any]:
        """Analyze if signal timing aligns with optimal market conditions"""
        try:
            signal_time = datetime.fromisoformat(signal_timestamp.replace('Z', '+00:00'))
            signal_hour = signal_time.hour
            signal_minute = signal_time.minute

            # Convert to decimal hour for easier comparison
            decimal_hour = signal_hour + (signal_minute / 60.0)

            # Market timing scores
            timing_analysis = {
                'decimal_hour': decimal_hour,
                'is_market_hours': 9.5 <= decimal_hour <= 16.0,
                'is_optimal_hours': 10.0 <= decimal_hour <= 15.5,
                'is_opening_rush': 9.5 <= decimal_hour <= 10.5,
                'is_closing_rush': 15.0 <= decimal_hour <= 16.0,
                'is_lunch_time': 12.0 <= decimal_hour <= 13.0,
                'timing_score': self._calculate_timing_score(decimal_hour),
                'day_of_week': signal_time.weekday(),  # 0=Monday, 4=Friday
                'is_weekday': signal_time.weekday() < 5
            }

            return timing_analysis

        except Exception as e:
            logger.error(f"Error analyzing market timing: {e}")
            return {
                'timing_score': 0.5,
                'is_market_hours': False,
                'is_optimal_hours': False
            }

    def _calculate_timing_score(self, decimal_hour: float) -> float:
        """Calculate timing quality score (0-1)"""
        if not (9.5 <= decimal_hour <= 16.0):
            return 0.1  # After hours

        if 10.0 <= decimal_hour <= 15.5:
            return 1.0  # Optimal hours

        if 9.5 <= decimal_hour <= 10.0 or 15.5 <= decimal_hour <= 16.0:
            return 0.8  # Market open/close

        if 12.0 <= decimal_hour <= 13.0:
            return 0.6  # Lunch time

        return 0.7  # Other market hours

    def analyze_market_volatility_context(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current market volatility for signal validation"""
        try:
            # Extract volatility indicators from market data
            contracts = market_data.get('normalized_data', {}).get('contracts', [])

            if not contracts:
                return {
                    'volatility_score': 0.5,
                    'volume_concentration': 0.5,
                    'bid_ask_spread_health': 0.5
                }

            # Calculate volume concentration
            volumes = [c.get('volume', 0) for c in contracts if c.get('volume', 0) > 0]
            total_volume = sum(volumes)

            if total_volume > 0:
                # Calculate Herfindahl-Hirschman Index for volume concentration
                volume_shares = [(v / total_volume) ** 2 for v in volumes]
                hhi = sum(volume_shares)
                volume_concentration = 1 - hhi  # 0 = concentrated, 1 = dispersed
            else:
                volume_concentration = 0.5

            # Calculate bid-ask spread health
            spreads = []
            for contract in contracts:
                bid = contract.get('bid', 0)
                ask = contract.get('ask', 0)
                if bid > 0 and ask > bid:
                    spread_pct = (ask - bid) / ((ask + bid) / 2)
                    spreads.append(spread_pct)

            avg_spread = statistics.mean(spreads) if spreads else 0.05
            spread_health = max(0, 1 - (avg_spread / 0.1))  # Penalize spreads > 10%

            # Calculate overall volatility score
            volatility_score = (volume_concentration * 0.4) + (spread_health * 0.6)

            return {
                'volatility_score': volatility_score,
                'volume_concentration': volume_concentration,
                'bid_ask_spread_health': spread_health,
                'avg_spread_pct': avg_spread,
                'total_volume': total_volume,
                'active_contracts': len([c for c in contracts if c.get('volume', 0) > 0])
            }

        except Exception as e:
            logger.error(f"Error analyzing market volatility: {e}")
            return {
                'volatility_score': 0.5,
                'volume_concentration': 0.5,
                'bid_ask_spread_health': 0.5
            }


class HistoricalPatternMatcher:
    """Matches signals against historical patterns to detect anomalies"""

    def __init__(self, max_patterns: int = 1000):
        self.historical_patterns: List[HistoricalPattern] = []
        self.max_patterns = max_patterns
        self.pattern_cache = {}

    def add_historical_pattern(self, algorithm_version: str, signal_type: str,
                             market_conditions: Dict[str, Any], success_rate: float,
                             confidence_range: Tuple[float, float],
                             avg_profit_loss: float, sample_size: int):
        """Add a historical pattern for future validation"""
        pattern = HistoricalPattern(
            algorithm_version=algorithm_version,
            signal_type=signal_type,
            market_conditions=market_conditions,
            confidence_range=confidence_range,
            success_rate=success_rate,
            average_hold_time=300.0,  # Default 5 minutes
            avg_profit_loss=avg_profit_loss,
            sample_size=sample_size,
            last_updated=datetime.now(timezone.utc).isoformat()
        )

        self.historical_patterns.append(pattern)

        # Keep only most recent patterns
        if len(self.historical_patterns) > self.max_patterns:
            self.historical_patterns = self.historical_patterns[-self.max_patterns:]

        logger.debug(f"Added historical pattern: {algorithm_version} {signal_type}")

    def find_similar_patterns(self, signal: Dict[str, Any]) -> List[HistoricalPattern]:
        """Find historical patterns similar to the current signal"""
        algorithm_version = signal.get('algorithm_version', 'unknown')
        signal_type = signal.get('signal_type', 'unknown')
        confidence = signal.get('confidence', 0.65)

        similar_patterns = []

        for pattern in self.historical_patterns:
            # Match algorithm version
            if pattern.algorithm_version != algorithm_version:
                continue

            # Match signal type (with some flexibility)
            if signal_type.lower() in pattern.signal_type.lower() or pattern.signal_type.lower() in signal_type.lower():
                # Check confidence range
                conf_min, conf_max = pattern.confidence_range
                if conf_min <= confidence <= conf_max:
                    similar_patterns.append(pattern)

        return similar_patterns

    def calculate_historical_correlation(self, signal: Dict[str, Any]) -> float:
        """Calculate how well signal correlates with historical success patterns"""
        similar_patterns = self.find_similar_patterns(signal)

        if not similar_patterns:
            return 0.5  # Neutral score when no patterns available

        # Weight patterns by sample size and recency
        weighted_success_rates = []
        total_weight = 0

        for pattern in similar_patterns:
            # Calculate weight based on sample size and recency
            sample_weight = min(pattern.sample_size / 50.0, 1.0)  # Cap at 50 samples

            # Recency weight (prefer patterns from last 30 days)
            try:
                pattern_date = datetime.fromisoformat(pattern.last_updated.replace('Z', '+00:00'))
                days_old = (datetime.now(timezone.utc) - pattern_date).days
                recency_weight = max(0.1, 1.0 - (days_old / 30.0))
            except:
                recency_weight = 0.5

            total_weight += sample_weight * recency_weight
            weighted_success_rates.append(pattern.success_rate * sample_weight * recency_weight)

        if total_weight > 0:
            weighted_avg_success = sum(weighted_success_rates) / total_weight
            return weighted_avg_success

        return 0.5


class TechnicalValidationEngine:
    """Validates signals using technical analysis criteria"""

    def __init__(self):
        self.validation_rules = {
            'confidence_threshold': 0.60,
            'min_expected_value': 5.0,
            'min_risk_reward_ratio': 0.8,
            'max_confidence': 0.98,  # Flag suspiciously high confidence
            'volume_thresholds': {
                'min_volume': 10,
                'min_dollar_volume': 1000
            }
        }

    def validate_signal_technical_criteria(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Validate signal against technical criteria"""
        validation_results = {
            'technical_score': 0.0,
            'flags': [],
            'passed_checks': [],
            'failed_checks': []
        }

        checks = []

        # Check 1: Confidence level
        confidence = signal.get('confidence', 0.0)
        if confidence >= self.validation_rules['confidence_threshold']:
            checks.append(('confidence_check', True, f"Confidence {confidence:.2f} >= {self.validation_rules['confidence_threshold']}"))
            validation_results['passed_checks'].append('confidence_threshold')
        else:
            checks.append(('confidence_check', False, f"Low confidence {confidence:.2f}"))
            validation_results['failed_checks'].append('confidence_threshold')
            validation_results['flags'].append('LOW_CONFIDENCE')

        # Check 2: Suspiciously high confidence
        if confidence > self.validation_rules['max_confidence']:
            checks.append(('max_confidence_check', False, f"Suspiciously high confidence {confidence:.2f}"))
            validation_results['flags'].append('SUSPICIOUS_HIGH_CONFIDENCE')
            validation_results['failed_checks'].append('max_confidence')
        else:
            checks.append(('max_confidence_check', True, f"Confidence {confidence:.2f} within normal range"))
            validation_results['passed_checks'].append('max_confidence')

        # Check 3: Expected value
        expected_value = signal.get('expected_value', 0.0)
        if expected_value >= self.validation_rules['min_expected_value']:
            checks.append(('expected_value_check', True, f"Expected value {expected_value:.2f} >= {self.validation_rules['min_expected_value']}"))
            validation_results['passed_checks'].append('expected_value')
        else:
            checks.append(('expected_value_check', False, f"Low expected value {expected_value:.2f}"))
            validation_results['failed_checks'].append('expected_value')
            validation_results['flags'].append('LOW_EXPECTED_VALUE')

        # Check 4: Risk-reward ratio
        risk_reward = signal.get('risk_reward_ratio', 0.0)
        if risk_reward >= self.validation_rules['min_risk_reward_ratio']:
            checks.append(('risk_reward_check', True, f"Risk/reward {risk_reward:.2f} >= {self.validation_rules['min_risk_reward_ratio']}"))
            validation_results['passed_checks'].append('risk_reward')
        else:
            checks.append(('risk_reward_check', False, f"Poor risk/reward {risk_reward:.2f}"))
            validation_results['failed_checks'].append('risk_reward')
            validation_results['flags'].append('POOR_RISK_REWARD')

        # Check 5: Volume metrics (if available)
        volume_metrics = signal.get('volume_metrics', {})
        if volume_metrics:
            volume = volume_metrics.get('volume', 0)
            dollar_size = volume_metrics.get('dollar_size', 0)

            if volume >= self.validation_rules['volume_thresholds']['min_volume']:
                checks.append(('volume_check', True, f"Volume {volume} adequate"))
                validation_results['passed_checks'].append('volume')
            else:
                checks.append(('volume_check', False, f"Low volume {volume}"))
                validation_results['failed_checks'].append('volume')
                validation_results['flags'].append('LOW_VOLUME')

            if dollar_size >= self.validation_rules['volume_thresholds']['min_dollar_volume']:
                checks.append(('dollar_volume_check', True, f"Dollar volume ${dollar_size:,.0f} adequate"))
                validation_results['passed_checks'].append('dollar_volume')
            else:
                checks.append(('dollar_volume_check', False, f"Low dollar volume ${dollar_size:,.0f}"))
                validation_results['failed_checks'].append('dollar_volume')
                validation_results['flags'].append('LOW_DOLLAR_VOLUME')

        # Calculate technical score
        passed_count = len([check for check in checks if check[1]])
        total_count = len(checks)
        validation_results['technical_score'] = passed_count / total_count if total_count > 0 else 0.0

        return validation_results


class FalsePositiveDetector:
    """Detects potential false positive signals"""

    def __init__(self):
        self.false_positive_patterns = {
            'market_making_signals': {
                'description': 'Signals that might be market maker activity',
                'indicators': ['small_size', 'tight_spreads', 'rapid_reversals']
            },
            'noise_signals': {
                'description': 'Signals based on market noise rather than real flow',
                'indicators': ['low_volume', 'wide_spreads', 'isolated_activity']
            },
            'stale_data_signals': {
                'description': 'Signals based on stale or outdated data',
                'indicators': ['old_timestamps', 'data_inconsistency']
            }
        }

        self.recent_signals = deque(maxlen=100)  # Track recent signals for pattern detection

    def analyze_false_positive_probability(self, signal: Dict[str, Any],
                                         market_context: Dict[str, Any],
                                         validation_flags: List[str]) -> float:
        """Calculate probability that signal is a false positive"""
        false_positive_score = 0.0

        # Factor 1: Validation flags
        flag_penalties = {
            'LOW_CONFIDENCE': 0.2,
            'SUSPICIOUS_HIGH_CONFIDENCE': 0.3,
            'LOW_EXPECTED_VALUE': 0.15,
            'POOR_RISK_REWARD': 0.15,
            'LOW_VOLUME': 0.1,
            'LOW_DOLLAR_VOLUME': 0.1,
            'BAD_TIMING': 0.2,
            'POOR_MARKET_CONTEXT': 0.15
        }

        for flag in validation_flags:
            false_positive_score += flag_penalties.get(flag, 0.05)

        # Factor 2: Market context issues
        market_volatility_score = market_context.get('volatility_score', 0.5)
        if market_volatility_score < 0.3:
            false_positive_score += 0.2  # Poor market conditions

        # Factor 3: Signal isolation (is this signal appearing alone?)
        if len(self.recent_signals) > 0:
            similar_recent = self._count_similar_recent_signals(signal)
            if similar_recent == 0:
                false_positive_score += 0.1  # Isolated signal

        # Factor 4: Algorithm-specific false positive patterns
        algorithm_version = signal.get('algorithm_version', 'unknown')
        if algorithm_version == 'v1.0':
            # Dead Simple algorithm specific checks
            volume_metrics = signal.get('volume_metrics', {})
            vol_oi_ratio = volume_metrics.get('vol_oi_ratio', 0)
            if vol_oi_ratio > 100:  # Extremely high vol/OI ratio might be anomaly
                false_positive_score += 0.15
        elif algorithm_version == 'v3.0':
            # IFD v3.0 specific checks
            pressure_metrics = signal.get('pressure_metrics', {})
            signal_strength = pressure_metrics.get('signal_strength', 0)
            if signal_strength > 5.0:  # Unusually high signal strength
                false_positive_score += 0.1

        # Cap at 1.0
        return min(false_positive_score, 1.0)

    def _count_similar_recent_signals(self, signal: Dict[str, Any]) -> int:
        """Count how many similar signals appeared recently"""
        algorithm_version = signal.get('algorithm_version', 'unknown')
        signal_type = signal.get('signal_type', 'unknown')

        similar_count = 0
        for recent_signal in self.recent_signals:
            if (recent_signal.get('algorithm_version') == algorithm_version and
                recent_signal.get('signal_type') == signal_type):
                similar_count += 1

        return similar_count

    def add_signal_to_history(self, signal: Dict[str, Any]):
        """Add signal to recent history for pattern detection"""
        signal_copy = signal.copy()
        signal_copy['processed_timestamp'] = datetime.now(timezone.utc).isoformat()
        self.recent_signals.append(signal_copy)


class SignalValidationEngine:
    """Main signal validation engine combining all validation components"""

    def __init__(self):
        self.market_analyzer = MarketContextAnalyzer()
        self.pattern_matcher = HistoricalPatternMatcher()
        self.technical_validator = TechnicalValidationEngine()
        self.false_positive_detector = FalsePositiveDetector()

        # Validation weights
        self.validation_weights = {
            'historical_correlation': 0.25,
            'market_context': 0.20,
            'timing': 0.20,
            'technical': 0.25,
            'false_positive_penalty': 0.10
        }

        logger.info("Signal validation engine initialized")

    def validate_signal(self, signal: Dict[str, Any],
                       market_data: Dict[str, Any] = None) -> ValidationResult:
        """Comprehensive signal validation"""
        try:
            signal_id = signal.get('id', 'unknown')
            timestamp = signal.get('timestamp', datetime.now(timezone.utc).isoformat())

            # Component validations
            timing_analysis = self.market_analyzer.analyze_market_timing(timestamp)

            market_context = {}
            if market_data:
                market_context = self.market_analyzer.analyze_market_volatility_context(market_data)

            historical_correlation = self.pattern_matcher.calculate_historical_correlation(signal)

            technical_validation = self.technical_validator.validate_signal_technical_criteria(signal)

            # Collect all validation flags
            all_flags = technical_validation.get('flags', [])

            if not timing_analysis.get('is_optimal_hours', False):
                all_flags.append('BAD_TIMING')

            if market_context.get('volatility_score', 0.5) < 0.3:
                all_flags.append('POOR_MARKET_CONTEXT')

            # Calculate false positive probability
            false_positive_prob = self.false_positive_detector.analyze_false_positive_probability(
                signal, market_context, all_flags
            )

            # Calculate component scores
            timing_score = timing_analysis.get('timing_score', 0.5)
            market_context_score = market_context.get('volatility_score', 0.5)
            technical_score = technical_validation.get('technical_score', 0.0)

            # Calculate overall validation score
            overall_score = (
                (historical_correlation * self.validation_weights['historical_correlation']) +
                (market_context_score * self.validation_weights['market_context']) +
                (timing_score * self.validation_weights['timing']) +
                (technical_score * self.validation_weights['technical']) -
                (false_positive_prob * self.validation_weights['false_positive_penalty'])
            )

            overall_score = max(0.0, min(1.0, overall_score))

            # Determine if signal is valid
            is_valid = overall_score >= 0.65 and false_positive_prob < 0.5

            # Calculate confidence adjustment
            confidence_adjustment = (overall_score - 0.5) * 0.2  # Adjust by up to ±10%

            # Generate reasoning
            reasoning = []
            if historical_correlation > 0.7:
                reasoning.append("Strong historical correlation with successful patterns")
            elif historical_correlation < 0.3:
                reasoning.append("Weak historical correlation")

            if timing_score > 0.8:
                reasoning.append("Excellent market timing")
            elif timing_score < 0.5:
                reasoning.append("Poor market timing")

            if technical_score > 0.8:
                reasoning.append("Strong technical criteria")
            elif technical_score < 0.5:
                reasoning.append("Failed multiple technical checks")

            if false_positive_prob > 0.6:
                reasoning.append("High false positive probability")

            # Add signal to history for future validation
            self.false_positive_detector.add_signal_to_history(signal)

            return ValidationResult(
                signal_id=signal_id,
                timestamp=timestamp,
                overall_score=overall_score,
                is_valid=is_valid,
                confidence_adjustment=confidence_adjustment,
                validation_flags=all_flags,
                false_positive_probability=false_positive_prob,
                historical_correlation=historical_correlation,
                market_context_score=market_context_score,
                timing_score=timing_score,
                technical_score=technical_score,
                reasoning=reasoning
            )

        except Exception as e:
            logger.error(f"Error validating signal {signal.get('id', 'unknown')}: {e}")

            # Return neutral validation result on error
            return ValidationResult(
                signal_id=signal.get('id', 'unknown'),
                timestamp=datetime.now(timezone.utc).isoformat(),
                overall_score=0.5,
                is_valid=False,
                confidence_adjustment=0.0,
                validation_flags=['VALIDATION_ERROR'],
                false_positive_probability=0.5,
                historical_correlation=0.5,
                market_context_score=0.5,
                timing_score=0.5,
                technical_score=0.5,
                reasoning=[f"Validation error: {str(e)}"]
            )

    def add_historical_outcome(self, signal_id: str, was_successful: bool,
                             profit_loss: float, hold_time_minutes: float):
        """Add historical outcome to improve future validation"""
        # This would typically update the historical patterns
        # For now, just log the outcome
        logger.info(f"Signal {signal_id} outcome: {'success' if was_successful else 'failure'}, "
                   f"P&L: {profit_loss:.2f}, hold time: {hold_time_minutes:.1f}min")

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of validation engine performance"""
        return {
            'historical_patterns_count': len(self.pattern_matcher.historical_patterns),
            'recent_signals_count': len(self.false_positive_detector.recent_signals),
            'validation_weights': self.validation_weights,
            'validation_rules': self.technical_validator.validation_rules
        }


# Factory function
def create_signal_validation_engine() -> SignalValidationEngine:
    """Create signal validation engine instance"""
    return SignalValidationEngine()


if __name__ == "__main__":
    # Example usage
    engine = create_signal_validation_engine()

    # Test signal
    test_signal = {
        'id': 'test_signal_1',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'algorithm_version': 'v1.0',
        'signal_type': 'call_buying',
        'confidence': 0.75,
        'expected_value': 12.5,
        'risk_reward_ratio': 1.2,
        'volume_metrics': {
            'volume': 500,
            'dollar_size': 25000,
            'vol_oi_ratio': 15.0
        }
    }

    # Validate signal
    result = engine.validate_signal(test_signal)
    print(f"Validation Result: {result.overall_score:.2f}, Valid: {result.is_valid}")
    print(f"Reasoning: {result.reasoning}")
