import psutil
import GPUtil
import os
import time
import joblib
import numpy as np
import pandas as pd
import threading
from collections import deque
from plyer import notification
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from river import anomaly
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
from sklearn.ensemble import IsolationForest
import wmi
import pyttsx3
import tkinter as tk
from tkinter import messagebox
import shutil
import subprocess
from datetime import datetime, timedelta

# ===== Step 1: Accurate Data Collection =====
cpu_load_history = deque(maxlen=30)

def get_cpu_temperature():
    try:
        w = wmi.WMI(namespace="root\\WMI")
        temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
        temperature = (temperature_info.CurrentTemperature / 10) - 273.15
        return round(temperature, 2)
    except:
        return None

def get_system_metrics():
    gpus = GPUtil.getGPUs()
    return {
        "cpu_usage": psutil.cpu_percent(interval=1),
        "ram_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "running_processes": len(psutil.pids()),
        "network_sent": psutil.net_io_counters().bytes_sent,
        "network_recv": psutil.net_io_counters().bytes_recv,
        "gpu_usage": gpus[0].load * 100 if gpus else 0,
        "temperature": get_cpu_temperature() or 40,
    }

def safe_clean_system_cache():
    """A safer version of cache cleaning that doesn't kill browser processes"""
    try:
        files_removed = 0
        space_freed = 0
        
        now = datetime.now()
        max_age = timedelta(hours=24)

        temp_folders = [
            os.environ.get('TEMP'),
            os.environ.get('TMP'),
            os.path.join(os.environ.get('LOCALAPPDATA'), 'Temp'),
            os.path.join(os.environ.get('SYSTEMROOT'), 'Temp'),
            os.path.join(os.environ.get('LOCALAPPDATA'), 'Microsoft', 'Windows', 'INetCache'),
        ]

        for folder in temp_folders:
            if folder and os.path.exists(folder):
                print(f"Cleaning folder: {folder}")
                for root, dirs, files in os.walk(folder, topdown=False):
                    for name in files:
                        try:
                            file_path = os.path.join(root, name)
                            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            if (now - file_time) > max_age:
                                if os.path.exists(file_path):
                                    size = os.path.getsize(file_path)
                                    try:
                                        os.unlink(file_path)
                                        files_removed += 1
                                        space_freed += size
                                        print(f"Removed: {file_path}")
                                    except PermissionError:
                                        print(f"Couldn't remove (in use): {file_path}")
                        except (PermissionError, FileNotFoundError, OSError) as e:
                            print(f"Error processing {name}: {str(e)}")
                            continue

        # Browser cache cleaning
        browser_paths = {
            'Chrome': os.path.join(os.environ.get('LOCALAPPDATA'), 
                                 'Google', 'Chrome', 'User Data', 'Default', 'Cache'),
            'Edge': os.path.join(os.environ.get('LOCALAPPDATA'), 
                               'Microsoft', 'Edge', 'User Data', 'Default', 'Cache'),
            'Firefox': os.path.join(os.environ.get('LOCALAPPDATA'), 
                                  'Mozilla', 'Firefox', 'Profiles')
        }
        
        for browser, path in browser_paths.items():
            if os.path.exists(path):
                try:
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                                if (now - file_time) > max_age:
                                    if os.path.exists(file_path):
                                        size = os.path.getsize(file_path)
                                        os.unlink(file_path)
                                        files_removed += 1
                                        space_freed += size
                            except (PermissionError, FileNotFoundError):
                                continue
                except Exception as e:
                    print(f"Error cleaning {browser} cache: {str(e)}")

        # System cache cleaning
        try:
            # DNS Cache
            subprocess.run('ipconfig /flushdns', shell=True, capture_output=True)
            
            # Thumbnail Cache
            thumbnail_cache = os.path.join(os.environ.get('LOCALAPPDATA'), 
                                         'Microsoft', 'Windows', 'Explorer')
            for file in os.listdir(thumbnail_cache):
                if file.startswith('thumbcache'):
                    try:
                        file_path = os.path.join(thumbnail_cache, file)
                        size = os.path.getsize(file_path)
                        os.unlink(file_path)
                        files_removed += 1
                        space_freed += size
                    except (PermissionError, FileNotFoundError):
                        continue

            # Windows Store Cache
            subprocess.run('wsreset.exe', shell=True, capture_output=True)

        except Exception as e:
            print(f"Error in system cache cleaning: {str(e)}")

        return {
            'files_removed': files_removed,
            'space_freed_mb': round(space_freed / (1024 * 1024), 2),
            'status': 'completed'
        }

    except Exception as e:
        return {
            'error': str(e),
            'files_removed': files_removed,
            'space_freed_mb': round(space_freed / (1024 * 1024), 2),
            'status': 'error'
        }

def update_cpu_history():
    cpu_load_history.append(psutil.cpu_percent(interval=1))

def get_cpu_trend():
    return sum(cpu_load_history) / len(cpu_load_history) if cpu_load_history else 0

engine = pyttsx3.init()

def speak_alert(message):
    engine.say(message)
    engine.runAndWait()

