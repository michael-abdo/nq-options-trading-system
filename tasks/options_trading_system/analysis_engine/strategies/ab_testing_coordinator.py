#!/usr/bin/env python3
"""
A/B Testing Coordinator for IFD v1.0 vs v3.0 Comparison

This module provides comprehensive A/B testing capabilities for comparing
the performance of IFD v1.0 (Dead Simple) and v3.0 (Enhanced MBO Streaming)
algorithms in real-time and historical scenarios.

Features:
- Parallel execution of both algorithms on same data
- Real-time signal comparison and correlation analysis
- Performance metrics tracking and reporting
- Cost analysis and optimization recommendations
- Backward compatibility with existing pipeline
"""

import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import statistics
from collections import defaultdict

from ..config_manager import ConfigManager, AlgorithmVersion
from ..integration import AnalysisEngine


@dataclass
class SignalComparison:
    """Comparison data structure for v1.0 vs v3.0 signals"""
    timestamp: datetime
    symbol: str
    strike: float

    # v1.0 Signal Data
    v1_signal_detected: bool
    v1_confidence: float
    v1_direction: str
    v1_volume_metrics: Dict[str, Any]
    v1_execution_time_ms: float

    # v3.0 Signal Data
    v3_signal_detected: bool
    v3_confidence: float
    v3_direction: str
    v3_pressure_metrics: Dict[str, Any]
    v3_baseline_context: Dict[str, Any]
    v3_execution_time_ms: float

    # Comparison Metrics
    signal_agreement: bool  # Both detected signal
    direction_agreement: bool  # Same direction
    confidence_difference: float
    performance_difference_ms: float


@dataclass
class PerformanceMetrics:
    """Performance tracking for algorithm comparison"""
    algorithm_version: str

    # Signal Quality Metrics
    total_signals: int
    signal_accuracy: float
    win_rate: float
    false_positive_rate: float
    average_confidence: float

    # Processing Performance
    average_processing_time: float
    max_processing_time: float
    memory_usage_mb: float

    # Trading Performance (Paper Trading)
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float

    # Cost Analysis
    api_calls_made: int
    processing_cost: float
    total_cost: float


@dataclass
class ABTestResults:
    """Comprehensive A/B testing results"""
    test_start: datetime
    test_end: datetime
    test_duration_hours: float

    # Algorithm Performance
    v1_metrics: PerformanceMetrics
    v3_metrics: PerformanceMetrics

    # Comparison Analysis
    signal_correlations: List[SignalComparison]
    agreement_rate: float
    performance_winner: str
    cost_winner: str

    # Recommendations
    recommended_algorithm: str
    confidence_in_recommendation: float
    reasoning: List[str]


