#!/usr/bin/env python3
"""
Security Monitoring System for IFD v3.0 Trading System

Monitors and alerts on security events including:
- API authentication failures
- Data access auditing
- Intrusion detection
- Unusual access patterns
- Credential compromise detection
- Rate limit violations
"""

import json
import time
import logging
import hashlib
import ipaddress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import sys
import os
import re

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
from utils.timezone_utils import get_eastern_time

@dataclass
class SecurityEvent:
    """Security event data structure"""
    id: str
    event_type: str  # auth_failure, data_access, intrusion_attempt, rate_limit_exceeded
    severity: str   # LOW, MEDIUM, HIGH, CRITICAL
    timestamp: str
    source_ip: str
    user_agent: str
    endpoint: str
    user_id: Optional[str]
    api_key_hash: Optional[str]
    event_details: Dict[str, Any]
    risk_score: int  # 0-100

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SecurityMetrics:
    """Security metrics tracking"""
    failed_auth_attempts: int = 0
    successful_auth_attempts: int = 0
    data_access_events: int = 0
    suspicious_activity_events: int = 0
    blocked_ips: int = 0
    rate_limit_violations: int = 0
    last_intrusion_attempt: Optional[str] = None
    high_risk_events_24h: int = 0

class SecurityMonitor:
    """Comprehensive security monitoring system"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/security_monitoring.json"
        self.events_file = "outputs/monitoring/security_events.json"
        self.metrics_file = "outputs/monitoring/security_metrics.json"
        self.blocked_ips_file = "outputs/monitoring/blocked_ips.json"

        # Ensure directories exist
        os.makedirs("outputs/monitoring", exist_ok=True)

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Load configuration
        self.config = self._load_config()

        # Security tracking
        self.recent_events: deque = deque(maxlen=1000)
        self.metrics = SecurityMetrics()
        self.blocked_ips: Set[str] = set()
        self.failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self.rate_limiters: Dict[str, deque] = defaultdict(deque)
        self.suspicious_patterns: Dict[str, int] = defaultdict(int)

        # Load existing data
        self._load_existing_data()

        # Initialize alert system if available
        try:
            from .alert_system import AlertSystem
            self.alert_system = AlertSystem()
        except ImportError:
            self.alert_system = None
            self.logger.warning("Alert system not available")

    def _load_config(self) -> Dict[str, Any]:
        """Load security monitoring configuration"""
        default_config = {
            "thresholds": {
                "failed_auth_attempts_per_hour": 10,
                "failed_auth_attempts_per_day": 50,
                "max_requests_per_minute": 100,
                "max_requests_per_hour": 1000,
                "suspicious_user_agent_patterns": [
                    "curl", "wget", "python-requests", "bot", "scanner"
                ],
                "blocked_ip_duration_hours": 24,
                "max_data_access_per_hour": 500
            },
            "monitoring": {
                "track_api_calls": True,
                "track_data_access": True,
                "track_failed_auth": True,
                "track_rate_limits": True,
                "log_successful_auth": False,
                "geo_location_tracking": False
            },
            "response": {
                "auto_block_ips": True,
                "alert_on_intrusion": True,
                "alert_on_repeated_failures": True,
                "quarantine_suspicious_users": False
            },
            "whitelist": {
                "trusted_ips": ["127.0.0.1", "::1"],
                "service_accounts": [],
                "internal_networks": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
            }
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            except Exception as e:
                self.logger.warning(f"Error loading security config: {e}. Using defaults.")

        return default_config

    def _load_existing_data(self):
        """Load existing security data"""
        # Load blocked IPs
        if os.path.exists(self.blocked_ips_file):
            try:
                with open(self.blocked_ips_file, 'r') as f:
                    blocked_data = json.load(f)
                    current_time = get_eastern_time()
                    duration_hours = self.config["thresholds"]["blocked_ip_duration_hours"]

                    for ip, blocked_time_str in blocked_data.items():
                        blocked_time = datetime.fromisoformat(blocked_time_str)
                        if current_time - blocked_time < timedelta(hours=duration_hours):
                            self.blocked_ips.add(ip)
            except Exception as e:
                self.logger.warning(f"Error loading blocked IPs: {e}")

        # Load recent events
        if os.path.exists(self.events_file):
            try:
                with open(self.events_file, 'r') as f:
                    events_data = json.load(f)
                    for event_data in events_data[-100:]:  # Load last 100 events
                        event = SecurityEvent(**event_data)
                        self.recent_events.append(event)
            except Exception as e:
                self.logger.warning(f"Error loading security events: {e}")

    def log_auth_attempt(self,
                        success: bool,
                        source_ip: str,
                        user_agent: str = "",
                        api_key: str = "",
                        user_id: str = "",
                        endpoint: str = "",
                        additional_details: Optional[Dict[str, Any]] = None) -> Optional[SecurityEvent]:
        """Log authentication attempt and check for security issues"""

        # Check if IP is blocked
        if source_ip in self.blocked_ips:
            return self._create_security_event(
                event_type="blocked_ip_attempt",
                severity="HIGH",
                source_ip=source_ip,
                user_agent=user_agent,
                endpoint=endpoint,
                event_details={"reason": "IP is blocked", "api_key_hash": self._hash_api_key(api_key)}
            )

        if success:
            self.metrics.successful_auth_attempts += 1

            # Log successful auth if configured
            if self.config["monitoring"]["log_successful_auth"]:
                return self._create_security_event(
                    event_type="auth_success",
                    severity="LOW",
                    source_ip=source_ip,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    user_id=user_id,
                    api_key_hash=self._hash_api_key(api_key),
                    event_details=additional_details or {}
                )
        else:
            self.metrics.failed_auth_attempts += 1

            # Track failed attempts by IP
            current_time = get_eastern_time()
            self.failed_attempts[source_ip].append(current_time)

            # Clean old failed attempts (keep last 24 hours)
            cutoff_time = current_time - timedelta(hours=24)
            self.failed_attempts[source_ip] = [
                attempt for attempt in self.failed_attempts[source_ip]
                if attempt > cutoff_time
            ]

            # Check for brute force attack
            recent_failures = len(self.failed_attempts[source_ip])
            severity = self._calculate_auth_failure_severity(recent_failures, source_ip)

            # Auto-block IP if threshold exceeded
            if (recent_failures >= self.config["thresholds"]["failed_auth_attempts_per_hour"]
                and self.config["response"]["auto_block_ips"]):
                self._block_ip(source_ip, "Excessive failed authentication attempts")

            return self._create_security_event(
                event_type="auth_failure",
                severity=severity,
                source_ip=source_ip,
                user_agent=user_agent,
                endpoint=endpoint,
                user_id=user_id,
                api_key_hash=self._hash_api_key(api_key),
                event_details={
                    "recent_failures": recent_failures,
                    "failure_reason": additional_details.get("reason", "Invalid credentials") if additional_details else "Invalid credentials"
                }
            )

    def log_data_access(self,
                       endpoint: str,
                       source_ip: str,
                       user_agent: str = "",
                       user_id: str = "",
                       api_key: str = "",
                       data_type: str = "",
                       record_count: int = 0,
                       sensitive_data: bool = False) -> Optional[SecurityEvent]:
        """Log data access event and check for unusual patterns"""

        if not self.config["monitoring"]["track_data_access"]:
            return None

        self.metrics.data_access_events += 1

        # Check for unusual access patterns
        risk_score = self._calculate_data_access_risk(
            endpoint=endpoint,
            source_ip=source_ip,
            user_agent=user_agent,
            data_type=data_type,
            record_count=record_count,
            sensitive_data=sensitive_data
        )

        severity = "LOW"
        if risk_score > 70:
            severity = "CRITICAL"
        elif risk_score > 50:
            severity = "HIGH"
        elif risk_score > 30:
            severity = "MEDIUM"

        return self._create_security_event(
            event_type="data_access",
            severity=severity,
            source_ip=source_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            user_id=user_id,
            api_key_hash=self._hash_api_key(api_key),
            event_details={
                "data_type": data_type,
                "record_count": record_count,
                "sensitive_data": sensitive_data,
                "risk_score": risk_score
            },
            risk_score=risk_score
        )

    def log_rate_limit_violation(self,
                                source_ip: str,
                                endpoint: str,
                                user_agent: str = "",
                                request_count: int = 0,
                                time_window: str = "minute") -> SecurityEvent:
        """Log rate limit violation"""

        self.metrics.rate_limit_violations += 1

        # Check if this is part of a pattern
        pattern_key = f"{source_ip}:{endpoint}"
        self.suspicious_patterns[pattern_key] += 1

        severity = "MEDIUM"
        if self.suspicious_patterns[pattern_key] > 5:
            severity = "HIGH"

        return self._create_security_event(
            event_type="rate_limit_exceeded",
            severity=severity,
            source_ip=source_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            event_details={
                "request_count": request_count,
                "time_window": time_window,
                "violation_count": self.suspicious_patterns[pattern_key]
            }
        )

    def detect_intrusion_attempt(self,
                                source_ip: str,
                                user_agent: str = "",
                                endpoint: str = "",
                                request_details: Optional[Dict[str, Any]] = None) -> Optional[SecurityEvent]:
        """Detect potential intrusion attempts"""

        risk_indicators = []
        risk_score = 0

        # Check suspicious user agent
        suspicious_agents = self.config["thresholds"]["suspicious_user_agent_patterns"]
        for pattern in suspicious_agents:
            if pattern.lower() in user_agent.lower():
                risk_indicators.append(f"Suspicious user agent: {pattern}")
                risk_score += 20

        # Check for SQL injection patterns
        if request_details:
            sql_patterns = [r"union.*select", r"drop.*table", r"insert.*into", r"'.*or.*'.*=.*'"]
            for pattern in sql_patterns:
                for value in str(request_details.values()):
                    if re.search(pattern, value, re.IGNORECASE):
                        risk_indicators.append(f"SQL injection pattern: {pattern}")
                        risk_score += 30

        # Check for path traversal
        if "../" in endpoint or "..%2f" in endpoint.lower():
            risk_indicators.append("Path traversal attempt")
            risk_score += 25

        # Check for scanner behavior
        if endpoint.endswith(('.php', '.asp', '.jsp', '.cgi')):
            risk_indicators.append("Scanner-like behavior")
            risk_score += 15

        # Check IP reputation (simplified)
        if self._is_suspicious_ip(source_ip):
            risk_indicators.append("Suspicious IP address")
            risk_score += 20

        if risk_score > 30:  # Threshold for intrusion attempt
            severity = "CRITICAL" if risk_score > 70 else "HIGH"

            # Auto-block highly suspicious IPs
            if risk_score > 70 and self.config["response"]["auto_block_ips"]:
                self._block_ip(source_ip, "Intrusion attempt detected")

            return self._create_security_event(
                event_type="intrusion_attempt",
                severity=severity,
                source_ip=source_ip,
                user_agent=user_agent,
                endpoint=endpoint,
                event_details={
                    "risk_indicators": risk_indicators,
                    "risk_score": risk_score,
                    "request_details": request_details
                },
                risk_score=risk_score
            )

        return None

    def _create_security_event(self,
                              event_type: str,
                              severity: str,
                              source_ip: str,
                              user_agent: str = "",
                              endpoint: str = "",
                              user_id: Optional[str] = None,
                              api_key_hash: Optional[str] = None,
                              event_details: Optional[Dict[str, Any]] = None,
                              risk_score: int = 0) -> SecurityEvent:
        """Create and process security event"""

        event_id = self._generate_event_id(event_type, source_ip, endpoint)

        event = SecurityEvent(
            id=event_id,
            event_type=event_type,
            severity=severity,
            timestamp=get_eastern_time().isoformat(),
            source_ip=source_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            user_id=user_id,
            api_key_hash=api_key_hash,
            event_details=event_details or {},
            risk_score=risk_score
        )

        # Store event
        self.recent_events.append(event)

        # Update metrics
        if severity in ["HIGH", "CRITICAL"]:
            self.metrics.high_risk_events_24h += 1

        # Send alerts if configured
        if self.alert_system and severity in ["HIGH", "CRITICAL"]:
            self._send_security_alert(event)

        # Save to storage
        self._save_security_data()

        self.logger.warning(f"Security event: [{severity}] {event_type} from {source_ip}")
        return event

    def _calculate_auth_failure_severity(self, failure_count: int, source_ip: str) -> str:
        """Calculate severity of authentication failure"""
        if failure_count >= 20:
            return "CRITICAL"
        elif failure_count >= 10:
            return "HIGH"
        elif failure_count >= 5:
            return "MEDIUM"
        else:
            return "LOW"

    def _calculate_data_access_risk(self,
                                  endpoint: str,
                                  source_ip: str,
                                  user_agent: str,
                                  data_type: str,
                                  record_count: int,
                                  sensitive_data: bool) -> int:
        """Calculate risk score for data access"""
        risk_score = 0

        # Base score for sensitive data
        if sensitive_data:
            risk_score += 30

        # Large data access
        if record_count > 1000:
            risk_score += 20
        elif record_count > 100:
            risk_score += 10

        # Unusual endpoint access
        if endpoint.endswith("/admin") or "admin" in endpoint:
            risk_score += 25

        # Check for bulk data endpoints
        if any(pattern in endpoint.lower() for pattern in ["export", "dump", "backup", "all"]):
            risk_score += 20

        # Time-based risk (after hours access)
        current_time = get_eastern_time()
        if current_time.hour < 6 or current_time.hour > 22:
            risk_score += 15

        # Check if IP is from expected location (simplified)
        if not self._is_trusted_ip(source_ip):
            risk_score += 10

        return min(risk_score, 100)  # Cap at 100

    def _is_suspicious_ip(self, ip: str) -> bool:
        """Check if IP is suspicious (simplified implementation)"""
        try:
            ip_obj = ipaddress.ip_address(ip)

            # Check for known suspicious ranges (simplified)
            suspicious_ranges = [
                "185.220.100.0/22",  # Tor exit nodes (example)
                "198.98.48.0/20"     # VPN ranges (example)
            ]

            for range_str in suspicious_ranges:
                if ip_obj in ipaddress.ip_network(range_str):
                    return True

            return False
        except:
            return True  # Invalid IP format is suspicious

    def _is_trusted_ip(self, ip: str) -> bool:
        """Check if IP is in trusted ranges"""
        try:
            ip_obj = ipaddress.ip_address(ip)

            # Check whitelist
            for trusted_ip in self.config["whitelist"]["trusted_ips"]:
                if ip == trusted_ip:
                    return True

            # Check internal networks
            for network_str in self.config["whitelist"]["internal_networks"]:
                if ip_obj in ipaddress.ip_network(network_str):
                    return True

            return False
        except:
            return False

    def _block_ip(self, ip: str, reason: str):
        """Block an IP address"""
        self.blocked_ips.add(ip)
        self.metrics.blocked_ips += 1

        # Store block time for expiration
        block_data = {ip: get_eastern_time().isoformat()}

        if os.path.exists(self.blocked_ips_file):
            try:
                with open(self.blocked_ips_file, 'r') as f:
                    existing_blocks = json.load(f)
                    block_data.update(existing_blocks)
            except:
                pass

        with open(self.blocked_ips_file, 'w') as f:
            json.dump(block_data, f, indent=2)

        self.logger.warning(f"IP blocked: {ip} - {reason}")

        # Send alert
        if self.alert_system:
            self.alert_system.create_alert(
                severity="HIGH",
                title=f"IP Address Blocked: {ip}",
                message=f"IP {ip} has been automatically blocked. Reason: {reason}",
                component="security_monitor",
                source="auto_block_system",
                tags=["security", "ip_block", "auto_response"],
                metadata={"blocked_ip": ip, "reason": reason}
            )

    def _send_security_alert(self, event: SecurityEvent):
        """Send security alert"""
        if not self.alert_system:
            return

        alert_title = f"Security Event: {event.event_type.replace('_', ' ').title()}"
        alert_message = f"Security event detected from {event.source_ip}\n\n"
        alert_message += f"Event Type: {event.event_type}\n"
        alert_message += f"Endpoint: {event.endpoint}\n"
        alert_message += f"User Agent: {event.user_agent}\n"

        if event.risk_score > 0:
            alert_message += f"Risk Score: {event.risk_score}/100\n"

        if event.event_details:
            alert_message += f"\nDetails:\n"
            for key, value in event.event_details.items():
                alert_message += f"  {key}: {value}\n"

        self.alert_system.create_alert(
            severity=event.severity,
            title=alert_title,
            message=alert_message,
            component="security_monitor",
            source="security_system",
            tags=["security", event.event_type],
            metadata=event.event_details
        )

    def _generate_event_id(self, event_type: str, source_ip: str, endpoint: str) -> str:
        """Generate unique event ID"""
        content = f"{event_type}:{source_ip}:{endpoint}:{int(time.time())}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for logging (keep first 8 chars visible)"""
        if not api_key:
            return ""
        if len(api_key) <= 8:
            return api_key
        return api_key[:8] + "..." + hashlib.sha256(api_key.encode()).hexdigest()[:8]

    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics summary"""
        current_time = get_eastern_time()
        last_24h = current_time - timedelta(hours=24)

        # Count recent events by type
        recent_events = [
            event for event in self.recent_events
            if datetime.fromisoformat(event.timestamp.replace('Z', '+00:00')) > last_24h
        ]

        events_by_type = defaultdict(int)
        events_by_severity = defaultdict(int)

        for event in recent_events:
            events_by_type[event.event_type] += 1
            events_by_severity[event.severity] += 1

        return {
            "timestamp": current_time.isoformat(),
            "metrics": asdict(self.metrics),
            "events_24h": {
                "total": len(recent_events),
                "by_type": dict(events_by_type),
                "by_severity": dict(events_by_severity)
            },
            "blocked_ips": {
                "count": len(self.blocked_ips),
                "list": list(self.blocked_ips)
            },
            "top_failed_ips": self._get_top_failed_ips(),
            "security_score": self._calculate_security_score()
        }

    def _get_top_failed_ips(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get top IPs with failed authentication attempts"""
        return sorted(
            [(ip, len(attempts)) for ip, attempts in self.failed_attempts.items()],
            key=lambda x: x[1],
            reverse=True
        )[:limit]

    def _calculate_security_score(self) -> int:
        """Calculate overall security score (0-100, higher is better)"""
        base_score = 100

        # Deduct for security events
        base_score -= min(self.metrics.high_risk_events_24h * 5, 30)
        base_score -= min(self.metrics.failed_auth_attempts * 2, 20)
        base_score -= min(len(self.blocked_ips) * 3, 15)
        base_score -= min(self.metrics.rate_limit_violations, 10)

        return max(base_score, 0)

    def _save_security_data(self):
        """Save security data to storage"""
        try:
            # Save recent events
            events_data = [event.to_dict() for event in list(self.recent_events)[-100:]]
            with open(self.events_file, 'w') as f:
                json.dump(events_data, f, indent=2)

            # Save metrics
            metrics_data = self.get_security_metrics()
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save security data: {e}")

