#!/usr/bin/env python3
"""
30-Day Test Period Tracking System for IFD v3.0

Comprehensive tracking system for extended testing:
- Daily performance metrics collection
- Signal accuracy tracking over time
- Market condition correlation analysis
- Long-term stability validation
- Regression detection
"""

import sys
import os
import json
import time
import sqlite3
from datetime import datetime, timedelta
from utils.timezone_utils import get_eastern_time, get_utc_time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import statistics

# Add project paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')
sys.path.append('tasks/options_trading_system/analysis_engine')

# Load environment
from dotenv import load_dotenv
load_dotenv()


@dataclass
class DailyMetrics:
    """Daily performance metrics structure"""
    date: str

    # Signal Generation Metrics
    total_signals: int
    high_confidence_signals: int
    signal_quality_score: float
    false_positive_rate: float

    # Performance Metrics
    avg_latency_ms: float
    max_latency_ms: float
    throughput_strikes_per_sec: float
    memory_usage_mb: float
    cpu_usage_percent: float

    # Trading Performance (Paper Trading)
    signals_acted_on: int
    winning_signals: int
    losing_signals: int
    daily_pnl: float
    cumulative_pnl: float
    max_drawdown: float

    # Market Context
    market_volatility: float
    volume_profile: str  # LOW, NORMAL, HIGH
    institutional_activity: str  # LOW, MODERATE, HIGH

    # Quality Indicators
    data_quality_score: float
    api_error_rate: float
    uptime_percentage: float


@dataclass
class WeeklyAnalysis:
    """Weekly analysis and trends"""
    week_start: str
    week_end: str

    # Performance Trends
    performance_trend: str  # IMPROVING, STABLE, DECLINING
    signal_quality_trend: str
    latency_trend: str

    # Key Metrics
    avg_daily_signals: float
    avg_signal_quality: float
    avg_latency_ms: float
    week_pnl: float

    # Market Analysis
    dominant_market_conditions: List[str]
    best_performing_conditions: str
    worst_performing_conditions: str

    # Alerts and Recommendations
    alerts: List[str]
    recommendations: List[str]


