#!/usr/bin/env python3
"""
Streaming Data Validation and Quality Checks for IFD v3.0

This module provides comprehensive data validation and quality assurance for real-time
MBO streaming data to ensure reliable institutional flow detection.

Key Features:
- Real-time data validation with configurable rules
- Quality scoring based on completeness, consistency, and reliability
- Anomaly detection for data integrity issues
- Circuit breaker patterns for automatic error handling
- Performance monitoring and alerting
- Historical quality trend analysis

Architecture:
Raw MBO Data → Validation Rules → Quality Scoring → Anomaly Detection → Validated Data
"""

import os
import sys
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Callable, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
import statistics
import json

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(current_dir)))

from utils.timezone_utils import get_eastern_time, is_futures_market_hours

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ValidationRule:
    """Individual validation rule configuration"""
    name: str
    field: str
    rule_type: str  # 'range', 'required', 'format', 'consistency'
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    required: bool = True
    format_pattern: Optional[str] = None
    weight: float = 1.0  # Importance weight for quality scoring

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    quality_score: float  # 0.0 to 1.0
    failed_rules: List[str]
    warnings: List[str]
    data_completeness: float
    field_scores: Dict[str, float]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class QualityMetrics:
    """Data quality metrics over time"""
    total_events: int = 0
    valid_events: int = 0
    invalid_events: int = 0
    avg_quality_score: float = 0.0
    completeness_rate: float = 0.0
    consistency_score: float = 0.0
    anomaly_count: int = 0
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class DataValidator:
    """Comprehensive data validation engine for MBO streaming"""

    def __init__(self, validation_rules: List[ValidationRule]):
        """Initialize data validator

        Args:
            validation_rules: List of validation rules to apply
        """
        self.rules = {rule.name: rule for rule in validation_rules}
        self.rule_categories = defaultdict(list)

        # Categorize rules by type
        for rule in validation_rules:
            self.rule_categories[rule.rule_type].append(rule)

        # Quality tracking
        self.quality_history = deque(maxlen=1000)
        self.field_quality_history = defaultdict(lambda: deque(maxlen=100))

        # Statistics
        self.validation_stats = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'rule_failures': defaultdict(int)
        }

        logger.info(f"Data validator initialized with {len(validation_rules)} rules")

    def validate_data(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate data against all configured rules

        Args:
            data: Raw data to validate

        Returns:
            ValidationResult with validation outcome and quality metrics
        """
        self.validation_stats['total_validations'] += 1

        failed_rules = []
        warnings = []
        field_scores = {}

        # 1. Required field validation
        for rule in self.rule_categories['required']:
            if rule.required and rule.field not in data:
                failed_rules.append(f"missing_required_field_{rule.field}")
                self.validation_stats['rule_failures'][rule.name] += 1
                field_scores[rule.field] = 0.0
            elif rule.field in data:
                field_scores[rule.field] = 1.0

        # 2. Range validation
        for rule in self.rule_categories['range']:
            if rule.field in data:
                value = data[rule.field]
                score = self._validate_range(value, rule)
                field_scores[rule.field] = score

                if score < 0.5:  # Failed validation
                    failed_rules.append(f"range_violation_{rule.field}")
                    self.validation_stats['rule_failures'][rule.name] += 1
                elif score < 0.8:  # Warning threshold
                    warnings.append(f"range_warning_{rule.field}")

        # 3. Format validation
        for rule in self.rule_categories['format']:
            if rule.field in data:
                score = self._validate_format(data[rule.field], rule)
                field_scores[rule.field] = score

                if score < 0.5:
                    failed_rules.append(f"format_violation_{rule.field}")
                    self.validation_stats['rule_failures'][rule.name] += 1

        # 4. Consistency validation
        consistency_score = self._validate_consistency(data)
        if consistency_score < 0.7:
            failed_rules.append("consistency_violation")
            warnings.append("data_consistency_warning")

        # Calculate overall quality score
        quality_score = self._calculate_quality_score(field_scores, consistency_score)

        # Calculate completeness
        expected_fields = len([r for r in self.rules.values() if r.required])
        present_fields = sum(1 for r in self.rules.values() if r.required and r.field in data)
        completeness = present_fields / max(expected_fields, 1)

        # Create result
        result = ValidationResult(
            is_valid=len(failed_rules) == 0,
            quality_score=quality_score,
            failed_rules=failed_rules,
            warnings=warnings,
            data_completeness=completeness,
            field_scores=field_scores
        )

        # Update statistics
        if result.is_valid:
            self.validation_stats['passed_validations'] += 1
        else:
            self.validation_stats['failed_validations'] += 1

        # Store quality history
        self.quality_history.append(quality_score)
        for field, score in field_scores.items():
            self.field_quality_history[field].append(score)

        return result

    def _validate_range(self, value: Any, rule: ValidationRule) -> float:
        """Validate value against range constraints"""
        try:
            numeric_value = float(value)

            # Check min/max bounds
            if rule.min_value is not None and numeric_value < rule.min_value:
                return 0.0
            if rule.max_value is not None and numeric_value > rule.max_value:
                return 0.0

            # Calculate distance-based score for warnings
            if rule.min_value is not None and rule.max_value is not None:
                range_size = rule.max_value - rule.min_value
                if range_size > 0:
                    # Give full score if in middle 80% of range
                    center = (rule.min_value + rule.max_value) / 2
                    distance_from_center = abs(numeric_value - center)
                    max_good_distance = range_size * 0.4  # 80% of range

                    if distance_from_center <= max_good_distance:
                        return 1.0
                    else:
                        # Gradual degradation toward edges
                        return max(0.5, 1.0 - (distance_from_center - max_good_distance) / (range_size * 0.1))

            return 1.0

        except (ValueError, TypeError):
            return 0.0

    def _validate_format(self, value: Any, rule: ValidationRule) -> float:
        """Validate value format"""
        if rule.format_pattern:
            import re
            try:
                if re.match(rule.format_pattern, str(value)):
                    return 1.0
                else:
                    return 0.0
            except re.error:
                logger.warning(f"Invalid regex pattern in rule {rule.name}")
                return 0.5

        # Basic type checking
        if rule.field.endswith('_id') and not isinstance(value, int):
            return 0.5
        if rule.field.endswith('_price') and not isinstance(value, (int, float)):
            return 0.5
        if rule.field.endswith('_time') and not isinstance(value, (str, datetime)):
            return 0.5

        return 1.0

    def _validate_consistency(self, data: Dict[str, Any]) -> float:
        """Validate internal data consistency"""
        consistency_checks = []

        # Price consistency checks
        if 'bid_price' in data and 'ask_price' in data:
            try:
                bid = float(data['bid_price'])
                ask = float(data['ask_price'])
                if bid <= ask:
                    consistency_checks.append(1.0)
                else:
                    consistency_checks.append(0.0)  # Bid > Ask is invalid
            except (ValueError, TypeError):
                consistency_checks.append(0.0)

        # Trade price vs bid/ask consistency
        if all(field in data for field in ['trade_price', 'bid_price', 'ask_price']):
            try:
                trade = float(data['trade_price'])
                bid = float(data['bid_price'])
                ask = float(data['ask_price'])

                # Trade should be within reasonable bounds of bid/ask
                spread = ask - bid
                if bid <= trade <= ask:
                    consistency_checks.append(1.0)
                elif abs(trade - bid) <= spread * 0.1 or abs(trade - ask) <= spread * 0.1:
                    consistency_checks.append(0.8)  # Close but outside
                else:
                    consistency_checks.append(0.5)  # Concerning but not impossible

            except (ValueError, TypeError):
                consistency_checks.append(0.0)

        # Volume consistency checks
        if 'trade_size' in data:
            try:
                size = int(data['trade_size'])
                if size > 0:
                    consistency_checks.append(1.0)
                else:
                    consistency_checks.append(0.0)  # Non-positive volume
            except (ValueError, TypeError):
                consistency_checks.append(0.0)

        # Timestamp consistency
        if 'timestamp' in data:
            try:
                if isinstance(data['timestamp'], str):
                    ts = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                else:
                    ts = data['timestamp']

                now = datetime.now(timezone.utc)
                age = (now - ts).total_seconds()

                if 0 <= age <= 60:  # Data is 0-60 seconds old
                    consistency_checks.append(1.0)
                elif age <= 300:  # Data is 1-5 minutes old
                    consistency_checks.append(0.8)
                elif age <= 3600:  # Data is 5-60 minutes old
                    consistency_checks.append(0.6)
                else:
                    consistency_checks.append(0.3)  # Very old data

            except (ValueError, TypeError):
                consistency_checks.append(0.5)

        return statistics.mean(consistency_checks) if consistency_checks else 1.0

    def _calculate_quality_score(self, field_scores: Dict[str, float],
                                consistency_score: float) -> float:
        """Calculate overall quality score"""
        if not field_scores:
            return 0.0

        # Weighted average of field scores
        weighted_sum = 0.0
        total_weight = 0.0

        for field, score in field_scores.items():
            # Find rule weight
            rule_weight = 1.0
            for rule in self.rules.values():
                if rule.field == field:
                    rule_weight = rule.weight
                    break

            weighted_sum += score * rule_weight
            total_weight += rule_weight

        field_average = weighted_sum / max(total_weight, 1)

        # Combine with consistency score
        overall_score = field_average * 0.7 + consistency_score * 0.3

        return min(max(overall_score, 0.0), 1.0)

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get comprehensive validation statistics"""
        total = max(self.validation_stats['total_validations'], 1)

        return {
            'total_validations': self.validation_stats['total_validations'],
            'passed_validations': self.validation_stats['passed_validations'],
            'failed_validations': self.validation_stats['failed_validations'],
            'success_rate': self.validation_stats['passed_validations'] / total,
            'avg_quality_score': statistics.mean(self.quality_history) if self.quality_history else 0.0,
            'recent_quality_trend': list(self.quality_history)[-10:],
            'rule_failure_counts': dict(self.validation_stats['rule_failures']),
            'field_quality_averages': {
                field: statistics.mean(scores) for field, scores in self.field_quality_history.items()
            }
        }

class AnomalyDetector:
    """Detects anomalies in streaming data quality"""

    def __init__(self, window_size: int = 100, anomaly_threshold: float = 2.0):
        """Initialize anomaly detector

        Args:
            window_size: Number of recent observations to consider
            anomaly_threshold: Standard deviations for anomaly detection
        """
        self.window_size = window_size
        self.threshold = anomaly_threshold

        # Quality score tracking
        self.quality_scores = deque(maxlen=window_size)
        self.field_scores = defaultdict(lambda: deque(maxlen=window_size))

        # Anomaly tracking
        self.anomalies_detected = 0
        self.recent_anomalies = deque(maxlen=50)

    def detect_anomalies(self, validation_result: ValidationResult) -> List[Dict[str, Any]]:
        """
        Detect anomalies in validation results

        Args:
            validation_result: Result from data validation

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Add current scores to history
        self.quality_scores.append(validation_result.quality_score)
        for field, score in validation_result.field_scores.items():
            self.field_scores[field].append(score)

        # Overall quality anomaly detection
        if len(self.quality_scores) >= 10:
            mean_quality = statistics.mean(self.quality_scores)
            std_quality = statistics.stdev(self.quality_scores) if len(self.quality_scores) > 1 else 0

            if std_quality > 0:
                z_score = (validation_result.quality_score - mean_quality) / std_quality
                if abs(z_score) > self.threshold:
                    anomaly = {
                        'type': 'quality_anomaly',
                        'severity': 'high' if abs(z_score) > 3.0 else 'medium',
                        'z_score': z_score,
                        'current_score': validation_result.quality_score,
                        'mean_score': mean_quality,
                        'timestamp': validation_result.timestamp
                    }
                    anomalies.append(anomaly)
                    self.anomalies_detected += 1

        # Field-specific anomaly detection
        for field, score in validation_result.field_scores.items():
            field_history = self.field_scores[field]
            if len(field_history) >= 10:
                mean_score = statistics.mean(field_history)
                std_score = statistics.stdev(field_history) if len(field_history) > 1 else 0

                if std_score > 0:
                    z_score = (score - mean_score) / std_score
                    if abs(z_score) > self.threshold:
                        anomaly = {
                            'type': 'field_anomaly',
                            'field': field,
                            'severity': 'high' if abs(z_score) > 3.0 else 'medium',
                            'z_score': z_score,
                            'current_score': score,
                            'mean_score': mean_score,
                            'timestamp': validation_result.timestamp
                        }
                        anomalies.append(anomaly)

        # Store recent anomalies
        for anomaly in anomalies:
            self.recent_anomalies.append(anomaly)

        return anomalies

    def get_anomaly_stats(self) -> Dict[str, Any]:
        """Get anomaly detection statistics"""
        recent_count = len([a for a in self.recent_anomalies
                           if (datetime.now(timezone.utc) - a['timestamp']).total_seconds() < 3600])

        return {
            'total_anomalies': self.anomalies_detected,
            'recent_anomalies': recent_count,
            'recent_anomaly_list': list(self.recent_anomalies)[-10:],
            'detection_window_size': len(self.quality_scores),
            'current_threshold': self.threshold
        }

class CircuitBreaker:
    """Circuit breaker for data quality failures"""

    def __init__(self, failure_threshold: int = 10, timeout_seconds: int = 60):
        """Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Timeout before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout_seconds

        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.last_failure_time = None
        self.open_time = None

    def record_result(self, validation_result: ValidationResult) -> bool:
        """
        Record validation result and update circuit state

        Args:
            validation_result: Validation result

        Returns:
            True if circuit allows processing, False if circuit is open
        """
        current_time = datetime.now(timezone.utc)

        if self.state == 'OPEN':
            # Check if timeout has passed
            if (current_time - self.open_time).total_seconds() >= self.timeout:
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker moving to HALF_OPEN state")
            else:
                return False  # Circuit still open

        if validation_result.quality_score < 0.5 or not validation_result.is_valid:
            # Record failure
            self.failure_count += 1
            self.last_failure_time = current_time

            if self.state == 'HALF_OPEN':
                # Failure in half-open state - go back to open
                self.state = 'OPEN'
                self.open_time = current_time
                logger.warning("Circuit breaker opening due to failure in HALF_OPEN state")
                return False

            elif self.failure_count >= self.failure_threshold:
                # Too many failures - open circuit
                self.state = 'OPEN'
                self.open_time = current_time
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
                return False
        else:
            # Success
            if self.state == 'HALF_OPEN':
                # Success in half-open state - close circuit
                self.state = 'CLOSED'
                self.failure_count = 0
                logger.info("Circuit breaker closed after successful validation")

            # Reset failure count on success (with some decay)
            self.failure_count = max(0, self.failure_count - 1)

        return True

    def get_circuit_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'open_time': self.open_time.isoformat() if self.open_time else None,
            'timeout_seconds': self.timeout
        }

