#!/usr/bin/env python3
"""
Cost Analysis and Optimization Module for IFD Trading System

This module provides detailed cost tracking, analysis, and optimization
recommendations for multi-provider data sources and trading operations.

Features:
- Per-provider cost tracking
- API call monitoring and optimization
- Cost-benefit analysis
- Budget enforcement
- Cost optimization recommendations
"""

import json
import os
from datetime import datetime, timedelta
from utils.timezone_utils import get_eastern_time, get_utc_time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict
import pandas as pd


class DataProvider(Enum):
    """Supported data providers"""
    BARCHART = "BARCHART"
    DATABENTO = "DATABENTO"
    POLYGON = "POLYGON"
    TRADOVATE = "TRADOVATE"
    INTERACTIVE_BROKERS = "INTERACTIVE_BROKERS"


class CostType(Enum):
    """Types of costs tracked"""
    API_CALL = "API_CALL"
    DATA_STREAMING = "DATA_STREAMING"
    MARKET_DATA = "MARKET_DATA"
    EXECUTION = "EXECUTION"
    PLATFORM_FEE = "PLATFORM_FEE"


@dataclass
class ProviderCosts:
    """Cost structure for a data provider"""
    provider: DataProvider

    # API costs
    cost_per_api_call: float = 0.0
    cost_per_streaming_minute: float = 0.0
    cost_per_symbol: float = 0.0

    # Subscription costs
    monthly_base_fee: float = 0.0
    annual_base_fee: float = 0.0

    # Usage limits
    free_api_calls_per_month: int = 0
    free_streaming_minutes: int = 0
    rate_limit_per_second: int = 10

    # Overage charges
    overage_cost_per_call: float = 0.0
    overage_cost_per_minute: float = 0.0


@dataclass
class UsageRecord:
    """Record of API/data usage"""
    provider: DataProvider
    timestamp: datetime
    cost_type: CostType

    # Usage details
    api_calls: int = 0
    streaming_minutes: float = 0.0
    symbols_accessed: int = 0
    data_points: int = 0

    # Cost calculation
    estimated_cost: float = 0.0
    actual_cost: Optional[float] = None

    # Context
    algorithm_version: str = ""
    operation: str = ""  # e.g., "signal_generation", "backtesting"


@dataclass
class CostOptimizationRecommendation:
    """Cost optimization recommendation"""
    recommendation_id: str
    priority: str  # HIGH, MEDIUM, LOW
    category: str  # API_USAGE, CACHING, PROVIDER_SWITCH, BATCHING

    title: str
    description: str

    # Impact estimates
    potential_monthly_savings: float
    implementation_effort: str  # LOW, MEDIUM, HIGH
    estimated_time_to_implement: str

    # Specific actions
    actions: List[str] = field(default_factory=list)

    # Metrics
    current_cost: float = 0.0
    projected_cost: float = 0.0
    cost_reduction_percentage: float = 0.0


@dataclass
class BudgetAlert:
    """Budget threshold alert"""
    alert_id: str
    timestamp: datetime
    severity: str  # INFO, WARNING, CRITICAL

    budget_category: str
    current_spend: float
    budget_limit: float
    percentage_used: float

    message: str
    recommended_action: str


