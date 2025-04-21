import psutil
import GPUtil
import os
import time
import numpy as np
import pandas as pd
import threading
from collections import deque
from datetime import datetime
import plotly.graph_objs as go
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import wmi

# Data Storage Class
class SystemDataStore:
    def __init__(self, max_points=100):
        self.max_points = max_points
        self.timestamps = deque(maxlen=max_points)
        self.cpu_data = deque(maxlen=max_points)
        self.ram_data = deque(maxlen=max_points)
        self.disk_data = deque(maxlen=max_points)
        self.gpu_data = deque(maxlen=max_points)
        self.temp_data = deque(maxlen=max_points)
        self.network_sent = deque(maxlen=max_points)
        self.network_recv = deque(maxlen=max_points)

    def update(self, metrics):
        self.timestamps.append(datetime.now())
        self.cpu_data.append(metrics['cpu_usage'])
        self.ram_data.append(metrics['ram_usage'])
        self.disk_data.append(metrics['disk_usage'])
        self.gpu_data.append(metrics['gpu_usage'])
        self.temp_data.append(metrics['temperature'])
        self.network_sent.append(metrics['network_sent'])
        self.network_recv.append(metrics['network_recv'])

# System Metrics Collection
def get_cpu_temperature():
    try:
        w = wmi.WMI(namespace="root\\WMI")
        temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
        return (temperature_info.CurrentTemperature / 10.0) - 273.15
    except:
        return 45.0

def get_system_metrics():
    gpus = GPUtil.getGPUs()
    net_io = psutil.net_io_counters()
    
    return {
        "cpu_usage": psutil.cpu_percent(interval=1),
        "ram_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "gpu_usage": gpus[0].load * 100 if gpus else 0,
        "temperature": get_cpu_temperature(),
        "network_sent": net_io.bytes_sent,
        "network_recv": net_io.bytes_recv
    }

# Initialize Dash app
app = Dash(__name__,
           external_stylesheets=[
               dbc.themes.BOOTSTRAP,
               'https://use.fontawesome.com/releases/v5.15.4/css/all.css'
           ])

# Initialize data store
data_store = SystemDataStore()

