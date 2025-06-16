#!/usr/bin/env python3
"""
Minimal Dash Test - Diagnose rendering issues
"""

import dash
from dash import dcc, html
import plotly.graph_objects as go

# Create minimal app
app = dash.Dash(__name__)

# Simple layout
app.layout = html.Div([
    html.H1("Minimal Dash Test", style={'textAlign': 'center'}),
    html.Div("If you can see this text, Dash is working!", style={'textAlign': 'center', 'fontSize': '20px', 'margin': '20px'}),
    dcc.Graph(
        id='test-graph',
        figure={
            'data': [
                {'x': [1, 2, 3, 4], 'y': [4, 1, 3, 5], 'type': 'scatter', 'name': 'Test'},
            ],
            'layout': {
                'title': 'Simple Test Chart'
            }
        }
    )
])

if __name__ == '__main__':
    print("Starting minimal test on http://127.0.0.1:8052/")
    app.run(debug=True, host='127.0.0.1', port=8052)
