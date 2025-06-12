#!/usr/bin/env python3
"""
Production Rollout Strategy for IFD v3.0

This module provides systematic deployment and rollout capabilities for
transitioning from IFD v1.0 to v3.0 in production environments.

Features:
- Gradual traffic shifting between algorithms
- Performance-based rollout decisions
- Automatic rollback on performance degradation
- A/B testing integration
- Risk-controlled deployment
"""

import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
from collections import deque, defaultdict


class RolloutPhase(Enum):
    """Rollout phase stages"""
    PREPARATION = "PREPARATION"
    CANARY = "CANARY"  # 5% traffic
    GRADUAL = "GRADUAL"  # 25% -> 50% -> 75%
    FULL = "FULL"  # 100% traffic
    ROLLBACK = "ROLLBACK"
    COMPLETE = "COMPLETE"


class RolloutStatus(Enum):
    """Rollout execution status"""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class RolloutDecision(Enum):
    """Rollout progression decisions"""
    CONTINUE = "CONTINUE"
    PAUSE = "PAUSE"
    ROLLBACK = "ROLLBACK"
    ACCELERATE = "ACCELERATE"


@dataclass
class RolloutConfig:
    """Rollout configuration parameters"""
    # Traffic splitting
    canary_traffic_percent: float = 5.0
    gradual_traffic_steps: List[float] = None
    full_traffic_percent: float = 100.0

    # Timing
    canary_duration_minutes: int = 60  # 1 hour
    gradual_step_duration_minutes: int = 120  # 2 hours per step
    full_validation_duration_minutes: int = 240  # 4 hours

    # Performance thresholds
    min_accuracy_threshold: float = 0.85
    max_error_rate_threshold: float = 0.05
    min_success_rate_threshold: float = 0.95
    max_response_time_ms: float = 2000

    # Risk controls
    max_position_risk_percent: float = 2.0  # 2% of total portfolio
    stop_loss_threshold_percent: float = 1.0  # 1% portfolio loss

    # Comparison requirements
    min_performance_improvement: float = 0.02  # 2% improvement required
    min_sample_size: int = 100  # Minimum signals for decision

    def __post_init__(self):
        if self.gradual_traffic_steps is None:
            self.gradual_traffic_steps = [25.0, 50.0, 75.0]


@dataclass
class RolloutMetrics:
    """Performance metrics during rollout"""
    timestamp: datetime
    phase: RolloutPhase
    traffic_percent: float

    # Algorithm performance
    v1_accuracy: float = 0.0
    v3_accuracy: float = 0.0
    v1_response_time_ms: float = 0.0
    v3_response_time_ms: float = 0.0
    v1_error_rate: float = 0.0
    v3_error_rate: float = 0.0

    # Trading performance
    v1_pnl: float = 0.0
    v3_pnl: float = 0.0
    v1_signal_count: int = 0
    v3_signal_count: int = 0

    # Risk metrics
    current_exposure_percent: float = 0.0
    max_drawdown_percent: float = 0.0

    # Decision factors
    performance_delta: float = 0.0
    confidence_score: float = 0.0


@dataclass
class RolloutEvent:
    """Rollout event record"""
    event_id: str
    timestamp: datetime
    event_type: str
    phase: RolloutPhase

    description: str
    metrics: Optional[RolloutMetrics] = None
    decision: Optional[RolloutDecision] = None
    context: Dict[str, Any] = None


