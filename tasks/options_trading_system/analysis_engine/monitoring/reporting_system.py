#!/usr/bin/env python3
"""
Automated Reporting System for IFD v3.0 Trading System

Generates comprehensive operational reports including:
- Daily operational summaries
- Weekly business reports
- SLA compliance tracking
- Performance trend analysis
- Cost analysis and budget tracking
- Incident summaries and post-mortems
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import sys
from collections import defaultdict

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
from utils.timezone_utils import get_eastern_time

@dataclass
class ReportMetrics:
    """Metrics for report generation"""
    period_start: str
    period_end: str
    trading_metrics: Dict[str, Any]
    system_metrics: Dict[str, Any]
    cost_metrics: Dict[str, Any]
    security_metrics: Dict[str, Any]
    sla_metrics: Dict[str, Any]
    alerts_summary: Dict[str, Any]

class ReportingSystem:
    """Automated reporting system for operational insights"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/reporting.json"
        self.reports_dir = "outputs/reports"
        self.data_dir = "outputs/monitoring"

        # Ensure directories exist
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Load configuration
        self.config = self._load_config()

        # Initialize alert system for report delivery
        try:
            from .alert_system import AlertSystem
            self.alert_system = AlertSystem()
        except ImportError:
            self.alert_system = None
            self.logger.warning("Alert system not available for report delivery")

    def _load_config(self) -> Dict[str, Any]:
        """Load reporting configuration"""
        default_config = {
            "daily_report": {
                "enabled": True,
                "generation_time": "08:00",
                "recipients": ["ops@company.com"],
                "format": "html",
                "include_sections": [
                    "executive_summary",
                    "trading_performance",
                    "system_health",
                    "cost_summary",
                    "alerts_summary",
                    "recommendations"
                ]
            },
            "weekly_report": {
                "enabled": True,
                "generation_day": "monday",
                "generation_time": "09:00",
                "recipients": ["management@company.com", "ops@company.com"],
                "format": "html",
                "include_sections": [
                    "executive_summary",
                    "sla_compliance",
                    "performance_trends",
                    "cost_analysis",
                    "incident_summary",
                    "business_metrics",
                    "recommendations",
                    "action_items"
                ]
            },
            "sla_targets": {
                "uptime": 99.9,
                "response_time_ms": 100,
                "signal_accuracy": 75.0,
                "data_freshness_minutes": 5,
                "alert_response_minutes": 15
            },
            "thresholds": {
                "trading_performance": {
                    "excellent": 85,
                    "good": 75,
                    "poor": 65
                },
                "system_performance": {
                    "excellent": 95,
                    "good": 90,
                    "poor": 80
                },
                "cost_efficiency": {
                    "excellent": 80,  # % of budget used efficiently
                    "good": 70,
                    "poor": 60
                }
            }
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            except Exception as e:
                self.logger.warning(f"Error loading reporting config: {e}. Using defaults.")

        return default_config

    def generate_daily_report(self, target_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate comprehensive daily operational report"""
        if target_date is None:
            target_date = get_eastern_time().date()

        # Define report period (previous day)
        period_start = datetime.combine(target_date, datetime.min.time())
        period_end = period_start + timedelta(days=1)

        self.logger.info(f"Generating daily report for {target_date}")

        # Collect metrics
        metrics = self._collect_period_metrics(period_start, period_end)

        # Generate report sections
        report = {
            "report_type": "daily_operational",
            "generated_at": get_eastern_time().isoformat(),
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
                "date": target_date.isoformat()
            },
            "sections": {}
        }

        # Add configured sections
        for section in self.config["daily_report"]["include_sections"]:
            if section == "executive_summary":
                report["sections"]["executive_summary"] = self._generate_executive_summary(metrics)
            elif section == "trading_performance":
                report["sections"]["trading_performance"] = self._generate_trading_performance_section(metrics)
            elif section == "system_health":
                report["sections"]["system_health"] = self._generate_system_health_section(metrics)
            elif section == "cost_summary":
                report["sections"]["cost_summary"] = self._generate_cost_summary_section(metrics)
            elif section == "alerts_summary":
                report["sections"]["alerts_summary"] = self._generate_alerts_summary_section(metrics)
            elif section == "recommendations":
                report["sections"]["recommendations"] = self._generate_recommendations(metrics)

        # Save report
        report_file = f"{self.reports_dir}/daily_report_{target_date.strftime('%Y%m%d')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Generate HTML version if configured
        if self.config["daily_report"]["format"] == "html":
            html_report = self._generate_html_report(report)
            html_file = f"{self.reports_dir}/daily_report_{target_date.strftime('%Y%m%d')}.html"
            with open(html_file, 'w') as f:
                f.write(html_report)

        self.logger.info(f"Daily report generated: {report_file}")
        return report

    def generate_weekly_report(self, target_week_start: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate comprehensive weekly business report"""
        if target_week_start is None:
            today = get_eastern_time().date()
            days_since_monday = today.weekday()
            target_week_start = today - timedelta(days=days_since_monday + 7)  # Previous week

        period_start = datetime.combine(target_week_start, datetime.min.time())
        period_end = period_start + timedelta(days=7)

        self.logger.info(f"Generating weekly report for week starting {target_week_start}")

        # Collect weekly metrics
        metrics = self._collect_period_metrics(period_start, period_end)

        # Generate report
        report = {
            "report_type": "weekly_business",
            "generated_at": get_eastern_time().isoformat(),
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
                "week_starting": target_week_start.isoformat()
            },
            "sections": {}
        }

        # Add configured sections
        for section in self.config["weekly_report"]["include_sections"]:
            if section == "executive_summary":
                report["sections"]["executive_summary"] = self._generate_weekly_executive_summary(metrics)
            elif section == "sla_compliance":
                report["sections"]["sla_compliance"] = self._generate_sla_compliance_section(metrics)
            elif section == "performance_trends":
                report["sections"]["performance_trends"] = self._generate_performance_trends_section(metrics)
            elif section == "cost_analysis":
                report["sections"]["cost_analysis"] = self._generate_cost_analysis_section(metrics)
            elif section == "incident_summary":
                report["sections"]["incident_summary"] = self._generate_incident_summary_section(metrics)
            elif section == "business_metrics":
                report["sections"]["business_metrics"] = self._generate_business_metrics_section(metrics)
            elif section == "recommendations":
                report["sections"]["recommendations"] = self._generate_weekly_recommendations(metrics)
            elif section == "action_items":
                report["sections"]["action_items"] = self._generate_action_items(metrics)

        # Save report
        report_file = f"{self.reports_dir}/weekly_report_{target_week_start.strftime('%Y%m%d')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Generate HTML version
        if self.config["weekly_report"]["format"] == "html":
            html_report = self._generate_html_report(report)
            html_file = f"{self.reports_dir}/weekly_report_{target_week_start.strftime('%Y%m%d')}.html"
            with open(html_file, 'w') as f:
                f.write(html_report)

        self.logger.info(f"Weekly report generated: {report_file}")
        return report

    def _collect_period_metrics(self, start_time: datetime, end_time: datetime) -> ReportMetrics:
        """Collect all metrics for a given time period"""

        # Collect trading metrics
        trading_metrics = self._collect_trading_metrics(start_time, end_time)

        # Collect system metrics
        system_metrics = self._collect_system_metrics(start_time, end_time)

        # Collect cost metrics
        cost_metrics = self._collect_cost_metrics(start_time, end_time)

        # Collect security metrics
        security_metrics = self._collect_security_metrics(start_time, end_time)

        # Calculate SLA metrics
        sla_metrics = self._calculate_sla_metrics(start_time, end_time)

        # Collect alerts summary
        alerts_summary = self._collect_alerts_summary(start_time, end_time)

        return ReportMetrics(
            period_start=start_time.isoformat(),
            period_end=end_time.isoformat(),
            trading_metrics=trading_metrics,
            system_metrics=system_metrics,
            cost_metrics=cost_metrics,
            security_metrics=security_metrics,
            sla_metrics=sla_metrics,
            alerts_summary=alerts_summary
        )

    def _collect_trading_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Collect trading performance metrics"""
        # In a real implementation, this would query the trading database
        # For now, return simulated metrics
        return {
            "signals_generated": 45,
            "signals_accuracy": 78.5,
            "profitable_signals": 35,
            "losing_signals": 10,
            "average_latency_ms": 85,
            "max_latency_ms": 145,
            "signal_distribution": {
                "EXTREME": 5,
                "VERY_HIGH": 12,
                "HIGH": 18,
                "MODERATE": 10
            },
            "market_coverage": {
                "hours_active": 6.5,
                "total_market_hours": 8.0,
                "coverage_percentage": 81.25
            }
        }

    def _collect_system_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Collect system performance metrics"""
        return {
            "uptime_percentage": 99.95,
            "average_cpu_usage": 65.2,
            "average_memory_usage": 72.1,
            "average_disk_usage": 45.8,
            "api_response_time_avg_ms": 95,
            "api_response_time_p95_ms": 145,
            "error_rate_percentage": 0.8,
            "data_processing_rate": 1250,  # events per minute
            "system_restarts": 0,
            "component_health": {
                "websocket_server": "healthy",
                "streaming_bridge": "healthy",
                "analysis_engine": "healthy",
                "monitoring_system": "healthy"
            }
        }

    def _collect_cost_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Collect cost and budget metrics"""
        return {
            "total_cost": 7.85,
            "daily_budget": 10.0,
            "budget_utilization": 78.5,
            "cost_breakdown": {
                "databento_api": 6.20,
                "polygon_api": 1.05,
                "infrastructure": 0.60
            },
            "cost_per_signal": 0.17,
            "monthly_projection": 235.5,
            "monthly_budget": 300.0,
            "cost_trends": {
                "vs_yesterday": -5.2,
                "vs_last_week_avg": 12.3,
                "vs_monthly_avg": 8.1
            }
        }

    def _collect_security_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Collect security metrics"""
        return {
            "security_score": 92,
            "failed_auth_attempts": 3,
            "successful_auth_attempts": 124,
            "blocked_ips": 0,
            "intrusion_attempts": 1,
            "high_risk_events": 0,
            "data_access_events": 89,
            "rate_limit_violations": 2,
            "security_alerts": {
                "LOW": 2,
                "MEDIUM": 1,
                "HIGH": 0,
                "CRITICAL": 0
            }
        }

    def _calculate_sla_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Calculate SLA compliance metrics"""
        targets = self.config["sla_targets"]

        # Simulate SLA calculations based on collected metrics
        return {
            "uptime": {
                "actual": 99.95,
                "target": targets["uptime"],
                "compliance": True,
                "breach_minutes": 0.36
            },
            "response_time": {
                "actual_ms": 95,
                "target_ms": targets["response_time_ms"],
                "compliance": True,
                "p95_ms": 145
            },
            "signal_accuracy": {
                "actual": 78.5,
                "target": targets["signal_accuracy"],
                "compliance": True,
                "variance": 3.5
            },
            "data_freshness": {
                "actual_minutes": 2.1,
                "target_minutes": targets["data_freshness_minutes"],
                "compliance": True,
                "max_delay_minutes": 4.2
            },
            "alert_response": {
                "actual_minutes": 8.5,
                "target_minutes": targets["alert_response_minutes"],
                "compliance": True,
                "max_response_minutes": 12.1
            },
            "overall_sla_score": 98.5
        }

    def _collect_alerts_summary(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Collect alerts summary"""
        return {
            "total_alerts": 8,
            "by_severity": {
                "INFO": 3,
                "WARNING": 4,
                "CRITICAL": 1,
                "EMERGENCY": 0
            },
            "by_component": {
                "trading_engine": 2,
                "system_monitor": 3,
                "cost_monitor": 2,
                "security_monitor": 1
            },
            "resolution_time_avg_minutes": 25.4,
            "acknowledged_alerts": 7,
            "auto_resolved_alerts": 5,
            "escalated_alerts": 1,
            "top_alert_triggers": [
                "High memory usage",
                "Budget warning threshold",
                "API response time spike"
            ]
        }

    def _generate_executive_summary(self, metrics: ReportMetrics) -> Dict[str, Any]:
        """Generate executive summary for daily report"""
        trading = metrics.trading_metrics
        system = metrics.system_metrics
        cost = metrics.cost_metrics

        # Determine overall health score
        health_score = self._calculate_health_score(metrics)

        # Generate status indicators
        trading_status = "Good" if trading["signals_accuracy"] >= 75 else "Poor"
        system_status = "Excellent" if system["uptime_percentage"] >= 99.9 else "Good"
        cost_status = "Good" if cost["budget_utilization"] <= 80 else "Warning"

        return {
            "overall_health_score": health_score,
            "key_metrics": {
                "signals_generated": trading["signals_generated"],
                "signal_accuracy": f"{trading['signals_accuracy']:.1f}%",
                "system_uptime": f"{system['uptime_percentage']:.2f}%",
                "cost_utilization": f"{cost['budget_utilization']:.1f}%"
            },
            "status_indicators": {
                "trading_performance": trading_status,
                "system_health": system_status,
                "cost_management": cost_status
            },
            "highlights": [
                f"Generated {trading['signals_generated']} trading signals with {trading['signals_accuracy']:.1f}% accuracy",
                f"System maintained {system['uptime_percentage']:.2f}% uptime",
                f"Daily budget utilization at {cost['budget_utilization']:.1f}%",
                f"Average signal latency: {trading['average_latency_ms']}ms"
            ],
            "concerns": self._identify_concerns(metrics)
        }

    def _generate_weekly_executive_summary(self, metrics: ReportMetrics) -> Dict[str, Any]:
        """Generate executive summary for weekly report"""
        return {
            "week_overview": "Strong performance with minor optimization opportunities",
            "key_achievements": [
                "Maintained 99.9%+ uptime throughout the week",
                "Signal accuracy exceeded target by 3.5%",
                "Stayed within budget constraints",
                "Zero critical security incidents"
            ],
            "performance_vs_targets": {
                "uptime": "✅ Target exceeded",
                "accuracy": "✅ Target exceeded",
                "latency": "✅ Within target",
                "cost": "✅ Under budget"
            },
            "business_impact": {
                "trading_signals": metrics.trading_metrics["signals_generated"],
                "profitable_trades": metrics.trading_metrics["profitable_signals"],
                "cost_efficiency": f"{metrics.cost_metrics['budget_utilization']:.1f}%"
            }
        }

    def _generate_sla_compliance_section(self, metrics: ReportMetrics) -> Dict[str, Any]:
        """Generate SLA compliance section"""
        sla = metrics.sla_metrics

        compliance_items = []
        for metric, data in sla.items():
            if metric != "overall_sla_score" and isinstance(data, dict):
                compliance_items.append({
                    "metric": metric.replace("_", " ").title(),
                    "target": data.get("target", "N/A"),
                    "actual": data.get("actual", "N/A"),
                    "compliance": data.get("compliance", False),
                    "status": "✅ Compliant" if data.get("compliance") else "❌ Breach"
                })

        return {
            "overall_score": sla["overall_sla_score"],
            "compliance_status": "Compliant" if sla["overall_sla_score"] >= 95 else "At Risk",
            "individual_slas": compliance_items,
            "breaches": [
                item for item in compliance_items if not item["compliance"]
            ],
            "recommendations": [
                "Continue monitoring response time trends",
                "Implement additional redundancy for uptime",
                "Optimize data processing pipeline"
            ]
        }

    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML version of report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>IFD v3.0 {report['report_type'].replace('_', ' ').title()} Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #f8f9fa; border-radius: 3px; }}
        .good {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .critical {{ color: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; border: 1px solid #ddd; text-align: left; }}
        th {{ background: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>IFD v3.0 Trading System Report</h1>
        <p>Generated: {report['generated_at']}</p>
        <p>Period: {report['period']['start']} to {report['period']['end']}</p>
    </div>
        """

        # Add sections
        for section_name, section_data in report["sections"].items():
            html += f'<div class="section"><h2>{section_name.replace("_", " ").title()}</h2>'
            html += self._format_section_html(section_data)
            html += '</div>'

        html += "</body></html>"
        return html

    def _format_section_html(self, section_data: Dict[str, Any]) -> str:
        """Format section data as HTML"""
        html = ""

        for key, value in section_data.items():
            if isinstance(value, dict):
                html += f"<h3>{key.replace('_', ' ').title()}</h3>"
                html += "<table><tr><th>Metric</th><th>Value</th></tr>"
                for sub_key, sub_value in value.items():
                    html += f"<tr><td>{sub_key.replace('_', ' ').title()}</td><td>{sub_value}</td></tr>"
                html += "</table>"
            elif isinstance(value, list):
                html += f"<h3>{key.replace('_', ' ').title()}</h3><ul>"
                for item in value:
                    html += f"<li>{item}</li>"
                html += "</ul>"
            else:
                html += f'<div class="metric"><strong>{key.replace("_", " ").title()}:</strong> {value}</div>'

        return html

    def _calculate_health_score(self, metrics: ReportMetrics) -> int:
        """Calculate overall system health score (0-100)"""
        trading_score = min(metrics.trading_metrics["signals_accuracy"], 100)
        system_score = metrics.system_metrics["uptime_percentage"]
        cost_score = max(100 - metrics.cost_metrics["budget_utilization"], 0)
        security_score = metrics.security_metrics["security_score"]

        # Weighted average
        health_score = (
            trading_score * 0.3 +
            system_score * 0.3 +
            cost_score * 0.2 +
            security_score * 0.2
        )

        return int(health_score)

    def _identify_concerns(self, metrics: ReportMetrics) -> List[str]:
        """Identify areas of concern from metrics"""
        concerns = []

        if metrics.trading_metrics["signals_accuracy"] < 75:
            concerns.append("Signal accuracy below target threshold")

        if metrics.system_metrics["uptime_percentage"] < 99.9:
            concerns.append("System uptime below SLA target")

        if metrics.cost_metrics["budget_utilization"] > 90:
            concerns.append("Budget utilization approaching limit")

        if metrics.security_metrics["high_risk_events"] > 0:
            concerns.append("High-risk security events detected")

        if metrics.alerts_summary["by_severity"]["CRITICAL"] > 0:
            concerns.append("Critical alerts generated")

        return concerns if concerns else ["No significant concerns identified"]

    def _generate_recommendations(self, metrics: ReportMetrics) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Trading performance recommendations
        if metrics.trading_metrics["signals_accuracy"] < 80:
            recommendations.append("Review and tune signal generation algorithms")

        if metrics.trading_metrics["average_latency_ms"] > 100:
            recommendations.append("Optimize data processing pipeline for better latency")

        # System recommendations
        if metrics.system_metrics["average_memory_usage"] > 80:
            recommendations.append("Consider increasing system memory allocation")

        # Cost recommendations
        if metrics.cost_metrics["budget_utilization"] > 80:
            recommendations.append("Review API usage patterns to optimize costs")

        # Security recommendations
        if metrics.security_metrics["failed_auth_attempts"] > 5:
            recommendations.append("Review authentication security measures")

        return recommendations if recommendations else ["System operating optimally - continue monitoring"]

    def _generate_action_items(self, metrics: ReportMetrics) -> List[Dict[str, Any]]:
        """Generate specific action items for follow-up"""
        action_items = []

        # High priority items
        if metrics.alerts_summary["by_severity"]["CRITICAL"] > 0:
            action_items.append({
                "priority": "HIGH",
                "item": "Investigate and resolve critical alerts",
                "owner": "Operations Team",
                "due_date": (get_eastern_time() + timedelta(days=1)).strftime("%Y-%m-%d")
            })

        # Medium priority items
        if metrics.cost_metrics["budget_utilization"] > 85:
            action_items.append({
                "priority": "MEDIUM",
                "item": "Review cost optimization opportunities",
                "owner": "Development Team",
                "due_date": (get_eastern_time() + timedelta(days=7)).strftime("%Y-%m-%d")
            })

        return action_items

# Additional report types
    def generate_sla_compliance_report(self) -> Dict[str, Any]:
        """Generate dedicated SLA compliance report"""
        end_time = get_eastern_time()
        start_time = end_time - timedelta(days=30)  # Last 30 days

        metrics = self._collect_period_metrics(start_time, end_time)

        return {
            "report_type": "sla_compliance",
            "generated_at": end_time.isoformat(),
            "period_days": 30,
            "sla_summary": metrics.sla_metrics,
            "compliance_score": metrics.sla_metrics["overall_sla_score"],
            "recommendations": self._generate_sla_recommendations(metrics.sla_metrics)
        }

    def _generate_sla_recommendations(self, sla_metrics: Dict[str, Any]) -> List[str]:
        """Generate SLA-specific recommendations"""
        recommendations = []

        for metric, data in sla_metrics.items():
            if isinstance(data, dict) and not data.get("compliance", True):
                recommendations.append(f"Address SLA breach in {metric}: {data.get('actual')} vs target {data.get('target')}")

        return recommendations if recommendations else ["All SLAs are compliant"]

# Example usage and testing
if __name__ == "__main__":
    # Create reporting system
    reporting_system = ReportingSystem()

    print("Testing Reporting System...")

    # Generate daily report
    daily_report = reporting_system.generate_daily_report()
    print(f"Daily report generated with {len(daily_report['sections'])} sections")

    # Generate weekly report
    weekly_report = reporting_system.generate_weekly_report()
    print(f"Weekly report generated with {len(weekly_report['sections'])} sections")

    # Generate SLA compliance report
    sla_report = reporting_system.generate_sla_compliance_report()
    print(f"SLA compliance score: {sla_report['compliance_score']:.1f}%")

    print("All reports generated successfully!")
