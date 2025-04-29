import tkinter as tk
from tkinter import ttk, scrolledtext
import customtkinter as ctk
from PIL import Image, ImageTk
import requests
import socketio
import datetime
import psutil
from plyer import notification
import pyttsx3
import json
import threading

class SystemMonitorWidget:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("PC DOCTOR")
        self.root.geometry("1000x700")
        
        # Initialize components
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        
        # Configure style
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Initialize socket connection
        self.sio = socketio.Client()
        self.setup_socket_connection()
        
        # Initialize notifications list
        self.notifications = []
        
        self.setup_gui()

    def setup_socket_connection(self):
        try:
            self.sio.connect('http://localhost:8050')
            
            @self.sio.on('new_notification')
            def handle_notification(data):
                if isinstance(data, dict):
                    if 'messages' in data:  # Handle multiple messages
                        for message in data['messages']:
                            self.handle_notification(message, data.get('type', 'info'))
                    else:  # Handle single message
                        self.handle_notification(data.get('message', str(data)), data.get('type', 'info'))
                else:
                    self.handle_notification(str(data), 'info')
                    
        except Exception as e:
            print(f"Failed to connect to server: {e}")

    def handle_notification(self, message, type="info"):
        # Add to notifications list
        self.add_notification(message)
        
        # Show system tray notification for important alerts
        if type in ['alert', 'warning']:
            notification.notify(
                title='PC DOCTOR Alert',
                message=message,
                timeout=10
            )
            
            # Text-to-speech for critical alerts
            if "High" in message or "Critical" in message:
                threading.Thread(target=self.speak_alert, args=(message,), daemon=True).start()
            
            # Show popup for critical alerts
            if "Critical" in message or "Anomaly" in message:
                self.show_alert_popup("System Alert", message)

    def speak_alert(self, message):
        try:
            self.engine.say(message)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Text-to-speech error: {e}")

    def show_alert_popup(self, title, message):
        def show():
            dialog = tk.Toplevel(self.root)
            dialog.title(title)
            dialog.geometry("400x200")
            
            # Style
            dialog.configure(bg='#f0f0f0')
            
            # Message
            label = tk.Label(
                dialog,
                text=message,
                wraplength=350,
                bg='#f0f0f0',
                font=("Helvetica", 10)
            )
            label.pack(pady=20, padx=20)
            
            # OK button
            tk.Button(
                dialog,
                text="OK",
                command=dialog.destroy,
                bg='#4CAF50',
                fg='white'
            ).pack(pady=10)
            
            # Center the window
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f'{width}x{height}+{x}+{y}')
            
        self.root.after(0, show)

    def setup_gui(self):
        # Create header
        self.create_header()
        
        # Create notebook for pages
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create pages
        self.analytics_page = ctk.CTkFrame(self.notebook)
        self.chat_page = ctk.CTkFrame(self.notebook)
        self.notifications_page = ctk.CTkFrame(self.notebook)
        
        # Add pages to notebook
        self.notebook.add(self.analytics_page, text='System Analytics')
        self.notebook.add(self.chat_page, text='AI Assistant')
        self.notebook.add(self.notifications_page, text='Notifications')
        
        # Setup each page
        self.setup_analytics_page()
        self.setup_chat_page()
        self.setup_notifications_page()

    def create_header(self):
        header_frame = ctk.CTkFrame(self.root)
        header_frame.pack(fill="x", padx=10, pady=5)
        
        title = ctk.CTkLabel(
            header_frame, 
            text="PC DOCTOR", 
            font=("Helvetica", 24, "bold")
        )
        title.pack(pady=10)

        self.connection_status = ctk.CTkLabel(
            header_frame,
            text="⚫ Offline",
            font=("Helvetica", 12)
        )
        self.connection_status.pack(pady=5)

    def setup_analytics_page(self):
        # Title
        title_label = ctk.CTkLabel(
            self.analytics_page,
            text="System Performance Metrics",
            font=("Helvetica", 20, "bold")
        )
        title_label.pack(pady=10)

        # Metrics Frame
        self.metrics_frame = ctk.CTkFrame(self.analytics_page)
        self.metrics_frame.pack(fill="x", padx=20, pady=10)
        
        # Create metrics displays
        self.metric_labels = {}
        metrics = [
            ("CPU Usage:", "cpu_usage"),
            ("RAM Usage:", "ram_usage"),
            ("Disk Usage:", "disk_usage"),
            ("Temperature:", "temperature")
        ]
        
        for text, key in metrics:
            frame = ctk.CTkFrame(self.metrics_frame)
            frame.pack(fill="x", padx=5, pady=5)
            
            label = ctk.CTkLabel(frame, text=text, font=("Helvetica", 14))
            label.pack(side="left", padx=10)
            
            value = ctk.CTkLabel(frame, text="0%", font=("Helvetica", 14, "bold"))
            value.pack(side="right", padx=10)
            
            progress = ctk.CTkProgressBar(frame)
            progress.pack(fill="x", padx=10, pady=5)
            progress.set(0)
            
            self.metric_labels[key] = {"label": label, "value": value, "progress": progress}
        
        # Process List Frame
        self.setup_process_list()
        
        # Start metrics update
        self.update_metrics()

    def setup_process_list(self):
        process_frame = ctk.CTkFrame(self.analytics_page)
        process_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        title = ctk.CTkLabel(
            process_frame,
            text="High Memory Processes",
            font=("Helvetica", 16, "bold")
        )
        title.pack(pady=5)
        
        self.process_text = scrolledtext.ScrolledText(
            process_frame,
            wrap=tk.WORD,
            height=10,
            font=("Helvetica", 10)
        )
        self.process_text.pack(fill="both", expand=True, padx=5, pady=5)

    def setup_chat_page(self):
        chat_frame = ctk.CTkFrame(self.chat_page)
        chat_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        title = ctk.CTkLabel(
            chat_frame, 
            text="AI Assistant", 
            font=("Helvetica", 20, "bold")
        )
        title.pack(pady=10)
        
        self.chat_history = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            height=20,
            font=("Helvetica", 10)
        )
        self.chat_history.pack(fill="both", expand=True, padx=5, pady=5)
        
        input_frame = ctk.CTkFrame(chat_frame)
        input_frame.pack(fill="x", padx=5, pady=5)
        
        self.question_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Ask a question...",
            height=40
        )
        self.question_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        ask_button = ctk.CTkButton(
            input_frame,
            text="Ask",
            command=self.ask_question,
            height=40
        )
        ask_button.pack(side="right", padx=5)

    def setup_notifications_page(self):
        notifications_frame = ctk.CTkFrame(self.notifications_page)
        notifications_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        title = ctk.CTkLabel(
            notifications_frame, 
            text="System Notifications", 
            font=("Helvetica", 20, "bold")
        )
        title.pack(pady=10)
        
        self.notifications_text = scrolledtext.ScrolledText(
            notifications_frame,
            wrap=tk.WORD,
            height=25,
            font=("Helvetica", 10)
        )
        self.notifications_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add initial notification
        self.add_notification("System monitoring started")

    def update_metrics(self):
        try:
            response = requests.get('http://localhost:8050/metrics')
            if response.status_code == 200:
                metrics = response.json()
                
                # Update metrics display
                self.update_metric_value('cpu_usage', metrics['cpu_usage'])
                self.update_metric_value('ram_usage', metrics['ram_usage'])
                self.update_metric_value('disk_usage', metrics['disk_usage'])
                self.update_metric_value('temperature', metrics['temperature'])
                
                # Update connection status
                self.connection_status.configure(text="🟢 Online")
                
                # Update process list
                self.update_process_list()
            else:
                self.connection_status.configure(text="🔴 Error")
                
        except Exception as e:
            print(f"Error updating metrics: {e}")
            self.connection_status.configure(text="🔴 Offline")
        
        self.root.after(2000, self.update_metrics)

    def update_metric_value(self, metric_key, value):
        if metric_key in self.metric_labels:
            self.metric_labels[metric_key]["value"].configure(text=f"{value}%")
            self.metric_labels[metric_key]["progress"].set(value/100)
            
            # Color coding based on value
            if value > 90:
                self.metric_labels[metric_key]["progress"].configure(progress_color="red")
            elif value > 70:
                self.metric_labels[metric_key]["progress"].configure(progress_color="orange")
            else:
                self.metric_labels[metric_key]["progress"].configure(progress_color="#1f538d")

    def update_process_list(self):
        try:
            response = requests.get('http://localhost:8050/high-memory-processes')
            if response.status_code == 200:
                processes = response.json()
                
                self.process_text.delete(1.0, tk.END)
                if processes:
                    for proc in processes:
                        self.process_text.insert(tk.END, 
                            f"Process: {proc['name']}\n"
                            f"Memory Usage: {proc['memory_mb']:.1f} MB\n"
                            f"PID: {proc['pid']}\n"
                            f"{'-'*50}\n"
                        )
                else:
                    self.process_text.insert(tk.END, "No high memory processes detected")
        except Exception as e:
            print(f"Error updating process list: {e}")

    def add_notification(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        if hasattr(self, 'notifications_text'):
            self.notifications_text.insert(
                tk.END, 
                f"[{timestamp}] {message}\n"
            )
            self.notifications_text.see(tk.END)
            
            # Add to chat history if it's a warning or error
            if any(keyword in message for keyword in ["Warning", "Error", "Alert", "Critical"]):
                if hasattr(self, 'chat_history'):
                    self.chat_history.insert(tk.END, f"System Alert: {message}\n")
                    self.chat_history.see(tk.END)

    def ask_question(self):
        question = self.question_entry.get()
        if question:
            self.chat_history.insert(tk.END, f"\nYou: {question}\n")
            
            # Get system context
            try:
                response = requests.get('http://localhost:8050/metrics')
                if response.status_code == 200:
                    metrics = response.json()
                    context = (f"Current system status - "
                             f"CPU: {metrics['cpu_usage']}%, "
                             f"RAM: {metrics['ram_usage']}%, "
                             f"Disk: {metrics['disk_usage']}%")
                    
                    # Add response with system context
                    self.chat_history.insert(tk.END, f"System Context: {context}\n")
                    self.chat_history.insert(tk.END, "AI: Processing your question with current system status...\n")
            except Exception as e:
                self.chat_history.insert(tk.END, "AI: Unable to get system context. Processing your question...\n")
            
            self.chat_history.see(tk.END)
            self.question_entry.delete(0, tk.END)

    def kill_process(self, pid):
        try:
            response = requests.get(f'http://localhost:8050/kill-process/{pid}')
            if response.status_code == 200:
                self.add_notification(f"Successfully terminated process (PID: {pid})")
            else:
                self.add_notification(f"Failed to terminate process (PID: {pid})")
        except Exception as e:
            self.add_notification(f"Error terminating process: {e}")

    def run(self):
        try:
            self.root.mainloop()
        finally:
            if hasattr(self, 'sio'):
                self.sio.disconnect()

if __name__ == "__main__":
    try:
        app = SystemMonitorWidget()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        input("Press Enter to exit...")