#!/usr/bin/env python3
"""
Enhanced Real-Time NQ Futures 5-Minute Chart with IFD v3.0 Integration
Auto-refreshes in browser with configurable IFD signal overlays
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import json
import dash
from dash import dcc, html, Input, Output, callback, State
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

from databento_5m_provider import Databento5MinuteProvider
# Simple time formatting function
def format_eastern_display(dt=None):
    """Format datetime for Eastern time display"""
    if dt is None:
        dt = datetime.now(pytz.timezone('US/Eastern'))
    elif hasattr(dt, 'tz_convert'):
        dt = dt.tz_convert(pytz.timezone('US/Eastern'))
    elif hasattr(dt, 'astimezone'):
        dt = dt.astimezone(pytz.timezone('US/Eastern'))
    return dt.strftime('%Y-%m-%d %H:%M:%S ET')
from chart_config_manager import ChartConfigManager

# Import IFD components
try:
    from ifd_chart_bridge import IFDAggregatedSignal
    IFD_AVAILABLE = True
except ImportError:
    IFD_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NQDashAppIFD:
    """Enhanced Real-time NQ 5-minute chart with IFD v3.0 integration"""

    def __init__(self, symbol="NQM5", hours=4, update_interval=30, port=8050):
        self.symbol = symbol
        self.hours = hours
        self.update_interval = update_interval * 1000  # Convert to milliseconds
        self.port = port

        # Initialize configuration manager
        self.config_manager = ChartConfigManager()
        self.current_config = "default"

        # Initialize data provider with IFD support
        self.data_provider = Databento5MinuteProvider(enable_ifd_signals=IFD_AVAILABLE)

        # Initialize Dash app
        self.app = dash.Dash(__name__)
        self.app.title = f"{symbol} - Real-Time 5-Minute Chart with IFD"

        # Set up layout
        self._setup_layout()

        # Set up callbacks
        self._setup_callbacks()

        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _setup_layout(self):
        """Set up the enhanced Dash app layout with IFD controls"""

        # Get available configurations
        available_configs = ["default", "ifd_enabled", "ifd_advanced", "ifd_minimal"]
        config_options = [
            {'label': 'Default (No IFD)', 'value': 'default'},
            {'label': 'IFD Enabled', 'value': 'ifd_enabled'},
            {'label': 'IFD Advanced', 'value': 'ifd_advanced'},
            {'label': 'IFD Minimal', 'value': 'ifd_minimal'}
        ]

        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1(
                    f"{self.symbol} - Real-Time 5-Minute Chart with IFD v3.0",
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
                    html.Span(" | IFD: ", style={'color': '#CCCCCC', 'marginLeft': '10px'}),
                    html.Span("Available" if IFD_AVAILABLE else "Not Available",
                             style={'color': '#00FF00' if IFD_AVAILABLE else '#FF0000', 'fontWeight': 'bold'}),
                    html.Span(f" | Last updated: ",
                             style={'color': '#CCCCCC', 'marginLeft': '10px'}),
                    html.Span(id='last-update-time',
                             style={'color': '#00FF00', 'fontWeight': 'bold'})
                ], style={'textAlign': 'center', 'marginBottom': '20px'})
            ]),

            # Enhanced Controls with IFD Configuration
            html.Div([
                # First row of controls
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
                    'marginBottom': '15px'
                }),

                # Second row - IFD Configuration
                html.Div([
                    html.Label("IFD Configuration:",
                              style={'color': '#FFFFFF', 'marginRight': '10px', 'fontWeight': 'bold'}),
                    dcc.Dropdown(
                        id='ifd-config-dropdown',
                        options=config_options,
                        value='default',
                        style={
                            'backgroundColor': '#2E2E2E',
                            'color': '#000000',
                            'width': '160px',
                            'marginRight': '20px'
                        },
                        disabled=not IFD_AVAILABLE
                    ),
                    html.Div(id='ifd-status-indicator', style={'display': 'inline-block'})
                ], style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'center',
                    'marginBottom': '20px'
                })
            ]),

            # IFD Configuration Info Panel
            html.Div(id='ifd-info-panel', style={
                'backgroundColor': '#2E2E2E',
                'border': '1px solid #555',
                'borderRadius': '8px',
                'padding': '10px',
                'margin': '10px auto',
                'maxWidth': '800px',
                'color': '#FFFFFF'
            }),

            # Status indicators
            html.Div([
                html.Div(id='price-display', style={
                    'textAlign': 'center',
                    'fontSize': '24px',
                    'fontWeight': 'bold',
                    'color': '#00FF00',
                    'marginBottom': '10px'
                }),
                html.Div(id='statistics-display', style={
                    'textAlign': 'center',
                    'fontSize': '14px',
                    'color': '#CCCCCC',
                    'marginBottom': '20px'
                })
            ]),

            # Chart
            dcc.Graph(
                id='live-chart',
                style={'height': '75vh'},
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

            # Store for configuration data
            dcc.Store(id='config-store')

        ], style={'backgroundColor': '#1E1E1E', 'minHeight': '100vh', 'padding': '20px'})

    def _setup_callbacks(self):
        """Set up Dash callbacks for interactivity"""

        @self.app.callback(
            Output('config-store', 'data'),
            Input('ifd-config-dropdown', 'value')
        )
        def update_config_store(config_name):
            """Update stored configuration when dropdown changes"""
            try:
                if config_name and config_name != 'default':
                    # Load the actual config file
                    config_path = f"configs/{config_name}.json"
                    if os.path.exists(config_path):
                        import json
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                        return config
                    else:
                        # Return a basic config if file doesn't exist
                        return {
                            'indicators': {
                                'ifd_v3': {
                                    'show_signals': True,
                                    'min_confidence_display': 0.7
                                }
                            }
                        }
                return {}
            except Exception as e:
                logger.error(f"Failed to load config {config_name}: {e}")
                return {}

        @self.app.callback(
            Output('ifd-info-panel', 'children'),
            Input('ifd-config-dropdown', 'value')
        )
        def update_ifd_info(config_name):
            """Update IFD configuration info panel"""
            if not config_name or config_name == 'default':
                return html.Div([
                    html.H4("📊 Standard Chart Mode", style={'color': '#00BFFF', 'margin': '0 0 10px 0'}),
                    html.P("Displaying 5-minute candlestick chart with volume. No IFD signals.",
                           style={'margin': '0'})
                ])

            try:
                config = self.config_manager.load_config(config_name)
                ifd_config = config.get('indicators', {}).get('ifd_v3', {})

                if not ifd_config:
                    return html.Div([
                        html.H4("⚠️ Configuration Error", style={'color': '#FFA500', 'margin': '0 0 10px 0'}),
                        html.P(f"IFD configuration not found in {config_name}", style={'margin': '0'})
                    ])

                # Create configuration summary
                show_signals = ifd_config.get('show_signals', False)
                min_confidence = ifd_config.get('min_confidence_display', 0.0)
                show_background = ifd_config.get('show_confidence_background', False)
                max_signals = ifd_config.get('performance', {}).get('max_signals_display', 200)

                config_descriptions = {
                    'ifd_enabled': '🟢 Basic IFD integration with standard settings',
                    'ifd_advanced': '🔵 Advanced IFD with background highlighting and more indicators',
                    'ifd_minimal': '🟡 Performance-optimized IFD with high confidence threshold'
                }

                return html.Div([
                    html.H4(f"🎯 {config_name.replace('_', ' ').title()}",
                            style={'color': '#00FF00', 'margin': '0 0 10px 0'}),
                    html.P(config_descriptions.get(config_name, 'Custom IFD configuration'),
                           style={'margin': '0 0 10px 0'}),
                    html.Div([
                        html.Span(f"Signals: {'✅' if show_signals else '❌'}",
                                 style={'marginRight': '20px'}),
                        html.Span(f"Min Confidence: {min_confidence:.0%}",
                                 style={'marginRight': '20px'}),
                        html.Span(f"Background: {'✅' if show_background else '❌'}",
                                 style={'marginRight': '20px'}),
                        html.Span(f"Max Display: {max_signals}")
                    ], style={'fontSize': '12px', 'color': '#CCCCCC'})
                ])

            except Exception as e:
                return html.Div([
                    html.H4("❌ Configuration Error", style={'color': '#FF0000', 'margin': '0 0 10px 0'}),
                    html.P(f"Failed to load {config_name}: {str(e)}", style={'margin': '0'})
                ])

        @self.app.callback(
            [Output('live-chart', 'figure'),
             Output('last-update-time', 'children'),
             Output('price-display', 'children'),
             Output('statistics-display', 'children')],
            [Input('interval-component', 'n_intervals'),
             Input('symbol-input', 'value'),
             Input('hours-dropdown', 'value'),
             Input('reset-button', 'n_clicks'),
             Input('ifd-config-dropdown', 'value')],
            [State('config-store', 'data')]
        )
        def update_chart(n_intervals, symbol, hours, reset_clicks, ifd_config_name, config_data):
            """Update the chart with latest data and IFD signals"""
            try:
                # Update instance variables
                self.symbol = symbol or "NQM5"
                self.hours = hours or 4

                # Calculate number of bars needed
                bars_needed = (self.hours * 60) // 5

                # Get data based on whether IFD is enabled
                current_time = datetime.now(pytz.UTC)

                # Check if IFD is enabled from dropdown
                ifd_enabled = ifd_config_name and ifd_config_name != 'default'

                if ifd_enabled:
                    # Get data with IFD signals
                    df, ifd_signals = self.data_provider.get_latest_bars_with_ifd(
                        symbol=self.symbol,
                        count=bars_needed
                    )
                    logger.info(f"Retrieved {len(df)} bars and {len(ifd_signals)} IFD signals")
                else:
                    # Get regular OHLCV data
                    df = self.data_provider.get_latest_bars(
                        symbol=self.symbol,
                        count=bars_needed
                    )
                    ifd_signals = []

                if df.empty:
                    # Create demo mode chart
                    fig, df_demo = self._create_demo_chart_with_data()

                    # Add IFD signals if enabled
                    if ifd_enabled and config_data:
                        demo_ifd_signals = self._create_demo_ifd_signals()
                        if demo_ifd_signals:
                            self._add_ifd_overlay(fig, df_demo, demo_ifd_signals, config_data)

                    return fig, format_eastern_display(), "Demo Mode", "Markets Closed - Showing Sample Data"

                # Create chart
                fig = self._create_chart(df, ifd_signals, config_data)

                # Update status
                last_price = df['close'].iloc[-1]
                high_price = df['high'].max()
                low_price = df['low'].min()
                total_volume = df['volume'].sum()

                price_display = f"${last_price:,.2f}"
                stats_display = f"High: ${high_price:,.2f} | Low: ${low_price:,.2f} | Volume: {total_volume:,}"
                if ifd_signals:
                    stats_display += f" | IFD Signals: {len(ifd_signals)}"

                return fig, format_eastern_display(), price_display, stats_display

            except Exception as e:
                logger.error(f"Error updating chart: {e}")
                empty_fig = self._create_empty_chart()
                # Create demo chart on error
                fig, _ = self._create_demo_chart_with_data()
                return fig, format_eastern_display(), "Error", f"Chart update failed: {str(e)}"

    def _create_chart(self, df, ifd_signals=None, config_data=None):
        """Create plotly chart with optional IFD overlay"""
        # Convert UTC timestamps to Eastern Time for display
        et_tz = pytz.timezone('US/Eastern')
        df_display = df.copy()
        df_display.index = df_display.index.tz_convert(et_tz)

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
            x=df_display.index,
            open=df_display['open'],
            high=df_display['high'],
            low=df_display['low'],
            close=df_display['close'],
            name='Price',
            increasing_line_color='#00FF00',
            decreasing_line_color='#FF0000'
        )
        fig.add_trace(candlestick, row=1, col=1)

        # Add volume bars
        colors = ['#FF0000' if close < open else '#00FF00'
                 for close, open in zip(df_display['close'], df_display['open'])]

        volume_bars = go.Bar(
            x=df_display.index,
            y=df_display['volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.7
        )
        fig.add_trace(volume_bars, row=2, col=1)

        # Add IFD signals if available and enabled
        if ifd_signals and config_data:
            self._add_ifd_overlay(fig, df_display, ifd_signals, config_data)

        # Update layout with dark theme
        fig.update_layout(
            title=dict(
                text=f"{self.symbol} - Real-Time 5 Minute Chart (Eastern Time)",
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
        fig.update_xaxes(title_text="Time (Eastern)", row=2, col=1)

        return fig

    def _add_ifd_overlay(self, fig, df_display, ifd_signals, config_data):
        """Add IFD signal overlay to the chart"""
        try:
            ifd_config = config_data.get('indicators', {}).get('ifd_v3', {})

            if not ifd_config.get('show_signals', True):
                return

            # Configuration settings
            min_confidence = ifd_config.get('min_confidence_display', 0.7)
            signal_colors = ifd_config.get('signal_colors', {
                'STRONG_BUY': '#00FF00',
                'BUY': '#32CD32',
                'MONITOR': '#FFA500',
                'IGNORE': '#808080'
            })
            marker_sizes = ifd_config.get('marker_sizes', {
                'EXTREME': 20,
                'VERY_HIGH': 16,
                'HIGH': 12,
                'MODERATE': 8
            })

            # Process signals for display
            signal_groups = {}

            for signal in ifd_signals:
                if signal.max_confidence < min_confidence:
                    continue

                action = signal.dominant_action
                if action not in signal_groups:
                    signal_groups[action] = {
                        'timestamps': [],
                        'prices': [],
                        'hover_texts': [],
                        'sizes': []
                    }

                # Find matching OHLCV bar for price placement
                signal_time = signal.window_timestamp
                matching_bar = None
                for idx, bar_time in enumerate(df_display.index):
                    if abs((bar_time.to_pydatetime() - signal_time).total_seconds()) < 300:
                        matching_bar = df_display.iloc[idx]
                        break

                if matching_bar is not None:
                    # Position signal relative to candlestick
                    if action in ["STRONG_BUY", "BUY"]:
                        price_level = matching_bar['high'] + (matching_bar['high'] - matching_bar['low']) * 0.1
                    else:
                        price_level = matching_bar['low'] - (matching_bar['high'] - matching_bar['low']) * 0.1

                    # Create hover text
                    hover_text = (
                        f"IFD Signal<br>"
                        f"Action: {action}<br>"
                        f"Confidence: {signal.max_confidence:.1%}<br>"
                        f"Strength: {signal.window_strength}<br>"
                        f"Signals: {signal.signal_count}<br>"
                        f"Time: {signal_time.strftime('%H:%M')}"
                    )

                    signal_groups[action]['timestamps'].append(signal_time)
                    signal_groups[action]['prices'].append(price_level)
                    signal_groups[action]['hover_texts'].append(hover_text)

                    # Determine marker size
                    size = marker_sizes.get(signal.window_strength, 8)
                    signal_groups[action]['sizes'].append(size)

            # Add trace for each signal action type
            for action, group_data in signal_groups.items():
                if not group_data['timestamps']:
                    continue

                color = signal_colors.get(action, '#808080')
                marker_symbol = "triangle-up" if action in ["STRONG_BUY", "BUY"] else "triangle-down"

                fig.add_trace(
                    go.Scatter(
                        x=group_data['timestamps'],
                        y=group_data['prices'],
                        mode='markers',
                        name=f'IFD {action}',
                        marker=dict(
                            symbol=marker_symbol,
                            size=group_data['sizes'],
                            color=color,
                            line=dict(width=1, color='white')
                        ),
                        hovertext=group_data['hover_texts'],
                        hoverinfo='text',
                        showlegend=True
                    ),
                    row=1, col=1
                )

        except Exception as e:
            logger.error(f"Failed to add IFD overlay: {e}")

    def _create_demo_chart_with_data(self):
        """Create demo chart with realistic data for weekend display"""
        # Generate demo data
        times = pd.date_range(start='2024-03-15 09:30:00', periods=48, freq='5min', tz='US/Eastern')
        base_price = 21800
        prices = []

        for i in range(48):
            price = base_price + np.sin(i/5) * 50 + np.random.normal(0, 10)
            prices.append(price)

        df_demo = pd.DataFrame({
            'open': [p - np.random.uniform(0, 10) for p in prices],
            'high': [p + np.random.uniform(0, 20) for p in prices],
            'low': [p - np.random.uniform(0, 20) for p in prices],
            'close': prices,
            'volume': [np.random.randint(1000, 5000) for _ in prices]
        }, index=times)

        # Ensure OHLC consistency
        for i in range(len(df_demo)):
            df_demo.loc[df_demo.index[i], 'high'] = max(df_demo.iloc[i][['open', 'high', 'low', 'close']])
            df_demo.loc[df_demo.index[i], 'low'] = min(df_demo.iloc[i][['open', 'high', 'low', 'close']])

        # Create the chart using the existing _create_chart method
        fig = self._create_chart(df_demo, ifd_signals=None, config_data=None)

        # Update title for demo mode
        fig.update_layout(
            title=dict(
                text=f"{self.symbol} - Demo Mode (Markets Closed)",
                font=dict(size=20, color='#FFFFFF')
            ),
            annotations=[
                dict(
                    text="📊 Showing sample data. Real data available during market hours.<br>Futures: Sun 6PM - Fri 5PM ET",
                    xref="paper", yref="paper",
                    x=0.5, y=0.95,
                    xanchor='center', yanchor='top',
                    showarrow=False,
                    font=dict(size=14, color='#FFAA00'),
                    bgcolor='rgba(0,0,0,0.7)',
                    borderpad=10
                )
            ]
        )

        return fig, df_demo

    def _create_demo_ifd_signals(self):
        """Create demo IFD signals for weekend/closed market display"""
        try:
            # Create simple demo signals without importing IFDAggregatedSignal
            base_time = pd.Timestamp('2024-03-15 09:30:00', tz='US/Eastern')
            demo_signals = []

            # Simple signal structure that matches what _add_ifd_overlay expects
            signal_configs = [
                (5, 0.85, 'EXTREME', 'STRONG_BUY'),
                (12, 0.75, 'HIGH', 'BUY'),
                (20, 0.65, 'MODERATE', 'MONITOR'),
                (28, 0.90, 'VERY_HIGH', 'STRONG_BUY'),
                (35, 0.72, 'HIGH', 'BUY'),
                (42, 0.68, 'MODERATE', 'MONITOR')
            ]

            for offset_minutes, confidence, strength, action in signal_configs:
                signal_time = base_time + pd.Timedelta(minutes=offset_minutes)

                # Create a simple object with the required attributes
                class DemoSignal:
                    def __init__(self):
                        self.window_timestamp = signal_time.to_pydatetime()
                        self.max_confidence = confidence
                        self.dominant_action = action
                        self.window_strength = strength
                        self.signal_count = 2

                demo_signals.append(DemoSignal())

            return demo_signals

        except Exception as e:
            logger.warning(f"Could not create demo IFD signals: {e}")
            return []

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received")
        sys.exit(0)

    def run(self, debug=False, open_browser=True):
        """Run the Dash app"""
        logger.info(f"Starting enhanced NQ chart with IFD integration on port {self.port}")
        logger.info(f"IFD Available: {IFD_AVAILABLE}")

        if open_browser:
            # Open browser after a short delay
            def open_browser_delayed():
                time.sleep(2)
                webbrowser.open(f'http://127.0.0.1:{self.port}')

            browser_thread = threading.Thread(target=open_browser_delayed)
            browser_thread.daemon = True
            browser_thread.start()

        try:
            self.app.run(debug=debug, host='127.0.0.1', port=self.port)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error running app: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Enhanced NQ Futures 5-Minute Chart with IFD')
    parser.add_argument('--symbol', default='NQM5', help='Contract symbol')
    parser.add_argument('--hours', type=int, default=4, help='Hours of data to display')
    parser.add_argument('--update', type=int, default=30, help='Update interval in seconds')
    parser.add_argument('--port', type=int, default=8050, help='Port to run on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--no-browser', action='store_true', help='Don\'t open browser automatically')

    args = parser.parse_args()

    # Create and run app
    app = NQDashAppIFD(
        symbol=args.symbol,
        hours=args.hours,
        update_interval=args.update,
        port=args.port
    )

    app.run(debug=args.debug, open_browser=not args.no_browser)

if __name__ == "__main__":
    main()
