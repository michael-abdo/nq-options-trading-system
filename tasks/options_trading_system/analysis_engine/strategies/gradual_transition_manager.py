#!/usr/bin/env python3
"""
Gradual Transition Manager for IFD v1.0 to v3.0

This module provides granular transition mechanics for smoothly moving
from IFD v1.0 (Dead Simple) to v3.0 (Enhanced) with minimal disruption
to trading operations.

Features:
- Parameter interpolation during transition
- Configuration synchronization
- Smooth algorithm handover
- State preservation during transition
- Fallback safety mechanisms
"""

import json
import os
import time
import threading
from datetime import datetime, timedelta
from utils.timezone_utils import get_eastern_time, get_utc_time
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
from collections import deque, defaultdict
import math


class TransitionState(Enum):
    """Transition execution states"""
    PREPARING = "PREPARING"
    PARAMETER_SYNC = "PARAMETER_SYNC"
    GRADUAL_BLEND = "GRADUAL_BLEND"
    HANDOVER = "HANDOVER"
    VERIFICATION = "VERIFICATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLING_BACK = "ROLLING_BACK"


class BlendMode(Enum):
    """Signal blending modes during transition"""
    WEIGHTED_AVERAGE = "WEIGHTED_AVERAGE"
    CONFIDENCE_BASED = "CONFIDENCE_BASED"
    PERFORMANCE_BASED = "PERFORMANCE_BASED"
    GRADUAL_SWITCH = "GRADUAL_SWITCH"


class ParameterSyncStrategy(Enum):
    """Parameter synchronization strategies"""
    INTERPOLATION = "INTERPOLATION"
    STEP_WISE = "STEP_WISE"
    PERFORMANCE_DRIVEN = "PERFORMANCE_DRIVEN"
    CONSERVATIVE = "CONSERVATIVE"


@dataclass
class TransitionConfig:
    """Configuration for gradual transition"""
    # Timing
    total_transition_duration_hours: float = 24.0  # 24 hours
    parameter_sync_duration_hours: float = 2.0     # 2 hours
    blend_duration_hours: float = 16.0             # 16 hours
    handover_duration_hours: float = 4.0           # 4 hours
    verification_duration_hours: float = 2.0       # 2 hours

    # Blending
    blend_mode: BlendMode = BlendMode.CONFIDENCE_BASED
    initial_v3_weight: float = 0.1  # Start with 10% v3.0
    final_v3_weight: float = 1.0    # End with 100% v3.0

    # Parameter synchronization
    sync_strategy: ParameterSyncStrategy = ParameterSyncStrategy.INTERPOLATION
    parameter_adjustment_steps: int = 20

    # Safety thresholds
    max_performance_degradation: float = 0.05  # 5%
    min_signal_correlation: float = 0.7        # 70%
    max_position_variance: float = 0.1         # 10%

    # Fallback triggers
    emergency_fallback_threshold: float = 0.15  # 15% performance drop
    consecutive_failure_limit: int = 5

    # Verification requirements
    min_verification_samples: int = 50
    required_accuracy_ratio: float = 0.95  # v3.0 must be 95% as good as v1.0


@dataclass
class TransitionMetrics:
    """Metrics during transition"""
    timestamp: datetime
    state: TransitionState
    progress_percent: float

    # Current blending weights
    v1_weight: float
    v3_weight: float

    # Performance comparison
    v1_accuracy: float = 0.0
    v3_accuracy: float = 0.0
    blended_accuracy: float = 0.0

    # Signal correlation
    signal_correlation: float = 0.0
    position_variance: float = 0.0

    # Transition health
    sync_completion: float = 0.0
    stability_score: float = 1.0
    confidence_score: float = 0.0


@dataclass
class ParameterMapping:
    """Maps v1.0 parameters to v3.0 equivalents"""
    v1_parameter: str
    v3_parameter: str
    conversion_function: Optional[str] = None  # Function name for conversion
    scaling_factor: float = 1.0
    offset: float = 0.0