class StreamingDataValidator:
    """Main validator orchestrating all validation components"""

    def __init__(self, validation_rules: List[ValidationRule]):
        """Initialize streaming data validator

        Args:
            validation_rules: List of validation rules
        """
        self.validator = DataValidator(validation_rules)
        self.anomaly_detector = AnomalyDetector()
        self.circuit_breaker = CircuitBreaker()

        # Callbacks
        self.validation_callbacks = []
        self.anomaly_callbacks = []

        # Metrics
        self.metrics = QualityMetrics()

        logger.info("Streaming data validator initialized")

    def validate_streaming_data(self, data: Dict[str, Any]) -> Tuple[bool, ValidationResult]:
        """
        Validate streaming data with full quality pipeline

        Args:
            data: Raw streaming data

        Returns:
            Tuple of (should_process, validation_result)
        """
        # 1. Basic validation
        validation_result = self.validator.validate_data(data)

        # 2. Anomaly detection
        anomalies = self.anomaly_detector.detect_anomalies(validation_result)

        # 3. Circuit breaker check
        should_process = self.circuit_breaker.record_result(validation_result)

        # 4. Update metrics
        self._update_metrics(validation_result, anomalies)

        # 5. Notify callbacks
        self._notify_callbacks(validation_result, anomalies)

        return should_process, validation_result

    def _update_metrics(self, validation_result: ValidationResult, anomalies: List[Dict]):
        """Update quality metrics"""
        self.metrics.total_events += 1

        if validation_result.is_valid:
            self.metrics.valid_events += 1
        else:
            self.metrics.invalid_events += 1

        self.metrics.anomaly_count += len(anomalies)

        # Update averages
        total = max(self.metrics.total_events, 1)
        self.metrics.avg_quality_score = (
            (self.metrics.avg_quality_score * (total - 1) + validation_result.quality_score) / total
        )
        self.metrics.completeness_rate = (
            (self.metrics.completeness_rate * (total - 1) + validation_result.data_completeness) / total
        )

        self.metrics.last_update = datetime.now(timezone.utc)

    def register_validation_callback(self, callback: Callable[[ValidationResult], None]):
        """Register callback for validation results"""
        self.validation_callbacks.append(callback)

    def register_anomaly_callback(self, callback: Callable[[List[Dict]], None]):
        """Register callback for anomaly detection"""
        self.anomaly_callbacks.append(callback)

    def _notify_callbacks(self, validation_result: ValidationResult, anomalies: List[Dict]):
        """Notify all registered callbacks"""
        for callback in self.validation_callbacks:
            try:
                callback(validation_result)
            except Exception as e:
                logger.error(f"Validation callback error: {e}")

        if anomalies:
            for callback in self.anomaly_callbacks:
                try:
                    callback(anomalies)
                except Exception as e:
                    logger.error(f"Anomaly callback error: {e}")

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive validation and quality statistics"""
        return {
            'metrics': {
                'total_events': self.metrics.total_events,
                'valid_events': self.metrics.valid_events,
                'invalid_events': self.metrics.invalid_events,
                'avg_quality_score': self.metrics.avg_quality_score,
                'completeness_rate': self.metrics.completeness_rate,
                'anomaly_count': self.metrics.anomaly_count,
                'last_update': self.metrics.last_update.isoformat()
            },
            'validation': self.validator.get_validation_stats(),
            'anomaly_detection': self.anomaly_detector.get_anomaly_stats(),
            'circuit_breaker': self.circuit_breaker.get_circuit_state()
        }

# Predefined validation rule sets
def create_mbo_validation_rules() -> List[ValidationRule]:
    """Create standard validation rules for MBO data"""
    return [
        # Required fields
        ValidationRule("timestamp_required", "timestamp", "required", required=True, weight=2.0),
        ValidationRule("instrument_id_required", "instrument_id", "required", required=True, weight=2.0),

        # Price validations
        ValidationRule("bid_price_range", "bid_price", "range", min_value=0.01, max_value=50000.0, weight=1.5),
        ValidationRule("ask_price_range", "ask_price", "range", min_value=0.01, max_value=50000.0, weight=1.5),
        ValidationRule("trade_price_range", "trade_price", "range", min_value=0.01, max_value=50000.0, weight=1.5),

        # Volume validations
        ValidationRule("trade_size_range", "trade_size", "range", min_value=1, max_value=10000, weight=1.0),

        # Format validations
        ValidationRule("instrument_id_format", "instrument_id", "format", required=False, weight=0.5),
        ValidationRule("side_format", "side", "format", format_pattern="^(BUY|SELL|UNKNOWN)$", required=False, weight=1.0),

        # Quality thresholds
        ValidationRule("confidence_range", "confidence", "range", min_value=0.0, max_value=1.0, required=False, weight=0.8)
    ]

def create_pressure_validation_rules() -> List[ValidationRule]:
    """Create validation rules for pressure metrics"""
    return [
        ValidationRule("pressure_ratio_range", "pressure_ratio", "range", min_value=0.1, max_value=100.0, weight=2.0),
        ValidationRule("bid_volume_range", "bid_volume", "range", min_value=0, max_value=100000, weight=1.5),
        ValidationRule("ask_volume_range", "ask_volume", "range", min_value=0, max_value=100000, weight=1.5),
        ValidationRule("total_trades_range", "total_trades", "range", min_value=1, max_value=1000, weight=1.0),
        ValidationRule("confidence_range", "confidence", "range", min_value=0.0, max_value=1.0, weight=1.5)
    ]

# Example usage and testing
if __name__ == "__main__":
    print("=== Streaming Data Validator Test ===")

    # Create validator with MBO rules
    rules = create_mbo_validation_rules()
    validator = StreamingDataValidator(rules)

    # Test callbacks
    def validation_callback(result: ValidationResult):
        print(f"📊 Validation: valid={result.is_valid} quality={result.quality_score:.2f}")

    def anomaly_callback(anomalies: List[Dict]):
        print(f"🚨 Anomalies detected: {len(anomalies)}")

    validator.register_validation_callback(validation_callback)
    validator.register_anomaly_callback(anomaly_callback)

    # Test with various data quality levels
    test_data = [
        # Good data
        {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'bid_price': 100.0,
            'ask_price': 100.5,
            'trade_price': 100.25,
            'trade_size': 10,
            'side': 'BUY',
            'confidence': 0.85
        },
        # Missing required field
        {
            'bid_price': 99.0,
            'ask_price': 99.5,
            'trade_size': 5
        },
        # Invalid price relationship
        {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'bid_price': 101.0,
            'ask_price': 100.0,  # Bid > Ask (invalid)
            'trade_price': 100.5,
            'trade_size': 10
        }
    ]

    for i, data in enumerate(test_data):
        print(f"\n--- Test {i+1} ---")
        should_process, result = validator.validate_streaming_data(data)
        print(f"Should process: {should_process}")
        if result.failed_rules:
            print(f"Failed rules: {result.failed_rules}")
        if result.warnings:
            print(f"Warnings: {result.warnings}")

    # Get comprehensive stats
    stats = validator.get_comprehensive_stats()
    print("\n📈 Validation Stats:")
    for category, data in stats.items():
        print(f"  {category}:")
        if isinstance(data, dict):
            for k, v in data.items():
                print(f"    {k}: {v}")
        else:
            print(f"    {data}")

    print("\n✅ Streaming data validator test completed")
