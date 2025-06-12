#!/usr/bin/env python3
"""
Historical Download Cost Tracker for IFD v3.0

This module tracks costs for one-time historical data downloads from external providers
(primarily Databento) to ensure budget compliance and cost optimization.

Key Features:
- Pre-download cost estimation and approval workflow
- Real-time cost tracking during downloads
- Integration with monthly budget dashboard
- Historical download audit trail
- Cost optimization recommendations
- Provider cost comparison
- Download scheduling for cost optimization

Cost Management:
- Pre-approval required for downloads >$10
- Automatic budget checks before downloads
- Real-time cost accumulation during downloads
- Monthly budget integration
- Cost alerting and notifications
"""

import os
import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum
import hashlib
import statistics

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing databento for cost estimation
try:
    import databento as db
    DATABENTO_AVAILABLE = True
except ImportError:
    DATABENTO_AVAILABLE = False
    logger.warning("Databento not available - using mock cost estimation")

# Try importing monthly budget dashboard
try:
    from .monthly_budget_dashboard import MonthlyBudgetDashboard
    BUDGET_INTEGRATION_AVAILABLE = True
except ImportError:
    logger.warning("Budget dashboard not available - running standalone")
    BUDGET_INTEGRATION_AVAILABLE = False


class DownloadStatus(Enum):
    """Status of historical download requests"""
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CostProvider(Enum):
    """Data providers with different cost structures"""
    DATABENTO = "databento"
    POLYGON = "polygon"
    BARCHART = "barchart"
    INTERACTIVE_BROKERS = "interactive_brokers"


@dataclass
class CostEstimate:
    """Cost estimation for a historical download"""
    request_id: str
    provider: CostProvider
    dataset: str
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    schema: str

    # Cost breakdown
    base_cost: float
    per_day_cost: float
    per_symbol_cost: float
    data_volume_gb: float
    data_volume_cost: float

    # Total estimates
    estimated_total_cost: float
    estimated_duration_minutes: int
    confidence: float  # 0-1, confidence in estimate

    # Budget impact
    current_monthly_spend: float
    monthly_budget_limit: float
    remaining_budget: float
    budget_utilization_after: float

    # Recommendations
    optimization_suggestions: List[str]
    approval_required: bool
    recommended_action: str  # "APPROVE", "OPTIMIZE", "REJECT", "SCHEDULE"


@dataclass
class DownloadRequest:
    """Request for historical data download"""
    request_id: str
    requester: str
    timestamp: datetime

    # Data specifications
    provider: CostProvider
    dataset: str
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    schema: str
    stype_in: Optional[str] = None

    # Cost management
    cost_estimate: Optional[CostEstimate] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    max_cost_limit: Optional[float] = None

    # Status tracking
    status: DownloadStatus = DownloadStatus.PENDING_APPROVAL
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    actual_cost: Optional[float] = None
    records_downloaded: Optional[int] = None
    data_size_gb: Optional[float] = None
    error_message: Optional[str] = None

    # Usage tracking
    download_purpose: str = "analysis"
    priority: str = "normal"  # "low", "normal", "high", "urgent"


@dataclass
class DownloadSession:
    """Active download session tracking"""
    session_id: str
    request_id: str
    started_at: datetime

    # Progress tracking
    records_processed: int = 0
    estimated_total_records: int = 0
    data_size_mb: float = 0.0

    # Cost tracking
    cost_accumulator: float = 0.0
    last_cost_update: datetime = None

    # Performance metrics
    records_per_second: float = 0.0
    estimated_completion: Optional[datetime] = None

    # Error tracking
    errors_encountered: int = 0
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.last_cost_update is None:
            self.last_cost_update = self.started_at


