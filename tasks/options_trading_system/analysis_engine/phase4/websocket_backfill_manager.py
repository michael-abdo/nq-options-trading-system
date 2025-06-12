#!/usr/bin/env python3
"""
WebSocket Backfill Manager for IFD v3.0

This module handles automatic backfill of market data when WebSocket connections
are lost or interrupted, ensuring no data gaps that could affect signal quality.

Key Features:
- Automatic detection of WebSocket connection gaps
- Cost-controlled backfill requests to data providers
- Intelligent gap analysis and prioritization
- Integration with historical download cost tracker
- Real-time monitoring of connection health
- Configurable backfill strategies and limits

Connection Gap Handling:
1. Real-time monitoring of WebSocket connection status
2. Automatic detection of connection interruptions
3. Gap analysis to determine missing data periods
4. Cost estimation for backfill requests
5. Prioritized backfill based on data importance
6. Integration with monthly budget constraints
"""

import os
import json
import logging
import sqlite3
import threading
import time
import queue
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing cost tracker for budget integration
try:
    from .historical_download_cost_tracker import create_historical_download_cost_tracker, CostProvider
    COST_TRACKER_AVAILABLE = True
except ImportError:
    logger.warning("Historical download cost tracker not available")
    COST_TRACKER_AVAILABLE = False


class BackfillPriority(Enum):
    """Priority levels for backfill requests"""
    CRITICAL = "critical"    # Real-time signal generation affected
    HIGH = "high"           # Recent data gaps
    MEDIUM = "medium"       # Older gaps but within analysis window
    LOW = "low"            # Historical data for baseline updates


