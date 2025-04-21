import sys
import os
import subprocess
import psutil
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import Qt, QPoint


class ChatBotInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.full_width = 500
        self.collapsed_width = 50
        self.dragging = False
        self.server_process = None

        self.setWindowTitle("PC Doc Notifications")
        self.setGeometry(100, 100, self.full_width, 800)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: black; border: none; border-radius: 20px;")
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout()
        self.central_widget.setLayout(layout)

        self.browser = QWebEngineView()
        layout.addWidget(self.browser)

        self.channel = QWebChannel()
        self.browser.page().setWebChannel(self.channel)
        self.channel.registerObject("backend", self)
        self.browser.setHtml(self.get_html())

        # Collapse and Expand Buttons
        self.toggle_button = QPushButton("→", self)
        self.toggle_button.setGeometry(self.full_width - 30, 10, 30, 40)
        self.toggle_button.setStyleSheet(self.arrow_style("#444"))
        self.toggle_button.clicked.connect(self.hide_chat)

        self.expand_button = QPushButton("←", self)
        self.expand_button.setStyleSheet(self.arrow_style("#444"))
        self.expand_button.clicked.connect(self.show_chat)
        self.expand_button.hide()

        # Server Start/Stop Button
        self.server_button = QPushButton("▶", self)
        self.server_button.setGeometry(self.width()//2 - 40, self.height()//2 - 40, 80, 80)
        self.server_button.setStyleSheet(self.server_button_style("start"))
        self.server_button.clicked.connect(self.toggle_server)
        self.server_button.raise_()

    def arrow_style(self, bg_color):
        return f"background-color: {bg_color}; color: white; border: none; font-size: 18px; border-radius: 15px; padding: 5px;"

    def server_button_style(self, state):
        return (
            "background-color: #2e7d32;" if state == "start" else "background-color: #c62828;"
        ) + " color: white; border: none; font-size: 40px; border-radius: 40px; padding: 20px;"

    def toggle_server(self):
        if self.server_process is None:
            try:
                project_dir = r"D:\SEM-8\AI Lab\CAT-2 Project\PC-DOCTOR-Backend"
                command = f'start cmd /K "cd /d \"{project_dir}\" && py app.py"'
                self.server_process = subprocess.Popen(
                    command,
                    shell=True
                )
                self.server_button.setText("■")
                self.server_button.setStyleSheet(self.server_button_style("stop"))
                self.server_button.setGeometry(10, 10, 40, 40)
            except Exception as e:
                print(f"Error starting server: {e}")
        else:
            self.terminate_server()



    def terminate_server(self):
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if "app.py" in str(proc.info['cmdline']) and "python" in proc.info['name'].lower():
                    proc.kill()
                    print(f"Flask server killed (PID: {proc.pid})")
                    break
        except Exception as e:
            print(f"Error killing server: {e}")

        self.server_process = None
        self.server_button.setText("▶")
        self.server_button.setStyleSheet(self.server_button_style("start"))
        self.server_button.setGeometry(self.width()//2 - 40, self.height()//2 - 40, 80, 80)

    def closeEvent(self, event):
        self.terminate_server()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False
        event.accept()

    def hide_chat(self):
        screen_width = QApplication.primaryScreen().geometry().width()
        self.setGeometry(screen_width - self.collapsed_width, self.y(), self.collapsed_width, 800)
        self.central_widget.hide()
        self.toggle_button.hide()
        self.expand_button.setParent(self)
        self.expand_button.setGeometry(self.width() - 40, 10, 30, 40)
        self.expand_button.show()

    def show_chat(self):
        screen_width = QApplication.primaryScreen().geometry().width()
        self.setGeometry(screen_width - self.full_width, self.y(), self.full_width, 800)
        self.central_widget.show()
        self.toggle_button.show()
        self.expand_button.hide()

    def get_html(self):
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PC Doc - 3D Model & Notifications</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <style>
        body { background-color: #000; color: white; font-family: Arial; text-align: center; margin: 0; padding: 20px; }
        canvas { display: block; }
        .notification-container {
            max-width: 400px;
            border: 2px solid #444;
            padding: 10px;
            border-radius: 20px;
            background-color: #111;
            height: 300px;
            overflow: hidden;
        }
        .notification-box {
            overflow-y: auto;
            background-color: #222;
            border: 1px solid #444;
            border-radius: 5px;
            padding: 10px;
            height: 100%;
        }
        .notification {
            background-color: #333;
            border: 1px solid #555;
            border-radius: 5px;
            margin: 5px 0;
            padding: 10px;
        }
    </style>
</head>
<body>
    <h2>PC Doc - 3D Astronaut & Notifications</h2>
    <div id="3d-container" style="width: 400px; height: 400px;"></div>
    <div class="notification-container">
        <div class="notification-box" id="notificationBox"></div>
    </div>
    <script>
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x000000);
        const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
        camera.position.set(0, 1, 3);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(400, 400);
        document.getElementById("3d-container").appendChild(renderer.domElement);
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        scene.add(new THREE.AmbientLight(0xffffff, 1));
        new THREE.GLTFLoader().load(
            'file:///D:/SEM-8/AI%20Lab/CAT-2%20Project/Chatbot/Astronaut.glb',
            gltf => { scene.add(gltf.scene); animate(); },
            undefined,
            error => console.error('Error loading model:', error)
        );
        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }
        const notifications = [
            "System update available.",
            "Security scan completed successfully.",
            "New software update installed.",
            "Battery health is good.",
            "Storage space running low.",
            "Connected to a new Wi-Fi network.",
            "Reminder: Run disk cleanup.",
            "New messages received."
        ];
        const notificationBox = document.getElementById("notificationBox");
        notifications.forEach(msg => {
            const div = document.createElement("div");
            div.className = "notification";
            div.textContent = msg;
            notificationBox.appendChild(div);
        });
    </script>
</body>
</html>"""


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatBotInterface()
    window.show()
    sys.exit(app.exec_())