class CostEstimator:
    """Estimates costs for historical data downloads"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize cost estimator

        Args:
            config: Configuration with provider cost structures
        """
        self.config = config

        # Cost structures by provider (rates per unit)
        self.cost_structures = self._load_cost_structures(config)

        # Data volume estimation models
        self.volume_models = self._load_volume_models(config)

    def _load_cost_structures(self, config: Dict[str, Any]) -> Dict[CostProvider, Dict]:
        """Load provider cost structures"""

        return {
            CostProvider.DATABENTO: {
                'base_cost': 0.01,  # Base API call cost
                'per_gb': 10.0,     # $10 per GB
                'per_day': 0.50,    # $0.50 per day of data
                'per_symbol': 0.10, # $0.10 per symbol
                'mbo_multiplier': 2.0,  # MBO data costs 2x more
                'options_multiplier': 1.5,  # Options data costs 1.5x more
                'priority_multiplier': {'low': 0.8, 'normal': 1.0, 'high': 1.2, 'urgent': 1.5}
            },
            CostProvider.POLYGON: {
                'base_cost': 0.005,
                'per_gb': 8.0,
                'per_day': 0.30,
                'per_symbol': 0.05,
                'options_multiplier': 1.3,
                'priority_multiplier': {'low': 1.0, 'normal': 1.0, 'high': 1.1, 'urgent': 1.2}
            },
            CostProvider.BARCHART: {
                'base_cost': 0.02,
                'per_gb': 15.0,
                'per_day': 1.00,
                'per_symbol': 0.20,
                'options_multiplier': 2.0,
                'priority_multiplier': {'low': 1.0, 'normal': 1.0, 'high': 1.0, 'urgent': 1.0}
            }
        }

    def _load_volume_models(self, config: Dict[str, Any]) -> Dict:
        """Load data volume estimation models"""

        return {
            'base_mb_per_symbol_day': {
                'trades': 5.0,      # 5 MB per symbol per day for trades
                'quotes': 15.0,     # 15 MB per symbol per day for quotes
                'mbo': 50.0,        # 50 MB per symbol per day for MBO
                'options_trades': 2.0,
                'options_quotes': 8.0,
                'options_mbo': 25.0
            },
            'market_multipliers': {
                'high_volume': 2.5,   # High volume days
                'normal': 1.0,
                'low_volume': 0.6,    # Low volume days (weekends, holidays)
                'options': 0.8        # Options generally lower volume than equities
            }
        }

    def estimate_download_cost(self, request: DownloadRequest,
                              current_monthly_spend: float = 0.0,
                              monthly_budget: float = 200.0) -> CostEstimate:
        """
        Estimate cost for a historical download request

        Args:
            request: Download request to estimate
            current_monthly_spend: Current month spending
            monthly_budget: Monthly budget limit

        Returns:
            Detailed cost estimate
        """

        provider_costs = self.cost_structures.get(request.provider, self.cost_structures[CostProvider.DATABENTO])

        # Calculate time period
        days = (request.end_date - request.start_date).days + 1

        # Base costs
        base_cost = provider_costs['base_cost']
        per_day_cost = provider_costs['per_day'] * days
        per_symbol_cost = provider_costs['per_symbol'] * len(request.symbols)

        # Estimate data volume
        data_volume_gb = self._estimate_data_volume(request) / 1024  # Convert MB to GB
        data_volume_cost = data_volume_gb * provider_costs['per_gb']

        # Apply multipliers
        total_cost = base_cost + per_day_cost + per_symbol_cost + data_volume_cost

        # Schema multiplier
        if 'mbo' in request.schema.lower():
            total_cost *= provider_costs.get('mbo_multiplier', 1.0)

        # Options multiplier
        if 'opt' in request.dataset.lower() or any('opt' in sym.lower() for sym in request.symbols):
            total_cost *= provider_costs.get('options_multiplier', 1.0)

        # Priority multiplier
        priority_mult = provider_costs.get('priority_multiplier', {}).get(request.priority, 1.0)
        total_cost *= priority_mult

        # Calculate budget impact
        remaining_budget = monthly_budget - current_monthly_spend
        budget_utilization_after = (current_monthly_spend + total_cost) / monthly_budget

        # Generate optimization suggestions
        optimization_suggestions = self._generate_optimization_suggestions(
            request, total_cost, remaining_budget, budget_utilization_after
        )

        # Determine if approval required (>$10 or >50% remaining budget)
        approval_required = (total_cost > 10.0 or
                           total_cost > remaining_budget * 0.5 or
                           budget_utilization_after > 0.8)

        # Make recommendation
        recommended_action = self._make_cost_recommendation(
            total_cost, remaining_budget, budget_utilization_after, approval_required
        )

        # Estimate duration
        estimated_duration = self._estimate_download_duration(request, data_volume_gb * 1024)

        # Confidence in estimate (based on data availability and complexity)
        confidence = self._calculate_estimate_confidence(request)

        return CostEstimate(
            request_id=request.request_id,
            provider=request.provider,
            dataset=request.dataset,
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            schema=request.schema,
            base_cost=base_cost,
            per_day_cost=per_day_cost,
            per_symbol_cost=per_symbol_cost,
            data_volume_gb=data_volume_gb,
            data_volume_cost=data_volume_cost,
            estimated_total_cost=total_cost,
            estimated_duration_minutes=estimated_duration,
            confidence=confidence,
            current_monthly_spend=current_monthly_spend,
            monthly_budget_limit=monthly_budget,
            remaining_budget=remaining_budget,
            budget_utilization_after=budget_utilization_after,
            optimization_suggestions=optimization_suggestions,
            approval_required=approval_required,
            recommended_action=recommended_action
        )

    def _estimate_data_volume(self, request: DownloadRequest) -> float:
        """Estimate data volume in MB"""

        days = (request.end_date - request.start_date).days + 1
        base_volumes = self.volume_models['base_mb_per_symbol_day']

        # Get base volume per symbol per day
        if 'mbo' in request.schema.lower():
            if 'opt' in request.dataset.lower():
                base_mb = base_volumes['options_mbo']
            else:
                base_mb = base_volumes['mbo']
        elif 'trades' in request.schema.lower():
            if 'opt' in request.dataset.lower():
                base_mb = base_volumes['options_trades']
            else:
                base_mb = base_volumes['trades']
        else:  # quotes or other
            if 'opt' in request.dataset.lower():
                base_mb = base_volumes['options_quotes']
            else:
                base_mb = base_volumes['quotes']

        # Calculate total volume
        total_mb = base_mb * len(request.symbols) * days

        # Apply market multipliers (simplified - could be more sophisticated)
        multiplier = self.volume_models['market_multipliers']['normal']
        if 'opt' in request.dataset.lower():
            multiplier *= self.volume_models['market_multipliers']['options']

        return total_mb * multiplier

    def _estimate_download_duration(self, request: DownloadRequest, data_size_mb: float) -> int:
        """Estimate download duration in minutes"""

        # Base processing rate (MB per minute)
        base_rate = 50.0  # 50 MB/minute

        # Provider-specific rates
        provider_rates = {
            CostProvider.DATABENTO: 100.0,  # Fast
            CostProvider.POLYGON: 75.0,     # Medium
            CostProvider.BARCHART: 30.0     # Slower
        }

        rate = provider_rates.get(request.provider, base_rate)

        # MBO data takes longer to process
        if 'mbo' in request.schema.lower():
            rate *= 0.5

        # More symbols = more parallel requests = faster
        if len(request.symbols) > 10:
            rate *= 1.5

        estimated_minutes = max(data_size_mb / rate, 1.0)  # Minimum 1 minute

        return int(estimated_minutes)

    def _calculate_estimate_confidence(self, request: DownloadRequest) -> float:
        """Calculate confidence in cost estimate (0-1)"""

        confidence = 0.8  # Base confidence

        # Higher confidence for known providers
        if request.provider == CostProvider.DATABENTO:
            confidence += 0.1

        # Lower confidence for MBO data (more variable)
        if 'mbo' in request.schema.lower():
            confidence -= 0.1

        # Lower confidence for very large date ranges
        days = (request.end_date - request.start_date).days
        if days > 365:
            confidence -= 0.2
        elif days > 90:
            confidence -= 0.1

        # Lower confidence for many symbols
        if len(request.symbols) > 100:
            confidence -= 0.1

        return max(min(confidence, 1.0), 0.3)  # Bound between 0.3 and 1.0

    def _generate_optimization_suggestions(self, request: DownloadRequest,
                                         total_cost: float, remaining_budget: float,
                                         budget_utilization_after: float) -> List[str]:
        """Generate cost optimization suggestions"""

        suggestions = []

        if total_cost > remaining_budget:
            suggestions.append("Cost exceeds remaining budget - consider reducing scope")

        if budget_utilization_after > 0.9:
            suggestions.append("Will use >90% of monthly budget - consider scheduling for next month")

        if len(request.symbols) > 50:
            suggestions.append("Large symbol list - consider splitting into multiple requests")

        days = (request.end_date - request.start_date).days
        if days > 365:
            suggestions.append("Long time period - consider breaking into smaller chunks")

        if request.priority == "urgent" and total_cost > 20:
            suggestions.append("Urgent priority adds cost - consider normal priority if not time-sensitive")

        if request.provider == CostProvider.BARCHART and total_cost > 10:
            suggestions.append("Barchart is expensive for large downloads - consider Databento or Polygon")

        # Suggest alternative schemas
        if 'mbo' in request.schema.lower() and total_cost > 15:
            suggestions.append("MBO data is expensive - consider trades/quotes schema if sufficient")

        return suggestions

    def _make_cost_recommendation(self, total_cost: float, remaining_budget: float,
                                budget_utilization_after: float, approval_required: bool) -> str:
        """Make recommendation for cost management"""

        if total_cost > remaining_budget:
            return "REJECT"
        elif budget_utilization_after > 0.95:
            return "SCHEDULE"  # Schedule for next month
        elif approval_required:
            return "OPTIMIZE"  # Optimize before approval
        else:
            return "APPROVE"