# App Layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1("PC Doctor - Advanced System Monitor", className="dashboard-title"),
                html.P("Real-time system performance monitoring and analysis", className="dashboard-subtitle"),
            ], className="dashboard-header text-center")
        ], width=12)
    ]),

    # Quick Stats
    dbc.Row([
        dbc.Col([
            html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.H3(id="cpu-stat", className="stat-value"),
                            html.P("CPU Usage", className="stat-label")
                        ], className="stat-item")
                    ], width=3),
                    dbc.Col([
                        html.Div([
                            html.H3(id="ram-stat", className="stat-value"),
                            html.P("RAM Usage", className="stat-label")
                        ], className="stat-item")
                    ], width=3),
                    dbc.Col([
                        html.Div([
                            html.H3(id="temp-stat", className="stat-value"),
                            html.P("Temperature", className="stat-label")
                        ], className="stat-item")
                    ], width=3),
                    dbc.Col([
                        html.Div([
                            html.H3(id="disk-stat", className="stat-value"),
                            html.P("Disk Usage", className="stat-label")
                        ], className="stat-item")
                    ], width=3),
                ])
            ], className="stats-container")
        ], width=12)
    ]),

    # Control Panel
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-cogs me-2"),
                    "System Controls"
                ]),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.ButtonGroup([
                                dbc.Button([
                                    html.I(className="fas fa-sync-alt me-2"),
                                    "Refresh"
                                ], id="refresh-btn", color="primary", className="me-2"),
                                dbc.Button([
                                    html.I(className="fas fa-download me-2"),
                                    "Export Data"
                                ], id="export-btn", color="success"),
                            ]),
                        ], width=6),
                        dbc.Col([
                            dbc.Select(
                                id='time-range',
                                options=[
                                    {'label': 'Last 5 minutes', 'value': '5'},
                                    {'label': 'Last 15 minutes', 'value': '15'},
                                    {'label': 'Last 1 hour', 'value': '60'}
                                ],
                                value='5',
                                className="w-100"
                            )
                        ], width=6),
                    ])
                ])
            ], className="mb-4")
        ], width=12)
    ]),

    # Main Graphs
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-microchip me-2"),
                    "CPU & RAM Usage"
                ]),
                dbc.CardBody([
                    dcc.Graph(id='cpu-ram-graph'),
                    html.Div([
                        dbc.Checklist(
                            options=[
                                {"label": "Show CPU", "value": "cpu"},
                                {"label": "Show RAM", "value": "ram"},
                            ],
                            value=["cpu", "ram"],
                            id="cpu-ram-options",
                            inline=True,
                            switch=True,
                        )
                    ], className="checklist-item")
                ])
            ])
        ], width=6),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-hdd me-2"),
                    "Disk & GPU Usage"
                ]),
                dbc.CardBody([
                    dcc.Graph(id='disk-gpu-graph'),
                    html.Div([
                        dbc.Checklist(
                            options=[
                                {"label": "Show Disk", "value": "disk"},
                                {"label": "Show GPU", "value": "gpu"},
                            ],
                            value=["disk", "gpu"],
                            id="disk-gpu-options",
                            inline=True,
                            switch=True,
                        )
                    ], className="checklist-item")
                ])
            ])
        ], width=6)
    ]),

    # Temperature and Network
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-thermometer-half me-2"),
                    "Temperature"
                ]),
                dbc.CardBody([
                    dcc.Graph(id='temp-gauge'),
                    html.Div(id='temp-alert')
                ])
            ])
        ], width=4),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-network-wired me-2"),
                    "Network Traffic"
                ]),
                dbc.CardBody([
                    dcc.Graph(id='network-graph'),
                    html.Div([
                        dbc.RadioItems(
                            options=[
                                {"label": "KB/s", "value": "KB"},
                                {"label": "MB/s", "value": "MB"},
                            ],
                            value="MB",
                            id="network-unit",
                            inline=True,
                            className="checklist-item"
                        )
                    ])
                ])
            ])
        ], width=8)
    ], className="mt-4"),

    # System Overview
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="fas fa-chart-pie me-2"),
                    "System Overview"
                ]),
                dbc.CardBody([
                    dcc.Graph(id='system-radar')
                ])
            ])
        ], width=12)
    ], className="mt-4"),

    # Team Section
        html.Div([
        html.H2("Meet the Creators", className="creator-title"),
        html.Div([
            dbc.Row([
                # Team Member 1
                dbc.Col([
                    html.Div([
                        html.Img(src="assets/images/team/shajith.JPG", className="creator-avatar"),
                        html.H3("Shajithrooban", className="creator-name"),
                        html.P("Fullstack Developer", className="creator-role"),
                        html.P("Full-stack developer with expertise in C++ and system monitoring", 
                               className="creator-bio"),
                        html.Div([
                            html.A([html.I(className="fab fa-github")], 
                                   href="https://github.com/rooban33", 
                                   className="creator-social-link"),
                            html.A([html.I(className="fab fa-linkedin")], 
                                   href="https://www.linkedin.com/in/shajith-rooban-b26453221/", 
                                   className="creator-social-link"),
                        ], className="creator-social")
                    ], className="creator-profile")
                ], width=6),  # Changed from width=4 to width=6 for two columns
                
                # Team Member 2
                dbc.Col([
                    html.Div([
                        html.Img(src="assets/images/team/pranav.JPG", className="creator-avatar"),
                        html.H3("Pranavarul", className="creator-name"),
                        html.P("Python Developer", className="creator-role"),
                        html.P("Creative designer with a passion for user experience", 
                               className="creator-bio"),
                        html.Div([
                            html.A([html.I(className="fab fa-github")], 
                                   href="https://github.com/janesmith", 
                                   className="creator-social-link"),
                            html.A([html.I(className="fab fa-linkedin")], 
                                   href="https://www.linkedin.com/in/pranavarul-karthikeyan-89945a223/", 
                                   className="creator-social-link"),
                        ], className="creator-social")
                    ], className="creator-profile")
                ], width=6)  # Changed from width=4 to width=6 for two columns
            ], justify="center")  # Added justify="center" to center the columns
        ], className="creator-grid")
    ], className="creator-card mt-4"),

    dcc.Interval(id='update-interval', interval=2000, n_intervals=0),
    dcc.Download(id="download-data")

], fluid=True, className="fade-in")

# Callbacks
@app.callback(
    [Output("cpu-stat", "children"),
     Output("ram-stat", "children"),
     Output("temp-stat", "children"),
     Output("disk-stat", "children")],
    Input('update-interval', 'n_intervals')
)
def update_quick_stats(n):
    metrics = get_system_metrics()
    return [
        f"{metrics['cpu_usage']}%",
        f"{metrics['ram_usage']}%",
        f"{metrics['temperature']}°C",
        f"{metrics['disk_usage']}%"
    ]

