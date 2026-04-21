import sys
import os
import requests

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                 QHBoxLayout, QLabel, QFrame, QScrollArea, QGridLayout)
    from PyQt6.QtCore import Qt, QTimer, QDateTime
    from PyQt6.QtGui import QFont, QColor, QLinearGradient, QPalette, QBrush
    QT6 = True
except ImportError:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                 QHBoxLayout, QLabel, QFrame, QScrollArea, QGridLayout)
    from PyQt5.QtCore import Qt, QTimer, QDateTime
    from PyQt5.QtGui import QFont, QColor, QLinearGradient, QPalette, QBrush
    QT6 = False

if QT6:
    ALIGN_TOP = Qt.AlignmentFlag.AlignTop
    FONT_BOLD = QFont.Weight.Bold
    FONT_DEMIBOLD = QFont.Weight.DemiBold
    PALETTE_WINDOW = QPalette.ColorRole.Window
    STYLED_PANEL = QFrame.Shape.StyledPanel
else:
    ALIGN_TOP = Qt.AlignTop
    FONT_BOLD = QFont.Bold
    FONT_DEMIBOLD = QFont.DemiBold
    PALETTE_WINDOW = QPalette.Window
    STYLED_PANEL = QFrame.StyledPanel

class Card(QFrame):
    def __init__(self, title, content, priority, type="notice", assignee=None, time=None):
        super().__init__()
        self.setFrameShape(STYLED_PANEL)
        
        # Color mapping
        colors = {
            "High": "#e74c3c",
            "Medium": "#f39c12",
            "Low": "#3498db"
        }
        accent = colors.get(priority, "#3498db")
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 15px;
                border-left: 8px solid {accent};
                margin: 5px;
            }}
            QLabel {{
                background: transparent;
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 18, FONT_BOLD))
        title_lbl.setStyleSheet(f"color: {accent};")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)
        
        if type == "notice":
            content_lbl = QLabel(content)
            content_lbl.setFont(QFont("Segoe UI", 14))
            content_lbl.setStyleSheet("color: #2c3e50;")
            content_lbl.setWordWrap(True)
            layout.addWidget(content_lbl)
        else:
            info_layout = QHBoxLayout()
            person_lbl = QLabel(f"👤 {assignee}")
            person_lbl.setFont(QFont("Segoe UI", 14, FONT_DEMIBOLD))
            person_lbl.setStyleSheet("color: #34495e;")
            
            time_lbl = QLabel(f"⏰ {time}")
            time_lbl.setFont(QFont("Segoe UI", 14))
            time_lbl.setStyleSheet("color: #7f8c8d;")
            
            info_layout.addWidget(person_lbl)
            info_layout.addStretch()
            info_layout.addWidget(time_lbl)
            layout.addLayout(info_layout)

class PiDisplay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Department Noticeboard")
        self.showFullScreen()
        self.server_url = os.environ.get("NOTICEBOARD_API_URL", "http://127.0.0.1:5000/api")
        
        self.init_ui()
        
        # Timers
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(10000) # Refresh every 10 seconds
        
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        
        self.refresh_data()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        # Background Gradient
        palette = self.palette()
        gradient = QLinearGradient(0, 0, 0, 400)
        gradient.setColorAt(0.0, QColor("#2c3e50"))
        gradient.setColorAt(1.0, QColor("#000000"))
        palette.setBrush(PALETTE_WINDOW, QBrush(gradient))
        self.setPalette(palette)
        
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        self.title_label = QLabel("DEPARTMENT NOTICEBOARD")
        self.title_label.setFont(QFont("Segoe UI", 36, FONT_BOLD))
        self.title_label.setStyleSheet("color: white; letter-spacing: 2px;")
        header.addWidget(self.title_label)
        
        header.addStretch()
        
        self.clock_label = QLabel()
        self.clock_label.setFont(QFont("Segoe UI", 28))
        self.clock_label.setStyleSheet("color: #ecf0f1;")
        header.addWidget(self.clock_label)
        
        self.main_layout.addLayout(header)
        
        # Content Area
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)
        
        # Notices Column
        notices_col = QVBoxLayout()
        notices_title = QLabel("📢 NOTICES")
        notices_title.setFont(QFont("Segoe UI", 22, FONT_BOLD))
        notices_title.setStyleSheet("color: #3498db;")
        notices_col.addWidget(notices_title)
        
        self.notices_area = QScrollArea()
        self.notices_area.setWidgetResizable(True)
        self.notices_area.setStyleSheet("background: transparent; border: none;")
        self.notices_widget = QWidget()
        self.notices_widget.setStyleSheet("background: transparent;")
        self.notices_layout = QVBoxLayout(self.notices_widget)
        self.notices_layout.setAlignment(ALIGN_TOP)
        self.notices_area.setWidget(self.notices_widget)
        notices_col.addWidget(self.notices_area)
        
        # Tasks Column
        tasks_col = QVBoxLayout()
        tasks_title = QLabel("✅ TASKS")
        tasks_title.setFont(QFont("Segoe UI", 22, FONT_BOLD))
        tasks_title.setStyleSheet("color: #2ecc71;")
        tasks_col.addWidget(tasks_title)
        
        self.tasks_area = QScrollArea()
        self.tasks_area.setWidgetResizable(True)
        self.tasks_area.setStyleSheet("background: transparent; border: none;")
        self.tasks_widget = QWidget()
        self.tasks_widget.setStyleSheet("background: transparent;")
        self.tasks_layout = QVBoxLayout(self.tasks_widget)
        self.tasks_layout.setAlignment(ALIGN_TOP)
        self.tasks_area.setWidget(self.tasks_widget)
        tasks_col.addWidget(self.tasks_area)
        
        content_layout.addLayout(notices_col, 1)
        content_layout.addLayout(tasks_col, 1)
        
        self.main_layout.addLayout(content_layout)

    def update_clock(self):
        self.clock_label.setText(QDateTime.currentDateTime().toString("h:mm:ss AP | ddd, MMM d"))

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def refresh_data(self):
        try:
            # Fetch Notices
            n_resp = requests.get(f"{self.server_url}/notices", timeout=2)
            if n_resp.status_code == 200:
                self.clear_layout(self.notices_layout)
                for n in n_resp.json():
                    card = Card(n['title'], n['content'], n['priority'], type="notice")
                    self.notices_layout.addWidget(card)
            
            # Fetch Tasks
            t_resp = requests.get(f"{self.server_url}/tasks", timeout=2)
            if t_resp.status_code == 200:
                self.clear_layout(self.tasks_layout)
                for t in t_resp.json():
                    card = Card(t['title'], "", t['priority'], type="task", 
                               assignee=t['assignee'], time=t['due_time'])
                    self.tasks_layout.addWidget(card)
        except Exception as e:
            print(f"Refresh error: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PiDisplay()
    window.show()
    if hasattr(app, "exec"):
        sys.exit(app.exec())
    sys.exit(app.exec_())
