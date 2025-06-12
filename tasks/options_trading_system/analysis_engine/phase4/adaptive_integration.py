#!/usr/bin/env python3
"""
Adaptive Threshold Integration for IFD v3.0

This module integrates the adaptive threshold manager with the IFD v3.0 system,
enabling automatic threshold updates based on performance feedback.

Key Features:
- Real-time threshold updates to IFD v3.0 configuration
- Performance monitoring integration
- Graceful fallback handling
- Thread-safe threshold updates
- Validation and safety checks
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import adaptive threshold manager
try:
    from .adaptive_threshold_manager import (
        create_adaptive_threshold_manager,
        AdaptiveThresholdManager,
        OptimizationObjective,
        OptimizationResult
    )
    ADAPTIVE_AVAILABLE = True
except ImportError:
    logger.warning("Adaptive threshold manager not available")
    ADAPTIVE_AVAILABLE = False

# Import IFD v3.0 components
try:
    from .institutional_flow_v3.solution import create_ifd_v3_analyzer, IFDv3Engine
    IFD_AVAILABLE = True
except ImportError:
    logger.warning("IFD v3.0 system not available")
    IFD_AVAILABLE = False

# Import success metrics tracker
try:
    from .success_metrics_tracker import create_success_metrics_tracker, SuccessMetricsTracker
    METRICS_AVAILABLE = True
except ImportError:
    logger.warning("Success metrics tracker not available")
    METRICS_AVAILABLE = False


@dataclass
class SystemPerformanceMetrics:
    """Current system performance metrics"""
    timestamp: datetime
    accuracy: float
    cost_per_signal: float
    roi: float
    win_loss_ratio: float
    signal_volume: int
    processing_latency: float
    uptime_percentage: float


class ConfigurationValidator:
    """Validates threshold configurations before applying"""

    def __init__(self):
        # Define reasonable bounds for validation
        self.validation_bounds = {
            'min_pressure_ratio': {'min': 1.0, 'max': 10.0},
            'min_total_volume': {'min': 10.0, 'max': 1000.0},
            'min_confidence': {'min': 0.3, 'max': 0.99},
            'min_final_confidence': {'min': 0.3, 'max': 0.95},
            'pressure_weight': {'min': 0.1, 'max': 0.8},
            'baseline_weight': {'min': 0.1, 'max': 0.6},
            'market_making_weight': {'min': 0.05, 'max': 0.4}
        }

    def validate_threshold_change(self, threshold_name: str, new_value: float,
                                 current_config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate a proposed threshold change

        Args:
            threshold_name: Name of threshold to change
            new_value: Proposed new value
            current_config: Current configuration

        Returns:
            Tuple of (is_valid, reason)
        """

        # Check if threshold exists in validation bounds
        if threshold_name not in self.validation_bounds:
            return True, "Threshold not in validation scope"

        bounds = self.validation_bounds[threshold_name]

        # Check bounds
        if new_value < bounds['min'] or new_value > bounds['max']:
            return False, f"Value {new_value} outside safe bounds [{bounds['min']}, {bounds['max']}]"

        # Check for reasonable change magnitude
        if threshold_name in current_config:
            current_value = current_config[threshold_name]
            change_ratio = abs(new_value - current_value) / current_value

            if change_ratio > 0.5:  # More than 50% change
                return False, f"Change too large: {change_ratio:.1%} (max 50%)"

        # Specific validation rules
        if threshold_name == 'min_confidence' and 'min_final_confidence' in current_config:
            final_confidence = current_config['min_final_confidence']
            if new_value < final_confidence:
                return False, "min_confidence cannot be less than min_final_confidence"

        return True, "Valid"

    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate entire configuration for consistency

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check confidence hierarchy
        min_conf = config.get('min_confidence', 0.8)
        final_conf = config.get('min_final_confidence', 0.7)

        if min_conf < final_conf:
            issues.append("min_confidence should be >= min_final_confidence")

        # Check weight consistency
        weights = [
            config.get('pressure_weight', 0.4),
            config.get('baseline_weight', 0.3),
            config.get('market_making_weight', 0.2),
            config.get('coordination_weight', 0.1)
        ]

        total_weight = sum(weights)
        if abs(total_weight - 1.0) > 0.1:
            issues.append(f"Confidence weights don't sum to 1.0: {total_weight:.2f}")

        # Check minimum thresholds are reasonable
        min_pressure = config.get('min_pressure_ratio', 2.0)
        min_volume = config.get('min_total_volume', 100)

        if min_pressure < 1.1:
            issues.append("min_pressure_ratio too low - may generate excessive signals")

        if min_volume < 20:
            issues.append("min_total_volume too low - may include noise")

        return len(issues) == 0, issues