class TrafficSplitter:
    """Manages traffic splitting between v1.0 and v3.0"""

    def __init__(self):
        self.current_v3_percent = 0.0
        self.total_requests = 0
        self.v3_requests = 0
        self._lock = threading.Lock()

    def set_traffic_split(self, v3_percent: float):
        """Set the percentage of traffic going to v3.0"""
        with self._lock:
            self.current_v3_percent = max(0.0, min(100.0, v3_percent))

    def route_request(self, request_id: str = None) -> str:
        """Route request to v1.0 or v3.0 based on current split"""
        with self._lock:
            self.total_requests += 1

            # Use deterministic routing based on request hash for consistency
            if request_id:
                import hashlib
                hash_value = int(hashlib.md5(request_id.encode()).hexdigest()[:8], 16)
                route_to_v3 = (hash_value % 100) < self.current_v3_percent
            else:
                # Fallback to simple percentage-based routing
                route_to_v3 = (self.v3_requests / self.total_requests * 100) < self.current_v3_percent

            if route_to_v3:
                self.v3_requests += 1
                return "v3.0"
            else:
                return "v1.0"

    def get_actual_split(self) -> Dict[str, float]:
        """Get actual traffic split percentages"""
        with self._lock:
            if self.total_requests == 0:
                return {"v1.0": 0.0, "v3.0": 0.0}

            v3_actual = (self.v3_requests / self.total_requests) * 100
            v1_actual = 100.0 - v3_actual

            return {
                "v1.0": v1_actual,
                "v3.0": v3_actual,
                "total_requests": self.total_requests
            }


class PerformanceAnalyzer:
    """Analyzes algorithm performance during rollout"""

    def __init__(self, analysis_window_minutes: int = 30):
        self.analysis_window = timedelta(minutes=analysis_window_minutes)
        self.metrics_history: deque = deque(maxlen=10000)
        self._lock = threading.Lock()

    def record_algorithm_result(self, algorithm_version: str, result: Dict[str, Any]):
        """Record algorithm execution result"""
        with self._lock:
            metric_record = {
                "timestamp": datetime.now(),
                "algorithm": algorithm_version,
                "accuracy": result.get("accuracy", 0.0),
                "response_time_ms": result.get("response_time_ms", 0.0),
                "success": result.get("success", True),
                "pnl": result.get("pnl", 0.0),
                "signal_id": result.get("signal_id", "")
            }
            self.metrics_history.append(metric_record)

    def get_performance_comparison(self) -> Dict[str, Any]:
        """Compare v1.0 vs v3.0 performance in analysis window"""
        cutoff_time = datetime.now() - self.analysis_window

        # Filter recent metrics
        recent_metrics = [
            m for m in self.metrics_history
            if m["timestamp"] >= cutoff_time
        ]

        # Separate by algorithm
        v1_metrics = [m for m in recent_metrics if m["algorithm"] == "v1.0"]
        v3_metrics = [m for m in recent_metrics if m["algorithm"] == "v3.0"]

        def calculate_stats(metrics):
            if not metrics:
                return {
                    "accuracy": 0.0,
                    "response_time_ms": 0.0,
                    "error_rate": 0.0,
                    "total_pnl": 0.0,
                    "signal_count": 0
                }

            accuracy = statistics.mean(m["accuracy"] for m in metrics)
            response_time = statistics.mean(m["response_time_ms"] for m in metrics)
            error_rate = 1.0 - (sum(1 for m in metrics if m["success"]) / len(metrics))
            total_pnl = sum(m["pnl"] for m in metrics)
            signal_count = len(metrics)

            return {
                "accuracy": accuracy,
                "response_time_ms": response_time,
                "error_rate": error_rate,
                "total_pnl": total_pnl,
                "signal_count": signal_count
            }

        v1_stats = calculate_stats(v1_metrics)
        v3_stats = calculate_stats(v3_metrics)

        # Calculate performance delta
        performance_delta = 0.0
        if v1_stats["signal_count"] > 0 and v3_stats["signal_count"] > 0:
            accuracy_delta = v3_stats["accuracy"] - v1_stats["accuracy"]
            pnl_delta = v3_stats["total_pnl"] - v1_stats["total_pnl"]
            response_delta = (v1_stats["response_time_ms"] - v3_stats["response_time_ms"]) / 1000  # Normalize

            # Weighted performance score
            performance_delta = (accuracy_delta * 0.4) + (pnl_delta * 0.4) + (response_delta * 0.2)

        return {
            "v1.0": v1_stats,
            "v3.0": v3_stats,
            "performance_delta": performance_delta,
            "sample_size": {
                "v1.0": v1_stats["signal_count"],
                "v3.0": v3_stats["signal_count"]
            }
        }


