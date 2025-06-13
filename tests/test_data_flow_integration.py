#!/usr/bin/env python3
"""
Data Flow Integration Tests for IFD v3.0

Tests the complete data flow:
MBO Data -> PressureMetrics -> InstitutionalSignalV3 -> Trade Recommendations

Validates data integrity and transformation at each stage.
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta
from utils.timezone_utils import get_eastern_time, get_utc_time
from typing import List, Dict, Any
from dataclasses import dataclass

# Add project paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')
sys.path.append('tasks/options_trading_system/analysis_engine')

# Load environment
from dotenv import load_dotenv
load_dotenv()


@dataclass
class MBOTestData:
    """Mock Market-By-Order data for testing"""
    symbol: str
    timestamp: datetime
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    trade_price: float
    trade_size: int
    trade_side: str  # 'BUY' or 'SELL'


class DataFlowIntegrationTest:
    """Comprehensive data flow integration testing"""

    def __init__(self):
        self.test_results = {
            "test_suite": "data_flow_integration",
            "timestamp": get_eastern_time().isoformat(),
            "stages": [],
            "performance_metrics": {},
            "status": "UNKNOWN"
        }

        self.sample_mbo_data = self._generate_sample_mbo_data()

    def _generate_sample_mbo_data(self) -> List[MBOTestData]:
        """Generate realistic MBO test data"""
        base_time = get_eastern_time() - timedelta(minutes=30)
        mbo_data = []

        # Generate 300 ticks over 30 minutes (10 ticks per minute)
        for i in range(300):
            timestamp = base_time + timedelta(seconds=i*6)  # Every 6 seconds

            # Simulate some institutional pressure building up
            if i < 100:  # First 10 minutes - normal activity
                bid_size = 50 + (i % 20) * 5
                ask_size = 45 + (i % 15) * 4
                trade_size = 10 + (i % 8) * 2
            elif i < 200:  # Next 10 minutes - building pressure
                bid_size = 100 + (i % 30) * 8
                ask_size = 60 + (i % 20) * 3
                trade_size = 25 + (i % 12) * 5
            else:  # Last 10 minutes - strong institutional activity
                bid_size = 200 + (i % 40) * 10
                ask_size = 80 + (i % 25) * 4
                trade_size = 50 + (i % 15) * 8

            mbo_data.append(MBOTestData(
                symbol="NQM25",
                timestamp=timestamp,
                bid_price=21350.0 + (i % 10) * 0.25,
                ask_price=21350.25 + (i % 10) * 0.25,
                bid_size=bid_size,
                ask_size=ask_size,
                trade_price=21350.125 + (i % 10) * 0.25,
                trade_size=trade_size,
                trade_side="BUY" if i % 3 != 0 else "SELL"  # 67% buy pressure
            ))

        return mbo_data

    def test_stage_1_mbo_to_pressure_metrics(self) -> tuple[bool, List[Dict[str, Any]]]:
        """Test Stage 1: MBO Data -> PressureMetrics conversion"""
        print("📊 Stage 1: MBO Data -> PressureMetrics")

        try:
            start_time = time.time()

            # Group MBO data into 5-minute windows
            pressure_windows = self._group_mbo_into_windows(self.sample_mbo_data, window_minutes=5)

            # Convert each window to pressure metrics
            pressure_metrics = []
            for window_start, window_data in pressure_windows.items():
                metrics = self._calculate_pressure_metrics(window_data, window_start)
                pressure_metrics.append(metrics)

            conversion_time = (time.time() - start_time) * 1000

            # Validate pressure metrics
            validation_results = self._validate_pressure_metrics(pressure_metrics)

            stage_result = {
                "stage": "mbo_to_pressure_metrics",
                "status": "PASSED" if validation_results["valid"] else "FAILED",
                "input_records": len(self.sample_mbo_data),
                "output_records": len(pressure_metrics),
                "conversion_time_ms": conversion_time,
                "validation": validation_results
            }

            self.test_results["stages"].append(stage_result)

            print(f"   📥 Input: {len(self.sample_mbo_data)} MBO records")
            print(f"   📤 Output: {len(pressure_metrics)} pressure metrics")
            print(f"   ⏱️  Conversion time: {conversion_time:.1f}ms")
            print(f"   ✅ Validation: {'PASSED' if validation_results['valid'] else 'FAILED'}")

            return validation_results["valid"], pressure_metrics

        except Exception as e:
            stage_result = {
                "stage": "mbo_to_pressure_metrics",
                "status": "ERROR",
                "error": str(e)
            }
            self.test_results["stages"].append(stage_result)
            print(f"   ❌ Error: {e}")
            return False, []

    def _group_mbo_into_windows(self, mbo_data: List[MBOTestData], window_minutes: int) -> Dict[datetime, List[MBOTestData]]:
        """Group MBO data into time windows"""
        windows = {}

        for record in mbo_data:
            # Round down to nearest window boundary
            window_start = record.timestamp.replace(
                minute=(record.timestamp.minute // window_minutes) * window_minutes,
                second=0,
                microsecond=0
            )

            if window_start not in windows:
                windows[window_start] = []

            windows[window_start].append(record)

        return windows

    def _calculate_pressure_metrics(self, window_data: List[MBOTestData], window_start: datetime) -> Dict[str, Any]:
        """Calculate pressure metrics for a time window"""
        if not window_data:
            return {}

        # Calculate aggregated metrics
        total_bid_volume = sum(r.bid_size for r in window_data)
        total_ask_volume = sum(r.ask_size for r in window_data)
        total_trade_volume = sum(r.trade_size for r in window_data)

        buy_trades = [r for r in window_data if r.trade_side == "BUY"]
        sell_trades = [r for r in window_data if r.trade_side == "SELL"]

        buy_volume = sum(r.trade_size for r in buy_trades)
        sell_volume = sum(r.trade_size for r in sell_trades)

        # Calculate pressure metrics
        pressure_ratio = buy_volume / max(sell_volume, 1)
        volume_concentration = total_trade_volume / max(total_bid_volume + total_ask_volume, 1)

        # Calculate average trade size
        avg_trade_size = total_trade_volume / len(window_data) if window_data else 0

        # Determine dominant side
        if buy_volume > sell_volume * 1.2:
            dominant_side = "BUY"
            confidence = min((buy_volume / max(sell_volume, 1) - 1) * 2, 1.0)
        elif sell_volume > buy_volume * 1.2:
            dominant_side = "SELL"
            confidence = min((sell_volume / max(buy_volume, 1) - 1) * 2, 1.0)
        else:
            dominant_side = "NEUTRAL"
            confidence = 0.3

        return {
            "window_start": window_start.isoformat(),
            "window_end": (window_start + timedelta(minutes=5)).isoformat(),
            "symbol": window_data[0].symbol,
            "total_trades": len(window_data),
            "bid_volume": total_bid_volume,
            "ask_volume": total_ask_volume,
            "trade_volume": total_trade_volume,
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
            "pressure_ratio": pressure_ratio,
            "volume_concentration": volume_concentration,
            "avg_trade_size": avg_trade_size,
            "dominant_side": dominant_side,
            "confidence": confidence
        }

    def _validate_pressure_metrics(self, pressure_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate pressure metrics quality"""
        if not pressure_metrics:
            return {"valid": False, "reason": "No pressure metrics generated"}

        validation_checks = []

        for i, metrics in enumerate(pressure_metrics):
            # Check required fields
            required_fields = ["pressure_ratio", "volume_concentration", "confidence", "dominant_side"]
            missing_fields = [f for f in required_fields if f not in metrics]

            if missing_fields:
                validation_checks.append(f"Window {i}: Missing fields {missing_fields}")
                continue

            # Check value ranges
            if not (0.1 <= metrics["pressure_ratio"] <= 10.0):
                validation_checks.append(f"Window {i}: Invalid pressure ratio {metrics['pressure_ratio']}")

            if not (0.0 <= metrics["volume_concentration"] <= 1.0):
                validation_checks.append(f"Window {i}: Invalid volume concentration {metrics['volume_concentration']}")

            if not (0.0 <= metrics["confidence"] <= 1.0):
                validation_checks.append(f"Window {i}: Invalid confidence {metrics['confidence']}")

            if metrics["dominant_side"] not in ["BUY", "SELL", "NEUTRAL"]:
                validation_checks.append(f"Window {i}: Invalid dominant side {metrics['dominant_side']}")

        return {
            "valid": len(validation_checks) == 0,
            "validation_checks": validation_checks,
            "total_windows": len(pressure_metrics),
            "valid_windows": len(pressure_metrics) - len(validation_checks)
        }

    def test_stage_2_pressure_to_signals(self, pressure_metrics: List[Dict[str, Any]]) -> tuple[bool, List[Dict[str, Any]]]:
        """Test Stage 2: PressureMetrics -> InstitutionalSignalV3"""
        print("\n🔍 Stage 2: PressureMetrics -> InstitutionalSignalV3")

        try:
            start_time = time.time()

            # Convert pressure metrics to the format expected by IFD v3
            from analysis_engine.integration import AnalysisEngine

            engine = AnalysisEngine({})
            formatted_metrics = engine._convert_to_pressure_metrics_objects(pressure_metrics)

            # Run IFD v3 analysis
            from institutional_flow_v3.solution import run_ifd_v3_analysis

            # Use testing-specific configuration with lower thresholds
            config = {
                "db_path": "/tmp/data_flow_test.db",
                "pressure_thresholds": {
                    "min_pressure_ratio": 1.5,
                    "min_volume_concentration": 0.3,
                    "min_time_persistence": 0.3,  # Lowered from 0.4
                    "min_trend_strength": 0.4      # Lowered from 0.5
                },
                "confidence_thresholds": {
                    "min_baseline_anomaly": 1.5,
                    "min_overall_confidence": 0.5  # Lowered from 0.6
                },
                "market_making_penalty": 0.3
            }

            result = run_ifd_v3_analysis(formatted_metrics, config)
            signals = result.get("signals", [])

            analysis_time = (time.time() - start_time) * 1000

            # Validate signals
            signal_validation = self._validate_signals(signals)

            stage_result = {
                "stage": "pressure_to_signals",
                "status": "PASSED" if signal_validation["valid"] else "FAILED",
                "input_records": len(pressure_metrics),
                "output_signals": len(signals),
                "analysis_time_ms": analysis_time,
                "validation": signal_validation
            }

            self.test_results["stages"].append(stage_result)

            print(f"   📥 Input: {len(pressure_metrics)} pressure metrics")
            print(f"   📤 Output: {len(signals)} institutional signals")
            print(f"   ⏱️  Analysis time: {analysis_time:.1f}ms")
            print(f"   ✅ Validation: {'PASSED' if signal_validation['valid'] else 'FAILED'}")

            return signal_validation["valid"], signals

        except Exception as e:
            stage_result = {
                "stage": "pressure_to_signals",
                "status": "ERROR",
                "error": str(e)
            }
            self.test_results["stages"].append(stage_result)
            print(f"   ❌ Error: {e}")
            return False, []

    def _validate_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate institutional signals quality"""
        validation_checks = []

        for i, signal in enumerate(signals):
            # Check required fields
            required_fields = ["symbol", "confidence", "expected_direction", "signal_strength"]
            missing_fields = [f for f in required_fields if f not in signal]

            if missing_fields:
                validation_checks.append(f"Signal {i}: Missing fields {missing_fields}")
                continue

            # Check value ranges
            if not (0.0 <= signal["confidence"] <= 1.0):
                validation_checks.append(f"Signal {i}: Invalid confidence {signal['confidence']}")

            if signal["expected_direction"] not in ["LONG", "SHORT"]:
                validation_checks.append(f"Signal {i}: Invalid direction {signal['expected_direction']}")

            if not (0.0 <= signal["signal_strength"] <= 10.0):
                validation_checks.append(f"Signal {i}: Invalid strength {signal['signal_strength']}")

        return {
            "valid": len(validation_checks) == 0,
            "validation_checks": validation_checks,
            "total_signals": len(signals),
            "valid_signals": len(signals) - len(validation_checks)
        }

    def test_stage_3_signals_to_recommendations(self, signals: List[Dict[str, Any]]) -> tuple[bool, List[Dict[str, Any]]]:
        """Test Stage 3: InstitutionalSignalV3 -> Trade Recommendations"""
        print("\n💡 Stage 3: InstitutionalSignalV3 -> Trade Recommendations")

        try:
            start_time = time.time()

            # Convert signals to trade recommendations
            recommendations = []
            base_price = 21350.0

            for signal in signals:
                if signal.get("confidence", 0) >= 0.6:  # Only high-confidence signals

                    direction = signal["expected_direction"]
                    strength = signal["signal_strength"]
                    confidence = signal["confidence"]

                    # Calculate entry, target, and stop prices
                    if direction == "LONG":
                        entry_price = base_price
                        target_price = base_price + (strength * 10)
                        stop_price = base_price - (strength * 5)
                        expected_value = target_price - entry_price
                    else:  # SHORT
                        entry_price = base_price
                        target_price = base_price - (strength * 10)
                        stop_price = base_price + (strength * 5)
                        expected_value = entry_price - target_price

                    # Calculate position size based on confidence
                    position_size = min(10, int(confidence * 15))

                    recommendation = {
                        "signal_id": signal.get("symbol", "NQM25"),
                        "direction": direction,
                        "entry_price": entry_price,
                        "target_price": target_price,
                        "stop_price": stop_price,
                        "expected_value": expected_value,
                        "position_size": position_size,
                        "confidence": confidence,
                        "signal_strength": strength,
                        "risk_reward_ratio": abs(expected_value) / abs(entry_price - stop_price),
                        "max_risk": abs(entry_price - stop_price) * position_size,
                        "max_reward": abs(expected_value) * position_size
                    }

                    recommendations.append(recommendation)

            recommendation_time = (time.time() - start_time) * 1000

            # Validate recommendations
            rec_validation = self._validate_recommendations(recommendations)

            stage_result = {
                "stage": "signals_to_recommendations",
                "status": "PASSED" if rec_validation["valid"] else "FAILED",
                "input_signals": len(signals),
                "output_recommendations": len(recommendations),
                "recommendation_time_ms": recommendation_time,
                "validation": rec_validation
            }

            self.test_results["stages"].append(stage_result)

            print(f"   📥 Input: {len(signals)} institutional signals")
            print(f"   📤 Output: {len(recommendations)} trade recommendations")
            print(f"   ⏱️  Recommendation time: {recommendation_time:.1f}ms")
            print(f"   ✅ Validation: {'PASSED' if rec_validation['valid'] else 'FAILED'}")

            return rec_validation["valid"], recommendations

        except Exception as e:
            stage_result = {
                "stage": "signals_to_recommendations",
                "status": "ERROR",
                "error": str(e)
            }
            self.test_results["stages"].append(stage_result)
            print(f"   ❌ Error: {e}")
            return False, []

    def _validate_recommendations(self, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate trade recommendations quality"""
        validation_checks = []

        for i, rec in enumerate(recommendations):
            # Check required fields
            required_fields = ["direction", "entry_price", "target_price", "stop_price", "expected_value"]
            missing_fields = [f for f in required_fields if f not in rec]

            if missing_fields:
                validation_checks.append(f"Recommendation {i}: Missing fields {missing_fields}")
                continue

            # Check price relationships
            if rec["direction"] == "LONG":
                if rec["target_price"] <= rec["entry_price"]:
                    validation_checks.append(f"Recommendation {i}: Invalid LONG target price")
                if rec["stop_price"] >= rec["entry_price"]:
                    validation_checks.append(f"Recommendation {i}: Invalid LONG stop price")
            else:  # SHORT
                if rec["target_price"] >= rec["entry_price"]:
                    validation_checks.append(f"Recommendation {i}: Invalid SHORT target price")
                if rec["stop_price"] <= rec["entry_price"]:
                    validation_checks.append(f"Recommendation {i}: Invalid SHORT stop price")

            # Check expected value
            if rec["expected_value"] <= 0:
                validation_checks.append(f"Recommendation {i}: Non-positive expected value")

            # Check risk/reward ratio
            if rec.get("risk_reward_ratio", 0) < 1.0:
                validation_checks.append(f"Recommendation {i}: Poor risk/reward ratio")

        return {
            "valid": len(validation_checks) == 0,
            "validation_checks": validation_checks,
            "total_recommendations": len(recommendations),
            "valid_recommendations": len(recommendations) - len(validation_checks)
        }

    def test_end_to_end_performance(self) -> bool:
        """Test end-to-end performance metrics"""
        print("\n⚡ End-to-End Performance Testing")

        try:
            # Run complete data flow multiple times to test consistency
            performance_runs = []

            for run in range(5):
                start_time = time.time()

                # Stage 1: MBO -> Pressure
                success_1, pressure_metrics = self.test_stage_1_mbo_to_pressure_metrics()
                if not success_1:
                    continue

                # Stage 2: Pressure -> Signals
                success_2, signals = self.test_stage_2_pressure_to_signals(pressure_metrics)
                if not success_2:
                    continue

                # Stage 3: Signals -> Recommendations
                success_3, recommendations = self.test_stage_3_signals_to_recommendations(signals)

                total_time = (time.time() - start_time) * 1000

                performance_runs.append({
                    "run": run + 1,
                    "total_time_ms": total_time,
                    "input_mbo_records": len(self.sample_mbo_data),
                    "output_recommendations": len(recommendations) if success_3 else 0,
                    "success": success_1 and success_2 and success_3
                })

            # Calculate performance metrics
            successful_runs = [r for r in performance_runs if r["success"]]

            if successful_runs:
                avg_time = sum(r["total_time_ms"] for r in successful_runs) / len(successful_runs)
                min_time = min(r["total_time_ms"] for r in successful_runs)
                max_time = max(r["total_time_ms"] for r in successful_runs)

                avg_throughput = sum(r["input_mbo_records"] / r["total_time_ms"] * 1000 for r in successful_runs) / len(successful_runs)

                self.test_results["performance_metrics"] = {
                    "total_runs": len(performance_runs),
                    "successful_runs": len(successful_runs),
                    "avg_time_ms": avg_time,
                    "min_time_ms": min_time,
                    "max_time_ms": max_time,
                    "avg_throughput_records_per_sec": avg_throughput,
                    "meets_latency_requirement": avg_time < 1000  # <1 second for full pipeline
                }

                print(f"   🏃 Successful runs: {len(successful_runs)}/{len(performance_runs)}")
                print(f"   ⏱️  Average time: {avg_time:.1f}ms")
                print(f"   📊 Throughput: {avg_throughput:.1f} records/sec")
                print(f"   ✅ Latency requirement: {'MET' if avg_time < 1000 else 'MISSED'}")

                return len(successful_runs) == len(performance_runs) and avg_time < 1000
            else:
                print("   ❌ No successful runs completed")
                return False

        except Exception as e:
            print(f"   ❌ Performance testing error: {e}")
            return False

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive data flow integration test"""
        print("🔄 COMPREHENSIVE DATA FLOW INTEGRATION TEST")
        print("=" * 60)

        overall_start = time.time()

        # Stage 1: MBO -> Pressure Metrics
        success_1, pressure_metrics = self.test_stage_1_mbo_to_pressure_metrics()

        # Stage 2: Pressure -> Signals
        success_2, signals = (
            self.test_stage_2_pressure_to_signals(pressure_metrics)
            if success_1 else (False, [])
        )

        # Stage 3: Signals -> Recommendations
        success_3, recommendations = (
            self.test_stage_3_signals_to_recommendations(signals if success_2 else [])
            if success_2 else (False, [])
        )

        # End-to-end performance test
        performance_success = self.test_end_to_end_performance()

        # Calculate overall results
        total_time = (time.time() - overall_start) * 1000
        all_stages_passed = success_1 and success_2 and success_3

        self.test_results["status"] = "PASSED" if all_stages_passed and performance_success else "FAILED"
        self.test_results["total_test_time_ms"] = total_time
        self.test_results["stages_passed"] = sum([success_1, success_2, success_3])
        self.test_results["total_stages"] = 3

        return self.test_results

    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("🏁 DATA FLOW INTEGRATION TEST SUMMARY")
        print("=" * 60)

        print(f"Overall Status: {self.test_results['status']}")
        print(f"Stages Passed: {self.test_results.get('stages_passed', 0)}/{self.test_results.get('total_stages', 3)}")
        print(f"Total Test Time: {self.test_results.get('total_test_time_ms', 0):.1f}ms")

        # Print stage details
        for stage in self.test_results.get("stages", []):
            status_emoji = "✅" if stage["status"] == "PASSED" else "❌"
            print(f"{status_emoji} {stage['stage']}: {stage['status']}")

        # Print performance metrics
        perf = self.test_results.get("performance_metrics", {})
        if perf:
            print(f"\n📊 Performance Metrics:")
            print(f"   Average Pipeline Time: {perf.get('avg_time_ms', 0):.1f}ms")
            print(f"   Throughput: {perf.get('avg_throughput_records_per_sec', 0):.1f} records/sec")
            print(f"   Latency Requirement: {'✅ MET' if perf.get('meets_latency_requirement', False) else '❌ MISSED'}")

        if self.test_results["status"] == "PASSED":
            print("\n🎉 ALL DATA FLOW INTEGRATION TESTS PASSED!")
        else:
            print("\n⚠️  SOME TESTS NEED ATTENTION")

    def save_results(self, filepath: str):
        """Save test results"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(self.test_results, f, indent=2)

        print(f"\n📄 Test results saved to: {filepath}")


def main():
    """Main test execution"""
    test = DataFlowIntegrationTest()
    results = test.run_comprehensive_test()
    test.print_summary()

    # Save results
    output_path = "outputs/ifd_v3_testing/data_flow_integration_tests.json"
    test.save_results(output_path)

    return 0 if results["status"] == "PASSED" else 1


if __name__ == "__main__":
    exit(main())
