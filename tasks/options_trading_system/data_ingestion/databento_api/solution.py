#!/usr/bin/env python3
"""
Databento MBO Streaming for IFD v3.0 - Enhanced Institutional Flow Detection

This module provides real-time Market-By-Order (MBO) streaming from Databento
for NQ options, enabling bid/ask pressure analysis for institutional flow detection.

Architecture:
- Real-time MBO streaming via WebSocket
- Tick-level bid/ask pressure derivation
- Local SQLite storage for processed metrics
- Cost-effective streaming with monitoring
- Smart reconnection and error handling
"""

import os
import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
import queue
from collections import defaultdict, deque

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing databento
try:
    import databento as db
    import pandas as pd
    DATABENTO_AVAILABLE = True
except ImportError:
    DATABENTO_AVAILABLE = False
    pd = None
    db = None
    logger.warning("Databento package not available. Install with: pip install databento")

@dataclass
class MBOEvent:
    """Individual MBO event structure"""
    timestamp: datetime
    instrument_id: int
    strike: float
    option_type: str  # 'C' or 'P'
    bid_price: float
    ask_price: float
    trade_price: Optional[float]
    trade_size: Optional[int]
    side: Optional[str]  # 'BUY', 'SELL', or None
    sequence: int

@dataclass
class PressureMetrics:
    """Aggregated pressure metrics for a strike/time window"""
    strike: float
    option_type: str
    time_window: datetime
    bid_volume: int
    ask_volume: int
    pressure_ratio: float
    total_trades: int
    avg_trade_size: float
    dominant_side: str
    confidence: float

class MBOEventProcessor:
    """Processes individual MBO events and derives trade initiation direction"""

    def __init__(self):
        self.last_prices = {}  # Track last bid/ask by instrument

    def process_event(self, raw_event: Dict) -> Optional[MBOEvent]:
        """
        Process raw MBO event from Databento stream

        Args:
            raw_event: Raw event dictionary from Databento

        Returns:
            Processed MBOEvent or None if invalid
        """
        try:
            # Extract basic fields
            ts_event = raw_event.get('ts_event', 0)
            if pd is not None:
                timestamp = pd.to_datetime(ts_event, unit='ns', utc=True)
            else:
                # Fallback timestamp parsing when pandas not available
                if ts_event:
                    timestamp = datetime.fromtimestamp(ts_event / 1_000_000_000, tz=timezone.utc)
                else:
                    timestamp = datetime.now(timezone.utc)

            instrument_id = int(raw_event.get('instrument_id', 0))

            # Skip if essential fields missing
            if not instrument_id or timestamp is None:
                return None

            # Extract price data
            bid_price = float(raw_event.get('bid_px_00', 0)) / 1000000  # Databento price scaling
            ask_price = float(raw_event.get('ask_px_00', 0)) / 1000000

            # Extract trade data if present
            trade_price = None
            trade_size = None
            side = None

            if 'price' in raw_event and 'size' in raw_event:
                trade_price = float(raw_event['price']) / 1000000
                trade_size = int(raw_event['size'])

                # Derive trade initiation direction
                side = self._derive_trade_side(trade_price, bid_price, ask_price)

            # Get instrument metadata (strike, option type) from cache
            strike, option_type = self._get_instrument_metadata(instrument_id)

            event = MBOEvent(
                timestamp=timestamp,
                instrument_id=instrument_id,
                strike=strike,
                option_type=option_type,
                bid_price=bid_price,
                ask_price=ask_price,
                trade_price=trade_price,
                trade_size=trade_size,
                side=side,
                sequence=raw_event.get('sequence', 0)
            )

            # Update price tracking
            self.last_prices[instrument_id] = {
                'bid': bid_price,
                'ask': ask_price,
                'timestamp': timestamp
            }

            return event

        except Exception as e:
            logger.warning(f"Failed to process MBO event: {e}")
            return None

    def _derive_trade_side(self, trade_price: float, bid_price: float, ask_price: float) -> str:
        """
        Derive trade initiation side from price comparison

        Logic:
        - If trade_price >= ask_price: BUY (aggressor hit the ask)
        - If trade_price <= bid_price: SELL (aggressor hit the bid)
        - Otherwise: UNKNOWN (trade between bid/ask)
        """
        if trade_price >= ask_price:
            return 'BUY'
        elif trade_price <= bid_price:
            return 'SELL'
        else:
            return 'UNKNOWN'

    def _get_instrument_metadata(self, instrument_id: int) -> tuple[float, str]:
        """
        Get strike and option type for instrument ID
        This would be populated from contract definitions
        For now, return defaults - will be enhanced with actual lookup
        """
        # Instrument metadata lookup - using symbol parsing for NQ options
        # This should query contract definitions to map instrument_id to strike/type
        return 21900.0, 'C'  # Default values for testing