def detect_anomalies():
    try:
        model = joblib.load("anomaly_model.pkl")
        predictor = anomaly.HalfSpaceTrees()

        while True:
            metrics = get_system_metrics()
            df = pd.DataFrame([metrics])
            prediction = model.predict(df)

            if prediction[0] == -1:
                alert_message = f"Anomaly Detected! CPU: {metrics['cpu_usage']}%, RAM: {metrics['ram_usage']}%"
                if metrics['cpu_usage'] > 90:
                    alert_message += "\nHigh CPU Usage detected!"
                if metrics['ram_usage'] > 85:
                    alert_message += "\nHigh RAM Usage detected!"
                
                notification.notify(
                    title="System Alert",
                    message=alert_message,
                    timeout=5
                )

            time.sleep(5)
    except Exception as e:
        print(f"Error in anomaly detection: {str(e)}")

# ===== Web Dashboard =====
app = Dash(__name__)

app.layout = html.Div([
    # Header
    html.Div([
        html.H1("System Monitor & Cache Cleaner", 
                style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '20px'})
    ]),

    # Main content
    html.Div([
        # System Metrics Panel
        html.Div([
            html.H3("System Metrics", style={'color': '#34495e'}),
            dcc.Interval(id="update", interval=2000, n_intervals=0),
            html.Div(id="live-update-text", 
                    style={'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '5px'})
        ], style={'marginBottom': '20px'}),

        # Cache Cleaning Panel
        html.Div([
            html.H3("Cache Cleaning", style={'color': '#34495e'}),
            html.Button(
                'Clean System Cache',
                id='clean-cache-button',
                style={
                    'backgroundColor': '#3498db',
                    'color': 'white',
                    'padding': '10px 20px',
                    'border': 'none',
                    'borderRadius': '5px',
                    'cursor': 'pointer',
                    'marginBottom': '15px'
                }
            ),
            html.Div(id='cleaning-progress'),
            html.Div(id='clean-cache-output'),
            html.Div(id='cleaning-details')
        ], style={'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '10px', 
                 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
    ], style={'maxWidth': '800px', 'margin': '0 auto', 'padding': '20px'})
], style={'backgroundColor': '#ecf0f1', 'minHeight': '100vh', 'padding': '20px'})

@app.callback(
    [Output('clean-cache-output', 'children'),
     Output('cleaning-details', 'children'),
     Output('cleaning-progress', 'children')],
    [Input('clean-cache-button', 'n_clicks')]
)
def clean_cache_callback(n_clicks):
    if n_clicks is None:
        return '', '', ''

    results = safe_clean_system_cache()
    
    if results['status'] == 'completed':
        summary = html.Div([
            html.H4("Cache Cleaning Results"),
            html.P(f"Files removed: {results['files_removed']}"),
            html.P(f"Space freed: {results['space_freed_mb']} MB"),
            html.P("Note: Some files may remain if they are in use by Windows"),
            html.P("Tip: Restart your computer to clean additional locked files"),
            html.P(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        ], style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '5px'})
        
        return (
            f"Successfully cleaned {results['files_removed']} files ({results['space_freed_mb']} MB)",
            summary,
            html.Div("Cleaning completed!", 
                     style={'padding': '10px', 'backgroundColor': '#e8f5e9', 'borderRadius': '5px'})
        )
    else:
        error_summary = html.Div([
            html.H4("Error Details"),
            html.P(str(results['error'])),
            html.P(f"Files removed before error: {results['files_removed']}"),
            html.P(f"Space freed before error: {results['space_freed_mb']} MB")
        ], style={'backgroundColor': '#fff3f3', 'padding': '15px', 'borderRadius': '5px'})
        
        return (
            "Error during cleaning",
            error_summary,
            html.Div("Cleaning failed!", 
                     style={'padding': '10px', 'backgroundColor': '#ffebee', 'borderRadius': '5px'})
        )

@app.callback(
    Output("live-update-text", "children"),
    [Input("update", "n_intervals")]
)
def update_metrics(n):
    data = get_system_metrics()
    return html.Div([
        html.Div([
            html.Span("CPU: ", style={'fontWeight': 'bold'}),
            html.Span(f"{data['cpu_usage']}%"),
            html.Div(style={'backgroundColor': '#3498db', 
                          'width': f"{data['cpu_usage']}%", 
                          'height': '5px'})
        ], style={'marginBottom': '10px'}),
        html.Div([
            html.Span("RAM: ", style={'fontWeight': 'bold'}),
            html.Span(f"{data['ram_usage']}%"),
            html.Div(style={'backgroundColor': '#e74c3c', 
                          'width': f"{data['ram_usage']}%", 
                          'height': '5px'})
        ], style={'marginBottom': '10px'}),
        html.Div([
            html.Span("Disk: ", style={'fontWeight': 'bold'}),
            html.Span(f"{data['disk_usage']}%"),
            html.Div(style={'backgroundColor': '#2ecc71', 
                          'width': f"{data['disk_usage']}%", 
                          'height': '5px'})
        ])
    ])

if __name__ == '__main__':
    # Start anomaly detection in a separate thread
    anomaly_thread = threading.Thread(target=detect_anomalies, daemon=True)
    anomaly_thread.start()

    # Run the dashboard
    app.run(debug=True)