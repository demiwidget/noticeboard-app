import sys
import requests
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QTextEdit, 
                             QPushButton, QComboBox, QListWidget, QListWidgetItem,
                             QMessageBox, QTabWidget, QFrame)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QIcon
import qtawesome as qta

class ModernButton(QPushButton):
    def __init__(self, text, color="#3498db", icon=None):
        super().__init__(text)
        if icon:
            try:
                self.setIcon(qta.icon(icon, color='white'))
            except Exception:
                # Keep the app usable if a qtawesome icon name changes.
                pass
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {QColor(color).lighter(110).name()};
            }}
            QPushButton:pressed {{
                background-color: {QColor(color).darker(110).name()};
            }}
        """)

class NoticeBoardAdmin(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Noticeboard Manager")
        self.setMinimumSize(900, 700)
        self.server_url = "http://localhost:5000/api" # Default to localhost
        
        self.init_ui()
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            QLabel {
                color: #2f3640;
                font-size: 14px;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 2px solid #dcdde1;
                border-radius: 6px;
                padding: 8px;
                background-color: white;
                color: #1f2933;
                selection-background-color: #3498db;
                selection-color: white;
                font-size: 14px;
                placeholder-text-color: #7f8c8d;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 2px solid #3498db;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #1f2933;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QListWidget {
                background-color: white;
                color: #1f2933;
                border: 2px solid #dcdde1;
                border-radius: 6px;
                padding: 6px;
            }
            QTabWidget::pane {
                border: 1px solid #dcdde1;
                background: white;
                border-radius: 10px;
            }
            QTabBar::tab {
                background: #f1f2f6;
                color: #52606d;
                padding: 12px 30px;
                margin-right: 5px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background: #e7ecf3;
                color: #2f3640;
            }
            QTabBar::tab:selected {
                background: white;
                color: #3498db;
                border-bottom: 2px solid #3498db;
            }
        """)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title_label = QLabel("Department Noticeboard Admin")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        header.addWidget(title_label)
        header.addStretch()
        
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("Server IP (e.g., 192.168.1.100)")
        self.server_input.setFixedWidth(250)
        self.server_input.setText("localhost")
        header.addWidget(self.server_input)
        
        connect_btn = ModernButton("Connect", "#2ecc71", "fa5s.link")
        connect_btn.clicked.connect(self.update_server_url)
        header.addWidget(connect_btn)

        self.restart_display_btn = ModernButton("Restart Pi Display", "#e67e22", "fa5s.redo-alt")
        self.restart_display_btn.clicked.connect(self.restart_pi_display)
        header.addWidget(self.restart_display_btn)
        
        layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Notice Tab
        self.notice_tab = QWidget()
        self.setup_notice_tab()
        self.tabs.addTab(self.notice_tab, "Manage Notices")

        # Task Tab
        self.task_tab = QWidget()
        self.setup_task_tab()
        self.tabs.addTab(self.task_tab, "Assign Tasks")

        # Refresh button at bottom
        refresh_btn = ModernButton("Refresh All Data", "#9b59b6", "fa5s.sync")
        refresh_btn.clicked.connect(self.refresh_data)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def setup_notice_tab(self):
        layout = QHBoxLayout(self.notice_tab)
        
        # Left side: Form
        form_container = QFrame()
        form_container.setFixedWidth(350)
        form_layout = QVBoxLayout(form_container)
        
        form_layout.addWidget(QLabel("<b>Add New Notice</b>"))
        
        self.notice_title = QLineEdit()
        self.notice_title.setPlaceholderText("Notice Title")
        form_layout.addWidget(self.notice_title)
        
        self.notice_content = QTextEdit()
        self.notice_content.setPlaceholderText("Notice Content...")
        form_layout.addWidget(self.notice_content)
        
        self.notice_priority = QComboBox()
        self.notice_priority.addItems(["Low", "Medium", "High"])
        self.notice_priority.setCurrentText("Medium")
        form_layout.addWidget(QLabel("Priority:"))
        form_layout.addWidget(self.notice_priority)
        
        add_btn = ModernButton("Post Notice", "#3498db", "fa5s.paper-plane")
        add_btn.clicked.connect(self.add_notice)
        form_layout.addWidget(add_btn)
        form_layout.addStretch()
        
        layout.addWidget(form_container)
        
        # Right side: List
        list_container = QVBoxLayout()
        list_container.addWidget(QLabel("<b>Current Notices</b>"))
        self.notice_list = QListWidget()
        self.notice_list.setSpacing(5)
        list_container.addWidget(self.notice_list)
        
        del_btn = ModernButton("Remove Selected", "#e74c3c", "fa5s.trash-alt")
        del_btn.clicked.connect(self.delete_notice)
        list_container.addWidget(del_btn)
        
        layout.addLayout(list_container)

    def setup_task_tab(self):
        layout = QHBoxLayout(self.task_tab)
        
        # Left side: Form
        form_container = QFrame()
        form_container.setFixedWidth(350)
        form_layout = QVBoxLayout(form_container)
        
        form_layout.addWidget(QLabel("<b>Assign New Task</b>"))
        
        self.task_title = QLineEdit()
        self.task_title.setPlaceholderText("Task Title")
        form_layout.addWidget(self.task_title)
        
        self.task_assignee = QLineEdit()
        self.task_assignee.setPlaceholderText("Assign to (Person Name)")
        form_layout.addWidget(self.task_assignee)
        
        self.task_time = QLineEdit()
        self.task_time.setPlaceholderText("Due Time (e.g., 2:00 PM)")
        form_layout.addWidget(self.task_time)
        
        self.task_priority = QComboBox()
        self.task_priority.addItems(["Low", "Medium", "High"])
        self.task_priority.setCurrentText("Medium")
        form_layout.addWidget(QLabel("Priority:"))
        form_layout.addWidget(self.task_priority)
        
        add_btn = ModernButton("Assign Task", "#f39c12", "fa5s.tasks")
        add_btn.clicked.connect(self.add_task)
        form_layout.addWidget(add_btn)
        form_layout.addStretch()
        
        layout.addWidget(form_container)
        
        # Right side: List
        list_container = QVBoxLayout()
        list_container.addWidget(QLabel("<b>Current Tasks</b>"))
        self.task_list = QListWidget()
        self.task_list.setSpacing(5)
        list_container.addWidget(self.task_list)
        
        del_btn = ModernButton("Remove Selected", "#e74c3c", "fa5s.trash-alt")
        del_btn.clicked.connect(self.delete_task)
        list_container.addWidget(del_btn)
        
        layout.addLayout(list_container)

    def update_server_url(self):
        self.server_url = self.build_server_url()
        self.refresh_data()

    def build_server_url(self):
        ip = self.server_input.text().strip()
        if not ip:
            ip = "localhost"
        return f"http://{ip}:5000/api"

    def response_message(self, response, fallback):
        try:
            payload = response.json()
        except ValueError:
            return fallback

        if isinstance(payload, dict):
            return payload.get("message") or payload.get("error") or fallback

        return fallback

    def restart_pi_display(self):
        self.server_url = self.build_server_url()
        reply = QMessageBox.question(
            self,
            "Restart Pi Display",
            "Restart the Raspberry Pi display app now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.restart_display_btn.setEnabled(False)
        try:
            response = requests.post(f"{self.server_url}/admin/restart-display", timeout=5)
            if response.status_code == 202:
                message = self.response_message(response, "Pi display restart requested.")
                QMessageBox.information(self, "Restart Requested", message)
            else:
                message = self.response_message(
                    response,
                    f"Could not restart the Pi display (HTTP {response.status_code}).",
                )
                QMessageBox.critical(self, "Restart Failed", message)
        except requests.RequestException as e:
            QMessageBox.critical(self, "Restart Failed", f"Could not reach the Pi backend: {e}")
        finally:
            self.restart_display_btn.setEnabled(True)

    def refresh_data(self):
        try:
            # Refresh Notices
            resp = requests.get(f"{self.server_url}/notices", timeout=3)
            if resp.status_code == 200:
                self.notice_list.clear()
                for n in resp.json():
                    item = QListWidgetItem(f"[{n['priority']}] {n['title']}")
                    if n['priority'] == 'High': item.setForeground(QColor("#e74c3c"))
                    elif n['priority'] == 'Medium': item.setForeground(QColor("#f39c12"))
                    else: item.setForeground(QColor("#3498db"))
                    item.setData(Qt.ItemDataRole.UserRole, n['id'])
                    self.notice_list.addItem(item)
            
            # Refresh Tasks
            resp = requests.get(f"{self.server_url}/tasks", timeout=3)
            if resp.status_code == 200:
                self.task_list.clear()
                for t in resp.json():
                    item = QListWidgetItem(f"[{t['priority']}] {t['title']} -> {t['assignee']} ({t['due_time']})")
                    item.setData(Qt.ItemDataRole.UserRole, t['id'])
                    self.task_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, "Connection Error", f"Could not connect to server: {e}")

    def add_notice(self):
        data = {
            "title": self.notice_title.text(),
            "content": self.notice_content.toPlainText(),
            "priority": self.notice_priority.currentText()
        }
        if not data['title'] or not data['content']:
            return QMessageBox.warning(self, "Input Error", "Title and Content are required")
        
        try:
            resp = requests.post(f"{self.server_url}/notices", json=data)
            if resp.status_code == 201:
                self.notice_title.clear()
                self.notice_content.clear()
                self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_notice(self):
        item = self.notice_list.currentItem()
        if not item: return
        notice_id = item.data(Qt.ItemDataRole.UserRole)
        try:
            requests.delete(f"{self.server_url}/notices/{notice_id}")
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def add_task(self):
        data = {
            "title": self.task_title.text(),
            "assignee": self.task_assignee.text(),
            "due_time": self.task_time.text(),
            "priority": self.task_priority.currentText()
        }
        if not data['title'] or not data['assignee']:
            return QMessageBox.warning(self, "Input Error", "Title and Assignee are required")
        
        try:
            resp = requests.post(f"{self.server_url}/tasks", json=data)
            if resp.status_code == 201:
                self.task_title.clear()
                self.task_assignee.clear()
                self.task_time.clear()
                self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_task(self):
        item = self.task_list.currentItem()
        if not item: return
        task_id = item.data(Qt.ItemDataRole.UserRole)
        try:
            requests.delete(f"{self.server_url}/tasks/{task_id}")
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NoticeBoardAdmin()
    window.show()
    sys.exit(app.exec())