class DownloadCostDatabase:
    """Database for tracking historical download costs"""

    def __init__(self, db_path: str = "outputs/historical_download_costs.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Download requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS download_requests (
                    request_id TEXT PRIMARY KEY,
                    requester TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    dataset TEXT NOT NULL,
                    symbols TEXT NOT NULL,  -- JSON array
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    schema TEXT NOT NULL,
                    stype_in TEXT,
                    download_purpose TEXT DEFAULT 'analysis',
                    priority TEXT DEFAULT 'normal',
                    status TEXT NOT NULL,
                    approved_by TEXT,
                    approved_at TEXT,
                    max_cost_limit REAL,
                    started_at TEXT,
                    completed_at TEXT,
                    actual_cost REAL,
                    records_downloaded INTEGER,
                    data_size_gb REAL,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Cost estimates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cost_estimates (
                    request_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    estimated_total_cost REAL NOT NULL,
                    estimated_duration_minutes INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    base_cost REAL NOT NULL,
                    per_day_cost REAL NOT NULL,
                    per_symbol_cost REAL NOT NULL,
                    data_volume_gb REAL NOT NULL,
                    data_volume_cost REAL NOT NULL,
                    current_monthly_spend REAL NOT NULL,
                    monthly_budget_limit REAL NOT NULL,
                    remaining_budget REAL NOT NULL,
                    budget_utilization_after REAL NOT NULL,
                    optimization_suggestions TEXT,  -- JSON array
                    approval_required BOOLEAN NOT NULL,
                    recommended_action TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (request_id) REFERENCES download_requests (request_id)
                )
            """)

            # Download sessions table (for active tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS download_sessions (
                    session_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    records_processed INTEGER DEFAULT 0,
                    estimated_total_records INTEGER DEFAULT 0,
                    data_size_mb REAL DEFAULT 0.0,
                    cost_accumulator REAL DEFAULT 0.0,
                    last_cost_update TEXT,
                    records_per_second REAL DEFAULT 0.0,
                    estimated_completion TEXT,
                    errors_encountered INTEGER DEFAULT 0,
                    warnings TEXT,  -- JSON array
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (request_id) REFERENCES download_requests (request_id)
                )
            """)

            # Monthly cost summaries
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monthly_download_costs (
                    month TEXT PRIMARY KEY,  -- YYYY-MM format
                    total_cost REAL DEFAULT 0.0,
                    total_downloads INTEGER DEFAULT 0,
                    total_records INTEGER DEFAULT 0,
                    total_data_gb REAL DEFAULT 0.0,
                    cost_by_provider TEXT,  -- JSON object
                    cost_by_purpose TEXT,   -- JSON object
                    avg_cost_per_gb REAL DEFAULT 0.0,
                    largest_download_cost REAL DEFAULT 0.0,
                    budget_utilization REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON download_requests(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON download_requests(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_request ON download_sessions(request_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_month ON monthly_download_costs(month)")

            conn.commit()

    def save_download_request(self, request: DownloadRequest):
        """Save download request"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO download_requests
                (request_id, requester, timestamp, provider, dataset, symbols, start_date, end_date,
                 schema, stype_in, download_purpose, priority, status, approved_by, approved_at,
                 max_cost_limit, started_at, completed_at, actual_cost, records_downloaded,
                 data_size_gb, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.request_id, request.requester, request.timestamp.isoformat(),
                request.provider.value, request.dataset, json.dumps(request.symbols),
                request.start_date.isoformat(), request.end_date.isoformat(),
                request.schema, request.stype_in, request.download_purpose, request.priority,
                request.status.value, request.approved_by,
                request.approved_at.isoformat() if request.approved_at else None,
                request.max_cost_limit,
                request.started_at.isoformat() if request.started_at else None,
                request.completed_at.isoformat() if request.completed_at else None,
                request.actual_cost, request.records_downloaded, request.data_size_gb,
                request.error_message
            ))
            conn.commit()

    def save_cost_estimate(self, estimate: CostEstimate):
        """Save cost estimate"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO cost_estimates
                (request_id, provider, estimated_total_cost, estimated_duration_minutes, confidence,
                 base_cost, per_day_cost, per_symbol_cost, data_volume_gb, data_volume_cost,
                 current_monthly_spend, monthly_budget_limit, remaining_budget, budget_utilization_after,
                 optimization_suggestions, approval_required, recommended_action)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                estimate.request_id, estimate.provider.value, estimate.estimated_total_cost,
                estimate.estimated_duration_minutes, estimate.confidence, estimate.base_cost,
                estimate.per_day_cost, estimate.per_symbol_cost, estimate.data_volume_gb,
                estimate.data_volume_cost, estimate.current_monthly_spend, estimate.monthly_budget_limit,
                estimate.remaining_budget, estimate.budget_utilization_after,
                json.dumps(estimate.optimization_suggestions), estimate.approval_required,
                estimate.recommended_action
            ))
            conn.commit()

    def get_monthly_download_costs(self, year: int, month: int) -> Dict[str, Any]:
        """Get monthly download cost summary"""
        month_key = f"{year:04d}-{month:02d}"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get existing summary
            cursor.execute("""
                SELECT * FROM monthly_download_costs WHERE month = ?
            """, (month_key,))

            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))

            # Calculate summary from individual requests
            start_date = f"{year:04d}-{month:02d}-01"
            end_date = f"{year:04d}-{month:02d}-31"

            cursor.execute("""
                SELECT provider, SUM(actual_cost), COUNT(*), SUM(records_downloaded), SUM(data_size_gb)
                FROM download_requests
                WHERE DATE(completed_at) >= ? AND DATE(completed_at) <= ? AND actual_cost IS NOT NULL
                GROUP BY provider
            """, (start_date, end_date))

            provider_data = cursor.fetchall()

            total_cost = sum(row[1] for row in provider_data if row[1])
            total_downloads = sum(row[2] for row in provider_data)
            total_records = sum(row[3] for row in provider_data if row[3])
            total_data_gb = sum(row[4] for row in provider_data if row[4])

            cost_by_provider = {row[0]: row[1] for row in provider_data if row[1]}

            return {
                'month': month_key,
                'total_cost': total_cost,
                'total_downloads': total_downloads,
                'total_records': total_records,
                'total_data_gb': total_data_gb,
                'cost_by_provider': cost_by_provider,
                'avg_cost_per_gb': total_cost / max(total_data_gb, 0.001)
            }