class ParameterSynchronizer:
    """Synchronizes parameters between v1.0 and v3.0"""

    def __init__(self):
        # Define parameter mappings
        self.parameter_mappings = [
            ParameterMapping("volume_threshold", "institutional_flow_v3.volume_concentration", scaling_factor=1.2),
            ParameterMapping("spike_threshold", "institutional_flow_v3.min_pressure_ratio", scaling_factor=0.8),
            ParameterMapping("confidence_threshold", "analysis_thresholds.min_confidence", scaling_factor=1.0),
            ParameterMapping("time_window", "institutional_flow_v3.time_persistence", scaling_factor=1.5),
        ]

        self.interpolated_configs: deque = deque(maxlen=100)

    def create_interpolated_config(self, v1_config: Dict[str, Any], v3_config: Dict[str, Any],
                                 blend_ratio: float) -> Dict[str, Any]:
        """Create interpolated configuration between v1.0 and v3.0"""
        interpolated = v3_config.copy()

        for mapping in self.parameter_mappings:
            try:
                # Get v1.0 parameter value
                v1_value = self._get_nested_value(v1_config, mapping.v1_parameter)
                if v1_value is None:
                    continue

                # Convert and scale
                converted_value = v1_value * mapping.scaling_factor + mapping.offset

                # Get current v3.0 value
                v3_value = self._get_nested_value(v3_config, mapping.v3_parameter)
                if v3_value is None:
                    continue

                # Interpolate
                interpolated_value = v3_value * blend_ratio + converted_value * (1 - blend_ratio)

                # Set interpolated value
                self._set_nested_value(interpolated, mapping.v3_parameter, interpolated_value)

            except Exception as e:
                print(f"Parameter interpolation error for {mapping.v1_parameter}: {e}")

        # Record interpolated config
        self.interpolated_configs.append({
            "timestamp": get_eastern_time(),
            "blend_ratio": blend_ratio,
            "config": interpolated
        })

        return interpolated

    def _get_nested_value(self, config: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        keys = path.split('.')
        value = config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any):
        """Set value in nested dictionary using dot notation"""
        keys = path.split('.')
        target = config

        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]

        target[keys[-1]] = value