class RiskMonitor:
    """Monitors risk during rollout"""

    def __init__(self, portfolio_value: float = 1000000):
        self.portfolio_value = portfolio_value
        self.position_history: deque = deque(maxlen=1000)
        self.pnl_history: deque = deque(maxlen=1000)
        self._lock = threading.Lock()

    def record_position(self, algorithm_version: str, position_value: float, pnl: float):
        """Record position and P&L"""
        with self._lock:
            record = {
                "timestamp": datetime.now(),
                "algorithm": algorithm_version,
                "position_value": position_value,
                "pnl": pnl
            }
            self.position_history.append(record)
            self.pnl_history.append(pnl)

    def get_risk_metrics(self) -> Dict[str, Any]:
        """Calculate current risk metrics"""
        if not self.position_history:
            return {
                "current_exposure_percent": 0.0,
                "max_drawdown_percent": 0.0,
                "portfolio_pnl_percent": 0.0,
                "risk_level": "LOW"
            }

        # Current exposure
        current_positions = defaultdict(float)
        for record in self.position_history[-10:]:  # Last 10 positions
            current_positions[record["algorithm"]] += record["position_value"]

        total_exposure = sum(abs(v) for v in current_positions.values())
        exposure_percent = (total_exposure / self.portfolio_value) * 100

        # P&L analysis
        if self.pnl_history:
            cumulative_pnl = list(self.pnl_history)
            running_max = 0
            max_drawdown = 0

            for pnl in cumulative_pnl:
                running_max = max(running_max, pnl)
                drawdown = running_max - pnl
                max_drawdown = max(max_drawdown, drawdown)

            max_drawdown_percent = (max_drawdown / self.portfolio_value) * 100
            total_pnl_percent = (sum(cumulative_pnl) / self.portfolio_value) * 100
        else:
            max_drawdown_percent = 0.0
            total_pnl_percent = 0.0

        # Risk level assessment
        if exposure_percent > 5.0 or max_drawdown_percent > 2.0:
            risk_level = "HIGH"
        elif exposure_percent > 2.5 or max_drawdown_percent > 1.0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "current_exposure_percent": exposure_percent,
            "max_drawdown_percent": max_drawdown_percent,
            "portfolio_pnl_percent": total_pnl_percent,
            "risk_level": risk_level,
            "position_breakdown": dict(current_positions)
        }


