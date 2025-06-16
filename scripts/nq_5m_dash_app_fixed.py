#!/usr/bin/env python3
"""
Fixed NQ Futures 5-Minute Chart with IFD Integration
Simplified version to avoid white screen issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create app
app = dash.Dash(__name__)
app.title = "NQ 5-Minute Chart with IFD"

# Create demo data since markets are closed
def create_demo_data():
    """Create demo candlestick data"""
    times = pd.date_range(start='2024-03-15 09:30:00', periods=48, freq='5min', tz='US/Eastern')
    base_price = 21800
    prices = []

    for i in range(48):
        price = base_price + np.sin(i/5) * 50 + np.random.normal(0, 10)
        prices.append(price)

    df = pd.DataFrame({
        'open': [p - np.random.uniform(0, 10) for p in prices],
        'high': [p + np.random.uniform(0, 20) for p in prices],
        'low': [p - np.random.uniform(0, 20) for p in prices],
        'close': prices,
        'volume': [np.random.randint(1000, 5000) for _ in prices]
    }, index=times)

    # Ensure OHLC consistency
    for i in range(len(df)):
        df.loc[df.index[i], 'high'] = max(df.iloc[i][['open', 'high', 'low', 'close']])
        df.loc[df.index[i], 'low'] = min(df.iloc[i][['open', 'high', 'low', 'close']])

    return df

# Create demo IFD signals
def create_demo_signals(df):
    """Create demo IFD signals"""
    signals = []
    signal_times = [df.index[i] for i in [5, 12, 20, 28, 35, 42]]

    for i, time in enumerate(signal_times):
        if i % 3 == 0:
            action = "STRONG_BUY"
            color = "lime"
            confidence = 0.85
        elif i % 3 == 1:
            action = "BUY"
            color = "green"
            confidence = 0.75
        else:
            action = "MONITOR"
            color = "orange"
            confidence = 0.65

        signals.append({
            'time': time,
            'action': action,
            'color': color,
            'confidence': confidence,
            'price': df.loc[time, 'high'] if 'BUY' in action else df.loc[time, 'low']
        })

    return signals

# Layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("NQM5 - Real-Time 5-Minute Chart with IFD v3.0",
                style={'textAlign': 'center', 'color': 'white', 'marginBottom': '10px'}),
        html.Div([
            html.Span("🔴 DEMO MODE - Markets Closed",
                     style={'color': '#FF0000', 'fontWeight': 'bold'}),
            html.Span(" | Last Update: ", style={'color': '#CCCCCC', 'marginLeft': '20px'}),
            html.Span(id='update-time', style={'color': '#00FF00'})
        ], style={'textAlign': 'center', 'marginBottom': '20px'})
    ]),

    # Controls
    html.Div([
        html.Label("IFD Configuration: ", style={'color': 'white', 'marginRight': '10px'}),
        dcc.Dropdown(
            id='ifd-dropdown',
            options=[
                {'label': 'Default (No IFD)', 'value': 'none'},
                {'label': 'IFD Enabled', 'value': 'enabled'},
                {'label': 'IFD Advanced', 'value': 'advanced'},
                {'label': 'IFD Minimal', 'value': 'minimal'}
            ],
            value='enabled',
            style={'width': '200px', 'display': 'inline-block'}
        ),
        html.Button('Refresh', id='refresh-btn', n_clicks=0,
                   style={'marginLeft': '20px', 'backgroundColor': '#0066CC',
                          'color': 'white', 'border': 'none', 'padding': '5px 15px'})
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),

    # Status
    html.Div(id='status', style={'textAlign': 'center', 'color': 'white', 'marginBottom': '10px'}),

    # Chart
    dcc.Graph(id='main-chart', style={'height': '70vh'}),

    # Auto refresh
    dcc.Interval(id='interval', interval=30000)

], style={'backgroundColor': '#1E1E1E', 'minHeight': '100vh', 'padding': '20px'})

# Callback
@app.callback(
    [Output('main-chart', 'figure'),
     Output('update-time', 'children'),
     Output('status', 'children')],
    [Input('interval', 'n_intervals'),
     Input('refresh-btn', 'n_clicks'),
     Input('ifd-dropdown', 'value')]
)
def update_chart(n_intervals, n_clicks, ifd_mode):
    """Update chart with demo data"""

    # Create demo data
    df = create_demo_data()

    # Create figure
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=('NQM5 - 5 Minute Chart (Demo)', 'Volume')
    )

    # Add candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='NQM5',
            increasing_line_color='#00FF00',
            decreasing_line_color='#FF0000'
        ),
        row=1, col=1
    )

    # Add volume
    colors = ['#FF0000' if c < o else '#00FF00'
              for c, o in zip(df['close'], df['open'])]

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.7
        ),
        row=2, col=1
    )

    # Add IFD signals if enabled
    signal_count = 0
    if ifd_mode != 'none':
        signals = create_demo_signals(df)

        # Filter signals based on mode
        if ifd_mode == 'minimal':
            signals = [s for s in signals if s['confidence'] >= 0.8]
        elif ifd_mode == 'enabled':
            signals = [s for s in signals if s['confidence'] >= 0.7]

        signal_count = len(signals)

        # Add signal markers
        for signal in signals:
            symbol = 'triangle-up' if 'BUY' in signal['action'] else 'triangle-down'
            y_offset = df['high'].max() * 0.01
            y_pos = signal['price'] + y_offset if 'BUY' in signal['action'] else signal['price'] - y_offset

            fig.add_trace(
                go.Scatter(
                    x=[signal['time']],
                    y=[y_pos],
                    mode='markers',
                    name=signal['action'],
                    marker=dict(
                        symbol=symbol,
                        size=20 if signal['confidence'] > 0.8 else 15,
                        color=signal['color'],
                        line=dict(width=2, color='white')
                    ),
                    hovertext=f"{signal['action']}<br>Confidence: {signal['confidence']:.0%}",
                    hoverinfo='text',
                    showlegend=False
                ),
                row=1, col=1
            )

    # Update layout
    fig.update_layout(
        template='plotly_dark',
        height=600,
        showlegend=False,
        hovermode='x unified',
        xaxis_rangeslider_visible=False,
        paper_bgcolor='#1E1E1E',
        plot_bgcolor='#2E2E2E'
    )

    # Update axes
    fig.update_xaxes(gridcolor='#444', row=2, col=1)
    fig.update_yaxes(gridcolor='#444', row=1, col=1)
    fig.update_yaxes(gridcolor='#444', row=2, col=1)

    # Status
    last_price = df['close'].iloc[-1]
    status = f"Last: ${last_price:,.2f} | High: ${df['high'].max():,.2f} | Low: ${df['low'].min():,.2f}"
    if signal_count > 0:
        status += f" | IFD Signals: {signal_count}"

    # Time
    current_time = datetime.now().strftime("%H:%M:%S")

    return fig, current_time, status

if __name__ == '__main__':
    print("🚀 Starting Fixed Dashboard on http://127.0.0.1:8050/")
    print("📊 This version includes:")
    print("   ✅ Demo data (markets closed)")
    print("   ✅ Working IFD signal overlays")
    print("   ✅ Dark theme")
    print("   ✅ Simplified rendering")
    app.run(debug=True, host='127.0.0.1', port=8050)