class SignalBlender:
    """Blends signals from v1.0 and v3.0 during transition"""

    def __init__(self, blend_mode: BlendMode = BlendMode.CONFIDENCE_BASED):
        self.blend_mode = blend_mode
        self.signal_history: deque = deque(maxlen=1000)
        self.performance_history: deque = deque(maxlen=500)

    def blend_signals(self, v1_signal: Dict[str, Any], v3_signal: Dict[str, Any],
                     v1_weight: float, v3_weight: float) -> Dict[str, Any]:
        """Blend signals from both algorithms"""
        if self.blend_mode == BlendMode.WEIGHTED_AVERAGE:
            return self._weighted_average_blend(v1_signal, v3_signal, v1_weight, v3_weight)
        elif self.blend_mode == BlendMode.CONFIDENCE_BASED:
            return self._confidence_based_blend(v1_signal, v3_signal, v1_weight, v3_weight)
        elif self.blend_mode == BlendMode.PERFORMANCE_BASED:
            return self._performance_based_blend(v1_signal, v3_signal, v1_weight, v3_weight)
        elif self.blend_mode == BlendMode.GRADUAL_SWITCH:
            return self._gradual_switch_blend(v1_signal, v3_signal, v1_weight, v3_weight)
        else:
            return self._weighted_average_blend(v1_signal, v3_signal, v1_weight, v3_weight)

    def _weighted_average_blend(self, v1_signal: Dict[str, Any], v3_signal: Dict[str, Any],
                               v1_weight: float, v3_weight: float) -> Dict[str, Any]:
        """Simple weighted average blending"""
        blended_signal = v3_signal.copy()

        # Blend numerical values
        for key in ["confidence", "volume", "strike_price", "entry_price"]:
            if key in v1_signal and key in v3_signal:
                v1_val = float(v1_signal[key]) if v1_signal[key] is not None else 0.0
                v3_val = float(v3_signal[key]) if v3_signal[key] is not None else 0.0
                blended_signal[key] = (v1_val * v1_weight + v3_val * v3_weight)

        # Use higher confidence algorithm for direction
        v1_conf = v1_signal.get("confidence", 0.0)
        v3_conf = v3_signal.get("confidence", 0.0)

        if v1_conf * v1_weight > v3_conf * v3_weight:
            blended_signal["direction"] = v1_signal.get("direction", v3_signal.get("direction"))
        else:
            blended_signal["direction"] = v3_signal.get("direction", v1_signal.get("direction"))

        # Mark as blended
        blended_signal["blended"] = True
        blended_signal["blend_weights"] = {"v1.0": v1_weight, "v3.0": v3_weight}

        return blended_signal

    def _confidence_based_blend(self, v1_signal: Dict[str, Any], v3_signal: Dict[str, Any],
                               v1_weight: float, v3_weight: float) -> Dict[str, Any]:
        """Confidence-weighted blending"""
        v1_conf = v1_signal.get("confidence", 0.0)
        v3_conf = v3_signal.get("confidence", 0.0)

        # Adjust weights based on confidence
        total_conf = v1_conf + v3_conf
        if total_conf > 0:
            conf_v1_weight = (v1_conf / total_conf) * v1_weight
            conf_v3_weight = (v3_conf / total_conf) * v3_weight

            # Normalize
            total_weight = conf_v1_weight + conf_v3_weight
            if total_weight > 0:
                conf_v1_weight /= total_weight
                conf_v3_weight /= total_weight
        else:
            conf_v1_weight = v1_weight
            conf_v3_weight = v3_weight

        return self._weighted_average_blend(v1_signal, v3_signal, conf_v1_weight, conf_v3_weight)

    def _performance_based_blend(self, v1_signal: Dict[str, Any], v3_signal: Dict[str, Any],
                                v1_weight: float, v3_weight: float) -> Dict[str, Any]:
        """Performance-history weighted blending"""
        if not self.performance_history:
            return self._weighted_average_blend(v1_signal, v3_signal, v1_weight, v3_weight)

        # Calculate recent performance
        recent_performance = list(self.performance_history)[-20:]  # Last 20 signals

        v1_accuracy = statistics.mean([p["v1_accuracy"] for p in recent_performance])
        v3_accuracy = statistics.mean([p["v3_accuracy"] for p in recent_performance])

        # Adjust weights based on performance
        total_accuracy = v1_accuracy + v3_accuracy
        if total_accuracy > 0:
            perf_v1_weight = (v1_accuracy / total_accuracy) * v1_weight
            perf_v3_weight = (v3_accuracy / total_accuracy) * v3_weight

            # Normalize
            total_weight = perf_v1_weight + perf_v3_weight
            if total_weight > 0:
                perf_v1_weight /= total_weight
                perf_v3_weight /= total_weight
        else:
            perf_v1_weight = v1_weight
            perf_v3_weight = v3_weight

        return self._weighted_average_blend(v1_signal, v3_signal, perf_v1_weight, perf_v3_weight)

    def _gradual_switch_blend(self, v1_signal: Dict[str, Any], v3_signal: Dict[str, Any],
                             v1_weight: float, v3_weight: float) -> Dict[str, Any]:
        """Gradual switching based on weights"""
        # Use deterministic switching based on weights
        import random
        random.seed(int(time.time() * 1000) % 1000)  # Semi-deterministic

        if random.random() < v3_weight:
            result = v3_signal.copy()
            result["primary_algorithm"] = "v3.0"
        else:
            result = v1_signal.copy()
            result["primary_algorithm"] = "v1.0"

        # Add blending metadata
        result["blended"] = True
        result["blend_weights"] = {"v1.0": v1_weight, "v3.0": v3_weight}

        return result

    def record_signal_result(self, blended_signal: Dict[str, Any], v1_result: Dict[str, Any],
                           v3_result: Dict[str, Any]):
        """Record signal results for performance tracking"""
        performance_record = {
            "timestamp": get_eastern_time(),
            "v1_accuracy": v1_result.get("accuracy", 0.0),
            "v3_accuracy": v3_result.get("accuracy", 0.0),
            "blended_accuracy": blended_signal.get("accuracy", 0.0),
            "correlation": self._calculate_signal_correlation(v1_result, v3_result)
        }

        self.performance_history.append(performance_record)

    def _calculate_signal_correlation(self, v1_result: Dict[str, Any], v3_result: Dict[str, Any]) -> float:
        """Calculate correlation between v1.0 and v3.0 signals"""
        try:
            # Simple correlation based on direction agreement and confidence similarity
            direction_match = 1.0 if v1_result.get("direction") == v3_result.get("direction") else 0.0

            v1_conf = v1_result.get("confidence", 0.0)
            v3_conf = v3_result.get("confidence", 0.0)

            if v1_conf > 0 and v3_conf > 0:
                conf_similarity = 1.0 - abs(v1_conf - v3_conf) / max(v1_conf, v3_conf)
            else:
                conf_similarity = 0.5

            return (direction_match * 0.7) + (conf_similarity * 0.3)
        except:
            return 0.5