class ProductionRolloutStrategy:
    """
    Main production rollout strategy coordinator

    Manages systematic deployment of IFD v3.0 with gradual traffic shifting,
    performance monitoring, and automatic rollback capabilities.
    """

    def __init__(self, config: RolloutConfig = None, output_dir: str = "outputs/rollout"):
        self.config = config or RolloutConfig()
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Initialize components
        self.traffic_splitter = TrafficSplitter()
        self.performance_analyzer = PerformanceAnalyzer()
        self.risk_monitor = RiskMonitor()

        # Rollout state
        self.current_phase = RolloutPhase.PREPARATION
        self.rollout_status = RolloutStatus.PENDING
        self.rollout_id = f"rollout_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.phase_start_time: Optional[datetime] = None

        # Event tracking
        self.events: deque = deque(maxlen=1000)
        self.metrics_history: deque = deque(maxlen=10000)

        # Control flags
        self.auto_progression = True
        self.rollout_active = False

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Setup rollout logging"""
        import logging

        log_file = os.path.join(self.output_dir, f"rollout_{datetime.now().strftime('%Y%m%d')}.log")

        self.logger = logging.getLogger("ProductionRollout")
        if not self.logger.handlers:
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def start_rollout(self, portfolio_value: float = 1000000):
        """Start the production rollout process"""
        self.rollout_status = RolloutStatus.ACTIVE
        self.rollout_active = True
        self.risk_monitor.portfolio_value = portfolio_value

        # Record rollout start event
        self._record_event(
            "ROLLOUT_STARTED",
            "Production rollout initiated",
            decision=RolloutDecision.CONTINUE
        )

        self.logger.info(f"Starting production rollout: {self.rollout_id}")
        print(f"🚀 Starting production rollout: {self.rollout_id}")

        # Start with canary phase
        self._transition_to_phase(RolloutPhase.CANARY)

        # Start monitoring thread
        if self.auto_progression:
            monitor_thread = threading.Thread(target=self._rollout_monitor_loop, daemon=True)
            monitor_thread.start()

    def pause_rollout(self):
        """Pause the rollout process"""
        self.rollout_status = RolloutStatus.PAUSED
        self._record_event("ROLLOUT_PAUSED", "Rollout paused by operator")
        self.logger.info("Rollout paused")
        print("⏸️ Rollout paused")

    def resume_rollout(self):
        """Resume paused rollout"""
        if self.rollout_status == RolloutStatus.PAUSED:
            self.rollout_status = RolloutStatus.ACTIVE
            self._record_event("ROLLOUT_RESUMED", "Rollout resumed by operator")
            self.logger.info("Rollout resumed")
            print("▶️ Rollout resumed")

    def initiate_rollback(self, reason: str = "Manual rollback"):
        """Initiate immediate rollback to v1.0"""
        self._transition_to_phase(RolloutPhase.ROLLBACK)
        self.rollout_status = RolloutStatus.ROLLED_BACK

        self._record_event(
            "ROLLBACK_INITIATED",
            f"Rollback initiated: {reason}",
            decision=RolloutDecision.ROLLBACK
        )

        # Set traffic to 100% v1.0
        self.traffic_splitter.set_traffic_split(0.0)

        self.logger.warning(f"Rollback initiated: {reason}")
        print(f"🔙 Rollback initiated: {reason}")

    def route_trading_request(self, signal_data: Dict[str, Any]) -> str:
        """Route trading request to appropriate algorithm version"""
        signal_id = signal_data.get("signal_id", f"sig_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
        algorithm_version = self.traffic_splitter.route_request(signal_id)

        # Record the routing decision
        signal_data["routed_to"] = algorithm_version
        signal_data["rollout_phase"] = self.current_phase.value

        return algorithm_version

    def record_algorithm_result(self, algorithm_version: str, result: Dict[str, Any]):
        """Record algorithm execution result"""
        self.performance_analyzer.record_algorithm_result(algorithm_version, result)

        # Record risk metrics if P&L available
        if "pnl" in result and "position_value" in result:
            self.risk_monitor.record_position(
                algorithm_version,
                result["position_value"],
                result["pnl"]
            )

    def _transition_to_phase(self, new_phase: RolloutPhase):
        """Transition to new rollout phase"""
        old_phase = self.current_phase
        self.current_phase = new_phase
        self.phase_start_time = datetime.now()

        # Set appropriate traffic split
        if new_phase == RolloutPhase.CANARY:
            self.traffic_splitter.set_traffic_split(self.config.canary_traffic_percent)
        elif new_phase == RolloutPhase.GRADUAL:
            # Start with first gradual step
            self.traffic_splitter.set_traffic_split(self.config.gradual_traffic_steps[0])
        elif new_phase == RolloutPhase.FULL:
            self.traffic_splitter.set_traffic_split(self.config.full_traffic_percent)
        elif new_phase == RolloutPhase.ROLLBACK:
            self.traffic_splitter.set_traffic_split(0.0)  # Back to 100% v1.0

        self._record_event(
            "PHASE_TRANSITION",
            f"Transitioned from {old_phase.value} to {new_phase.value}",
            decision=RolloutDecision.CONTINUE
        )

        self.logger.info(f"Phase transition: {old_phase.value} -> {new_phase.value}")
        print(f"📈 Phase transition: {old_phase.value} -> {new_phase.value}")

    def _rollout_monitor_loop(self):
        """Main rollout monitoring loop"""
        while self.rollout_active and self.rollout_status == RolloutStatus.ACTIVE:
            try:
                decision = self._evaluate_rollout_progress()

                if decision == RolloutDecision.ROLLBACK:
                    self.initiate_rollback("Automatic rollback due to performance degradation")
                    break
                elif decision == RolloutDecision.CONTINUE:
                    self._check_phase_progression()

                # Record current metrics
                self._record_metrics()

                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Rollout monitor error: {e}")
                time.sleep(5)

    def _evaluate_rollout_progress(self) -> RolloutDecision:
        """Evaluate whether to continue, pause, or rollback"""
        performance_comparison = self.performance_analyzer.get_performance_comparison()
        risk_metrics = self.risk_monitor.get_risk_metrics()

        v3_stats = performance_comparison["v3.0"]

        # Check rollback conditions
        if v3_stats["signal_count"] >= self.config.min_sample_size:
            # Performance checks
            if v3_stats["accuracy"] < self.config.min_accuracy_threshold:
                return RolloutDecision.ROLLBACK

            if v3_stats["error_rate"] > self.config.max_error_rate_threshold:
                return RolloutDecision.ROLLBACK

            if v3_stats["response_time_ms"] > self.config.max_response_time_ms:
                return RolloutDecision.ROLLBACK

        # Risk checks
        if risk_metrics["risk_level"] == "HIGH":
            return RolloutDecision.ROLLBACK

        if risk_metrics["max_drawdown_percent"] > self.config.stop_loss_threshold_percent:
            return RolloutDecision.ROLLBACK

        return RolloutDecision.CONTINUE

    def _check_phase_progression(self):
        """Check if current phase should progress to next"""
        if not self.phase_start_time:
            return

        phase_duration = datetime.now() - self.phase_start_time

        if self.current_phase == RolloutPhase.CANARY:
            if phase_duration >= timedelta(minutes=self.config.canary_duration_minutes):
                if self._phase_success_criteria_met():
                    self._transition_to_phase(RolloutPhase.GRADUAL)

        elif self.current_phase == RolloutPhase.GRADUAL:
            if phase_duration >= timedelta(minutes=self.config.gradual_step_duration_minutes):
                self._progress_gradual_phase()

        elif self.current_phase == RolloutPhase.FULL:
            if phase_duration >= timedelta(minutes=self.config.full_validation_duration_minutes):
                if self._phase_success_criteria_met():
                    self._complete_rollout()

    def _progress_gradual_phase(self):
        """Progress through gradual phase steps"""
        current_split = self.traffic_splitter.current_v3_percent
        next_step = None

        for step in self.config.gradual_traffic_steps:
            if current_split < step:
                next_step = step
                break

        if next_step:
            if self._phase_success_criteria_met():
                self.traffic_splitter.set_traffic_split(next_step)
                self.phase_start_time = datetime.now()  # Reset phase timer
                self.logger.info(f"Gradual phase progression: {current_split}% -> {next_step}%")
                print(f"📊 Traffic split updated: {next_step}% to v3.0")
        else:
            # All gradual steps complete, move to full
            self._transition_to_phase(RolloutPhase.FULL)

    def _phase_success_criteria_met(self) -> bool:
        """Check if current phase meets success criteria"""
        performance_comparison = self.performance_analyzer.get_performance_comparison()
        risk_metrics = self.risk_monitor.get_risk_metrics()

        v3_stats = performance_comparison["v3.0"]

        # Minimum sample size required
        if v3_stats["signal_count"] < self.config.min_sample_size:
            return False

        # Performance requirements
        success_criteria = [
            v3_stats["accuracy"] >= self.config.min_accuracy_threshold,
            v3_stats["error_rate"] <= self.config.max_error_rate_threshold,
            v3_stats["response_time_ms"] <= self.config.max_response_time_ms,
            risk_metrics["risk_level"] != "HIGH",
            performance_comparison["performance_delta"] >= self.config.min_performance_improvement
        ]

        return all(success_criteria)

    def _complete_rollout(self):
        """Complete successful rollout"""
        self.current_phase = RolloutPhase.COMPLETE
        self.rollout_status = RolloutStatus.SUCCESSFUL
        self.rollout_active = False

        self._record_event(
            "ROLLOUT_COMPLETED",
            "Rollout completed successfully",
            decision=RolloutDecision.CONTINUE
        )

        self.logger.info("Rollout completed successfully")
        print("✅ Rollout completed successfully")

    def _record_event(self, event_type: str, description: str,
                     decision: RolloutDecision = None, context: Dict[str, Any] = None):
        """Record rollout event"""
        event = RolloutEvent(
            event_id=f"evt_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.now(),
            event_type=event_type,
            phase=self.current_phase,
            description=description,
            decision=decision,
            context=context or {}
        )

        self.events.append(event)
        self._save_event(event)

    def _record_metrics(self):
        """Record current rollout metrics"""
        performance_comparison = self.performance_analyzer.get_performance_comparison()
        risk_metrics = self.risk_monitor.get_risk_metrics()
        traffic_split = self.traffic_splitter.get_actual_split()

        metrics = RolloutMetrics(
            timestamp=datetime.now(),
            phase=self.current_phase,
            traffic_percent=traffic_split.get("v3.0", 0.0),
            v1_accuracy=performance_comparison["v1.0"]["accuracy"],
            v3_accuracy=performance_comparison["v3.0"]["accuracy"],
            v1_response_time_ms=performance_comparison["v1.0"]["response_time_ms"],
            v3_response_time_ms=performance_comparison["v3.0"]["response_time_ms"],
            v1_error_rate=performance_comparison["v1.0"]["error_rate"],
            v3_error_rate=performance_comparison["v3.0"]["error_rate"],
            v1_pnl=performance_comparison["v1.0"]["total_pnl"],
            v3_pnl=performance_comparison["v3.0"]["total_pnl"],
            v1_signal_count=performance_comparison["v1.0"]["signal_count"],
            v3_signal_count=performance_comparison["v3.0"]["signal_count"],
            current_exposure_percent=risk_metrics["current_exposure_percent"],
            max_drawdown_percent=risk_metrics["max_drawdown_percent"],
            performance_delta=performance_comparison["performance_delta"],
            confidence_score=self._calculate_confidence_score(performance_comparison, risk_metrics)
        )

        self.metrics_history.append(metrics)

    def _calculate_confidence_score(self, performance_comparison: Dict[str, Any],
                                  risk_metrics: Dict[str, Any]) -> float:
        """Calculate confidence score for rollout progression"""
        v3_stats = performance_comparison["v3.0"]

        # Sample size factor (0-1)
        sample_factor = min(1.0, v3_stats["signal_count"] / (self.config.min_sample_size * 2))

        # Performance factor (0-1)
        perf_factor = min(1.0, max(0.0, performance_comparison["performance_delta"] / 0.1))

        # Risk factor (0-1)
        risk_factor = 1.0 if risk_metrics["risk_level"] == "LOW" else (0.5 if risk_metrics["risk_level"] == "MEDIUM" else 0.0)

        # Weighted confidence score
        confidence = (sample_factor * 0.3) + (perf_factor * 0.4) + (risk_factor * 0.3)

        return confidence

    def _save_event(self, event: RolloutEvent):
        """Save event to file"""
        event_file = os.path.join(
            self.output_dir,
            f"rollout_events_{datetime.now().strftime('%Y%m%d')}.json"
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
        event_dict = asdict(event)
        event_dict["timestamp"] = event.timestamp.isoformat()
        if event_dict["metrics"]:
            event_dict["metrics"]["timestamp"] = event_dict["metrics"]["timestamp"].isoformat()

        events.append(event_dict)

        # Save events
        with open(event_file, 'w') as f:
            json.dump(events, f, indent=2, default=str)

    def get_rollout_status(self) -> Dict[str, Any]:
        """Get current rollout status"""
        traffic_split = self.traffic_splitter.get_actual_split()
        performance_comparison = self.performance_analyzer.get_performance_comparison()
        risk_metrics = self.risk_monitor.get_risk_metrics()

        return {
            "rollout_id": self.rollout_id,
            "status": self.rollout_status.value,
            "phase": self.current_phase.value,
            "phase_start_time": self.phase_start_time.isoformat() if self.phase_start_time else None,
            "traffic_split": traffic_split,
            "performance": performance_comparison,
            "risk_metrics": risk_metrics,
            "auto_progression": self.auto_progression,
            "total_events": len(self.events)
        }

    def generate_rollout_report(self) -> str:
        """Generate formatted rollout status report"""
        status = self.get_rollout_status()

        report = f"""
