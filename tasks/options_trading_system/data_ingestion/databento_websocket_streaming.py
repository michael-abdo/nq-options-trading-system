#!/usr/bin/env python3
"""
Enhanced Databento WebSocket Streaming Implementation

This module provides real-time WebSocket streaming for MBO data from Databento,
implementing all missing requirements:
- Real-time WebSocket connection to GLBX.MDP3
- Market hours control (9:30 AM - 4:00 PM ET)
- Automatic reconnection with exponential backoff
- Parent symbol subscription for all strikes
"""

import os
import json
import logging
import threading
import time
import queue
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
import pytz

# Import backfill manager
try:
    from .websocket_backfill_manager import create_backfill_manager, BackfillManager
    BACKFILL_AVAILABLE = True
except ImportError:
    BACKFILL_AVAILABLE = False
    BackfillManager = None

# Try importing databento
try:
    import databento as db
    import pandas as pd
    DATABENTO_AVAILABLE = True
except ImportError:
    DATABENTO_AVAILABLE = False
    pd = None
    db = None
    print("Warning: Databento package not available. Install with: pip install databento")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketHoursController:
    """Controls streaming based on market hours (9:30 AM - 4:00 PM ET)"""

    def __init__(self):
        self.eastern_tz = pytz.timezone('America/New_York')
        self.market_open_time = (9, 30)  # 9:30 AM
        self.market_close_time = (16, 0)  # 4:00 PM
        self.check_interval = 60  # Check every minute

        self._market_open_callback = None
        self._market_close_callback = None
        self._monitoring = False
        self._monitor_thread = None

    def start_monitoring(self, on_market_open: Callable, on_market_close: Callable):
        """Start monitoring market hours"""
        self._market_open_callback = on_market_open
        self._market_close_callback = on_market_close
        self._monitoring = True

        self._monitor_thread = threading.Thread(
            target=self._monitor_market_hours,
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("Market hours monitoring started")

    def stop_monitoring(self):
        """Stop monitoring market hours"""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        logger.info("Market hours monitoring stopped")

    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        now_et = datetime.now(self.eastern_tz)

        # Check if weekday (Monday=0, Friday=4)
        if now_et.weekday() > 4:  # Weekend
            return False

        # Check time
        current_time = (now_et.hour, now_et.minute)
        return (self.market_open_time <= current_time < self.market_close_time)

    def get_next_market_open(self) -> datetime:
        """Get next market open time"""
        now_et = datetime.now(self.eastern_tz)

        # If it's before market open today
        if now_et.hour < self.market_open_time[0] or \
           (now_et.hour == self.market_open_time[0] and now_et.minute < self.market_open_time[1]):
            # Market opens today
            next_open = now_et.replace(
                hour=self.market_open_time[0],
                minute=self.market_open_time[1],
                second=0,
                microsecond=0
            )
        else:
            # Market opens next business day
            next_open = now_et + timedelta(days=1)
            next_open = next_open.replace(
                hour=self.market_open_time[0],
                minute=self.market_open_time[1],
                second=0,
                microsecond=0
            )

            # Skip weekends
            while next_open.weekday() > 4:
                next_open += timedelta(days=1)

        return next_open

    def _monitor_market_hours(self):
        """Monitor market hours and trigger callbacks"""
        was_open = False

        while self._monitoring:
            try:
                is_open = self.is_market_open()

                # Market just opened
                if is_open and not was_open:
                    logger.info("Market opened - starting streaming")
                    if self._market_open_callback:
                        self._market_open_callback()

                # Market just closed
                elif not is_open and was_open:
                    logger.info("Market closed - stopping streaming")
                    if self._market_close_callback:
                        self._market_close_callback()

                was_open = is_open

                # Log next market open if closed
                if not is_open:
                    next_open = self.get_next_market_open()
                    logger.debug(f"Market closed. Next open: {next_open}")

                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Market hours monitoring error: {e}")
                time.sleep(self.check_interval)


class EnhancedMBOStreamingClient:
    """
    Enhanced MBO streaming client with full WebSocket implementation

    Features:
    - Real-time WebSocket connection to GLBX.MDP3
    - Automatic reconnection with exponential backoff
    - Market hours control
    - Parent symbol subscription
    - Comprehensive error handling
    """

    def __init__(self, api_key: str, symbols: List[str] = None,
                 enable_backfill: bool = True, max_backfill_cost: float = 20.0):
        """
        Initialize enhanced MBO streaming client

        Args:
            api_key: Databento API key
            symbols: Base symbols to stream (e.g., ['NQ'])
            enable_backfill: Enable automatic backfill on reconnection
            max_backfill_cost: Maximum daily backfill cost
        """
        if not DATABENTO_AVAILABLE:
            raise ImportError("Databento package required. Install with: pip install databento")

        self.api_key = api_key
        self.base_symbols = symbols or ['NQ']
        # Convert to parent symbols for options
        self.parent_symbols = [f"{symbol}.OPT" for symbol in self.base_symbols]

        # Backfill manager
        self.backfill_manager = None
        if enable_backfill and BACKFILL_AVAILABLE:
            try:
                self.backfill_manager = create_backfill_manager(api_key, max_backfill_cost)
                self.backfill_manager.on_backfill_event = self._handle_backfill_event
                logger.info("Backfill manager enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize backfill manager: {e}")
                self.backfill_manager = None

        # Connection management
        self.client = None
        self.is_connected = False
        self.is_streaming = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.base_reconnect_delay = 5.0  # seconds

        # Event processing
        self.event_queue = queue.Queue(maxsize=50000)
        self.processing_thread = None
        self.should_stop = False

        # Market hours control
        self.market_hours_controller = MarketHoursController()
        self.enforce_market_hours = True

        # Callbacks
        self.on_mbo_event: Optional[Callable[[Dict], None]] = None
        self.on_connection_status: Optional[Callable[[bool], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

        # Statistics
        self.stats = {
            'connection_start': None,
            'events_received': 0,
            'events_processed': 0,
            'bytes_received': 0,
            'last_event_time': None,
            'errors': 0
        }

        logger.info(f"Enhanced MBO client initialized for symbols: {self.parent_symbols}")

    def start(self):
        """Start streaming with market hours control"""
        logger.info("Starting enhanced MBO streaming client")

        # Start processing thread
        self.should_stop = False
        self.processing_thread = threading.Thread(
            target=self._process_event_queue,
            daemon=True,
            name="MBO-EventProcessor"
        )
        self.processing_thread.start()

        if self.enforce_market_hours:
            # Start market hours monitoring
            self.market_hours_controller.start_monitoring(
                on_market_open=self._on_market_open,
                on_market_close=self._on_market_close
            )

            # Start streaming immediately if market is open
            if self.market_hours_controller.is_market_open():
                self._start_streaming()
            else:
                next_open = self.market_hours_controller.get_next_market_open()
                logger.info(f"Market closed. Will start streaming at: {next_open}")
        else:
            # Start streaming immediately
            self._start_streaming()

    def stop(self):
        """Stop streaming and cleanup"""
        logger.info("Stopping enhanced MBO streaming client")

        # Stop market hours monitoring
        if self.enforce_market_hours:
            self.market_hours_controller.stop_monitoring()

        # Stop streaming
        self._stop_streaming()

        # Stop processing thread
        self.should_stop = True
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)

        # Clear queue
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
            except:
                break

        logger.info(f"Streaming stopped. Stats: {self.get_stats()}")

    def _start_streaming(self):
        """Start the WebSocket streaming connection"""
        if self.is_streaming:
            logger.warning("Streaming already active")
            return

        streaming_thread = threading.Thread(
            target=self._streaming_loop,
            daemon=True,
            name="MBO-StreamingLoop"
        )
        streaming_thread.start()

    def _streaming_loop(self):
        """Main streaming loop with reconnection logic"""
        while not self.should_stop:
            try:
                logger.info(f"Connecting to Databento WebSocket (attempt {self.reconnect_attempts + 1})")

                # Create new client
                self.client = db.Live(key=self.api_key)

                # Set connection callbacks
                self.client.on_connect = self._on_connect
                self.client.on_disconnect = self._on_disconnect

                # Subscribe to parent symbols for all options
                self.client.subscribe(
                    dataset='GLBX.MDP3',      # CME Globex
                    schema='mbo',             # Market-by-order
                    symbols=self.parent_symbols,
                    stype_in='parent',        # Parent symbol subscription
                    start=datetime.now(timezone.utc)
                )

                self.is_streaming = True
                self.stats['connection_start'] = datetime.now(timezone.utc)

                # Process events
                for event in self.client:
                    if self.should_stop or not self.is_streaming:
                        break

                    self._handle_raw_event(event)

            except Exception as e:
                logger.error(f"Streaming error: {e}")
                self.stats['errors'] += 1

                if self.on_error:
                    self.on_error(str(e))

                # Handle reconnection
                if not self.should_stop and self.reconnect_attempts < self.max_reconnect_attempts:
                    self._schedule_reconnect()
                else:
                    logger.error("Max reconnection attempts reached or stop requested")
                    break

            finally:
                self._cleanup_connection()

    def _handle_raw_event(self, event):
        """Handle raw event from WebSocket"""
        try:
            self.stats['events_received'] += 1
            self.stats['last_event_time'] = datetime.now(timezone.utc)

            # Estimate event size
            event_size = len(str(event).encode('utf-8'))
            self.stats['bytes_received'] += event_size

            # Convert to dictionary format
            event_dict = self._convert_event_to_dict(event)

            # Track timestamp for backfill manager
            if self.backfill_manager and event_dict.get('ts_event'):
                event_timestamp = datetime.fromtimestamp(
                    event_dict['ts_event'] / 1e9, tz=timezone.utc
                )
                self.backfill_manager.track_event_timestamp(event_timestamp)

            # Add to processing queue
            if not self.event_queue.full():
                self.event_queue.put(event_dict)
            else:
                logger.warning("Event queue full, dropping event")

        except Exception as e:
            logger.error(f"Error handling raw event: {e}")
            self.stats['errors'] += 1

    def _convert_event_to_dict(self, event) -> Dict[str, Any]:
        """Convert Databento event to dictionary format"""
        # Extract all available fields from the event
        event_dict = {
            'event_type': 'mbo',
            'ts_event': getattr(event, 'ts_event', None),
            'ts_recv': getattr(event, 'ts_recv', None),
            'instrument_id': getattr(event, 'instrument_id', None),
            'symbol': getattr(event, 'symbol', None),
            'action': getattr(event, 'action', None),
            'side': getattr(event, 'side', None),
            'price': getattr(event, 'price', None),
            'size': getattr(event, 'size', None),
            'order_id': getattr(event, 'order_id', None),
            'flags': getattr(event, 'flags', None),
            'sequence': getattr(event, 'sequence', None),
            'order_priority': getattr(event, 'order_priority', None),
            'ts_in_delta': getattr(event, 'ts_in_delta', None)
        }

        # Add metadata
        event_dict['_received_at'] = datetime.now(timezone.utc).isoformat()
        event_dict['_source'] = 'databento_websocket'

        return event_dict

    def _process_event_queue(self):
        """Process events from queue in separate thread"""
        logger.info("Event processing thread started")

        while not self.should_stop:
            try:
                # Get event with timeout
                event_dict = self.event_queue.get(timeout=1.0)

                self.stats['events_processed'] += 1

                # Trigger callback
                if self.on_mbo_event:
                    self.on_mbo_event(event_dict)

                # Log progress periodically
                if self.stats['events_processed'] % 1000 == 0:
                    logger.info(f"Processed {self.stats['events_processed']} events, "
                              f"Queue size: {self.event_queue.qsize()}")

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                self.stats['errors'] += 1

        logger.info("Event processing thread stopped")

    def _on_connect(self):
        """Handle successful connection"""
        logger.info("WebSocket connected successfully")
        self.is_connected = True
        self.reconnect_attempts = 0

        # Initiate backfill if this is a reconnection
        if self.backfill_manager and self.stats.get('connection_start'):
            backfill_request = self.backfill_manager.on_reconnect(self.parent_symbols)
            if backfill_request:
                logger.info(f"Backfill initiated: {backfill_request.request_id}")

        if self.on_connection_status:
            self.on_connection_status(True)

    def _on_disconnect(self):
        """Handle disconnection"""
        logger.warning("WebSocket disconnected")
        self.is_connected = False

        # Notify backfill manager of disconnection
        if self.backfill_manager:
            self.backfill_manager.on_disconnect()

        if self.on_connection_status:
            self.on_connection_status(False)

    def _schedule_reconnect(self):
        """Schedule reconnection with exponential backoff"""
        self.reconnect_attempts += 1
        delay = min(
            self.base_reconnect_delay * (2 ** (self.reconnect_attempts - 1)),
            300  # Cap at 5 minutes
        )

        logger.info(f"Scheduling reconnection in {delay} seconds")
        time.sleep(delay)

    def _cleanup_connection(self):
        """Cleanup current connection"""
        self.is_streaming = False
        self.is_connected = False

        if self.client:
            try:
                self.client.stop()
            except:
                pass
            self.client = None

    def _on_market_open(self):
        """Handle market open"""
        logger.info("Market opened - starting streaming")
        self._start_streaming()

    def _on_market_close(self):
        """Handle market close"""
        logger.info("Market closed - stopping streaming")
        self._stop_streaming()

    def _stop_streaming(self):
        """Stop current streaming session"""
        self.is_streaming = False
        self._cleanup_connection()

    def _handle_backfill_event(self, event_dict: Dict[str, Any]):
        """Handle backfill event - add to processing queue"""
        try:
            # Add backfill event to processing queue
            if not self.event_queue.full():
                self.event_queue.put(event_dict)
                logger.debug(f"Added backfill event to queue: {event_dict.get('symbol')}")
            else:
                logger.warning("Event queue full during backfill, dropping event")
        except Exception as e:
            logger.error(f"Error handling backfill event: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        stats = self.stats.copy()

        # Calculate uptime
        if stats['connection_start'] and self.is_connected:
            uptime = datetime.now(timezone.utc) - stats['connection_start']
            stats['uptime_seconds'] = uptime.total_seconds()
        else:
            stats['uptime_seconds'] = 0

        # Calculate throughput
        if stats['uptime_seconds'] > 0:
            stats['events_per_second'] = stats['events_received'] / stats['uptime_seconds']
            stats['mbps'] = (stats['bytes_received'] * 8 / 1_000_000) / stats['uptime_seconds']
        else:
            stats['events_per_second'] = 0
            stats['mbps'] = 0

        stats['queue_size'] = self.event_queue.qsize()
        stats['is_connected'] = self.is_connected
        stats['is_streaming'] = self.is_streaming
        stats['market_open'] = self.market_hours_controller.is_market_open()

        # Add backfill statistics
        if self.backfill_manager:
            try:
                backfill_stats = self.backfill_manager.get_backfill_statistics()
                stats['backfill'] = backfill_stats
            except Exception as e:
                logger.warning(f"Failed to get backfill stats: {e}")
                stats['backfill'] = {'error': str(e)}
        else:
            stats['backfill'] = {'enabled': False}

        return stats


def create_enhanced_mbo_client(api_key: str, symbols: List[str] = None,
                              enable_backfill: bool = True,
                              max_backfill_cost: float = 20.0) -> EnhancedMBOStreamingClient:
    """
    Factory function to create enhanced MBO streaming client

    Args:
        api_key: Databento API key
        symbols: List of base symbols (e.g., ['NQ', 'ES'])
        enable_backfill: Enable automatic backfill on reconnection
        max_backfill_cost: Maximum daily backfill cost

    Returns:
        Configured EnhancedMBOStreamingClient instance
    """
    return EnhancedMBOStreamingClient(api_key, symbols, enable_backfill, max_backfill_cost)


if __name__ == "__main__":
    # Example usage
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv('DATABENTO_API_KEY')
    if not api_key:
        print("Please set DATABENTO_API_KEY environment variable")
        exit(1)

    # Create client
    client = create_enhanced_mbo_client(api_key, symbols=['NQ'])

    # Set up event handler
    def handle_mbo_event(event: Dict[str, Any]):
        print(f"MBO Event: {event.get('symbol')} - "
              f"Side: {event.get('side')}, "
              f"Price: {event.get('price')}, "
              f"Size: {event.get('size')}")

    client.on_mbo_event = handle_mbo_event

    # Start streaming
    try:
        client.start()

        # Run for a while
        print("Streaming MBO data... Press Ctrl+C to stop")
        while True:
            time.sleep(10)
            stats = client.get_stats()
            print(f"Stats: Events: {stats['events_received']}, "
                  f"Queue: {stats['queue_size']}, "
                  f"Connected: {stats['is_connected']}")

    except KeyboardInterrupt:
        print("\nStopping...")
        client.stop()
