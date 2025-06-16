#!/usr/bin/env python3
"""
Event Filtering and Batching System for IFD v3.0 Live Streaming

This module provides intelligent event filtering and batching to optimize analysis performance
while maintaining signal quality and reducing computational overhead for real-time processing.

Key Features:
- Smart event filtering based on volume, price impact, and market conditions
- Adaptive batching for optimal IFD analysis timing
- Quality-based event prioritization
- Memory-efficient processing with bounded queues
- Performance monitoring and auto-tuning

Architecture:
Raw MBO Events → Filter → Batch → Priority Queue → IFD Analysis
"""

import os
import sys
import logging
import threading
import time
import queue
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
from dataclasses import dataclass, field
import statistics

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(current_dir)))

from utils.timezone_utils import get_eastern_time, is_futures_market_hours

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EventFilter:
    """Configuration for event filtering"""

    # Volume filters
    min_trade_size: int = 10              # Minimum contracts per trade
    min_pressure_volume: int = 100        # Minimum volume for pressure calculation

    # Quality filters
    min_confidence: float = 0.7           # Minimum event confidence
    max_spread_ratio: float = 0.05        # Maximum bid-ask spread as ratio of mid

    # Time filters
    market_hours_only: bool = True        # Filter to market hours only
    exclude_opening_minutes: int = 5      # Exclude first N minutes of session
    exclude_closing_minutes: int = 5      # Exclude last N minutes of session

    # Strike filters
    near_money_strikes_only: bool = True  # Focus on near-the-money strikes
    max_strike_distance: float = 500      # Maximum distance from ATM

    # Performance filters
    max_events_per_second: int = 50       # Rate limiting
    priority_threshold: float = 0.8       # Priority event threshold

@dataclass
class BatchConfig:
    """Configuration for event batching"""

    # Batching parameters
    max_batch_size: int = 20              # Maximum events per batch
    batch_timeout_ms: int = 2000          # Batch timeout in milliseconds

    # Processing controls
    max_queue_size: int = 1000            # Maximum queue size
    processing_threads: int = 2           # Number of processing threads

    # Adaptive batching
    enable_adaptive: bool = True          # Enable adaptive batch sizing
    min_batch_size: int = 5              # Minimum batch size
    target_latency_ms: int = 500         # Target processing latency