🚀 PRODUCTION ROLLOUT REPORT
Rollout ID: {status['rollout_id']}
Status: {status['status']}
Phase: {status['phase']}
{'=' * 60}

📊 TRAFFIC SPLIT
v1.0: {status['traffic_split']['v1.0']:.1f}%
v3.0: {status['traffic_split']['v3.0']:.1f}%
Total Requests: {status['traffic_split']['total_requests']:,}

📈 PERFORMANCE COMPARISON
v1.0 Accuracy: {status['performance']['v1.0']['accuracy']:.1%} ({status['performance']['v1.0']['signal_count']} signals)
v3.0 Accuracy: {status['performance']['v3.0']['accuracy']:.1%} ({status['performance']['v3.0']['signal_count']} signals)
Performance Delta: {status['performance']['performance_delta']:.3f}

💰 P&L COMPARISON
v1.0 P&L: ${status['performance']['v1.0']['total_pnl']:.2f}
v3.0 P&L: ${status['performance']['v3.0']['total_pnl']:.2f}

⚠️ RISK METRICS
Current Exposure: {status['risk_metrics']['current_exposure_percent']:.1f}%
Max Drawdown: {status['risk_metrics']['max_drawdown_percent']:.2f}%
Risk Level: {status['risk_metrics']['risk_level']}

