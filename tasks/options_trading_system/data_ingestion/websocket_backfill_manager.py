#!/usr/bin/env python3
"""
WebSocket Backfill Manager for IFD v3.0

This module enhances the WebSocket streaming with automatic backfill capabilities:
- Tracks last received timestamp
- Automatically backfills missing data on reconnection
- Cost tracking for backfill operations
- Seamless integration with real-time stream
"""

import os
import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import deque
import queue

# Try importing databento
try:
    import databento as db
    DATABENTO_AVAILABLE = True
except ImportError:
    DATABENTO_AVAILABLE = False
    db = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BackfillRequest:
    """Backfill request details"""
    request_id: str
    start_time: datetime
    end_time: datetime
    symbols: List[str]

    # Status
    status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    initiated_at: datetime = None
    completed_at: datetime = None

    # Results
    events_retrieved: int = 0
    cost_estimate: float = 0.0
    actual_cost: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class ConnectionGap:
    """Connection gap that needs backfilling"""
    gap_id: str
    disconnect_time: datetime
    reconnect_time: datetime
    last_event_timestamp: datetime

    # Gap analysis
    gap_duration_seconds: float = 0.0
    estimated_missed_events: int = 0
    backfill_required: bool = True

    def __post_init__(self):
        self.gap_duration_seconds = (self.reconnect_time - self.disconnect_time).total_seconds()
        # Estimate missed events based on typical volume
        self.estimated_missed_events = int(self.gap_duration_seconds * 10)  # ~10 events/second estimate


