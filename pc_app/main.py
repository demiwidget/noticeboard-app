import sys

import qtawesome as qta
import requests
from PyQt6.QtCore import QSettings, QSize, QTimer, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ModernButton(QPushButton):
    def __init__(self, text, color="#3498db", icon=None):
        super().__init__(text)
        if icon:
            try:
                self.setIcon(qta.icon(icon, color="white"))
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
            QPushButton:disabled {{
                background-color: #a0aec0;
                color: #edf2f7;
            }}
        """)


class NoticeBoardAdmin(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Demiwidget", "NoticeboardManager")
        self.saved_server_host = self.settings.value("server_host", "localhost", type=str) or "localhost"
        self.server_url = self.build_server_url_from_host(self.saved_server_host)
        self.cached_tasks = []
        self.elapsed_notified_ids = set()
        self.assignee_api_available = False

        self.setWindowTitle("Noticeboard Manager")
        self.setMinimumSize(980, 740)

        self.init_ui()
        self.apply_styles()

        self.task_poll_timer = QTimer(self)
        self.task_poll_timer.timeout.connect(self.poll_tasks)
        self.task_poll_timer.start(1000)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            QLabel {
                color: #2f3640;
                font-size: 14px;
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                border: 2px solid #dcdde1;
                border-radius: 6px;
                padding: 8px;
                background-color: white;
                color: #1f2933;
                selection-background-color: #3498db;
                selection-color: white;
                font-size: 14px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 2px solid #3498db;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #1f2933;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QCheckBox {
                color: #2f3640;
                font-size: 14px;
                font-weight: 600;
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

        header = QHBoxLayout()
        title_label = QLabel("Department Noticeboard Admin")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        header.addWidget(title_label)
        header.addStretch()

        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("Server IP (e.g., 192.168.1.100)")
        self.server_input.setFixedWidth(250)
        self.server_input.setText(self.saved_server_host)
        header.addWidget(self.server_input)

        connect_btn = ModernButton("Connect", "#2ecc71", "fa5s.link")
        connect_btn.clicked.connect(self.update_server_url)
        header.addWidget(connect_btn)

        self.restart_display_btn = ModernButton("Restart Pi Display", "#e67e22", "fa5s.redo-alt")
        self.restart_display_btn.clicked.connect(self.restart_pi_display)
        header.addWidget(self.restart_display_btn)

        layout.addLayout(header)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.notice_tab = QWidget()
        self.setup_notice_tab()
        self.tabs.addTab(self.notice_tab, "Manage Notices")

        self.task_tab = QWidget()
        self.setup_task_tab()
        self.tabs.addTab(self.task_tab, "Assign Tasks")

        refresh_btn = ModernButton("Refresh All Data", "#9b59b6", "fa5s.sync")
        refresh_btn.clicked.connect(self.refresh_data)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def setup_notice_tab(self):
        layout = QHBoxLayout(self.notice_tab)

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

        form_container = QFrame()
        form_container.setFixedWidth(400)
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(10)

        form_layout.addWidget(QLabel("<b>Assign New Task</b>"))

        self.task_title = QLineEdit()
        self.task_title.setPlaceholderText("Task Title")
        form_layout.addWidget(self.task_title)

        form_layout.addWidget(QLabel("Assign To:"))
        self.task_assignee = QComboBox()
        self.task_assignee.setEditable(True)
        self.task_assignee.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.task_assignee.setPlaceholderText("Choose or type a person name")
        form_layout.addWidget(self.task_assignee)

        assignee_buttons = QHBoxLayout()
        self.save_assignee_btn = ModernButton("Save Person", "#27ae60", "fa5s.user-plus")
        self.save_assignee_btn.clicked.connect(self.save_current_assignee)
        assignee_buttons.addWidget(self.save_assignee_btn)

        self.remove_assignee_btn = ModernButton("Remove Person", "#c0392b", "fa5s.user-minus")
        self.remove_assignee_btn.clicked.connect(self.delete_current_assignee)
        assignee_buttons.addWidget(self.remove_assignee_btn)
        form_layout.addLayout(assignee_buttons)

        self.assignee_status_label = QLabel("Saved people will appear in the dropdown after you connect.")
        self.assignee_status_label.setWordWrap(True)
        form_layout.addWidget(self.assignee_status_label)

        self.task_due_note = QLineEdit()
        self.task_due_note.setPlaceholderText("Due note or time (optional)")
        form_layout.addWidget(self.task_due_note)

        self.task_timer_enabled = QCheckBox("Enable countdown timer")
        self.task_timer_enabled.toggled.connect(self.update_timer_inputs_enabled)
        form_layout.addWidget(self.task_timer_enabled)

        timer_row = QHBoxLayout()
        timer_row.addWidget(QLabel("Hours:"))
        self.task_timer_hours = QSpinBox()
        self.task_timer_hours.setRange(0, 72)
        timer_row.addWidget(self.task_timer_hours)

        timer_row.addWidget(QLabel("Minutes:"))
        self.task_timer_minutes = QSpinBox()
        self.task_timer_minutes.setRange(0, 59)
        timer_row.addWidget(self.task_timer_minutes)
        form_layout.addLayout(timer_row)

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

        list_container = QVBoxLayout()
        list_container.addWidget(QLabel("<b>Current Tasks</b>"))

        self.task_alert_label = QLabel("No timer alerts")
        self.task_alert_label.setWordWrap(True)
        self.set_task_alert_banner("No timer alerts", "#edf2f7", "#2f3640")
        list_container.addWidget(self.task_alert_label)

        self.task_list = QListWidget()
        self.task_list.setSpacing(6)
        list_container.addWidget(self.task_list)

        del_btn = ModernButton("Remove Selected", "#e74c3c", "fa5s.trash-alt")
        del_btn.clicked.connect(self.delete_task)
        list_container.addWidget(del_btn)

        layout.addLayout(list_container)

        self.update_timer_inputs_enabled(False)
        self.set_assignee_controls_available(
            False,
            "Saved people list will be available once the Pi backend supports assignees.",
            "#8e44ad",
        )

    def update_server_url(self):
        host = self.current_server_host()
        self.server_url = self.build_server_url_from_host(host)
        self.settings.setValue("server_host", host)
        self.refresh_data()

    def current_server_host(self):
        host = self.server_input.text().strip()
        if not host:
            host = "localhost"
        return host

    def build_server_url(self):
        return self.build_server_url_from_host(self.current_server_host())

    def build_server_url_from_host(self, host):
        return f"http://{host}:5000/api"

    def endpoint_url(self, path):
        return f"{self.server_url}/{path.lstrip('/')}"

    def response_message(self, response, fallback):
        try:
            payload = response.json()
        except ValueError:
            return fallback

        if isinstance(payload, dict):
            return payload.get("message") or payload.get("error") or fallback

        return fallback

    def current_assignee_name(self):
        return self.task_assignee.currentText().strip()

    def update_timer_inputs_enabled(self, enabled):
        self.task_timer_hours.setEnabled(enabled)
        self.task_timer_minutes.setEnabled(enabled)

    def reset_timer_inputs(self):
        self.task_timer_enabled.setChecked(False)
        self.task_timer_hours.setValue(0)
        self.task_timer_minutes.setValue(0)

    def current_countdown_seconds(self):
        total_minutes = (self.task_timer_hours.value() * 60) + self.task_timer_minutes.value()
        if total_minutes <= 0:
            return None
        return total_minutes * 60

    def format_duration(self, total_seconds):
        total_seconds = max(0, int(total_seconds))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def set_task_alert_banner(self, text, background, foreground):
        self.task_alert_label.setText(text)
        self.task_alert_label.setStyleSheet(f"""
            QLabel {{
                background-color: {background};
                color: {foreground};
                border: 1px solid {QColor(background).darker(110).name()};
                border-radius: 8px;
                padding: 10px 12px;
                font-weight: bold;
            }}
        """)

    def set_assignee_controls_available(self, available, message, color):
        self.assignee_api_available = available
        self.save_assignee_btn.setEnabled(available)
        self.remove_assignee_btn.setEnabled(available)
        self.assignee_status_label.setText(message)
        self.assignee_status_label.setStyleSheet(f"color: {color}; font-weight: 600;")

    def populate_assignee_combo(self, assignees, selected_name=None):
        if selected_name is None:
            selected_name = self.current_assignee_name()

        self.task_assignee.blockSignals(True)
        self.task_assignee.clear()
        for assignee in assignees:
            self.task_assignee.addItem(assignee["name"], assignee["id"])
        self.task_assignee.setCurrentText(selected_name)
        self.task_assignee.blockSignals(False)

    def fetch_assignees(self, show_errors=False, preserve_text=None):
        try:
            response = requests.get(self.endpoint_url("assignees"), timeout=3)
        except requests.RequestException as error:
            if show_errors:
                QMessageBox.warning(self, "Connection Error", f"Could not load saved people: {error}")
            return

        if response.status_code == 200:
            assignees = response.json()
            self.populate_assignee_combo(assignees, preserve_text)
            self.set_assignee_controls_available(
                True,
                "Choose a saved person or type a new one and click Save Person.",
                "#1f7a43",
            )
            return

        if response.status_code == 404:
            self.set_assignee_controls_available(
                False,
                "This Pi backend does not support saved people yet. Pull the latest update on the Pi.",
                "#c05621",
            )
            return

        if show_errors:
            message = self.response_message(response, f"Could not load saved people (HTTP {response.status_code}).")
            QMessageBox.warning(self, "Saved People Error", message)

    def save_assignee_name(self, name, silent=False):
        assignee_name = name.strip()
        if not assignee_name:
            if not silent:
                QMessageBox.warning(self, "Input Error", "Enter a person name before saving it.")
            return False

        try:
            response = requests.post(self.endpoint_url("assignees"), json={"name": assignee_name}, timeout=3)
        except requests.RequestException as error:
            if not silent:
                QMessageBox.critical(self, "Saved People Error", f"Could not save the person name: {error}")
            return False

        if response.status_code in (200, 201):
            self.fetch_assignees(show_errors=False, preserve_text=assignee_name)
            if not silent:
                QMessageBox.information(self, "Person Saved", f"{assignee_name} is now in the assignee dropdown.")
            return True

        if response.status_code == 404:
            self.set_assignee_controls_available(
                False,
                "This Pi backend does not support saved people yet. Pull the latest update on the Pi.",
                "#c05621",
            )
            if not silent:
                QMessageBox.warning(
                    self,
                    "Saved People Unavailable",
                    "The connected Pi backend does not support saved people yet.",
                )
            return False

        if not silent:
            message = self.response_message(response, f"Could not save the person name (HTTP {response.status_code}).")
            QMessageBox.critical(self, "Saved People Error", message)
        return False

    def save_current_assignee(self):
        self.save_assignee_name(self.current_assignee_name())

    def delete_current_assignee(self):
        assignee_id = self.task_assignee.currentData()
        assignee_name = self.current_assignee_name()

        if assignee_id is None:
            return QMessageBox.warning(
                self,
                "Saved People",
                "Select a saved person from the dropdown before removing them.",
            )

        reply = QMessageBox.question(
            self,
            "Remove Person",
            f"Remove {assignee_name} from the saved assignee list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            response = requests.delete(self.endpoint_url(f"assignees/{assignee_id}"), timeout=3)
        except requests.RequestException as error:
            return QMessageBox.critical(self, "Saved People Error", f"Could not remove the person name: {error}")

        if response.status_code == 204:
            self.fetch_assignees(show_errors=False, preserve_text="")
            return

        message = self.response_message(response, f"Could not remove the person name (HTTP {response.status_code}).")
        QMessageBox.critical(self, "Saved People Error", message)

    def restart_pi_display(self):
        self.server_url = self.build_server_url()
        reply = QMessageBox.question(
            self,
            "Restart Pi Display",
            "Check GitHub for Pi updates and restart the display app now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.restart_display_btn.setEnabled(False)
        try:
            response = requests.post(self.endpoint_url("admin/restart-display"), timeout=5)
            if response.status_code == 202:
                message = self.response_message(
                    response,
                    "Pi display refresh requested. The Pi will pull updates if any are available.",
                )
                QMessageBox.information(self, "Refresh Requested", message)
            else:
                message = self.response_message(
                    response,
                    f"Could not refresh the Pi display (HTTP {response.status_code}).",
                )
                QMessageBox.critical(self, "Refresh Failed", message)
        except requests.RequestException as error:
            QMessageBox.critical(self, "Refresh Failed", f"Could not reach the Pi backend: {error}")
        finally:
            self.restart_display_btn.setEnabled(True)

    def current_selected_id(self, list_widget):
        item = list_widget.currentItem()
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def restore_selection(self, list_widget, selected_id):
        if selected_id is None:
            return

        for index in range(list_widget.count()):
            item = list_widget.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == selected_id:
                list_widget.setCurrentItem(item)
                return

    def refresh_notices(self, show_errors=True):
        selected_id = self.current_selected_id(self.notice_list)
        try:
            response = requests.get(self.endpoint_url("notices"), timeout=3)
        except requests.RequestException as error:
            if show_errors:
                QMessageBox.warning(self, "Connection Error", f"Could not load notices: {error}")
            return

        if response.status_code != 200:
            if show_errors:
                message = self.response_message(response, f"Could not load notices (HTTP {response.status_code}).")
                QMessageBox.warning(self, "Connection Error", message)
            return

        self.notice_list.clear()
        for notice in response.json():
            item = QListWidgetItem(f"[{notice['priority']}] {notice['title']}")
            if notice["priority"] == "High":
                item.setForeground(QColor("#e74c3c"))
            elif notice["priority"] == "Medium":
                item.setForeground(QColor("#f39c12"))
            else:
                item.setForeground(QColor("#3498db"))
            item.setData(Qt.ItemDataRole.UserRole, notice["id"])
            self.notice_list.addItem(item)

        self.restore_selection(self.notice_list, selected_id)

    def build_task_item_text(self, task):
        header = f"[{task['priority']}] {task['title']} -> {task['assignee']}"
        details = []

        if task.get("due_time"):
            details.append(f"Due: {task['due_time']}")

        if task.get("timer_elapsed"):
            details.append("TIMER ELAPSED")
        elif task.get("timer_remaining_seconds") is not None:
            details.append(f"Timer: {self.format_duration(task['timer_remaining_seconds'])}")

        if not details:
            return header

        return header + "\n" + " | ".join(details)

    def update_task_alerts(self, tasks):
        elapsed_tasks = [task for task in tasks if task.get("timer_elapsed")]
        elapsed_ids = {task["id"] for task in elapsed_tasks}
        new_elapsed_tasks = [task for task in elapsed_tasks if task["id"] not in self.elapsed_notified_ids]

        self.elapsed_notified_ids.intersection_update(elapsed_ids)
        if new_elapsed_tasks:
            self.play_alert_sound()
            for task in new_elapsed_tasks:
                self.elapsed_notified_ids.add(task["id"])

        if elapsed_tasks:
            names = ", ".join(f"{task['title']} ({task['assignee']})" for task in elapsed_tasks)
            self.set_task_alert_banner(f"Timer elapsed: {names}", "#fff1ef", "#c0392b")
        else:
            self.set_task_alert_banner("No timer alerts", "#edf2f7", "#2f3640")

    def play_alert_sound(self):
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            QApplication.beep()

    def refresh_tasks(self, show_errors=True):
        selected_id = self.current_selected_id(self.task_list)
        try:
            response = requests.get(self.endpoint_url("tasks"), timeout=3)
        except requests.RequestException as error:
            if show_errors:
                QMessageBox.warning(self, "Connection Error", f"Could not load tasks: {error}")
            return

        if response.status_code != 200:
            if show_errors:
                message = self.response_message(response, f"Could not load tasks (HTTP {response.status_code}).")
                QMessageBox.warning(self, "Connection Error", message)
            return

        self.cached_tasks = response.json()
        self.task_list.clear()
        for task in self.cached_tasks:
            item = QListWidgetItem(self.build_task_item_text(task))
            item.setData(Qt.ItemDataRole.UserRole, task["id"])

            if task.get("timer_elapsed"):
                item.setForeground(QColor("#c0392b"))
                item.setBackground(QColor("#fff1ef"))
            elif task["priority"] == "High":
                item.setForeground(QColor("#e74c3c"))
            elif task["priority"] == "Medium":
                item.setForeground(QColor("#f39c12"))
            else:
                item.setForeground(QColor("#1f7a43"))

            item.setSizeHint(QSize(item.sizeHint().width(), max(56, item.sizeHint().height())))
            self.task_list.addItem(item)

        self.restore_selection(self.task_list, selected_id)
        self.update_task_alerts(self.cached_tasks)

    def poll_tasks(self):
        self.refresh_tasks(show_errors=False)

    def refresh_data(self, show_errors=True):
        self.refresh_notices(show_errors=show_errors)
        self.fetch_assignees(show_errors=False)
        self.refresh_tasks(show_errors=show_errors)

    def add_notice(self):
        data = {
            "title": self.notice_title.text().strip(),
            "content": self.notice_content.toPlainText().strip(),
            "priority": self.notice_priority.currentText(),
        }
        if not data["title"] or not data["content"]:
            return QMessageBox.warning(self, "Input Error", "Title and Content are required")

        try:
            response = requests.post(self.endpoint_url("notices"), json=data, timeout=5)
        except requests.RequestException as error:
            return QMessageBox.critical(self, "Error", str(error))

        if response.status_code == 201:
            self.notice_title.clear()
            self.notice_content.clear()
            self.refresh_notices(show_errors=False)
            return

        message = self.response_message(response, f"Could not post the notice (HTTP {response.status_code}).")
        QMessageBox.critical(self, "Error", message)

    def delete_notice(self):
        item = self.notice_list.currentItem()
        if not item:
            return

        notice_id = item.data(Qt.ItemDataRole.UserRole)
        try:
            response = requests.delete(self.endpoint_url(f"notices/{notice_id}"), timeout=5)
        except requests.RequestException as error:
            return QMessageBox.critical(self, "Error", str(error))

        if response.status_code == 204:
            self.refresh_notices(show_errors=False)
            return

        message = self.response_message(response, f"Could not remove the notice (HTTP {response.status_code}).")
        QMessageBox.critical(self, "Error", message)

    def add_task(self):
        assignee_name = self.current_assignee_name()
        countdown_seconds = None

        if self.task_timer_enabled.isChecked():
            countdown_seconds = self.current_countdown_seconds()
            if countdown_seconds is None:
                return QMessageBox.warning(
                    self,
                    "Input Error",
                    "Set the countdown timer to at least 1 minute before assigning the task.",
                )

        data = {
            "title": self.task_title.text().strip(),
            "assignee": assignee_name,
            "due_time": self.task_due_note.text().strip(),
            "priority": self.task_priority.currentText(),
            "countdown_seconds": countdown_seconds,
        }
        if not data["title"] or not data["assignee"]:
            return QMessageBox.warning(self, "Input Error", "Title and Assignee are required")

        if self.assignee_api_available:
            self.save_assignee_name(assignee_name, silent=True)

        try:
            response = requests.post(self.endpoint_url("tasks"), json=data, timeout=5)
        except requests.RequestException as error:
            return QMessageBox.critical(self, "Error", str(error))

        if response.status_code == 201:
            self.task_title.clear()
            self.task_due_note.clear()
            self.reset_timer_inputs()
            self.fetch_assignees(show_errors=False, preserve_text=assignee_name)
            self.refresh_tasks(show_errors=False)
            return

        message = self.response_message(response, f"Could not assign the task (HTTP {response.status_code}).")
        QMessageBox.critical(self, "Error", message)

    def delete_task(self):
        item = self.task_list.currentItem()
        if not item:
            return

        task_id = item.data(Qt.ItemDataRole.UserRole)
        try:
            response = requests.delete(self.endpoint_url(f"tasks/{task_id}"), timeout=5)
        except requests.RequestException as error:
            return QMessageBox.critical(self, "Error", str(error))

        if response.status_code == 204:
            self.refresh_tasks(show_errors=False)
            return

        message = self.response_message(response, f"Could not remove the task (HTTP {response.status_code}).")
        QMessageBox.critical(self, "Error", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NoticeBoardAdmin()
    window.show()
    sys.exit(app.exec())