class GradualTransitionManager:
    """
    Main gradual transition manager

    Coordinates smooth transition from IFD v1.0 to v3.0 with parameter
    synchronization, signal blending, and safety controls.
    """

    def __init__(self, config: TransitionConfig = None, output_dir: str = "outputs/transition"):
        self.config = config or TransitionConfig()
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Initialize components
        self.parameter_sync = ParameterSynchronizer()
        self.signal_blender = SignalBlender(self.config.blend_mode)

        # Transition state
        self.current_state = TransitionState.PREPARING
        self.transition_id = f"transition_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}"
        self.transition_start_time: Optional[datetime] = None
        self.state_start_time: Optional[datetime] = None

        # Current configurations
        self.v1_config: Optional[Dict[str, Any]] = None
        self.v3_config: Optional[Dict[str, Any]] = None
        self.current_config: Optional[Dict[str, Any]] = None

        # Blending weights
        self.current_v1_weight = 1.0
        self.current_v3_weight = 0.0

        # Metrics tracking
        self.metrics_history: deque = deque(maxlen=10000)
        self.events: deque = deque(maxlen=1000)

        # Control flags
        self.transition_active = False
        self.emergency_stop = False

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Setup transition logging"""
        import logging

        log_file = os.path.join(self.output_dir, f"transition_{get_eastern_time().strftime('%Y%m%d')}.log")

        self.logger = logging.getLogger("GradualTransition")
        if not self.logger.handlers:
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def start_transition(self, v1_config: Dict[str, Any], v3_config: Dict[str, Any]):
        """Start gradual transition process"""
        self.v1_config = v1_config.copy()
        self.v3_config = v3_config.copy()
        self.transition_start_time = get_eastern_time()
        self.transition_active = True

        self._record_event("TRANSITION_STARTED", "Gradual transition initiated")

        self.logger.info(f"Starting gradual transition: {self.transition_id}")
        print(f"🔄 Starting gradual transition: {self.transition_id}")

        # Begin with parameter synchronization
        self._transition_to_state(TransitionState.PARAMETER_SYNC)

        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._transition_monitor_loop, daemon=True)
        monitor_thread.start()

    def pause_transition(self):
        """Pause transition process"""
        self.transition_active = False
        self._record_event("TRANSITION_PAUSED", "Transition paused by operator")
        self.logger.info("Transition paused")
        print("⏸️ Transition paused")

    def resume_transition(self):
        """Resume paused transition"""
        self.transition_active = True
        self._record_event("TRANSITION_RESUMED", "Transition resumed by operator")
        self.logger.info("Transition resumed")
        print("▶️ Transition resumed")

    def emergency_rollback(self, reason: str = "Emergency rollback"):
        """Initiate emergency rollback to v1.0"""
        self.emergency_stop = True
        self.current_v1_weight = 1.0
        self.current_v3_weight = 0.0
        self.current_config = self.v1_config

        self._transition_to_state(TransitionState.ROLLING_BACK)

        self._record_event("EMERGENCY_ROLLBACK", f"Emergency rollback: {reason}")

        self.logger.error(f"Emergency rollback: {reason}")
        print(f"🚨 Emergency rollback: {reason}")

    def get_current_config(self) -> Dict[str, Any]:
        """Get current interpolated configuration"""
        if self.current_config is None:
            return self.v1_config.copy() if self.v1_config else {}
        return self.current_config.copy()

    def process_signal(self, v1_signal: Dict[str, Any], v3_signal: Dict[str, Any]) -> Dict[str, Any]:
        """Process and blend signals from both algorithms"""
        if self.current_state in [TransitionState.PREPARING, TransitionState.PARAMETER_SYNC]:
            # Use v1.0 only during preparation and parameter sync
            return v1_signal

        elif self.current_state == TransitionState.ROLLING_BACK:
            # Emergency rollback - use v1.0 only
            return v1_signal

        elif self.current_state == TransitionState.COMPLETED:
            # Transition complete - use v3.0 only
            return v3_signal

        else:
            # Blend signals during transition phases
            blended_signal = self.signal_blender.blend_signals(
                v1_signal, v3_signal,
                self.current_v1_weight, self.current_v3_weight
            )

            # Add transition metadata
            blended_signal["transition_state"] = self.current_state.value
            blended_signal["transition_id"] = self.transition_id

            return blended_signal

    def record_signal_results(self, blended_signal: Dict[str, Any],
                            v1_result: Dict[str, Any], v3_result: Dict[str, Any]):
        """Record signal execution results"""
        self.signal_blender.record_signal_result(blended_signal, v1_result, v3_result)

        # Update metrics
        self._update_metrics()

    def _transition_to_state(self, new_state: TransitionState):
        """Transition to new state"""
        old_state = self.current_state
        self.current_state = new_state
        self.state_start_time = get_eastern_time()

        self._record_event("STATE_TRANSITION", f"Transitioned from {old_state.value} to {new_state.value}")

        self.logger.info(f"State transition: {old_state.value} -> {new_state.value}")
        print(f"📈 State transition: {old_state.value} -> {new_state.value}")

    def _transition_monitor_loop(self):
        """Main transition monitoring loop"""
        while self.transition_active and not self.emergency_stop:
            try:
                self._update_transition_progress()
                self._check_safety_conditions()
                self._update_metrics()

                time.sleep(10)  # Check every 10 seconds

            except Exception as e:
                self.logger.error(f"Transition monitor error: {e}")
                time.sleep(5)

    def _update_transition_progress(self):
        """Update transition progress and state transitions"""
        if not self.state_start_time:
            return

        state_duration = get_eastern_time() - self.state_start_time

        if self.current_state == TransitionState.PARAMETER_SYNC:
            if state_duration >= timedelta(hours=self.config.parameter_sync_duration_hours):
                self._transition_to_state(TransitionState.GRADUAL_BLEND)

        elif self.current_state == TransitionState.GRADUAL_BLEND:
            # Update blending weights during gradual blend phase
            self._update_blending_weights()

            if state_duration >= timedelta(hours=self.config.blend_duration_hours):
                self._transition_to_state(TransitionState.HANDOVER)

        elif self.current_state == TransitionState.HANDOVER:
            # Final handover phase
            progress = min(1.0, state_duration.total_seconds() / (self.config.handover_duration_hours * 3600))
            self.current_v3_weight = 0.9 + (0.1 * progress)  # 90% -> 100%
            self.current_v1_weight = 1.0 - self.current_v3_weight

            if state_duration >= timedelta(hours=self.config.handover_duration_hours):
                self._transition_to_state(TransitionState.VERIFICATION)

        elif self.current_state == TransitionState.VERIFICATION:
            if state_duration >= timedelta(hours=self.config.verification_duration_hours):
                if self._verification_criteria_met():
                    self._complete_transition()
                else:
                    self.emergency_rollback("Verification criteria not met")

    def _update_blending_weights(self):
        """Update blending weights during gradual blend phase"""
        if not self.state_start_time:
            return

        state_duration = get_eastern_time() - self.state_start_time
        total_duration = timedelta(hours=self.config.blend_duration_hours)

        progress = min(1.0, state_duration.total_seconds() / total_duration.total_seconds())

        # Smooth transition curve (S-curve)
        smooth_progress = self._smooth_curve(progress)

        # Calculate weights
        weight_range = self.config.final_v3_weight - self.config.initial_v3_weight
        self.current_v3_weight = self.config.initial_v3_weight + (weight_range * smooth_progress)
        self.current_v1_weight = 1.0 - self.current_v3_weight

        # Update interpolated configuration
        self.current_config = self.parameter_sync.create_interpolated_config(
            self.v1_config, self.v3_config, self.current_v3_weight
        )

    def _smooth_curve(self, x: float) -> float:
        """Create smooth S-curve for gradual transition"""
        # Sigmoid-like curve
        return 1 / (1 + math.exp(-6 * (x - 0.5)))

    def _check_safety_conditions(self):
        """Check safety conditions and trigger rollback if needed"""
        if len(self.signal_blender.performance_history) < 10:
            return

        recent_performance = list(self.signal_blender.performance_history)[-20:]

        # Calculate performance metrics
        v1_accuracy = statistics.mean([p["v1_accuracy"] for p in recent_performance])
        v3_accuracy = statistics.mean([p["v3_accuracy"] for p in recent_performance])
        avg_correlation = statistics.mean([p["correlation"] for p in recent_performance])

        # Check emergency conditions
        performance_degradation = v1_accuracy - v3_accuracy

        if performance_degradation > self.config.emergency_fallback_threshold:
            self.emergency_rollback(f"Performance degradation: {performance_degradation:.3f}")
            return

        if avg_correlation < self.config.min_signal_correlation:
            self.emergency_rollback(f"Low signal correlation: {avg_correlation:.3f}")
            return

    def _verification_criteria_met(self) -> bool:
        """Check if verification criteria are met"""
        if len(self.signal_blender.performance_history) < self.config.min_verification_samples:
            return False

        recent_performance = list(self.signal_blender.performance_history)[-self.config.min_verification_samples:]

        v1_accuracy = statistics.mean([p["v1_accuracy"] for p in recent_performance])
        v3_accuracy = statistics.mean([p["v3_accuracy"] for p in recent_performance])

        accuracy_ratio = v3_accuracy / v1_accuracy if v1_accuracy > 0 else 0

        return accuracy_ratio >= self.config.required_accuracy_ratio

    def _complete_transition(self):
        """Complete successful transition"""
        self.current_state = TransitionState.COMPLETED
        self.transition_active = False
        self.current_v1_weight = 0.0
        self.current_v3_weight = 1.0
        self.current_config = self.v3_config

        self._record_event("TRANSITION_COMPLETED", "Gradual transition completed successfully")

        self.logger.info("Gradual transition completed successfully")
        print("✅ Gradual transition completed successfully")

    def _update_metrics(self):
        """Update transition metrics"""
        if not self.transition_start_time:
            return

        total_duration = get_eastern_time() - self.transition_start_time
        total_hours = self.config.total_transition_duration_hours
        progress_percent = min(100.0, (total_duration.total_seconds() / (total_hours * 3600)) * 100)

        # Calculate performance metrics if available
        v1_accuracy = 0.0
        v3_accuracy = 0.0
        signal_correlation = 0.0

        if self.signal_blender.performance_history:
            recent_performance = list(self.signal_blender.performance_history)[-10:]
            v1_accuracy = statistics.mean([p["v1_accuracy"] for p in recent_performance])
            v3_accuracy = statistics.mean([p["v3_accuracy"] for p in recent_performance])
            signal_correlation = statistics.mean([p["correlation"] for p in recent_performance])

        # Calculate sync completion
        sync_completion = 1.0 if self.current_state != TransitionState.PARAMETER_SYNC else 0.5

        # Calculate stability score
        stability_score = min(1.0, signal_correlation + 0.3) if signal_correlation > 0 else 1.0

        # Calculate confidence score
        confidence_score = (stability_score * 0.5) + (min(1.0, v3_accuracy / max(0.01, v1_accuracy)) * 0.5)

        metrics = TransitionMetrics(
            timestamp=get_eastern_time(),
            state=self.current_state,
            progress_percent=progress_percent,
            v1_weight=self.current_v1_weight,
            v3_weight=self.current_v3_weight,
            v1_accuracy=v1_accuracy,
            v3_accuracy=v3_accuracy,
            signal_correlation=signal_correlation,
            sync_completion=sync_completion,
            stability_score=stability_score,
            confidence_score=confidence_score
        )

        self.metrics_history.append(metrics)

    def _record_event(self, event_type: str, description: str, context: Dict[str, Any] = None):
        """Record transition event"""
        event = {
            "event_id": f"evt_{get_eastern_time().strftime('%Y%m%d_%H%M%S_%f')}",
            "timestamp": get_eastern_time(),
            "event_type": event_type,
            "description": description,
            "state": self.current_state.value,
            "context": context or {}
        }

        self.events.append(event)
        self._save_event(event)

    def _save_event(self, event: Dict[str, Any]):
        """Save event to file"""
        event_file = os.path.join(
            self.output_dir,
            f"transition_events_{get_eastern_time().strftime('%Y%m%d')}.json"
        )

        # Load existing events
        events = []
        if os.path.exists(event_file):
            try:
                with open(event_file, 'r') as f:
                    events = json.load(f)
            except:
                pass

        # Add new event
        event_to_save = event.copy()
        event_to_save["timestamp"] = event["timestamp"].isoformat()
        events.append(event_to_save)

        # Save events
        with open(event_file, 'w') as f:
            json.dump(events, f, indent=2, default=str)

    def get_transition_status(self) -> Dict[str, Any]:
        """Get current transition status"""
        if not self.transition_start_time:
            return {"status": "Not started"}

        total_duration = get_eastern_time() - self.transition_start_time

        return {
            "transition_id": self.transition_id,
            "state": self.current_state.value,
            "progress_percent": self.metrics_history[-1].progress_percent if self.metrics_history else 0.0,
            "duration_hours": total_duration.total_seconds() / 3600,
            "blending_weights": {
                "v1.0": self.current_v1_weight,
                "v3.0": self.current_v3_weight
            },
            "active": self.transition_active,
            "emergency_stop": self.emergency_stop,
            "total_events": len(self.events),
            "performance": {
                "v1_accuracy": self.metrics_history[-1].v1_accuracy if self.metrics_history else 0.0,
                "v3_accuracy": self.metrics_history[-1].v3_accuracy if self.metrics_history else 0.0,
                "correlation": self.metrics_history[-1].signal_correlation if self.metrics_history else 0.0,
                "confidence": self.metrics_history[-1].confidence_score if self.metrics_history else 0.0
            }
        }

    def generate_transition_report(self) -> str:
        """Generate formatted transition status report"""
        status = self.get_transition_status()

        report = f"""