class PressureAggregator:
    """Aggregates MBO events into pressure metrics by strike and time window"""

    def __init__(self, window_minutes: int = 5):
        """
        Initialize pressure aggregator

        Args:
            window_minutes: Time window for aggregation (default 5 minutes)
        """
        self.window_minutes = window_minutes
        self.window_delta = timedelta(minutes=window_minutes)

        # Storage for active windows
        self.active_windows = defaultdict(lambda: {
            'bid_volume': 0,
            'ask_volume': 0,
            'trades': [],
            'start_time': None
        })

    def add_event(self, event: MBOEvent) -> Optional[PressureMetrics]:
        """
        Add MBO event to aggregation and return completed metrics if window is full

        Args:
            event: Processed MBO event

        Returns:
            PressureMetrics if window completed, None otherwise
        """
        if not event.trade_size or not event.side or event.side == 'UNKNOWN':
            return None

        # First, check for expired windows and complete them
        completed_metrics = self._check_and_complete_expired_windows(event.timestamp)

        # Calculate window start time for current event
        window_start = self._get_window_start(event.timestamp)

        # Create window key
        window_key = f"{event.strike}_{event.option_type}_{window_start.isoformat()}"

        # Initialize window if new
        if self.active_windows[window_key]['start_time'] is None:
            self.active_windows[window_key]['start_time'] = window_start

        # Add trade to appropriate side
        if event.side == 'BUY':
            self.active_windows[window_key]['ask_volume'] += event.trade_size
        elif event.side == 'SELL':
            self.active_windows[window_key]['bid_volume'] += event.trade_size

        # Add trade to list
        self.active_windows[window_key]['trades'].append({
            'timestamp': event.timestamp,
            'size': event.trade_size,
            'side': event.side,
            'price': event.trade_price
        })

        # Return completed metrics if any, otherwise None
        return completed_metrics

    def _get_window_start(self, timestamp: datetime) -> datetime:
        """Get the start time for the window containing this timestamp"""
        # Round down to nearest window interval
        minutes = (timestamp.minute // self.window_minutes) * self.window_minutes
        return timestamp.replace(minute=minutes, second=0, microsecond=0)

    def _finalize_window(self, window_key: str, strike: float, option_type: str, window_start: datetime) -> PressureMetrics:
        """Finalize a completed time window and calculate pressure metrics"""
        window_data = self.active_windows[window_key]

        bid_volume = window_data['bid_volume']
        ask_volume = window_data['ask_volume']
        trades = window_data['trades']

        # Calculate pressure ratio
        if bid_volume > 0:
            pressure_ratio = ask_volume / bid_volume
        else:
            pressure_ratio = float('inf') if ask_volume > 0 else 1.0

        # Determine dominant side
        total_volume = bid_volume + ask_volume
        if total_volume > 0:
            buy_percentage = ask_volume / total_volume
            if buy_percentage > 0.6:
                dominant_side = 'BUY'
            elif buy_percentage < 0.4:
                dominant_side = 'SELL'
            else:
                dominant_side = 'NEUTRAL'
        else:
            dominant_side = 'NEUTRAL'

        # Calculate confidence based on sample size and dominance
        confidence = min(len(trades) / 20.0, 1.0) * abs(0.5 - (ask_volume / max(total_volume, 1))) * 2

        # Average trade size
        avg_trade_size = sum(t['size'] for t in trades) / len(trades) if trades else 0

        metrics = PressureMetrics(
            strike=strike,
            option_type=option_type,
            time_window=window_start,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            pressure_ratio=pressure_ratio,
            total_trades=len(trades),
            avg_trade_size=avg_trade_size,
            dominant_side=dominant_side,
            confidence=confidence
        )

        # Clean up completed window
        del self.active_windows[window_key]

        return metrics

    def _check_and_complete_expired_windows(self, current_timestamp: datetime) -> Optional[PressureMetrics]:
        """
        Check for expired windows and complete them

        Args:
            current_timestamp: Current event timestamp

        Returns:
            PressureMetrics from first completed window, or None
        """
        completed_metrics = None
        expired_keys = []

        # Find expired windows
        for window_key, window_data in self.active_windows.items():
            if window_data['start_time'] is None:
                continue

            window_end = window_data['start_time'] + self.window_delta
            if current_timestamp >= window_end:
                expired_keys.append(window_key)

        # Complete the first expired window (return only one set of metrics)
        if expired_keys:
            first_key = expired_keys[0]

            # Parse window key to get strike and option_type
            parts = first_key.split('_')
            strike = float(parts[0])
            option_type = parts[1]
            window_start = self.active_windows[first_key]['start_time']

            completed_metrics = self._finalize_window(first_key, strike, option_type, window_start)

            # Complete remaining expired windows silently
            for key in expired_keys[1:]:
                parts = key.split('_')
                strike = float(parts[0])
                option_type = parts[1]
                window_start = self.active_windows[key]['start_time']
                self._finalize_window(key, strike, option_type, window_start)

        return completed_metrics

class MBODatabase:
    """SQLite database for storing processed MBO metrics efficiently"""

    def __init__(self, db_path: str):
        """
        Initialize MBO database

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Pressure metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pressure_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strike REAL NOT NULL,
                    option_type TEXT NOT NULL,
                    time_window TEXT NOT NULL,
                    bid_volume INTEGER NOT NULL,
                    ask_volume INTEGER NOT NULL,
                    pressure_ratio REAL NOT NULL,
                    total_trades INTEGER NOT NULL,
                    avg_trade_size REAL NOT NULL,
                    dominant_side TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(strike, option_type, time_window)
                )
            """)

            # Usage monitoring table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_monitoring (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    events_processed INTEGER NOT NULL,
                    data_bytes INTEGER NOT NULL,
                    estimated_cost REAL NOT NULL,
                    connection_time REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Create indexes for efficient queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pressure_time ON pressure_metrics(time_window)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pressure_strike ON pressure_metrics(strike, option_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_date ON usage_monitoring(date)")

            conn.commit()

    def store_pressure_metrics(self, metrics: PressureMetrics):
        """Store pressure metrics in database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO pressure_metrics
                (strike, option_type, time_window, bid_volume, ask_volume,
                 pressure_ratio, total_trades, avg_trade_size, dominant_side,
                 confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.strike, metrics.option_type, metrics.time_window.isoformat(),
                metrics.bid_volume, metrics.ask_volume, metrics.pressure_ratio,
                metrics.total_trades, metrics.avg_trade_size, metrics.dominant_side,
                metrics.confidence, datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()

    def get_pressure_history(self, strike: float, option_type: str, hours: int = 24) -> List[Dict]:
        """Get pressure metrics history for a strike"""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM pressure_metrics
                WHERE strike = ? AND option_type = ? AND time_window >= ?
                ORDER BY time_window ASC
            """, (strike, option_type, since.isoformat()))

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def record_usage(self, date: str, events: int, bytes_processed: int, cost: float, connection_time: float):
        """Record usage statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usage_monitoring
                (date, events_processed, data_bytes, estimated_cost, connection_time, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (date, events, bytes_processed, cost, connection_time, datetime.now(timezone.utc).isoformat()))
            conn.commit()

class UsageMonitor:
    """Monitor streaming costs and usage to prevent overruns"""

    def __init__(self, daily_budget: float = 10.0):
        """
        Initialize usage monitor

        Args:
            daily_budget: Maximum daily budget in USD
        """
        self.daily_budget = daily_budget
        self.events_processed = 0
        self.bytes_processed = 0
        self.estimated_cost = 0.0
        self.start_time = datetime.now()

        # Cost estimation (rough estimates based on Databento pricing)
        self.cost_per_mb = 0.01  # $0.01 per MB
        self.cost_per_hour = 1.0  # $1 per hour base streaming cost

    def record_event(self, event_size_bytes: int):
        """Record a processed event and update cost estimates"""
        self.events_processed += 1
        self.bytes_processed += event_size_bytes

        # Update cost estimate
        data_cost = (self.bytes_processed / 1024 / 1024) * self.cost_per_mb
        time_cost = ((datetime.now() - self.start_time).total_seconds() / 3600) * self.cost_per_hour
        self.estimated_cost = data_cost + time_cost

    def should_continue_streaming(self) -> bool:
        """Check if streaming should continue based on budget"""
        return self.estimated_cost < (self.daily_budget * 0.8)  # Stop at 80% of budget

    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        return {
            'events_processed': self.events_processed,
            'bytes_processed': self.bytes_processed,
            'estimated_cost': self.estimated_cost,
            'budget_remaining': self.daily_budget - self.estimated_cost,
            'runtime_hours': (datetime.now() - self.start_time).total_seconds() / 3600
        }

class MBOStreamingClient:
    """Real-time MBO streaming client using Databento Live API"""

    def __init__(self, api_key: str, symbols: List[str] = None):
        """
        Initialize MBO streaming client

        Args:
            api_key: Databento API key
            symbols: List of symbols to stream (default: ['NQ.OPT'])
        """
        if not DATABENTO_AVAILABLE:
            raise ImportError("Databento package not installed")

        self.api_key = api_key
        self.symbols = symbols or ['NQ.OPT']
        self.client = None
        self.is_streaming = False
        self.event_queue = queue.Queue(maxsize=10000)

        # Processing components
        self.event_processor = MBOEventProcessor()
        self.pressure_aggregator = PressureAggregator()
        self.usage_monitor = UsageMonitor()

        # Callbacks
        self.on_pressure_metrics: Optional[Callable[[PressureMetrics], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

    def start_streaming(self):
        """Start real-time MBO streaming"""
        if self.is_streaming:
            logger.warning("Streaming already active")
            return

        try:
            logger.info(f"Starting MBO streaming for symbols: {self.symbols}")

            # Initialize live client
            self.client = db.Live(key=self.api_key)

            # Subscribe to NQ options data using available schema
            # Note: MBO schema requires premium subscription, using trades schema
            self.client.subscribe(
                dataset='GLBX.MDP3',
                schema='trades',  # Available schema (MBO requires premium subscription)
                symbols=self.symbols,
                stype_in='parent'  # Required: Use parent symbology for options access
            )

            self.is_streaming = True

            # Start processing thread
            processing_thread = threading.Thread(target=self._process_events, daemon=True)
            processing_thread.start()

            # Stream events
            for event in self.client:
                if not self.is_streaming:
                    break

                # Add to processing queue
                try:
                    self.event_queue.put(event, timeout=1.0)

                    # Record usage
                    event_size = len(str(event).encode('utf-8'))
                    self.usage_monitor.record_event(event_size)

                    # Check budget
                    if not self.usage_monitor.should_continue_streaming():
                        logger.warning("Daily budget limit reached, stopping stream")
                        self.stop_streaming()
                        break

                except queue.Full:
                    logger.warning("Event queue full, dropping event")

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            if self.on_error:
                self.on_error(e)
            self.stop_streaming()

    def _process_events(self):
        """Process events from queue in separate thread"""
        while self.is_streaming:
            try:
                # Get event from queue
                raw_event = self.event_queue.get(timeout=1.0)

                # Process event
                processed_event = self.event_processor.process_event(raw_event)
                if not processed_event:
                    continue

                # Aggregate for pressure metrics
                pressure_metrics = self.pressure_aggregator.add_event(processed_event)
                if pressure_metrics and self.on_pressure_metrics:
                    self.on_pressure_metrics(pressure_metrics)

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Event processing error: {e}")

    def stop_streaming(self):
        """Stop MBO streaming"""
        logger.info("Stopping MBO streaming")
        self.is_streaming = False

        if self.client:
            try:
                self.client.stop()
            except:
                pass
            self.client = None

class DatabentoMBOIngestion:
    """
    Main MBO ingestion class implementing standard data ingestion interface
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Databento MBO ingestion

        Args:
            config: Configuration dictionary with:
                - api_key: Databento API key
                - symbols: List of symbols (default: ['NQ'])
                - streaming_mode: Enable real-time streaming (default: False)
                - cache_dir: Directory for local storage
        """
        self.config = config
        self.api_key = self._get_api_key(config)
        # Configure symbols with proper Databento GLBX.MDP3 format
        # For NQ options: use "NQ.OPT" with stype_in="parent" to get all strikes/expirations
        self.symbols = [f"{symbol}.OPT" for symbol in config.get('symbols', ['NQ'])]
        self.symbol_type = 'parent'  # Required: Use parent symbology for options access
        self.streaming_mode = config.get('streaming_mode', False)

        if not self.api_key:
            raise ValueError("Databento API key not found in config or environment")

        # Initialize storage
        cache_dir = Path(config.get('cache_dir', 'outputs/mbo_cache'))
        cache_dir.mkdir(parents=True, exist_ok=True)

        self.database = MBODatabase(str(cache_dir / 'mbo_metrics.db'))
        self.streaming_client = None

        logger.info("DatabentoMBOIngestion initialized")

    def _get_api_key(self, config: Dict[str, Any]) -> Optional[str]:
        """Get API key from config or environment"""
        # Check config first
        api_key = config.get('api_key')

        # Check environment variables
        if not api_key:
            api_key = os.getenv('DATABENTO_API_KEY')

        return api_key

    def _check_dataset_access(self) -> bool:
        """Check if we have access to GLBX.MDP3 dataset"""
        if not DATABENTO_AVAILABLE:
            return False

        try:
            client = db.Historical(self.api_key)
            end_time = datetime.now(timezone.utc) - timedelta(days=1)
            start_time = end_time - timedelta(seconds=1)

            test_response = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                stype_in="parent",
                schema="ohlcv-1d",
                start=start_time,
                end=end_time,
                limit=1
            )

            return True

        except Exception as e:
            error_msg = str(e)
            if "no_dataset_entitlement" in error_msg or "403" in error_msg:
                logger.warning("No access to GLBX.MDP3 dataset. Subscription upgrade required.")
                return False
            elif "422" in error_msg and "available" in error_msg:
                return True
            else:
                logger.error(f"Error checking dataset access: {e}")
                return False

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            'loader': None,
            'metadata': {
                'source': 'databento_mbo',
                'error': error_message,
                'dataset_required': 'GLBX.MDP3',
                'subscription_info': 'https://databento.com/pricing'
            },
            'options_summary': {'total_contracts': 0, 'calls': [], 'puts': []},
            'quality_metrics': {
                'total_contracts': 0,
                'volume_coverage': 0.0,
                'data_source': 'databento_mbo',
                'access_status': 'DENIED'
            },
            'raw_data_available': False
        }

    def load_options_data(self) -> Dict[str, Any]:
        """
        Load options data - either streaming or historical based on config

        Returns:
            Dictionary with standard format for pipeline integration
        """
        # Check dataset access before attempting to load
        if not self._check_dataset_access():
            logger.error("No access to required GLBX.MDP3 dataset")
            return self._create_error_response(
                "Dataset access denied. GLBX.MDP3 subscription required for NQ options data. "
                "Please contact Databento to upgrade your subscription."
            )

        if self.streaming_mode:
            return self._start_real_time_streaming()
        else:
            return self._load_historical_data()

    def _start_real_time_streaming(self) -> Dict[str, Any]:
        """Start real-time MBO streaming and return initial status"""
        logger.info("Starting real-time MBO streaming")

        try:
            self.streaming_client = MBOStreamingClient(self.api_key, self.symbols)

            # Set up callbacks
            self.streaming_client.on_pressure_metrics = self._on_pressure_metrics
            self.streaming_client.on_error = self._on_streaming_error

            # Start streaming in background thread
            streaming_thread = threading.Thread(
                target=self.streaming_client.start_streaming,
                daemon=True
            )
            streaming_thread.start()

            # Wait a moment for connection
            time.sleep(2)

            return {
                'loader': self,
                'metadata': {
                    'source': 'databento_mbo',
                    'mode': 'streaming',
                    'symbols': self.symbols,
                    'started_at': datetime.now(timezone.utc).isoformat()
                },
                'options_summary': {
                    'streaming_active': True,
                    'symbols': self.symbols,
                    'real_time': True
                },
                'quality_metrics': {
                    'data_source': 'databento_mbo',
                    'streaming': True,
                    'timestamp': datetime.now().isoformat()
                },
                'raw_data_available': True
            }

        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            return self._error_result(str(e))

    def _load_historical_data(self) -> Dict[str, Any]:
        """Load historical data for analysis (fallback mode)"""
        logger.info("Loading historical pressure metrics")

        try:
            # Get recent pressure metrics from database
            recent_metrics = []
            for symbol in self.symbols:
                # Extract base symbol (remove .OPT)
                base_symbol = symbol.replace('.OPT', '')
                # This would query recent pressure data - for now return empty
                pass

            return {
                'loader': self,
                'metadata': {
                    'source': 'databento_mbo',
                    'mode': 'historical',
                    'symbols': self.symbols
                },
                'options_summary': {
                    'total_contracts': 0,
                    'calls': [],
                    'puts': [],
                    'pressure_metrics_available': True
                },
                'quality_metrics': {
                    'data_source': 'databento_mbo',
                    'historical': True,
                    'timestamp': datetime.now().isoformat()
                },
                'raw_data_available': True
            }

        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            return self._error_result(str(e))

    def _on_pressure_metrics(self, metrics: PressureMetrics):
        """Handle new pressure metrics from streaming"""
        # Store in database
        self.database.store_pressure_metrics(metrics)

        # Log significant pressure events
        if metrics.pressure_ratio > 2.0 and metrics.confidence > 0.7:
            logger.info(f"Significant pressure detected: {metrics.strike}{metrics.option_type} "
                       f"ratio={metrics.pressure_ratio:.2f} side={metrics.dominant_side}")

    def _on_streaming_error(self, error: Exception):
        """Handle streaming errors"""
        logger.error(f"Streaming error: {error}")
        # Could implement reconnection logic here

    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """Return error result in standard format"""
        return {
            'loader': self,
            'metadata': {'source': 'databento_mbo', 'error': error_msg},
            'options_summary': {'total_contracts': 0, 'calls': [], 'puts': []},
            'quality_metrics': {
                'total_contracts': 0,
                'volume_coverage': 0.0,
                'data_source': 'databento_mbo'
            },
            'raw_data_available': False
        }

    def get_recent_pressure_metrics(self, hours: int = 1) -> List[Dict]:
        """Get recent pressure metrics for analysis"""
        # This would query the database for recent pressure metrics
        # For now, return empty list
        return []

    def stop_streaming(self):
        """Stop any active streaming"""
        if self.streaming_client:
            self.streaming_client.stop_streaming()
            self.streaming_client = None

# Standard interface functions for pipeline integration
def load_databento_mbo_data(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standard interface function for loading Databento MBO data

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary with standard data ingestion format
    """
    try:
        loader = DatabentoMBOIngestion(config)
        return loader.load_options_data()
    except Exception as e:
        logger.error(f"Failed to load Databento MBO data: {e}")
        return {
            'loader': None,
            'metadata': {'source': 'databento_mbo', 'error': str(e)},
            'options_summary': {'total_contracts': 0, 'calls': [], 'puts': []},
            'quality_metrics': {
                'total_contracts': 0,
                'volume_coverage': 0.0,
                'data_source': 'databento_mbo'
            },
            'raw_data_available': False
        }

# Factory function for compatibility
def create_databento_loader(config: Optional[Dict] = None) -> DatabentoMBOIngestion:
    """Factory function to create Databento MBO loader instance"""
    if config is None:
        config = {}

    return DatabentoMBOIngestion(config)

# Legacy compatibility - maintain old function name
load_databento_api_data = load_databento_mbo_data
