#!/usr/bin/env python3
"""
Extended Test Runner for 2-Week Signal Accuracy Measurement

This module provides automated testing infrastructure for running
extended duration tests to measure signal accuracy over a 2-week period
as specified in Phase 3 requirements.

Features:
- Automated 2-week test execution
- Daily performance snapshots
- Signal accuracy tracking over time
- Market condition analysis
- Comprehensive reporting
"""

import json
import os
import time
from datetime import datetime, timedelta
from utils.timezone_utils import get_eastern_time, get_utc_time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
import threading
try:
    import schedule
except ImportError:
    # Create a mock schedule module for testing
    class MockSchedule:
        def every(self):
            return self
        def day(self):
            return self
        def at(self, time):
            return self
        def do(self, func):
            return self
        def friday(self):
            return self
        def run_pending(self):
            pass
    schedule = MockSchedule()
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class DailyPerformance:
    """Daily performance metrics snapshot"""
    date: str
    algorithm_version: str

    # Signal metrics
    total_signals: int = 0
    accurate_signals: int = 0
    false_positives: int = 0
    signal_accuracy: float = 0.0

    # Trading metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    # P&L metrics
    daily_pnl: float = 0.0
    cumulative_pnl: float = 0.0
    max_drawdown: float = 0.0

    # Cost metrics
    api_calls: int = 0
    daily_cost: float = 0.0
    cumulative_cost: float = 0.0

    # Market conditions
    market_volatility: float = 0.0
    trading_volume: int = 0
    vix_level: float = 0.0


@dataclass
class WeeklyReport:
    """Weekly performance summary"""
    week_number: int
    start_date: str
    end_date: str
    algorithm_version: str

    # Aggregated metrics
    total_signals: int = 0
    signal_accuracy: float = 0.0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    sharpe_ratio: float = 0.0

    # Best/worst days
    best_day_pnl: float = 0.0
    worst_day_pnl: float = 0.0
    most_signals_day: int = 0

    # Cost analysis
    total_cost: float = 0.0
    cost_per_signal: float = 0.0
    roi: float = 0.0


@dataclass
class ExtendedTestSession:
    """Extended test session tracking"""
    session_id: str
    start_date: datetime
    end_date: datetime
    algorithms: List[str]

    # Test configuration
    test_duration_days: int = 14
    data_mode: str = "historical"  # historical, real_time, simulation

    # Performance tracking
    daily_performances: Dict[str, List[DailyPerformance]] = field(default_factory=dict)
    weekly_reports: Dict[str, List[WeeklyReport]] = field(default_factory=dict)

    # Test status
    is_active: bool = True
    current_day: int = 0
    completion_percentage: float = 0.0


