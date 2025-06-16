#!/usr/bin/env python3
"""
Enhanced Real-Time NQ Futures Dashboard with Live IFD v3.0 Integration

This dashboard provides real-time institutional flow detection with:
- WebSocket connection to live streaming analysis engine
- Real-time signal overlays with confidence levels
- Live data connection status indicators
- Signal strength visualization
- Graceful fallback to historical data
- User controls for signal sensitivity
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import json
import dash
from dash import dcc, html, Input, Output, callback, State, clientside_callback, ClientsideFunction
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
import pytz
import websocket
import queue
from collections import deque

from databento_5m_provider import Databento5MinuteProvider

# Import timezone utilities for proper futures market hours
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'utils'))
from timezone_utils import is_futures_market_hours

def format_eastern_display(dt=None):
    """Format datetime for Eastern time display"""
    if dt is None:
        dt = datetime.now(pytz.timezone('US/Eastern'))
    elif hasattr(dt, 'tz_convert'):
        dt = dt.tz_convert(pytz.timezone('US/Eastern'))
    elif hasattr(dt, 'astimezone'):
        dt = dt.astimezone(pytz.timezone('US/Eastern'))
    return dt.strftime('%Y-%m-%d %H:%M:%S ET')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LiveSignalManager:
    """Manages real-time signals from WebSocket connection"""

    def __init__(self, max_signals=100):
        self.signals = deque(maxlen=max_signals)
        self.connection_status = "disconnected"
        self.last_signal_time = None
        self.total_signals_received = 0
        self.signal_queue = queue.Queue()

    def add_signal(self, signal_data):
        """Add new signal from WebSocket"""
        try:
            self.signals.append(signal_data)
            self.last_signal_time = datetime.now(pytz.UTC)
            self.total_signals_received += 1

            # Add to queue for dashboard processing
            self.signal_queue.put(signal_data)

            logger.info(f"Signal received: {signal_data.get('signal', {}).get('strike')}"
                       f"{signal_data.get('signal', {}).get('option_type')} "
                       f"confidence={signal_data.get('signal', {}).get('final_confidence', 0):.3f}")

        except Exception as e:
            logger.error(f"Error adding signal: {e}")

    def get_recent_signals(self, limit=20):
        """Get recent signals for display"""
        return list(self.signals)[-limit:]

    def get_status(self):
        """Get connection and signal status"""
        return {
            'connection_status': self.connection_status,
            'total_signals': self.total_signals_received,
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None,
            'signals_in_buffer': len(self.signals)
        }

class WebSocketClient:
    """WebSocket client for real-time signal reception"""

    def __init__(self, uri, signal_manager):
        self.uri = uri
        self.signal_manager = signal_manager
        self.ws = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5

    def on_message(self, ws, message):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get('type')

            if message_type == 'ifd_signal':
                self.signal_manager.add_signal(data)
            elif message_type == 'connection':
                logger.info(f"WebSocket connection confirmed: {data.get('message')}")
                self.signal_manager.connection_status = "connected"
            elif message_type == 'status_update':
                logger.info(f"Status update: {data.get('status_type')}")
            elif message_type == 'pong':
                # Heartbeat response
                pass

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {message}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")

    def on_error(self, ws, error):
        """Handle WebSocket error"""
        logger.error(f"WebSocket error: {error}")
        self.signal_manager.connection_status = "error"

    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        self.is_connected = False
        self.signal_manager.connection_status = "disconnected"

        # Attempt to reconnect
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Attempting to reconnect ({self.reconnect_attempts}/{self.max_reconnect_attempts})...")
            threading.Timer(self.reconnect_delay, self.connect).start()
        else:
            logger.error("Max reconnection attempts reached")

    def on_open(self, ws):
        """Handle WebSocket connection open"""
        logger.info("WebSocket connection established")
        self.is_connected = True
        self.reconnect_attempts = 0
        self.signal_manager.connection_status = "connected"

        # Send subscription message
        subscribe_msg = {
            'type': 'subscribe',
            'signal_types': ['all']
        }
        ws.send(json.dumps(subscribe_msg))

        # Start heartbeat
        self.start_heartbeat()

    def start_heartbeat(self):
        """Start heartbeat to keep connection alive"""
        def send_ping():
            if self.is_connected and self.ws:
                try:
                    ping_msg = {'type': 'ping', 'timestamp': datetime.now().isoformat()}
                    self.ws.send(json.dumps(ping_msg))
                    threading.Timer(30, send_ping).start()  # Send ping every 30 seconds
                except Exception as e:
                    logger.error(f"Error sending ping: {e}")

        send_ping()

    def connect(self):
        """Connect to WebSocket server"""
        try:
            logger.info(f"Connecting to WebSocket server: {self.uri}")
            self.ws = websocket.WebSocketApp(
                self.uri,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )

            # Run WebSocket in background thread
            wst = threading.Thread(target=self.ws.run_forever)
            wst.daemon = True
            wst.start()

        except Exception as e:
            logger.error(f"Error connecting to WebSocket: {e}")
            self.signal_manager.connection_status = "error"

    def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.ws:
            self.ws.close()

class NQRealtimeIFDDashboard:
    """Enhanced Real-time NQ Dashboard with Live IFD Integration"""

    def __init__(self, symbol="NQM5", hours=4, update_interval=10, port=8051, websocket_uri="ws://localhost:8765"):
        self.symbol = symbol
        self.hours = hours
        self.update_interval = update_interval * 1000  # Convert to milliseconds
        self.port = port
        self.websocket_uri = websocket_uri

        # Live signal management
        self.signal_manager = LiveSignalManager()
        self.websocket_client = WebSocketClient(websocket_uri, self.signal_manager)

        # Data provider for historical data fallback
        self.data_provider = Databento5MinuteProvider()

        # Dashboard state
        self.live_mode = True
        self.signal_sensitivity = 0.7  # Minimum confidence to display
        self.signal_types_filter = ['all']

        # Connect to WebSocket
        self.websocket_client.connect()

        # Initialize Dash app
        self.app = dash.Dash(__name__)
        self.app.title = f"{symbol} - Real-Time IFD Dashboard"

        # Set up layout and callbacks
        self._setup_layout()
        self._setup_callbacks()

        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _setup_layout(self):
        """Set up the enhanced dashboard layout"""

        self.app.layout = html.Div([
            # Header with live status
            html.Div([
                html.H1(
                    f"{self.symbol} - Real-Time IFD Dashboard",
                    style={
                        'textAlign': 'center',
                        'color': '#FFFFFF',
                        'marginBottom': '10px',
                        'fontFamily': 'Arial, sans-serif'
                    }
                ),

                # Live status bar
                html.Div([
                    html.Div(id='connection-status', children=[
                        html.Span("🔴 DISCONNECTED", style={'color': '#FF0000', 'fontWeight': 'bold'})
                    ], style={'display': 'inline-block', 'marginRight': '20px'}),

                    html.Div(id='signal-count', children=[
                        html.Span("Signals: 0", style={'color': '#CCCCCC'})
                    ], style={'display': 'inline-block', 'marginRight': '20px'}),

                    html.Div(id='last-update', children=[
                        html.Span("Last Update: Never", style={'color': '#CCCCCC'})
                    ], style={'display': 'inline-block', 'marginRight': '20px'}),

                    html.Div([
                        html.Span(f"Mode: {'LIVE' if self.live_mode else 'HISTORICAL'}",
                                style={'color': '#00FF00' if self.live_mode else '#FFA500', 'fontWeight': 'bold'})
                    ], style={'display': 'inline-block'})

                ], style={'textAlign': 'center', 'marginBottom': '20px'})
            ]),

            # Controls panel
            html.Div([
                # Chart controls
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
                            {'label': '8 Hours', 'value': 8}
                        ],
                        value=self.hours,
                        style={
                            'backgroundColor': '#2E2E2E',
                            'color': '#000000',
                            'width': '120px',
                            'marginRight': '20px'
                        }
                    ),

                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '15px', 'justifyContent': 'center'}),

                # Signal controls
                html.Div([
                    html.Label("Signal Sensitivity:", style={'color': '#FFFFFF', 'marginRight': '10px'}),
                    dcc.Slider(
                        id='sensitivity-slider',
                        min=0.5,
                        max=1.0,
                        step=0.05,
                        value=self.signal_sensitivity,
                        marks={i/10: f'{i/10:.1f}' for i in range(5, 11)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),

                    html.Div([
                        html.Button(
                            "Toggle Live Mode",
                            id='live-mode-button',
                            style={
                                'backgroundColor': '#00AA00' if self.live_mode else '#AA0000',
                                'color': '#FFFFFF',
                                'border': 'none',
                                'borderRadius': '4px',
                                'padding': '8px 16px',
                                'cursor': 'pointer',
                                'marginLeft': '20px'
                            }
                        ),

                        html.Button(
                            "Reconnect WebSocket",
                            id='reconnect-button',
                            style={
                                'backgroundColor': '#0066CC',
                                'color': '#FFFFFF',
                                'border': 'none',
                                'borderRadius': '4px',
                                'padding': '8px 16px',
                                'cursor': 'pointer',
                                'marginLeft': '10px'
                            }
                        )
                    ], style={'display': 'inline-block'})

                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px', 'justifyContent': 'center'})

            ], style={'backgroundColor': '#333333', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '20px'}),

            # Main chart
            dcc.Graph(
                id='live-chart',
                style={'height': '70vh'},
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
                }
            ),

            # Signal information panel
            html.Div([
                html.H3("Live Signal Information", style={'color': '#FFFFFF', 'textAlign': 'center'}),
                html.Div(id='signal-info-panel', style={'color': '#FFFFFF'})
            ], style={'backgroundColor': '#333333', 'padding': '15px', 'borderRadius': '8px', 'marginTop': '20px'}),

            # Auto-refresh intervals
            dcc.Interval(
                id='chart-interval',
                interval=self.update_interval,
                n_intervals=0
            ),

            dcc.Interval(
                id='status-interval',
                interval=1000,  # Update status every second
                n_intervals=0
            ),

            # Data stores
            dcc.Store(id='live-signal-store'),
            dcc.Store(id='connection-store')

        ], style={'backgroundColor': '#1E1E1E', 'minHeight': '100vh', 'padding': '20px'})

    def _setup_callbacks(self):
        """Set up Dash callbacks for interactivity"""

        @self.app.callback(
            [Output('connection-status', 'children'),
             Output('signal-count', 'children'),
             Output('last-update', 'children'),
             Output('connection-store', 'data')],
            Input('status-interval', 'n_intervals')
        )
        def update_status(n_intervals):
            """Update connection and signal status"""
            status = self.signal_manager.get_status()

            # Connection status indicator
            connection_status = status['connection_status']
            if connection_status == 'connected':
                conn_display = html.Span("🟢 CONNECTED", style={'color': '#00FF00', 'fontWeight': 'bold'})
            elif connection_status == 'error':
                conn_display = html.Span("🟠 ERROR", style={'color': '#FFA500', 'fontWeight': 'bold'})
            else:
                conn_display = html.Span("🔴 DISCONNECTED", style={'color': '#FF0000', 'fontWeight': 'bold'})

            # Signal count
            signal_count_display = html.Span(f"Signals: {status['total_signals']}", style={'color': '#CCCCCC'})

            # Last update time
            if status['last_signal_time']:
                try:
                    last_time = datetime.fromisoformat(status['last_signal_time'].replace('Z', '+00:00'))
                    last_time_et = last_time.astimezone(pytz.timezone('US/Eastern'))
                    last_update_display = html.Span(
                        f"Last Signal: {last_time_et.strftime('%H:%M:%S ET')}",
                        style={'color': '#00FF00'}
                    )
                except:
                    last_update_display = html.Span("Last Signal: Invalid time", style={'color': '#CCCCCC'})
            else:
                last_update_display = html.Span("Last Signal: Never", style={'color': '#CCCCCC'})

            return [conn_display], [signal_count_display], [last_update_display], status

        @self.app.callback(
            Output('live-signal-store', 'data'),
            Input('status-interval', 'n_intervals')
        )
        def update_signal_store(n_intervals):
            """Update live signal data store"""
            signals = []

            # Get signals from queue
            while not self.signal_manager.signal_queue.empty():
                try:
                    signal = self.signal_manager.signal_queue.get_nowait()
                    signals.append(signal)
                except queue.Empty:
                    break

            return signals

        @self.app.callback(
            [Output('live-chart', 'figure'),
             Output('signal-info-panel', 'children')],
            [Input('chart-interval', 'n_intervals'),
             Input('symbol-input', 'value'),
             Input('hours-dropdown', 'value'),
             Input('sensitivity-slider', 'value'),
             Input('live-signal-store', 'data')],
            [State('connection-store', 'data')]
        )
        def update_chart(n_intervals, symbol, hours, sensitivity, new_signals, connection_status):
            """Update the main chart with latest data and signals"""
            try:
                self.symbol = symbol or "NQM5"
                self.hours = hours or 4
                self.signal_sensitivity = sensitivity or 0.7

                # Get historical chart data
                bars_needed = (self.hours * 60) // 5
                df = self.data_provider.get_latest_bars(symbol=self.symbol, count=bars_needed)

                if df.empty:
                    return self._create_no_data_chart(), self._create_no_data_info()

                # Create base chart
                fig = self._create_base_chart(df)

                # Add live signals overlay
                if new_signals and connection_status and connection_status.get('connection_status') == 'connected':
                    fig = self._add_live_signals_overlay(fig, df, new_signals)

                # Add recent signals info
                signal_info = self._create_signal_info_panel(new_signals)

                return fig, signal_info

            except Exception as e:
                logger.error(f"Error updating chart: {e}")
                return self._create_error_chart(str(e)), self._create_error_info(str(e))

        @self.app.callback(
            Output('reconnect-button', 'style'),
            Input('reconnect-button', 'n_clicks')
        )
        def handle_reconnect(n_clicks):
            """Handle WebSocket reconnection"""
            if n_clicks:
                logger.info("Manual WebSocket reconnection requested")
                self.websocket_client.disconnect()
                time.sleep(1)
                self.websocket_client.connect()

            return {
                'backgroundColor': '#0066CC',
                'color': '#FFFFFF',
                'border': 'none',
                'borderRadius': '4px',
                'padding': '8px 16px',
                'cursor': 'pointer',
                'marginLeft': '10px'
            }

    def _create_base_chart(self, df):
        """Create base candlestick chart"""
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=('Price', 'Volume'),
            row_width=[0.7, 0.3]
        )

        # Candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='Price',
                increasing_line_color='#00AA00',
                decreasing_line_color='#AA0000'
            ),
            row=1, col=1
        )

        # Volume bars
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['volume'],
                name='Volume',
                marker_color='#4444AA',
                opacity=0.7
            ),
            row=2, col=1
        )

        # Update layout
        fig.update_layout(
            title=dict(
                text=f"{self.symbol} - Real-Time Chart with Live IFD Signals",
                font=dict(size=20, color='#FFFFFF')
            ),
            xaxis_rangeslider_visible=False,
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            font=dict(color='#FFFFFF'),
            showlegend=True,
            legend=dict(
                bgcolor='rgba(0,0,0,0.5)',
                bordercolor='#444444',
                borderwidth=1
            )
        )

        # Update axes
        fig.update_xaxes(gridcolor='#333333', showgrid=True)
        fig.update_yaxes(gridcolor='#333333', showgrid=True)

        return fig

    def _add_live_signals_overlay(self, fig, df, signals):
        """Add live signal overlay to chart"""
        if not signals:
            return fig

        try:
            # Filter signals by sensitivity
            filtered_signals = [
                s for s in signals
                if s.get('signal', {}).get('final_confidence', 0) >= self.signal_sensitivity
            ]

            if not filtered_signals:
                return fig

            # Group signals by strength for color coding
            signal_colors = {
                'EXTREME': '#FF0000',    # Red
                'VERY_HIGH': '#FF8C00',  # Dark Orange
                'HIGH': '#FFD700',       # Gold
                'MODERATE': '#90EE90'    # Light Green
            }

            for signal in filtered_signals:
                signal_data = signal.get('signal', {})

                strike = signal_data.get('strike')
                option_type = signal_data.get('option_type')
                confidence = signal_data.get('final_confidence', 0)
                strength = signal_data.get('signal_strength', 'MODERATE')
                action = signal_data.get('action', 'MONITOR')

                if not strike:
                    continue

                # Use current time for signal placement
                signal_time = pd.Timestamp.now(tz='US/Eastern')

                # Find appropriate price level (use latest close price)
                if not df.empty:
                    signal_price = df['close'].iloc[-1]
                else:
                    signal_price = strike

                # Determine marker properties
                color = signal_colors.get(strength, '#808080')
                symbol_marker = "triangle-up" if action in ["STRONG_BUY", "BUY"] else "triangle-down"
                size = 15 + (confidence * 10)  # Size based on confidence

                # Add signal marker
                fig.add_trace(
                    go.Scatter(
                        x=[signal_time],
                        y=[signal_price],
                        mode='markers',
                        name=f'LIVE {strength}',
                        marker=dict(
                            symbol=symbol_marker,
                            size=size,
                            color=color,
                            line=dict(width=2, color='white')
                        ),
                        hovertext=f"LIVE SIGNAL<br>"
                                 f"Strike: {strike}{option_type}<br>"
                                 f"Confidence: {confidence:.1%}<br>"
                                 f"Strength: {strength}<br>"
                                 f"Action: {action}",
                        hoverinfo='text',
                        showlegend=True
                    ),
                    row=1, col=1
                )

        except Exception as e:
            logger.error(f"Error adding signal overlay: {e}")

        return fig

    def _create_signal_info_panel(self, signals):
        """Create signal information panel"""
        if not signals:
            return html.Div([
                html.P("No live signals received yet.", style={'textAlign': 'center', 'color': '#CCCCCC'})
            ])

        # Filter signals by sensitivity
        filtered_signals = [
            s for s in signals
            if s.get('signal', {}).get('final_confidence', 0) >= self.signal_sensitivity
        ]

        if not filtered_signals:
            return html.Div([
                html.P(f"No signals above {self.signal_sensitivity:.0%} confidence threshold.",
                      style={'textAlign': 'center', 'color': '#CCCCCC'})
            ])

        # Create signal cards
        signal_cards = []
        for i, signal in enumerate(filtered_signals[-5:]):  # Show last 5 signals
            signal_data = signal.get('signal', {})

            # Signal strength color
            strength_colors = {
                'EXTREME': '#FF0000',
                'VERY_HIGH': '#FF8C00',
                'HIGH': '#FFD700',
                'MODERATE': '#90EE90'
            }

            strength = signal_data.get('signal_strength', 'MODERATE')
            color = strength_colors.get(strength, '#808080')

            card = html.Div([
                html.Div([
                    html.H4(f"{signal_data.get('strike')}{signal_data.get('option_type')}",
                           style={'margin': '0', 'color': color}),
                    html.P(f"Confidence: {signal_data.get('final_confidence', 0):.1%}",
                          style={'margin': '5px 0', 'fontSize': '14px'}),
                    html.P(f"Strength: {strength}",
                          style={'margin': '5px 0', 'fontSize': '12px', 'color': color}),
                    html.P(f"Action: {signal_data.get('action', 'MONITOR')}",
                          style={'margin': '5px 0', 'fontSize': '12px'})
                ], style={
                    'backgroundColor': '#444444',
                    'padding': '10px',
                    'borderRadius': '5px',
                    'margin': '5px',
                    'border': f'2px solid {color}'
                })
            ])

            signal_cards.append(card)

        return html.Div(signal_cards, style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'center'})

    def _create_no_data_chart(self):
        """Create chart for no data scenario"""
        fig = go.Figure()
        fig.update_layout(
            title="No Data Available",
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            font=dict(color='#FFFFFF')
        )
        return fig

    def _create_no_data_info(self):
        """Create info panel for no data scenario"""
        return html.Div([
            html.P("No market data available. Check symbol and market hours.",
                  style={'textAlign': 'center', 'color': '#FFA500'})
        ])

    def _create_error_chart(self, error_msg):
        """Create chart for error scenario"""
        fig = go.Figure()
        fig.update_layout(
            title=f"Error: {error_msg}",
            plot_bgcolor='#1E1E1E',
            paper_bgcolor='#1E1E1E',
            font=dict(color='#FFFFFF')
        )
        return fig

    def _create_error_info(self, error_msg):
        """Create info panel for error scenario"""
        return html.Div([
            html.P(f"Error: {error_msg}", style={'textAlign': 'center', 'color': '#FF0000'})
        ])

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received")
        self.websocket_client.disconnect()
        sys.exit(0)

    def run(self, debug=False, open_browser=True):
        """Run the enhanced dashboard"""
        logger.info(f"Starting enhanced real-time IFD dashboard on port {self.port}")
        logger.info(f"WebSocket URI: {self.websocket_uri}")

        if open_browser:
            def open_browser_delayed():
                time.sleep(2)
                webbrowser.open(f'http://127.0.0.1:{self.port}')

            browser_thread = threading.Thread(target=open_browser_delayed)
            browser_thread.daemon = True
            browser_thread.start()

        try:
            self.app.run(debug=debug, host='127.0.0.1', port=self.port)
        except KeyboardInterrupt:
            logger.info("Dashboard shutdown requested")
            self.websocket_client.disconnect()

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Enhanced Real-Time NQ IFD Dashboard')
    parser.add_argument('--symbol', default='NQM5', help='Futures symbol to display')
    parser.add_argument('--hours', type=int, default=4, help='Number of hours to display')
    parser.add_argument('--update-interval', type=int, default=10, help='Update interval in seconds')
    parser.add_argument('--port', type=int, default=8051, help='Dashboard port')
    parser.add_argument('--websocket-uri', default='ws://localhost:8765', help='WebSocket server URI')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--no-browser', action='store_true', help='Don\'t open browser automatically')

    args = parser.parse_args()

    # Create and run dashboard
    dashboard = NQRealtimeIFDDashboard(
        symbol=args.symbol,
        hours=args.hours,
        update_interval=args.update_interval,
        port=args.port,
        websocket_uri=args.websocket_uri
    )

    dashboard.run(debug=args.debug, open_browser=not args.no_browser)

if __name__ == "__main__":
    main()