class HistoricalDownloadCostTracker:
    """
    Main historical download cost tracking system

    Features:
    - Pre-download cost estimation and approval
    - Real-time cost tracking during downloads
    - Monthly budget integration
    - Cost optimization recommendations
    - Download audit trail and analytics
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize historical download cost tracker

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.database = DownloadCostDatabase(config.get('db_path', 'outputs/historical_download_costs.db'))
        self.cost_estimator = CostEstimator(config.get('cost_estimation', {}))

        # Budget integration
        self.budget_dashboard = None
        if BUDGET_INTEGRATION_AVAILABLE:
            try:
                from .monthly_budget_dashboard import create_budget_dashboard
                monthly_budget = config.get('monthly_budget', 200.0)
                self.budget_dashboard = create_budget_dashboard(monthly_budget)
                logger.info("Budget dashboard integration enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize budget dashboard: {e}")

        # Active download sessions
        self.active_sessions: Dict[str, DownloadSession] = {}
        self.session_lock = threading.Lock()

        # Approval workflow
        self.auto_approve_limit = config.get('auto_approve_limit', 5.0)  # $5
        self.require_approval_above = config.get('require_approval_above', 10.0)  # $10

        # Callbacks
        self.on_approval_required: Optional[Callable[[DownloadRequest, CostEstimate], None]] = None
        self.on_download_completed: Optional[Callable[[DownloadRequest], None]] = None
        self.on_budget_exceeded: Optional[Callable[[str, float, float], None]] = None

        logger.info("Historical Download Cost Tracker initialized")

    def request_download(self,
                        requester: str,
                        provider: CostProvider,
                        dataset: str,
                        symbols: List[str],
                        start_date: datetime,
                        end_date: datetime,
                        schema: str,
                        purpose: str = "analysis",
                        priority: str = "normal",
                        stype_in: Optional[str] = None) -> Tuple[str, CostEstimate]:
        """
        Request a historical data download with cost estimation

        Args:
            requester: Who is requesting the download
            provider: Data provider
            dataset: Dataset name
            symbols: List of symbols to download
            start_date: Start date for data
            end_date: End date for data
            schema: Data schema (mbo, trades, quotes, etc.)
            purpose: Purpose of download
            priority: Priority level
            stype_in: Symbol type (optional)

        Returns:
            Tuple of (request_id, cost_estimate)
        """

        # Generate request ID
        request_id = self._generate_request_id(provider, dataset, symbols, start_date, end_date)

        # Create download request
        request = DownloadRequest(
            request_id=request_id,
            requester=requester,
            timestamp=datetime.now(timezone.utc),
            provider=provider,
            dataset=dataset,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            schema=schema,
            stype_in=stype_in,
            download_purpose=purpose,
            priority=priority
        )

        # Get current monthly spending
        current_month = datetime.now(timezone.utc)
        monthly_costs = self.database.get_monthly_download_costs(current_month.year, current_month.month)
        current_monthly_spend = monthly_costs.get('total_cost', 0.0)

        # Get monthly budget
        monthly_budget = self.config.get('monthly_budget', 200.0)

        # Generate cost estimate
        cost_estimate = self.cost_estimator.estimate_download_cost(
            request, current_monthly_spend, monthly_budget
        )

        # Store estimate
        request.cost_estimate = cost_estimate

        # Determine approval workflow
        if cost_estimate.estimated_total_cost <= self.auto_approve_limit:
            # Auto-approve small downloads
            request.status = DownloadStatus.APPROVED
            request.approved_by = "AUTO_APPROVED"
            request.approved_at = datetime.now(timezone.utc)
            logger.info(f"Auto-approved download {request_id}: ${cost_estimate.estimated_total_cost:.2f}")

        elif cost_estimate.recommended_action == "REJECT":
            # Auto-reject if over budget
            request.status = DownloadStatus.CANCELLED
            logger.warning(f"Auto-rejected download {request_id}: {cost_estimate.optimization_suggestions}")

        else:
            # Requires manual approval
            request.status = DownloadStatus.PENDING_APPROVAL
            logger.info(f"Download {request_id} requires approval: ${cost_estimate.estimated_total_cost:.2f}")

            # Trigger approval callback
            if self.on_approval_required:
                self.on_approval_required(request, cost_estimate)

        # Save to database
        self.database.save_download_request(request)
        self.database.save_cost_estimate(cost_estimate)

        # Update budget dashboard
        if self.budget_dashboard:
            try:
                # Add estimated cost to historical costs
                cost_data = {
                    'historical_download_costs': cost_estimate.estimated_total_cost
                }
                self.budget_dashboard.update_costs(cost_data)
            except Exception as e:
                logger.warning(f"Failed to update budget dashboard: {e}")

        return request_id, cost_estimate

    def approve_download(self, request_id: str, approved_by: str,
                        max_cost_limit: Optional[float] = None) -> bool:
        """Approve a pending download request"""

        # Implementation would load request, update status, and save
        logger.info(f"Approved download {request_id} by {approved_by}")
        return True

    def reject_download(self, request_id: str, rejected_by: str, reason: str) -> bool:
        """Reject a pending download request"""

        # Implementation would update status to cancelled
        logger.info(f"Rejected download {request_id} by {rejected_by}: {reason}")
        return True

    def start_download(self, request_id: str) -> Optional[str]:
        """
        Start a download and return session ID for tracking

        Args:
            request_id: Download request ID

        Returns:
            Session ID if started successfully
        """

        # Load request (simplified - would load from database)
        # For now, create a mock session
        session_id = f"session_{request_id}_{int(time.time())}"

        session = DownloadSession(
            session_id=session_id,
            request_id=request_id,
            started_at=datetime.now(timezone.utc)
        )

        with self.session_lock:
            self.active_sessions[session_id] = session

        logger.info(f"Started download session {session_id} for request {request_id}")
        return session_id

    def update_download_progress(self, session_id: str,
                                records_processed: int,
                                data_size_mb: float,
                                cost_increment: float = 0.0):
        """Update progress for active download session"""

        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found")
            return

        session = self.active_sessions[session_id]

        # Update progress
        session.records_processed = records_processed
        session.data_size_mb = data_size_mb
        session.cost_accumulator += cost_increment
        session.last_cost_update = datetime.now(timezone.utc)

        # Calculate rate
        duration = (session.last_cost_update - session.started_at).total_seconds()
        if duration > 0:
            session.records_per_second = records_processed / duration

        # Estimate completion
        if session.estimated_total_records > 0 and session.records_per_second > 0:
            remaining_records = session.estimated_total_records - records_processed
            remaining_seconds = remaining_records / session.records_per_second
            session.estimated_completion = session.last_cost_update + timedelta(seconds=remaining_seconds)

        logger.debug(f"Session {session_id}: {records_processed} records, "
                    f"${session.cost_accumulator:.2f} cost")

    def complete_download(self, session_id: str, success: bool = True,
                         error_message: Optional[str] = None) -> bool:
        """Complete a download session"""

        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found")
            return False

        session = self.active_sessions[session_id]

        # Update request status and actual costs
        # This would update the database with final results

        with self.session_lock:
            del self.active_sessions[session_id]

        logger.info(f"Completed download session {session_id}: "
                   f"success={success}, cost=${session.cost_accumulator:.2f}")

        return True

    def get_download_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a download request"""

        # This would load from database and return current status
        # For now, return mock data
        return {
            'request_id': request_id,
            'status': 'in_progress',
            'estimated_cost': 12.50,
            'actual_cost': 8.75,
            'progress': 0.7,
            'estimated_completion': datetime.now(timezone.utc) + timedelta(minutes=15)
        }

    def get_monthly_cost_summary(self, year: int, month: int) -> Dict[str, Any]:
        """Get monthly cost summary with analysis"""

        monthly_data = self.database.get_monthly_download_costs(year, month)

        # Add analysis
        monthly_budget = self.config.get('monthly_budget', 200.0)
        utilization = monthly_data.get('total_cost', 0.0) / monthly_budget

        # Get cost trends
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        prev_data = self.database.get_monthly_download_costs(prev_year, prev_month)

        cost_trend = "stable"
        if prev_data.get('total_cost', 0) > 0:
            change = (monthly_data.get('total_cost', 0.0) - prev_data.get('total_cost', 0.0)) / prev_data.get('total_cost', 1.0)
            if change > 0.1:
                cost_trend = "increasing"
            elif change < -0.1:
                cost_trend = "decreasing"

        return {
            **monthly_data,
            'budget_utilization': utilization,
            'cost_trend': cost_trend,
            'recommendations': self._generate_monthly_recommendations(monthly_data, monthly_budget)
        }

    def _generate_request_id(self, provider: CostProvider, dataset: str,
                           symbols: List[str], start_date: datetime, end_date: datetime) -> str:
        """Generate unique request ID"""

        # Create hash of request parameters
        request_str = f"{provider.value}_{dataset}_{','.join(sorted(symbols))}_{start_date.isoformat()}_{end_date.isoformat()}"
        request_hash = hashlib.md5(request_str.encode()).hexdigest()[:8]

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

        return f"hist_{provider.value}_{request_hash}_{timestamp}"

    def _generate_monthly_recommendations(self, monthly_data: Dict[str, Any],
                                        monthly_budget: float) -> List[str]:
        """Generate cost optimization recommendations"""

        recommendations = []

        utilization = monthly_data.get('total_cost', 0.0) / monthly_budget

        if utilization > 0.9:
            recommendations.append("Approaching monthly budget limit - consider deferring non-critical downloads")

        if monthly_data.get('avg_cost_per_gb', 0) > 12:
            recommendations.append("High cost per GB - consider optimizing data requests or switching providers")

        cost_by_provider = monthly_data.get('cost_by_provider', {})
        if cost_by_provider:
            max_provider = max(cost_by_provider.items(), key=lambda x: x[1])
            if max_provider[1] > monthly_budget * 0.5:
                recommendations.append(f"High costs from {max_provider[0]} - consider cost comparison with alternatives")

        if monthly_data.get('total_downloads', 0) > 20:
            recommendations.append("High number of downloads - consider consolidating requests")

        return recommendations


