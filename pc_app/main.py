import sys

import qtawesome as qta
import requests
from PyQt6.QtCore import QEvent, QRect, QSize, QSettings, QTimer, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
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
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

DEFAULT_REMOTE_SETTINGS = {
    "pi_timer_sound_enabled": True,
    "pi_timer_popup_enabled": True,
    "pi_timer_voice": "en-gb",
    "pi_timer_speech_rate": 120,
    "pi_timer_popup_duration_seconds": 30,
    "pi_refresh_interval_seconds": 2,
    "pi_scroll_step": 2,
    "pi_scroll_pause_seconds": 2,
}

VOICE_TEST_SAMPLE = "Hello team. This is a Noticeboard voice test."

VOICE_PRESETS = [
    ("British English", "en-gb"),
    ("British English Female", "en-gb+f3"),
    ("British English Male", "en-gb+m3"),
    ("English Default", "en"),
    ("American English", "en-us"),
    ("Scottish English", "en-sc"),
]


class ModernButton(QPushButton):
    def __init__(self, text, color="#3498db", icon=None):
        super().__init__(text)
        if icon:
            try:
                self.setIcon(qta.icon(icon, color="white"))
            except Exception:
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


class ReliableSpinBox(QSpinBox):
    BUTTON_WIDTH = 26
    BUTTON_MARGIN = 2

    def __init__(self):
        super().__init__()
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        self.setAccelerated(True)
        self.lineEdit().installEventFilter(self)

    def spin_button_rects(self):
        button_width = min(max(self.BUTTON_WIDTH, self.height() // 2), max(self.BUTTON_WIDTH, self.width() // 3))
        button_left = max(self.BUTTON_MARGIN, self.width() - button_width - self.BUTTON_MARGIN)
        top = self.BUTTON_MARGIN
        available_height = max(2, self.height() - (self.BUTTON_MARGIN * 2))
        top_height = max(1, available_height // 2)
        bottom_height = max(1, available_height - top_height)
        up_rect = QRect(button_left, top, button_width, top_height)
        down_rect = QRect(button_left, top + top_height, button_width, bottom_height)
        return up_rect, down_rect

    def handle_button_click(self, point):
        if not self.isEnabled() or self.isReadOnly():
            return False

        up_rect, down_rect = self.spin_button_rects()
        if up_rect.contains(point):
            self.stepUp()
            return True
        if down_rect.contains(point):
            self.stepDown()
            return True
        return False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.handle_button_click(event.position().toPoint()):
            event.accept()
            return
        super().mousePressEvent(event)

    def eventFilter(self, watched, event):
        if watched is self.lineEdit() and event.type() == QEvent.Type.MouseButtonPress:
            point = self.lineEdit().mapToParent(event.position().toPoint())
            if self.handle_button_click(point):
                event.accept()
                return True
        return super().eventFilter(watched, event)


class NoticeBoardAdmin(QMainWindow):
    def __init__(self):
        super().__init__()
        self.local_settings = QSettings("Demiwidget", "NoticeboardManager")
        self.saved_server_host = self.local_settings.value("server_host", "localhost", type=str) or "localhost"
        self.server_url = self.build_server_url_from_host(self.saved_server_host)
        self.cached_tasks = []
        self.assignee_api_available = False
        self.remote_settings_available = False
        self.remote_settings = DEFAULT_REMOTE_SETTINGS.copy()

        self.setWindowTitle("Noticeboard Manager")
        self.setMinimumSize(1040, 760)

        self.init_ui()
        self.apply_styles()
        self.update_connection_labels()

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
            QLineEdit, QTextEdit {
                border: 2px solid #9fb5a6;
                border-radius: 8px;
                padding: 8px 10px;
                background-color: #fcfffd;
                color: #102a1c;
                selection-background-color: #1f7a43;
                selection-color: white;
                font-size: 14px;
            }
            QLineEdit {
                min-height: 34px;
            }
            QTextEdit {
                min-height: 110px;
                padding: 10px 12px;
            }
            QLineEdit:hover, QTextEdit:hover {
                border-color: #6f9278;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 2px solid #1f7a43;
                background-color: white;
            }
            QLineEdit::placeholder, QTextEdit::placeholder {
                color: #6b7f73;
            }
            QComboBox, QSpinBox {
                min-height: 34px;
                background-color: #ffffff;
                color: #102a1c;
                border: 1px solid #9fb5a6;
                border-radius: 6px;
                font-size: 14px;
            }
            QSpinBox {
                padding-right: 28px;
            }
            QComboBox:hover, QSpinBox:hover {
                border: 1px solid #6f9278;
            }
            QComboBox:focus, QSpinBox:focus {
                border: 2px solid #1f7a43;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #102a1c;
                selection-background-color: #1f7a43;
                selection-color: white;
                border: 1px solid #9fb5a6;
                outline: 0;
            }
            QComboBox QAbstractItemView::item {
                min-height: 28px;
                padding: 6px 10px;
                background-color: #ffffff;
                color: #102a1c;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #1f7a43;
                color: white;
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

        self.connection_summary_label = QLabel()
        self.connection_summary_label.setStyleSheet("color: #1f7a43; font-weight: 700;")
        header.addWidget(self.connection_summary_label)

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

        self.settings_tab = QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.settings_tab, "Settings")

        refresh_btn = ModernButton("Refresh All Data", "#9b59b6", "fa5s.sync")
        refresh_btn.clicked.connect(lambda: self.refresh_data(show_errors=True))
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def create_card(self, title, subtitle=None):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #dfe4ea;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        heading = QLabel(title)
        heading.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        heading.setStyleSheet("color: #2c3e50;")
        layout.addWidget(heading)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            subtitle_label.setStyleSheet("color: #52606d;")
            layout.addWidget(subtitle_label)

        return frame, layout

    def add_settings_field(self, layout, label_text, widget, help_text=None):
        label = QLabel(label_text)
        label.setStyleSheet("color: #2c3e50; font-weight: 700;")
        layout.addWidget(label)
        layout.addWidget(widget)

        if help_text:
            help_label = QLabel(help_text)
            help_label.setWordWrap(True)
            help_label.setStyleSheet("color: #6b7280; font-size: 13px;")
            layout.addWidget(help_label)

    def setup_notice_tab(self):
        layout = QHBoxLayout(self.notice_tab)

        form_container, form_layout = self.create_card("Add New Notice")
        form_container.setFixedWidth(360)

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

        list_container, list_layout = self.create_card("Current Notices")
        self.notice_list = QListWidget()
        self.notice_list.setSpacing(5)
        list_layout.addWidget(self.notice_list)

        del_btn = ModernButton("Remove Selected", "#e74c3c", "fa5s.trash-alt")
        del_btn.clicked.connect(self.delete_notice)
        list_layout.addWidget(del_btn)
        layout.addWidget(list_container, 1)

    def setup_task_tab(self):
        layout = QHBoxLayout(self.task_tab)

        form_container, form_layout = self.create_card(
            "Assign New Task",
            "Choose a saved person or type a new name. Timers are optional and can trigger Pi-side alerts.",
        )
        form_container.setFixedWidth(420)

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
        self.task_timer_hours = ReliableSpinBox()
        self.task_timer_hours.setRange(0, 72)
        timer_row.addWidget(self.task_timer_hours)

        timer_row.addWidget(QLabel("Minutes:"))
        self.task_timer_minutes = ReliableSpinBox()
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

        list_container, list_layout = self.create_card(
            "Current Tasks",
            "Elapsed timers are highlighted here. Sounds and popups now happen on the Pi display.",
        )

        self.task_alert_label = QLabel("No timer alerts")
        self.task_alert_label.setWordWrap(True)
        self.set_task_alert_banner("No timer alerts", "#edf2f7", "#2f3640")
        list_layout.addWidget(self.task_alert_label)

        self.task_list = QListWidget()
        self.task_list.setSpacing(6)
        list_layout.addWidget(self.task_list)

        del_btn = ModernButton("Remove Selected", "#e74c3c", "fa5s.trash-alt")
        del_btn.clicked.connect(self.delete_task)
        list_layout.addWidget(del_btn)

        layout.addWidget(list_container, 1)

        self.update_timer_inputs_enabled(False)
        self.set_assignee_controls_available(
            False,
            "Saved people list will be available once the Pi backend supports assignees.",
            "#8e44ad",
        )

    def setup_settings_tab(self):
        outer_layout = QVBoxLayout(self.settings_tab)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent; border: none;")
        outer_layout.addWidget(scroll_area)

        scroll_widget = QWidget()
        scroll_area.setWidget(scroll_widget)

        layout = QHBoxLayout(scroll_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        left_column = QVBoxLayout()
        left_column.setSpacing(16)
        right_column = QVBoxLayout()
        right_column.setSpacing(16)

        connection_card, connection_layout = self.create_card(
            "Pi Connection",
            "This connection setting is stored on this PC so the app remembers which Pi to talk to.",
        )
        self.server_host_input = QLineEdit()
        self.server_host_input.setPlaceholderText("Pi host or IP address")
        self.server_host_input.setText(self.saved_server_host)
        self.add_settings_field(
            connection_layout,
            "Pi Host or IP",
            self.server_host_input,
            "Examples: 192.168.1.180 or dashboardmanager.local",
        )

        connection_buttons = QHBoxLayout()
        connect_btn = ModernButton("Apply Connection", "#2ecc71", "fa5s.link")
        connect_btn.clicked.connect(self.update_server_url)
        connection_buttons.addWidget(connect_btn)

        reload_btn = ModernButton("Load Pi Settings", "#2980b9", "fa5s.download")
        reload_btn.clicked.connect(lambda: self.load_remote_settings(show_errors=True))
        connection_buttons.addWidget(reload_btn)
        connection_layout.addLayout(connection_buttons)

        self.connection_details_label = QLabel()
        self.connection_details_label.setWordWrap(True)
        connection_layout.addWidget(self.connection_details_label)
        left_column.addWidget(connection_card)

        alerts_card, alerts_layout = self.create_card(
            "Pi Timer Alerts",
            "These settings are stored on the Pi backend and control sounds and timer popups on the display screen.",
        )
        self.setting_pi_sound_enabled = QCheckBox("Speak timer alerts on the Pi display")
        alerts_layout.addWidget(self.setting_pi_sound_enabled)

        self.setting_voice = QComboBox()
        self.setting_voice.setEditable(True)
        self.setting_voice.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for label, voice_code in VOICE_PRESETS:
            self.setting_voice.addItem(f"{label} ({voice_code})", voice_code)
        self.add_settings_field(
            alerts_layout,
            "Speech Voice",
            self.setting_voice,
            "Pick a voice preset or type a custom `espeak-ng` voice code if you want to experiment.",
        )

        self.setting_speech_rate = ReliableSpinBox()
        self.setting_speech_rate.setRange(80, 220)
        self.add_settings_field(
            alerts_layout,
            "Speech Speed",
            self.setting_speech_rate,
            "Lower values sound slower and usually a bit easier to understand from across the room.",
        )

        voice_actions = QHBoxLayout()
        self.test_voice_btn = ModernButton("Test Pi Voice", "#1f7a43", "fa5s.volume-up")
        self.test_voice_btn.clicked.connect(self.test_pi_voice)
        voice_actions.addWidget(self.test_voice_btn)
        voice_actions.addStretch()
        alerts_layout.addLayout(voice_actions)

        voice_help = QLabel("This plays a short sample on the Pi using the voice and speed shown above, even before you save.")
        voice_help.setWordWrap(True)
        voice_help.setStyleSheet("color: #6b7280; font-size: 13px;")
        alerts_layout.addWidget(voice_help)

        self.setting_pi_popup_enabled = QCheckBox("Show timer popup on the Pi display")
        alerts_layout.addWidget(self.setting_pi_popup_enabled)

        self.setting_popup_duration = ReliableSpinBox()
        self.setting_popup_duration.setRange(5, 300)
        self.add_settings_field(
            alerts_layout,
            "Popup Duration (seconds)",
            self.setting_popup_duration,
            "How long the elapsed-task popup stays on the Pi screen before it disappears.",
        )
        left_column.addWidget(alerts_card)

        display_card, display_layout = self.create_card(
            "Pi Display Behaviour",
            "These controls tune how often the Pi refreshes and how quickly long notice/task columns scroll.",
        )

        self.setting_refresh_interval = ReliableSpinBox()
        self.setting_refresh_interval.setRange(1, 60)
        self.add_settings_field(
            display_layout,
            "Pi Refresh Interval (seconds)",
            self.setting_refresh_interval,
            "How often the Pi asks the backend for fresh notices, tasks, timers, and settings.",
        )

        self.setting_scroll_step = ReliableSpinBox()
        self.setting_scroll_step.setRange(1, 10)
        self.add_settings_field(
            display_layout,
            "Auto-Scroll Speed",
            self.setting_scroll_step,
            "Higher values make long lists move faster on the Pi display.",
        )

        self.setting_scroll_pause = ReliableSpinBox()
        self.setting_scroll_pause.setRange(1, 30)
        self.add_settings_field(
            display_layout,
            "Auto-Scroll Pause (seconds)",
            self.setting_scroll_pause,
            "How long the Pi pauses at the top and bottom of a scrolling column.",
        )
        right_column.addWidget(display_card)

        actions_card, actions_layout = self.create_card(
            "Save Settings",
            "Use these buttons to push the current Pi display settings to the connected backend or reload them.",
        )
        actions_row = QHBoxLayout()
        self.save_pi_settings_btn = ModernButton("Save Pi Settings", "#16a085", "fa5s.save")
        self.save_pi_settings_btn.clicked.connect(self.save_remote_settings)
        actions_row.addWidget(self.save_pi_settings_btn)

        self.reload_pi_settings_btn = ModernButton("Reload Pi Settings", "#7f8c8d", "fa5s.sync-alt")
        self.reload_pi_settings_btn.clicked.connect(lambda: self.load_remote_settings(show_errors=True))
        actions_row.addWidget(self.reload_pi_settings_btn)
        actions_layout.addLayout(actions_row)

        self.pi_settings_status_label = QLabel("Pi settings have not been loaded yet.")
        self.pi_settings_status_label.setWordWrap(True)
        actions_layout.addWidget(self.pi_settings_status_label)
        right_column.addWidget(actions_card)

        left_column.addStretch()
        right_column.addStretch()
        layout.addLayout(left_column, 1)
        layout.addLayout(right_column, 1)
        self.populate_remote_settings_controls(DEFAULT_REMOTE_SETTINGS.copy())
        self.update_remote_settings_availability(False, "Connect to the Pi and load its settings to edit them.")

    def current_server_host(self):
        host = self.server_host_input.text().strip()
        if not host:
            host = "localhost"
        return host

    def build_server_url_from_host(self, host):
        return f"http://{host}:5000/api"

    def endpoint_url(self, path):
        return f"{self.server_url}/{path.lstrip('/')}"

    def sync_server_host(self):
        host = self.current_server_host()
        self.saved_server_host = host
        self.server_url = self.build_server_url_from_host(host)
        self.local_settings.setValue("server_host", host)
        self.update_connection_labels()
        return host

    def update_connection_labels(self):
        summary = f"Configured Pi: {self.saved_server_host}"
        self.connection_summary_label.setText(summary)
        self.connection_details_label.setText(
            f"Current API base: {self.server_url}\nUse Apply Connection after changing the Pi address."
        )

    def response_message(self, response, fallback):
        try:
            payload = response.json()
        except ValueError:
            return fallback

        if isinstance(payload, dict):
            return payload.get("message") or payload.get("error") or fallback

        return fallback

    def update_server_url(self):
        self.sync_server_host()
        self.refresh_data(show_errors=True)

    def populate_remote_settings_controls(self, settings):
        merged = DEFAULT_REMOTE_SETTINGS.copy()
        merged.update(settings)
        self.remote_settings = merged

        self.setting_pi_sound_enabled.setChecked(bool(merged["pi_timer_sound_enabled"]))
        self.set_voice_combo_value(str(merged["pi_timer_voice"]))
        self.setting_speech_rate.setValue(int(merged["pi_timer_speech_rate"]))
        self.setting_pi_popup_enabled.setChecked(bool(merged["pi_timer_popup_enabled"]))
        self.setting_popup_duration.setValue(int(merged["pi_timer_popup_duration_seconds"]))
        self.setting_refresh_interval.setValue(int(merged["pi_refresh_interval_seconds"]))
        self.setting_scroll_step.setValue(int(merged["pi_scroll_step"]))
        self.setting_scroll_pause.setValue(int(merged["pi_scroll_pause_seconds"]))

    def set_voice_combo_value(self, voice_value):
        voice_text = (voice_value or "").strip() or DEFAULT_REMOTE_SETTINGS["pi_timer_voice"]

        self.setting_voice.blockSignals(True)
        for index in range(self.setting_voice.count()):
            if self.setting_voice.itemData(index) == voice_text:
                self.setting_voice.setCurrentIndex(index)
                self.setting_voice.blockSignals(False)
                return

        self.setting_voice.setCurrentIndex(-1)
        self.setting_voice.setEditText(voice_text)
        self.setting_voice.blockSignals(False)

    def current_voice_value(self):
        index = self.setting_voice.currentIndex()
        if index >= 0:
            data_value = self.setting_voice.itemData(index)
            item_text = self.setting_voice.itemText(index)
            current_text = self.setting_voice.currentText().strip()
            if current_text == item_text and data_value:
                return str(data_value)

        current_text = self.setting_voice.currentText().strip()
        return current_text or DEFAULT_REMOTE_SETTINGS["pi_timer_voice"]

    def collect_remote_settings_payload(self):
        return {
            "pi_timer_sound_enabled": self.setting_pi_sound_enabled.isChecked(),
            "pi_timer_voice": self.current_voice_value(),
            "pi_timer_speech_rate": self.setting_speech_rate.value(),
            "pi_timer_popup_enabled": self.setting_pi_popup_enabled.isChecked(),
            "pi_timer_popup_duration_seconds": self.setting_popup_duration.value(),
            "pi_refresh_interval_seconds": self.setting_refresh_interval.value(),
            "pi_scroll_step": self.setting_scroll_step.value(),
            "pi_scroll_pause_seconds": self.setting_scroll_pause.value(),
        }

    def update_remote_settings_availability(self, available, message):
        self.remote_settings_available = available
        self.save_pi_settings_btn.setEnabled(available)
        self.reload_pi_settings_btn.setEnabled(True)
        self.setting_pi_sound_enabled.setEnabled(available)
        self.setting_voice.setEnabled(available)
        self.setting_speech_rate.setEnabled(available)
        self.test_voice_btn.setEnabled(available)
        self.setting_pi_popup_enabled.setEnabled(available)
        self.setting_popup_duration.setEnabled(available)
        self.setting_refresh_interval.setEnabled(available)
        self.setting_scroll_step.setEnabled(available)
        self.setting_scroll_pause.setEnabled(available)
        self.pi_settings_status_label.setText(message)
        self.pi_settings_status_label.setStyleSheet(
            f"color: {'#1f7a43' if available else '#c05621'}; font-weight: 600;"
        )

    def load_remote_settings(self, show_errors=False):
        self.sync_server_host()
        try:
            response = requests.get(self.endpoint_url("settings"), timeout=3)
        except requests.RequestException as error:
            self.update_remote_settings_availability(False, f"Could not load Pi settings: {error}")
            if show_errors:
                QMessageBox.warning(self, "Connection Error", f"Could not load Pi settings: {error}")
            return

        if response.status_code == 200:
            self.populate_remote_settings_controls(response.json())
            self.update_remote_settings_availability(True, "Pi settings loaded. Changes here affect the display app.")
            return

        if response.status_code == 404:
            self.populate_remote_settings_controls(DEFAULT_REMOTE_SETTINGS.copy())
            self.update_remote_settings_availability(
                False,
                "This Pi backend does not support shared Pi settings yet. Pull the latest update on the Pi.",
            )
            if show_errors:
                QMessageBox.warning(
                    self,
                    "Pi Settings Unavailable",
                    "The connected Pi backend does not support shared Pi settings yet.",
                )
            return

        message = self.response_message(response, f"Could not load Pi settings (HTTP {response.status_code}).")
        self.update_remote_settings_availability(False, message)
        if show_errors:
            QMessageBox.warning(self, "Pi Settings Error", message)

    def save_remote_settings(self):
        self.sync_server_host()
        payload = self.collect_remote_settings_payload()

        try:
            response = requests.put(self.endpoint_url("settings"), json=payload, timeout=5)
        except requests.RequestException as error:
            return QMessageBox.critical(self, "Pi Settings Error", f"Could not save Pi settings: {error}")

        if response.status_code == 200:
            self.populate_remote_settings_controls(response.json())
            self.update_remote_settings_availability(True, "Pi settings saved. The display app will pick them up.")
            QMessageBox.information(self, "Pi Settings Saved", "The connected Pi display settings were updated.")
            return

        message = self.response_message(response, f"Could not save Pi settings (HTTP {response.status_code}).")
        QMessageBox.critical(self, "Pi Settings Error", message)

    def test_pi_voice(self):
        if not self.remote_settings_available:
            QMessageBox.warning(
                self,
                "Voice Test Unavailable",
                "Connect to the Pi and load its settings before testing the voice.",
            )
            return

        self.sync_server_host()
        payload = {
            "voice": self.current_voice_value(),
            "speech_rate": self.setting_speech_rate.value(),
            "text": VOICE_TEST_SAMPLE,
        }

        self.test_voice_btn.setEnabled(False)
        try:
            response = requests.post(self.endpoint_url("admin/test-voice"), json=payload, timeout=5)
        except requests.RequestException as error:
            QMessageBox.critical(self, "Voice Test Failed", f"Could not reach the Pi backend: {error}")
            return
        finally:
            self.test_voice_btn.setEnabled(self.remote_settings_available)

        if response.status_code == 202:
            message = self.response_message(response, "Voice test started on the Pi.")
            QMessageBox.information(self, "Voice Test Started", message)
            return

        if response.status_code == 404:
            QMessageBox.warning(
                self,
                "Voice Test Unavailable",
                "The connected Pi backend does not support voice testing yet. Pull the latest update on the Pi.",
            )
            return

        message = self.response_message(response, f"Could not start the Pi voice test (HTTP {response.status_code}).")
        QMessageBox.critical(self, "Voice Test Failed", message)

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
        self.sync_server_host()
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
        if elapsed_tasks:
            names = ", ".join(f"{task['title']} ({task['assignee']})" for task in elapsed_tasks)
            self.set_task_alert_banner(f"Pi alert active for: {names}", "#fff1ef", "#c0392b")
        else:
            self.set_task_alert_banner("No timer alerts", "#edf2f7", "#2f3640")

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
        self.sync_server_host()
        self.refresh_notices(show_errors=show_errors)
        self.fetch_assignees(show_errors=False)
        self.load_remote_settings(show_errors=False)
        self.refresh_tasks(show_errors=show_errors)

    def add_notice(self):
        self.sync_server_host()
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
        self.sync_server_host()
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
        self.sync_server_host()
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
        self.sync_server_host()
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