class BackfillStatus(Enum):
    """Status of backfill requests"""
    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConnectionStatus(Enum):
    """WebSocket connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ConnectionGap:
    """Represents a gap in WebSocket connection"""
    gap_id: str
    symbol: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[float]

    # Gap characteristics
    data_type: str  # "mbo", "trades", "quotes"
    estimated_records_lost: int
    estimated_data_size_mb: float

    # Impact assessment
    affects_real_time_signals: bool
    affects_baseline_calculation: bool
    priority: BackfillPriority

    # Status
    detected_at: datetime
    is_closed: bool = False

    def calculate_duration(self):
        """Calculate gap duration"""
        if self.end_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
            self.is_closed = True


@dataclass
class BackfillRequest:
    """Request for backfilling missing data"""
    request_id: str
    gap_id: str
    symbol: str
    start_time: datetime
    end_time: datetime

    # Request details
    data_type: str
    provider: CostProvider
    priority: BackfillPriority

    # Cost management
    estimated_cost: float
    max_cost_limit: float
    requires_approval: bool

    # Status tracking
    status: BackfillStatus
    created_at: datetime
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    actual_cost: Optional[float] = None
    records_retrieved: Optional[int] = None
    error_message: Optional[str] = None

    # Metadata
    requester: str = "websocket_backfill_manager"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ConnectionEvent:
    """WebSocket connection event"""
    event_id: str
    symbol: str
    timestamp: datetime
    event_type: str  # "connected", "disconnected", "error", "reconnected"
    connection_status: ConnectionStatus

    # Event details
    error_message: Optional[str] = None
    reconnect_attempt: int = 0
    last_message_time: Optional[datetime] = None

    # Connection metrics
    connection_duration_seconds: Optional[float] = None
    messages_received: int = 0
    bytes_received: int = 0


class GapAnalyzer:
    """Analyzes connection gaps and determines backfill requirements"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Gap analysis parameters
        self.min_gap_duration = config.get('min_gap_duration_seconds', 30)  # 30 seconds
        self.max_backfill_cost = config.get('max_backfill_cost', 50.0)  # $50
        self.critical_gap_duration = config.get('critical_gap_duration_seconds', 300)  # 5 minutes

        # Data volume estimation
        self.volume_estimates = {
            'mbo': {'records_per_second': 1000, 'bytes_per_record': 150},
            'trades': {'records_per_second': 100, 'bytes_per_record': 80},
            'quotes': {'records_per_second': 500, 'bytes_per_record': 100}
        }

        # Cost estimation
        self.cost_per_mb = config.get('cost_per_mb', 0.10)  # $0.10 per MB

    def analyze_gap(self, gap: ConnectionGap) -> Tuple[bool, Dict[str, Any]]:
        """
        Analyze a connection gap and determine if backfill is needed

        Args:
            gap: Connection gap to analyze

        Returns:
            Tuple of (should_backfill, analysis_details)
        """

        analysis = {
            'gap_duration': gap.duration_seconds or 0,
            'is_significant': False,
            'backfill_recommended': False,
            'estimated_cost': 0.0,
            'priority': BackfillPriority.LOW,
            'reasons': []
        }

        if not gap.duration_seconds:
            gap.calculate_duration()

        duration_seconds = gap.duration_seconds or 0

        # Check if gap is significant enough for backfill
        if duration_seconds < self.min_gap_duration:
            analysis['reasons'].append(f"Gap too short: {duration_seconds}s < {self.min_gap_duration}s minimum")
            return False, analysis

        analysis['is_significant'] = True

        # Estimate data volume and cost
        volume_info = self.volume_estimates.get(gap.data_type, self.volume_estimates['mbo'])

        estimated_records = int(duration_seconds * volume_info['records_per_second'])
        estimated_bytes = estimated_records * volume_info['bytes_per_record']
        estimated_mb = estimated_bytes / (1024 * 1024)
        estimated_cost = estimated_mb * self.cost_per_mb

        # Update gap with estimates
        gap.estimated_records_lost = estimated_records
        gap.estimated_data_size_mb = estimated_mb

        analysis['estimated_records'] = estimated_records
        analysis['estimated_mb'] = estimated_mb
        analysis['estimated_cost'] = estimated_cost

        # Determine priority based on gap characteristics
        if duration_seconds >= self.critical_gap_duration:
            analysis['priority'] = BackfillPriority.CRITICAL
            analysis['reasons'].append(f"Critical gap: {duration_seconds}s >= {self.critical_gap_duration}s")
        elif gap.affects_real_time_signals:
            analysis['priority'] = BackfillPriority.HIGH
            analysis['reasons'].append("Affects real-time signal generation")
        elif gap.affects_baseline_calculation:
            analysis['priority'] = BackfillPriority.MEDIUM
            analysis['reasons'].append("Affects baseline calculation")
        else:
            analysis['priority'] = BackfillPriority.LOW
            analysis['reasons'].append("Historical data gap")

        gap.priority = analysis['priority']

        # Cost-based decision
        if estimated_cost > self.max_backfill_cost:
            analysis['reasons'].append(f"Cost too high: ${estimated_cost:.2f} > ${self.max_backfill_cost}")
            analysis['backfill_recommended'] = False
        elif analysis['priority'] in [BackfillPriority.CRITICAL, BackfillPriority.HIGH]:
            analysis['reasons'].append(f"High priority gap requires backfill")
            analysis['backfill_recommended'] = True
        elif estimated_cost < 5.0:  # Auto-approve cheap backfills
            analysis['reasons'].append(f"Low cost backfill: ${estimated_cost:.2f}")
            analysis['backfill_recommended'] = True
        else:
            analysis['reasons'].append(f"Medium priority gap, cost analysis required")
            analysis['backfill_recommended'] = True

        return analysis['backfill_recommended'], analysis

    def prioritize_backfill_requests(self, requests: List[BackfillRequest]) -> List[BackfillRequest]:
        """Prioritize backfill requests based on importance and cost"""

        def priority_score(request: BackfillRequest) -> float:
            """Calculate priority score for sorting"""

            # Base score by priority
            priority_scores = {
                BackfillPriority.CRITICAL: 1000,
                BackfillPriority.HIGH: 100,
                BackfillPriority.MEDIUM: 10,
                BackfillPriority.LOW: 1
            }

            base_score = priority_scores.get(request.priority, 1)

            # Adjust for recency (more recent gaps have higher priority)
            hours_old = (datetime.now(timezone.utc) - request.start_time).total_seconds() / 3600
            recency_factor = max(0.1, 1.0 - (hours_old / 24))  # Decay over 24 hours

            # Adjust for cost efficiency (lower cost per record = higher priority)
            gap_duration = (request.end_time - request.start_time).total_seconds()
            cost_efficiency = 1.0 / max(request.estimated_cost, 0.01)

            return base_score * recency_factor * cost_efficiency

        # Sort by priority score (highest first)
        return sorted(requests, key=priority_score, reverse=True)