@app.callback(
    [Output('cpu-ram-graph', 'figure'),
     Output('disk-gpu-graph', 'figure'),
     Output('temp-gauge', 'figure'),
     Output('network-graph', 'figure'),
     Output('system-radar', 'figure')],
    [Input('update-interval', 'n_intervals'),
     Input('cpu-ram-options', 'value'),
     Input('disk-gpu-options', 'value'),
     Input('network-unit', 'value')]
)
def update_graphs(n, cpu_ram_opts, disk_gpu_opts, net_unit):
    metrics = get_system_metrics()
    data_store.update(metrics)

    # CPU & RAM Graph
    cpu_ram_fig = go.Figure()
    if "cpu" in cpu_ram_opts:
        cpu_ram_fig.add_trace(go.Scatter(
            x=list(data_store.timestamps),
            y=list(data_store.cpu_data),
            name="CPU Usage",
            line=dict(color="#e74c3c")
        ))
    if "ram" in cpu_ram_opts:
        cpu_ram_fig.add_trace(go.Scatter(
            x=list(data_store.timestamps),
            y=list(data_store.ram_data),
            name="RAM Usage",
            line=dict(color="#3498db")
        ))
    cpu_ram_fig.update_layout(
        title="CPU & RAM Usage",
        yaxis_title="Usage (%)",
        hovermode='x unified',
        template="plotly_dark"
    )

    # Disk & GPU Graph
    disk_gpu_fig = go.Figure()
    if "disk" in disk_gpu_opts:
        disk_gpu_fig.add_trace(go.Scatter(
            x=list(data_store.timestamps),
            y=list(data_store.disk_data),
            name="Disk Usage",
            line=dict(color="#2ecc71")
        ))
    if "gpu" in disk_gpu_opts:
        disk_gpu_fig.add_trace(go.Scatter(
            x=list(data_store.timestamps),
            y=list(data_store.gpu_data),
            name="GPU Usage",
            line=dict(color="#9b59b6")
        ))
    disk_gpu_fig.update_layout(
        title="Disk & GPU Usage",
        yaxis_title="Usage (%)",
        hovermode='x unified',
        template="plotly_dark"
    )

    # Temperature Gauge
    temp_gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=metrics['temperature'],
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "CPU Temperature (°C)"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "#e74c3c"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 70], 'color': "yellow"},
                {'range': [70, 100], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 80
            }
        }
    ))
    temp_gauge_fig.update_layout(template="plotly_dark")

    # Network Traffic Graph
    multiplier = 1024 * 1024 if net_unit == "MB" else 1024
    network_fig = go.Figure()
    network_fig.add_trace(go.Scatter(
        x=list(data_store.timestamps),
        y=[b/multiplier for b in data_store.network_sent],
        name=f'Sent ({net_unit}/s)',
        line=dict(color="#2ecc71")
    ))
    network_fig.add_trace(go.Scatter(
        x=list(data_store.timestamps),
        y=[b/multiplier for b in data_store.network_recv],
        name=f'Received ({net_unit}/s)',
        line=dict(color="#3498db")
    ))
    network_fig.update_layout(
        title="Network Traffic",
        yaxis_title=f"Traffic ({net_unit}/s)",
        hovermode='x unified',
        template="plotly_dark"
    )

    # System Radar Chart
    radar_fig = go.Figure()
    radar_fig.add_trace(go.Scatterpolar(
        r=[
            metrics['cpu_usage'],
            metrics['ram_usage'],
            metrics['disk_usage'],
            metrics['gpu_usage'],
            metrics['temperature']
        ],
        theta=['CPU', 'RAM', 'Disk', 'GPU', 'Temperature'],
        fill='toself',
        name='Current Usage'
    ))
    radar_fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=False,
        title="System Overview",
        template="plotly_dark"
    )

    return cpu_ram_fig, disk_gpu_fig, temp_gauge_fig, network_fig, radar_fig

@app.callback(
    Output('temp-alert', 'children'),
    Input('update-interval', 'n_intervals')
)
def update_temp_alert(n):
    metrics = get_system_metrics()
    if metrics['temperature'] > 80:
        return dbc.Alert(
            "Critical Temperature!",
            color="danger",
            dismissable=True
        )
    elif metrics['temperature'] > 70:
        return dbc.Alert(
            "High Temperature Warning",
            color="warning",
            dismissable=True
        )
    return None

@app.callback(
    Output("download-data", "data"),
    Input("export-btn", "n_clicks"),
    prevent_initial_call=True
)
def export_data(n_clicks):
    if n_clicks is None:
        raise PreventUpdate
        
    df = pd.DataFrame({
        'timestamp': list(data_store.timestamps),
        'cpu_usage': list(data_store.cpu_data),
        'ram_usage': list(data_store.ram_data),
        'disk_usage': list(data_store.disk_data),
        'gpu_usage': list(data_store.gpu_data),
        'temperature': list(data_store.temp_data),
        'network_sent': list(data_store.network_sent),
        'network_recv': list(data_store.network_recv)
    })
    return dcc.send_data_frame(df.to_csv, "system_metrics.csv")

if __name__ == '__main__':
    app.run(debug=True)