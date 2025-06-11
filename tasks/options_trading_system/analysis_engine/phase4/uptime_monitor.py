#!/usr/bin/env python3
"""
Uptime Monitoring System for IFD v3.0

This module provides comprehensive uptime monitoring to ensure the system
meets the 99.9% uptime SLA target specified in Phase 4 requirements.

Key Features:
- Real-time availability monitoring of critical system components
- Downtime detection and incident tracking
- SLA compliance calculation and reporting
- Automated alerting for availability issues
- Historical uptime analysis and trending
- Incident categorization and root cause tracking

SLA Target: 99.9% uptime
- Allowed downtime: 8.76 hours/year, 43.2 minutes/month, 10.1 minutes/week
- Monitoring frequency: Every 30 seconds
- Incident response: Immediate alerting for downtime >1 minute
"""

import os
import json
import logging
import sqlite3
import threading
import time
import requests
import socket
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import statistics
import subprocess

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComponentType(Enum):
    """Types of system components to monitor"""
    WEB_SERVICE = "web_service"
    DATABASE = "database"
    DATA_FEED = "data_feed"
    WEBSOCKET = "websocket"
    API_ENDPOINT = "api_endpoint"
    FILE_SYSTEM = "file_system"
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"
    EXTERNAL_API = "external_api"


class ComponentStatus(Enum):
    """Component status states"""
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"


class IncidentSeverity(Enum):
    """Incident severity levels"""
    CRITICAL = "critical"    # Complete system down
    HIGH = "high"           # Core functionality impacted
    MEDIUM = "medium"       # Degraded performance
    LOW = "low"            # Minor issues
    INFO = "info"          # Informational


@dataclass
class ComponentConfig:
    """Configuration for a monitored component"""
    component_id: str
    name: str
    component_type: ComponentType
    
    # Health check configuration
    check_method: str  # "http", "tcp", "ping", "function", "file"
    check_target: str  # URL, host:port, IP, function name, file path
    check_interval: int = 30  # seconds
    timeout: int = 10  # seconds
    
    # Health criteria
    expected_response_code: Optional[int] = None
    expected_response_text: Optional[str] = None
    max_response_time: Optional[float] = None  # seconds
    
    # Criticality and SLA
    is_critical: bool = True
    sla_target: float = 99.9  # percentage
    
    # Alerting
    alert_after_failures: int = 2  # Alert after N consecutive failures
    escalation_minutes: int = 5   # Escalate if down for N minutes
    
    # Metadata
    description: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component_id: str
    timestamp: datetime
    status: ComponentStatus
    response_time: float  # seconds
    
    # Check details
    check_method: str
    success: bool
    error_message: Optional[str] = None
    response_code: Optional[int] = None
    response_size: Optional[int] = None
    
    # Metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DowntimeIncident:
    """Represents a downtime incident"""
    incident_id: str
    component_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    
    # Incident details
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    title: str = ""
    description: str = ""
    root_cause: str = ""
    
    # Impact assessment
    duration_minutes: Optional[float] = None
    affected_users: int = 0
    revenue_impact: float = 0.0
    
    # Response tracking
    detected_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Status
    is_resolved: bool = False
    resolution_notes: str = ""
    
    def calculate_duration(self):
        """Calculate incident duration"""
        if self.ended_at:
            self.duration_minutes = (self.ended_at - self.started_at).total_seconds() / 60


@dataclass
class UptimeStatistics:
    """Uptime statistics for a time period"""
    component_id: str
    period_start: datetime
    period_end: datetime
    
    # Uptime metrics
    total_checks: int
    successful_checks: int
    failed_checks: int
    uptime_percentage: float
    
    # SLA compliance
    sla_target: float
    sla_compliance: bool
    sla_breach_minutes: float
    
    # Downtime analysis
    total_incidents: int
    total_downtime_minutes: float
    longest_incident_minutes: float
    mean_time_to_recovery: float
    
    # Performance metrics
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    
    # Availability grade
    availability_grade: str  # A, B, C, D, F