class BackfillDatabase:
    """Database for tracking backfill operations"""

    def __init__(self, db_path: str = "outputs/backfill_tracking.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Connection gaps table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connection_gaps (
                    gap_id TEXT PRIMARY KEY,
                    disconnect_time TEXT NOT NULL,
                    reconnect_time TEXT NOT NULL,
                    last_event_timestamp TEXT NOT NULL,
                    gap_duration_seconds REAL NOT NULL,
                    estimated_missed_events INTEGER,
                    backfill_required BOOLEAN DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Backfill requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backfill_requests (
                    request_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    symbols TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING',
                    initiated_at TEXT,
                    completed_at TEXT,
                    events_retrieved INTEGER DEFAULT 0,
                    cost_estimate REAL DEFAULT 0.0,
                    actual_cost REAL,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Backfill events table (for deduplication)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backfill_events (
                    event_id TEXT PRIMARY KEY,
                    request_id TEXT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    processed BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (request_id) REFERENCES backfill_requests (request_id)
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_gaps_time ON connection_gaps(disconnect_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON backfill_requests(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON backfill_events(timestamp)")

            conn.commit()

    def record_connection_gap(self, gap: ConnectionGap):
        """Record a connection gap"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO connection_gaps
                (gap_id, disconnect_time, reconnect_time, last_event_timestamp,
                 gap_duration_seconds, estimated_missed_events, backfill_required)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                gap.gap_id,
                gap.disconnect_time.isoformat(),
                gap.reconnect_time.isoformat(),
                gap.last_event_timestamp.isoformat(),
                gap.gap_duration_seconds,
                gap.estimated_missed_events,
                gap.backfill_required
            ))

            conn.commit()

    def record_backfill_request(self, request: BackfillRequest):
        """Record backfill request"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO backfill_requests
                (request_id, start_time, end_time, symbols, status, initiated_at,
                 completed_at, events_retrieved, cost_estimate, actual_cost, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.request_id,
                request.start_time.isoformat(),
                request.end_time.isoformat(),
                json.dumps(request.symbols),
                request.status,
                request.initiated_at.isoformat() if request.initiated_at else None,
                request.completed_at.isoformat() if request.completed_at else None,
                request.events_retrieved,
                request.cost_estimate,
                request.actual_cost,
                request.error_message
            ))

            conn.commit()


class BackfillManager:
    """
    Manages automatic backfill of missing data during connection gaps

    Features:
    - Automatic gap detection
    - Historical data retrieval via Databento API
    - Cost-aware backfill operations
    - Deduplication of overlapping data
    """

    def __init__(self, api_key: str, max_backfill_cost: float = 20.0):
        """
        Initialize backfill manager

        Args:
            api_key: Databento API key
            max_backfill_cost: Maximum cost for backfill operations per day
        """
        if not DATABENTO_AVAILABLE:
            raise ImportError("Databento package required for backfill operations")

        self.api_key = api_key
        self.max_backfill_cost = max_backfill_cost
        self.database = BackfillDatabase()

        # Tracking
        self.last_event_timestamp: Optional[datetime] = None
        self.disconnect_time: Optional[datetime] = None
        self.daily_backfill_cost = 0.0
        self.backfill_requests: deque = deque(maxlen=100)

        # Callbacks
        self.on_backfill_event: Optional[Callable[[Dict], None]] = None
        self.on_backfill_complete: Optional[Callable[[BackfillRequest], None]] = None

        # Cost estimation (rough Databento pricing)
        self.cost_per_request = 0.01
        self.cost_per_gb = 10.0

        logger.info(f"Backfill manager initialized with ${max_backfill_cost} daily budget")

    def track_event_timestamp(self, event_timestamp: datetime):
        """Track the timestamp of the last received event"""
        self.last_event_timestamp = event_timestamp

    def on_disconnect(self):
        """Handle disconnection - record disconnect time"""
        self.disconnect_time = datetime.now(timezone.utc)
        logger.warning(f"Connection lost at {self.disconnect_time}")

    def on_reconnect(self, symbols: List[str]) -> Optional[BackfillRequest]:
        """
        Handle reconnection - initiate backfill if needed

        Args:
            symbols: Symbols to backfill

        Returns:
            BackfillRequest if backfill was initiated
        """
        reconnect_time = datetime.now(timezone.utc)

        if not self.disconnect_time or not self.last_event_timestamp:
            logger.info("No backfill needed - no previous disconnect or event data")
            return None

        # Create connection gap record
        gap_id = f"gap_{self.disconnect_time.strftime('%Y%m%d_%H%M%S')}"
        gap = ConnectionGap(
            gap_id=gap_id,
            disconnect_time=self.disconnect_time,
            reconnect_time=reconnect_time,
            last_event_timestamp=self.last_event_timestamp
        )

        self.database.record_connection_gap(gap)

        # Check if backfill is needed (gap > 30 seconds)
        if gap.gap_duration_seconds < 30:
            logger.info(f"Gap too small ({gap.gap_duration_seconds:.1f}s) - skipping backfill")
            gap.backfill_required = False
            self.database.record_connection_gap(gap)
            return None

        # Check daily cost budget
        if self.daily_backfill_cost >= self.max_backfill_cost:
            logger.warning(f"Daily backfill budget exhausted: ${self.daily_backfill_cost:.2f}")
            gap.backfill_required = False
            self.database.record_connection_gap(gap)
            return None

        # Initiate backfill
        logger.info(f"Initiating backfill for {gap.gap_duration_seconds:.1f}s gap")

        backfill_request = BackfillRequest(
            request_id=f"backfill_{gap_id}",
            start_time=self.last_event_timestamp,
            end_time=self.disconnect_time,
            symbols=symbols,
            initiated_at=reconnect_time
        )

        # Start backfill in background thread
        backfill_thread = threading.Thread(
            target=self._execute_backfill,
            args=(backfill_request,),
            daemon=True,
            name="BackfillThread"
        )
        backfill_thread.start()

        # Reset disconnect tracking
        self.disconnect_time = None

        return backfill_request

    def _execute_backfill(self, request: BackfillRequest):
        """Execute backfill request"""
        try:
            request.status = "IN_PROGRESS"
            self.database.record_backfill_request(request)

            # Estimate cost
            duration_hours = (request.end_time - request.start_time).total_seconds() / 3600
            estimated_data_size_gb = duration_hours * 0.1  # Rough estimate
            request.cost_estimate = self.cost_per_request + (estimated_data_size_gb * self.cost_per_gb)

            # Check if cost is acceptable
            if request.cost_estimate > (self.max_backfill_cost - self.daily_backfill_cost):
                raise Exception(f"Backfill cost (${request.cost_estimate:.2f}) exceeds remaining budget")

            logger.info(f"Starting backfill: {request.start_time} to {request.end_time}, "
                       f"estimated cost: ${request.cost_estimate:.2f}")

            # Create historical client
            historical_client = db.Historical(key=self.api_key)

            # Request historical data
            data = historical_client.timeseries.get_range(
                dataset='GLBX.MDP3',
                symbols=request.symbols,
                schema='mbo',
                start=request.start_time,
                end=request.end_time,
                stype_in='parent'
            )

            # Process backfill data
            events_processed = 0
            for event in data:
                # Create event dictionary
                event_dict = self._convert_historical_event(event)

                # Check for duplicates
                event_id = f"{event_dict.get('instrument_id')}_{event_dict.get('ts_event')}"
                if not self._is_duplicate_event(event_id, request.request_id):
                    # Send to callback
                    if self.on_backfill_event:
                        event_dict['_backfill'] = True  # Mark as backfill data
                        self.on_backfill_event(event_dict)

                    events_processed += 1

                    # Record event for deduplication
                    self._record_backfill_event(event_id, request.request_id, event_dict)

            # Complete request
            request.status = "COMPLETED"
            request.completed_at = datetime.now(timezone.utc)
            request.events_retrieved = events_processed
            request.actual_cost = request.cost_estimate  # Simplified - would use actual billing

            self.daily_backfill_cost += request.actual_cost

            logger.info(f"Backfill completed: {events_processed} events, cost: ${request.actual_cost:.2f}")

            if self.on_backfill_complete:
                self.on_backfill_complete(request)

        except Exception as e:
            request.status = "FAILED"
            request.error_message = str(e)
            request.completed_at = datetime.now(timezone.utc)

            logger.error(f"Backfill failed: {e}")

        finally:
            self.database.record_backfill_request(request)
            self.backfill_requests.append(request)

    def _convert_historical_event(self, event) -> Dict[str, Any]:
        """Convert historical event to dictionary format"""
        # Similar to WebSocket conversion
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
            '_source': 'databento_backfill',
            '_backfill_timestamp': datetime.now(timezone.utc).isoformat()
        }

        return event_dict

    def _is_duplicate_event(self, event_id: str, request_id: str) -> bool:
        """Check if event is duplicate"""
        with sqlite3.connect(self.database.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) FROM backfill_events
                WHERE event_id = ?
            """, (event_id,))

            count = cursor.fetchone()[0]
            return count > 0

    def _record_backfill_event(self, event_id: str, request_id: str, event_dict: Dict):
        """Record backfill event for deduplication"""
        with sqlite3.connect(self.database.db_path) as conn:
            cursor = conn.cursor()

            timestamp = event_dict.get('ts_event')
            if timestamp:
                timestamp = datetime.fromtimestamp(timestamp / 1e9, tz=timezone.utc).isoformat()
            else:
                timestamp = datetime.now(timezone.utc).isoformat()

            cursor.execute("""
                INSERT OR IGNORE INTO backfill_events
                (event_id, request_id, timestamp, symbol, event_type)
                VALUES (?, ?, ?, ?, ?)
            """, (
                event_id,
                request_id,
                timestamp,
                event_dict.get('symbol', ''),
                event_dict.get('action', '')
            ))

            conn.commit()

    def get_backfill_statistics(self) -> Dict[str, Any]:
        """Get backfill operation statistics"""
        # Get recent requests
        recent_requests = list(self.backfill_requests)

        # Calculate stats
        total_requests = len(recent_requests)
        completed_requests = [r for r in recent_requests if r.status == "COMPLETED"]
        failed_requests = [r for r in recent_requests if r.status == "FAILED"]

        total_events = sum(r.events_retrieved for r in completed_requests)
        total_cost = sum(r.actual_cost for r in completed_requests if r.actual_cost)

        success_rate = len(completed_requests) / total_requests if total_requests > 0 else 0

        # Gap analysis
        with sqlite3.connect(self.database.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*), AVG(gap_duration_seconds), SUM(estimated_missed_events)
                FROM connection_gaps
                WHERE date(disconnect_time) = date('now')
            """)

            gap_stats = cursor.fetchone()
            daily_gaps = gap_stats[0] if gap_stats[0] else 0
            avg_gap_duration = gap_stats[1] if gap_stats[1] else 0
            estimated_missed = gap_stats[2] if gap_stats[2] else 0

        return {
            'backfill_requests': {
                'total': total_requests,
                'completed': len(completed_requests),
                'failed': len(failed_requests),
                'success_rate': success_rate
            },
            'events_retrieved': total_events,
            'total_cost': total_cost,
            'daily_cost_used': self.daily_backfill_cost,
            'daily_budget_remaining': self.max_backfill_cost - self.daily_backfill_cost,
            'connection_gaps': {
                'daily_gaps': daily_gaps,
                'avg_duration_seconds': avg_gap_duration,
                'estimated_missed_events': estimated_missed
            }
        }


def create_backfill_manager(api_key: str, max_daily_cost: float = 20.0) -> BackfillManager:
    """
    Factory function to create backfill manager

    Args:
        api_key: Databento API key
        max_daily_cost: Maximum daily backfill cost

    Returns:
        Configured BackfillManager instance
    """
    return BackfillManager(api_key, max_daily_cost)


if __name__ == "__main__":
    # Example usage
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv('DATABENTO_API_KEY')
    if not api_key:
        print("Please set DATABENTO_API_KEY environment variable")
        exit(1)

    # Create backfill manager
    manager = create_backfill_manager(api_key, max_daily_cost=10.0)

    # Simulate backfill event handler
    def handle_backfill_event(event: Dict[str, Any]):
        print(f"Backfill event: {event.get('symbol')} - {event.get('action')}")

    def handle_backfill_complete(request: BackfillRequest):
        print(f"Backfill completed: {request.events_retrieved} events, "
              f"cost: ${request.actual_cost:.2f}")

    manager.on_backfill_event = handle_backfill_event
    manager.on_backfill_complete = handle_backfill_complete

    # Simulate connection gap
    print("Simulating connection gap and backfill...")

    # Track some events
    manager.track_event_timestamp(datetime.now(timezone.utc) - timedelta(minutes=5))

    # Simulate disconnect
    manager.on_disconnect()

    # Wait a bit
    time.sleep(2)

    # Simulate reconnect with backfill
    backfill_request = manager.on_reconnect(['NQ.OPT'])

    if backfill_request:
        print(f"Backfill initiated: {backfill_request.request_id}")

        # Wait for completion
        time.sleep(10)

        # Get statistics
        stats = manager.get_backfill_statistics()
        print(f"\nBackfill Statistics:")
        print(f"  Requests: {stats['backfill_requests']['total']}")
        print(f"  Success rate: {stats['backfill_requests']['success_rate']:.1%}")
        print(f"  Daily cost: ${stats['daily_cost_used']:.2f}")
        print(f"  Budget remaining: ${stats['daily_budget_remaining']:.2f}")
    else:
        print("No backfill needed")
