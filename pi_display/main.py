import os
import sys

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

if QT6:
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
    ALIGN_TOP = Qt.AlignmentFlag.AlignTop
    FONT_BOLD = QFont.Weight.Bold
    FONT_DEMIBOLD = QFont.Weight.DemiBold
    PALETTE_WINDOW = QPalette.ColorRole.Window
    STYLED_PANEL = QFrame.Shape.StyledPanel
else:
    ALIGN_CENTER = Qt.AlignCenter
    ALIGN_TOP = Qt.AlignTop
    FONT_BOLD = QFont.Bold
    FONT_DEMIBOLD = QFont.DemiBold
    PALETTE_WINDOW = QPalette.Window
    STYLED_PANEL = QFrame.StyledPanel


class Card(QFrame):
    def __init__(self, title, content, priority, type="notice", assignee=None, time=None):
        super().__init__()
        self.setObjectName("noticeCard")
        self.setFrameShape(STYLED_PANEL)

        priority_styles = {
            "High": {"accent": "#ff6154", "border": "#ffd7d3"},
            "Medium": {"accent": "#ffb340", "border": "#ffe4b3"},
            "Low": {"accent": "#45c2ff", "border": "#c7ebff"},
        }
        style = priority_styles.get(priority, priority_styles["Low"])

        self.setStyleSheet(f"""
            QFrame#noticeCard {{
                background-color: rgba(250, 252, 255, 248);
                border: 3px solid {style["border"]};
                border-left: 14px solid {style["accent"]};
                border-radius: 24px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("DejaVu Sans", 24, FONT_BOLD))
        title_lbl.setStyleSheet("color: #10213d;")
        title_lbl.setWordWrap(True)
        top_row.addWidget(title_lbl, 1)

        priority_lbl = QLabel(priority.upper())
        priority_lbl.setAlignment(ALIGN_CENTER)
        priority_lbl.setMinimumWidth(122)
        priority_lbl.setFont(QFont("DejaVu Sans", 14, FONT_BOLD))
        priority_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {style["accent"]};
                color: white;
                border-radius: 16px;
                padding: 8px 14px;
            }}
        """)
        top_row.addWidget(priority_lbl)
        layout.addLayout(top_row)

        if type == "notice":
            content_lbl = QLabel(content)
            content_lbl.setFont(QFont("DejaVu Sans", 20, FONT_DEMIBOLD))
            content_lbl.setStyleSheet("color: #263b59; line-height: 1.35;")
            content_lbl.setWordWrap(True)
            layout.addWidget(content_lbl)
        else:
            info_layout = QHBoxLayout()
            info_layout.setSpacing(16)

            assignee_text = assignee or "Unassigned"
            due_text = time or "No due time"

            person_lbl = QLabel(f"ASSIGNEE  {assignee_text}")
            person_lbl.setFont(QFont("DejaVu Sans", 16, FONT_BOLD))
            person_lbl.setStyleSheet("""
                color: #153359;
                background-color: #e8f2ff;
                border-radius: 16px;
                padding: 10px 14px;
            """)

            time_lbl = QLabel(f"DUE  {due_text}")
            time_lbl.setFont(QFont("DejaVu Sans", 16, FONT_BOLD))
            time_lbl.setStyleSheet("""
                color: #153359;
                background-color: #eef8f1;
                border-radius: 16px;
                padding: 10px 14px;
            """)

            info_layout.addWidget(person_lbl)
            info_layout.addStretch()
            info_layout.addWidget(time_lbl)
            layout.addLayout(info_layout)


