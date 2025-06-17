#!/usr/bin/env python3
"""
Demo script showing IFD Live Streaming Pipeline in action
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta, timezone
import random

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(current_dir))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

def simulate_live_ifd_analysis():
    """Demonstrate the complete live streaming pipeline"""

    # Import components
    from tasks.options_trading_system.analysis_engine.live_streaming.event_processor import EventProcessor
    from tasks.options_trading_system.analysis_engine.live_streaming.pressure_aggregator import RealTimePressureEngine
    from tasks.options_trading_system.analysis_engine.live_streaming.data_validator import (
        StreamingDataValidator, create_mbo_validation_rules
    )
    from tasks.options_trading_system.analysis_engine.live_streaming.baseline_context_manager import BaselineContextManager

    print("\n" + "="*60)
    print("🚀 IFD LIVE STREAMING DEMO")
    print("="*60)

    # Create components
    print("\n📦 Initializing components...")
    processor = EventProcessor()
    pressure_engine = RealTimePressureEngine()
    validator = StreamingDataValidator(create_mbo_validation_rules())
    baseline_manager = BaselineContextManager("demo_baseline.db")

    # Track signals
    signals_detected = []

    def process_batch(batch):
        """Process batch of events through full pipeline"""
        for event in batch:
            try:
                # 1. Validate data
                should_process, validation_result = validator.validate_streaming_data(event)

                if should_process and validation_result.quality_score > 0.7:
                    # 2. Generate pressure metrics
                    pressure_metrics = pressure_engine.process_mbo_event(event)

                    if pressure_metrics:
                        for metrics in pressure_metrics:
                            # 3. Update baseline context
                            context = baseline_manager.update_baseline(
                                strike=metrics.strike,
                                option_type=metrics.option_type,
                                pressure_ratio=metrics.pressure_ratio,
                                volume=metrics.total_volume,
                                confidence=metrics.confidence,
                                timestamp=metrics.time_window
                            )

                            # 4. Check for institutional signals
                            if context.anomaly_detected and context.anomaly_severity in ['severe', 'extreme']:
                                signal = {
                                'timestamp': datetime.now(timezone.utc),
                                'strike': metrics.strike,
                                'option_type': metrics.option_type,
                                'pressure_ratio': metrics.pressure_ratio,
                                'severity': context.anomaly_severity,
                                'confidence': context.confidence,
                                'recommendation': 'BUY' if metrics.dominant_side == 'BUY' else 'SELL'
                            }
                            signals_detected.append(signal)

                            print(f"\n🎯 IFD SIGNAL DETECTED!")
                            print(f"   Strike: {signal['strike']}{signal['option_type']}")
                            print(f"   Pressure: {signal['pressure_ratio']:.2f}")
                            print(f"   Severity: {signal['severity'].upper()}")
                            print(f"   Confidence: {signal['confidence']:.2%}")
                            print(f"   Recommendation: {signal['recommendation']}")
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    # Register batch processor
    processor.register_batch_callback(process_batch)
    processor.start_processing()

    # Simulate market data
    print("\n📊 Starting market simulation...")
    print("   Simulating 2 minutes of NQ option flow...")

    start_time = datetime.now(timezone.utc)
    base_bid = 100.0
    base_ask = 100.5

    for i in range(120):  # 2 minutes of data
        current_time = start_time + timedelta(seconds=i)

        # Normal market activity
        if random.random() < 0.95:
            # Regular trade
            trade_size = random.randint(1, 20) * 10
            trade_price = random.uniform(base_bid, base_ask)
        else:
            # Institutional size trade (potential signal)
            trade_size = random.randint(50, 200) * 10
            if random.random() < 0.5:
                # Aggressive buy
                trade_price = base_ask + random.uniform(0, 0.5)
            else:
                # Aggressive sell
                trade_price = base_bid - random.uniform(0, 0.5)

        # Create MBO event
        event = {
            'timestamp': current_time,
            'instrument_id': 12345,
            'strike': 21900.0,
            'option_type': 'C',
            'bid_price': base_bid,
            'ask_price': base_ask,
            'trade_price': trade_price,
            'trade_size': trade_size,
            'side': 'BUY' if trade_price >= base_ask else 'SELL',
            'confidence': 0.85,
            'bid_px_00': int(base_bid * 1000000),
            'ask_px_00': int(base_ask * 1000000),
            'size': trade_size
        }

        processor.process_event(event)

        # Market drift
        base_bid += random.gauss(0, 0.02)
        base_ask = base_bid + 0.5

        # Progress indicator
        if i % 10 == 0:
            print(f"\r   Progress: {i+1}/120 seconds... Signals: {len(signals_detected)}", end='')

        time.sleep(0.05)  # Simulate real-time

    # Stop processing
    print("\n\n⏹️  Stopping simulation...")
    processor.stop_processing()
    time.sleep(2)  # Allow final processing

    # Summary
    print("\n" + "="*60)
    print("📈 SIMULATION RESULTS")
    print("="*60)

    # Get statistics
    processor_stats = processor.get_performance_stats()
    engine_stats = pressure_engine.get_engine_stats()
    validator_stats = validator.get_comprehensive_stats()
    baseline_stats = baseline_manager.get_manager_stats()

    print(f"\n📊 Processing Statistics:")
    print(f"   Events processed: {processor_stats['metrics']['events_processed']}")
    print(f"   Batches created: {processor_stats['metrics']['batches_created']}")
    print(f"   Filter ratio: {processor_stats['filtering']['filter_ratio']:.2%}")
    print(f"   Avg quality score: {validator_stats['metrics']['avg_quality_score']:.2f}")

    print(f"\n🎯 IFD Analysis:")
    print(f"   Pressure windows completed: {engine_stats['aggregation']['windows_completed']}")
    print(f"   Baseline updates: {baseline_stats['updates_processed']}")
    print(f"   Anomalies detected: {baseline_stats['anomalies_detected']}")
    print(f"   Signals generated: {len(signals_detected)}")

    if signals_detected:
        print(f"\n🚨 Institutional Signals:")
        for i, signal in enumerate(signals_detected[-5:], 1):  # Show last 5
            print(f"   {i}. {signal['strike']}{signal['option_type']} - "
                  f"{signal['recommendation']} (confidence: {signal['confidence']:.1%})")

    print(f"\n✅ Live streaming demonstration complete!")

    # Cleanup
    if os.path.exists("demo_baseline.db"):
        os.remove("demo_baseline.db")

if __name__ == "__main__":
    simulate_live_ifd_analysis()
