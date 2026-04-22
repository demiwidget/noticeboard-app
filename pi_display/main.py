import os
import shutil
import subprocess
import sys
from html import escape as html_escape

import requests

try:
    from PyQt6.QtCore import QDateTime, QTimer, Qt
    from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPalette
    from PyQt6.QtWidgets import (
        QApplication,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )
    QT6 = True
except ImportError:
    from PyQt5.QtCore import QDateTime, QTimer, Qt
    from PyQt5.QtGui import QBrush, QColor, QFont, QLinearGradient, QPalette
    from PyQt5.QtWidgets import (
        QApplication,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )
    QT6 = False

DEFAULT_PI_SETTINGS = {
    "pi_timer_sound_enabled": True,
    "pi_timer_popup_enabled": True,
    "pi_timer_voice": "en-gb",
    "pi_timer_speech_rate": 120,
    "pi_timer_popup_duration_seconds": 30,
    "pi_refresh_interval_seconds": 2,
    "pi_scroll_step": 2,
    "pi_scroll_pause_seconds": 2,
}

VOICE_START_DELAY_MS = 350

if QT6:
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
    ALIGN_TOP = Qt.AlignmentFlag.AlignTop
    FONT_BOLD = QFont.Weight.Bold
    FONT_DEMIBOLD = QFont.Weight.DemiBold
    PALETTE_WINDOW = QPalette.ColorRole.Window
    STYLED_PANEL = QFrame.Shape.StyledPanel
    WA_TRANSPARENT = Qt.WidgetAttribute.WA_TransparentForMouseEvents
else:
    ALIGN_CENTER = Qt.AlignCenter
    ALIGN_TOP = Qt.AlignTop
    FONT_BOLD = QFont.Bold
    FONT_DEMIBOLD = QFont.DemiBold
    PALETTE_WINDOW = QPalette.Window
    STYLED_PANEL = QFrame.StyledPanel
    WA_TRANSPARENT = Qt.WA_TransparentForMouseEvents


class Card(QFrame):
    def __init__(
        self,
        title,
        content,
        priority,
        type="notice",
        assignee=None,
        due_text=None,
        timer_label=None,
        timer_elapsed=False,
    ):
        super().__init__()
        self.setObjectName("noticeCard")
        self.setFrameShape(STYLED_PANEL)

        priority_styles = {
            "High": {"accent": "#ef6b57", "border": "#f7c8be", "badge": "#b94f3e"},
            "Medium": {"accent": "#d7ac45", "border": "#eddca8", "badge": "#8a6a18"},
            "Low": {"accent": "#39a85d", "border": "#cce8d3", "badge": "#1f7d3f"},
        }
        style = priority_styles.get(priority, priority_styles["Low"])
        if timer_elapsed:
            style = {"accent": "#f0625f", "border": "#f5c5c3", "badge": "#c0392b"}

        self.setStyleSheet(f"""
            QFrame#noticeCard {{
                background-color: rgba(249, 252, 249, 248);
                border: 2px solid {style["border"]};
                border-left: 10px solid {style["accent"]};
                border-radius: 18px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("DejaVu Sans", 19, FONT_BOLD))
        title_lbl.setStyleSheet("color: #10301f;")
        title_lbl.setWordWrap(True)
        top_row.addWidget(title_lbl, 1)

        badge_text = "ALERT" if timer_elapsed else priority.upper()
        priority_lbl = QLabel(badge_text)
        priority_lbl.setAlignment(ALIGN_CENTER)
        priority_lbl.setMinimumWidth(92)
        priority_lbl.setFont(QFont("DejaVu Sans", 11, FONT_BOLD))
        priority_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {style["badge"]};
                color: white;
                border-radius: 12px;
                padding: 6px 10px;
            }}
        """)
        top_row.addWidget(priority_lbl)
        layout.addLayout(top_row)

        if type == "notice":
            content_lbl = QLabel(content)
            content_lbl.setFont(QFont("DejaVu Sans", 15, FONT_DEMIBOLD))
            content_lbl.setStyleSheet("color: #2c4a39;")
            content_lbl.setWordWrap(True)
            layout.addWidget(content_lbl)
            return

        def build_chip(text, background, foreground="#123a26"):
            chip = QLabel(text)
            chip.setFont(QFont("DejaVu Sans", 12, FONT_BOLD))
            chip.setStyleSheet(f"""
                QLabel {{
                    color: {foreground};
                    background-color: {background};
                    border-radius: 12px;
                    padding: 8px 10px;
                }}
            """)
            return chip

        row_one = QHBoxLayout()
        row_one.setSpacing(10)
        row_one.addWidget(build_chip(f"ASSIGNEE  {assignee or 'Unassigned'}", "#e8f5eb"), 1)

        if timer_label:
            timer_background = "#ffe9e7" if timer_elapsed else "#e2f6e8"
            timer_foreground = "#b63b34" if timer_elapsed else "#14532d"
            row_one.addWidget(build_chip(timer_label, timer_background, timer_foreground), 1)

        layout.addLayout(row_one)

        if due_text:
            row_two = QHBoxLayout()
            row_two.addWidget(build_chip(f"DUE  {due_text}", "#f1f7e8"))
            layout.addLayout(row_two)


