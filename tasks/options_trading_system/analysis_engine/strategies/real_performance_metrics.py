#!/usr/bin/env python3
"""
Real Performance Metrics for Shadow Trading

This module provides real performance measurement capabilities including:
- Actual API cost tracking from data providers
- Real latency measurement from live data feeds
- Data quality and completeness monitoring
- System resource usage tracking
"""

import time
import psutil
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import statistics

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LatencyMetrics:
    """Latency measurement data structure"""
    operation_type: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class CostMetrics:
    """API cost tracking data structure"""
    provider: str
    operation: str
    timestamp: datetime
    estimated_cost: float
    actual_cost: Optional[float] = None
    requests_count: int = 1
    data_volume_mb: float = 0.0


@dataclass
class DataQualityMetrics:
    """Data quality and completeness metrics"""
    source: str
    timestamp: datetime
    total_expected_records: int
    actual_records: int
    completeness_pct: float
    latency_ms: float
    error_count: int
    quality_score: float


@dataclass
class SystemResourceMetrics:
    """System resource usage metrics"""
    timestamp: datetime
    cpu_usage_pct: float
    memory_usage_pct: float
    disk_usage_pct: float
    network_io_mb: float
    process_count: int


class RealLatencyMonitor:
    """Real-time latency monitoring for all system operations"""

    def __init__(self, max_history: int = 1000):
        """
        Initialize latency monitor

        Args:
            max_history: Maximum number of latency records to keep
        """
        self.max_history = max_history
        self.latency_history: deque = deque(maxlen=max_history)
        self.operation_stats = defaultdict(list)

    def start_operation(self, operation_type: str) -> str:
        """
        Start timing an operation

        Args:
            operation_type: Type of operation being timed

        Returns:
            Operation ID for tracking
        """
        operation_id = f"{operation_type}_{int(time.time() * 1000)}"
        start_time = datetime.now(timezone.utc)

        # Store start time for this operation
        setattr(self, f"_start_{operation_id}", start_time)

        return operation_id

    def end_operation(self, operation_id: str, success: bool = True,
                     error_message: Optional[str] = None) -> LatencyMetrics:
        """
        End timing an operation and record metrics

        Args:
            operation_id: Operation ID from start_operation
            success: Whether operation completed successfully
            error_message: Error message if operation failed

        Returns:
            LatencyMetrics for the completed operation
        """
        end_time = datetime.now(timezone.utc)
        start_time_attr = f"_start_{operation_id}"

        if not hasattr(self, start_time_attr):
            logger.warning(f"No start time found for operation {operation_id}")
            return None

        start_time = getattr(self, start_time_attr)
        duration = (end_time - start_time).total_seconds() * 1000  # Convert to milliseconds

        # Extract operation type from operation_id
        operation_type = operation_id.split('_')[0]

        metrics = LatencyMetrics(
            operation_type=operation_type,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration,
            success=success,
            error_message=error_message
        )

        # Store metrics
        self.latency_history.append(metrics)
        self.operation_stats[operation_type].append(duration)

        # Clean up start time
        delattr(self, start_time_attr)

        return metrics

    def record_data_load_latency(self, duration_seconds: float):
        """Record data loading latency"""
        duration_ms = duration_seconds * 1000
        metrics = LatencyMetrics(
            operation_type='data_load',
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            success=True
        )
        self.latency_history.append(metrics)
        self.operation_stats['data_load'].append(duration_ms)

    def record_algorithm_latency(self, duration_seconds: float):
        """Record algorithm execution latency"""
        duration_ms = duration_seconds * 1000
        metrics = LatencyMetrics(
            operation_type='algorithm',
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            success=True
        )
        self.latency_history.append(metrics)
        self.operation_stats['algorithm'].append(duration_ms)

    def get_operation_stats(self, operation_type: str) -> Dict[str, float]:
        """Get statistics for a specific operation type"""
        durations = self.operation_stats.get(operation_type, [])

        if not durations:
            return {
                'count': 0,
                'avg_ms': 0.0,
                'min_ms': 0.0,
                'max_ms': 0.0,
                'p50_ms': 0.0,
                'p95_ms': 0.0,
                'p99_ms': 0.0
            }

        sorted_durations = sorted(durations)
        count = len(durations)

        return {
            'count': count,
            'avg_ms': statistics.mean(durations),
            'min_ms': min(durations),
            'max_ms': max(durations),
            'p50_ms': sorted_durations[int(count * 0.5)] if count > 0 else 0.0,
            'p95_ms': sorted_durations[int(count * 0.95)] if count > 0 else 0.0,
            'p99_ms': sorted_durations[int(count * 0.99)] if count > 0 else 0.0
        }

    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all operation types"""
        stats = {}
        for operation_type in self.operation_stats.keys():
            stats[operation_type] = self.get_operation_stats(operation_type)
        return stats


class RealCostTracker:
    """Real API cost tracking for data providers"""

    def __init__(self):
        """Initialize cost tracker"""
        self.cost_history: List[CostMetrics] = []
        self.daily_costs = defaultdict(float)
        self.provider_costs = defaultdict(float)

        # Cost rates (estimated - should be updated with real rates)
        self.cost_rates = {
            'barchart': {
                'api_call': 0.01,  # $0.01 per API call
                'mb_data': 0.005   # $0.005 per MB
            },
            'databento': {
                'api_call': 0.02,  # $0.02 per API call
                'mb_data': 0.01    # $0.01 per MB
            },
            'polygon': {
                'api_call': 0.003,  # $0.003 per API call
                'mb_data': 0.002    # $0.002 per MB
            },
            'tradovate': {
                'api_call': 0.0,   # Free tier
                'mb_data': 0.0     # Free tier
            }
        }

    def record_data_request_cost(self, metadata: Dict[str, Any]):
        """Record cost from data request metadata"""
        provider = metadata.get('source', 'unknown')
        data_size_mb = metadata.get('data_size_bytes', 0) / (1024 * 1024)

        # Calculate estimated cost
        rates = self.cost_rates.get(provider, {'api_call': 0.01, 'mb_data': 0.005})
        estimated_cost = rates['api_call'] + (data_size_mb * rates['mb_data'])

        cost_metrics = CostMetrics(
            provider=provider,
            operation='data_request',
            timestamp=datetime.now(timezone.utc),
            estimated_cost=estimated_cost,
            requests_count=1,
            data_volume_mb=data_size_mb
        )

        self.cost_history.append(cost_metrics)

        # Update daily and provider totals
        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_costs[today] += estimated_cost
        self.provider_costs[provider] += estimated_cost

        logger.debug(f"Recorded cost: {provider} ${estimated_cost:.4f}")

    def record_streaming_cost(self, provider: str, duration_minutes: float,
                            data_volume_mb: float):
        """Record cost for streaming data operations"""
        rates = self.cost_rates.get(provider, {'api_call': 0.01, 'mb_data': 0.005})

        # Streaming cost based on time and data volume
        time_cost = duration_minutes * 0.01  # $0.01 per minute
        data_cost = data_volume_mb * rates['mb_data']
        estimated_cost = time_cost + data_cost

        cost_metrics = CostMetrics(
            provider=provider,
            operation='streaming',
            timestamp=datetime.now(timezone.utc),
            estimated_cost=estimated_cost,
            requests_count=1,
            data_volume_mb=data_volume_mb
        )

        self.cost_history.append(cost_metrics)

        # Update totals
        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_costs[today] += estimated_cost
        self.provider_costs[provider] += estimated_cost

    def get_daily_cost(self, date: str = None) -> float:
        """Get total cost for a specific date"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        return self.daily_costs.get(date, 0.0)

    def get_provider_costs(self) -> Dict[str, float]:
        """Get costs by provider"""
        return dict(self.provider_costs)

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get comprehensive cost summary"""
        today = datetime.now().strftime('%Y-%m-%d')
        total_cost = sum(self.daily_costs.values())

        return {
            'today_cost': self.get_daily_cost(today),
            'total_cost': total_cost,
            'provider_costs': self.get_provider_costs(),
            'daily_breakdown': dict(self.daily_costs),
            'cost_per_request': total_cost / len(self.cost_history) if self.cost_history else 0.0,
            'total_requests': len(self.cost_history)
        }


class DataQualityMonitor:
    """Monitor data quality and completeness from providers"""

    def __init__(self):
        """Initialize data quality monitor"""
        self.quality_history: List[DataQualityMetrics] = []
        self.source_stats = defaultdict(list)

    def record_data_quality(self, source: str, expected_records: int,
                          actual_records: int, latency_ms: float,
                          error_count: int = 0):
        """Record data quality metrics for a source"""

        completeness_pct = (actual_records / max(expected_records, 1)) * 100

        # Calculate quality score (0-1) based on completeness, latency, and errors
        completeness_score = min(completeness_pct / 100, 1.0)
        latency_score = max(0, 1.0 - (latency_ms / 5000))  # Penalize >5s latency
        error_score = max(0, 1.0 - (error_count / 10))     # Penalize >10 errors

        quality_score = (completeness_score * 0.5) + (latency_score * 0.3) + (error_score * 0.2)

        metrics = DataQualityMetrics(
            source=source,
            timestamp=datetime.now(timezone.utc),
            total_expected_records=expected_records,
            actual_records=actual_records,
            completeness_pct=completeness_pct,
            latency_ms=latency_ms,
            error_count=error_count,
            quality_score=quality_score
        )

        self.quality_history.append(metrics)
        self.source_stats[source].append(quality_score)

        logger.debug(f"Data quality: {source} {quality_score:.2f} score")

    def get_source_quality(self, source: str) -> Dict[str, float]:
        """Get quality statistics for a specific source"""
        scores = self.source_stats.get(source, [])

        if not scores:
            return {
                'avg_quality': 0.0,
                'min_quality': 0.0,
                'max_quality': 0.0,
                'sample_count': 0
            }

        return {
            'avg_quality': statistics.mean(scores),
            'min_quality': min(scores),
            'max_quality': max(scores),
            'sample_count': len(scores)
        }

    def get_overall_quality(self) -> Dict[str, Any]:
        """Get overall data quality summary"""
        all_scores = []
        for scores in self.source_stats.values():
            all_scores.extend(scores)

        if not all_scores:
            return {
                'overall_quality': 0.0,
                'source_breakdown': {},
                'total_samples': 0
            }

        source_breakdown = {}
        for source in self.source_stats.keys():
            source_breakdown[source] = self.get_source_quality(source)

        return {
            'overall_quality': statistics.mean(all_scores),
            'source_breakdown': source_breakdown,
            'total_samples': len(all_scores)
        }


class SystemResourceMonitor:
    """Monitor system resource usage during shadow trading"""

    def __init__(self, sample_interval: int = 60):
        """
        Initialize system resource monitor

        Args:
            sample_interval: Sampling interval in seconds
        """
        self.sample_interval = sample_interval
        self.resource_history: List[SystemResourceMetrics] = []
        self.monitoring_active = False

    def start_monitoring(self):
        """Start continuous system monitoring"""
        self.monitoring_active = True
        logger.info("Started system resource monitoring")

    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring_active = False
        logger.info("Stopped system resource monitoring")

    def sample_resources(self) -> SystemResourceMetrics:
        """Take a single sample of system resources"""
        try:
            # Get system metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Get network I/O
            network = psutil.net_io_counters()
            network_mb = (network.bytes_sent + network.bytes_recv) / (1024 * 1024)

            # Get process count
            process_count = len(psutil.pids())

            metrics = SystemResourceMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_usage_pct=cpu_usage,
                memory_usage_pct=memory.percent,
                disk_usage_pct=disk.percent,
                network_io_mb=network_mb,
                process_count=process_count
            )

            self.resource_history.append(metrics)
            return metrics

        except Exception as e:
            logger.error(f"Error sampling system resources: {e}")
            return None

    def get_resource_summary(self) -> Dict[str, Any]:
        """Get summary of resource usage"""
        if not self.resource_history:
            return {
                'avg_cpu': 0.0,
                'avg_memory': 0.0,
                'avg_disk': 0.0,
                'sample_count': 0
            }

        cpu_values = [m.cpu_usage_pct for m in self.resource_history]
        memory_values = [m.memory_usage_pct for m in self.resource_history]
        disk_values = [m.disk_usage_pct for m in self.resource_history]

        return {
            'avg_cpu': statistics.mean(cpu_values),
            'max_cpu': max(cpu_values),
            'avg_memory': statistics.mean(memory_values),
            'max_memory': max(memory_values),
            'avg_disk': statistics.mean(disk_values),
            'max_disk': max(disk_values),
            'sample_count': len(self.resource_history)
        }


class RealPerformanceMetrics:
    """Unified real performance metrics for shadow trading"""

    def __init__(self):
        """Initialize all performance monitoring components"""
        self.latency_monitor = RealLatencyMonitor()
        self.cost_tracker = RealCostTracker()
        self.quality_monitor = DataQualityMonitor()
        self.resource_monitor = SystemResourceMonitor()

        logger.info("Real performance metrics initialized")

    def start_monitoring(self):
        """Start all monitoring components"""
        self.resource_monitor.start_monitoring()

    def stop_monitoring(self):
        """Stop all monitoring components"""
        self.resource_monitor.stop_monitoring()

    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics summary"""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'latency_stats': self.latency_monitor.get_all_stats(),
            'cost_summary': self.cost_tracker.get_cost_summary(),
            'data_quality': self.quality_monitor.get_overall_quality(),
            'system_resources': self.resource_monitor.get_resource_summary()
        }


# Factory function
def create_real_performance_metrics() -> RealPerformanceMetrics:
    """Create real performance metrics instance"""
    return RealPerformanceMetrics()


if __name__ == "__main__":
    # Example usage
    metrics = create_real_performance_metrics()
    metrics.start_monitoring()

    # Simulate some operations
    op_id = metrics.latency_monitor.start_operation('data_load')
    time.sleep(0.1)  # Simulate data loading
    metrics.latency_monitor.end_operation(op_id, success=True)

    # Record some costs
    metadata = {'source': 'barchart', 'data_size_bytes': 1024000}
    metrics.cost_tracker.record_data_request_cost(metadata)

    # Sample system resources
    metrics.resource_monitor.sample_resources()

    # Get comprehensive report
    report = metrics.get_comprehensive_metrics()
    print(f"Performance Metrics: {report}")

    metrics.stop_monitoring()
