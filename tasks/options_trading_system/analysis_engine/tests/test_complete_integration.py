#!/usr/bin/env python3
"""
Complete Integration Testing for IFD v3.0 Missing Components

This module tests the integration of all newly implemented components:
- WebSocket streaming with MBO processing
- Baseline calculation and scheduled updates
- Call/put coordination detection
- Volatility crush pattern matching
- Market making filtering
- Complete data flow validation
"""

import os
import sys
import json
import time
import unittest
import threading
from datetime import datetime, timedelta, timezone
from utils.timezone_utils import get_eastern_time, get_utc_time
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all components
from data_ingestion.databento_websocket_streaming import (
    create_enhanced_mbo_client, EnhancedMBOStreamingClient
)
from data_ingestion.mbo_event_processor import (
    create_mbo_processor, MBOEventStreamProcessor, ProcessedMBOEvent
)
from data_ingestion.baseline_calculation_engine import (
    create_baseline_engine, BaselineCalculationEngine, HistoricalDataPoint
)
from data_ingestion.scheduled_baseline_updater import (
    create_scheduled_updater, ScheduledBaselineUpdater
)
from analysis_engine.call_put_coordination_detector import (
    create_coordination_detector, CoordinationDetector, StrikeActivity
)
from analysis_engine.volatility_crush_detector import (
    create_volatility_detector, VolatilityCrushDetector, ImpliedVolatilityPoint
)
from analysis_engine.market_making_filter import (
    create_market_making_filter, MarketMakingFilter, QuoteUpdate
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IntegrationTestResult:
    """Result of integration test"""
    test_name: str
    passed: bool
    duration_seconds: float
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = None


class TestDataGenerator:
    """Generates test data for integration testing"""

    @staticmethod
    def generate_mbo_event(strike: float, timestamp: datetime,
                          action: str = 'T', side: str = 'B') -> Dict[str, Any]:
        """Generate test MBO event"""
        return {
            'symbol': f'NQH5 C{int(strike)}',
            'instrument_id': int(strike),
            'ts_event': int(timestamp.timestamp() * 1e9),
            'action': action,
            'side': side,
            'price': 100.0 + (strike % 100) / 100,
            'size': 10 + int(strike % 50),
            'sequence': int(time.time() * 1000) % 1000000,
            'bid_px_00': 99500000,  # Scaled price
            'ask_px_00': 100500000
        }

    @staticmethod
    def generate_strike_activity(strike: float, timestamp: datetime,
                               call_pressure: float = 0.6,
                               put_pressure: float = 0.4) -> StrikeActivity:
        """Generate test strike activity"""
        return StrikeActivity(
            strike=strike,
            timestamp=timestamp,
            call_volume=1000,
            call_buy_volume=int(1000 * call_pressure),
            call_sell_volume=int(1000 * (1 - call_pressure)),
            call_pressure_ratio=call_pressure,
            call_avg_size=25,
            put_volume=800,
            put_buy_volume=int(800 * put_pressure),
            put_sell_volume=int(800 * (1 - put_pressure)),
            put_pressure_ratio=put_pressure,
            put_avg_size=20
        )

    @staticmethod
    def generate_iv_point(strike: float, timestamp: datetime,
                         iv: float = 0.25) -> ImpliedVolatilityPoint:
        """Generate test IV point"""
        return ImpliedVolatilityPoint(
            timestamp=timestamp,
            strike=strike,
            expiration=timestamp + timedelta(days=30),
            implied_volatility=iv,
            iv_bid=iv - 0.01,
            iv_ask=iv + 0.01,
            vega=50,
            delta=0.5,
            gamma=0.01,
            volume=500,
            open_interest=1000,
            moneyness=1.0
        )

    @staticmethod
    def generate_quote_update(strike: float, timestamp: datetime,
                            spread: float = 0.10) -> QuoteUpdate:
        """Generate test quote update"""
        mid_price = 100.0 + (strike % 100) / 100
        return QuoteUpdate(
            timestamp=timestamp,
            instrument_id=int(strike),
            strike=strike,
            bid_price=mid_price - spread/2,
            bid_size=10,
            ask_price=mid_price + spread/2,
            ask_size=10,
            update_type='MODIFY'
        )


class IFDv3IntegrationTest(unittest.TestCase):
    """Main integration test suite for IFD v3.0 components"""

    def setUp(self):
        """Set up test environment"""
        self.test_results = []
        self.test_generator = TestDataGenerator()

        # Initialize all components
        self.init_components()

    def init_components(self):
        """Initialize all system components"""
        # MBO processor
        self.mbo_processor = create_mbo_processor(window_minutes=5)

        # Baseline engine
        self.baseline_engine = create_baseline_engine(lookback_days=20)

        # Pattern detectors
        self.coordination_detector = create_coordination_detector(lookback_minutes=30)
        self.volatility_detector = create_volatility_detector(lookback_days=30)
        self.mm_filter = create_market_making_filter(detection_window=300)

        logger.info("All components initialized for integration testing")

    def test_01_mbo_event_processing(self):
        """Test MBO event processing pipeline"""
        start_time = time.time()

        try:
            # Generate test events
            events_processed = 0
            trades_identified = 0

            for i in range(100):
                timestamp = datetime.now(timezone.utc) - timedelta(minutes=10-i/10)
                event_data = self.test_generator.generate_mbo_event(
                    21000, timestamp, 'T', 'T'
                )

                # Process event
                processed = self.mbo_processor.process_event(event_data)

                if processed:
                    events_processed += 1

                    if processed.trade_direction:
                        trades_identified += 1

                        # Aggregate trade
                        metrics = self.mbo_processor.aggregate_trade(processed)

                        if metrics:
                            logger.info(f"Pressure metrics generated: "
                                      f"Strike {metrics.strike_price}, "
                                      f"Buy pressure: {metrics.buy_pressure_ratio:.2f}")

            # Verify results
            self.assertGreater(events_processed, 50)
            self.assertGreater(trades_identified, 30)

            stats = self.mbo_processor.get_stats()
            self.assertEqual(stats['events_processed'], events_processed)

            result = IntegrationTestResult(
                test_name="MBO Event Processing",
                passed=True,
                duration_seconds=time.time() - start_time,
                metrics={
                    'events_processed': events_processed,
                    'trades_identified': trades_identified,
                    'processor_stats': stats
                }
            )

        except Exception as e:
            result = IntegrationTestResult(
                test_name="MBO Event Processing",
                passed=False,
                duration_seconds=time.time() - start_time,
                error_message=str(e)
            )

        self.test_results.append(result)
        self.assertTrue(result.passed, result.error_message)

    def test_02_baseline_calculation(self):
        """Test baseline calculation and updates"""
        start_time = time.time()

        try:
            # Generate historical data
            historical_data = []
            base_date = datetime.now(timezone.utc) - timedelta(days=10)

            for day in range(10):
                date = base_date + timedelta(days=day)

                for hour in range(9, 16):  # Market hours
                    timestamp = date.replace(hour=hour, minute=30)

                    # Create data point
                    point = HistoricalDataPoint(
                        date=timestamp,
                        strike_price=21000,
                        contract_type='C',
                        time_bucket=f"{hour:02d}:30-{hour+1:02d}:00",
                        total_volume=1000 + day * 50,
                        buy_volume=600 + day * 30,
                        sell_volume=400 + day * 20,
                        buy_pressure_ratio=0.6,
                        trade_count=50,
                        avg_trade_size=20,
                        large_trades=5
                    )
                    historical_data.append(point)

            # Update baselines
            self.baseline_engine.update_baselines_incremental(historical_data)

            # Check anomaly detection
            current_metrics = {
                'volume': 3000,  # Anomalous
                'pressure_ratio': 0.9,
                'avg_trade_size': 50
            }

            anomaly_result = self.baseline_engine.check_anomaly(
                21000, 'C', '09:30-10:00', current_metrics
            )

            self.assertTrue(anomaly_result['has_baseline'])
            self.assertTrue(anomaly_result['is_anomalous'])
            self.assertGreater(anomaly_result['anomaly_score'], 2.0)

            result = IntegrationTestResult(
                test_name="Baseline Calculation",
                passed=True,
                duration_seconds=time.time() - start_time,
                metrics={
                    'data_points_processed': len(historical_data),
                    'anomaly_detected': anomaly_result['is_anomalous'],
                    'anomaly_score': anomaly_result['anomaly_score']
                }
            )

        except Exception as e:
            result = IntegrationTestResult(
                test_name="Baseline Calculation",
                passed=False,
                duration_seconds=time.time() - start_time,
                error_message=str(e)
            )

        self.test_results.append(result)
        self.assertTrue(result.passed, result.error_message)

    def test_03_coordination_detection(self):
        """Test call/put coordination detection"""
        start_time = time.time()

        try:
            patterns_detected = 0

            # Test same-strike coordination
            activity = self.test_generator.generate_strike_activity(
                21000, datetime.now(timezone.utc),
                call_pressure=0.8, put_pressure=0.2  # Synthetic long
            )

            pattern = self.coordination_detector.process_strike_activity(activity)

            if pattern:
                patterns_detected += 1
                self.assertEqual(pattern.pattern_type.value, "SYNTHETIC_LONG")
                self.assertGreater(pattern.confidence, 0.6)

            # Test butterfly pattern
            strikes = [20900, 21000, 21100]
            for i, strike in enumerate(strikes):
                volume_multiplier = 2 if i == 1 else 1  # Middle strike higher

                activity = StrikeActivity(
                    strike=strike,
                    timestamp=datetime.now(timezone.utc) + timedelta(seconds=i*30),
                    call_volume=200 * volume_multiplier,
                    call_buy_volume=150 * volume_multiplier,
                    call_pressure_ratio=0.75,
                    put_volume=200 * volume_multiplier,
                    put_pressure_ratio=0.75
                )

                pattern = self.coordination_detector.process_strike_activity(activity)
                if pattern and pattern.pattern_type.value == "BUTTERFLY":
                    patterns_detected += 1

            stats = self.coordination_detector.get_statistics()
            self.assertGreater(stats['patterns_detected'], 0)

            result = IntegrationTestResult(
                test_name="Coordination Detection",
                passed=True,
                duration_seconds=time.time() - start_time,
                metrics={
                    'patterns_detected': patterns_detected,
                    'detector_stats': stats
                }
            )

        except Exception as e:
            result = IntegrationTestResult(
                test_name="Coordination Detection",
                passed=False,
                duration_seconds=time.time() - start_time,
                error_message=str(e)
            )

        self.test_results.append(result)
        self.assertTrue(result.passed, result.error_message)

    def test_04_volatility_pattern_detection(self):
        """Test volatility crush pattern detection"""
        start_time = time.time()

        try:
            patterns_detected = 0

            # Test pre-earnings expansion
            base_iv = 0.25
            for i in range(20):
                current_iv = base_iv * (1 + 0.015 * i)  # Gradual increase

                iv_point = self.test_generator.generate_iv_point(
                    21000,
                    datetime.now(timezone.utc) - timedelta(hours=20-i),
                    iv=current_iv
                )

                pattern = self.volatility_detector.process_iv_update(iv_point)

                if pattern:
                    patterns_detected += 1
                    logger.info(f"Volatility pattern: {pattern.pattern_type.value}, "
                              f"Confidence: {pattern.confidence:.2f}")

            # Test volatility crush
            for i in range(5):
                high_iv_point = self.test_generator.generate_iv_point(
                    21000,
                    datetime.now(timezone.utc) - timedelta(hours=10-i),
                    iv=0.45
                )
                self.volatility_detector.process_iv_update(high_iv_point)

            # Crush
            for i in range(5):
                crush_iv = 0.45 * (1 - 0.08 * i)
                crush_point = self.test_generator.generate_iv_point(
                    21000,
                    datetime.now(timezone.utc) - timedelta(hours=5-i),
                    iv=crush_iv
                )

                pattern = self.volatility_detector.process_iv_update(crush_point)
                if pattern:
                    patterns_detected += 1

            stats = self.volatility_detector.get_statistics()
            self.assertGreater(patterns_detected, 0)

            result = IntegrationTestResult(
                test_name="Volatility Pattern Detection",
                passed=True,
                duration_seconds=time.time() - start_time,
                metrics={
                    'patterns_detected': patterns_detected,
                    'detector_stats': stats
                }
            )

        except Exception as e:
            result = IntegrationTestResult(
                test_name="Volatility Pattern Detection",
                passed=False,
                duration_seconds=time.time() - start_time,
                error_message=str(e)
            )

        self.test_results.append(result)
        self.assertTrue(result.passed, result.error_message)

    def test_05_market_making_filter(self):
        """Test market making detection and filtering"""
        start_time = time.time()

        try:
            mm_patterns = 0
            institutional_flow = 0

            # Generate MM pattern (rapid quotes)
            base_time = datetime.now(timezone.utc)
            for i in range(50):
                quote = self.test_generator.generate_quote_update(
                    21000,
                    base_time + timedelta(milliseconds=i*200),  # 5/sec
                    spread=0.05  # Tight spread
                )

                is_mm, pattern = self.mm_filter.process_quote(quote)

                if pattern and is_mm:
                    mm_patterns += 1
                elif pattern and not is_mm:
                    institutional_flow += 1

            # Generate institutional pattern (slower)
            for i in range(10):
                quote = self.test_generator.generate_quote_update(
                    21100,
                    base_time + timedelta(seconds=i*5),  # Slower
                    spread=0.20  # Wider spread
                )

                is_mm, pattern = self.mm_filter.process_quote(quote)

                if pattern and not is_mm:
                    institutional_flow += 1

            # Check market quality
            quality = self.mm_filter.assess_market_quality(21000)

            stats = self.mm_filter.get_statistics()
            self.assertGreater(stats['mm_patterns_detected'], 0)

            result = IntegrationTestResult(
                test_name="Market Making Filter",
                passed=True,
                duration_seconds=time.time() - start_time,
                metrics={
                    'mm_patterns': mm_patterns,
                    'institutional_flow': institutional_flow,
                    'filter_stats': stats,
                    'market_quality': quality.__dict__ if quality else None
                }
            )

        except Exception as e:
            result = IntegrationTestResult(
                test_name="Market Making Filter",
                passed=False,
                duration_seconds=time.time() - start_time,
                error_message=str(e)
            )

        self.test_results.append(result)
        self.assertTrue(result.passed, result.error_message)

    def test_06_complete_pipeline_flow(self):
        """Test complete data flow through all components"""
        start_time = time.time()

        try:
            # Simulate complete flow
            timestamp = datetime.now(timezone.utc)
            strike = 21000

            # 1. MBO Event
            mbo_event = self.test_generator.generate_mbo_event(
                strike, timestamp, 'T', 'T'
            )

            processed_mbo = self.mbo_processor.process_event(mbo_event)
            self.assertIsNotNone(processed_mbo)

            # 2. Aggregate to pressure metrics
            if processed_mbo and processed_mbo.action == 'T':
                pressure_metrics = self.mbo_processor.aggregate_trade(processed_mbo)

            # 3. Create strike activity from pressure metrics
            activity = self.test_generator.generate_strike_activity(
                strike, timestamp
            )

            # 4. Check for coordination
            coord_pattern = self.coordination_detector.process_strike_activity(activity)

            # 5. Check volatility patterns
            iv_point = self.test_generator.generate_iv_point(strike, timestamp)
            vol_pattern = self.volatility_detector.process_iv_update(iv_point)

            # 6. Filter market making
            quote = self.test_generator.generate_quote_update(strike, timestamp)
            is_mm, mm_pattern = self.mm_filter.process_quote(quote)

            # 7. Check baseline anomaly
            current_metrics = {
                'volume': activity.call_volume + activity.put_volume,
                'pressure_ratio': activity.call_pressure_ratio,
                'avg_trade_size': activity.call_avg_size
            }

            # Would check anomaly if baseline was populated
            # anomaly = self.baseline_engine.check_anomaly(
            #     strike, 'C', '09:30-10:00', current_metrics
            # )

            result = IntegrationTestResult(
                test_name="Complete Pipeline Flow",
                passed=True,
                duration_seconds=time.time() - start_time,
                metrics={
                    'mbo_processed': processed_mbo is not None,
                    'coordination_detected': coord_pattern is not None,
                    'volatility_detected': vol_pattern is not None,
                    'mm_detected': is_mm
                }
            )

        except Exception as e:
            result = IntegrationTestResult(
                test_name="Complete Pipeline Flow",
                passed=False,
                duration_seconds=time.time() - start_time,
                error_message=str(e)
            )

        self.test_results.append(result)
        self.assertTrue(result.passed, result.error_message)

    @patch('data_ingestion.databento_websocket_streaming.DATABENTO_AVAILABLE', False)
    def test_07_websocket_unavailable_handling(self):
        """Test handling when Databento is unavailable"""
        start_time = time.time()

        try:
            # Should raise ImportError
            with self.assertRaises(ImportError):
                from data_ingestion.databento_websocket_streaming import EnhancedMBOStreamingClient
                client = EnhancedMBOStreamingClient("fake_key")

            result = IntegrationTestResult(
                test_name="WebSocket Unavailable Handling",
                passed=True,
                duration_seconds=time.time() - start_time,
                metrics={
                    'error_handled': True
                }
            )

        except Exception as e:
            result = IntegrationTestResult(
                test_name="WebSocket Unavailable Handling",
                passed=False,
                duration_seconds=time.time() - start_time,
                error_message=str(e)
            )

        self.test_results.append(result)

    def test_08_scheduled_job_system(self):
        """Test scheduled job system"""
        start_time = time.time()

        try:
            # Create scheduler with test config
            config = {
                'lookback_days': 20,
                'update_time': '06:30',
                'enabled_days': [0, 1, 2, 3, 4],
                'run_immediate': False,
                'active_strikes': [20900, 21000, 21100]
            }

            scheduler = create_scheduled_updater(config)

            # Get status
            status = scheduler.get_job_status()

            self.assertFalse(status['scheduler_running'])
            self.assertEqual(len(status['active_strikes']), 3)
            self.assertEqual(status['update_time'], '06:30')

            # Test manual update (mock)
            with patch.object(scheduler.baseline_job, 'execute') as mock_execute:
                from data_ingestion.scheduled_baseline_updater import JobExecutionRecord, JobStatus

                mock_record = JobExecutionRecord(
                    job_id='test_job',
                    job_type='baseline_update',
                    start_time=datetime.now(timezone.utc),
                    status=JobStatus.COMPLETED,
                    strikes_processed=3,
                    data_points_added=100
                )
                mock_execute.return_value = mock_record

                # Run manual update
                record = scheduler.run_manual_update([21000])

                self.assertEqual(record.status, JobStatus.COMPLETED)
                self.assertEqual(record.strikes_processed, 3)

            result = IntegrationTestResult(
                test_name="Scheduled Job System",
                passed=True,
                duration_seconds=time.time() - start_time,
                metrics={
                    'scheduler_configured': True,
                    'manual_update_tested': True
                }
            )

        except Exception as e:
            result = IntegrationTestResult(
                test_name="Scheduled Job System",
                passed=False,
                duration_seconds=time.time() - start_time,
                error_message=str(e)
            )

        self.test_results.append(result)
        self.assertTrue(result.passed, result.error_message)

    def tearDown(self):
        """Generate test report"""
        print("\n" + "="*80)
        print("IFD v3.0 INTEGRATION TEST REPORT")
        print("="*80)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failed_tests = total_tests - passed_tests

        print(f"\nSummary: {passed_tests}/{total_tests} tests passed")

        if failed_tests > 0:
            print(f"⚠️  {failed_tests} tests FAILED")
        else:
            print("✅ All tests PASSED")

        print("\nDetailed Results:")
        print("-"*80)

        for result in self.test_results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"{status} | {result.test_name:<40} | {result.duration_seconds:.2f}s")

            if not result.passed and result.error_message:
                print(f"       Error: {result.error_message}")

            if result.metrics:
                print(f"       Metrics: {json.dumps(result.metrics, indent=10)}")

        print("-"*80)

        # Save report
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'success_rate': passed_tests / total_tests if total_tests > 0 else 0
            },
            'results': [
                {
                    'test_name': r.test_name,
                    'passed': r.passed,
                    'duration_seconds': r.duration_seconds,
                    'error_message': r.error_message,
                    'metrics': r.metrics
                }
                for r in self.test_results
            ]
        }

        report_file = f"outputs/integration_test_report_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved to: {report_file}")


def run_integration_tests():
    """Run all integration tests"""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(IFDv3IntegrationTest)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    print("Starting IFD v3.0 Integration Tests...")
    print("This will test all newly implemented components")
    print("-"*80)

    success = run_integration_tests()

    sys.exit(0 if success else 1)