class HealthChecker:
    """Performs health checks on system components"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timeout = config.get('default_timeout', 10)
        
        # Request session for HTTP checks
        self.session = requests.Session()
        self.session.timeout = self.timeout
    
    def check_component(self, component_config: ComponentConfig) -> HealthCheckResult:
        """
        Perform health check on a component
        
        Args:
            component_config: Component configuration
            
        Returns:
            HealthCheckResult with check outcome
        """
        
        start_time = time.time()
        
        try:
            if component_config.check_method == "http":
                result = self._check_http(component_config)
            elif component_config.check_method == "tcp":
                result = self._check_tcp(component_config)
            elif component_config.check_method == "ping":
                result = self._check_ping(component_config)
            elif component_config.check_method == "function":
                result = self._check_function(component_config)
            elif component_config.check_method == "file":
                result = self._check_file(component_config)
            else:
                result = HealthCheckResult(
                    component_id=component_config.component_id,
                    timestamp=datetime.now(timezone.utc),
                    status=ComponentStatus.UNKNOWN,
                    response_time=0.0,
                    check_method=component_config.check_method,
                    success=False,
                    error_message=f"Unknown check method: {component_config.check_method}"
                )
        
        except Exception as e:
            # Handle unexpected errors
            response_time = time.time() - start_time
            result = HealthCheckResult(
                component_id=component_config.component_id,
                timestamp=datetime.now(timezone.utc),
                status=ComponentStatus.DOWN,
                response_time=response_time,
                check_method=component_config.check_method,
                success=False,
                error_message=str(e)
            )
        
        # Apply response time threshold
        if (result.success and component_config.max_response_time and 
            result.response_time > component_config.max_response_time):
            result.status = ComponentStatus.DEGRADED
            result.error_message = f"Response time {result.response_time:.2f}s exceeds threshold {component_config.max_response_time}s"
        
        return result
    
    def _check_http(self, config: ComponentConfig) -> HealthCheckResult:
        """Check HTTP endpoint"""
        
        start_time = time.time()
        
        try:
            response = self.session.get(
                config.check_target,
                timeout=config.timeout,
                allow_redirects=True
            )
            
            response_time = time.time() - start_time
            
            # Check response code
            success = True
            error_message = None
            
            if config.expected_response_code and response.status_code != config.expected_response_code:
                success = False
                error_message = f"Expected {config.expected_response_code}, got {response.status_code}"
            
            # Check response text
            if success and config.expected_response_text:
                if config.expected_response_text not in response.text:
                    success = False
                    error_message = f"Expected text '{config.expected_response_text}' not found"
            
            return HealthCheckResult(
                component_id=config.component_id,
                timestamp=datetime.now(timezone.utc),
                status=ComponentStatus.UP if success else ComponentStatus.DOWN,
                response_time=response_time,
                check_method="http",
                success=success,
                error_message=error_message,
                response_code=response.status_code,
                response_size=len(response.content)
            )
        
        except requests.exceptions.Timeout:
            response_time = time.time() - start_time
            return HealthCheckResult(
                component_id=config.component_id,
                timestamp=datetime.now(timezone.utc),
                status=ComponentStatus.DOWN,
                response_time=response_time,
                check_method="http",
                success=False,
                error_message=f"Timeout after {config.timeout}s"
            )
        
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                component_id=config.component_id,
                timestamp=datetime.now(timezone.utc),
                status=ComponentStatus.DOWN,
                response_time=response_time,
                check_method="http",
                success=False,
                error_message=str(e)
            )
    
    def _check_tcp(self, config: ComponentConfig) -> HealthCheckResult:
        """Check TCP port connectivity"""
        
        start_time = time.time()
        
        try:
            # Parse host:port
            if ':' in config.check_target:
                host, port = config.check_target.split(':', 1)
                port = int(port)
            else:
                host = config.check_target
                port = 80  # Default port
            
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(config.timeout)
            
            result = sock.connect_ex((host, port))
            response_time = time.time() - start_time
            
            sock.close()
            
            success = (result == 0)
            
            return HealthCheckResult(
                component_id=config.component_id,
                timestamp=datetime.now(timezone.utc),
                status=ComponentStatus.UP if success else ComponentStatus.DOWN,
                response_time=response_time,
                check_method="tcp",
                success=success,
                error_message=None if success else f"Connection failed to {host}:{port}"
            )
        
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                component_id=config.component_id,
                timestamp=datetime.now(timezone.utc),
                status=ComponentStatus.DOWN,
                response_time=response_time,
                check_method="tcp",
                success=False,
                error_message=str(e)
            )
    
    def _check_ping(self, config: ComponentConfig) -> HealthCheckResult:
        """Check host connectivity via ping"""
        
        start_time = time.time()
        
        try:
            # Use system ping command
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(config.timeout * 1000), config.check_target],
                capture_output=True,
                text=True,
                timeout=config.timeout + 1
            )
            
            response_time = time.time() - start_time
            success = (result.returncode == 0)
            
            return HealthCheckResult(
                component_id=config.component_id,
                timestamp=datetime.now(timezone.utc),
                status=ComponentStatus.UP if success else ComponentStatus.DOWN,
                response_time=response_time,
                check_method="ping",
                success=success,
                error_message=None if success else result.stderr.strip()
            )
        
        except subprocess.TimeoutExpired:
            response_time = time.time() - start_time
            return HealthCheckResult(
                component_id=config.component_id,
                timestamp=datetime.now(timezone.utc),
                status=ComponentStatus.DOWN,
                response_time=response_time,
                check_method="ping",
                success=False,
                error_message=f"Ping timeout after {config.timeout}s"
            )
        
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                component_id=config.component_id,
                timestamp=datetime.now(timezone.utc),
                status=ComponentStatus.DOWN,
                response_time=response_time,
                check_method="ping",
                success=False,
                error_message=str(e)
            )
    
    def _check_function(self, config: ComponentConfig) -> HealthCheckResult:
        """Check custom function"""
        
        start_time = time.time()
        
        try:
            # This would call a custom health check function
            # For now, return a mock result
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                component_id=config.component_id,
                timestamp=datetime.now(timezone.utc),
                status=ComponentStatus.UP,
                response_time=response_time,
                check_method="function",
                success=True,
                metadata={'function': config.check_target}
            )
        
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                component_id=config.component_id,
                timestamp=datetime.now(timezone.utc),
                status=ComponentStatus.DOWN,
                response_time=response_time,
                check_method="function",
                success=False,
                error_message=str(e)
            )
    
    def _check_file(self, config: ComponentConfig) -> HealthCheckResult:
        """Check file system health"""
        
        start_time = time.time()
        
        try:
            # Check if file/directory exists and is accessible
            path = config.check_target
            exists = os.path.exists(path)
            
            if exists and os.path.isfile(path):
                # Try to read file
                with open(path, 'r') as f:
                    f.read(100)  # Read first 100 bytes
            elif exists and os.path.isdir(path):
                # Try to list directory
                os.listdir(path)
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                component_id=config.component_id,
                timestamp=datetime.now(timezone.utc),
                status=ComponentStatus.UP if exists else ComponentStatus.DOWN,
                response_time=response_time,
                check_method="file",
                success=exists,
                error_message=None if exists else f"Path does not exist: {path}"
            )
        
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                component_id=config.component_id,
                timestamp=datetime.now(timezone.utc),
                status=ComponentStatus.DOWN,
                response_time=response_time,
                check_method="file",
                success=False,
                error_message=str(e)
            )


class UptimeDatabase:
    """Database for storing uptime monitoring data"""
    
    def __init__(self, db_path: str = "outputs/uptime_monitoring.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Component configurations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS components (
                    component_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    check_method TEXT NOT NULL,
                    check_target TEXT NOT NULL,
                    check_interval INTEGER DEFAULT 30,
                    timeout INTEGER DEFAULT 10,
                    is_critical BOOLEAN DEFAULT 1,
                    sla_target REAL DEFAULT 99.9,
                    description TEXT,
                    tags TEXT,  -- JSON array
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Health check results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time REAL NOT NULL,
                    check_method TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    response_code INTEGER,
                    response_size INTEGER,
                    metadata TEXT,  -- JSON
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (component_id) REFERENCES components (component_id)
                )
            """)
            
            # Downtime incidents
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    component_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    root_cause TEXT,
                    duration_minutes REAL,
                    affected_users INTEGER DEFAULT 0,
                    revenue_impact REAL DEFAULT 0.0,
                    detected_at TEXT,
                    acknowledged_at TEXT,
                    resolved_at TEXT,
                    is_resolved BOOLEAN DEFAULT 0,
                    resolution_notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (component_id) REFERENCES components (component_id)
                )
            """)
            
            # Uptime statistics (hourly/daily summaries)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uptime_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_id TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    period_type TEXT NOT NULL,  -- 'hour', 'day', 'week', 'month'
                    total_checks INTEGER NOT NULL,
                    successful_checks INTEGER NOT NULL,
                    failed_checks INTEGER NOT NULL,
                    uptime_percentage REAL NOT NULL,
                    sla_target REAL NOT NULL,
                    sla_compliance BOOLEAN NOT NULL,
                    sla_breach_minutes REAL DEFAULT 0.0,
                    total_incidents INTEGER DEFAULT 0,
                    total_downtime_minutes REAL DEFAULT 0.0,
                    longest_incident_minutes REAL DEFAULT 0.0,
                    mean_time_to_recovery REAL DEFAULT 0.0,
                    avg_response_time REAL DEFAULT 0.0,
                    p95_response_time REAL DEFAULT 0.0,
                    p99_response_time REAL DEFAULT 0.0,
                    availability_grade TEXT DEFAULT 'F',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(component_id, period_start, period_type),
                    FOREIGN KEY (component_id) REFERENCES components (component_id)
                )
            """)
            
            # SLA breach log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sla_breaches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_id TEXT NOT NULL,
                    breach_start TEXT NOT NULL,
                    breach_end TEXT,
                    period_type TEXT NOT NULL,  -- 'month', 'year'
                    target_uptime REAL NOT NULL,
                    actual_uptime REAL NOT NULL,
                    breach_minutes REAL NOT NULL,
                    incident_count INTEGER NOT NULL,
                    severity TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (component_id) REFERENCES components (component_id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_checks_component_time ON health_checks(component_id, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_checks_status ON health_checks(status, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_component ON incidents(component_id, started_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_uptime_stats_component_period ON uptime_statistics(component_id, period_start, period_type)")
            
            conn.commit()
    
    def save_component_config(self, config: ComponentConfig):
        """Save component configuration"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO components
                (component_id, name, component_type, check_method, check_target,
                 check_interval, timeout, is_critical, sla_target, description, tags, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                config.component_id, config.name, config.component_type.value,
                config.check_method, config.check_target, config.check_interval,
                config.timeout, config.is_critical, config.sla_target,
                config.description, json.dumps(config.tags),
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()
    
    def store_health_check(self, result: HealthCheckResult):
        """Store health check result"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO health_checks
                (component_id, timestamp, status, response_time, check_method, success,
                 error_message, response_code, response_size, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.component_id, result.timestamp.isoformat(), result.status.value,
                result.response_time, result.check_method, result.success,
                result.error_message, result.response_code, result.response_size,
                json.dumps(result.metadata) if result.metadata else None
            ))
            conn.commit()
    
    def store_incident(self, incident: DowntimeIncident):
        """Store downtime incident"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO incidents
                (incident_id, component_id, started_at, ended_at, severity, title, description,
                 root_cause, duration_minutes, affected_users, revenue_impact, detected_at,
                 acknowledged_at, resolved_at, is_resolved, resolution_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                incident.incident_id, incident.component_id, incident.started_at.isoformat(),
                incident.ended_at.isoformat() if incident.ended_at else None,
                incident.severity.value, incident.title, incident.description,
                incident.root_cause, incident.duration_minutes, incident.affected_users,
                incident.revenue_impact,
                incident.detected_at.isoformat() if incident.detected_at else None,
                incident.acknowledged_at.isoformat() if incident.acknowledged_at else None,
                incident.resolved_at.isoformat() if incident.resolved_at else None,
                incident.is_resolved, incident.resolution_notes
            ))
            conn.commit()
    
    def get_recent_health_checks(self, component_id: str, hours: int = 24) -> List[HealthCheckResult]:
        """Get recent health checks for a component"""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT component_id, timestamp, status, response_time, check_method,
                       success, error_message, response_code, response_size, metadata
                FROM health_checks
                WHERE component_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (component_id, since.isoformat()))
            
            results = []
            for row in cursor.fetchall():
                metadata = json.loads(row[9]) if row[9] else {}
                
                result = HealthCheckResult(
                    component_id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    status=ComponentStatus(row[2]),
                    response_time=row[3],
                    check_method=row[4],
                    success=row[5],
                    error_message=row[6],
                    response_code=row[7],
                    response_size=row[8],
                    metadata=metadata
                )
                results.append(result)
            
            return results


class UptimeAnalyzer:
    """Analyzes uptime data and calculates statistics"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sla_target = config.get('default_sla_target', 99.9)
    
    def calculate_uptime_statistics(self, component_id: str,
                                   health_checks: List[HealthCheckResult],
                                   incidents: List[DowntimeIncident]) -> UptimeStatistics:
        """Calculate uptime statistics for a component"""
        
        if not health_checks:
            # Return empty statistics
            return UptimeStatistics(
                component_id=component_id,
                period_start=datetime.now(timezone.utc),
                period_end=datetime.now(timezone.utc),
                total_checks=0,
                successful_checks=0,
                failed_checks=0,
                uptime_percentage=0.0,
                sla_target=self.sla_target,
                sla_compliance=False,
                sla_breach_minutes=0.0,
                total_incidents=0,
                total_downtime_minutes=0.0,
                longest_incident_minutes=0.0,
                mean_time_to_recovery=0.0,
                avg_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                availability_grade="F"
            )
        
        # Basic counts
        total_checks = len(health_checks)
        successful_checks = len([c for c in health_checks if c.success])
        failed_checks = total_checks - successful_checks
        
        # Uptime percentage
        uptime_percentage = (successful_checks / total_checks) * 100 if total_checks > 0 else 0.0
        
        # Time period
        period_start = min(c.timestamp for c in health_checks)
        period_end = max(c.timestamp for c in health_checks)
        
        # SLA compliance
        sla_compliance = uptime_percentage >= self.sla_target
        sla_breach_minutes = self._calculate_sla_breach_minutes(
            period_start, period_end, uptime_percentage, self.sla_target
        )
        
        # Incident analysis
        total_incidents = len(incidents)
        total_downtime_minutes = sum(i.duration_minutes for i in incidents if i.duration_minutes)
        longest_incident_minutes = max((i.duration_minutes for i in incidents if i.duration_minutes), default=0.0)
        
        # Mean time to recovery
        recovery_times = [i.duration_minutes for i in incidents if i.duration_minutes and i.is_resolved]
        mean_time_to_recovery = statistics.mean(recovery_times) if recovery_times else 0.0
        
        # Response time analysis
        response_times = [c.response_time for c in health_checks if c.success]
        avg_response_time = statistics.mean(response_times) if response_times else 0.0
        p95_response_time = self._percentile(sorted(response_times), 95) if response_times else 0.0
        p99_response_time = self._percentile(sorted(response_times), 99) if response_times else 0.0
        
        # Availability grade
        availability_grade = self._calculate_availability_grade(uptime_percentage, total_incidents, longest_incident_minutes)
        
        return UptimeStatistics(
            component_id=component_id,
            period_start=period_start,
            period_end=period_end,
            total_checks=total_checks,
            successful_checks=successful_checks,
            failed_checks=failed_checks,
            uptime_percentage=uptime_percentage,
            sla_target=self.sla_target,
            sla_compliance=sla_compliance,
            sla_breach_minutes=sla_breach_minutes,
            total_incidents=total_incidents,
            total_downtime_minutes=total_downtime_minutes,
            longest_incident_minutes=longest_incident_minutes,
            mean_time_to_recovery=mean_time_to_recovery,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            availability_grade=availability_grade
        )
    
    def _calculate_sla_breach_minutes(self, period_start: datetime, period_end: datetime,
                                    actual_uptime: float, target_uptime: float) -> float:
        """Calculate SLA breach minutes"""
        
        if actual_uptime >= target_uptime:
            return 0.0
        
        period_minutes = (period_end - period_start).total_seconds() / 60
        target_minutes = period_minutes * (target_uptime / 100)
        actual_minutes = period_minutes * (actual_uptime / 100)
        
        return max(target_minutes - actual_minutes, 0.0)
    
    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile of sorted values"""
        if not sorted_values:
            return 0.0
        
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1] if int(index) + 1 < len(sorted_values) else lower
            fraction = index - int(index)
            return lower + fraction * (upper - lower)
    
    def _calculate_availability_grade(self, uptime_percentage: float, 
                                    incident_count: int, longest_incident: float) -> str:
        """Calculate availability grade A-F"""
        
        grade_score = 0
        
        # Uptime percentage factor (60% weight)
        if uptime_percentage >= 99.95:
            grade_score += 60
        elif uptime_percentage >= 99.9:
            grade_score += 50
        elif uptime_percentage >= 99.5:
            grade_score += 40
        elif uptime_percentage >= 99.0:
            grade_score += 30
        elif uptime_percentage >= 95.0:
            grade_score += 20
        else:
            grade_score += 0
        
        # Incident frequency factor (25% weight)
        if incident_count == 0:
            grade_score += 25
        elif incident_count <= 2:
            grade_score += 20
        elif incident_count <= 5:
            grade_score += 15
        elif incident_count <= 10:
            grade_score += 10
        else:
            grade_score += 0
        
        # Longest incident factor (15% weight)
        if longest_incident == 0:
            grade_score += 15
        elif longest_incident <= 5:  # 5 minutes
            grade_score += 12
        elif longest_incident <= 15:  # 15 minutes
            grade_score += 8
        elif longest_incident <= 60:  # 1 hour
            grade_score += 5
        else:
            grade_score += 0
        
        # Convert to letter grade
        if grade_score >= 90:
            return "A"
        elif grade_score >= 80:
            return "B"
        elif grade_score >= 70:
            return "C"
        elif grade_score >= 60:
            return "D"
        else:
            return "F"


class UptimeMonitor:
    """
    Main uptime monitoring system
    
    Features:
    - Continuous health monitoring of system components
    - Real-time incident detection and tracking
    - SLA compliance monitoring and reporting
    - Automated alerting for downtime events
    - Historical uptime analysis and trending
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize uptime monitor
        
        Args:
            config: Monitor configuration
        """
        self.config = config
        self.database = UptimeDatabase(config.get('db_path', 'outputs/uptime_monitoring.db'))
        self.health_checker = HealthChecker(config.get('health_checks', {}))
        self.analyzer = UptimeAnalyzer(config.get('analysis', {}))
        
        # Component management
        self.components: Dict[str, ComponentConfig] = {}
        self.component_lock = threading.Lock()
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor_threads: Dict[str, threading.Thread] = {}
        
        # Incident tracking
        self.active_incidents: Dict[str, DowntimeIncident] = {}
        self.incident_lock = threading.Lock()
        
        # Component status tracking
        self.component_status: Dict[str, ComponentStatus] = {}
        self.last_status_change: Dict[str, datetime] = {}
        self.consecutive_failures: Dict[str, int] = defaultdict(int)
        
        # Callbacks
        self.on_component_down: Optional[Callable[[str, HealthCheckResult], None]] = None
        self.on_component_up: Optional[Callable[[str, HealthCheckResult], None]] = None
        self.on_incident_created: Optional[Callable[[DowntimeIncident], None]] = None
        self.on_incident_resolved: Optional[Callable[[DowntimeIncident], None]] = None
        self.on_sla_breach: Optional[Callable[[str, float, float], None]] = None
        
        logger.info("Uptime Monitor initialized")
    
    def add_component(self, config: ComponentConfig):
        """Add a component to monitor"""
        
        with self.component_lock:
            self.components[config.component_id] = config
            self.component_status[config.component_id] = ComponentStatus.UNKNOWN
        
        # Save to database
        self.database.save_component_config(config)
        
        logger.info(f"Added component for monitoring: {config.name} ({config.component_id})")
    
    def remove_component(self, component_id: str):
        """Remove a component from monitoring"""
        
        with self.component_lock:
            if component_id in self.components:
                del self.components[component_id]
                self.component_status.pop(component_id, None)
                self.last_status_change.pop(component_id, None)
                self.consecutive_failures.pop(component_id, None)
        
        logger.info(f"Removed component from monitoring: {component_id}")
    
    def start_monitoring(self):
        """Start monitoring all components"""
        
        if self.monitoring_active:
            logger.warning("Uptime monitoring already active")
            return
        
        self.monitoring_active = True
        
        # Start monitoring thread for each component
        with self.component_lock:
            for component_id, config in self.components.items():
                thread = threading.Thread(
                    target=self._monitor_component,
                    args=(component_id, config),
                    daemon=True,
                    name=f"UptimeMonitor-{component_id}"
                )
                thread.start()
                self.monitor_threads[component_id] = thread
        
        logger.info(f"Started uptime monitoring for {len(self.components)} components")
    
    def stop_monitoring(self):
        """Stop monitoring all components"""
        
        self.monitoring_active = False
        
        # Wait for monitor threads to finish
        for thread in self.monitor_threads.values():
            if thread.is_alive():
                thread.join(timeout=5)
        
        self.monitor_threads.clear()
        
        logger.info("Stopped uptime monitoring")
    
    def _monitor_component(self, component_id: str, config: ComponentConfig):
        """Monitor individual component"""
        
        while self.monitoring_active:
            try:
                # Perform health check
                result = self.health_checker.check_component(config)
                
                # Store result
                self.database.store_health_check(result)
                
                # Update component status
                self._update_component_status(component_id, result)
                
                # Sleep until next check
                time.sleep(config.check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring component {component_id}: {e}")
                time.sleep(30)  # Short sleep on error
    
    def _update_component_status(self, component_id: str, result: HealthCheckResult):
        """Update component status and handle state changes"""
        
        previous_status = self.component_status.get(component_id, ComponentStatus.UNKNOWN)
        current_status = result.status
        
        # Update status
        self.component_status[component_id] = current_status
        
        # Track consecutive failures
        if result.success:
            self.consecutive_failures[component_id] = 0
        else:
            self.consecutive_failures[component_id] += 1
        
        # Handle status changes
        if previous_status != current_status:
            self.last_status_change[component_id] = result.timestamp
            
            if current_status == ComponentStatus.DOWN:
                self._handle_component_down(component_id, result)
            elif current_status == ComponentStatus.UP and previous_status == ComponentStatus.DOWN:
                self._handle_component_up(component_id, result)
        
        # Check for incident creation/resolution
        config = self.components[component_id]
        
        if (current_status == ComponentStatus.DOWN and 
            self.consecutive_failures[component_id] >= config.alert_after_failures):
            self._create_incident_if_needed(component_id, result)
        
        elif current_status == ComponentStatus.UP:
            self._resolve_incident_if_needed(component_id, result)
    
    def _handle_component_down(self, component_id: str, result: HealthCheckResult):
        """Handle component going down"""
        
        config = self.components[component_id]
        logger.warning(f"Component DOWN: {config.name} ({component_id}) - {result.error_message}")
        
        # Trigger callback
        if self.on_component_down:
            self.on_component_down(component_id, result)
    
    def _handle_component_up(self, component_id: str, result: HealthCheckResult):
        """Handle component coming back up"""
        
        config = self.components[component_id]
        logger.info(f"Component UP: {config.name} ({component_id})")
        
        # Trigger callback
        if self.on_component_up:
            self.on_component_up(component_id, result)
    
    def _create_incident_if_needed(self, component_id: str, result: HealthCheckResult):
        """Create downtime incident if needed"""
        
        with self.incident_lock:
            # Check if incident already exists
            if component_id in self.active_incidents:
                return
            
            config = self.components[component_id]
            
            # Create new incident
            incident_id = f"incident_{component_id}_{int(result.timestamp.timestamp())}"
            
            incident = DowntimeIncident(
                incident_id=incident_id,
                component_id=component_id,
                started_at=result.timestamp,
                severity=IncidentSeverity.HIGH if config.is_critical else IncidentSeverity.MEDIUM,
                title=f"{config.name} is down",
                description=f"Component {config.name} failed health check: {result.error_message}",
                detected_at=result.timestamp
            )
            
            self.active_incidents[component_id] = incident
            self.database.store_incident(incident)
            
            logger.error(f"INCIDENT CREATED: {incident_id} - {config.name} is down")
            
            # Trigger callback
            if self.on_incident_created:
                self.on_incident_created(incident)
    
    def _resolve_incident_if_needed(self, component_id: str, result: HealthCheckResult):
        """Resolve active incident if component is back up"""
        
        with self.incident_lock:
            if component_id not in self.active_incidents:
                return
            
            incident = self.active_incidents[component_id]
            
            # Mark incident as resolved
            incident.ended_at = result.timestamp
            incident.is_resolved = True
            incident.resolved_at = result.timestamp
            incident.calculate_duration()
            incident.resolution_notes = "Component health check successful"
            
            # Store updated incident
            self.database.store_incident(incident)
            
            # Remove from active incidents
            del self.active_incidents[component_id]
            
            logger.info(f"INCIDENT RESOLVED: {incident.incident_id} - Duration: {incident.duration_minutes:.1f} minutes")
            
            # Trigger callback
            if self.on_incident_resolved:
                self.on_incident_resolved(incident)
    
    def get_component_status(self, component_id: str) -> Dict[str, Any]:
        """Get current status of a component"""
        
        if component_id not in self.components:
            return {'error': 'Component not found'}
        
        config = self.components[component_id]
        status = self.component_status.get(component_id, ComponentStatus.UNKNOWN)
        last_change = self.last_status_change.get(component_id)
        consecutive_failures = self.consecutive_failures.get(component_id, 0)
        
        # Get recent health checks
        recent_checks = self.database.get_recent_health_checks(component_id, hours=1)
        
        # Calculate uptime for last 24 hours
        daily_checks = self.database.get_recent_health_checks(component_id, hours=24)
        daily_stats = self.analyzer.calculate_uptime_statistics(component_id, daily_checks, [])
        
        return {
            'component_id': component_id,
            'name': config.name,
            'type': config.component_type.value,
            'current_status': status.value,
            'last_status_change': last_change.isoformat() if last_change else None,
            'consecutive_failures': consecutive_failures,
            'is_critical': config.is_critical,
            'sla_target': config.sla_target,
            'recent_checks': len(recent_checks),
            'daily_uptime': daily_stats.uptime_percentage,
            'daily_sla_compliance': daily_stats.sla_compliance,
            'avg_response_time': daily_stats.avg_response_time,
            'active_incident': component_id in self.active_incidents
        }
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get overview of entire system uptime"""
        
        overview = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_components': len(self.components),
            'components_up': 0,
            'components_down': 0,
            'components_degraded': 0,
            'critical_components_down': 0,
            'active_incidents': len(self.active_incidents),
            'overall_health': 'unknown',
            'sla_compliance': True,
            'components': {}
        }
        
        # Analyze each component
        for component_id, config in self.components.items():
            status = self.component_status.get(component_id, ComponentStatus.UNKNOWN)
            
            # Count by status
            if status == ComponentStatus.UP:
                overview['components_up'] += 1
            elif status == ComponentStatus.DOWN:
                overview['components_down'] += 1
                if config.is_critical:
                    overview['critical_components_down'] += 1
            elif status == ComponentStatus.DEGRADED:
                overview['components_degraded'] += 1
            
            # Get component details
            overview['components'][component_id] = self.get_component_status(component_id)
            
            # Check SLA compliance
            if not overview['components'][component_id]['daily_sla_compliance']:
                overview['sla_compliance'] = False
        
        # Determine overall health
        if overview['critical_components_down'] > 0:
            overview['overall_health'] = 'critical'
        elif overview['components_down'] > 0:
            overview['overall_health'] = 'degraded'
        elif overview['components_degraded'] > 0:
            overview['overall_health'] = 'warning'
        elif overview['components_up'] == overview['total_components']:
            overview['overall_health'] = 'healthy'
        else:
            overview['overall_health'] = 'unknown'
        
        return overview
    
    def generate_uptime_report(self, component_id: Optional[str] = None, 
                              days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive uptime report"""
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        report = {
            'report_period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'days': days
            },
            'sla_target': 99.9,
            'components': {},
            'overall_summary': {},
            'sla_breaches': [],
            'recommendations': []
        }
        
        # Analyze specific component or all components
        components_to_analyze = [component_id] if component_id else list(self.components.keys())
        
        all_stats = []
        
        for comp_id in components_to_analyze:
            if comp_id not in self.components:
                continue
            
            # Get health checks and incidents
            health_checks = self.database.get_recent_health_checks(comp_id, hours=days * 24)
            incidents = []  # Would load from database
            
            # Calculate statistics
            stats = self.analyzer.calculate_uptime_statistics(comp_id, health_checks, incidents)
            
            report['components'][comp_id] = asdict(stats)
            all_stats.append(stats)
        
        # Generate overall summary
        if all_stats:
            total_uptime = statistics.mean([s.uptime_percentage for s in all_stats])
            total_incidents = sum(s.total_incidents for s in all_stats)
            total_downtime = sum(s.total_downtime_minutes for s in all_stats)
            
            critical_components = [s for s in all_stats if self.components[s.component_id].is_critical]
            critical_sla_compliance = all(s.sla_compliance for s in critical_components)
            
            report['overall_summary'] = {
                'overall_uptime_percentage': total_uptime,
                'total_incidents': total_incidents,
                'total_downtime_minutes': total_downtime,
                'critical_sla_compliance': critical_sla_compliance,
                'components_analyzed': len(all_stats)
            }
            
            # Generate recommendations
            report['recommendations'] = self._generate_uptime_recommendations(all_stats)
        
        return report
    
    def _generate_uptime_recommendations(self, stats_list: List[UptimeStatistics]) -> List[str]:
        """Generate uptime improvement recommendations"""
        
        recommendations = []
        
        # Check for components with poor uptime
        poor_uptime = [s for s in stats_list if s.uptime_percentage < 99.5]
        if poor_uptime:
            recommendations.append(f"{len(poor_uptime)} components have uptime below 99.5% - investigate reliability issues")
        
        # Check for frequent incidents
        high_incident_components = [s for s in stats_list if s.total_incidents > 10]
        if high_incident_components:
            recommendations.append(f"{len(high_incident_components)} components have >10 incidents - improve stability")
        
        # Check for long incidents
        long_incident_components = [s for s in stats_list if s.longest_incident_minutes > 60]
        if long_incident_components:
            recommendations.append(f"{len(long_incident_components)} components had incidents >1 hour - improve recovery procedures")
        
        # Check response times
        slow_components = [s for s in stats_list if s.avg_response_time > 5.0]
        if slow_components:
            recommendations.append(f"{len(slow_components)} components have slow response times - optimize performance")
        
        # SLA compliance
        sla_breaches = [s for s in stats_list if not s.sla_compliance]
        if sla_breaches:
            recommendations.append(f"{len(sla_breaches)} components failed SLA targets - critical attention required")
        
        if not recommendations:
            recommendations.append("System uptime is meeting all targets - maintain current practices")
        
        return recommendations


def create_uptime_monitor(config: Optional[Dict] = None) -> UptimeMonitor:
    """Factory function to create uptime monitor"""
    
    if config is None:
        config = {
            'db_path': 'outputs/uptime_monitoring.db',
            'health_checks': {
                'default_timeout': 10
            },
            'analysis': {
                'default_sla_target': 99.9
            }
        }
    
    return config


if __name__ == "__main__":
    # Example usage
    monitor = create_uptime_monitor()
    
    def on_component_down(component_id: str, result: HealthCheckResult):
        print(f"🚨 COMPONENT DOWN: {component_id} - {result.error_message}")
    
    def on_component_up(component_id: str, result: HealthCheckResult):
        print(f"✅ COMPONENT UP: {component_id}")
    
    def on_incident_created(incident: DowntimeIncident):
        print(f"🔥 INCIDENT: {incident.title} ({incident.severity.value})")
    
    def on_incident_resolved(incident: DowntimeIncident):
        print(f"✅ RESOLVED: {incident.title} - {incident.duration_minutes:.1f} minutes")
    
    monitor.on_component_down = on_component_down
    monitor.on_component_up = on_component_up
    monitor.on_incident_created = on_incident_created
    monitor.on_incident_resolved = on_incident_resolved
    
    # Add some components to monitor
    print("=== Uptime Monitor Test ===")
    
    # Add test components
    components = [
        ComponentConfig(
            component_id="web_api",
            name="Web API Service",
            component_type=ComponentType.WEB_SERVICE,
            check_method="http",
            check_target="http://localhost:8080/health",
            check_interval=30,
            is_critical=True
        ),
        ComponentConfig(
            component_id="database",
            name="Main Database",
            component_type=ComponentType.DATABASE,
            check_method="tcp",
            check_target="localhost:5432",
            check_interval=30,
            is_critical=True
        ),
        ComponentConfig(
            component_id="data_feed",
            name="Market Data Feed",
            component_type=ComponentType.DATA_FEED,
            check_method="ping",
            check_target="8.8.8.8",  # Using Google DNS as test
            check_interval=30,
            is_critical=True
        )
    ]
    
    for component in components:
        monitor.add_component(component)
        print(f"✓ Added component: {component.name}")
    
    # Start monitoring
    monitor.start_monitoring()
    print("✓ Uptime monitoring started")
    
    # Run for a while to collect data
    print("\nCollecting uptime data for 60 seconds...")
    time.sleep(60)
    
    # Get system overview
    overview = monitor.get_system_overview()
    print(f"\nSystem Overview:")
    print(f"  Overall Health: {overview['overall_health']}")
    print(f"  Components Up: {overview['components_up']}/{overview['total_components']}")
    print(f"  Active Incidents: {overview['active_incidents']}")
    print(f"  SLA Compliance: {overview['sla_compliance']}")
    
    # Component details
    for comp_id, details in overview['components'].items():
        print(f"\n  {details['name']}:")
        print(f"    Status: {details['current_status']}")
        print(f"    24h Uptime: {details['daily_uptime']:.2f}%")
        print(f"    Avg Response: {details['avg_response_time']:.3f}s")
        print(f"    SLA Compliant: {details['daily_sla_compliance']}")
    
    # Generate uptime report
    report = monitor.generate_uptime_report(days=1)
    
    if report['overall_summary']:
        print(f"\nUptime Report (24 hours):")
        summary = report['overall_summary']
        print(f"  Overall Uptime: {summary['overall_uptime_percentage']:.3f}%")
        print(f"  Total Incidents: {summary['total_incidents']}")
        print(f"  Total Downtime: {summary['total_downtime_minutes']:.1f} minutes")
        print(f"  Critical SLA Compliance: {summary['critical_sla_compliance']}")
    
    if report['recommendations']:
        print(f"\nRecommendations:")
        for rec in report['recommendations']:
            print(f"  - {rec}")
    
    monitor.stop_monitoring()
    print("\n✓ Uptime monitoring stopped")