🎯 PHASE PROGRESS
Auto Progression: {"Enabled" if status['auto_progression'] else "Disabled"}
Events Recorded: {status['total_events']}

{'=' * 60}
        """

        return report.strip()


# Module-level convenience functions
def create_rollout_strategy(config: RolloutConfig = None) -> ProductionRolloutStrategy:
    """Create production rollout strategy instance"""
    return ProductionRolloutStrategy(config)


def create_default_config() -> RolloutConfig:
    """Create default rollout configuration"""
    return RolloutConfig()


if __name__ == "__main__":
    # Example usage
    config = create_default_config()
    rollout = create_rollout_strategy(config)

    print("Starting rollout test...")
    rollout.start_rollout(portfolio_value=1000000)

    # Simulate some trading requests and results
    for i in range(100):
        signal_data = {
            "signal_id": f"test_signal_{i}",
            "symbol": "NQM25",
            "confidence": 0.85 + (i % 10) * 0.01
        }

        algorithm = rollout.route_trading_request(signal_data)

        # Simulate algorithm result
        result = {
            "accuracy": 0.87 + (i % 5) * 0.02,
            "response_time_ms": 150 + (i % 3) * 50,
            "success": True,
            "pnl": (i % 7) - 3,  # Random P&L
            "position_value": 1000,
            "signal_id": signal_data["signal_id"]
        }

        rollout.record_algorithm_result(algorithm, result)

        if i % 20 == 0:
            print(f"\nProgress update ({i} requests):")
            print(rollout.generate_rollout_report())

        time.sleep(0.1)  # Simulate time between requests

    # Final status
    print("\nFinal Status:")
    print(rollout.generate_rollout_report())