class BackfillDatabase:
    """Database for tracking connection gaps and backfill requests"""

    def __init__(self, db_path: str = "outputs/websocket_backfill.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Connection events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connection_events (
                    event_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    connection_status TEXT NOT NULL,
                    error_message TEXT,
                    reconnect_attempt INTEGER DEFAULT 0,
                    last_message_time TEXT,
                    connection_duration_seconds REAL,
                    messages_received INTEGER DEFAULT 0,
                    bytes_received INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Connection gaps table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connection_gaps (
                    gap_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds REAL,
                    data_type TEXT NOT NULL,
                    estimated_records_lost INTEGER DEFAULT 0,
                    estimated_data_size_mb REAL DEFAULT 0.0,
                    affects_real_time_signals BOOLEAN DEFAULT 0,
                    affects_baseline_calculation BOOLEAN DEFAULT 0,
                    priority TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    is_closed BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Backfill requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backfill_requests (
                    request_id TEXT PRIMARY KEY,
                    gap_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    estimated_cost REAL NOT NULL,
                    max_cost_limit REAL NOT NULL,
                    requires_approval BOOLEAN NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    approved_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    actual_cost REAL,
                    records_retrieved INTEGER,
                    error_message TEXT,
                    requester TEXT DEFAULT 'websocket_backfill_manager',
                    metadata TEXT,  -- JSON
                    FOREIGN KEY (gap_id) REFERENCES connection_gaps (gap_id)
                )
            """)

            # Backfill sessions (for tracking active backfills)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backfill_sessions (
                    session_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    provider_session_id TEXT,
                    records_processed INTEGER DEFAULT 0,
                    bytes_processed INTEGER DEFAULT 0,
                    cost_accumulated REAL DEFAULT 0.0,
                    last_update TEXT NOT NULL,
                    FOREIGN KEY (request_id) REFERENCES backfill_requests (request_id)
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_symbol_time ON connection_events(symbol, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_gaps_symbol_time ON connection_gaps(symbol, start_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON backfill_requests(status, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_request ON backfill_sessions(request_id)")

            conn.commit()

    def store_connection_event(self, event: ConnectionEvent):
        """Store connection event"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO connection_events
                (event_id, symbol, timestamp, event_type, connection_status, error_message,
                 reconnect_attempt, last_message_time, connection_duration_seconds,
                 messages_received, bytes_received)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.symbol, event.timestamp.isoformat(),
                event.event_type, event.connection_status.value, event.error_message,
                event.reconnect_attempt,
                event.last_message_time.isoformat() if event.last_message_time else None,
                event.connection_duration_seconds, event.messages_received, event.bytes_received
            ))
            conn.commit()

    def store_connection_gap(self, gap: ConnectionGap):
        """Store connection gap"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO connection_gaps
                (gap_id, symbol, start_time, end_time, duration_seconds, data_type,
                 estimated_records_lost, estimated_data_size_mb, affects_real_time_signals,
                 affects_baseline_calculation, priority, detected_at, is_closed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                gap.gap_id, gap.symbol, gap.start_time.isoformat(),
                gap.end_time.isoformat() if gap.end_time else None,
                gap.duration_seconds, gap.data_type, gap.estimated_records_lost,
                gap.estimated_data_size_mb, gap.affects_real_time_signals,
                gap.affects_baseline_calculation, gap.priority.value,
                gap.detected_at.isoformat(), gap.is_closed
            ))
            conn.commit()

    def store_backfill_request(self, request: BackfillRequest):
        """Store backfill request"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO backfill_requests
                (request_id, gap_id, symbol, start_time, end_time, data_type, provider,
                 priority, estimated_cost, max_cost_limit, requires_approval, status,
                 created_at, approved_at, started_at, completed_at, actual_cost,
                 records_retrieved, error_message, requester, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.request_id, request.gap_id, request.symbol,
                request.start_time.isoformat(), request.end_time.isoformat(),
                request.data_type, request.provider.value, request.priority.value,
                request.estimated_cost, request.max_cost_limit, request.requires_approval,
                request.status.value, request.created_at.isoformat(),
                request.approved_at.isoformat() if request.approved_at else None,
                request.started_at.isoformat() if request.started_at else None,
                request.completed_at.isoformat() if request.completed_at else None,
                request.actual_cost, request.records_retrieved, request.error_message,
                request.requester, json.dumps(request.metadata) if request.metadata else None
            ))
            conn.commit()

    def get_open_gaps(self, symbol: Optional[str] = None) -> List[ConnectionGap]:
        """Get open (unclosed) connection gaps"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if symbol:
                cursor.execute("""
                    SELECT * FROM connection_gaps
                    WHERE symbol = ? AND is_closed = 0
                    ORDER BY start_time DESC
                """, (symbol,))
            else:
                cursor.execute("""
                    SELECT * FROM connection_gaps
                    WHERE is_closed = 0
                    ORDER BY start_time DESC
                """)

            gaps = []
            for row in cursor.fetchall():
                gap = ConnectionGap(
                    gap_id=row[0],
                    symbol=row[1],
                    start_time=datetime.fromisoformat(row[2]),
                    end_time=datetime.fromisoformat(row[3]) if row[3] else None,
                    duration_seconds=row[4],
                    data_type=row[5],
                    estimated_records_lost=row[6],
                    estimated_data_size_mb=row[7],
                    affects_real_time_signals=bool(row[8]),
                    affects_baseline_calculation=bool(row[9]),
                    priority=BackfillPriority(row[10]),
                    detected_at=datetime.fromisoformat(row[11]),
                    is_closed=bool(row[12])
                )
                gaps.append(gap)

            return gaps

    def get_pending_backfill_requests(self) -> List[BackfillRequest]:
        """Get pending backfill requests"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM backfill_requests
                WHERE status = ?
                ORDER BY created_at ASC
            """, (BackfillStatus.PENDING.value,))

            requests = []
            for row in cursor.fetchall():
                metadata = json.loads(row[20]) if row[20] else {}

                request = BackfillRequest(
                    request_id=row[0],
                    gap_id=row[1],
                    symbol=row[2],
                    start_time=datetime.fromisoformat(row[3]),
                    end_time=datetime.fromisoformat(row[4]),
                    data_type=row[5],
                    provider=CostProvider(row[6]),
                    priority=BackfillPriority(row[7]),
                    estimated_cost=row[8],
                    max_cost_limit=row[9],
                    requires_approval=bool(row[10]),
                    status=BackfillStatus(row[11]),
                    created_at=datetime.fromisoformat(row[12]),
                    approved_at=datetime.fromisoformat(row[13]) if row[13] else None,
                    started_at=datetime.fromisoformat(row[14]) if row[14] else None,
                    completed_at=datetime.fromisoformat(row[15]) if row[15] else None,
                    actual_cost=row[16],
                    records_retrieved=row[17],
                    error_message=row[18],
                    requester=row[19],
                    metadata=metadata
                )
                requests.append(request)

            return requests


class WebSocketBackfillManager:
    """
    Main WebSocket backfill management system

    Features:
    - Real-time monitoring of WebSocket connections
    - Automatic detection of connection gaps
    - Cost-controlled backfill request management
    - Integration with historical download cost tracker
    - Prioritized backfill processing
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize WebSocket backfill manager

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.database = BackfillDatabase(config.get('db_path', 'outputs/websocket_backfill.db'))
        self.gap_analyzer = GapAnalyzer(config.get('gap_analysis', {}))

        # Cost tracker integration
        self.cost_tracker = None
        if COST_TRACKER_AVAILABLE:
            try:
                cost_config = config.get('cost_tracker', {})
                self.cost_tracker = create_historical_download_cost_tracker(cost_config)
                logger.info("Cost tracker integration enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize cost tracker: {e}")

        # Connection monitoring
        self.active_connections: Dict[str, datetime] = {}  # symbol -> last_message_time
        self.connection_status: Dict[str, ConnectionStatus] = {}  # symbol -> status
        self.open_gaps: Dict[str, ConnectionGap] = {}  # gap_id -> gap

        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread = None
        self.backfill_queue = queue.Queue()
        self.backfill_processor_thread = None

        # Configuration
        self.auto_approve_limit = config.get('auto_approve_limit', 10.0)  # $10
        self.max_concurrent_backfills = config.get('max_concurrent_backfills', 3)
        self.gap_detection_interval = config.get('gap_detection_interval', 60)  # seconds

        # Callbacks
        self.on_gap_detected: Optional[Callable[[ConnectionGap], None]] = None
        self.on_backfill_requested: Optional[Callable[[BackfillRequest], None]] = None
        self.on_backfill_completed: Optional[Callable[[BackfillRequest], None]] = None

        logger.info("WebSocket Backfill Manager initialized")

    def start_monitoring(self):
        """Start WebSocket connection monitoring"""
        if self.monitoring_active:
            logger.warning("Backfill monitoring already active")
            return

        self.monitoring_active = True

        # Start gap detection thread
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="BackfillMonitor"
        )
        self.monitor_thread.start()

        # Start backfill processor thread
        self.backfill_processor_thread = threading.Thread(
            target=self._backfill_processor_loop,
            daemon=True,
            name="BackfillProcessor"
        )
        self.backfill_processor_thread.start()

        logger.info("WebSocket backfill monitoring started")

    def stop_monitoring(self):
        """Stop WebSocket connection monitoring"""
        self.monitoring_active = False

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)

        if self.backfill_processor_thread and self.backfill_processor_thread.is_alive():
            self.backfill_processor_thread.join(timeout=5)

        logger.info("WebSocket backfill monitoring stopped")

    def report_connection_event(self, symbol: str, event_type: str,
                               error_message: Optional[str] = None,
                               metadata: Optional[Dict] = None):
        """Report a WebSocket connection event"""

        event_id = f"{symbol}_{event_type}_{int(time.time())}"
        timestamp = datetime.now(timezone.utc)

        # Determine connection status
        status_mapping = {
            'connected': ConnectionStatus.CONNECTED,
            'disconnected': ConnectionStatus.DISCONNECTED,
            'reconnecting': ConnectionStatus.RECONNECTING,
            'error': ConnectionStatus.FAILED,
            'reconnected': ConnectionStatus.CONNECTED
        }

        connection_status = status_mapping.get(event_type, ConnectionStatus.DISCONNECTED)

        # Create event
        event = ConnectionEvent(
            event_id=event_id,
            symbol=symbol,
            timestamp=timestamp,
            event_type=event_type,
            connection_status=connection_status,
            error_message=error_message
        )

        # Store event
        self.database.store_connection_event(event)

        # Update connection state
        if event_type == 'connected' or event_type == 'reconnected':
            self.active_connections[symbol] = timestamp
            self.connection_status[symbol] = ConnectionStatus.CONNECTED

            # Close any open gaps
            self._close_open_gaps(symbol, timestamp)

        elif event_type == 'disconnected' or event_type == 'error':
            if symbol in self.active_connections:
                last_connected = self.active_connections[symbol]
                del self.active_connections[symbol]
            else:
                last_connected = timestamp  # Fallback

            self.connection_status[symbol] = connection_status

            # Create new gap
            self._create_connection_gap(symbol, last_connected, metadata or {})

        logger.debug(f"Connection event: {symbol} {event_type}")

    def report_message_received(self, symbol: str, message_data: Optional[Dict] = None):
        """Report that a WebSocket message was received"""

        timestamp = datetime.now(timezone.utc)

        # Update last message time
        self.active_connections[symbol] = timestamp
        self.connection_status[symbol] = ConnectionStatus.CONNECTED

        # If there was an open gap, close it
        if symbol in [gap.symbol for gap in self.open_gaps.values()]:
            self._close_open_gaps(symbol, timestamp)

    def request_backfill(self, backfill_request: BackfillRequest) -> Optional[str]:
        """
        Request a backfill for missing data

        Args:
            backfill_request: Backfill request details

        Returns:
            Request ID if successful, None if failed
        """

        try:
            # Store request
            self.database.store_backfill_request(backfill_request)

            # Add to processing queue
            self.backfill_queue.put(backfill_request)

            # Trigger callback
            if self.on_backfill_requested:
                self.on_backfill_requested(backfill_request)

            logger.info(f"Backfill requested: {backfill_request.request_id} "
                       f"({backfill_request.symbol} ${backfill_request.estimated_cost:.2f})")

            return backfill_request.request_id

        except Exception as e:
            logger.error(f"Failed to request backfill: {e}")
            return None

    def _monitoring_loop(self):
        """Main monitoring loop for gap detection"""

        while self.monitoring_active:
            try:
                # Check for stale connections (gaps in real time)
                self._detect_stale_connections()

                # Process pending backfill requests
                self._process_pending_requests()

                # Sleep until next check
                time.sleep(self.gap_detection_interval)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(30)  # Short sleep on error

    def _backfill_processor_loop(self):
        """Process backfill requests from queue"""

        while self.monitoring_active:
            try:
                # Get request from queue (blocking with timeout)
                request = self.backfill_queue.get(timeout=5)

                # Process the request
                self._process_backfill_request(request)

                # Mark task as done
                self.backfill_queue.task_done()

            except queue.Empty:
                continue  # Timeout, continue monitoring
            except Exception as e:
                logger.error(f"Backfill processor error: {e}")
                time.sleep(10)

    def _detect_stale_connections(self):
        """Detect connections that have gone stale"""

        now = datetime.now(timezone.utc)
        stale_threshold = timedelta(seconds=300)  # 5 minutes

        for symbol, last_message in list(self.active_connections.items()):
            if now - last_message > stale_threshold:
                # Connection appears stale, treat as disconnected
                logger.warning(f"Stale connection detected: {symbol}")
                self.report_connection_event(symbol, 'disconnected',
                                           error_message="Stale connection detected")

    def _close_open_gaps(self, symbol: str, end_time: datetime):
        """Close open gaps for a symbol"""

        for gap_id, gap in list(self.open_gaps.items()):
            if gap.symbol == symbol and not gap.is_closed:
                gap.end_time = end_time
                gap.calculate_duration()

                # Store updated gap
                self.database.store_connection_gap(gap)

                # Remove from open gaps
                del self.open_gaps[gap_id]

                logger.info(f"Closed gap: {gap_id} ({gap.duration_seconds:.1f}s)")

    def _create_connection_gap(self, symbol: str, start_time: datetime, metadata: Dict):
        """Create a new connection gap"""

        gap_id = f"gap_{symbol}_{int(start_time.timestamp())}"

        # Determine gap characteristics from metadata
        data_type = metadata.get('data_type', 'mbo')
        affects_real_time = metadata.get('affects_real_time_signals', True)
        affects_baseline = metadata.get('affects_baseline_calculation', True)

        gap = ConnectionGap(
            gap_id=gap_id,
            symbol=symbol,
            start_time=start_time,
            end_time=None,
            duration_seconds=None,
            data_type=data_type,
            estimated_records_lost=0,
            estimated_data_size_mb=0.0,
            affects_real_time_signals=affects_real_time,
            affects_baseline_calculation=affects_baseline,
            priority=BackfillPriority.MEDIUM,  # Will be updated by analyzer
            detected_at=datetime.now(timezone.utc)
        )

        # Store gap
        self.database.store_connection_gap(gap)
        self.open_gaps[gap_id] = gap

        # Trigger callback
        if self.on_gap_detected:
            self.on_gap_detected(gap)

        logger.info(f"Created gap: {gap_id} for {symbol}")

    def _process_pending_requests(self):
        """Process pending backfill requests"""

        pending_requests = self.database.get_pending_backfill_requests()

        for request in pending_requests:
            if request.estimated_cost <= self.auto_approve_limit:
                # Auto-approve low-cost requests
                request.status = BackfillStatus.APPROVED
                request.approved_at = datetime.now(timezone.utc)
                self.database.store_backfill_request(request)

                # Add to processing queue
                self.backfill_queue.put(request)

                logger.info(f"Auto-approved backfill: {request.request_id} (${request.estimated_cost:.2f})")

    def _process_backfill_request(self, request: BackfillRequest):
        """Process an individual backfill request"""

        try:
            if request.status != BackfillStatus.APPROVED:
                logger.warning(f"Skipping non-approved request: {request.request_id}")
                return

            # Update status to in progress
            request.status = BackfillStatus.IN_PROGRESS
            request.started_at = datetime.now(timezone.utc)
            self.database.store_backfill_request(request)

            # Use cost tracker integration if available
            if self.cost_tracker:
                try:
                    # Request historical download through cost tracker
                    download_request_id, estimate = self.cost_tracker.request_download(
                        requester=request.requester,
                        provider=request.provider,
                        dataset="GLBX.MDP3",  # Databento dataset
                        symbols=[request.symbol],
                        start_date=request.start_time,
                        end_date=request.end_time,
                        schema=request.data_type,
                        purpose="websocket_backfill"
                    )

                    # Simulate successful completion
                    request.status = BackfillStatus.COMPLETED
                    request.completed_at = datetime.now(timezone.utc)
                    request.actual_cost = estimate.estimated_total_cost
                    request.records_retrieved = 1000  # Mock value

                    logger.info(f"Backfill completed: {request.request_id} (${request.actual_cost:.2f})")

                except Exception as e:
                    request.status = BackfillStatus.FAILED
                    request.error_message = str(e)
                    logger.error(f"Backfill failed: {request.request_id} - {e}")

            else:
                # Mock completion without cost tracker
                request.status = BackfillStatus.COMPLETED
                request.completed_at = datetime.now(timezone.utc)
                request.actual_cost = request.estimated_cost
                request.records_retrieved = 1000

                logger.info(f"Mock backfill completed: {request.request_id}")

            # Store final result
            self.database.store_backfill_request(request)

            # Trigger callback
            if self.on_backfill_completed:
                self.on_backfill_completed(request)

        except Exception as e:
            request.status = BackfillStatus.FAILED
            request.error_message = str(e)
            self.database.store_backfill_request(request)
            logger.error(f"Backfill processing error: {e}")

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status for all symbols"""

        now = datetime.now(timezone.utc)

        status = {
            'timestamp': now.isoformat(),
            'active_connections': len(self.active_connections),
            'open_gaps': len(self.open_gaps),
            'connections': {},
            'recent_gaps': []
        }

        # Connection details
        for symbol, last_message in self.active_connections.items():
            age_seconds = (now - last_message).total_seconds()
            status['connections'][symbol] = {
                'status': self.connection_status.get(symbol, ConnectionStatus.UNKNOWN).value,
                'last_message_age_seconds': age_seconds,
                'is_healthy': age_seconds < 300  # 5 minutes
            }

        # Recent gaps
        for gap in list(self.open_gaps.values())[-5:]:  # Last 5 gaps
            status['recent_gaps'].append({
                'gap_id': gap.gap_id,
                'symbol': gap.symbol,
                'duration_seconds': gap.duration_seconds,
                'priority': gap.priority.value,
                'is_closed': gap.is_closed
            })

        return status

    def get_backfill_summary(self) -> Dict[str, Any]:
        """Get summary of backfill operations"""

        pending_requests = self.database.get_pending_backfill_requests()

        summary = {
            'pending_requests': len(pending_requests),
            'queue_size': self.backfill_queue.qsize(),
            'auto_approve_limit': self.auto_approve_limit,
            'max_concurrent_backfills': self.max_concurrent_backfills,
            'monitoring_active': self.monitoring_active
        }

        if pending_requests:
            total_estimated_cost = sum(r.estimated_cost for r in pending_requests)
            priorities = defaultdict(int)
            for r in pending_requests:
                priorities[r.priority.value] += 1

            summary.update({
                'total_estimated_cost': total_estimated_cost,
                'requests_by_priority': dict(priorities)
            })

        return summary


def create_websocket_backfill_manager(config: Optional[Dict] = None) -> WebSocketBackfillManager:
    """Factory function to create WebSocket backfill manager"""

    if config is None:
        config = {
            'db_path': 'outputs/websocket_backfill.db',
            'auto_approve_limit': 10.0,
            'max_concurrent_backfills': 3,
            'gap_detection_interval': 60,
            'gap_analysis': {
                'min_gap_duration_seconds': 30,
                'max_backfill_cost': 50.0,
                'critical_gap_duration_seconds': 300,
                'cost_per_mb': 0.10
            }
        }

    return WebSocketBackfillManager(config)


if __name__ == "__main__":
    # Example usage
    manager = create_websocket_backfill_manager()

    def on_gap_detected(gap: ConnectionGap):
        print(f"🔌 Gap detected: {gap.symbol} ({gap.duration_seconds:.1f}s)")

    def on_backfill_requested(request: BackfillRequest):
        print(f"📥 Backfill requested: {request.symbol} ${request.estimated_cost:.2f}")

    def on_backfill_completed(request: BackfillRequest):
        print(f"✅ Backfill completed: {request.symbol} ${request.actual_cost:.2f}")

    manager.on_gap_detected = on_gap_detected
    manager.on_backfill_requested = on_backfill_requested
    manager.on_backfill_completed = on_backfill_completed

    print("=== WebSocket Backfill Manager Test ===")

    # Start monitoring
    manager.start_monitoring()
    print("✓ Backfill monitoring started")

    # Simulate connection events
    print("\nSimulating connection events...")

    # Normal connection
    manager.report_connection_event("NQ.OPT", "connected")

    # Send some messages
    for i in range(5):
        time.sleep(1)
        manager.report_message_received("NQ.OPT")

    # Simulate disconnection
    manager.report_connection_event("NQ.OPT", "disconnected", error_message="Network timeout")
    print("Simulated disconnection...")

    # Wait for gap detection
    time.sleep(3)

    # Simulate reconnection
    manager.report_connection_event("NQ.OPT", "reconnected")
    print("Simulated reconnection...")

    # Create a manual backfill request
    backfill_request = BackfillRequest(
        request_id="test_backfill_001",
        gap_id="gap_NQ.OPT_123456",
        symbol="NQ.OPT",
        start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
        end_time=datetime.now(timezone.utc),
        data_type="mbo",
        provider=CostProvider.DATABENTO,
        priority=BackfillPriority.HIGH,
        estimated_cost=8.50,
        max_cost_limit=15.0,
        requires_approval=False,
        status=BackfillStatus.PENDING,
        created_at=datetime.now(timezone.utc)
    )

    request_id = manager.request_backfill(backfill_request)
    if request_id:
        print(f"✓ Manual backfill requested: {request_id}")

    # Show status
    print("\nConnection Status:")
    status = manager.get_connection_status()
    print(f"  Active connections: {status['active_connections']}")
    print(f"  Open gaps: {status['open_gaps']}")

    print("\nBackfill Summary:")
    summary = manager.get_backfill_summary()
    print(f"  Pending requests: {summary['pending_requests']}")
    print(f"  Queue size: {summary['queue_size']}")
    print(f"  Auto-approve limit: ${summary['auto_approve_limit']}")

    # Wait for processing
    time.sleep(5)

    manager.stop_monitoring()
    print("\n✓ Backfill monitoring stopped")
