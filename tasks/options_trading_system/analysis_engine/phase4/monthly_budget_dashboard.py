#!/usr/bin/env python3
"""
Monthly Budget Dashboard for IFD v3.0

This module provides comprehensive budget visualization and monitoring:
- Monthly budget target: $150-200
- Daily cost tracking dashboard
- Automatic alerts at 80% of monthly budget
- Cost breakdown by provider and operation type
- Trend analysis and projections
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import calendar

# Try importing plotting libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    import seaborn as sns
    import pandas as pd
    PLOTTING_AVAILABLE = True
    
    # Set style
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
except ImportError:
    PLOTTING_AVAILABLE = False
    plt = None
    sns = None
    pd = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BudgetAlert:
    """Budget alert configuration and status"""
    alert_id: str
    alert_type: str  # DAILY, WEEKLY, MONTHLY
    threshold_percentage: float  # 0.8 for 80%
    current_usage: float
    budget_limit: float
    triggered: bool = False
    triggered_at: Optional[datetime] = None
    message: str = ""


@dataclass
class CostBreakdown:
    """Cost breakdown by category"""
    period_start: datetime
    period_end: datetime
    
    # By provider
    by_provider: Dict[str, float]
    
    # By operation type
    by_operation: Dict[str, float]
    
    # By cost type
    by_cost_type: Dict[str, float]
    
    # Summary
    total_cost: float
    daily_average: float
    projected_monthly: float


class BudgetDatabase:
    """Database for budget tracking and historical data"""
    
    def __init__(self, db_path: str = "outputs/budget_tracking.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Daily budget tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_budget (
                    date TEXT PRIMARY KEY,
                    total_cost REAL DEFAULT 0.0,
                    api_costs REAL DEFAULT 0.0,
                    streaming_costs REAL DEFAULT 0.0,
                    backfill_costs REAL DEFAULT 0.0,
                    execution_costs REAL DEFAULT 0.0,
                    barchart_costs REAL DEFAULT 0.0,
                    databento_costs REAL DEFAULT 0.0,
                    polygon_costs REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Monthly budget summaries
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monthly_budget (
                    month TEXT PRIMARY KEY,  -- YYYY-MM format
                    budget_limit REAL NOT NULL,
                    total_spent REAL DEFAULT 0.0,
                    days_in_month INTEGER,
                    days_elapsed INTEGER,
                    projected_spend REAL DEFAULT 0.0,
                    budget_utilization REAL DEFAULT 0.0,
                    alert_triggered BOOLEAN DEFAULT 0,
                    alert_triggered_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Budget alerts history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budget_alerts (
                    alert_id TEXT PRIMARY KEY,
                    alert_type TEXT NOT NULL,
                    threshold_percentage REAL NOT NULL,
                    current_usage REAL NOT NULL,
                    budget_limit REAL NOT NULL,
                    triggered_at TEXT NOT NULL,
                    message TEXT,
                    acknowledged BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Cost breakdown details
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cost_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    provider TEXT,
                    operation_type TEXT,
                    cost_type TEXT,
                    amount REAL NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_budget(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_month ON monthly_budget(month)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_triggered ON budget_alerts(triggered_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_costs_date ON cost_details(date)")
            
            conn.commit()
    
    def update_daily_costs(self, date: str, cost_breakdown: Dict[str, float]):
        """Update daily cost breakdown"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Calculate totals
            total_cost = sum(cost_breakdown.values())
            
            cursor.execute("""
                INSERT OR REPLACE INTO daily_budget 
                (date, total_cost, api_costs, streaming_costs, backfill_costs,
                 execution_costs, barchart_costs, databento_costs, polygon_costs, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date, total_cost,
                cost_breakdown.get('api_costs', 0.0),
                cost_breakdown.get('streaming_costs', 0.0),
                cost_breakdown.get('backfill_costs', 0.0),
                cost_breakdown.get('execution_costs', 0.0),
                cost_breakdown.get('barchart_costs', 0.0),
                cost_breakdown.get('databento_costs', 0.0),
                cost_breakdown.get('polygon_costs', 0.0),
                datetime.now(timezone.utc).isoformat()
            ))
            
            conn.commit()
    
    def get_daily_costs(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get daily costs for a period"""
        if not PLOTTING_AVAILABLE:
            return None
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT * FROM daily_budget
                WHERE date >= ? AND date <= ?
                ORDER BY date
            """
            return pd.read_sql_query(query, conn, params=(start_date, end_date))
    
    def record_budget_alert(self, alert: BudgetAlert):
        """Record budget alert"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO budget_alerts
                (alert_id, alert_type, threshold_percentage, current_usage,
                 budget_limit, triggered_at, message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                alert.alert_type,
                alert.threshold_percentage,
                alert.current_usage,
                alert.budget_limit,
                alert.triggered_at.isoformat() if alert.triggered_at else None,
                alert.message
            ))
            
            conn.commit()