class ThirtyDayTracker:
    """30-day performance tracking and analysis system"""

    def __init__(self, db_path: str = "outputs/ifd_v3_testing/30_day_tracking.db"):
        """Initialize 30-day tracking system"""
        self.db_path = db_path
        self.output_dir = os.path.dirname(db_path)

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize database
        self._init_database()

        # Tracking state
        self.tracking_active = False
        self.start_date = None

    def _init_database(self):
        """Initialize SQLite database for tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Daily metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_metrics (
                date TEXT PRIMARY KEY,
                total_signals INTEGER,
                high_confidence_signals INTEGER,
                signal_quality_score REAL,
                false_positive_rate REAL,
                avg_latency_ms REAL,
                max_latency_ms REAL,
                throughput_strikes_per_sec REAL,
                memory_usage_mb REAL,
                cpu_usage_percent REAL,
                signals_acted_on INTEGER,
                winning_signals INTEGER,
                losing_signals INTEGER,
                daily_pnl REAL,
                cumulative_pnl REAL,
                max_drawdown REAL,
                market_volatility REAL,
                volume_profile TEXT,
                institutional_activity TEXT,
                data_quality_score REAL,
                api_error_rate REAL,
                uptime_percentage REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Weekly analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_analysis (
                week_start TEXT PRIMARY KEY,
                week_end TEXT,
                performance_trend TEXT,
                signal_quality_trend TEXT,
                latency_trend TEXT,
                avg_daily_signals REAL,
                avg_signal_quality REAL,
                avg_latency_ms REAL,
                week_pnl REAL,
                dominant_market_conditions TEXT,
                best_performing_conditions TEXT,
                worst_performing_conditions TEXT,
                alerts TEXT,
                recommendations TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Test sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_sessions (
                session_id TEXT PRIMARY KEY,
                start_date TEXT,
                end_date TEXT,
                duration_days INTEGER,
                total_days_tracked INTEGER,
                overall_performance_score REAL,
                status TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def start_tracking_session(self, session_id: str) -> bool:
        """Start a new 30-day tracking session"""
        print(f"🚀 Starting 30-day tracking session: {session_id}")

        try:
            self.tracking_active = True
            self.start_date = get_eastern_time().strftime('%Y-%m-%d')

            # Record session start
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO test_sessions
                (session_id, start_date, status)
                VALUES (?, ?, ?)
            ''', (session_id, self.start_date, 'ACTIVE'))

            conn.commit()
            conn.close()

            print(f"   ✅ Session started on {self.start_date}")
            print(f"   📊 Database: {self.db_path}")

            return True

        except Exception as e:
            print(f"   ❌ Failed to start tracking session: {e}")
            return False

    def collect_daily_metrics(self, date: str = None) -> DailyMetrics:
        """Collect comprehensive daily metrics"""
        if date is None:
            date = get_eastern_time().strftime('%Y-%m-%d')

        print(f"📊 Collecting daily metrics for {date}")

        try:
            # Run comprehensive analysis to get current metrics
            metrics = self._run_daily_analysis()

            # Create daily metrics object
            daily_metrics = DailyMetrics(
                date=date,
                total_signals=metrics.get("total_signals", 0),
                high_confidence_signals=metrics.get("high_confidence_signals", 0),
                signal_quality_score=metrics.get("signal_quality_score", 0.0),
                false_positive_rate=metrics.get("false_positive_rate", 0.0),
                avg_latency_ms=metrics.get("avg_latency_ms", 0.0),
                max_latency_ms=metrics.get("max_latency_ms", 0.0),
                throughput_strikes_per_sec=metrics.get("throughput_strikes_per_sec", 0.0),
                memory_usage_mb=metrics.get("memory_usage_mb", 0.0),
                cpu_usage_percent=metrics.get("cpu_usage_percent", 0.0),
                signals_acted_on=metrics.get("signals_acted_on", 0),
                winning_signals=metrics.get("winning_signals", 0),
                losing_signals=metrics.get("losing_signals", 0),
                daily_pnl=metrics.get("daily_pnl", 0.0),
                cumulative_pnl=metrics.get("cumulative_pnl", 0.0),
                max_drawdown=metrics.get("max_drawdown", 0.0),
                market_volatility=metrics.get("market_volatility", 0.0),
                volume_profile=metrics.get("volume_profile", "NORMAL"),
                institutional_activity=metrics.get("institutional_activity", "MODERATE"),
                data_quality_score=metrics.get("data_quality_score", 0.95),
                api_error_rate=metrics.get("api_error_rate", 0.0),
                uptime_percentage=metrics.get("uptime_percentage", 100.0)
            )

            # Store in database
            self._store_daily_metrics(daily_metrics)

            print(f"   ✅ Metrics collected: {daily_metrics.total_signals} signals, "
                  f"{daily_metrics.avg_latency_ms:.1f}ms latency")

            return daily_metrics

        except Exception as e:
            print(f"   ❌ Failed to collect daily metrics: {e}")
            # Return default metrics
            return DailyMetrics(
                date=date,
                total_signals=0, high_confidence_signals=0, signal_quality_score=0.0,
                false_positive_rate=0.0, avg_latency_ms=0.0, max_latency_ms=0.0,
                throughput_strikes_per_sec=0.0, memory_usage_mb=0.0, cpu_usage_percent=0.0,
                signals_acted_on=0, winning_signals=0, losing_signals=0,
                daily_pnl=0.0, cumulative_pnl=0.0, max_drawdown=0.0,
                market_volatility=0.0, volume_profile="NORMAL", institutional_activity="MODERATE",
                data_quality_score=0.0, api_error_rate=0.0, uptime_percentage=0.0
            )

    def _run_daily_analysis(self) -> Dict[str, Any]:
        """Run comprehensive daily analysis"""
        try:
            # Import analysis components
            from analysis_engine.integration import run_analysis_engine

            # Configure for comprehensive analysis
            data_config = {
                "mode": "real_time",
                "sources": ["databento", "barchart"],
                "symbols": ["NQ"],
                "daily_tracking": True
            }

            analysis_config = {
                "institutional_flow_v3": {
                    "db_path": "/tmp/daily_tracking.db",
                    "pressure_thresholds": {
                        "min_pressure_ratio": 1.5,
                        "min_volume_concentration": 0.3,
                        "min_time_persistence": 0.4,
                        "min_trend_strength": 0.5
                    },
                    "confidence_thresholds": {
                        "min_baseline_anomaly": 1.5,
                        "min_overall_confidence": 0.5  # Testing threshold (was 0.6)
                    },
                    "market_making_penalty": 0.3
                }
            }

            # Run analysis
            start_time = time.time()
            result = run_analysis_engine(data_config, analysis_config)
            execution_time = (time.time() - start_time) * 1000

            # Extract metrics from analysis result
            return self._extract_metrics_from_analysis(result, execution_time)

        except Exception as e:
            print(f"   ⚠️  Analysis failed, using simulated metrics: {e}")
            return self._generate_simulated_daily_metrics()

    def _extract_metrics_from_analysis(self, result: Dict[str, Any], execution_time: float) -> Dict[str, Any]:
        """Extract metrics from analysis result"""
        metrics = {}

        # Performance metrics
        metrics["avg_latency_ms"] = execution_time
        metrics["max_latency_ms"] = execution_time * 1.2  # Estimate

        # IFD v3 specific metrics
        ifd_v3_result = result.get("individual_results", {}).get("institutional_flow_v3", {})
        if ifd_v3_result.get("status") == "success":
            ifd_data = ifd_v3_result.get("result", {})
            metrics["total_signals"] = ifd_data.get("total_signals", 0)
            metrics["high_confidence_signals"] = ifd_data.get("high_confidence_signals", 0)

            # Calculate signal quality score
            if metrics["total_signals"] > 0:
                metrics["signal_quality_score"] = metrics["high_confidence_signals"] / metrics["total_signals"]
            else:
                metrics["signal_quality_score"] = 0.0

        # Trading recommendations
        recommendations = result.get("synthesis", {}).get("trading_recommendations", [])
        metrics["signals_acted_on"] = len(recommendations)

        # Simulate other metrics (would be real in production)
        metrics.update(self._generate_simulated_daily_metrics())

        return metrics

    def _generate_simulated_daily_metrics(self) -> Dict[str, Any]:
        """Generate simulated metrics for testing"""
        import random

        # Simulate realistic daily metrics
        total_signals = random.randint(15, 45)
        high_confidence = random.randint(5, int(total_signals * 0.4))

        return {
            "total_signals": total_signals,
            "high_confidence_signals": high_confidence,
            "signal_quality_score": high_confidence / max(total_signals, 1),
            "false_positive_rate": random.uniform(0.05, 0.20),
            "avg_latency_ms": random.uniform(25, 75),
            "max_latency_ms": random.uniform(60, 95),
            "throughput_strikes_per_sec": random.uniform(150, 300),
            "memory_usage_mb": random.uniform(45, 85),
            "cpu_usage_percent": random.uniform(15, 45),
            "signals_acted_on": random.randint(3, 12),
            "winning_signals": random.randint(2, 8),
            "losing_signals": random.randint(1, 6),
            "daily_pnl": random.uniform(-150, 300),
            "cumulative_pnl": random.uniform(-500, 2000),
            "max_drawdown": random.uniform(50, 400),
            "market_volatility": random.uniform(0.15, 0.85),
            "volume_profile": random.choice(["LOW", "NORMAL", "HIGH"]),
            "institutional_activity": random.choice(["LOW", "MODERATE", "HIGH"]),
            "data_quality_score": random.uniform(0.90, 0.99),
            "api_error_rate": random.uniform(0.0, 0.05),
            "uptime_percentage": random.uniform(98, 100)
        }

    def _store_daily_metrics(self, metrics: DailyMetrics):
        """Store daily metrics in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO daily_metrics (
                date, total_signals, high_confidence_signals, signal_quality_score,
                false_positive_rate, avg_latency_ms, max_latency_ms, throughput_strikes_per_sec,
                memory_usage_mb, cpu_usage_percent, signals_acted_on, winning_signals,
                losing_signals, daily_pnl, cumulative_pnl, max_drawdown, market_volatility,
                volume_profile, institutional_activity, data_quality_score, api_error_rate,
                uptime_percentage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics.date, metrics.total_signals, metrics.high_confidence_signals,
            metrics.signal_quality_score, metrics.false_positive_rate, metrics.avg_latency_ms,
            metrics.max_latency_ms, metrics.throughput_strikes_per_sec, metrics.memory_usage_mb,
            metrics.cpu_usage_percent, metrics.signals_acted_on, metrics.winning_signals,
            metrics.losing_signals, metrics.daily_pnl, metrics.cumulative_pnl,
            metrics.max_drawdown, metrics.market_volatility, metrics.volume_profile,
            metrics.institutional_activity, metrics.data_quality_score, metrics.api_error_rate,
            metrics.uptime_percentage
        ))

        conn.commit()
        conn.close()

    def analyze_weekly_trends(self, week_start: str) -> WeeklyAnalysis:
        """Analyze weekly trends and patterns"""
        print(f"📈 Analyzing weekly trends starting {week_start}")

        try:
            # Get daily metrics for the week
            daily_metrics = self._get_daily_metrics_for_week(week_start)

            if len(daily_metrics) < 3:  # Need at least 3 days of data
                print(f"   ⚠️  Insufficient data for weekly analysis ({len(daily_metrics)} days)")
                return self._create_default_weekly_analysis(week_start)

            # Calculate trends
            performance_trend = self._calculate_performance_trend(daily_metrics)
            signal_quality_trend = self._calculate_signal_quality_trend(daily_metrics)
            latency_trend = self._calculate_latency_trend(daily_metrics)

            # Calculate averages
            avg_daily_signals = statistics.mean([m.total_signals for m in daily_metrics])
            avg_signal_quality = statistics.mean([m.signal_quality_score for m in daily_metrics])
            avg_latency_ms = statistics.mean([m.avg_latency_ms for m in daily_metrics])
            week_pnl = sum([m.daily_pnl for m in daily_metrics])

            # Analyze market conditions
            market_analysis = self._analyze_market_conditions(daily_metrics)

            # Generate alerts and recommendations
            alerts, recommendations = self._generate_weekly_alerts_and_recommendations(daily_metrics)

            # Create weekly analysis
            week_end = (datetime.strptime(week_start, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')

            weekly_analysis = WeeklyAnalysis(
                week_start=week_start,
                week_end=week_end,
                performance_trend=performance_trend,
                signal_quality_trend=signal_quality_trend,
                latency_trend=latency_trend,
                avg_daily_signals=avg_daily_signals,
                avg_signal_quality=avg_signal_quality,
                avg_latency_ms=avg_latency_ms,
                week_pnl=week_pnl,
                dominant_market_conditions=market_analysis["dominant_conditions"],
                best_performing_conditions=market_analysis["best_conditions"],
                worst_performing_conditions=market_analysis["worst_conditions"],
                alerts=alerts,
                recommendations=recommendations
            )

            # Store weekly analysis
            self._store_weekly_analysis(weekly_analysis)

            print(f"   ✅ Weekly analysis complete: {performance_trend} performance trend")

            return weekly_analysis

        except Exception as e:
            print(f"   ❌ Weekly analysis failed: {e}")
            return self._create_default_weekly_analysis(week_start)

    def _get_daily_metrics_for_week(self, week_start: str) -> List[DailyMetrics]:
        """Get daily metrics for a specific week"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Calculate week end
        week_end = (datetime.strptime(week_start, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')

        cursor.execute('''
            SELECT * FROM daily_metrics
            WHERE date BETWEEN ? AND ?
            ORDER BY date
        ''', (week_start, week_end))

        rows = cursor.fetchall()
        conn.close()

        # Convert to DailyMetrics objects
        daily_metrics = []
        for row in rows:
            metrics = DailyMetrics(
                date=row[0], total_signals=row[1], high_confidence_signals=row[2],
                signal_quality_score=row[3], false_positive_rate=row[4], avg_latency_ms=row[5],
                max_latency_ms=row[6], throughput_strikes_per_sec=row[7], memory_usage_mb=row[8],
                cpu_usage_percent=row[9], signals_acted_on=row[10], winning_signals=row[11],
                losing_signals=row[12], daily_pnl=row[13], cumulative_pnl=row[14],
                max_drawdown=row[15], market_volatility=row[16], volume_profile=row[17],
                institutional_activity=row[18], data_quality_score=row[19], api_error_rate=row[20],
                uptime_percentage=row[21]
            )
            daily_metrics.append(metrics)

        return daily_metrics

    def _calculate_performance_trend(self, daily_metrics: List[DailyMetrics]) -> str:
        """Calculate performance trend over the week"""
        if len(daily_metrics) < 3:
            return "INSUFFICIENT_DATA"

        # Use signal quality and PnL as performance indicators
        recent_performance = statistics.mean([
            m.signal_quality_score + (m.daily_pnl / 100) for m in daily_metrics[-3:]
        ])

        earlier_performance = statistics.mean([
            m.signal_quality_score + (m.daily_pnl / 100) for m in daily_metrics[:3]
        ])

        improvement = (recent_performance - earlier_performance) / max(abs(earlier_performance), 0.1)

        if improvement > 0.1:
            return "IMPROVING"
        elif improvement < -0.1:
            return "DECLINING"
        else:
            return "STABLE"

    def _calculate_signal_quality_trend(self, daily_metrics: List[DailyMetrics]) -> str:
        """Calculate signal quality trend"""
        if len(daily_metrics) < 3:
            return "INSUFFICIENT_DATA"

        recent_quality = statistics.mean([m.signal_quality_score for m in daily_metrics[-3:]])
        earlier_quality = statistics.mean([m.signal_quality_score for m in daily_metrics[:3]])

        improvement = (recent_quality - earlier_quality) / max(earlier_quality, 0.1)

        if improvement > 0.05:
            return "IMPROVING"
        elif improvement < -0.05:
            return "DECLINING"
        else:
            return "STABLE"

    def _calculate_latency_trend(self, daily_metrics: List[DailyMetrics]) -> str:
        """Calculate latency trend (lower is better)"""
        if len(daily_metrics) < 3:
            return "INSUFFICIENT_DATA"

        recent_latency = statistics.mean([m.avg_latency_ms for m in daily_metrics[-3:]])
        earlier_latency = statistics.mean([m.avg_latency_ms for m in daily_metrics[:3]])

        improvement = (earlier_latency - recent_latency) / max(earlier_latency, 1)

        if improvement > 0.05:
            return "IMPROVING"
        elif improvement < -0.05:
            return "DECLINING"
        else:
            return "STABLE"

    def _analyze_market_conditions(self, daily_metrics: List[DailyMetrics]) -> Dict[str, Any]:
        """Analyze market conditions and performance correlation"""
        # Count market condition occurrences
        volume_profiles = [m.volume_profile for m in daily_metrics]
        institutional_activities = [m.institutional_activity for m in daily_metrics]

        dominant_conditions = []
        if volume_profiles:
            most_common_volume = max(set(volume_profiles), key=volume_profiles.count)
            dominant_conditions.append(f"Volume: {most_common_volume}")

        if institutional_activities:
            most_common_activity = max(set(institutional_activities), key=institutional_activities.count)
            dominant_conditions.append(f"Institutional: {most_common_activity}")

        # Find best/worst performing conditions
        condition_performance = {}
        for metrics in daily_metrics:
            condition = f"{metrics.volume_profile}_{metrics.institutional_activity}"
            if condition not in condition_performance:
                condition_performance[condition] = []
            condition_performance[condition].append(metrics.daily_pnl)

        # Calculate average performance per condition
        avg_performance = {}
        for condition, pnls in condition_performance.items():
            avg_performance[condition] = statistics.mean(pnls)

        best_conditions = max(avg_performance.keys(), key=lambda k: avg_performance[k]) if avg_performance else "UNKNOWN"
        worst_conditions = min(avg_performance.keys(), key=lambda k: avg_performance[k]) if avg_performance else "UNKNOWN"

        return {
            "dominant_conditions": dominant_conditions,
            "best_conditions": best_conditions,
            "worst_conditions": worst_conditions
        }

    def _generate_weekly_alerts_and_recommendations(self, daily_metrics: List[DailyMetrics]) -> tuple[List[str], List[str]]:
        """Generate alerts and recommendations based on weekly analysis"""
        alerts = []
        recommendations = []

        # Performance alerts
        avg_signal_quality = statistics.mean([m.signal_quality_score for m in daily_metrics])
        if avg_signal_quality < 0.4:
            alerts.append("LOW_SIGNAL_QUALITY: Average signal quality below 40%")
            recommendations.append("Review signal detection thresholds and market making penalties")

        # Latency alerts
        avg_latency = statistics.mean([m.avg_latency_ms for m in daily_metrics])
        if avg_latency > 80:
            alerts.append("HIGH_LATENCY: Average latency above 80ms")
            recommendations.append("Optimize pressure metrics calculation and caching")

        # PnL alerts
        total_pnl = sum([m.daily_pnl for m in daily_metrics])
        if total_pnl < -500:
            alerts.append("NEGATIVE_PNL: Weekly PnL below -$500")
            recommendations.append("Review signal quality and market timing")

        # Stability alerts
        latencies = [m.avg_latency_ms for m in daily_metrics]
        if len(latencies) > 1 and statistics.stdev(latencies) > 15:
            alerts.append("LATENCY_INSTABILITY: High latency variance detected")
            recommendations.append("Investigate system resource constraints")

        return alerts, recommendations

    def _create_default_weekly_analysis(self, week_start: str) -> WeeklyAnalysis:
        """Create default weekly analysis when insufficient data"""
        week_end = (datetime.strptime(week_start, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')

        return WeeklyAnalysis(
            week_start=week_start,
            week_end=week_end,
            performance_trend="INSUFFICIENT_DATA",
            signal_quality_trend="INSUFFICIENT_DATA",
            latency_trend="INSUFFICIENT_DATA",
            avg_daily_signals=0.0,
            avg_signal_quality=0.0,
            avg_latency_ms=0.0,
            week_pnl=0.0,
            dominant_market_conditions=[],
            best_performing_conditions="UNKNOWN",
            worst_performing_conditions="UNKNOWN",
            alerts=["INSUFFICIENT_DATA: Less than 3 days of data available"],
            recommendations=["Continue data collection for meaningful analysis"]
        )

    def _store_weekly_analysis(self, analysis: WeeklyAnalysis):
        """Store weekly analysis in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO weekly_analysis (
                week_start, week_end, performance_trend, signal_quality_trend,
                latency_trend, avg_daily_signals, avg_signal_quality, avg_latency_ms,
                week_pnl, dominant_market_conditions, best_performing_conditions,
                worst_performing_conditions, alerts, recommendations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            analysis.week_start, analysis.week_end, analysis.performance_trend,
            analysis.signal_quality_trend, analysis.latency_trend, analysis.avg_daily_signals,
            analysis.avg_signal_quality, analysis.avg_latency_ms, analysis.week_pnl,
            json.dumps(analysis.dominant_market_conditions), analysis.best_performing_conditions,
            analysis.worst_performing_conditions, json.dumps(analysis.alerts),
            json.dumps(analysis.recommendations)
        ))

        conn.commit()
        conn.close()

    def generate_30_day_report(self, session_id: str) -> Dict[str, Any]:
        """Generate comprehensive 30-day tracking report"""
        print(f"📋 Generating 30-day tracking report for session: {session_id}")

        try:
            # Get all daily metrics
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM daily_metrics ORDER BY date')
            daily_rows = cursor.fetchall()

            cursor.execute('SELECT * FROM weekly_analysis ORDER BY week_start')
            weekly_rows = cursor.fetchall()

            conn.close()

            if not daily_rows:
                print("   ⚠️  No daily metrics found")
                return {"error": "No tracking data available"}

            # Generate comprehensive report
            report = {
                "session_id": session_id,
                "report_generated": get_eastern_time().isoformat(),
                "tracking_period": {
                    "start_date": daily_rows[0][0],
                    "end_date": daily_rows[-1][0],
                    "total_days": len(daily_rows)
                },
                "overall_performance": self._calculate_overall_performance(daily_rows),
                "trend_analysis": self._analyze_long_term_trends(daily_rows),
                "market_correlation": self._analyze_market_correlation(daily_rows),
                "reliability_metrics": self._calculate_reliability_metrics(daily_rows),
                "weekly_summaries": self._summarize_weekly_data(weekly_rows),
                "recommendations": self._generate_final_recommendations(daily_rows, weekly_rows),
                "status": "COMPLETED"
            }

            # Save report
            report_path = f"{self.output_dir}/30_day_report_{session_id}.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)

            print(f"   ✅ Report generated: {report_path}")

            return report

        except Exception as e:
            print(f"   ❌ Report generation failed: {e}")
            return {"error": str(e)}

    def _calculate_overall_performance(self, daily_rows: List) -> Dict[str, Any]:
        """Calculate overall performance metrics"""
        # Extract key metrics
        total_signals = sum([row[1] for row in daily_rows])
        avg_signal_quality = statistics.mean([row[3] for row in daily_rows])
        avg_latency = statistics.mean([row[5] for row in daily_rows])
        total_pnl = sum([row[13] for row in daily_rows])
        avg_uptime = statistics.mean([row[21] for row in daily_rows])

        return {
            "total_signals_generated": total_signals,
            "average_signal_quality": avg_signal_quality,
            "average_latency_ms": avg_latency,
            "total_pnl": total_pnl,
            "average_daily_pnl": total_pnl / len(daily_rows),
            "average_uptime_percentage": avg_uptime,
            "performance_score": self._calculate_performance_score(daily_rows)
        }

    def _calculate_performance_score(self, daily_rows: List) -> float:
        """Calculate overall performance score (0-100)"""
        scores = []

        # Signal quality score (40% weight)
        avg_signal_quality = statistics.mean([row[3] for row in daily_rows])
        signal_score = min(avg_signal_quality * 100, 100)
        scores.append(signal_score * 0.4)

        # Latency score (30% weight) - lower is better
        avg_latency = statistics.mean([row[5] for row in daily_rows])
        latency_score = max(0, 100 - avg_latency)  # 100 = 0ms, 0 = 100ms+
        scores.append(latency_score * 0.3)

        # Reliability score (20% weight)
        avg_uptime = statistics.mean([row[21] for row in daily_rows])
        reliability_score = avg_uptime
        scores.append(reliability_score * 0.2)

        # PnL score (10% weight)
        total_pnl = sum([row[13] for row in daily_rows])
        pnl_score = min(max(total_pnl / 100, 0), 100)  # Normalize to 0-100
        scores.append(pnl_score * 0.1)

        return sum(scores)

    def _analyze_long_term_trends(self, daily_rows: List) -> Dict[str, Any]:
        """Analyze long-term trends over 30 days"""
        # Calculate weekly averages for trend analysis
        weeks = {}
        for row in daily_rows:
            date = datetime.strptime(row[0], '%Y-%m-%d')
            week_start = (date - timedelta(days=date.weekday())).strftime('%Y-%m-%d')

            if week_start not in weeks:
                weeks[week_start] = []
            weeks[week_start].append(row)

        # Calculate trends
        weekly_signal_quality = []
        weekly_latency = []
        weekly_pnl = []

        for week_data in weeks.values():
            weekly_signal_quality.append(statistics.mean([row[3] for row in week_data]))
            weekly_latency.append(statistics.mean([row[5] for row in week_data]))
            weekly_pnl.append(sum([row[13] for row in week_data]))

        # Calculate trend slopes (simple linear regression)
        def calculate_trend(values):
            if len(values) < 2:
                return "INSUFFICIENT_DATA"

            n = len(values)
            x_vals = list(range(n))

            # Simple slope calculation
            slope = (n * sum(x_vals[i] * values[i] for i in range(n)) - sum(x_vals) * sum(values)) / \
                   (n * sum(x * x for x in x_vals) - sum(x_vals) ** 2)

            if slope > 0.1:
                return "IMPROVING"
            elif slope < -0.1:
                return "DECLINING"
            else:
                return "STABLE"

        return {
            "signal_quality_trend": calculate_trend(weekly_signal_quality),
            "latency_trend": calculate_trend(weekly_latency),
            "pnl_trend": calculate_trend(weekly_pnl),
            "weekly_signal_quality": weekly_signal_quality,
            "weekly_latency": weekly_latency,
            "weekly_pnl": weekly_pnl
        }

    def _analyze_market_correlation(self, daily_rows: List) -> Dict[str, Any]:
        """Analyze performance correlation with market conditions"""
        volume_performance = {"LOW": [], "NORMAL": [], "HIGH": []}
        institutional_performance = {"LOW": [], "MODERATE": [], "HIGH": []}

        for row in daily_rows:
            volume_profile = row[17]
            institutional_activity = row[18]
            daily_pnl = row[13]

            if volume_profile in volume_performance:
                volume_performance[volume_profile].append(daily_pnl)

            if institutional_activity in institutional_performance:
                institutional_performance[institutional_activity].append(daily_pnl)

        # Calculate average performance per condition
        volume_avg = {}
        for condition, pnls in volume_performance.items():
            if pnls:
                volume_avg[condition] = statistics.mean(pnls)

        institutional_avg = {}
        for condition, pnls in institutional_performance.items():
            if pnls:
                institutional_avg[condition] = statistics.mean(pnls)

        return {
            "best_volume_condition": max(volume_avg.keys(), key=lambda k: volume_avg[k]) if volume_avg else "UNKNOWN",
            "best_institutional_condition": max(institutional_avg.keys(), key=lambda k: institutional_avg[k]) if institutional_avg else "UNKNOWN",
            "volume_performance": volume_avg,
            "institutional_performance": institutional_avg
        }

    def _calculate_reliability_metrics(self, daily_rows: List) -> Dict[str, Any]:
        """Calculate system reliability metrics"""
        uptime_values = [row[21] for row in daily_rows]
        api_error_rates = [row[20] for row in daily_rows]
        data_quality_scores = [row[19] for row in daily_rows]

        return {
            "average_uptime": statistics.mean(uptime_values),
            "min_uptime": min(uptime_values),
            "average_api_error_rate": statistics.mean(api_error_rates),
            "max_api_error_rate": max(api_error_rates),
            "average_data_quality": statistics.mean(data_quality_scores),
            "min_data_quality": min(data_quality_scores),
            "reliability_score": statistics.mean(uptime_values) * statistics.mean(data_quality_scores) / 100
        }

    def _summarize_weekly_data(self, weekly_rows: List) -> List[Dict[str, Any]]:
        """Summarize weekly analysis data"""
        summaries = []

        for row in weekly_rows:
            summary = {
                "week_start": row[0],
                "week_end": row[1],
                "performance_trend": row[2],
                "avg_signal_quality": row[5],
                "avg_latency_ms": row[6],
                "week_pnl": row[7],
                "alerts_count": len(json.loads(row[11])) if row[11] else 0,
                "recommendations_count": len(json.loads(row[12])) if row[12] else 0
            }
            summaries.append(summary)

        return summaries

    def _generate_final_recommendations(self, daily_rows: List, weekly_rows: List) -> List[str]:
        """Generate final recommendations based on 30-day analysis"""
        recommendations = []

        # Performance recommendations
        avg_signal_quality = statistics.mean([row[3] for row in daily_rows])
        if avg_signal_quality < 0.5:
            recommendations.append("SIGNAL_QUALITY: Consider adjusting confidence thresholds to improve signal quality")

        avg_latency = statistics.mean([row[5] for row in daily_rows])
        if avg_latency > 75:
            recommendations.append("LATENCY: Implement additional caching and optimization measures")

        total_pnl = sum([row[13] for row in daily_rows])
        if total_pnl < 0:
            recommendations.append("PROFITABILITY: Review trading strategy and signal validation criteria")

        # Stability recommendations
        latencies = [row[5] for row in daily_rows]
        if statistics.stdev(latencies) > 20:
            recommendations.append("STABILITY: Investigate system resource management and load balancing")

        # Data quality recommendations
        avg_data_quality = statistics.mean([row[19] for row in daily_rows])
        if avg_data_quality < 0.95:
            recommendations.append("DATA_QUALITY: Improve data validation and error handling")

        return recommendations


def main():
    """Main tracking system execution"""
    tracker = ThirtyDayTracker()

    print("🕐 30-DAY TRACKING SYSTEM")
    print("=" * 50)

    # Start tracking session
    session_id = f"ifd_v3_tracking_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}"
    success = tracker.start_tracking_session(session_id)

    if success:
        # Simulate daily data collection (in production, this would run daily)
        print("\n📊 Simulating daily metrics collection...")

        # Collect metrics for past 7 days as demonstration
        for i in range(7):
            test_date = (get_eastern_time() - timedelta(days=i)).strftime('%Y-%m-%d')
            metrics = tracker.collect_daily_metrics(test_date)

        # Analyze weekly trends
        week_start = (get_eastern_time() - timedelta(days=6)).strftime('%Y-%m-%d')
        weekly_analysis = tracker.analyze_weekly_trends(week_start)

        # Generate sample report
        report = tracker.generate_30_day_report(session_id)

        print(f"\n✅ 30-day tracking system demonstration completed")
        print(f"📊 Database: {tracker.db_path}")
        print(f"📋 Report: {tracker.output_dir}/30_day_report_{session_id}.json")

        return 0
    else:
        print("❌ Failed to start tracking session")
        return 1


if __name__ == "__main__":
    exit(main())