class AdaptiveIFDIntegration:
    """
    Main integration class that connects adaptive threshold management
    with the IFD v3.0 system for real-time performance optimization
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adaptive IFD integration

        Args:
            config: Integration configuration
        """
        self.config = config
        self.validator = ConfigurationValidator()

        # Initialize components
        self.threshold_manager = None
        self.ifd_analyzer = None
        self.metrics_tracker = None

        if ADAPTIVE_AVAILABLE:
            adaptive_config = config.get('adaptive_thresholds', {})
            self.threshold_manager = create_adaptive_threshold_manager(adaptive_config)
            self.threshold_manager.on_threshold_change = self._on_threshold_change
            self.threshold_manager.on_optimization_complete = self._on_optimization_complete

        if METRICS_AVAILABLE:
            self.metrics_tracker = create_success_metrics_tracker()

        # Current configuration state
        self._current_ifd_config = self._create_default_ifd_config()
        self._config_lock = threading.Lock()

        # Performance tracking
        self.performance_history = []
        self.last_performance_update = None

        # Integration state
        self.integration_active = False
        self.performance_monitor_thread = None

        logger.info("Adaptive IFD Integration initialized")

    def _create_default_ifd_config(self) -> Dict[str, Any]:
        """Create default IFD v3.0 configuration"""
        return {
            'baseline_db_path': 'outputs/ifd_v3_baselines.db',
            'pressure_analysis': {
                'min_pressure_ratio': 2.0,
                'min_total_volume': 100,
                'min_confidence': 0.8,
                'lookback_windows': 3
            },
            'historical_baselines': {
                'lookback_days': 20
            },
            'market_making_detection': {
                'straddle_time_window': 300,
                'volatility_crush_threshold': -5.0,
                'max_market_making_probability': 0.3
            },
            'confidence_scoring': {
                'pressure_weight': 0.4,
                'baseline_weight': 0.3,
                'market_making_weight': 0.2,
                'coordination_weight': 0.1
            },
            'min_final_confidence': 0.7
        }

    def start_adaptive_system(self):
        """Start the adaptive threshold system"""
        if not ADAPTIVE_AVAILABLE:
            logger.error("Adaptive threshold manager not available")
            return False

        try:
            # Start threshold manager monitoring
            self.threshold_manager.start_monitoring()

            # Start performance monitoring
            self.integration_active = True
            self.performance_monitor_thread = threading.Thread(
                target=self._performance_monitoring_loop,
                daemon=True,
                name="AdaptiveIFDMonitor"
            )
            self.performance_monitor_thread.start()

            logger.info("Adaptive IFD system started")
            return True

        except Exception as e:
            logger.error(f"Failed to start adaptive system: {e}")
            return False

    def stop_adaptive_system(self):
        """Stop the adaptive threshold system"""
        self.integration_active = False

        if self.threshold_manager:
            self.threshold_manager.stop_monitoring()

        logger.info("Adaptive IFD system stopped")

    def get_current_ifd_analyzer(self) -> Optional[IFDv3Engine]:
        """Get IFD analyzer with current adaptive configuration"""
        if not IFD_AVAILABLE:
            logger.warning("IFD v3.0 not available")
            return None

        with self._config_lock:
            current_config = self._current_ifd_config.copy()

        try:
            return create_ifd_v3_analyzer(current_config)
        except Exception as e:
            logger.error(f"Failed to create IFD analyzer: {e}")
            return None

    def get_current_configuration(self) -> Dict[str, Any]:
        """Get current IFD configuration with adaptive thresholds"""
        with self._config_lock:
            return self._current_ifd_config.copy()

    def manual_threshold_optimization(self, objective: OptimizationObjective) -> Optional[OptimizationResult]:
        """Manually trigger threshold optimization"""
        if not self.threshold_manager:
            logger.error("Threshold manager not available")
            return None

        try:
            result = self.threshold_manager.manual_optimization(objective)
            logger.info(f"Manual optimization result: {result.recommendation}")
            return result
        except Exception as e:
            logger.error(f"Manual optimization failed: {e}")
            return None

    def force_threshold_update(self, threshold_name: str, new_value: float) -> bool:
        """Force update of a specific threshold"""
        if not self.threshold_manager:
            logger.error("Threshold manager not available")
            return False

        try:
            # Validate the change
            with self._config_lock:
                is_valid, reason = self.validator.validate_threshold_change(
                    threshold_name, new_value, self._current_ifd_config
                )

            if not is_valid:
                logger.error(f"Invalid threshold change: {reason}")
                return False

            # Apply the change
            self.threshold_manager.force_threshold_adjustment(
                threshold_name, new_value, "Manual forced update"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to force threshold update: {e}")
            return False

    def _performance_monitoring_loop(self):
        """Monitor system performance and feed back to adaptive system"""

        while self.integration_active:
            try:
                # Collect current performance metrics
                performance = self._collect_current_performance()

                if performance:
                    self.performance_history.append(performance)
                    self.last_performance_update = datetime.now(timezone.utc)

                    # Keep history manageable
                    if len(self.performance_history) > 100:
                        self.performance_history = self.performance_history[-50:]

                    logger.debug(f"Performance update: accuracy={performance.accuracy:.3f}, "
                               f"cost=${performance.cost_per_signal:.2f}")

                # Sleep until next monitoring cycle
                time.sleep(300)  # 5 minutes

            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(60)  # Short sleep on error

    def _collect_current_performance(self) -> Optional[SystemPerformanceMetrics]:
        """Collect current system performance metrics"""

        if not self.metrics_tracker:
            # Return mock data for testing
            return SystemPerformanceMetrics(
                timestamp=datetime.now(timezone.utc),
                accuracy=0.72,
                cost_per_signal=4.5,
                roi=0.18,
                win_loss_ratio=1.6,
                signal_volume=25,
                processing_latency=85.0,
                uptime_percentage=99.2
            )

        try:
            # Get performance report from metrics tracker
            report = self.metrics_tracker.get_success_metrics_report(days_back=1)

            if not report.get('v3_performance'):
                return None

            perf = report['v3_performance']

            return SystemPerformanceMetrics(
                timestamp=datetime.now(timezone.utc),
                accuracy=perf.get('accuracy', 0.0),
                cost_per_signal=perf.get('cost_per_signal', 0.0),
                roi=perf.get('roi', 0.0),
                win_loss_ratio=perf.get('win_loss_ratio', 0.0),
                signal_volume=0,  # Would need additional tracking
                processing_latency=50.0,  # Would need additional tracking
                uptime_percentage=99.0   # Would need additional tracking
            )

        except Exception as e:
            logger.error(f"Failed to collect performance metrics: {e}")
            return None

    def _on_threshold_change(self, threshold_name: str, old_value: float, new_value: float):
        """Handle threshold change from adaptive manager"""

        logger.info(f"Adaptive threshold change: {threshold_name} {old_value:.3f} -> {new_value:.3f}")

        # Update IFD configuration
        with self._config_lock:
            self._update_ifd_config_threshold(threshold_name, new_value)

        # Recreate IFD analyzer with new configuration
        if IFD_AVAILABLE:
            try:
                # This would trigger recreation in the main system
                logger.debug("IFD configuration updated - analyzer recreation required")
            except Exception as e:
                logger.error(f"Failed to update IFD configuration: {e}")

    def _update_ifd_config_threshold(self, threshold_name: str, new_value: float):
        """Update specific threshold in IFD configuration"""

        # Map threshold names to configuration paths
        config_mapping = {
            'min_pressure_ratio': ['pressure_analysis', 'min_pressure_ratio'],
            'min_total_volume': ['pressure_analysis', 'min_total_volume'],
            'min_confidence': ['pressure_analysis', 'min_confidence'],
            'min_final_confidence': ['min_final_confidence'],
            'pressure_weight': ['confidence_scoring', 'pressure_weight'],
            'baseline_weight': ['confidence_scoring', 'baseline_weight'],
            'market_making_weight': ['confidence_scoring', 'market_making_weight'],
            'coordination_weight': ['confidence_scoring', 'coordination_weight']
        }

        if threshold_name not in config_mapping:
            logger.warning(f"Unknown threshold mapping: {threshold_name}")
            return

        # Navigate to the configuration section
        config_path = config_mapping[threshold_name]
        current_section = self._current_ifd_config

        # Navigate to parent section
        for key in config_path[:-1]:
            if key not in current_section:
                current_section[key] = {}
            current_section = current_section[key]

        # Update the value
        final_key = config_path[-1]
        current_section[final_key] = new_value

        logger.debug(f"Updated IFD config: {'.'.join(config_path)} = {new_value}")

    def _on_optimization_complete(self, result: OptimizationResult):
        """Handle optimization completion"""

        logger.info(f"Optimization {result.optimization_id} complete: "
                   f"{result.recommendation} (improvement: {result.expected_improvement:.3f})")

        # Log optimization details
        if result.threshold_adjustments:
            for threshold, value in result.threshold_adjustments.items():
                logger.info(f"  Recommended: {threshold} = {value:.3f}")

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""

        # Current performance
        latest_performance = None
        if self.performance_history:
            latest_performance = self.performance_history[-1]

        # Threshold manager status
        threshold_status = {}
        if self.threshold_manager:
            threshold_status = self.threshold_manager.get_optimization_summary()
            threshold_status['current_thresholds'] = self.threshold_manager.get_current_thresholds()

        # Configuration validation
        with self._config_lock:
            config_valid, config_issues = self.validator.validate_configuration(self._current_ifd_config)

        return {
            'integration_active': self.integration_active,
            'components_available': {
                'adaptive_thresholds': ADAPTIVE_AVAILABLE,
                'ifd_v3': IFD_AVAILABLE,
                'metrics_tracker': METRICS_AVAILABLE
            },
            'current_performance': {
                'accuracy': latest_performance.accuracy if latest_performance else 0.0,
                'cost_per_signal': latest_performance.cost_per_signal if latest_performance else 0.0,
                'roi': latest_performance.roi if latest_performance else 0.0,
                'win_loss_ratio': latest_performance.win_loss_ratio if latest_performance else 0.0,
                'last_update': latest_performance.timestamp.isoformat() if latest_performance else None
            },
            'threshold_management': threshold_status,
            'configuration': {
                'valid': config_valid,
                'issues': config_issues,
                'last_update': self.last_performance_update.isoformat() if self.last_performance_update else None
            },
            'performance_history_size': len(self.performance_history)
        }

    def export_performance_data(self) -> Dict[str, Any]:
        """Export performance data for analysis"""

        performance_data = []
        for perf in self.performance_history:
            performance_data.append({
                'timestamp': perf.timestamp.isoformat(),
                'accuracy': perf.accuracy,
                'cost_per_signal': perf.cost_per_signal,
                'roi': perf.roi,
                'win_loss_ratio': perf.win_loss_ratio,
                'signal_volume': perf.signal_volume,
                'processing_latency': perf.processing_latency,
                'uptime_percentage': perf.uptime_percentage
            })

        return {
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'performance_data': performance_data,
            'configuration_history': [],  # Would implement if needed
            'system_status': self.get_system_status()
        }


def create_adaptive_ifd_integration(config: Optional[Dict] = None) -> AdaptiveIFDIntegration:
    """Factory function to create adaptive IFD integration"""

    if config is None:
        config = {
            'adaptive_thresholds': {
                'targets': {
                    'accuracy': 0.75,
                    'cost_per_signal': 5.0,
                    'roi': 0.25,
                    'win_loss_ratio': 1.8
                },
                'monitoring_interval': 3600,  # 1 hour
                'optimization_interval': 21600,  # 6 hours
            }
        }

    return AdaptiveIFDIntegration(config)


if __name__ == "__main__":
    # Example usage
    integration = create_adaptive_ifd_integration()

    print("=== Adaptive IFD Integration Test ===")

    # Start adaptive system
    if integration.start_adaptive_system():
        print("✓ Adaptive system started")

        # Get current analyzer
        analyzer = integration.get_current_ifd_analyzer()
        if analyzer:
            print("✓ IFD analyzer created with adaptive configuration")

        # Show system status
        status = integration.get_system_status()
        print(f"\nSystem Status:")
        print(f"  Integration Active: {status['integration_active']}")
        print(f"  Components Available: {status['components_available']}")

        if status['threshold_management'].get('current_thresholds'):
            print(f"\nCurrent Thresholds:")
            for name, value in status['threshold_management']['current_thresholds'].items():
                print(f"  {name}: {value:.3f}")

        # Test manual optimization
        print(f"\nTesting manual optimization...")
        result = integration.manual_threshold_optimization(OptimizationObjective.BALANCED)
        if result:
            print(f"  Result: {result.recommendation}")
            print(f"  Expected improvement: {result.expected_improvement:.3f}")

        # Run for a short time
        print(f"\nRunning integration for 30 seconds...")
        time.sleep(30)

        # Show final status
        final_status = integration.get_system_status()
        print(f"\nFinal Status:")
        print(f"  Performance history: {final_status['performance_history_size']} entries")

        integration.stop_adaptive_system()
        print("✓ Adaptive system stopped")

    else:
        print("✗ Failed to start adaptive system")
