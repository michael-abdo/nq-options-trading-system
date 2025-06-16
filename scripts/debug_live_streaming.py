#!/usr/bin/env python3
"""
Debug script for live streaming issues
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta, timezone

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(current_dir))

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_pressure_aggregator():
    """Debug why pressure metrics aren't being generated"""
    print("\n=== DEBUGGING PRESSURE AGGREGATOR ===")

    from tasks.options_trading_system.analysis_engine.pressure_aggregator import (
        RealTimePressureEngine, MultiTimeframeAggregator, WindowConfig
    )

    # Create engine with shorter windows for testing
    engine = RealTimePressureEngine(timeframes=[1])  # Just 1-minute windows

    # Track metrics
    metrics_received = []

    def pressure_callback(metrics):
        metrics_received.append(metrics)
        print(f"📊 Metric: {metrics.strike}{metrics.option_type} "
              f"window={metrics.window_duration}m "
              f"pressure={metrics.pressure_ratio:.2f}")

    engine.register_pressure_callback(pressure_callback)

    # Generate enough events to complete a window
    print("\nGenerating events over 70 seconds to complete a 1-minute window...")

    start_time = datetime.now(timezone.utc)

    for i in range(70):  # 70 seconds worth of events
        current_time = start_time + timedelta(seconds=i)

        event = {
            'timestamp': current_time,
            'strike': 21900.0,
            'option_type': 'C',
            'trade_price': 100.0 + i * 0.1,
            'trade_size': 10 + i,
            'bid_price': 99.5 + i * 0.1,
            'ask_price': 100.5 + i * 0.1
        }

        print(f"\rSending event {i+1}/70 at {current_time.strftime('%H:%M:%S')}", end='')

        metrics_list = engine.process_mbo_event(event)

        if metrics_list:
            print(f"\n✅ Metrics generated at event {i+1}!")
            for m in metrics_list:
                print(f"   - {m.window_duration}m window completed")

        time.sleep(0.1)  # Small delay

    print(f"\n\nResults:")
    print(f"Events processed: {engine.events_processed}")
    print(f"Metrics generated: {engine.metrics_generated}")
    print(f"Metrics received via callback: {len(metrics_received)}")

    # Check aggregator state
    stats = engine.get_engine_stats()
    print(f"\nAggregator state:")
    print(f"Active windows: {stats['aggregation']['active_windows']}")
    print(f"Windows completed: {stats['aggregation']['windows_completed']}")

def debug_integration_timing():
    """Debug timing issues in integration"""
    print("\n=== DEBUGGING INTEGRATION TIMING ===")

    from tasks.options_trading_system.analysis_engine.event_processor import create_standard_processor
    from tasks.options_trading_system.analysis_engine.pressure_aggregator import RealTimePressureEngine

    # Create with 1-minute window for faster testing
    processor = create_standard_processor()
    engine = RealTimePressureEngine(timeframes=[1])

    # Track flow
    events_sent = 0
    batches_processed = 0
    metrics_generated = 0

    def process_batch(batch):
        nonlocal batches_processed, metrics_generated
        batches_processed += 1
        print(f"\n📦 Processing batch {batches_processed} with {len(batch)} events")

        for event in batch:
            # Add required fields for pressure aggregator
            event['strike'] = 21900.0
            event['option_type'] = 'C'
            event['trade_price'] = 100.25
            event['trade_size'] = 20
            event['bid_price'] = 100.0
            event['ask_price'] = 100.5

            metrics = engine.process_mbo_event(event)
            if metrics:
                metrics_generated += len(metrics)
                print(f"   ✅ Generated {len(metrics)} metrics!")

    processor.register_batch_callback(process_batch)
    processor.start_processing()

    # Send events over time to complete windows
    print("\nSending events over 70 seconds...")
    start_time = datetime.now(timezone.utc)

    for i in range(70):
        current_time = start_time + timedelta(seconds=i)

        event = {
            'timestamp': current_time,
            'instrument_id': 12345,
            'bid_px_00': 100000000,
            'ask_px_00': 100500000,
            'size': 20
        }

        processor.process_event(event)
        events_sent += 1

        print(f"\rSent {events_sent} events, {batches_processed} batches, {metrics_generated} metrics", end='')
        time.sleep(0.1)

    # Final wait
    time.sleep(3)
    processor.stop_processing()

    print(f"\n\nFinal results:")
    print(f"Events sent: {events_sent}")
    print(f"Batches processed: {batches_processed}")
    print(f"Metrics generated: {metrics_generated}")

def debug_performance_bottleneck():
    """Find performance bottlenecks"""
    print("\n=== DEBUGGING PERFORMANCE ===")

    from tasks.options_trading_system.analysis_engine.event_processor import EventProcessor, EventFilter, BatchConfig

    # Create processor with minimal overhead
    filter_config = EventFilter(
        min_trade_size=1,  # No filtering
        market_hours_only=False,
        max_events_per_second=1000  # No rate limit
    )

    batch_config = BatchConfig(
        max_batch_size=50,  # Larger batches
        batch_timeout_ms=100,  # Faster timeout
        processing_threads=4  # More threads
    )

    processor = EventProcessor(filter_config, batch_config)

    # Simple batch counter
    batch_count = 0
    def count_batch(batch):
        nonlocal batch_count
        batch_count += 1

    processor.register_batch_callback(count_batch)
    processor.start_processing()

    # Rapid fire events
    print("Sending 1000 events as fast as possible...")
    start_time = time.time()

    for i in range(1000):
        event = {
            'timestamp': datetime.now(timezone.utc),
            'instrument_id': 12345,
            'bid_px_00': 100000000,
            'ask_px_00': 100500000,
            'size': 10
        }
        processor.process_event(event)

    # Wait for processing
    time.sleep(2)

    elapsed = time.time() - start_time
    stats = processor.get_performance_stats()

    print(f"\nPerformance results:")
    print(f"Time elapsed: {elapsed:.2f}s")
    print(f"Events processed: {stats['metrics']['events_processed']}")
    print(f"Throughput: {stats['metrics']['events_processed']/elapsed:.1f} events/sec")
    print(f"Batches created: {batch_count}")
    print(f"Avg batch size: {stats['batching']['avg_batch_size']:.1f}")

    processor.stop_processing()

def main():
    """Run all debug tests"""
    print("🔍 LIVE STREAMING DEBUG SUITE")
    print("=" * 60)

    debug_pressure_aggregator()
    debug_integration_timing()
    debug_performance_bottleneck()

    print("\n✅ Debug complete!")

if __name__ == "__main__":
    main()