class ExtendedTestRunner:
    """
    Automated test runner for extended duration signal accuracy measurement

    Features:
    - 2-week automated test execution
    - Daily performance collection
    - Weekly report generation
    - Market condition tracking
    - Cost analysis
    """

    def __init__(self, output_dir: str = "outputs/extended_tests"):
        """
        Initialize extended test runner

        Args:
            output_dir: Directory for test results
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Test session tracking
        self.current_session: Optional[ExtendedTestSession] = None
        self.historical_sessions: List[ExtendedTestSession] = []

        # Component integration
        self.ab_coordinator = None
        self.paper_trader = None
        self.performance_tracker = None

        # Thread management
        self._scheduler_thread = None
        self._stop_event = threading.Event()

        # Daily snapshot cache
        self.daily_snapshots: Dict[str, Any] = {}

    def start_extended_test(self, algorithms: List[str] = ["v1.0", "v3.0"],
                           test_days: int = 14,
                           data_mode: str = "historical",
                           start_date: Optional[datetime] = None) -> str:
        """
        Start a new extended test session

        Args:
            algorithms: Algorithm versions to test
            test_days: Number of days to run test
            data_mode: Data mode (historical, real_time, simulation)
            start_date: Start date for historical testing

        Returns:
            Session ID
        """
        # Create session
        session_id = f"extended_test_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}"

        if start_date is None:
            start_date = get_eastern_time() - timedelta(days=test_days) if data_mode == "historical" else get_eastern_time()

        end_date = start_date + timedelta(days=test_days)

        self.current_session = ExtendedTestSession(
            session_id=session_id,
            start_date=start_date,
            end_date=end_date,
            algorithms=algorithms,
            test_duration_days=test_days,
            data_mode=data_mode
        )

        # Initialize performance tracking for each algorithm
        for algo in algorithms:
            self.current_session.daily_performances[algo] = []
            self.current_session.weekly_reports[algo] = []

        # Initialize components
        self._initialize_components()

        # Start test execution
        if data_mode == "historical":
            self._run_historical_test()
        else:
            self._start_realtime_test()

        print(f"🚀 Extended test started: {session_id}")
        print(f"   Algorithms: {algorithms}")
        print(f"   Duration: {test_days} days")
        print(f"   Mode: {data_mode}")
        print(f"   Start: {start_date.date()}")
        print(f"   End: {end_date.date()}")

        return session_id

    def _initialize_components(self):
        """Initialize integrated components"""
        from ab_testing_coordinator import create_ab_coordinator
        from config_manager import get_config_manager
        from paper_trading_executor import create_paper_trader
        from performance_tracker import create_performance_tracker

        # Initialize components
        config_manager = get_config_manager()
        self.ab_coordinator = create_ab_coordinator(config_manager)
        self.paper_trader = create_paper_trader()
        self.performance_tracker = create_performance_tracker()

        # Start component sessions
        if "v1.0" in self.current_session.algorithms and "v3.0" in self.current_session.algorithms:
            # Start A/B testing
            self.ab_coordinator.start_ab_test(
                "ifd_v1_production",
                "ifd_v3_production",
                duration_hours=self.current_session.test_duration_days * 24
            )

        # Start paper trading for each algorithm
        for algo in self.current_session.algorithms:
            self.paper_trader.start_session(algo)

        # Start performance tracking
        self.performance_tracker.start_tracking(self.current_session.algorithms)

    def _run_historical_test(self):
        """Run test on historical data"""
        print("📊 Running historical backtesting...")

        current_date = self.current_session.start_date

        while current_date <= self.current_session.end_date and self.current_session.is_active:
            # Simulate trading day
            self._process_trading_day(current_date)

            # Collect daily metrics
            self._collect_daily_metrics(current_date)

            # Generate weekly report if needed
            if current_date.weekday() == 4:  # Friday
                self._generate_weekly_report(current_date)

            # Update progress
            self.current_session.current_day += 1
            self.current_session.completion_percentage = (
                self.current_session.current_day / self.current_session.test_duration_days * 100
            )

            print(f"   Day {self.current_session.current_day}/{self.current_session.test_duration_days} "
                  f"({self.current_session.completion_percentage:.1f}%) - {current_date.date()}")

            # Move to next day
            current_date += timedelta(days=1)

            # Skip weekends for trading
            while current_date.weekday() >= 5:  # Saturday or Sunday
                current_date += timedelta(days=1)

        # Final report
        self._generate_final_report()

    def _start_realtime_test(self):
        """Start real-time test execution"""
        print("📡 Starting real-time test execution...")

        # Schedule daily tasks
        schedule.every().day.at("16:00").do(self._daily_market_close)  # 4 PM EST
        schedule.every().friday.at("16:30").do(self._weekly_summary)   # Friday after close

        # Start scheduler thread
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()

    def _run_scheduler(self):
        """Run scheduled tasks"""
        while not self._stop_event.is_set():
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def _process_trading_day(self, date: datetime):
        """Process a single trading day"""
        # In historical mode, load data for the specific date
        data_config = {
            "mode": self.current_session.data_mode,
            "date": date.isoformat(),
            "symbols": ["NQM25", "NQU25"]  # Example symbols
        }

        # Run analysis for each algorithm
        from integration import run_specific_algorithm

        with ThreadPoolExecutor(max_workers=len(self.current_session.algorithms)) as executor:
            futures = {}

            for algo in self.current_session.algorithms:
                future = executor.submit(run_specific_algorithm, algo, data_config)
                futures[future] = algo

            # Collect results
            for future in as_completed(futures):
                algo = futures[future]
                try:
                    result = future.result()
                    self._process_algorithm_results(algo, result, date)
                except Exception as e:
                    print(f"Error processing {algo} on {date}: {e}")

    def _process_algorithm_results(self, algorithm: str, results: Dict[str, Any], date: datetime):
        """Process results from algorithm execution"""
        # Extract signals and recommendations
        synthesis = results.get("synthesis", {})
        recommendations = synthesis.get("trading_recommendations", [])

        # Submit to paper trading
        for rec in recommendations:
            if rec.get("source") == "nq_ev_algorithm" or rec.get("priority") in ["PRIMARY", "IMMEDIATE"]:
                signal_data = {
                    "symbol": "NQM25",  # Default symbol
                    "strike": rec.get("strike", 21350),
                    "option_type": "CALL" if rec["trade_direction"] == "LONG" else "PUT",
                    "direction": rec["trade_direction"],
                    "confidence": rec.get("probability", 0.5),
                    "entry_price": rec["entry_price"],
                    "signal_id": f"{algorithm}_{date.strftime('%Y%m%d')}_{rec.get('rank', 1)}"
                }

                # Submit order
                order_id = self.paper_trader.submit_order(algorithm, signal_data)

                # Track signal for accuracy measurement
                if order_id:
                    signal_id = self.performance_tracker.record_signal(
                        algorithm,
                        signal_data,
                        processing_time=results.get("execution_time_seconds", 0)
                    )

    def _collect_daily_metrics(self, date: datetime):
        """Collect daily performance metrics"""
        for algo in self.current_session.algorithms:
            # Get performance metrics
            perf_summary = self.performance_tracker.get_performance_summary(algo)
            paper_perf = self.paper_trader.get_session_performance(algo)

            # Create daily snapshot
            daily = DailyPerformance(
                date=date.strftime("%Y-%m-%d"),
                algorithm_version=algo,
                total_signals=perf_summary.get("total_signals", 0),
                accurate_signals=int(perf_summary.get("validated_signals", 0) * perf_summary.get("overall_accuracy", 0)),
                signal_accuracy=perf_summary.get("overall_accuracy", 0),
                false_positives=int(perf_summary.get("validated_signals", 0) * perf_summary.get("false_positive_rate", 0)),
                total_trades=paper_perf.get("total_trades", 0),
                winning_trades=paper_perf.get("winning_trades", 0),
                losing_trades=paper_perf.get("losing_trades", 0),
                win_rate=paper_perf.get("win_rate", 0),
                daily_pnl=paper_perf.get("realized_pnl", 0),
                cumulative_pnl=paper_perf.get("total_pnl", 0),
                max_drawdown=paper_perf.get("max_drawdown", 0),
                api_calls=perf_summary.get("total_signals", 0) * 3,  # Estimate
                daily_cost=perf_summary.get("total_cost", 0),
                cumulative_cost=perf_summary.get("total_cost", 0)
            )

            # Add market conditions (would come from market data in production)
            daily.market_volatility = 15.5  # Example VIX
            daily.trading_volume = 1000000
            daily.vix_level = 15.5

            # Store daily performance
            self.current_session.daily_performances[algo].append(daily)

    def _generate_weekly_report(self, date: datetime):
        """Generate weekly performance report"""
        week_number = (date - self.current_session.start_date).days // 7 + 1
        week_start = date - timedelta(days=4)  # Monday
        week_end = date  # Friday

        for algo in self.current_session.algorithms:
            # Get week's daily performances
            week_dailies = [
                d for d in self.current_session.daily_performances[algo]
                if week_start.strftime("%Y-%m-%d") <= d.date <= week_end.strftime("%Y-%m-%d")
            ]

            if not week_dailies:
                continue

            # Calculate weekly metrics
            weekly = WeeklyReport(
                week_number=week_number,
                start_date=week_start.strftime("%Y-%m-%d"),
                end_date=week_end.strftime("%Y-%m-%d"),
                algorithm_version=algo,
                total_signals=sum(d.total_signals for d in week_dailies),
                signal_accuracy=sum(d.signal_accuracy for d in week_dailies) / len(week_dailies),
                win_rate=sum(d.win_rate for d in week_dailies) / len(week_dailies),
                total_pnl=sum(d.daily_pnl for d in week_dailies),
                total_cost=sum(d.daily_cost for d in week_dailies)
            )

            # Best/worst days
            pnls = [d.daily_pnl for d in week_dailies]
            weekly.best_day_pnl = max(pnls) if pnls else 0
            weekly.worst_day_pnl = min(pnls) if pnls else 0
            weekly.most_signals_day = max(d.total_signals for d in week_dailies) if week_dailies else 0

            # Cost analysis
            if weekly.total_signals > 0:
                weekly.cost_per_signal = weekly.total_cost / weekly.total_signals

            if weekly.total_cost > 0:
                weekly.roi = (weekly.total_pnl / weekly.total_cost - 1) * 100

            # Store weekly report
            self.current_session.weekly_reports[algo].append(weekly)

            # Save weekly report
            self._save_weekly_report(weekly)

    def _daily_market_close(self):
        """Daily market close processing for real-time tests"""
        print(f"📊 Daily market close processing - {get_eastern_time().date()}")

        # Collect metrics
        self._collect_daily_metrics(get_eastern_time())

        # Update progress
        self.current_session.current_day += 1
        self.current_session.completion_percentage = (
            self.current_session.current_day / self.current_session.test_duration_days * 100
        )

        # Check if test complete
        if self.current_session.current_day >= self.current_session.test_duration_days:
            self.stop_test()

    def _weekly_summary(self):
        """Generate weekly summary for real-time tests"""
        print(f"📈 Generating weekly summary - Week ending {get_eastern_time().date()}")
        self._generate_weekly_report(get_eastern_time())

    def _generate_final_report(self):
        """Generate comprehensive final report"""
        print("📊 Generating final test report...")

        final_report = {
            "session_id": self.current_session.session_id,
            "test_duration_days": self.current_session.test_duration_days,
            "start_date": self.current_session.start_date.isoformat(),
            "end_date": self.current_session.end_date.isoformat(),
            "algorithms_tested": self.current_session.algorithms,
            "data_mode": self.current_session.data_mode,
            "algorithm_performance": {},
            "comparison": {},
            "recommendations": []
        }

        # Aggregate performance for each algorithm
        for algo in self.current_session.algorithms:
            daily_perfs = self.current_session.daily_performances[algo]
            weekly_reports = self.current_session.weekly_reports[algo]

            algo_summary = {
                "total_signals": sum(d.total_signals for d in daily_perfs),
                "average_daily_signals": sum(d.total_signals for d in daily_perfs) / len(daily_perfs),
                "overall_signal_accuracy": sum(d.signal_accuracy for d in daily_perfs) / len(daily_perfs),
                "total_trades": sum(d.total_trades for d in daily_perfs),
                "overall_win_rate": sum(d.win_rate for d in daily_perfs) / len(daily_perfs),
                "total_pnl": sum(d.daily_pnl for d in daily_perfs),
                "average_daily_pnl": sum(d.daily_pnl for d in daily_perfs) / len(daily_perfs),
                "max_drawdown": max(d.max_drawdown for d in daily_perfs) if daily_perfs else 0,
                "total_cost": sum(d.daily_cost for d in daily_perfs),
                "cost_per_signal": sum(d.daily_cost for d in daily_perfs) / max(sum(d.total_signals for d in daily_perfs), 1),
                "daily_performances": [asdict(d) for d in daily_perfs],
                "weekly_summaries": [asdict(w) for w in weekly_reports]
            }

            final_report["algorithm_performance"][algo] = algo_summary

        # Comparison analysis
        if len(self.current_session.algorithms) > 1:
            comparison = self._compare_algorithm_performance()
            final_report["comparison"] = comparison

            # Generate recommendations
            recommendations = self._generate_recommendations(comparison)
            final_report["recommendations"] = recommendations

        # Save final report
        report_file = os.path.join(
            self.output_dir,
            f"extended_test_final_{self.current_session.session_id}.json"
        )

        with open(report_file, 'w') as f:
            json.dump(final_report, f, indent=2, default=str)

        print(f"✅ Final report saved: {report_file}")

        # Generate summary visualization
        self._generate_summary_visualization(final_report)

        return final_report

    def _compare_algorithm_performance(self) -> Dict[str, Any]:
        """Compare algorithm performance over test period"""
        comparison = {
            "metrics": {},
            "winner": None,
            "confidence": 0.0,
            "reasoning": []
        }

        # Collect metrics for comparison
        algo_metrics = {}
        for algo in self.current_session.algorithms:
            daily_perfs = self.current_session.daily_performances[algo]

            algo_metrics[algo] = {
                "signal_accuracy": sum(d.signal_accuracy for d in daily_perfs) / len(daily_perfs),
                "win_rate": sum(d.win_rate for d in daily_perfs) / len(daily_perfs),
                "total_pnl": sum(d.daily_pnl for d in daily_perfs),
                "sharpe_ratio": self._calculate_sharpe_ratio([d.daily_pnl for d in daily_perfs]),
                "max_drawdown": max(d.max_drawdown for d in daily_perfs) if daily_perfs else 0,
                "cost_efficiency": sum(d.daily_pnl for d in daily_perfs) / max(sum(d.daily_cost for d in daily_perfs), 1)
            }

        comparison["metrics"] = algo_metrics

        # Determine winner based on multiple factors
        scores = {}
        for algo, metrics in algo_metrics.items():
            score = 0
            score += metrics["signal_accuracy"] * 20  # Weight accuracy
            score += metrics["win_rate"] * 15         # Weight win rate
            score += min(metrics["sharpe_ratio"], 3) * 10  # Cap Sharpe contribution
            score += (100 - abs(metrics["max_drawdown"])) * 0.1  # Penalize drawdown
            score += min(metrics["cost_efficiency"], 10) * 5  # Weight cost efficiency
            scores[algo] = score

        # Find winner
        best_algo = max(scores, key=scores.get)
        comparison["winner"] = best_algo
        comparison["confidence"] = min((scores[best_algo] - min(scores.values())) / 10, 1.0)

        # Generate reasoning
        winner_metrics = algo_metrics[best_algo]
        comparison["reasoning"] = [
            f"Highest overall score: {scores[best_algo]:.2f}",
            f"Signal accuracy: {winner_metrics['signal_accuracy']:.1%}",
            f"Win rate: {winner_metrics['win_rate']:.1%}",
            f"Total P&L: ${winner_metrics['total_pnl']:,.2f}",
            f"Sharpe ratio: {winner_metrics['sharpe_ratio']:.2f}"
        ]

        return comparison

    def _calculate_sharpe_ratio(self, daily_returns: List[float]) -> float:
        """Calculate Sharpe ratio from daily returns"""
        if not daily_returns or len(daily_returns) < 2:
            return 0.0

        import numpy as np

        returns = np.array(daily_returns)
        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # Annualized Sharpe ratio (252 trading days)
        sharpe = (avg_return / std_return) * np.sqrt(252)

        return sharpe

    def _generate_recommendations(self, comparison: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on test results"""
        recommendations = []

        winner = comparison["winner"]
        confidence = comparison["confidence"]
        metrics = comparison["metrics"]

        # Primary recommendation
        if confidence > 0.7:
            recommendations.append(
                f"STRONG RECOMMENDATION: Deploy {winner} to production based on superior performance"
            )
        elif confidence > 0.5:
            recommendations.append(
                f"MODERATE RECOMMENDATION: Consider {winner} for production with additional testing"
            )
        else:
            recommendations.append(
                "WEAK SIGNAL: Continue testing both algorithms with longer duration"
            )

        # Specific insights
        for algo, algo_metrics in metrics.items():
            if algo_metrics["signal_accuracy"] < 0.5:
                recommendations.append(
                    f"⚠️ {algo}: Signal accuracy below 50% - review signal generation logic"
                )

            if algo_metrics["max_drawdown"] > 5000:
                recommendations.append(
                    f"⚠️ {algo}: High drawdown ${algo_metrics['max_drawdown']:,.0f} - implement better risk management"
                )

            if algo_metrics["cost_efficiency"] < 2:
                recommendations.append(
                    f"💰 {algo}: Low cost efficiency ({algo_metrics['cost_efficiency']:.1f}x) - optimize API usage"
                )

        # General recommendations
        if all(m["signal_accuracy"] > 0.6 for m in metrics.values()):
            recommendations.append(
                "✅ Both algorithms show good signal accuracy - consider ensemble approach"
            )

        return recommendations

    def _generate_summary_visualization(self, report: Dict[str, Any]):
        """Generate summary visualization (placeholder for actual charting)"""
        print("\n📊 EXTENDED TEST SUMMARY")
        print("=" * 60)

        for algo, perf in report["algorithm_performance"].items():
            print(f"\n{algo} Performance:")
            print(f"  Total Signals: {perf['total_signals']:,}")
            print(f"  Signal Accuracy: {perf['overall_signal_accuracy']:.1%}")
            print(f"  Win Rate: {perf['overall_win_rate']:.1%}")
            print(f"  Total P&L: ${perf['total_pnl']:,.2f}")
            print(f"  Total Cost: ${perf['total_cost']:,.2f}")
            print(f"  Cost per Signal: ${perf['cost_per_signal']:.2f}")

        if "comparison" in report:
            print(f"\n🏆 WINNER: {report['comparison']['winner']}")
            print(f"Confidence: {report['comparison']['confidence']:.1%}")

            print("\nRecommendations:")
            for i, rec in enumerate(report["recommendations"], 1):
                print(f"{i}. {rec}")

        print("=" * 60)

    def _save_weekly_report(self, report: WeeklyReport):
        """Save weekly report to file"""
        report_file = os.path.join(
            self.output_dir,
            f"weekly_report_{report.algorithm_version}_week{report.week_number}.json"
        )

        with open(report_file, 'w') as f:
            json.dump(asdict(report), f, indent=2)

    def stop_test(self):
        """Stop the current test and generate final report"""
        if not self.current_session:
            return

        print("🛑 Stopping extended test...")

        # Mark session as inactive
        self.current_session.is_active = False

        # Stop scheduler if running
        if self._scheduler_thread:
            self._stop_event.set()
            self._scheduler_thread.join()

        # Stop components
        if self.ab_coordinator and self.ab_coordinator.test_active:
            self.ab_coordinator.stop_ab_test()

        if self.paper_trader:
            self.paper_trader.stop_all_sessions()

        if self.performance_tracker:
            self.performance_tracker.stop_tracking()

        # Generate final report
        final_report = self._generate_final_report()

        # Archive session
        self.historical_sessions.append(self.current_session)
        self.current_session = None

        return final_report


# Module-level convenience functions
def run_2_week_test(algorithms: List[str] = ["v1.0", "v3.0"],
                   data_mode: str = "historical") -> Dict[str, Any]:
    """
    Run a 2-week extended test

    Args:
        algorithms: Algorithm versions to test
        data_mode: Testing mode (historical, real_time, simulation)

    Returns:
        Test results
    """
    runner = ExtendedTestRunner()

    # Start test
    session_id = runner.start_extended_test(
        algorithms=algorithms,
        test_days=14,
        data_mode=data_mode
    )

    # For historical mode, test runs synchronously
    # For real-time mode, this would return immediately

    if data_mode == "historical":
        # Test already completed
        return runner.current_session
    else:
        # Return session info for real-time test
        return {
            "session_id": session_id,
            "status": "running",
            "message": "Test will run for 14 days. Use get_test_status() to check progress."
        }


if __name__ == "__main__":
    # Example: Run 2-week historical test
    print("Starting 2-week extended test...")

    result = run_2_week_test(
        algorithms=["v1.0", "v3.0"],
        data_mode="historical"
    )

    print("\nTest completed!")
