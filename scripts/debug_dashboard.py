#!/usr/bin/env python3
"""
Debug Dashboard - Simplified version to identify graph issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import logging
import pytz

from databento_5m_provider import Databento5MinuteProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize app
app = dash.Dash(__name__)
app.title = "Debug Dashboard"

# Initialize data provider
data_provider = Databento5MinuteProvider(enable_ifd_signals=False)

# Layout
app.layout = html.Div([
    html.H1("Debug Dashboard - Checking Chart", style={'textAlign': 'center'}),
    html.Div(id='status', style={'textAlign': 'center', 'margin': '20px'}),
    dcc.Graph(id='chart', style={'height': '600px'}),
    dcc.Interval(id='interval', interval=30000)
], style={'backgroundColor': '#f0f0f0', 'padding': '20px'})

@app.callback(
    [Output('chart', 'figure'), Output('status', 'children')],
    [Input('interval', 'n_intervals')]
)
def update_chart(n):
    try:
        logger.info("Fetching data...")

        # Get data
        df = data_provider.get_latest_bars(symbol="NQM5", count=48)

        if df.empty:
            logger.warning("No data returned")
            fig = go.Figure()
            fig.add_annotation(
                text="No data available - markets may be closed",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font=dict(size=20)
            )
            return fig, "No data available"

        logger.info(f"Got {len(df)} bars")

        # Convert to Eastern time
        et_tz = pytz.timezone('US/Eastern')
        df_display = df.copy()
        df_display.index = df_display.index.tz_convert(et_tz)

        # Create simple chart
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.7, 0.3],
            subplot_titles=('Price', 'Volume')
        )

        # Add candlestick
        fig.add_trace(
            go.Candlestick(
                x=df_display.index,
                open=df_display['open'],
                high=df_display['high'],
                low=df_display['low'],
                close=df_display['close'],
                name='NQM5'
            ),
            row=1, col=1
        )

        # Add volume
        fig.add_trace(
            go.Bar(
                x=df_display.index,
                y=df_display['volume'],
                name='Volume',
                marker_color='blue'
            ),
            row=2, col=1
        )

        # Update layout
        fig.update_layout(
            height=600,
            showlegend=False,
            xaxis_rangeslider_visible=False
        )

        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)

        last_price = df['close'].iloc[-1]
        status = f"Last Price: ${last_price:,.2f} | Bars: {len(df)} | Last Update: {datetime.now().strftime('%H:%M:%S')}"

        return fig, status

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

        fig = go.Figure()
        fig.add_annotation(
            text=f"Error: {str(e)}",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=16, color='red')
        )
        return fig, f"Error: {str(e)}"

if __name__ == '__main__':
    print("Starting debug dashboard on http://127.0.0.1:8051/")
    app.run(debug=True, host='127.0.0.1', port=8051)