class EmptyStateCard(QFrame):
    def __init__(self, title, message, accent):
        super().__init__()
        self.setObjectName("emptyStateCard")
        self.setFrameShape(STYLED_PANEL)
        self.setStyleSheet(f"""
            QFrame#emptyStateCard {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 2px dashed rgba(214, 247, 222, 0.36);
                border-left: 10px solid {accent};
                border-radius: 18px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("DejaVu Sans", 18, FONT_BOLD))
        title_lbl.setStyleSheet("color: #ffffff;")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        message_lbl = QLabel(message)
        message_lbl.setFont(QFont("DejaVu Sans", 14, FONT_DEMIBOLD))
        message_lbl.setStyleSheet("color: #d9f5df;")
        message_lbl.setWordWrap(True)
        layout.addWidget(message_lbl)


class PiDisplay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Department Noticeboard")
        self.showFullScreen()
        self.server_url = os.environ.get("NOTICEBOARD_API_URL", "http://127.0.0.1:5000/api")
        self.scroll_states = {}
        self.pi_settings = DEFAULT_PI_SETTINGS.copy()
        self.alerted_task_ids = set()
        self.popup_queue = []
        self.active_popup_task_id = None

        self.init_ui()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(self.pi_settings["pi_refresh_interval_seconds"] * 1000)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        self.auto_scroll_timer = QTimer(self)
        self.auto_scroll_timer.timeout.connect(self.advance_auto_scroll)
        self.auto_scroll_timer.start(80)

        self.popup_hide_timer = QTimer(self)
        self.popup_hide_timer.setSingleShot(True)
        self.popup_hide_timer.timeout.connect(self.hide_current_popup)

        self.refresh_data()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        self.setAutoFillBackground(True)

        palette = self.palette()
        gradient = QLinearGradient(0, 0, 0, 900)
        gradient.setColorAt(0.0, QColor("#56d37f"))
        gradient.setColorAt(0.38, QColor("#157c4f"))
        gradient.setColorAt(0.72, QColor("#0d5a38"))
        gradient.setColorAt(1.0, QColor("#042515"))
        palette.setBrush(PALETTE_WINDOW, QBrush(gradient))
        self.setPalette(palette)

        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(24, 20, 24, 24)
        self.main_layout.setSpacing(16)

        header_frame = QFrame()
        header_frame.setObjectName("headerPanel")
        header_frame.setStyleSheet("""
            QFrame#headerPanel {
                background-color: rgba(4, 28, 16, 0.36);
                border: 2px solid rgba(221, 248, 228, 0.16);
                border-radius: 24px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)

        header = QHBoxLayout(header_frame)
        header.setContentsMargins(22, 16, 22, 16)
        header.setSpacing(18)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(6)

        self.title_label = QLabel("DEPARTMENT NOTICEBOARD")
        self.title_label.setFont(QFont("DejaVu Sans", 38, FONT_BOLD))
        self.title_label.setStyleSheet("color: white;")
        title_stack.addWidget(self.title_label)

        self.subtitle_label = QLabel("GREEN ROOM VIEW FOR LIVE NOTICES AND TASKS")
        self.subtitle_label.setFont(QFont("DejaVu Sans", 14, FONT_DEMIBOLD))
        self.subtitle_label.setStyleSheet("color: #d8f3de;")
        title_stack.addWidget(self.subtitle_label)

        self.status_label = QLabel()
        self.status_label.setAlignment(ALIGN_CENTER)
        self.status_label.setMinimumWidth(144)
        self.status_label.setFont(QFont("DejaVu Sans", 11, FONT_BOLD))
        title_stack.addWidget(self.status_label, 0, ALIGN_TOP)

        header.addLayout(title_stack, 1)
        header.addStretch()

        clock_panel = QFrame()
        clock_panel.setObjectName("clockPanel")
        clock_panel.setStyleSheet("""
            QFrame#clockPanel {
                background-color: rgba(255, 255, 255, 0.14);
                border: 2px solid rgba(222, 248, 228, 0.18);
                border-radius: 18px;
            }
        """)

        clock_layout = QVBoxLayout(clock_panel)
        clock_layout.setContentsMargins(16, 12, 16, 12)

        self.clock_label = QLabel()
        self.clock_label.setAlignment(ALIGN_CENTER)
        self.clock_label.setFont(QFont("DejaVu Sans", 24, FONT_BOLD))
        self.clock_label.setStyleSheet("color: #ffffff;")
        clock_layout.addWidget(self.clock_label)

        header.addWidget(clock_panel)
        self.main_layout.addWidget(header_frame)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        notices_panel, self.notices_area, self.notices_layout, self.notices_count_label = self.create_section_panel(
            "NOTICES", "#2bbf6c"
        )
        tasks_panel, self.tasks_area, self.tasks_layout, self.tasks_count_label = self.create_section_panel(
            "TASKS", "#1f9a57"
        )

        content_layout.addWidget(notices_panel, 1)
        content_layout.addWidget(tasks_panel, 1)
        self.main_layout.addLayout(content_layout)

        self.scroll_states = {
            "notices": {"area": self.notices_area, "pause_ticks": self.pause_ticks_for(2), "at_bottom": False},
            "tasks": {"area": self.tasks_area, "pause_ticks": self.pause_ticks_for(2), "at_bottom": False},
        }

        self.build_popup_frame()
        self.set_connection_status("SYNCING", "#d7ac45")
        self.show_placeholder_cards()

    def build_popup_frame(self):
        self.popup_frame = QFrame(self.centralWidget())
        self.popup_frame.setObjectName("timerPopup")
        self.popup_frame.setAttribute(WA_TRANSPARENT, True)
        self.popup_frame.setStyleSheet("""
            QFrame#timerPopup {
                background-color: rgba(28, 6, 6, 0.92);
                border: 3px solid #f0625f;
                border-radius: 24px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        popup_layout = QVBoxLayout(self.popup_frame)
        popup_layout.setContentsMargins(24, 22, 24, 22)
        popup_layout.setSpacing(10)

        popup_heading = QLabel("TIMER ELAPSED")
        popup_heading.setFont(QFont("DejaVu Sans", 24, FONT_BOLD))
        popup_heading.setStyleSheet("color: #ffd6d1;")
        popup_layout.addWidget(popup_heading)

        self.popup_title_label = QLabel("")
        self.popup_title_label.setWordWrap(True)
        self.popup_title_label.setFont(QFont("DejaVu Sans", 28, FONT_BOLD))
        self.popup_title_label.setStyleSheet("color: white;")
        popup_layout.addWidget(self.popup_title_label)

        self.popup_assignee_label = QLabel("")
        self.popup_assignee_label.setFont(QFont("DejaVu Sans", 16, FONT_DEMIBOLD))
        self.popup_assignee_label.setStyleSheet("color: #ffe8e5;")
        popup_layout.addWidget(self.popup_assignee_label)

        self.popup_due_label = QLabel("")
        self.popup_due_label.setFont(QFont("DejaVu Sans", 15, FONT_DEMIBOLD))
        self.popup_due_label.setStyleSheet("color: #ffd7d3;")
        popup_layout.addWidget(self.popup_due_label)
        self.popup_frame.hide()

    def update_clock(self):
        self.clock_label.setText(QDateTime.currentDateTime().toString("h:mm:ss AP | ddd, MMM d"))

    def create_section_panel(self, title, accent):
        section_frame = QFrame()
        section_frame.setObjectName("sectionPanel")
        section_frame.setStyleSheet("""
            QFrame#sectionPanel {
                background-color: rgba(4, 27, 16, 0.34);
                border: 2px solid rgba(220, 247, 227, 0.14);
                border-radius: 24px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.08);
                width: 10px;
                margin: 4px 0 4px 0;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(189, 239, 198, 0.7);
                border-radius: 5px;
                min-height: 40px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        outer_layout = QVBoxLayout(section_frame)
        outer_layout.setContentsMargins(16, 14, 16, 16)
        outer_layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        title_label = QLabel(title)
        title_label.setFont(QFont("DejaVu Sans", 22, FONT_BOLD))
        title_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                background-color: {accent};
                border-radius: 14px;
                padding: 7px 16px;
            }}
        """)
        title_row.addWidget(title_label)
        title_row.addStretch()

        count_label = QLabel("0")
        count_label.setAlignment(ALIGN_CENTER)
        count_label.setMinimumWidth(44)
        count_label.setFont(QFont("DejaVu Sans", 14, FONT_BOLD))
        count_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.14);
                border: 2px solid rgba(220, 247, 227, 0.18);
                border-radius: 14px;
                padding: 6px 10px;
            }
        """)
        title_row.addWidget(count_label)
        outer_layout.addLayout(title_row)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 2, 0, 2)
        container_layout.setSpacing(12)
        container_layout.setAlignment(ALIGN_TOP)

        scroll_area.setWidget(container)
        outer_layout.addWidget(scroll_area)

        return section_frame, scroll_area, container_layout, count_label

    def set_connection_status(self, text, accent):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: #ffffff;
                background-color: {accent};
                border-radius: 14px;
                padding: 6px 12px;
            }}
        """)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def show_placeholder_cards(self):
        self.render_notices([])
        self.render_tasks([])

    def pause_ticks_for(self, seconds):
        interval = max(1, self.auto_scroll_timer.interval() if hasattr(self, "auto_scroll_timer") else 80)
        return max(1, int((seconds * 1000) / interval))

    def apply_pi_settings(self, settings):
        merged = DEFAULT_PI_SETTINGS.copy()
        merged.update(settings or {})
        self.pi_settings = merged

        refresh_interval_ms = max(1000, int(self.pi_settings["pi_refresh_interval_seconds"]) * 1000)
        if self.refresh_timer.interval() != refresh_interval_ms:
            self.refresh_timer.setInterval(refresh_interval_ms)

        if not self.pi_settings["pi_timer_popup_enabled"]:
            self.popup_queue.clear()
            self.active_popup_task_id = None
            self.popup_hide_timer.stop()
            self.popup_frame.hide()

    def fetch_remote_settings(self):
        try:
            response = requests.get(f"{self.server_url}/settings", timeout=2)
        except requests.RequestException:
            return DEFAULT_PI_SETTINGS.copy()

        if response.status_code != 200:
            return DEFAULT_PI_SETTINGS.copy()

        payload = response.json()
        if not isinstance(payload, dict):
            return DEFAULT_PI_SETTINGS.copy()

        settings = DEFAULT_PI_SETTINGS.copy()
        settings.update(payload)
        return settings

    def reset_scroll_area(self, name):
        state = self.scroll_states.get(name)
        if not state:
            return

        scrollbar = state["area"].verticalScrollBar()
        scrollbar.setValue(0)
        state["pause_ticks"] = self.pause_ticks_for(self.pi_settings["pi_scroll_pause_seconds"])
        state["at_bottom"] = False

    def queue_scroll_reset(self, name):
        QTimer.singleShot(0, lambda key=name: self.reset_scroll_area(key))

    def advance_auto_scroll(self):
        pause_seconds = self.pi_settings["pi_scroll_pause_seconds"]
        scroll_step = self.pi_settings["pi_scroll_step"]

        for state in self.scroll_states.values():
            scrollbar = state["area"].verticalScrollBar()
            maximum = scrollbar.maximum()

            if maximum <= 0:
                if scrollbar.value() != 0:
                    scrollbar.setValue(0)
                state["pause_ticks"] = self.pause_ticks_for(pause_seconds)
                state["at_bottom"] = False
                continue

            if state["pause_ticks"] > 0:
                state["pause_ticks"] -= 1
                continue

            if state["at_bottom"]:
                scrollbar.setValue(0)
                state["at_bottom"] = False
                state["pause_ticks"] = self.pause_ticks_for(pause_seconds)
                continue

            next_value = min(maximum, scrollbar.value() + scroll_step)
            scrollbar.setValue(next_value)

            if next_value >= maximum:
                state["at_bottom"] = True
                state["pause_ticks"] = self.pause_ticks_for(pause_seconds * 2)

    def render_notices(self, notices):
        self.clear_layout(self.notices_layout)
        self.notices_count_label.setText(str(len(notices)))

        if notices:
            for notice in notices:
                card = Card(notice["title"], notice["content"], notice["priority"], type="notice")
                self.notices_layout.addWidget(card)
        else:
            self.notices_layout.addWidget(
                EmptyStateCard(
                    "No notices right now",
                    "New notices will appear here automatically as soon as they are added.",
                    "#2bbf6c",
                )
            )

        self.notices_layout.addStretch(1)
        self.queue_scroll_reset("notices")

    def render_tasks(self, tasks):
        self.clear_layout(self.tasks_layout)
        self.tasks_count_label.setText(str(len(tasks)))

        if tasks:
            for task in tasks:
                card = Card(
                    task["title"],
                    "",
                    task["priority"],
                    type="task",
                    assignee=task.get("assignee"),
                    due_text=task.get("due_time"),
                    timer_label=task.get("timer_label"),
                    timer_elapsed=task.get("timer_elapsed", False),
                )
                self.tasks_layout.addWidget(card)
        else:
            self.tasks_layout.addWidget(
                EmptyStateCard(
                    "No tasks queued",
                    "Tasks assigned from the manager app will show here automatically.",
                    "#1f9a57",
                )
            )

        self.tasks_layout.addStretch(1)
        self.queue_scroll_reset("tasks")

    def play_timer_sound(self):
        if not self.pi_settings["pi_timer_sound_enabled"]:
            return

        return self.play_fallback_alert_sound()

    def build_spoken_alert(self, task):
        assignee = (task.get("assignee") or "Team").strip()
        title = (task.get("title") or "this task").strip()
        return f"{assignee}, your time for {title} has elapsed."

    def speak_text(self, text):
        voice = str(self.pi_settings.get("pi_timer_voice") or DEFAULT_PI_SETTINGS["pi_timer_voice"]).strip()
        speech_rate = int(self.pi_settings.get("pi_timer_speech_rate") or DEFAULT_PI_SETTINGS["pi_timer_speech_rate"])
        delayed_ssml = f"<speak><break time='{VOICE_START_DELAY_MS}ms'/>{html_escape(text)}</speak>"
        speech_commands = [
            ["espeak-ng", "-m", "-v", voice, "-s", str(speech_rate), "-a", "170", delayed_ssml],
            ["espeak", "-m", "-v", voice, "-s", str(speech_rate), "-a", "170", delayed_ssml],
            ["spd-say", text],
        ]

        for command in speech_commands:
            command_path = shutil.which(command[0])
            if not command_path:
                continue
            try:
                subprocess.Popen(
                    [command_path, *command[1:]],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                continue

        return False

    def play_fallback_alert_sound(self):
        sound_options = [
            ("paplay", "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"),
            ("aplay", "/usr/share/sounds/alsa/Front_Center.wav"),
        ]

        for player, sound_file in sound_options:
            player_path = shutil.which(player)
            if not player_path or not os.path.exists(sound_file):
                continue
            try:
                subprocess.Popen(
                    [player_path, sound_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except Exception:
                continue

        QApplication.beep()
        return False

    def announce_elapsed_task(self, task):
        if not self.pi_settings["pi_timer_sound_enabled"]:
            return

        message = self.build_spoken_alert(task)
        if self.speak_text(message):
            return

        self.play_fallback_alert_sound()

    def enqueue_popup(self, task):
        task_id = task["id"]
        if task_id == self.active_popup_task_id:
            return
        if any(queued_task["id"] == task_id for queued_task in self.popup_queue):
            return

        self.popup_queue.append(task)
        if not self.popup_frame.isVisible():
            self.show_next_popup()

    def show_next_popup(self):
        if not self.pi_settings["pi_timer_popup_enabled"]:
            self.popup_queue.clear()
            self.active_popup_task_id = None
            self.popup_frame.hide()
            return

        if not self.popup_queue:
            self.active_popup_task_id = None
            self.popup_frame.hide()
            return

        task = self.popup_queue.pop(0)
        self.active_popup_task_id = task["id"]
        self.popup_title_label.setText(task["title"])
        self.popup_assignee_label.setText(f"Assignee: {task.get('assignee') or 'Unassigned'}")
        due_text = task.get("due_time") or "No due note"
        self.popup_due_label.setText(f"Due: {due_text}")
        self.position_popup()
        self.popup_frame.show()
        self.popup_frame.raise_()
        self.announce_elapsed_task(task)
        self.popup_hide_timer.start(int(self.pi_settings["pi_timer_popup_duration_seconds"]) * 1000)

    def hide_current_popup(self):
        self.popup_frame.hide()
        self.active_popup_task_id = None
        if self.popup_queue:
            self.show_next_popup()

    def position_popup(self):
        if not hasattr(self, "popup_frame"):
            return

        parent = self.centralWidget()
        available_width = max(360, parent.width() - 80)
        popup_width = min(760, available_width)
        self.popup_frame.setFixedWidth(popup_width)
        height = self.popup_frame.sizeHint().height()
        x = max(20, (parent.width() - popup_width) // 2)
        y = max(90, (parent.height() - height) // 4)
        self.popup_frame.setGeometry(x, y, popup_width, height)

    def process_elapsed_tasks(self, tasks):
        elapsed_tasks = [task for task in tasks if task.get("timer_elapsed")]
        elapsed_ids = {task["id"] for task in elapsed_tasks}
        self.alerted_task_ids.intersection_update(elapsed_ids)

        new_elapsed_tasks = [task for task in elapsed_tasks if task["id"] not in self.alerted_task_ids]
        if not new_elapsed_tasks:
            return

        for task in new_elapsed_tasks:
            self.alerted_task_ids.add(task["id"])

        if self.pi_settings["pi_timer_popup_enabled"]:
            for task in new_elapsed_tasks:
                self.enqueue_popup(task)
            return

        if self.pi_settings["pi_timer_sound_enabled"]:
            for task in new_elapsed_tasks:
                self.announce_elapsed_task(task)

    def refresh_data(self):
        try:
            self.apply_pi_settings(self.fetch_remote_settings())

            notices_response = requests.get(f"{self.server_url}/notices", timeout=2)
            tasks_response = requests.get(f"{self.server_url}/tasks", timeout=2)

            notices_ok = notices_response.status_code == 200
            tasks_ok = tasks_response.status_code == 200

            if notices_ok:
                self.render_notices(notices_response.json())
            if tasks_ok:
                tasks = tasks_response.json()
                self.render_tasks(tasks)
                self.process_elapsed_tasks(tasks)

            if notices_ok and tasks_ok:
                self.set_connection_status("LIVE", "#1f9a57")
            elif notices_ok or tasks_ok:
                self.set_connection_status("PARTIAL UPDATE", "#d7ac45")
            else:
                self.set_connection_status("SERVER ERROR", "#b94f3e")
        except Exception as error:
            self.set_connection_status("OFFLINE", "#b94f3e")
            print(f"Refresh error: {error}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_popup()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PiDisplay()
    window.show()
    if hasattr(app, "exec"):
        sys.exit(app.exec())
    sys.exit(app.exec_())