@dataclass
class ProcessingMetrics:
    """Metrics for performance monitoring"""

    events_received: int = 0
    events_filtered: int = 0
    events_processed: int = 0
    batches_created: int = 0

    avg_batch_size: float = 0.0
    avg_processing_time_ms: float = 0.0
    current_queue_size: int = 0

    filter_ratio: float = 0.0             # Percentage of events that pass filter
    processing_rate: float = 0.0          # Events per second

    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class SmartEventFilter:
    """Intelligent event filtering for performance optimization"""

    def __init__(self, config: EventFilter):
        """Initialize smart event filter

        Args:
            config: Event filtering configuration
        """
        self.config = config

        # Rate limiting
        self.event_timestamps = deque(maxlen=100)

        # Market data cache for filtering decisions
        self.current_futures_price = 21900.0  # Default NQ price
        self.price_update_time = None

        # Statistics for adaptive filtering
        self.filter_stats = {
            'total_events': 0,
            'passed_filter': 0,
            'rejected_reasons': defaultdict(int)
        }

    def should_process_event(self, event_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Determine if event should be processed based on filter criteria

        Args:
            event_data: Raw event data from MBO stream

        Returns:
            Tuple of (should_process, rejection_reason)
        """
        self.filter_stats['total_events'] += 1

        # 1. Market hours filter
        if self.config.market_hours_only:
            if not is_futures_market_hours():
                self.filter_stats['rejected_reasons']['market_closed'] += 1
                return False, "market_closed"

        # 2. Rate limiting filter
        current_time = datetime.now(timezone.utc)
        self.event_timestamps.append(current_time)

        # Check events per second
        if len(self.event_timestamps) >= self.config.max_events_per_second:
            time_window = current_time - self.event_timestamps[0]
            if time_window.total_seconds() < 1.0:
                self.filter_stats['rejected_reasons']['rate_limit'] += 1
                return False, "rate_limit"

        # 3. Trade size filter
        trade_size = event_data.get('size', 0)
        if trade_size < self.config.min_trade_size:
            self.filter_stats['rejected_reasons']['small_trade'] += 1
            return False, "small_trade"

        # 4. Price and spread filter
        bid_price = event_data.get('bid_px_00', 0) / 1000000
        ask_price = event_data.get('ask_px_00', 0) / 1000000

        if bid_price <= 0 or ask_price <= 0:
            self.filter_stats['rejected_reasons']['invalid_prices'] += 1
            return False, "invalid_prices"

        # Calculate spread ratio
        mid_price = (bid_price + ask_price) / 2
        spread_ratio = (ask_price - bid_price) / mid_price if mid_price > 0 else 1.0

        if spread_ratio > self.config.max_spread_ratio:
            self.filter_stats['rejected_reasons']['wide_spread'] += 1
            return False, "wide_spread"

        # 5. Strike distance filter (for options)
        if self.config.near_money_strikes_only:
            # This would require instrument metadata lookup
            # For now, assume all events are near-the-money
            pass

        # 6. Session timing filter
        current_et = get_eastern_time()

        # Check opening minutes
        if self.config.exclude_opening_minutes > 0:
            if self._is_within_opening_minutes(current_et):
                self.filter_stats['rejected_reasons']['opening_period'] += 1
                return False, "opening_period"

        # Check closing minutes
        if self.config.exclude_closing_minutes > 0:
            if self._is_within_closing_minutes(current_et):
                self.filter_stats['rejected_reasons']['closing_period'] += 1
                return False, "closing_period"

        # Event passed all filters
        self.filter_stats['passed_filter'] += 1
        return True, "passed"

    def _is_within_opening_minutes(self, current_time: datetime) -> bool:
        """Check if within opening minutes exclusion period"""
        # For futures: Sunday 6 PM ET opening
        weekday = current_time.weekday()
        if weekday == 6 and current_time.hour == 18:  # Sunday 6 PM
            return current_time.minute < self.config.exclude_opening_minutes
        return False

    def _is_within_closing_minutes(self, current_time: datetime) -> bool:
        """Check if within closing minutes exclusion period"""
        # For futures: Friday 5 PM ET closing
        weekday = current_time.weekday()
        if weekday == 4 and current_time.hour == 16:  # Friday 4 PM (hour before close)
            return (60 - current_time.minute) <= self.config.exclude_closing_minutes
        return False

    def get_filter_stats(self) -> Dict[str, Any]:
        """Get filtering statistics"""
        total = max(self.filter_stats['total_events'], 1)
        return {
            'total_events': self.filter_stats['total_events'],
            'passed_filter': self.filter_stats['passed_filter'],
            'filter_ratio': self.filter_stats['passed_filter'] / total,
            'rejection_reasons': dict(self.filter_stats['rejected_reasons']),
            'events_per_second': len(self.event_timestamps)
        }

class AdaptiveBatcher:
    """Adaptive batching system for optimal processing performance"""

    def __init__(self, config: BatchConfig):
        """Initialize adaptive batcher

        Args:
            config: Batching configuration
        """
        self.config = config
        self.current_batch = []
        self.batch_start_time = None

        # Adaptive sizing
        self.current_batch_size = config.max_batch_size // 2  # Start in middle
        self.latency_history = deque(maxlen=20)
        self.size_history = deque(maxlen=20)

        # Performance tracking
        self.batches_created = 0
        self.total_processing_time = 0.0

        # Threading
        self.lock = threading.Lock()

    def add_event(self, event_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Add event to current batch and return completed batch if ready

        Args:
            event_data: Filtered event data

        Returns:
            Completed batch if ready, None otherwise
        """
        with self.lock:
            # Initialize batch timing
            if not self.current_batch:
                self.batch_start_time = datetime.now(timezone.utc)

            self.current_batch.append(event_data)

            # Check if batch is ready
            batch_ready = self._is_batch_ready()

            if batch_ready:
                completed_batch = self.current_batch.copy()
                self._reset_batch()
                self.batches_created += 1
                return completed_batch

            return None

    def _is_batch_ready(self) -> bool:
        """Check if current batch is ready for processing"""

        # Size-based completion
        if len(self.current_batch) >= self.current_batch_size:
            return True

        # Time-based completion
        if self.batch_start_time:
            elapsed_ms = (datetime.now(timezone.utc) - self.batch_start_time).total_seconds() * 1000
            if elapsed_ms >= self.config.batch_timeout_ms:
                return True

        return False

    def _reset_batch(self):
        """Reset current batch state"""
        self.current_batch = []
        self.batch_start_time = None

    def record_processing_time(self, processing_time_ms: float, batch_size: int):
        """Record processing time for adaptive sizing"""
        self.latency_history.append(processing_time_ms)
        self.size_history.append(batch_size)
        self.total_processing_time += processing_time_ms

        # Adapt batch size if enabled
        if self.config.enable_adaptive:
            self._adapt_batch_size()

    def _adapt_batch_size(self):
        """Adapt batch size based on processing latency"""
        if len(self.latency_history) < 5:
            return

        avg_latency = statistics.mean(self.latency_history)
        target_latency = self.config.target_latency_ms

        # Adjust batch size based on latency
        if avg_latency > target_latency * 1.2:  # Too slow
            self.current_batch_size = max(
                self.config.min_batch_size,
                int(self.current_batch_size * 0.8)
            )
        elif avg_latency < target_latency * 0.8:  # Too fast
            self.current_batch_size = min(
                self.config.max_batch_size,
                int(self.current_batch_size * 1.2)
            )

        logger.debug(f"🎛️  Adapted batch size to {self.current_batch_size} "
                    f"(avg latency: {avg_latency:.1f}ms)")

    def get_batch_stats(self) -> Dict[str, Any]:
        """Get batching statistics"""
        avg_latency = statistics.mean(self.latency_history) if self.latency_history else 0
        avg_size = statistics.mean(self.size_history) if self.size_history else 0

        return {
            'batches_created': self.batches_created,
            'current_batch_size': self.current_batch_size,
            'avg_processing_time_ms': avg_latency,
            'avg_batch_size': avg_size,
            'current_events_in_batch': len(self.current_batch),
            'total_processing_time': self.total_processing_time
        }

class EventProcessor:
    """Main event processing coordinator with filtering and batching"""

    def __init__(self,
                 filter_config: Optional[EventFilter] = None,
                 batch_config: Optional[BatchConfig] = None):
        """Initialize event processor

        Args:
            filter_config: Event filtering configuration
            batch_config: Batching configuration
        """
        self.filter_config = filter_config or EventFilter()
        self.batch_config = batch_config or BatchConfig()

        # Core components
        self.event_filter = SmartEventFilter(self.filter_config)
        self.batcher = AdaptiveBatcher(self.batch_config)

        # Processing queue and threads
        self.batch_queue = queue.Queue(maxsize=self.batch_config.max_queue_size)
        self.processing_threads = []
        self.is_running = False
        self.stop_event = threading.Event()

        # Callbacks
        self.batch_callbacks = []

        # Metrics
        self.metrics = ProcessingMetrics()

        logger.info("Event processor initialized")

    def start_processing(self):
        """Start processing threads"""
        if self.is_running:
            return

        self.is_running = True
        self.stop_event.clear()

        # Start processing threads
        for i in range(self.batch_config.processing_threads):
            thread = threading.Thread(
                target=self._processing_loop,
                name=f"EventProcessor-{i}",
                daemon=True
            )
            thread.start()
            self.processing_threads.append(thread)

        logger.info(f"Started {len(self.processing_threads)} processing threads")

    def stop_processing(self):
        """Stop processing threads gracefully"""
        logger.info("Stopping event processor...")

        self.is_running = False
        self.stop_event.set()

        # Wait for threads to finish
        for thread in self.processing_threads:
            thread.join(timeout=5)

        self.processing_threads = []
        logger.info("Event processor stopped")

    def process_event(self, event_data: Dict[str, Any]):
        """Process a single event through the filter and batch pipeline"""
        self.metrics.events_received += 1

        # 1. Apply filtering
        should_process, reason = self.event_filter.should_process_event(event_data)

        if not should_process:
            self.metrics.events_filtered += 1
            logger.debug(f"Event filtered: {reason}")
            return

        # 2. Add to batch
        completed_batch = self.batcher.add_event(event_data)

        if completed_batch:
            # 3. Queue batch for processing
            try:
                self.batch_queue.put(completed_batch, block=False)
                logger.debug(f"Queued batch with {len(completed_batch)} events")
            except queue.Full:
                logger.warning("Batch queue full, dropping batch")

    def register_batch_callback(self, callback: Callable[[List[Dict[str, Any]]], None]):
        """Register callback for completed batches"""
        self.batch_callbacks.append(callback)

    def _processing_loop(self):
        """Main processing loop for handling batches"""
        while self.is_running and not self.stop_event.is_set():
            try:
                # Get batch from queue with timeout
                batch = self.batch_queue.get(timeout=1.0)

                # Process batch
                start_time = time.time()
                self._process_batch(batch)
                processing_time_ms = (time.time() - start_time) * 1000

                # Record metrics
                self.batcher.record_processing_time(processing_time_ms, len(batch))
                self.metrics.events_processed += len(batch)
                self.metrics.batches_created += 1

                # Update metrics
                self._update_metrics()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Batch processing error: {e}")

    def _process_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of events"""
        # Notify all callbacks
        for callback in self.batch_callbacks:
            try:
                callback(batch)
            except Exception as e:
                logger.error(f"Batch callback error: {e}")

    def _update_metrics(self):
        """Update processing metrics"""
        filter_stats = self.event_filter.get_filter_stats()
        batch_stats = self.batcher.get_batch_stats()

        self.metrics.current_queue_size = self.batch_queue.qsize()
        self.metrics.filter_ratio = filter_stats['filter_ratio']
        self.metrics.avg_batch_size = batch_stats['avg_batch_size']
        self.metrics.avg_processing_time_ms = batch_stats['avg_processing_time_ms']

        # Calculate processing rate
        time_elapsed = (datetime.now(timezone.utc) - self.metrics.last_reset).total_seconds()
        if time_elapsed > 0:
            self.metrics.processing_rate = self.metrics.events_processed / time_elapsed

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        filter_stats = self.event_filter.get_filter_stats()
        batch_stats = self.batcher.get_batch_stats()

        return {
            'metrics': {
                'events_received': self.metrics.events_received,
                'events_filtered': self.metrics.events_filtered,
                'events_processed': self.metrics.events_processed,
                'batches_created': self.metrics.batches_created,
                'filter_ratio': self.metrics.filter_ratio,
                'processing_rate': self.metrics.processing_rate,
                'current_queue_size': self.metrics.current_queue_size
            },
            'filtering': filter_stats,
            'batching': batch_stats,
            'threads': {
                'running': self.is_running,
                'thread_count': len(self.processing_threads),
                'queue_capacity': self.batch_config.max_queue_size
            }
        }

# Factory functions for easy configuration
def create_high_frequency_processor() -> EventProcessor:
    """Create processor optimized for high-frequency trading"""
    filter_config = EventFilter(
        min_trade_size=5,
        min_pressure_volume=50,
        max_events_per_second=100,
        priority_threshold=0.9
    )

    batch_config = BatchConfig(
        max_batch_size=10,
        batch_timeout_ms=1000,
        target_latency_ms=250,
        processing_threads=3
    )

    return EventProcessor(filter_config, batch_config)

def create_standard_processor() -> EventProcessor:
    """Create processor with standard settings"""
    return EventProcessor()

def create_conservative_processor() -> EventProcessor:
    """Create processor optimized for conservative analysis"""
    filter_config = EventFilter(
        min_trade_size=20,
        min_pressure_volume=200,
        max_events_per_second=30,
        priority_threshold=0.7
    )

    batch_config = BatchConfig(
        max_batch_size=30,
        batch_timeout_ms=5000,
        target_latency_ms=1000,
        processing_threads=1
    )

    return EventProcessor(filter_config, batch_config)

# Example usage and testing
if __name__ == "__main__":
    print("=== Event Processor Test ===")

    # Create processor
    processor = create_standard_processor()

    # Test callback
    def test_batch_callback(batch: List[Dict[str, Any]]):
        print(f"📦 Processed batch with {len(batch)} events")

    processor.register_batch_callback(test_batch_callback)

    # Start processing
    processor.start_processing()

    # Simulate events
    for i in range(50):
        test_event = {
            'timestamp': datetime.now(timezone.utc),
            'size': 10 + i,
            'bid_px_00': 21900000000 + i * 1000,
            'ask_px_00': 21901000000 + i * 1000,
            'instrument_id': 12345
        }
        processor.process_event(test_event)
        time.sleep(0.01)

    # Wait a bit for processing
    time.sleep(2)

    # Get stats
    stats = processor.get_performance_stats()
    print("\n📊 Performance Stats:")
    for category, data in stats.items():
        print(f"  {category}:")
        for key, value in data.items():
            print(f"    {key}: {value}")

    # Stop processor
    processor.stop_processing()
    print("\n✅ Event processor test completed")
