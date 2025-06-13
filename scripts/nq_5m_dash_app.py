#!/usr/bin/env python3
"""
Real-Time NQ Futures 5-Minute Chart using Plotly Dash
Auto-refreshes in browser without manual reload
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import logging
import signal
import webbrowser
import threading
import time

from databento_5m_provider import Databento5MinuteProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NQDashApp:
    """Real-time NQ 5-minute chart using Dash"""

    def __init__(self, symbol="NQM5", hours=4, update_interval=30, port=8050):
        self.symbol = symbol
        self.hours = hours
        self.update_interval = update_interval * 1000  # Convert to milliseconds
        self.port = port

        # Initialize data provider
        self.data_provider = Databento5MinuteProvider()

        # Initialize Dash app
        self.app = dash.Dash(__name__)
        self.app.title = f"{symbol} - Real-Time 5-Minute Chart"

        # Set up layout
        self._setup_layout()

        # Set up callbacks
        self._setup_callbacks()

        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _setup_layout(self):
        """Set up the Dash app layout"""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1(
                    f"{self.symbol} - Real-Time 5-Minute Chart",
                    style={
                        'textAlign': 'center',
                        'color': '#FFFFFF',
                        'marginBottom': '10px',
                        'fontFamily': 'Arial, sans-serif'
                    }
                ),
                html.Div([
                    html.Span("🔴 LIVE", style={'color': '#FF0000', 'fontWeight': 'bold'}),
                    html.Span(f" | Updates every {self.update_interval//1000}s",
                             style={'color': '#CCCCCC', 'marginLeft': '10px'}),
                    html.Span(f" | Last updated: ",
                             style={'color': '#CCCCCC', 'marginLeft': '10px'}),
                    html.Span(id='last-update-time',
                             style={'color': '#00FF00', 'fontWeight': 'bold'})
                ], style={'textAlign': 'center', 'marginBottom': '20px'})
            ]),

            # Controls
            html.Div([
                html.Div([
                    html.Label("Symbol:", style={'color': '#FFFFFF', 'marginRight': '10px'}),
                    dcc.Input(
                        id='symbol-input',
                        type='text',
                        value=self.symbol,
                        style={
                            'backgroundColor': '#2E2E2E',
                            'color': '#FFFFFF',
                            'border': '1px solid #555',
                            'borderRadius': '4px',
                            'padding': '5px',
                            'marginRight': '20px'
                        }
                    ),
                    html.Label("Hours:", style={'color': '#FFFFFF', 'marginRight': '10px'}),
                    dcc.Dropdown(
                        id='hours-dropdown',
                        options=[
                            {'label': '1 Hour', 'value': 1},
                            {'label': '2 Hours', 'value': 2},
                            {'label': '4 Hours', 'value': 4},
                            {'label': '8 Hours', 'value': 8},
                            {'label': '1 Day', 'value': 24}
                        ],
                        value=self.hours,
                        style={
                            'backgroundColor': '#2E2E2E',
                            'color': '#000000',
                            'width': '120px',
                            'marginRight': '20px'
                        }
                    ),
                    html.Button(
                        "Reset Chart",
                        id='reset-button',
                        style={
                            'backgroundColor': '#0066CC',
                            'color': '#FFFFFF',
                            'border': 'none',
                            'borderRadius': '4px',
                            'padding': '8px 16px',
                            'cursor': 'pointer'
                        }
                    )
                ], style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'center',
                    'marginBottom': '20px'
                })
            ]),

            # Status indicators
            html.Div([
                html.Div(id='price-display', style={
                    'textAlign': 'center',
                    'fontSize': '24px',
                    'fontWeight': 'bold',
                    'color': '#00FF00',
                    'marginBottom': '10px'
                }),
                html.Div(id='stats-display', style={
                    'textAlign': 'center',
                    'color': '#CCCCCC',
                    'marginBottom': '20px'
                })
            ]),

            # Chart
            dcc.Graph(
                id='live-chart',
                style={'height': '80vh'},
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
                }
            ),

            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=self.update_interval,
                n_intervals=0
            ),

            # Store for data
            dcc.Store(id='chart-data')

        ], style={
            'backgroundColor': '#1E1E1E',
            'minHeight': '100vh',
            'padding': '20px',
            'fontFamily': 'Arial, sans-serif'
        })

    def _setup_callbacks(self):
        """Set up Dash callbacks"""

        @self.app.callback(
            [Output('live-chart', 'figure'),
             Output('price-display', 'children'),
             Output('stats-display', 'children'),
             Output('last-update-time', 'children'),
             Output('chart-data', 'data')],
            [Input('interval-component', 'n_intervals'),
             Input('symbol-input', 'value'),
             Input('hours-dropdown', 'value'),
             Input('reset-button', 'n_clicks')],
            prevent_initial_call=False
        )
        def update_chart(n_intervals, symbol, hours, reset_clicks):
            """Update the chart with fresh data"""
            try:
                # Update symbol and hours if changed
                if symbol != self.symbol:
                    self.symbol = symbol
                if hours != self.hours:
                    self.hours = hours

                # Fetch fresh data
                df = self.data_provider.get_historical_5min_bars(
                    symbol=self.symbol,
                    hours_back=self.hours
                )

                if df.empty:
                    logger.warning("No data available")
                    empty_fig = self._create_empty_chart()
                    return empty_fig, "No Data", "Waiting for data...", "Never", {}

                # Create the chart
                fig = self._create_chart(df)

                # Calculate stats
                last_price = df['close'].iloc[-1]
                high_price = df['high'].max()
                low_price = df['low'].min()
                total_volume = df['volume'].sum()
                price_change = df['close'].iloc[-1] - df['close'].iloc[0] if len(df) > 1 else 0
                price_change_pct = (price_change / df['close'].iloc[0] * 100) if len(df) > 1 and df['close'].iloc[0] != 0 else 0

                # Format displays
                price_display = f"${last_price:,.2f}"
                if price_change >= 0:
                    price_display += f" (+${price_change:.2f}, +{price_change_pct:.2f}%)"
                    price_color = '#00FF00'
                else:
                    price_display += f" (${price_change:.2f}, {price_change_pct:.2f}%)"
                    price_color = '#FF0000'

                stats_display = f"High: ${high_price:,.2f} | Low: ${low_price:,.2f} | Volume: {total_volume:,} | Bars: {len(df)}"

                current_time = datetime.now().strftime("%H:%M:%S")

                # Store data for other callbacks
                chart_data = {
                    'timestamp': current_time,
                    'last_price': last_price,
                    'price_change': price_change,
                    'bars_count': len(df)
                }

                logger.info(f"Chart updated - {self.symbol} at ${last_price:,.2f} ({len(df)} bars)")

                return fig, price_display, stats_display, current_time, chart_data

            except Exception as e:
                logger.error(f"Error updating chart: {e}")
                error_fig = self._create_error_chart(str(e))
                return error_fig, "Error", f"Error: {e}", "Error", {}

        # Update price display color based on change
        @self.app.callback(
            Output('price-display', 'style'),
            [Input('chart-data', 'data')]
        )
        def update_price_color(chart_data):
            if not chart_data or 'price_change' not in chart_data:
                return {'textAlign': 'center', 'fontSize': '24px', 'fontWeight': 'bold', 'color': '#00FF00'}

            color = '#00FF00' if chart_data['price_change'] >= 0 else '#FF0000'
            return {
                'textAlign': 'center',
                'fontSize': '24px',
                'fontWeight': 'bold',
                'color': color,
                'marginBottom': '10px'
            }

    def _create_chart(self, df):
        """Create the plotly figure"""
        # Create subplots
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(f'{self.symbol} - 5 Minute Chart', 'Volume'),
            row_heights=[0.7, 0.3]
        )

        # Add candlestick chart
        candlestick = go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            increasing_line_color='#00FF00',
            decreasing_line_color='#FF0000',
            increasing_fillcolor='rgba(0, 255, 0, 0.3)',
            decreasing_fillcolor='rgba(255, 0, 0, 0.3)'
        )
        fig.add_trace(candlestick, row=1, col=1)

        # Add volume bars
        colors = ['#FF0000' if close < open else '#00FF00'
                 for close, open in zip(df['close'], df['open'])]

        volume_bars = go.Bar(
            x=df.index,
            y=df['volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.7
        )
        fig.add_trace(volume_bars, row=2, col=1)

        # Add moving averages if we have enough data
        if len(df) >= 20:
            ma20 = df['close'].rolling(window=20).mean()
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=ma20,
                    name='MA20',
                    line=dict(color='#0099FF', width=1),
                    opacity=0.8
                ),
                row=1, col=1
            )

        if len(df) >= 50:
            ma50 = df['close'].rolling(window=50).mean()
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=ma50,
                    name='MA50',
                    line=dict(color='#FF9900', width=1),
                    opacity=0.8
                ),
                row=1, col=1
            )

        # Update layout
        fig.update_layout(
            title=dict(
                text=f"{self.symbol} - Real-Time 5 Minute Chart",
                font=dict(size=20, color='#FFFFFF')
            ),
            paper_bgcolor='#1E1E1E',
            plot_bgcolor='#2E2E2E',
            font=dict(color='#FFFFFF'),
            xaxis_rangeslider_visible=False,
            height=600,
            showlegend=True,
            hovermode='x unified',
            legend=dict(
                bgcolor='rgba(30, 30, 30, 0.8)',
                bordercolor='#555',
                borderwidth=1
            )
        )

        # Update axes
        fig.update_xaxes(
            gridcolor='#555',
            showgrid=True,
            zeroline=False,
            title_font=dict(color='#FFFFFF'),
            tickfont=dict(color='#FFFFFF')
        )
        fig.update_yaxes(
            gridcolor='#555',
            showgrid=True,
            zeroline=False,
            title_font=dict(color='#FFFFFF'),
            tickfont=dict(color='#FFFFFF')
        )

        # Update specific y-axis labels
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)

        return fig

    def _create_empty_chart(self):
        """Create empty chart when no data is available"""
        fig = go.Figure()
        fig.update_layout(
            title="Waiting for data...",
            paper_bgcolor='#1E1E1E',
            plot_bgcolor='#2E2E2E',
            font=dict(color='#FFFFFF'),
            height=600
        )
        return fig

    def _create_error_chart(self, error_msg):
        """Create error chart"""
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error: {error_msg}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="red")
        )
        fig.update_layout(
            title="Chart Error",
            paper_bgcolor='#1E1E1E',
            plot_bgcolor='#2E2E2E',
            font=dict(color='#FFFFFF'),
            height=600
        )
        return fig

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Dash app...")
        os._exit(0)

    def run(self, debug=False, host='127.0.0.1'):
        """Run the Dash app"""
        url = f"http://{host}:{self.port}"

        def open_browser():
            """Open browser after a short delay"""
            time.sleep(1.5)
            webbrowser.open(url)

        # Start browser in separate thread
        if not debug:
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()

        logger.info(f"🚀 Starting Real-Time NQ 5-Minute Chart Dashboard")
        logger.info(f"📊 Symbol: {self.symbol} | Hours: {self.hours} | Update: {self.update_interval//1000}s")
        logger.info(f"🌐 Dashboard URL: {url}")
        logger.info("Press Ctrl+C to stop")

        try:
            self.app.run(
                debug=debug,
                host=host,
                port=self.port,
                dev_tools_silence_routes_logging=True
            )
        except KeyboardInterrupt:
            self.shutdown()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="NQ Futures Real-Time 5-Minute Chart Dashboard")
    parser.add_argument('--symbol', default='NQM5', help='Contract symbol (default: NQM5)')
    parser.add_argument('--hours', type=int, default=4, help='Hours of data to display (default: 4)')
    parser.add_argument('--update', type=int, default=30, help='Update interval in seconds (default: 30)')
    parser.add_argument('--port', type=int, default=8050, help='Dashboard port (default: 8050)')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--host', default='127.0.0.1', help='Host address (default: 127.0.0.1)')

    args = parser.parse_args()

    # Create and run app
    app = NQDashApp(
        symbol=args.symbol,
        hours=args.hours,
        update_interval=args.update,
        port=args.port
    )

    app.run(debug=args.debug, host=args.host)

if __name__ == "__main__":
    main()