class EmptyStateCard(QFrame):
    def __init__(self, title, message, accent):
        super().__init__()
        self.setObjectName("emptyStateCard")
        self.setFrameShape(STYLED_PANEL)
        self.setStyleSheet(f"""
            QFrame#emptyStateCard {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 3px dashed rgba(255, 255, 255, 0.24);
                border-left: 12px solid {accent};
                border-radius: 24px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(10)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("DejaVu Sans", 22, FONT_BOLD))
        title_lbl.setStyleSheet("color: #ffffff;")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        message_lbl = QLabel(message)
        message_lbl.setFont(QFont("DejaVu Sans", 17, FONT_DEMIBOLD))
        message_lbl.setStyleSheet("color: #d8e9ff; line-height: 1.35;")
        message_lbl.setWordWrap(True)
        layout.addWidget(message_lbl)


class PiDisplay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Department Noticeboard")
        self.showFullScreen()
        self.server_url = os.environ.get("NOTICEBOARD_API_URL", "http://127.0.0.1:5000/api")

        self.init_ui()

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(10000)

        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        self.refresh_data()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        self.setAutoFillBackground(True)

        palette = self.palette()
        gradient = QLinearGradient(0, 0, 0, 900)
        gradient.setColorAt(0.0, QColor("#2d78d2"))
        gradient.setColorAt(0.38, QColor("#103e82"))
        gradient.setColorAt(1.0, QColor("#08162d"))
        palette.setBrush(PALETTE_WINDOW, QBrush(gradient))
        self.setPalette(palette)

        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(38, 32, 38, 38)
        self.main_layout.setSpacing(24)

        header_frame = QFrame()
        header_frame.setObjectName("headerPanel")
        header_frame.setStyleSheet("""
            QFrame#headerPanel {
                background-color: rgba(5, 20, 43, 0.38);
                border: 2px solid rgba(255, 255, 255, 0.16);
                border-radius: 30px;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)

        header = QHBoxLayout(header_frame)
        header.setContentsMargins(28, 22, 28, 22)
        header.setSpacing(24)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(8)

        self.title_label = QLabel("DEPARTMENT NOTICEBOARD")
        self.title_label.setFont(QFont("DejaVu Sans", 48, FONT_BOLD))
        self.title_label.setStyleSheet("color: white;")
        title_stack.addWidget(self.title_label)

        self.subtitle_label = QLabel("LIVE UPDATES FOR NOTICES AND TASKS")
        self.subtitle_label.setFont(QFont("DejaVu Sans", 18, FONT_DEMIBOLD))
        self.subtitle_label.setStyleSheet("color: #d7ebff;")
        title_stack.addWidget(self.subtitle_label)

        self.status_label = QLabel()
        self.status_label.setAlignment(ALIGN_CENTER)
        self.status_label.setMinimumWidth(170)
        self.status_label.setFont(QFont("DejaVu Sans", 14, FONT_BOLD))
        title_stack.addWidget(self.status_label, 0, ALIGN_TOP)

        header.addLayout(title_stack, 1)
        header.addStretch()

        clock_panel = QFrame()
        clock_panel.setObjectName("clockPanel")
        clock_panel.setStyleSheet("""
            QFrame#clockPanel {
                background-color: rgba(255, 255, 255, 0.14);
                border: 2px solid rgba(255, 255, 255, 0.18);
                border-radius: 24px;
            }
        """)

        clock_layout = QVBoxLayout(clock_panel)
        clock_layout.setContentsMargins(20, 16, 20, 16)

        self.clock_label = QLabel()
        self.clock_label.setAlignment(ALIGN_CENTER)
        self.clock_label.setFont(QFont("DejaVu Sans", 32, FONT_BOLD))
        self.clock_label.setStyleSheet("color: #ffffff;")
        clock_layout.addWidget(self.clock_label)

        header.addWidget(clock_panel)
        self.main_layout.addWidget(header_frame)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(24)

        notices_panel, self.notices_layout, self.notices_count_label = self.create_section_panel(
            "NOTICES", "#49c2ff"
        )
        tasks_panel, self.tasks_layout, self.tasks_count_label = self.create_section_panel(
            "TASKS", "#65e886"
        )

        content_layout.addWidget(notices_panel, 1)
        content_layout.addWidget(tasks_panel, 1)
        self.main_layout.addLayout(content_layout)

        self.set_connection_status("SYNCING", "#ffbf47")
        self.show_placeholder_cards()

    def update_clock(self):
        self.clock_label.setText(QDateTime.currentDateTime().toString("h:mm:ss AP | ddd, MMM d"))

    def create_section_panel(self, title, accent):
        section_frame = QFrame()
        section_frame.setObjectName("sectionPanel")
        section_frame.setStyleSheet("""
            QFrame#sectionPanel {
                background-color: rgba(6, 22, 46, 0.34);
                border: 2px solid rgba(255, 255, 255, 0.14);
                border-radius: 30px;
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
                background: transparent;
                width: 12px;
                margin: 8px 0 8px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.28);
                border-radius: 6px;
                min-height: 48px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        outer_layout = QVBoxLayout(section_frame)
        outer_layout.setContentsMargins(22, 20, 22, 22)
        outer_layout.setSpacing(16)

        title_row = QHBoxLayout()
        title_row.setSpacing(14)

        title_label = QLabel(title)
        title_label.setFont(QFont("DejaVu Sans", 26, FONT_BOLD))
        title_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                background-color: {accent};
                border-radius: 18px;
                padding: 8px 18px;
            }}
        """)
        title_row.addWidget(title_label)
        title_row.addStretch()

        count_label = QLabel("0")
        count_label.setAlignment(ALIGN_CENTER)
        count_label.setMinimumWidth(54)
        count_label.setFont(QFont("DejaVu Sans", 16, FONT_BOLD))
        count_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.14);
                border: 2px solid rgba(255, 255, 255, 0.18);
                border-radius: 16px;
                padding: 7px 12px;
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
        container_layout.setContentsMargins(0, 4, 0, 4)
        container_layout.setSpacing(16)
        container_layout.setAlignment(ALIGN_TOP)

        scroll_area.setWidget(container)
        outer_layout.addWidget(scroll_area)

        return section_frame, container_layout, count_label

    def set_connection_status(self, text, accent):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: #ffffff;
                background-color: {accent};
                border-radius: 16px;
                padding: 8px 16px;
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
                    "#49c2ff",
                )
            )

        self.notices_layout.addStretch(1)

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
                    assignee=task["assignee"],
                    time=task["due_time"],
                )
                self.tasks_layout.addWidget(card)
        else:
            self.tasks_layout.addWidget(
                EmptyStateCard(
                    "No tasks queued",
                    "Tasks assigned from the manager app will show here in large, easy-to-read cards.",
                    "#65e886",
                )
            )

        self.tasks_layout.addStretch(1)

    def refresh_data(self):
        try:
            notices_response = requests.get(f"{self.server_url}/notices", timeout=2)
            tasks_response = requests.get(f"{self.server_url}/tasks", timeout=2)

            notices_ok = notices_response.status_code == 200
            tasks_ok = tasks_response.status_code == 200

            if notices_ok:
                self.render_notices(notices_response.json())
            if tasks_ok:
                self.render_tasks(tasks_response.json())

            if notices_ok and tasks_ok:
                self.set_connection_status("LIVE", "#2ecc71")
            elif notices_ok or tasks_ok:
                self.set_connection_status("PARTIAL UPDATE", "#ffbf47")
            else:
                self.set_connection_status("SERVER ERROR", "#ff6154")
        except Exception as error:
            self.set_connection_status("OFFLINE", "#ff6154")
            print(f"Refresh error: {error}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PiDisplay()
    window.show()
    if hasattr(app, "exec"):
        sys.exit(app.exec())
    sys.exit(app.exec_())