# Integration helpers
def monitor_api_request(security_monitor: SecurityMonitor,
                       request_info: Dict[str, Any]) -> Optional[SecurityEvent]:
    """Monitor API request for security issues"""

    # Extract request information
    source_ip = request_info.get("remote_addr", "unknown")
    endpoint = request_info.get("path", "")
    user_agent = request_info.get("user_agent", "")
    method = request_info.get("method", "GET")

    # Check for intrusion attempt
    intrusion_event = security_monitor.detect_intrusion_attempt(
        source_ip=source_ip,
        user_agent=user_agent,
        endpoint=endpoint,
        request_details=request_info.get("args", {})
    )

    if intrusion_event:
        return intrusion_event

    # Log data access for sensitive endpoints
    sensitive_endpoints = ["/api/trading", "/api/positions", "/api/account"]
    if any(endpoint.startswith(path) for path in sensitive_endpoints):
        return security_monitor.log_data_access(
            endpoint=endpoint,
            source_ip=source_ip,
            user_agent=user_agent,
            data_type="trading_data",
            sensitive_data=True
        )

    return None

# Example usage
if __name__ == "__main__":
    # Create security monitor
    security_monitor = SecurityMonitor()

    print("Testing Security Monitor...")

    # Test authentication failure
    security_monitor.log_auth_attempt(
        success=False,
        source_ip="192.168.1.100",
        user_agent="Mozilla/5.0",
        api_key="db-test123",
        endpoint="/api/auth"
    )

    # Test data access
    security_monitor.log_data_access(
        endpoint="/api/trading/positions",
        source_ip="192.168.1.100",
        user_agent="curl/7.68.0",
        data_type="trading_positions",
        record_count=150,
        sensitive_data=True
    )

    # Test intrusion attempt
    security_monitor.detect_intrusion_attempt(
        source_ip="203.0.113.1",
        user_agent="sqlmap/1.0",
        endpoint="/api/admin",
        request_details={"query": "1' OR '1'='1"}
    )

    # Print security metrics
    metrics = security_monitor.get_security_metrics()
    print(f"\nSecurity Metrics:")
    print(f"Events in last 24h: {metrics['events_24h']['total']}")
    print(f"Blocked IPs: {metrics['blocked_ips']['count']}")
    print(f"Security Score: {metrics['security_score']}/100")
    print(f"Failed Auth Attempts: {metrics['metrics']['failed_auth_attempts']}")