class MonthlyBudgetDashboard:
    """
    Monthly budget dashboard with visualization and monitoring
    
    Features:
    - Real-time cost tracking
    - Monthly budget visualization
    - Automated alerts
    - Cost breakdown analysis
    - Trend projections
    """
    
    def __init__(self, monthly_budget: float = 175.0, 
                 alert_threshold: float = 0.8):
        """
        Initialize monthly budget dashboard
        
        Args:
            monthly_budget: Monthly budget limit (default $175)
            alert_threshold: Alert threshold as percentage (default 80%)
        """
        self.monthly_budget = monthly_budget
        self.alert_threshold = alert_threshold
        self.database = BudgetDatabase()
        
        # Alert configuration
        self.alerts = {
            'daily_80': BudgetAlert("daily_80", "DAILY", 0.8, 0, 0),
            'weekly_70': BudgetAlert("weekly_70", "WEEKLY", 0.7, 0, 0),
            'monthly_80': BudgetAlert("monthly_80", "MONTHLY", 0.8, 0, monthly_budget),
            'monthly_95': BudgetAlert("monthly_95", "MONTHLY", 0.95, 0, monthly_budget)
        }
        
        # Dashboard output directory
        self.output_dir = "outputs/budget_dashboard"
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"Budget dashboard initialized with ${monthly_budget:.2f} monthly budget")
    
    def update_costs(self, cost_data: Dict[str, float]):
        """Update current costs and check alerts"""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        # Update daily costs
        self.database.update_daily_costs(today, cost_data)
        
        # Check and trigger alerts
        self._check_budget_alerts()
        
        logger.info(f"Costs updated for {today}: ${sum(cost_data.values()):.2f}")
    
    def _check_budget_alerts(self):
        """Check and trigger budget alerts"""
        now = datetime.now(timezone.utc)
        today = now.strftime('%Y-%m-%d')
        
        # Get current month spending
        month_start = now.replace(day=1).strftime('%Y-%m-%d')
        
        if PLOTTING_AVAILABLE:
            monthly_df = self.database.get_daily_costs(month_start, today)
            if monthly_df is not None and not monthly_df.empty:
                monthly_spend = monthly_df['total_cost'].sum()
                daily_spend = monthly_df[monthly_df['date'] == today]['total_cost'].sum()
                
                # Check monthly alerts
                monthly_usage = monthly_spend / self.monthly_budget
                
                for alert_id, alert in self.alerts.items():
                    if alert.alert_type == "MONTHLY" and not alert.triggered:
                        if monthly_usage >= alert.threshold_percentage:
                            alert.current_usage = monthly_spend
                            alert.triggered = True
                            alert.triggered_at = now
                            alert.message = (
                                f"Monthly budget alert: {monthly_usage:.1%} of "
                                f"${self.monthly_budget:.2f} budget used "
                                f"(${monthly_spend:.2f})"
                            )
                            
                            self.database.record_budget_alert(alert)
                            self._send_alert_notification(alert)
                
                # Check daily alerts (against projected daily budget)
                daily_budget = self.monthly_budget / calendar.monthrange(now.year, now.month)[1]
                daily_usage = daily_spend / daily_budget
                
                if daily_usage >= self.alerts['daily_80'].threshold_percentage:
                    alert = self.alerts['daily_80']
                    alert.current_usage = daily_spend
                    alert.budget_limit = daily_budget
                    alert.triggered = True
                    alert.triggered_at = now
                    alert.message = (
                        f"Daily budget alert: ${daily_spend:.2f} spent "
                        f"(${daily_budget:.2f} daily budget)"
                    )
                    
                    self.database.record_budget_alert(alert)
                    self._send_alert_notification(alert)
    
    def _send_alert_notification(self, alert: BudgetAlert):
        """Send budget alert notification"""
        logger.warning(f"🚨 BUDGET ALERT: {alert.message}")
        
        # In production, this would send email/slack/SMS notifications
        print(f"\n{'='*60}")
        print(f"🚨 BUDGET ALERT - {alert.alert_type}")
        print(f"{'='*60}")
        print(f"Threshold: {alert.threshold_percentage:.0%}")
        print(f"Current Usage: ${alert.current_usage:.2f}")
        print(f"Budget Limit: ${alert.budget_limit:.2f}")
        print(f"Message: {alert.message}")
        print(f"Time: {alert.triggered_at}")
        print(f"{'='*60}\n")
    
    def generate_dashboard(self, save_plots: bool = True) -> Dict[str, Any]:
        """Generate comprehensive budget dashboard"""
        if not PLOTTING_AVAILABLE:
            logger.warning("Plotting libraries not available - generating text-only dashboard")
            return self._generate_text_dashboard()
        
        dashboard_data = {}
        
        # Get current month data
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1).strftime('%Y-%m-%d')
        today = now.strftime('%Y-%m-%d')
        
        # Get monthly data
        monthly_df = self.database.get_daily_costs(month_start, today)
        
        if monthly_df is not None and not monthly_df.empty:
            # Create visualizations
            if save_plots:
                self._create_daily_spending_chart(monthly_df)
                self._create_budget_utilization_chart(monthly_df)
                self._create_cost_breakdown_chart(monthly_df)
                self._create_trend_projection_chart(monthly_df)
            
            # Calculate summary statistics
            total_spent = monthly_df['total_cost'].sum()
            days_elapsed = len(monthly_df)
            days_in_month = calendar.monthrange(now.year, now.month)[1]
            
            avg_daily_spend = total_spent / days_elapsed if days_elapsed > 0 else 0
            projected_monthly = avg_daily_spend * days_in_month
            budget_utilization = total_spent / self.monthly_budget
            
            dashboard_data = {
                'period': f"{now.strftime('%B %Y')}",
                'budget_limit': self.monthly_budget,
                'total_spent': total_spent,
                'budget_utilization': budget_utilization,
                'days_elapsed': days_elapsed,
                'days_remaining': days_in_month - days_elapsed,
                'avg_daily_spend': avg_daily_spend,
                'projected_monthly': projected_monthly,
                'budget_status': self._get_budget_status(budget_utilization, projected_monthly),
                'cost_breakdown': self._get_cost_breakdown(monthly_df),
                'recommendations': self._generate_recommendations(monthly_df)
            }
        
        # Save dashboard summary
        if save_plots:
            self._save_dashboard_summary(dashboard_data)
        
        return dashboard_data
    
    def _create_daily_spending_chart(self, df: pd.DataFrame):
        """Create daily spending chart"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Convert date column to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Plot daily spending
        ax.bar(df['date'], df['total_cost'], alpha=0.7, color='steelblue')
        
        # Add daily budget line
        now = datetime.now(timezone.utc)
        daily_budget = self.monthly_budget / calendar.monthrange(now.year, now.month)[1]
        ax.axhline(y=daily_budget, color='red', linestyle='--', 
                  label=f'Daily Budget Target: ${daily_budget:.2f}')
        
        # Add cumulative spending line
        ax2 = ax.twinx()
        cumulative = df['total_cost'].cumsum()
        ax2.plot(df['date'], cumulative, color='orange', linewidth=2, 
                label='Cumulative Spending')
        
        # Formatting
        ax.set_title('Daily Spending vs Budget Target')
        ax.set_xlabel('Date')
        ax.set_ylabel('Daily Cost ($)', color='steelblue')
        ax2.set_ylabel('Cumulative Cost ($)', color='orange')
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        # Legends
        ax.legend(loc='upper left')
        ax2.legend(loc='upper right')
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/daily_spending.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _create_budget_utilization_chart(self, df: pd.DataFrame):
        """Create budget utilization gauge chart"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Current utilization
        total_spent = df['total_cost'].sum()
        utilization = total_spent / self.monthly_budget
        
        # Gauge chart
        theta = np.linspace(0, np.pi, 100)
        r = 1
        
        # Background
        ax1.fill_between(theta, 0, r, color='lightgray', alpha=0.3)
        
        # Utilization fill
        util_theta = theta[:int(utilization * 100)]
        color = 'green' if utilization < 0.8 else 'orange' if utilization < 0.95 else 'red'
        ax1.fill_between(util_theta, 0, r, color=color, alpha=0.7)
        
        # Text
        ax1.text(np.pi/2, 0.5, f'{utilization:.1%}\nUtilized', 
                ha='center', va='center', fontsize=16, fontweight='bold')
        ax1.text(np.pi/2, 0.2, f'${total_spent:.2f} / ${self.monthly_budget:.2f}', 
                ha='center', va='center', fontsize=12)
        
        ax1.set_xlim(0, np.pi)
        ax1.set_ylim(0, 1.2)
        ax1.set_aspect('equal')
        ax1.axis('off')
        ax1.set_title('Monthly Budget Utilization', fontsize=14, fontweight='bold')
        
        # Projection chart
        now = datetime.now(timezone.utc)
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        days_elapsed = len(df)
        
        avg_daily = total_spent / days_elapsed if days_elapsed > 0 else 0
        projected = avg_daily * days_in_month
        
        categories = ['Current\nSpending', 'Projected\nMonthly', 'Budget\nLimit']
        values = [total_spent, projected, self.monthly_budget]
        colors = ['steelblue', 'orange', 'green']
        
        bars = ax2.bar(categories, values, color=colors, alpha=0.7)
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 2,
                    f'${value:.2f}', ha='center', va='bottom', fontweight='bold')
        
        ax2.set_title('Spending Projection', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Amount ($)')
        
        # Add horizontal line for budget limit
        ax2.axhline(y=self.monthly_budget, color='red', linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/budget_utilization.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _create_cost_breakdown_chart(self, df: pd.DataFrame):
        """Create cost breakdown charts"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Provider breakdown (pie chart)
        provider_costs = {
            'Barchart': df['barchart_costs'].sum(),
            'Databento': df['databento_costs'].sum(),
            'Polygon': df['polygon_costs'].sum()
        }
        provider_costs = {k: v for k, v in provider_costs.items() if v > 0}
        
        if provider_costs:
            ax1.pie(provider_costs.values(), labels=provider_costs.keys(), autopct='%1.1f%%')
            ax1.set_title('Cost by Provider')
        
        # Cost type breakdown
        cost_types = {
            'API Calls': df['api_costs'].sum(),
            'Streaming': df['streaming_costs'].sum(),
            'Backfill': df['backfill_costs'].sum(),
            'Execution': df['execution_costs'].sum()
        }
        cost_types = {k: v for k, v in cost_types.items() if v > 0}
        
        if cost_types:
            ax2.pie(cost_types.values(), labels=cost_types.keys(), autopct='%1.1f%%')
            ax2.set_title('Cost by Type')
        
        # Daily cost trend by provider
        df['date'] = pd.to_datetime(df['date'])
        providers = ['barchart_costs', 'databento_costs', 'polygon_costs']
        provider_labels = ['Barchart', 'Databento', 'Polygon']
        
        for provider, label in zip(providers, provider_labels):
            if df[provider].sum() > 0:
                ax3.plot(df['date'], df[provider], marker='o', label=label)
        
        ax3.set_title('Daily Cost Trend by Provider')
        ax3.set_xlabel('Date')
        ax3.set_ylabel('Cost ($)')
        ax3.legend()
        ax3.tick_params(axis='x', rotation=45)
        
        # Cost efficiency (cost per day)
        ax4.bar(range(len(df)), df['total_cost'], alpha=0.7)
        ax4.set_title('Daily Cost Efficiency')
        ax4.set_xlabel('Day of Month')
        ax4.set_ylabel('Daily Cost ($)')
        
        # Add average line
        avg_cost = df['total_cost'].mean()
        ax4.axhline(y=avg_cost, color='red', linestyle='--', 
                   label=f'Average: ${avg_cost:.2f}')
        ax4.legend()
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/cost_breakdown.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _create_trend_projection_chart(self, df: pd.DataFrame):
        """Create trend and projection chart"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Historical data
        df['date'] = pd.to_datetime(df['date'])
        cumulative = df['total_cost'].cumsum()
        
        ax.plot(df['date'], cumulative, 'o-', color='steelblue', 
               linewidth=2, label='Actual Spending')
        
        # Projection
        now = datetime.now(timezone.utc)
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        
        # Create projection dates
        last_date = df['date'].iloc[-1]
        projection_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            end=datetime(now.year, now.month, days_in_month),
            freq='D'
        )
        
        # Linear projection
        if len(df) > 1:
            daily_rate = cumulative.iloc[-1] / len(df)
            projection_values = []
            
            for i, date in enumerate(projection_dates):
                projected_day = len(df) + i + 1
                projection_values.append(daily_rate * projected_day)
            
            if projection_dates.any():
                ax.plot(projection_dates, projection_values, '--', color='orange', 
                       linewidth=2, label='Linear Projection')
        
        # Budget limit line
        budget_dates = pd.date_range(
            start=df['date'].iloc[0],
            end=datetime(now.year, now.month, days_in_month),
            freq='D'
        )
        budget_line = [self.monthly_budget] * len(budget_dates)
        
        ax.plot(budget_dates, budget_line, color='red', linestyle='-', 
               linewidth=2, alpha=0.7, label=f'Budget Limit: ${self.monthly_budget:.2f}')
        
        # Formatting
        ax.set_title('Monthly Spending Trend and Projection')
        ax.set_xlabel('Date')
        ax.set_ylabel('Cumulative Cost ($)')
        ax.legend()
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/trend_projection.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _get_budget_status(self, utilization: float, projected: float) -> str:
        """Get budget status description"""
        if utilization >= 0.95:
            return "CRITICAL - Budget Nearly Exhausted"
        elif utilization >= 0.8:
            return "WARNING - Approaching Budget Limit"
        elif projected > self.monthly_budget:
            return "CAUTION - Projected to Exceed Budget"
        elif utilization >= 0.5:
            return "ON_TRACK - Normal Usage"
        else:
            return "UNDER_BUDGET - Low Usage"
    
    def _get_cost_breakdown(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get detailed cost breakdown"""
        return {
            'by_provider': {
                'barchart': df['barchart_costs'].sum(),
                'databento': df['databento_costs'].sum(),
                'polygon': df['polygon_costs'].sum()
            },
            'by_type': {
                'api_calls': df['api_costs'].sum(),
                'streaming': df['streaming_costs'].sum(),
                'backfill': df['backfill_costs'].sum(),
                'execution': df['execution_costs'].sum()
            }
        }
    
    def _generate_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Generate cost optimization recommendations"""
        recommendations = []
        
        total_spent = df['total_cost'].sum()
        utilization = total_spent / self.monthly_budget
        
        if utilization > 0.8:
            recommendations.append("Consider implementing cost reduction measures")
            
            # Provider-specific recommendations
            if df['barchart_costs'].sum() > df['databento_costs'].sum() * 2:
                recommendations.append("Barchart costs are high - consider switching to Databento for some operations")
            
            if df['backfill_costs'].sum() > df['streaming_costs'].sum() * 0.3:
                recommendations.append("High backfill costs - improve connection stability")
        
        elif utilization < 0.5:
            recommendations.append("Budget utilization is low - consider increasing data coverage")
        
        # Daily variance check
        daily_std = df['total_cost'].std()
        daily_mean = df['total_cost'].mean()
        
        if daily_std / daily_mean > 0.5:
            recommendations.append("High daily cost variance - investigate irregular usage patterns")
        
        if not recommendations:
            recommendations.append("Cost management is on track - continue current practices")
        
        return recommendations
    
    def _save_dashboard_summary(self, dashboard_data: Dict[str, Any]):
        """Save dashboard summary to JSON"""
        summary_file = f"{self.output_dir}/dashboard_summary.json"
        
        # Make data JSON serializable
        json_data = dashboard_data.copy()
        for key, value in json_data.items():
            if isinstance(value, (datetime, pd.Timestamp)):
                json_data[key] = value.isoformat()
        
        with open(summary_file, 'w') as f:
            json.dump(json_data, f, indent=2, default=str)
        
        logger.info(f"Dashboard summary saved to {summary_file}")
    
    def _generate_text_dashboard(self) -> Dict[str, Any]:
        """Generate text-only dashboard when plotting is unavailable"""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1).strftime('%Y-%m-%d')
        today = now.strftime('%Y-%m-%d')
        
        # Get basic monthly totals from database
        with sqlite3.connect(self.database.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT SUM(total_cost), AVG(total_cost), COUNT(*)
                FROM daily_budget
                WHERE date >= ? AND date <= ?
            """, (month_start, today))
            
            result = cursor.fetchone()
            total_spent = result[0] if result[0] else 0
            avg_daily = result[1] if result[1] else 0
            days_elapsed = result[2] if result[2] else 0
        
        utilization = total_spent / self.monthly_budget
        
        return {
            'period': f"{now.strftime('%B %Y')}",
            'budget_limit': self.monthly_budget,
            'total_spent': total_spent,
            'budget_utilization': utilization,
            'days_elapsed': days_elapsed,
            'avg_daily_spend': avg_daily,
            'budget_status': self._get_budget_status(utilization, avg_daily * 30),
            'plotting_available': False
        }


def create_budget_dashboard(monthly_budget: float = 175.0) -> MonthlyBudgetDashboard:
    """
    Factory function to create budget dashboard
    
    Args:
        monthly_budget: Monthly budget limit
        
    Returns:
        Configured MonthlyBudgetDashboard instance
    """
    return MonthlyBudgetDashboard(monthly_budget)


if __name__ == "__main__":
    # Example usage
    dashboard = create_budget_dashboard(monthly_budget=175.0)
    
    # Simulate some daily costs
    print("Simulating monthly cost tracking...")
    
    import random
    from datetime import datetime, timedelta
    
    # Generate sample daily costs for current month
    start_date = datetime.now().replace(day=1)
    
    for day in range(1, 16):  # First 15 days
        date = start_date + timedelta(days=day-1)
        date_str = date.strftime('%Y-%m-%d')
        
        # Simulate varying daily costs
        base_cost = 4.50  # Average daily cost to stay under budget
        daily_cost = base_cost + random.uniform(-2.0, 3.0)
        
        cost_breakdown = {
            'api_costs': daily_cost * 0.3,
            'streaming_costs': daily_cost * 0.4,
            'backfill_costs': daily_cost * 0.1,
            'barchart_costs': daily_cost * 0.6,
            'databento_costs': daily_cost * 0.3,
            'polygon_costs': daily_cost * 0.1
        }
        
        dashboard.update_costs(cost_breakdown)
    
    # Generate dashboard
    dashboard_data = dashboard.generate_dashboard()
    
    print("\n💰 MONTHLY BUDGET DASHBOARD")
    print("=" * 60)
    print(f"Period: {dashboard_data['period']}")
    print(f"Budget Limit: ${dashboard_data['budget_limit']:.2f}")
    print(f"Total Spent: ${dashboard_data['total_spent']:.2f}")
    print(f"Budget Utilization: {dashboard_data['budget_utilization']:.1%}")
    print(f"Days Elapsed: {dashboard_data['days_elapsed']}")
    print(f"Average Daily: ${dashboard_data['avg_daily_spend']:.2f}")
    print(f"Projected Monthly: ${dashboard_data['projected_monthly']:.2f}")
    print(f"Status: {dashboard_data['budget_status']}")
    
    print(f"\n📊 Cost Breakdown:")
    breakdown = dashboard_data.get('cost_breakdown', {})
    for category, costs in breakdown.items():
        print(f"  {category}:")
        for item, cost in costs.items():
            print(f"    {item}: ${cost:.2f}")
    
    print(f"\n💡 Recommendations:")
    for rec in dashboard_data.get('recommendations', []):
        print(f"  - {rec}")
    
    if PLOTTING_AVAILABLE:
        print(f"\n📈 Dashboard charts saved to: {dashboard.output_dir}/")
    else:
        print("\n⚠️  Plotting libraries not available - install matplotlib and seaborn for full dashboard")