🔄 GRADUAL TRANSITION REPORT
Transition ID: {status['transition_id']}
State: {status['state']}
Progress: {status['progress_percent']:.1f}%
Duration: {status['duration_hours']:.1f} hours
{'=' * 60}

⚖️ BLENDING WEIGHTS
v1.0: {status['blending_weights']['v1.0']:.1%}
v3.0: {status['blending_weights']['v3.0']:.1%}

📊 PERFORMANCE METRICS
v1.0 Accuracy: {status['performance']['v1_accuracy']:.1%}
v3.0 Accuracy: {status['performance']['v3_accuracy']:.1%}
Signal Correlation: {status['performance']['correlation']:.1%}
Confidence Score: {status['performance']['confidence']:.1%}

🎛️ STATUS
Active: {"Yes" if status['active'] else "No"}
Emergency Stop: {"Yes" if status['emergency_stop'] else "No"}
Events Recorded: {status['total_events']}

{'=' * 60}
        """

        return report.strip()


# Module-level convenience functions
def create_transition_manager(config: TransitionConfig = None) -> GradualTransitionManager:
    """Create gradual transition manager instance"""
    return GradualTransitionManager(config)


def create_default_transition_config() -> TransitionConfig:
    """Create default transition configuration"""
    return TransitionConfig()


if __name__ == "__main__":
    # Example usage
    config = create_default_transition_config()
    transition_manager = create_transition_manager(config)

    # Example configurations
    v1_config = {
        "volume_threshold": 1000,
        "spike_threshold": 2.0,
        "confidence_threshold": 0.8,
        "time_window": 300
    }

    v3_config = {
        "institutional_flow_v3": {
            "volume_concentration": 1200,
            "min_pressure_ratio": 1.6,
            "time_persistence": 450
        },
        "analysis_thresholds": {
            "min_confidence": 0.8
        }
    }

    print("Starting transition test...")
    transition_manager.start_transition(v1_config, v3_config)

    # Simulate signal processing
    for i in range(50):
        v1_signal = {
            "confidence": 0.8 + (i % 5) * 0.02,
            "direction": "LONG" if i % 2 == 0 else "SHORT",
            "volume": 1000 + i * 10
        }

        v3_signal = {
            "confidence": 0.85 + (i % 4) * 0.02,
            "direction": "LONG" if i % 3 != 0 else "SHORT",
            "volume": 1100 + i * 12
        }

        blended_signal = transition_manager.process_signal(v1_signal, v3_signal)

        # Simulate results
        v1_result = {"accuracy": 0.82 + (i % 6) * 0.01}
        v3_result = {"accuracy": 0.87 + (i % 5) * 0.01}

        transition_manager.record_signal_results(blended_signal, v1_result, v3_result)

        if i % 10 == 0:
            print(f"\nProgress update ({i} signals):")
            print(transition_manager.generate_transition_report())

        time.sleep(0.1)

    # Final status
    print("\nFinal Status:")
    print(transition_manager.generate_transition_report())