class CostAnalyzer:
    """
    Comprehensive cost analysis and optimization system

    Features:
    - Real-time cost tracking
    - Provider comparison
    - Budget monitoring
    - Optimization recommendations
    """

    def __init__(self, config_file: str = "config/cost_config.json"):
        """
        Initialize cost analyzer

        Args:
            config_file: Path to cost configuration file
        """
        self.config_file = config_file
        self.provider_costs = self._load_provider_costs()

        # Usage tracking
        self.usage_records: List[UsageRecord] = []
        self.daily_usage: Dict[str, Dict[DataProvider, Dict[str, float]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float))
        )

        # Budget configuration
        self.budgets = {
            "daily": 100.0,
            "weekly": 500.0,
            "monthly": 2000.0,
            "per_algorithm": {
                "v1.0": 800.0,
                "v3.0": 1200.0
            }
        }

        # Alerts
        self.budget_alerts: List[BudgetAlert] = []

        # Optimization tracking
        self.optimization_history: List[CostOptimizationRecommendation] = []

    def _load_provider_costs(self) -> Dict[DataProvider, ProviderCosts]:
        """Load provider cost configurations"""
        # Default cost structures
        default_costs = {
            DataProvider.BARCHART: ProviderCosts(
                provider=DataProvider.BARCHART,
                cost_per_api_call=0.01,
                monthly_base_fee=299.0,
                free_api_calls_per_month=250000,
                overage_cost_per_call=0.02
            ),
            DataProvider.DATABENTO: ProviderCosts(
                provider=DataProvider.DATABENTO,
                cost_per_api_call=0.0001,  # Very cheap per call
                cost_per_streaming_minute=0.10,
                monthly_base_fee=0.0,  # Pay as you go
                rate_limit_per_second=100
            ),
            DataProvider.POLYGON: ProviderCosts(
                provider=DataProvider.POLYGON,
                cost_per_api_call=0.0,
                monthly_base_fee=79.0,
                free_api_calls_per_month=float('inf'),  # Unlimited with subscription
                rate_limit_per_second=100
            ),
            DataProvider.TRADOVATE: ProviderCosts(
                provider=DataProvider.TRADOVATE,
                cost_per_api_call=0.0,
                cost_per_streaming_minute=0.0,
                monthly_base_fee=0.0,  # Included with trading
                rate_limit_per_second=50
            ),
            DataProvider.INTERACTIVE_BROKERS: ProviderCosts(
                provider=DataProvider.INTERACTIVE_BROKERS,
                cost_per_api_call=0.0,
                cost_per_symbol=1.50,  # Per symbol per month
                monthly_base_fee=10.0,  # Market data base
                rate_limit_per_second=50
            )
        }

        # Load custom configuration if exists
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                custom_config = json.load(f)
                # Update default costs with custom values
                # Implementation depends on config format

        return default_costs

    def track_usage(self, provider: DataProvider, usage_data: Dict[str, Any]) -> UsageRecord:
        """
        Track API/data usage

        Args:
            provider: Data provider
            usage_data: Usage details

        Returns:
            UsageRecord with cost calculation
        """
        record = UsageRecord(
            provider=provider,
            timestamp=get_eastern_time(),
            cost_type=CostType(usage_data.get("cost_type", "API_CALL")),
            api_calls=usage_data.get("api_calls", 0),
            streaming_minutes=usage_data.get("streaming_minutes", 0.0),
            symbols_accessed=usage_data.get("symbols_accessed", 0),
            data_points=usage_data.get("data_points", 0),
            algorithm_version=usage_data.get("algorithm_version", ""),
            operation=usage_data.get("operation", "")
        )

        # Calculate estimated cost
        record.estimated_cost = self._calculate_usage_cost(record)

        # Store record
        self.usage_records.append(record)

        # Update daily usage
        date_key = record.timestamp.strftime("%Y-%m-%d")
        self.daily_usage[date_key][provider]["api_calls"] += record.api_calls
        self.daily_usage[date_key][provider]["streaming_minutes"] += record.streaming_minutes
        self.daily_usage[date_key][provider]["estimated_cost"] += record.estimated_cost

        # Check budget thresholds
        self._check_budget_alerts()

        return record

    def _calculate_usage_cost(self, record: UsageRecord) -> float:
        """Calculate cost for a usage record"""
        provider_cost = self.provider_costs[record.provider]
        cost = 0.0

        # API call costs
        if record.api_calls > 0:
            # Check if within free tier
            month_key = record.timestamp.strftime("%Y-%m")
            monthly_calls = sum(
                r.api_calls for r in self.usage_records
                if r.provider == record.provider and
                r.timestamp.strftime("%Y-%m") == month_key
            )

            if monthly_calls > provider_cost.free_api_calls_per_month:
                # Overage charges
                overage_calls = monthly_calls - provider_cost.free_api_calls_per_month
                cost += min(overage_calls, record.api_calls) * provider_cost.overage_cost_per_call
            else:
                # Within free tier, but count base cost
                cost += record.api_calls * provider_cost.cost_per_api_call

        # Streaming costs
        if record.streaming_minutes > 0:
            cost += record.streaming_minutes * provider_cost.cost_per_streaming_minute

        # Symbol access costs (e.g., IB)
        if record.symbols_accessed > 0:
            cost += record.symbols_accessed * provider_cost.cost_per_symbol

        return cost

    def get_cost_summary(self, start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get comprehensive cost summary

        Args:
            start_date: Start of period (default: 30 days ago)
            end_date: End of period (default: today)

        Returns:
            Cost summary with breakdowns
        """
        if start_date is None:
            start_date = get_eastern_time() - timedelta(days=30)
        if end_date is None:
            end_date = get_eastern_time()

        # Filter records
        period_records = [
            r for r in self.usage_records
            if start_date <= r.timestamp <= end_date
        ]

        summary = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days
            },
            "total_cost": sum(r.estimated_cost for r in period_records),
            "by_provider": {},
            "by_algorithm": {},
            "by_operation": {},
            "by_cost_type": {},
            "daily_average": 0.0,
            "projections": {}
        }

        # Group by provider
        for provider in DataProvider:
            provider_records = [r for r in period_records if r.provider == provider]
            if provider_records:
                summary["by_provider"][provider.value] = {
                    "total_cost": sum(r.estimated_cost for r in provider_records),
                    "api_calls": sum(r.api_calls for r in provider_records),
                    "streaming_minutes": sum(r.streaming_minutes for r in provider_records),
                    "percentage_of_total": 0.0
                }

        # Calculate percentages
        if summary["total_cost"] > 0:
            for provider_data in summary["by_provider"].values():
                provider_data["percentage_of_total"] = (
                    provider_data["total_cost"] / summary["total_cost"] * 100
                )

        # Group by algorithm
        for algo in ["v1.0", "v3.0"]:
            algo_records = [r for r in period_records if r.algorithm_version == algo]
            if algo_records:
                summary["by_algorithm"][algo] = {
                    "total_cost": sum(r.estimated_cost for r in algo_records),
                    "api_calls": sum(r.api_calls for r in algo_records),
                    "average_cost_per_call": 0.0
                }

                if summary["by_algorithm"][algo]["api_calls"] > 0:
                    summary["by_algorithm"][algo]["average_cost_per_call"] = (
                        summary["by_algorithm"][algo]["total_cost"] /
                        summary["by_algorithm"][algo]["api_calls"]
                    )

        # Group by operation
        operations = set(r.operation for r in period_records if r.operation)
        for operation in operations:
            op_records = [r for r in period_records if r.operation == operation]
            summary["by_operation"][operation] = {
                "total_cost": sum(r.estimated_cost for r in op_records),
                "frequency": len(op_records)
            }

        # Daily average
        if summary["period"]["days"] > 0:
            summary["daily_average"] = summary["total_cost"] / summary["period"]["days"]

        # Projections
        summary["projections"] = {
            "monthly": summary["daily_average"] * 30,
            "annual": summary["daily_average"] * 365
        }

        # Add subscription costs
        monthly_subscriptions = sum(
            cost.monthly_base_fee for cost in self.provider_costs.values()
        )
        summary["projections"]["monthly_with_subscriptions"] = (
            summary["projections"]["monthly"] + monthly_subscriptions
        )

        return summary

    def generate_optimization_recommendations(self) -> List[CostOptimizationRecommendation]:
        """
        Generate cost optimization recommendations based on usage patterns

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        # Get recent usage summary
        summary = self.get_cost_summary()

        # 1. Check for provider optimization
        if summary["by_provider"]:
            recommendations.extend(self._check_provider_optimization(summary))

        # 2. Check for API call batching opportunities
        recommendations.extend(self._check_batching_opportunities())

        # 3. Check for caching opportunities
        recommendations.extend(self._check_caching_opportunities())

        # 4. Check for rate limit optimization
        recommendations.extend(self._check_rate_limit_optimization())

        # 5. Algorithm-specific optimizations
        recommendations.extend(self._check_algorithm_optimization(summary))

        # Sort by priority and potential savings
        recommendations.sort(
            key=lambda x: (
                {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[x.priority],
                -x.potential_monthly_savings
            )
        )

        # Store recommendations
        self.optimization_history.extend(recommendations)

        return recommendations

    def _check_provider_optimization(self, summary: Dict[str, Any]) -> List[CostOptimizationRecommendation]:
        """Check for provider switching opportunities"""
        recommendations = []

        # Example: If Barchart is >50% of costs and high volume
        barchart_data = summary["by_provider"].get("BARCHART", {})

        if barchart_data.get("percentage_of_total", 0) > 50:
            if barchart_data.get("api_calls", 0) > 100000:  # High volume

                # Calculate potential savings with Databento
                current_cost = barchart_data["total_cost"]
                databento_cost = barchart_data["api_calls"] * 0.0001  # Databento rate
                savings = current_cost - databento_cost

                if savings > 100:  # Significant savings
                    recommendations.append(
                        CostOptimizationRecommendation(
                            recommendation_id=f"opt_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}_provider",
                            priority="HIGH",
                            category="PROVIDER_SWITCH",
                            title="Switch high-volume API calls to Databento",
                            description=(
                                f"Barchart accounts for {barchart_data['percentage_of_total']:.1f}% "
                                f"of costs. Switching high-frequency calls to Databento could save "
                                f"${savings:.2f}/month."
                            ),
                            potential_monthly_savings=savings,
                            implementation_effort="MEDIUM",
                            estimated_time_to_implement="1-2 days",
                            actions=[
                                "Implement Databento integration for real-time data",
                                "Keep Barchart for reference data and EOD summaries",
                                "Update data routing logic to use Databento for high-frequency calls"
                            ],
                            current_cost=current_cost,
                            projected_cost=databento_cost,
                            cost_reduction_percentage=(savings / current_cost * 100)
                        )
                    )

        return recommendations

    def _check_batching_opportunities(self) -> List[CostOptimizationRecommendation]:
        """Check for API call batching opportunities"""
        recommendations = []

        # Analyze recent API calls for patterns
        recent_records = [
            r for r in self.usage_records
            if r.timestamp > get_eastern_time() - timedelta(days=7)
            and r.api_calls > 0
        ]

        # Group by operation and time window
        operation_patterns = defaultdict(list)

        for record in recent_records:
            if record.operation:
                operation_patterns[record.operation].append(record)

        # Check for rapid successive calls
        for operation, records in operation_patterns.items():
            # Sort by timestamp
            records.sort(key=lambda x: x.timestamp)

            # Check for calls within 1 second
            rapid_calls = 0
            for i in range(1, len(records)):
                if (records[i].timestamp - records[i-1].timestamp).total_seconds() < 1:
                    rapid_calls += 1

            if rapid_calls > 10:  # Significant pattern
                avg_calls_per_batch = sum(r.api_calls for r in records) / len(records)
                potential_reduction = rapid_calls * 0.8  # 80% reduction through batching

                recommendations.append(
                    CostOptimizationRecommendation(
                        recommendation_id=f"opt_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}_batch_{operation}",
                        priority="MEDIUM",
                        category="BATCHING",
                        title=f"Batch API calls for {operation}",
                        description=(
                            f"Detected {rapid_calls} rapid successive API calls for {operation}. "
                            f"Batching these calls could reduce API usage by ~80%."
                        ),
                        potential_monthly_savings=potential_reduction * 0.01 * 30,  # Rough estimate
                        implementation_effort="LOW",
                        estimated_time_to_implement="2-4 hours",
                        actions=[
                            f"Implement request batching for {operation}",
                            "Add 100ms delay to aggregate requests",
                            "Combine multiple symbol requests into single API call"
                        ],
                        cost_reduction_percentage=80
                    )
                )

        return recommendations

    def _check_caching_opportunities(self) -> List[CostOptimizationRecommendation]:
        """Check for data caching opportunities"""
        recommendations = []

        # Analyze repeated requests
        request_frequency = defaultdict(int)

        for record in self.usage_records:
            if record.operation and record.symbols_accessed > 0:
                key = f"{record.provider.value}_{record.operation}"
                request_frequency[key] += 1

        # Find high-frequency requests
        for key, frequency in request_frequency.items():
            if frequency > 100:  # High frequency threshold
                provider, operation = key.split("_", 1)

                # Estimate cache hit rate
                cache_hit_rate = 0.7  # Conservative estimate
                calls_saved = frequency * cache_hit_rate
                monthly_savings = calls_saved * 0.01  # Average cost per call

                recommendations.append(
                    CostOptimizationRecommendation(
                        recommendation_id=f"opt_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}_cache_{operation}",
                        priority="MEDIUM" if monthly_savings > 50 else "LOW",
                        category="CACHING",
                        title=f"Implement caching for {operation}",
                        description=(
                            f"Operation '{operation}' has {frequency} repeated requests. "
                            f"Implementing a cache with {cache_hit_rate*100:.0f}% hit rate "
                            f"could save ${monthly_savings:.2f}/month."
                        ),
                        potential_monthly_savings=monthly_savings,
                        implementation_effort="LOW",
                        estimated_time_to_implement="1-2 hours",
                        actions=[
                            "Implement Redis or in-memory cache",
                            "Set appropriate TTL based on data freshness requirements",
                            "Add cache warming for frequently accessed data"
                        ],
                        cost_reduction_percentage=cache_hit_rate * 100
                    )
                )

        return recommendations

    def _check_rate_limit_optimization(self) -> List[CostOptimizationRecommendation]:
        """Check for rate limit optimization"""
        recommendations = []

        # Analyze rate limit usage
        for provider, cost_structure in self.provider_costs.items():
            provider_records = [
                r for r in self.usage_records
                if r.provider == provider and
                r.timestamp > get_eastern_time() - timedelta(days=7)
            ]

            if not provider_records:
                continue

            # Calculate peak request rate
            # Group by minute
            minute_groups = defaultdict(int)
            for record in provider_records:
                minute_key = record.timestamp.strftime("%Y-%m-%d %H:%M")
                minute_groups[minute_key] += record.api_calls

            peak_rate = max(minute_groups.values()) / 60 if minute_groups else 0

            # Check if approaching rate limit
            if peak_rate > cost_structure.rate_limit_per_second * 0.8:
                recommendations.append(
                    CostOptimizationRecommendation(
                        recommendation_id=f"opt_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}_ratelimit_{provider.value}",
                        priority="HIGH",
                        category="API_USAGE",
                        title=f"Optimize {provider.value} rate limit usage",
                        description=(
                            f"Peak request rate ({peak_rate:.1f}/s) is approaching "
                            f"rate limit ({cost_structure.rate_limit_per_second}/s). "
                            "Implement request throttling to avoid rate limit errors."
                        ),
                        potential_monthly_savings=0,  # Prevents errors, not direct savings
                        implementation_effort="LOW",
                        estimated_time_to_implement="1 hour",
                        actions=[
                            "Implement request queue with rate limiting",
                            "Add exponential backoff for retries",
                            "Consider upgrading plan for higher rate limits"
                        ],
                        cost_reduction_percentage=0
                    )
                )

        return recommendations

    def _check_algorithm_optimization(self, summary: Dict[str, Any]) -> List[CostOptimizationRecommendation]:
        """Check for algorithm-specific optimizations"""
        recommendations = []

        # Compare v1.0 vs v3.0 costs
        v1_data = summary["by_algorithm"].get("v1.0", {})
        v3_data = summary["by_algorithm"].get("v3.0", {})

        if v1_data and v3_data:
            v1_cost_per_signal = v1_data.get("average_cost_per_call", 0)
            v3_cost_per_signal = v3_data.get("average_cost_per_call", 0)

            # If v3.0 is significantly more expensive
            if v3_cost_per_signal > v1_cost_per_signal * 1.5:
                cost_difference = v3_cost_per_signal - v1_cost_per_signal
                monthly_extra = cost_difference * v3_data.get("api_calls", 0)

                recommendations.append(
                    CostOptimizationRecommendation(
                        recommendation_id=f"opt_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}_algo_efficiency",
                        priority="MEDIUM",
                        category="API_USAGE",
                        title="Optimize IFD v3.0 data efficiency",
                        description=(
                            f"IFD v3.0 costs {v3_cost_per_signal/v1_cost_per_signal:.1f}x more "
                            f"per signal than v1.0. Optimizing data access patterns could save "
                            f"${monthly_extra:.2f}/month."
                        ),
                        potential_monthly_savings=monthly_extra * 0.3,  # 30% reduction possible
                        implementation_effort="MEDIUM",
                        estimated_time_to_implement="2-3 days",
                        actions=[
                            "Review v3.0 data access patterns",
                            "Implement more selective data fetching",
                            "Cache MBO baseline data between analyses",
                            "Batch pressure metric calculations"
                        ],
                        current_cost=v3_data.get("total_cost", 0),
                        projected_cost=v3_data.get("total_cost", 0) * 0.7,
                        cost_reduction_percentage=30
                    )
                )

        return recommendations

    def _check_budget_alerts(self):
        """Check and generate budget alerts"""
        now = get_eastern_time()

        # Daily budget check
        today_key = now.strftime("%Y-%m-%d")
        today_cost = sum(
            provider_data["estimated_cost"]
            for provider_data in self.daily_usage.get(today_key, {}).values()
        )

        if today_cost > self.budgets["daily"] * 0.8:
            severity = "CRITICAL" if today_cost > self.budgets["daily"] else "WARNING"

            alert = BudgetAlert(
                alert_id=f"alert_{now.strftime('%Y%m%d_%H%M%S')}_daily",
                timestamp=now,
                severity=severity,
                budget_category="daily",
                current_spend=today_cost,
                budget_limit=self.budgets["daily"],
                percentage_used=(today_cost / self.budgets["daily"] * 100),
                message=f"Daily budget {severity}: ${today_cost:.2f} of ${self.budgets['daily']:.2f}",
                recommended_action="Reduce API usage or switch to cached data"
            )

            self.budget_alerts.append(alert)
            self._notify_budget_alert(alert)

    def _notify_budget_alert(self, alert: BudgetAlert):
        """Send budget alert notification"""
        print(f"\n⚠️ BUDGET ALERT - {alert.severity}")
        print(f"   {alert.message}")
        print(f"   Action: {alert.recommended_action}")

    def enforce_budget_limits(self, provider: DataProvider,
                            estimated_cost: float) -> Tuple[bool, Optional[str]]:
        """
        Check if an operation should be allowed based on budget

        Args:
            provider: Data provider
            estimated_cost: Estimated cost of operation

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        now = get_eastern_time()
        today_key = now.strftime("%Y-%m-%d")

        # Check daily budget
        today_cost = sum(
            provider_data["estimated_cost"]
            for provider_data in self.daily_usage.get(today_key, {}).values()
        )

        if today_cost + estimated_cost > self.budgets["daily"]:
            return False, f"Would exceed daily budget (${self.budgets['daily']})"

        # Check monthly budget
        month_cost = self.get_cost_summary(
            start_date=datetime(now.year, now.month, 1),
            end_date=now
        )["total_cost"]

        if month_cost + estimated_cost > self.budgets["monthly"]:
            return False, f"Would exceed monthly budget (${self.budgets['monthly']})"

        return True, None

    def generate_cost_report(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive cost report

        Args:
            output_file: Optional file path to save report

        Returns:
            Complete cost analysis report
        """
        report = {
            "generated_at": get_eastern_time().isoformat(),
            "summary": self.get_cost_summary(),
            "recommendations": [
                asdict(rec) for rec in self.generate_optimization_recommendations()
            ],
            "budget_status": {
                "daily": {
                    "limit": self.budgets["daily"],
                    "used": 0,
                    "remaining": 0,
                    "percentage": 0
                },
                "monthly": {
                    "limit": self.budgets["monthly"],
                    "used": 0,
                    "remaining": 0,
                    "percentage": 0
                }
            },
            "recent_alerts": [
                asdict(alert) for alert in self.budget_alerts[-10:]
            ],
            "provider_comparison": self._generate_provider_comparison(),
            "trend_analysis": self._generate_trend_analysis()
        }

        # Update budget status
        now = get_eastern_time()
        today_cost = sum(
            provider_data["estimated_cost"]
            for provider_data in self.daily_usage.get(now.strftime("%Y-%m-%d"), {}).values()
        )

        month_cost = self.get_cost_summary(
            start_date=datetime(now.year, now.month, 1),
            end_date=now
        )["total_cost"]

        report["budget_status"]["daily"]["used"] = today_cost
        report["budget_status"]["daily"]["remaining"] = self.budgets["daily"] - today_cost
        report["budget_status"]["daily"]["percentage"] = today_cost / self.budgets["daily"] * 100

        report["budget_status"]["monthly"]["used"] = month_cost
        report["budget_status"]["monthly"]["remaining"] = self.budgets["monthly"] - month_cost
        report["budget_status"]["monthly"]["percentage"] = month_cost / self.budgets["monthly"] * 100

        # Save report if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"💾 Cost report saved to: {output_file}")

        return report

    def _generate_provider_comparison(self) -> Dict[str, Any]:
        """Generate provider comparison analysis"""
        comparison = {
            "providers": {},
            "recommendations": []
        }

        # Calculate metrics for each provider
        for provider in DataProvider:
            provider_records = [
                r for r in self.usage_records
                if r.provider == provider
            ]

            if provider_records:
                total_cost = sum(r.estimated_cost for r in provider_records)
                total_calls = sum(r.api_calls for r in provider_records)

                comparison["providers"][provider.value] = {
                    "total_cost": total_cost,
                    "total_calls": total_calls,
                    "cost_per_call": total_cost / total_calls if total_calls > 0 else 0,
                    "reliability": 0.99,  # Placeholder - would track actual uptime
                    "average_latency_ms": 50  # Placeholder - would measure actual latency
                }

        # Generate recommendations
        if comparison["providers"]:
            # Find most cost-effective provider
            best_provider = min(
                comparison["providers"].items(),
                key=lambda x: x[1]["cost_per_call"] if x[1]["cost_per_call"] > 0 else float('inf')
            )

            comparison["recommendations"].append(
                f"Consider using {best_provider[0]} for high-volume operations "
                f"(lowest cost per call: ${best_provider[1]['cost_per_call']:.4f})"
            )

        return comparison

    def _generate_trend_analysis(self) -> Dict[str, Any]:
        """Generate cost trend analysis"""
        # Group by day
        daily_costs = defaultdict(float)

        for record in self.usage_records:
            day_key = record.timestamp.strftime("%Y-%m-%d")
            daily_costs[day_key] += record.estimated_cost

        # Calculate trends
        if len(daily_costs) > 7:
            costs_list = list(daily_costs.values())
            recent_avg = sum(costs_list[-7:]) / 7
            previous_avg = sum(costs_list[-14:-7]) / 7 if len(costs_list) > 14 else recent_avg

            trend_percentage = ((recent_avg - previous_avg) / previous_avg * 100) if previous_avg > 0 else 0

            return {
                "daily_average_7d": recent_avg,
                "daily_average_14d": previous_avg,
                "trend_direction": "increasing" if trend_percentage > 0 else "decreasing",
                "trend_percentage": abs(trend_percentage),
                "projection_30d": recent_avg * 30
            }

        return {
            "message": "Insufficient data for trend analysis (need 7+ days)"
        }


# Module-level convenience functions
def create_cost_analyzer() -> CostAnalyzer:
    """Create cost analyzer instance"""
    return CostAnalyzer()


def track_api_usage(provider: str, api_calls: int,
                   algorithm_version: str = "", operation: str = "") -> float:
    """
    Quick function to track API usage

    Args:
        provider: Provider name
        api_calls: Number of API calls
        algorithm_version: Algorithm version
        operation: Operation type

    Returns:
        Estimated cost
    """
    analyzer = create_cost_analyzer()

    record = analyzer.track_usage(
        DataProvider[provider.upper()],
        {
            "api_calls": api_calls,
            "algorithm_version": algorithm_version,
            "operation": operation
        }
    )

    return record.estimated_cost


if __name__ == "__main__":
    # Example usage
    analyzer = create_cost_analyzer()

    # Track some usage
    analyzer.track_usage(DataProvider.BARCHART, {
        "api_calls": 1000,
        "algorithm_version": "v1.0",
        "operation": "signal_generation"
    })

    analyzer.track_usage(DataProvider.DATABENTO, {
        "api_calls": 5000,
        "streaming_minutes": 10,
        "algorithm_version": "v3.0",
        "operation": "mbo_streaming"
    })

    # Generate cost report
    report = analyzer.generate_cost_report()

    print("\n📊 COST ANALYSIS REPORT")
    print("=" * 60)
    print(f"Total Cost (30d): ${report['summary']['total_cost']:.2f}")
    print(f"Daily Average: ${report['summary']['daily_average']:.2f}")
    print(f"Monthly Projection: ${report['summary']['projections']['monthly']:.2f}")

    print("\n💡 TOP RECOMMENDATIONS:")
    for i, rec in enumerate(report['recommendations'][:3], 1):
        print(f"\n{i}. {rec['title']}")
        print(f"   Potential Savings: ${rec['potential_monthly_savings']:.2f}/month")
        print(f"   Priority: {rec['priority']}")
        print(f"   Effort: {rec['implementation_effort']}")