class ABTestingCoordinator:
    """
    A/B Testing Coordinator for IFD v1.0 vs v3.0 comparison

    Responsibilities:
    - Execute both algorithms in parallel on same data
    - Track and compare signal generation
    - Measure performance metrics and costs
    - Generate comprehensive comparison reports
    - Provide algorithm selection recommendations
    """

    def __init__(self, config_manager: ConfigManager, output_dir: str = "outputs/ab_testing"):
        """
        Initialize A/B testing coordinator

        Args:
            config_manager: Configuration manager instance
            output_dir: Directory for saving test results
        """
        self.config_manager = config_manager
        self.output_dir = output_dir

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Performance tracking
        self.signal_comparisons: List[SignalComparison] = []
        self.v1_metrics = self._init_performance_metrics("v1.0")
        self.v3_metrics = self._init_performance_metrics("v3.0")

        # Test state
        self.test_active = False
        self.test_start_time: Optional[datetime] = None
        self.test_end_time: Optional[datetime] = None

        # Thread safety
        self._lock = threading.Lock()

    def _init_performance_metrics(self, version: str) -> PerformanceMetrics:
        """Initialize performance metrics structure"""
        return PerformanceMetrics(
            algorithm_version=version,
            total_signals=0,
            signal_accuracy=0.0,
            win_rate=0.0,
            false_positive_rate=0.0,
            average_confidence=0.0,
            average_processing_time=0.0,
            max_processing_time=0.0,
            memory_usage_mb=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            total_pnl=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            api_calls_made=0,
            processing_cost=0.0,
            total_cost=0.0
        )

    def start_ab_test(self, v1_profile: str, v3_profile: str,
                     duration_hours: float = 24.0, data_config: Dict[str, Any] = None) -> str:
        """
        Start A/B testing between v1.0 and v3.0 algorithms

        Args:
            v1_profile: Configuration profile name for v1.0
            v3_profile: Configuration profile name for v3.0
            duration_hours: Test duration in hours
            data_config: Data configuration for testing

        Returns:
            Test session ID
        """
        if self.test_active:
            raise RuntimeError("A/B test already active. Stop current test first.")

        # Validate profiles exist
        v1_config = self.config_manager.get_profile(v1_profile)
        v3_config = self.config_manager.get_profile(v3_profile)

        if not v1_config or not v3_config:
            raise ValueError(f"Invalid profiles: {v1_profile}, {v3_profile}")

        # Initialize test state
        self.test_active = True
        self.test_start_time = datetime.now()
        self.test_end_time = self.test_start_time + timedelta(hours=duration_hours)

        # Reset metrics
        self.v1_metrics = self._init_performance_metrics("v1.0")
        self.v3_metrics = self._init_performance_metrics("v3.0")
        self.signal_comparisons.clear()

        # Generate test session ID
        session_id = f"ab_test_{self.test_start_time.strftime('%Y%m%d_%H%M%S')}"

        print(f"🚀 Starting A/B Test: {session_id}")
        print(f"   v1.0 Profile: {v1_profile}")
        print(f"   v3.0 Profile: {v3_profile}")
        print(f"   Duration: {duration_hours} hours")
        print(f"   End Time: {self.test_end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Start parallel execution in background thread
        test_thread = threading.Thread(
            target=self._run_parallel_testing,
            args=(v1_profile, v3_profile, data_config),
            daemon=True
        )
        test_thread.start()

        return session_id

    def _run_parallel_testing(self, v1_profile: str, v3_profile: str,
                            data_config: Dict[str, Any] = None):
        """Run parallel testing of both algorithms"""

        try:
            # Get configurations
            v1_analysis_config = self.config_manager.get_analysis_config(v1_profile)
            v3_analysis_config = self.config_manager.get_analysis_config(v3_profile)

            if data_config is None:
                data_config = {"mode": "simulation"}  # Default to simulation

            print("   📊 Parallel execution started...")

            # Main testing loop
            iteration = 0
            while self.test_active and datetime.now() < self.test_end_time:
                iteration += 1

                try:
                    # Run both algorithms in parallel
                    comparison = self._execute_parallel_analysis(
                        v1_analysis_config, v3_analysis_config, data_config
                    )

                    if comparison:
                        with self._lock:
                            self.signal_comparisons.append(comparison)
                            self._update_performance_metrics(comparison)

                    # Progress update every 10 iterations
                    if iteration % 10 == 0:
                        elapsed = (datetime.now() - self.test_start_time).total_seconds() / 3600
                        remaining = (self.test_end_time - datetime.now()).total_seconds() / 3600
                        print(f"   ⏱️  Progress: {elapsed:.1f}h elapsed, {remaining:.1f}h remaining")
                        print(f"      Signals: v1.0={self.v1_metrics.total_signals}, v3.0={self.v3_metrics.total_signals}")

                    # Wait before next iteration (5 minute intervals)
                    time.sleep(300)  # 5 minutes

                except Exception as e:
                    print(f"   ⚠️  Error in iteration {iteration}: {e}")
                    continue

        except Exception as e:
            print(f"   ❌ Fatal error in parallel testing: {e}")

        finally:
            self.test_active = False
            print("   ✅ Parallel testing completed")

    def _execute_parallel_analysis(self, v1_config: Dict[str, Any], v3_config: Dict[str, Any],
                                 data_config: Dict[str, Any]) -> Optional[SignalComparison]:
        """Execute both algorithms in parallel and compare results"""

        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both analyses
            v1_future = executor.submit(self._run_v1_analysis, v1_config, data_config)
            v3_future = executor.submit(self._run_v3_analysis, v3_config, data_config)

            # Collect results
            v1_result = None
            v3_result = None
            v1_time = 0.0
            v3_time = 0.0

            for future in as_completed([v1_future, v3_future]):
                if future == v1_future:
                    v1_result, v1_time = future.result()
                else:
                    v3_result, v3_time = future.result()

        # Compare results
        if v1_result and v3_result:
            return self._compare_analysis_results(v1_result, v3_result, v1_time, v3_time)

        return None

    def _run_v1_analysis(self, config: Dict[str, Any], data_config: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """Run v1.0 analysis and measure performance"""
        start_time = time.time()

        try:
            # Create engine with v1.0 configuration
            engine = AnalysisEngine(config)

            # Run dead simple analysis
            result = engine.run_dead_simple_analysis(data_config)

            processing_time = time.time() - start_time
            return result, processing_time

        except Exception as e:
            print(f"v1.0 analysis error: {e}")
            processing_time = time.time() - start_time
            return {"status": "failed", "error": str(e)}, processing_time

    def _run_v3_analysis(self, config: Dict[str, Any], data_config: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """Run v3.0 analysis and measure performance"""
        start_time = time.time()

        try:
            # Create engine with v3.0 configuration
            engine = AnalysisEngine(config)

            # Run IFD v3.0 analysis
            result = engine.run_ifd_v3_analysis(data_config)

            processing_time = time.time() - start_time
            return result, processing_time

        except Exception as e:
            print(f"v3.0 analysis error: {e}")
            processing_time = time.time() - start_time
            return {"status": "failed", "error": str(e)}, processing_time

    def _compare_analysis_results(self, v1_result: Dict[str, Any], v3_result: Dict[str, Any],
                                v1_time: float, v3_time: float) -> SignalComparison:
        """Compare results from both algorithms"""

        # Extract v1.0 signals
        v1_signals = []
        if v1_result.get("status") == "success" and "result" in v1_result:
            v1_data = v1_result["result"]
            if "signals" in v1_data:
                v1_signals = v1_data["signals"]

        # Extract v3.0 signals
        v3_signals = []
        if v3_result.get("status") == "success" and "result" in v3_result:
            v3_data = v3_result["result"]
            if "signals" in v3_data:
                v3_signals = v3_data["signals"]

        # Create comparison (use first signal from each or default values)
        v1_signal = v1_signals[0] if v1_signals else None
        v3_signal = v3_signals[0] if v3_signals else None

        # Extract comparison data
        timestamp = datetime.now()
        symbol = "NQM25"  # Default symbol
        strike = 21350.0  # Default strike

        v1_detected = len(v1_signals) > 0
        v1_confidence = v1_signal.get("confidence", 0.0) if v1_signal else 0.0
        v1_direction = v1_signal.get("direction", "NONE") if v1_signal else "NONE"

        v3_detected = len(v3_signals) > 0
        v3_confidence = v3_signal.get("confidence", 0.0) if v3_signal else 0.0
        v3_direction = v3_signal.get("expected_direction", "NONE") if v3_signal else "NONE"

        # Calculate agreement metrics
        signal_agreement = v1_detected and v3_detected
        direction_agreement = v1_direction == v3_direction if signal_agreement else False

        # Calculate confidence correlation
        confidence_correlation = 0.0
        if v1_confidence > 0 and v3_confidence > 0:
            # Simple correlation approximation
            avg_conf = (v1_confidence + v3_confidence) / 2
            diff = abs(v1_confidence - v3_confidence)
            confidence_correlation = max(0, 1 - (diff / avg_conf))

        return SignalComparison(
            timestamp=timestamp,
            symbol=symbol,
            strike=strike,
            v1_signal_detected=v1_detected,
            v1_confidence=v1_confidence,
            v1_direction=v1_direction,
            v1_volume_metrics=v1_signal.to_dict() if v1_signal and hasattr(v1_signal, 'to_dict') else {},
            v3_signal_detected=v3_detected,
            v3_confidence=v3_confidence,
            v3_direction=v3_direction,
            v3_pressure_metrics=v3_signal if isinstance(v3_signal, dict) else {},
            v3_baseline_context={},
            signal_agreement=signal_agreement,
            direction_agreement=direction_agreement,
            confidence_correlation=confidence_correlation,
            processing_time_v1=v1_time,
            processing_time_v3=v3_time
        )

    def _update_performance_metrics(self, comparison: SignalComparison):
        """Update performance metrics based on comparison results"""

        # Update v1.0 metrics
        if comparison.v1_signal_detected:
            self.v1_metrics.total_signals += 1
            self.v1_metrics.average_confidence = (
                (self.v1_metrics.average_confidence * (self.v1_metrics.total_signals - 1) +
                 comparison.v1_confidence) / self.v1_metrics.total_signals
            )

        # Update v3.0 metrics
        if comparison.v3_signal_detected:
            self.v3_metrics.total_signals += 1
            self.v3_metrics.average_confidence = (
                (self.v3_metrics.average_confidence * (self.v3_metrics.total_signals - 1) +
                 comparison.v3_confidence) / self.v3_metrics.total_signals
            )

        # Update processing times
        self._update_processing_metrics(self.v1_metrics, comparison.processing_time_v1)
        self._update_processing_metrics(self.v3_metrics, comparison.processing_time_v3)

    def _update_processing_metrics(self, metrics: PerformanceMetrics, processing_time: float):
        """Update processing time metrics"""
        metrics.max_processing_time = max(metrics.max_processing_time, processing_time)

        # Update average processing time
        total_samples = metrics.total_signals if metrics.total_signals > 0 else 1
        metrics.average_processing_time = (
            (metrics.average_processing_time * (total_samples - 1) + processing_time) / total_samples
        )

    def stop_ab_test(self) -> ABTestResults:
        """Stop current A/B test and generate results"""

        if not self.test_active:
            raise RuntimeError("No active A/B test to stop")

        self.test_active = False
        self.test_end_time = datetime.now()

        print("🛑 Stopping A/B Test...")
        print(f"   Duration: {(self.test_end_time - self.test_start_time).total_seconds() / 3600:.2f} hours")
        print(f"   Comparisons: {len(self.signal_comparisons)}")

        # Generate comprehensive results
        results = self._generate_ab_test_results()

        # Save results
        self._save_results(results)

        return results

    def _generate_ab_test_results(self) -> ABTestResults:
        """Generate comprehensive A/B test results"""

        if not self.test_start_time or not self.test_end_time:
            raise RuntimeError("Test not properly initialized")

        test_duration = (self.test_end_time - self.test_start_time).total_seconds() / 3600

        # Calculate agreement metrics
        total_comparisons = len(self.signal_comparisons)
        signal_agreements = sum(1 for c in self.signal_comparisons if c.signal_agreement)
        agreement_rate = signal_agreements / total_comparisons if total_comparisons > 0 else 0.0

        # Determine winners
        performance_winner = self._determine_performance_winner()
        cost_winner = self._determine_cost_winner()

        # Generate recommendations
        recommendation, confidence, reasoning = self._generate_recommendations()

        return ABTestResults(
            test_start=self.test_start_time,
            test_end=self.test_end_time,
            test_duration_hours=test_duration,
            v1_metrics=self.v1_metrics,
            v3_metrics=self.v3_metrics,
            signal_correlations=self.signal_comparisons,
            agreement_rate=agreement_rate,
            performance_winner=performance_winner,
            cost_winner=cost_winner,
            recommended_algorithm=recommendation,
            confidence_in_recommendation=confidence,
            reasoning=reasoning
        )

    def _determine_performance_winner(self) -> str:
        """Determine performance winner based on multiple metrics"""

        v1_score = 0
        v3_score = 0

        # Compare signal generation
        if self.v3_metrics.total_signals > self.v1_metrics.total_signals:
            v3_score += 1
        elif self.v1_metrics.total_signals > self.v3_metrics.total_signals:
            v1_score += 1

        # Compare average confidence
        if self.v3_metrics.average_confidence > self.v1_metrics.average_confidence:
            v3_score += 1
        elif self.v1_metrics.average_confidence > self.v3_metrics.average_confidence:
            v1_score += 1

        # Compare processing speed
        if self.v1_metrics.average_processing_time < self.v3_metrics.average_processing_time:
            v1_score += 1
        elif self.v3_metrics.average_processing_time < self.v1_metrics.average_processing_time:
            v3_score += 1

        if v3_score > v1_score:
            return "v3.0"
        elif v1_score > v3_score:
            return "v1.0"
        else:
            return "tie"

    def _determine_cost_winner(self) -> str:
        """Determine cost winner (simulated for now)"""
        # v1.0 typically cheaper due to simpler processing
        # v3.0 more expensive due to MBO streaming and complex analysis

        if self.v1_metrics.average_processing_time < self.v3_metrics.average_processing_time:
            return "v1.0"
        else:
            return "v3.0"

    def _generate_recommendations(self) -> Tuple[str, float, List[str]]:
        """Generate algorithm recommendation with confidence and reasoning"""

        reasoning = []
        v1_advantages = 0
        v3_advantages = 0

        # Analyze signal quality
        if self.v3_metrics.average_confidence > self.v1_metrics.average_confidence:
            v3_advantages += 1
            reasoning.append(f"v3.0 has higher average confidence ({self.v3_metrics.average_confidence:.3f} vs {self.v1_metrics.average_confidence:.3f})")
        elif self.v1_metrics.average_confidence > self.v3_metrics.average_confidence:
            v1_advantages += 1
            reasoning.append(f"v1.0 has higher average confidence ({self.v1_metrics.average_confidence:.3f} vs {self.v3_metrics.average_confidence:.3f})")

        # Analyze processing performance
        if self.v1_metrics.average_processing_time < self.v3_metrics.average_processing_time:
            v1_advantages += 1
            reasoning.append(f"v1.0 is faster ({self.v1_metrics.average_processing_time:.3f}s vs {self.v3_metrics.average_processing_time:.3f}s)")
        elif self.v3_metrics.average_processing_time < self.v1_metrics.average_processing_time:
            v3_advantages += 1
            reasoning.append(f"v3.0 is faster ({self.v3_metrics.average_processing_time:.3f}s vs {self.v1_metrics.average_processing_time:.3f}s)")

        # Analyze signal generation
        if self.v3_metrics.total_signals > self.v1_metrics.total_signals:
            v3_advantages += 1
            reasoning.append(f"v3.0 generated more signals ({self.v3_metrics.total_signals} vs {self.v1_metrics.total_signals})")
        elif self.v1_metrics.total_signals > self.v3_metrics.total_signals:
            v1_advantages += 1
            reasoning.append(f"v1.0 generated more signals ({self.v1_metrics.total_signals} vs {self.v3_metrics.total_signals})")

        # Determine recommendation
        if v3_advantages > v1_advantages:
            recommendation = "v3.0"
            confidence = min(0.9, 0.6 + (v3_advantages - v1_advantages) * 0.1)
        elif v1_advantages > v3_advantages:
            recommendation = "v1.0"
            confidence = min(0.9, 0.6 + (v1_advantages - v3_advantages) * 0.1)
        else:
            recommendation = "v3.0"  # Default to v3.0 for ties (more advanced)
            confidence = 0.5
            reasoning.append("Close performance - recommending v3.0 for advanced features")

        return recommendation, confidence, reasoning

    def _save_results(self, results: ABTestResults):
        """Save A/B test results to files"""

        timestamp = results.test_start.strftime("%Y%m%d_%H%M%S")

        # Save main results
        results_file = os.path.join(self.output_dir, f"ab_test_results_{timestamp}.json")
        with open(results_file, 'w') as f:
            json.dump(asdict(results), f, indent=2, default=str)

        # Save detailed comparisons
        comparisons_file = os.path.join(self.output_dir, f"signal_comparisons_{timestamp}.json")
        comparisons_data = [asdict(comp) for comp in results.signal_correlations]
        with open(comparisons_file, 'w') as f:
            json.dump(comparisons_data, f, indent=2, default=str)

        print(f"💾 Results saved:")
        print(f"   Main results: {results_file}")
        print(f"   Comparisons: {comparisons_file}")

    def get_test_status(self) -> Dict[str, Any]:
        """Get current test status and interim results"""

        if not self.test_active:
            return {"status": "inactive", "message": "No active A/B test"}

        elapsed = (datetime.now() - self.test_start_time).total_seconds() / 3600
        remaining = (self.test_end_time - datetime.now()).total_seconds() / 3600

        return {
            "status": "active",
            "test_start": self.test_start_time.isoformat(),
            "elapsed_hours": elapsed,
            "remaining_hours": max(0, remaining),
            "comparisons_collected": len(self.signal_comparisons),
            "v1_signals": self.v1_metrics.total_signals,
            "v3_signals": self.v3_metrics.total_signals,
            "v1_avg_confidence": self.v1_metrics.average_confidence,
            "v3_avg_confidence": self.v3_metrics.average_confidence,
            "v1_avg_processing_time": self.v1_metrics.average_processing_time,
            "v3_avg_processing_time": self.v3_metrics.average_processing_time
        }


# Module-level convenience functions
def create_ab_coordinator(config_manager: ConfigManager = None) -> ABTestingCoordinator:
    """Create A/B testing coordinator instance"""
    if config_manager is None:
        from ..config_manager import get_config_manager
        config_manager = get_config_manager()

    return ABTestingCoordinator(config_manager)


def run_quick_ab_test(duration_minutes: int = 30) -> ABTestResults:
    """Run a quick A/B test for specified duration"""

    from ..config_manager import get_config_manager

    coordinator = create_ab_coordinator(get_config_manager())

    # Start test
    session_id = coordinator.start_ab_test(
        "ifd_v1_production",
        "ifd_v3_production",
        duration_hours=duration_minutes / 60.0
    )

    print(f"Running quick A/B test for {duration_minutes} minutes...")

    # Wait for completion
    import time
    time.sleep(duration_minutes * 60)

    # Stop and get results
    results = coordinator.stop_ab_test()

    print(f"✅ Quick A/B test completed")
    print(f"   Winner: {results.recommended_algorithm}")
    print(f"   Confidence: {results.confidence_in_recommendation:.1%}")

    return results


if __name__ == "__main__":
    # Example usage
    from ..config_manager import get_config_manager

    # Create coordinator
    coordinator = create_ab_coordinator()

    # Run a 5-minute test
    print("Starting 5-minute A/B test...")

    session_id = coordinator.start_ab_test(
        "ifd_v1_production",
        "ifd_v3_production",
        duration_hours=5/60  # 5 minutes
    )

    # Check status
    import time
    time.sleep(10)  # Wait 10 seconds

    status = coordinator.get_test_status()
    print(f"Test status: {status}")

    # Let it run for a bit then stop
    time.sleep(60)  # 1 minute

    results = coordinator.stop_ab_test()
    print(f"Recommended algorithm: {results.recommended_algorithm}")
    print(f"Confidence: {results.confidence_in_recommendation:.1%}")
    print(f"Reasoning: {results.reasoning}")
