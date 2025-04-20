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
from dash.dependencies import Input, Output
from sklearn.ensemble import IsolationForest
import wmi
import pyttsx3
import tkinter as tk
from tkinter import messagebox


# ===== Step 1: Accurate Data Collection =====
cpu_load_history = deque(maxlen=30)

def get_cpu_temperature():
    try:
        w = wmi.WMI(namespace="root\\WMI")
        temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
        temperature = (temperature_info.CurrentTemperature / 10) - 273.15  # Convert to Celsius
        return round(temperature, 2)
    except:
        return None  # Return None if unable to fetch temperature

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
        "temperature": get_cpu_temperature() or 40,  # Fixed temperature retrieval
    }

def update_cpu_history():
    cpu_load_history.append(psutil.cpu_percent(interval=1))

def get_cpu_trend():
    return sum(cpu_load_history) / len(cpu_load_history) if cpu_load_history else 0

# ===== Step 2: Intelligent Anomaly Detection =====
def train_anomaly_model():
    df_normal = pd.read_csv("system_data_normal.csv")
    df_high_load = pd.read_csv("system_data_high_load.csv")
    df_malicious = pd.read_csv("system_data_malicious.csv")
    df = pd.concat([df_normal, df_high_load, df_malicious], ignore_index=True).drop(columns=["state"], errors='ignore')
    model = IsolationForest(contamination=0.05, random_state=42).fit(df)
    joblib.dump(model, "anomaly_model.pkl")

engine = pyttsx3.init()

def speak_alert(message):
    """Convert text to speech"""
    engine.say(message)
    engine.runAndWait()



def prompt_to_kill_high_memory_process(threshold=500):
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    for proc in psutil.process_iter(['pid', 'memory_info', 'name']):
        try:
            mem_usage_mb = proc.info['memory_info'].rss / (1024 * 1024)
            if mem_usage_mb > threshold:
                # Create a new window instead of a simple messagebox
                def kill_and_exit():
                    os.kill(proc.info['pid'], 9)
                    tk.messagebox.showinfo("Terminated", f"{proc.info['name']} has been killed.")
                    root.destroy()

                def ignore_and_exit():
                    root.destroy()

                root.deiconify()
                root.title("High Memory Usage Alert")
                tk.Label(root, text=f"{proc.info['name']} is using {mem_usage_mb:.2f} MB RAM").pack(padx=20, pady=10)
                tk.Button(root, text="Terminate Process", command=kill_and_exit).pack(side=tk.LEFT, padx=10, pady=10)
                tk.Button(root, text="Ignore", command=ignore_and_exit).pack(side=tk.RIGHT, padx=10, pady=10)
                root.mainloop()
                break  # Only prompt for the first found process over threshold
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def detect_anomalies():
    model = joblib.load("anomaly_model.pkl")
    predictor = anomaly.HalfSpaceTrees()

    while True:
        metrics = get_system_metrics()
        df = pd.DataFrame([metrics])
        prediction = model.predict(df)

        if prediction[0] == -1:
            alert_message = f"Anomaly Detected! CPU: {metrics['cpu_usage']}%, RAM: {metrics['ram_usage']}%"
            predictor.learn_one(metrics)
            score = predictor.score_one(metrics)
            if score > 0.8:
                alert_message += "\nSystem overload predicted!"
            if metrics['cpu_usage'] > 90:
                alert_message += "\nSuggestion: Close unused applications."
            if metrics['ram_usage'] > 80:
                # Stop everything and show prompt
                prompt_to_kill_high_memory_process(threshold=400)

            notification.notify(title="PC Doctor Alert!", message=alert_message, timeout=3)

        time.sleep(5)


# ===== Step 3: Automated Fixes =====
def kill_heavy_processes(threshold=90):
    for proc in psutil.process_iter(['pid', 'cpu_percent', 'name']):
        if proc.info['cpu_percent'] > threshold:
            os.kill(proc.info['pid'], 9)

def check_battery():
    battery = psutil.sensors_battery()
    if battery and battery.percent < 20:
        os.system("taskkill /F /IM OneDrive.exe")

def switch_power_mode(mode):
    os.system(f"powercfg /S SCHEME_{mode.upper()}")

# ===== Step 4: Predictive Failure Detection =====
def predict_cpu_load():
    if len(cpu_load_history) > 10:
        model = ExponentialSmoothing(list(cpu_load_history), trend="add", seasonal=None)
        fit = model.fit()
        return fit.forecast(steps=5)[-1]
    return np.mean(cpu_load_history)

# ===== Step 5: Web Dashboard =====
app = Dash(__name__)

def get_system_data():
    return get_system_metrics()

app.layout = html.Div([
    dcc.Interval(id="update", interval=2000, n_intervals=0),
    html.Div(id="live-update-text")
])

@app.callback(Output("live-update-text", "children"), [Input("update", "n_intervals")])
def update_metrics(n):
    data = get_system_data()
    return f"CPU: {data['cpu_usage']}%, RAM: {data['ram_usage']}%, Disk: {data['disk_usage']}%"

if __name__ == '__main__':
    # Run anomaly detection in a separate thread
    anomaly_thread = threading.Thread(target=detect_anomalies, daemon=True)
    anomaly_thread.start()

    # Start Dash server
    app.run(debug=True)