def create_historical_download_cost_tracker(config: Optional[Dict] = None) -> HistoricalDownloadCostTracker:
    """Factory function to create historical download cost tracker"""

    if config is None:
        config = {
            'db_path': 'outputs/historical_download_costs.db',
            'monthly_budget': 200.0,
            'auto_approve_limit': 5.0,
            'require_approval_above': 10.0,
            'cost_estimation': {}
        }

    return HistoricalDownloadCostTracker(config)


if __name__ == "__main__":
    # Example usage
    tracker = create_historical_download_cost_tracker()

    def on_approval_required(request: DownloadRequest, estimate: CostEstimate):
        print(f"🔍 Approval required for {request.request_id}: ${estimate.estimated_total_cost:.2f}")
        print(f"   Suggestions: {estimate.optimization_suggestions}")

    def on_download_completed(request: DownloadRequest):
        print(f"✅ Download completed: {request.request_id}")

    tracker.on_approval_required = on_approval_required
    tracker.on_download_completed = on_download_completed

    # Test download request
    print("=== Historical Download Cost Tracker Test ===")

    request_id, estimate = tracker.request_download(
        requester="test_user",
        provider=CostProvider.DATABENTO,
        dataset="GLBX.MDP3",
        symbols=["NQ.OPT"],
        start_date=datetime.now(timezone.utc) - timedelta(days=30),
        end_date=datetime.now(timezone.utc),
        schema="mbo",
        purpose="IFD_v3_analysis",
        priority="normal",
        stype_in="parent"
    )

    print(f"\nDownload Request Created:")
    print(f"  Request ID: {request_id}")
    print(f"  Estimated Cost: ${estimate.estimated_total_cost:.2f}")
    print(f"  Data Volume: {estimate.data_volume_gb:.2f} GB")
    print(f"  Duration: {estimate.estimated_duration_minutes} minutes")
    print(f"  Confidence: {estimate.confidence:.1%}")
    print(f"  Approval Required: {estimate.approval_required}")
    print(f"  Recommendation: {estimate.recommended_action}")

    if estimate.optimization_suggestions:
        print(f"\nOptimization Suggestions:")
        for suggestion in estimate.optimization_suggestions:
            print(f"  - {suggestion}")

    # Test download session
    if estimate.recommended_action in ["APPROVE", "OPTIMIZE"]:
        session_id = tracker.start_download(request_id)
        if session_id:
            print(f"\nDownload session started: {session_id}")

            # Simulate progress updates
            for i in range(5):
                records = (i + 1) * 1000
                data_mb = (i + 1) * 10.0
                cost_increment = 0.50

                tracker.update_download_progress(session_id, records, data_mb, cost_increment)
                time.sleep(1)

            # Complete download
            tracker.complete_download(session_id, success=True)

    # Get monthly summary
    now = datetime.now(timezone.utc)
    monthly_summary = tracker.get_monthly_cost_summary(now.year, now.month)

    print(f"\nMonthly Cost Summary ({now.year}-{now.month:02d}):")
    print(f"  Total Cost: ${monthly_summary.get('total_cost', 0):.2f}")
    print(f"  Downloads: {monthly_summary.get('total_downloads', 0)}")
    print(f"  Budget Utilization: {monthly_summary.get('budget_utilization', 0):.1%}")
    print(f"  Cost Trend: {monthly_summary.get('cost_trend', 'unknown')}")

    if monthly_summary.get('recommendations'):
        print(f"\nRecommendations:")
        for rec in monthly_summary['recommendations']:
            print(f"  - {rec}")
