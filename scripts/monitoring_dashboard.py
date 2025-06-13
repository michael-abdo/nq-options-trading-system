#!/usr/bin/env python3
"""
Web-based Monitoring Dashboard for IFD v3.0 Trading System

Provides a simple web interface for viewing production metrics and alerts.
Includes real-time updates and historical trends.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
import sys
import os

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import timezone utilities
from utils.timezone_utils import get_eastern_time

class MonitoringDashboard:
    """Web-based monitoring dashboard"""

    def __init__(self, port: int = 8080):
        self.port = port
        self.metrics_file = "outputs/monitoring/production_metrics.json"
        self.alerts_file = "outputs/monitoring/alerts.json"
        self.dashboard_file = "outputs/monitoring/dashboard.json"

        # Ensure monitoring directory exists
        os.makedirs("outputs/monitoring", exist_ok=True)

    def generate_html_dashboard(self) -> str:
        """Generate HTML dashboard"""

        # Load latest metrics
        metrics = self._load_metrics()
        alerts = self._load_alerts()

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IFD v3.0 Production Monitor</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .header {{ background-color: #2c3e50; color: white; padding: 20px; margin: -20px -20px 20px -20px; }}
        .status-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 2em; font-weight: bold; margin: 10px 0; }}
        .metric-label {{ color: #666; font-size: 0.9em; }}
        .status-healthy {{ color: #27ae60; }}
        .status-warning {{ color: #f39c12; }}
        .status-critical {{ color: #e74c3c; }}
        .alerts-section {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .alert {{ padding: 10px; margin: 10px 0; border-radius: 4px; }}
        .alert-warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; }}
        .alert-critical {{ background-color: #f8d7da; border: 1px solid #f5c6cb; }}
        .charts-section {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }}
        .chart-card {{ background: white; padding: 20px; border-radius: 8px; }}
        .timestamp {{ color: #666; font-size: 0.8em; }}
        .refresh-info {{ text-align: center; margin-top: 20px; color: #666; }}
    </style>
    <script>
        function refreshPage() {{
            setTimeout(function() {{
                window.location.reload();
            }}, 300000); // Refresh every 5 minutes
        }}
        window.onload = refreshPage;
    </script>
</head>
<body>
    <div class="header">
        <h1>IFD v3.0 Production Monitor</h1>
        <p>Real-time monitoring dashboard for the trading system</p>
        <div class="timestamp">Last updated: {get_eastern_time().strftime('%Y-%m-%d %H:%M:%S %Z')}</div>
    </div>

    <div class="status-grid">
        {self._generate_metric_cards(metrics)}
    </div>

    <div class="alerts-section">
        <h2>Active Alerts</h2>
        {self._generate_alerts_html(alerts)}
    </div>

    <div class="charts-section">
        <div class="chart-card">
            <h3>System Health Summary</h3>
            {self._generate_system_summary(metrics)}
        </div>

        <div class="chart-card">
            <h3>Trading Performance</h3>
            {self._generate_trading_summary(metrics)}
        </div>

        <div class="chart-card">
            <h3>Cost Tracking</h3>
            {self._generate_cost_summary(metrics)}
        </div>

        <div class="chart-card">
            <h3>Error Monitoring</h3>
            {self._generate_error_summary(metrics)}
        </div>
    </div>

    <div class="refresh-info">
        <p>Dashboard refreshes automatically every 5 minutes</p>
        <p>Monitoring interval: 60 seconds | Data retention: 30 days</p>
    </div>
</body>
</html>
        """

        return html

    def _load_metrics(self) -> Dict[str, Any]:
        """Load latest metrics"""
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass

        return {
            "timestamp": get_eastern_time().isoformat(),
            "system_health": {},
            "trading_metrics": {},
            "cost_metrics": {},
            "error_metrics": {},
            "business_metrics": {}
        }

    def _load_alerts(self) -> List[Dict[str, Any]]:
        """Load current alerts"""
        try:
            if os.path.exists(self.alerts_file):
                with open(self.alerts_file, 'r') as f:
                    data = json.load(f)
                    return data.get("alerts", [])
        except Exception:
            pass

        return []

    def _generate_metric_cards(self, metrics: Dict[str, Any]) -> str:
        """Generate metric cards HTML"""
        cards = []

        # System Status
        uptime = metrics.get("error_metrics", {}).get("uptime_percentage", 0.999)
        status_class = "status-healthy" if uptime >= 0.995 else "status-warning" if uptime >= 0.99 else "status-critical"
        cards.append(f"""
        <div class="metric-card">
            <div class="metric-label">System Status</div>
            <div class="metric-value {status_class}">
                {"HEALTHY" if uptime >= 0.995 else "WARNING" if uptime >= 0.99 else "CRITICAL"}
            </div>
            <div class="metric-label">Uptime: {uptime:.3%}</div>
        </div>
        """)

        # Signal Accuracy
        accuracy = metrics.get("trading_metrics", {}).get("signal_accuracy", 0.75)
        accuracy_class = "status-healthy" if accuracy >= 0.75 else "status-warning" if accuracy >= 0.70 else "status-critical"
        cards.append(f"""
        <div class="metric-card">
            <div class="metric-label">Signal Accuracy</div>
            <div class="metric-value {accuracy_class}">{accuracy:.1%}</div>
            <div class="metric-label">Target: 75%+</div>
        </div>
        """)

        # System Latency
        latency = metrics.get("trading_metrics", {}).get("average_latency", 85.0)
        latency_class = "status-healthy" if latency <= 100 else "status-warning" if latency <= 150 else "status-critical"
        cards.append(f"""
        <div class="metric-card">
            <div class="metric-label">Average Latency</div>
            <div class="metric-value {latency_class}">{latency:.0f}ms</div>
            <div class="metric-label">Target: <100ms</div>
        </div>
        """)

        # Daily Cost
        daily_cost = metrics.get("cost_metrics", {}).get("daily_cost", 5.50)
        cost_class = "status-healthy" if daily_cost <= 8.0 else "status-warning" if daily_cost <= 10.0 else "status-critical"
        cards.append(f"""
        <div class="metric-card">
            <div class="metric-label">Daily Cost</div>
            <div class="metric-value {cost_class}">${daily_cost:.2f}</div>
            <div class="metric-label">Budget: <$8.00</div>
        </div>
        """)

        # Signals Today
        signals = metrics.get("trading_metrics", {}).get("signals_generated", 0)
        cards.append(f"""
        <div class="metric-card">
            <div class="metric-label">Signals Today</div>
            <div class="metric-value status-healthy">{signals}</div>
            <div class="metric-label">Generated signals</div>
        </div>
        """)

        # ROI Today
        roi = metrics.get("business_metrics", {}).get("roi_today", 0.15)
        roi_class = "status-healthy" if roi >= 0.1 else "status-warning" if roi >= 0.05 else "status-critical"
        cards.append(f"""
        <div class="metric-card">
            <div class="metric-label">ROI Today</div>
            <div class="metric-value {roi_class}">{roi:.1%}</div>
            <div class="metric-label">Return on investment</div>
        </div>
        """)

        return "\n".join(cards)

    def _generate_alerts_html(self, alerts: List[Dict[str, Any]]) -> str:
        """Generate alerts HTML"""
        if not alerts:
            return '<div class="alert">No active alerts - system is healthy</div>'

        alert_html = []
        for alert in alerts:
            level = alert.get("level", "INFO").lower()
            alert_class = f"alert-{level}" if level in ["warning", "critical"] else "alert"
            alert_html.append(f"""
            <div class="alert {alert_class}">
                <strong>{alert.get('level', 'INFO')}:</strong> {alert.get('message', 'No message')}
                <br><small>Metric: {alert.get('metric', 'unknown')} |
                Value: {alert.get('value', 'N/A')} |
                Threshold: {alert.get('threshold', 'N/A')}</small>
            </div>
            """)

        return "\n".join(alert_html)

    def _generate_system_summary(self, metrics: Dict[str, Any]) -> str:
        """Generate system health summary"""
        system = metrics.get("system_health", {})
        errors = metrics.get("error_metrics", {})

        return f"""
        <ul>
            <li>CPU Usage: {system.get('cpu_usage', 0):.1f}%</li>
            <li>Memory Usage: {system.get('memory_usage', 0):.1f}%</li>
            <li>Disk Usage: {system.get('disk_usage', 0):.1f}%</li>
            <li>Network: {"Connected" if system.get('network_status', True) else "Disconnected"}</li>
            <li>Error Rate: {errors.get('error_rate', 0):.2%}</li>
            <li>Critical Errors: {errors.get('critical_errors', 0)}</li>
        </ul>
        """

    def _generate_trading_summary(self, metrics: Dict[str, Any]) -> str:
        """Generate trading performance summary"""
        trading = metrics.get("trading_metrics", {})

        return f"""
        <ul>
            <li>Signals Generated: {trading.get('signals_generated', 0)}</li>
            <li>Signal Accuracy: {trading.get('signal_accuracy', 0):.1%}</li>
            <li>Win/Loss Ratio: {trading.get('win_loss_ratio', 0):.2f}</li>
            <li>Successful Trades: {trading.get('successful_trades', 0)}</li>
            <li>Failed Trades: {trading.get('failed_trades', 0)}</li>
            <li>Average Latency: {trading.get('average_latency', 0):.0f}ms</li>
        </ul>
        """

    def _generate_cost_summary(self, metrics: Dict[str, Any]) -> str:
        """Generate cost tracking summary"""
        cost = metrics.get("cost_metrics", {})

        return f"""
        <ul>
            <li>Daily Cost: ${cost.get('daily_cost', 0):.2f}</li>
            <li>Monthly Budget Used: {cost.get('monthly_budget_used', 0):.1%}</li>
            <li>Cost per Signal: ${cost.get('cost_per_signal', 0):.2f}</li>
            <li>Data Usage Cost: ${cost.get('data_usage_cost', 0):.2f}</li>
            <li>API Call Costs: ${cost.get('api_call_costs', 0):.2f}</li>
        </ul>
        """

    def _generate_error_summary(self, metrics: Dict[str, Any]) -> str:
        """Generate error monitoring summary"""
        errors = metrics.get("error_metrics", {})

        return f"""
        <ul>
            <li>Error Rate: {errors.get('error_rate', 0):.2%}</li>
            <li>Critical Errors: {errors.get('critical_errors', 0)}</li>
            <li>Warnings: {errors.get('warnings', 0)}</li>
            <li>Connection Failures: {errors.get('connection_failures', 0)}</li>
            <li>Data Quality Issues: {errors.get('data_quality_issues', 0)}</li>
            <li>Uptime: {errors.get('uptime_percentage', 0):.3%}</li>
        </ul>
        """

    def save_dashboard_html(self) -> str:
        """Save dashboard as HTML file"""
        html = self.generate_html_dashboard()
        html_file = "outputs/monitoring/dashboard.html"

        with open(html_file, 'w') as f:
            f.write(html)

        return html_file

    def start_simple_server(self):
        """Start a simple HTTP server for the dashboard"""
        try:
            import http.server
            import socketserver
            import webbrowser
            from pathlib import Path

            # Change to monitoring directory
            os.chdir("outputs/monitoring")

            # Generate initial dashboard
            self.save_dashboard_html()

            # Start server
            Handler = http.server.SimpleHTTPRequestHandler
            with socketserver.TCPServer(("", self.port), Handler) as httpd:
                print(f"Dashboard server started at http://localhost:{self.port}")
                print(f"Dashboard file: dashboard.html")
                print("Press Ctrl+C to stop the server")

                # Try to open browser
                try:
                    webbrowser.open(f"http://localhost:{self.port}/dashboard.html")
                except:
                    pass

                httpd.serve_forever()

        except Exception as e:
            print(f"Error starting server: {e}")
            print(f"Dashboard saved to: {self.save_dashboard_html()}")


def main():
    """Main dashboard entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Monitoring Dashboard for IFD v3.0")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--generate-only", action="store_true", help="Generate HTML only")

    args = parser.parse_args()

    dashboard = MonitoringDashboard(args.port)

    if args.generate_only:
        html_file = dashboard.save_dashboard_html()
        print(f"Dashboard generated: {html_file}")
    else:
        dashboard.start_simple_server()


if __name__ == "__main__":
    main()
