import os
import shutil
import subprocess
from datetime import datetime, timedelta
from html import escape as html_escape

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

app = Flask(__name__)
CORS(app)

db_path = os.path.join(os.path.dirname(__file__), "noticeboard.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

VOICE_START_DELAY_MS = 350

SETTING_DEFINITIONS = {
    "pi_timer_sound_enabled": {"type": "bool", "default": True},
    "pi_timer_popup_enabled": {"type": "bool", "default": True},
    "pi_timer_voice": {"type": "str", "default": "en-gb"},
    "pi_timer_speech_rate": {"type": "int", "default": 120, "min": 80, "max": 220},
    "pi_timer_popup_duration_seconds": {"type": "int", "default": 30, "min": 5, "max": 300},
    "pi_refresh_interval_seconds": {"type": "int", "default": 2, "min": 1, "max": 60},
    "pi_scroll_step": {"type": "int", "default": 2, "min": 1, "max": 10},
    "pi_scroll_pause_seconds": {"type": "int", "default": 2, "min": 1, "max": 30},
}


def format_duration(total_seconds):
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_optional_text(value):
    text_value = normalize_text(value)
    return text_value or None


def normalize_countdown_seconds(value):
    if value in (None, "", 0, "0"):
        return None

    try:
        countdown_seconds = int(value)
    except (TypeError, ValueError):
        return None

    if countdown_seconds <= 0:
        return None

    return countdown_seconds


def serialize_setting_value(key, value):
    setting_type = SETTING_DEFINITIONS[key]["type"]
    if setting_type == "bool":
        return "1" if value else "0"
    if setting_type == "str":
        return normalize_text(value)
    return str(int(value))


def deserialize_setting_value(key, raw_value):
    if raw_value is None:
        return SETTING_DEFINITIONS[key]["default"]

    setting_type = SETTING_DEFINITIONS[key]["type"]
    if setting_type == "bool":
        return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}
    if setting_type == "str":
        text_value = normalize_text(raw_value)
        return text_value or SETTING_DEFINITIONS[key]["default"]

    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return int(SETTING_DEFINITIONS[key]["default"])


def coerce_setting_value(key, value):
    definition = SETTING_DEFINITIONS[key]

    if definition["type"] == "bool":
        if isinstance(value, bool):
            return value
        text_value = str(value).strip().lower()
        if text_value in {"1", "true", "yes", "on"}:
            return True
        if text_value in {"0", "false", "no", "off"}:
            return False
        raise ValueError(f"{key} must be true or false.")

    if definition["type"] == "str":
        text_value = normalize_text(value)
        if not text_value:
            raise ValueError(f"{key} cannot be blank.")
        return text_value

    try:
        coerced_value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a whole number.") from None

    min_value = definition.get("min")
    max_value = definition.get("max")
    if min_value is not None and coerced_value < min_value:
        raise ValueError(f"{key} must be at least {min_value}.")
    if max_value is not None and coerced_value > max_value:
        raise ValueError(f"{key} must be at most {max_value}.")

    return coerced_value


def request_display_refresh():
    refresh_service = os.environ.get("NOTICEBOARD_REFRESH_SERVICE", "noticeboard-refresh.service")
    systemctl_bin = os.environ.get("NOTICEBOARD_SYSTEMCTL", "/usr/bin/systemctl")
    refresh_command = ["sudo", "-n", systemctl_bin, "start", refresh_service]

    try:
        subprocess.run(
            refresh_command,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError as exc:
        return jsonify({"error": f"Could not run refresh command: {exc}"}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timed out while starting the Pi refresh service."}), 500
    except subprocess.CalledProcessError as exc:
        error_message = (exc.stderr or exc.stdout or str(exc)).strip()
        return jsonify({"error": f"Could not start the Pi refresh service: {error_message}"}), 500

    return (
        jsonify({"message": "Pi display refresh requested. The Pi will pull updates if any are available."}),
        202,
    )


def start_speech_preview(voice, speech_rate, text):
    delayed_ssml = f"<speak><break time='{VOICE_START_DELAY_MS}ms'/>{html_escape(text)}</speak>"
    speech_commands = [
        ["espeak-ng", "-m", "-v", voice, "-s", str(speech_rate), "-a", "170", delayed_ssml],
        ["espeak", "-m", "-v", voice, "-s", str(speech_rate), "-a", "170", delayed_ssml],
        ["spd-say", text],
    ]
    last_error = None

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
            return None, os.path.basename(command_path)
        except OSError as exc:
            last_error = exc

    if last_error:
        return f"Could not start voice preview: {last_error}", None

    return "No supported speech engine is installed on the Pi.", None


class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default="Medium")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
        }


class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), unique=True, nullable=False)
    value = db.Column(db.String(120), nullable=False)


class Assignee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
        }


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    assignee = db.Column(db.String(50), nullable=False)
    due_time = db.Column(db.String(50))
    priority = db.Column(db.String(20), default="Medium")
    status = db.Column(db.String(20), default="Pending")
    countdown_seconds = db.Column(db.Integer)
    timer_end_at = db.Column(db.DateTime)

    def timer_snapshot(self):
        if not self.timer_end_at:
            return {
                "timer_elapsed": False,
                "timer_remaining_seconds": None,
                "timer_end_at": None,
                "timer_label": None,
            }

        remaining_seconds = int((self.timer_end_at - datetime.utcnow()).total_seconds())
        timer_elapsed = remaining_seconds <= 0

        if timer_elapsed:
            timer_remaining_seconds = 0
            timer_label = "TIMER ELAPSED"
        else:
            timer_remaining_seconds = remaining_seconds
            timer_label = f"TIMER {format_duration(timer_remaining_seconds)}"

        return {
            "timer_elapsed": timer_elapsed,
            "timer_remaining_seconds": timer_remaining_seconds,
            "timer_end_at": self.timer_end_at.isoformat(),
            "timer_label": timer_label,
        }

    def to_dict(self):
        snapshot = self.timer_snapshot()
        return {
            "id": self.id,
            "title": self.title,
            "assignee": self.assignee,
            "due_time": self.due_time,
            "priority": self.priority,
            "status": self.status,
            "countdown_seconds": self.countdown_seconds,
            **snapshot,
        }


def ensure_assignee(name):
    assignee_name = normalize_text(name)
    if not assignee_name:
        return None

    existing = Assignee.query.filter_by(name=assignee_name).first()
    if existing:
        return existing

    assignee = Assignee(name=assignee_name)
    db.session.add(assignee)
    db.session.flush()
    return assignee


def ensure_default_settings():
    for key, definition in SETTING_DEFINITIONS.items():
        existing = Setting.query.filter_by(key=key).first()
        if existing:
            continue
        db.session.add(Setting(key=key, value=serialize_setting_value(key, definition["default"])))


def get_settings_payload():
    records = {setting.key: setting.value for setting in Setting.query.all()}
    payload = {}
    for key, definition in SETTING_DEFINITIONS.items():
        payload[key] = deserialize_setting_value(key, records.get(key, definition["default"]))
    return payload


def set_setting_value(key, value):
    record = Setting.query.filter_by(key=key).first()
    if not record:
        record = Setting(key=key, value=serialize_setting_value(key, value))
        db.session.add(record)
        return
    record.value = serialize_setting_value(key, value)


def initialize_database():
    db.create_all()

    inspector = inspect(db.engine)
    task_columns = {column["name"] for column in inspector.get_columns("task")}
    pending_alters = []

    if "countdown_seconds" not in task_columns:
        pending_alters.append("ALTER TABLE task ADD COLUMN countdown_seconds INTEGER")
    if "timer_end_at" not in task_columns:
        pending_alters.append("ALTER TABLE task ADD COLUMN timer_end_at DATETIME")

    for statement in pending_alters:
        db.session.execute(text(statement))

    if pending_alters:
        db.session.commit()

    ensure_default_settings()

    task_assignees = db.session.execute(
        text("SELECT DISTINCT assignee FROM task WHERE assignee IS NOT NULL AND TRIM(assignee) != ''")
    ).fetchall()
    for row in task_assignees:
        ensure_assignee(row[0])

    db.session.commit()


@app.route("/api/notices", methods=["GET"])
def get_notices():
    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    return jsonify([notice.to_dict() for notice in notices])


@app.route("/api/notices", methods=["POST"])
def add_notice():
    data = request.json or {}
    title = normalize_text(data.get("title"))
    content = normalize_text(data.get("content"))

    if not title or not content:
        return jsonify({"error": "Title and content are required."}), 400

    new_notice = Notice(
        title=title,
        content=content,
        priority=normalize_text(data.get("priority")) or "Medium",
    )
    db.session.add(new_notice)
    db.session.commit()
    return jsonify(new_notice.to_dict()), 201


@app.route("/api/notices/<int:id>", methods=["DELETE"])
def delete_notice(id):
    notice = Notice.query.get_or_404(id)
    db.session.delete(notice)
    db.session.commit()
    return "", 204


@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify(get_settings_payload())


@app.route("/api/settings", methods=["PUT"])
def update_settings():
    data = request.json or {}
    unknown_keys = [key for key in data if key not in SETTING_DEFINITIONS]
    if unknown_keys:
        return jsonify({"error": f"Unknown setting(s): {', '.join(sorted(unknown_keys))}"}), 400

    try:
        coerced_values = {key: coerce_setting_value(key, value) for key, value in data.items()}
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    for key, value in coerced_values.items():
        set_setting_value(key, value)

    db.session.commit()
    return jsonify(get_settings_payload())


@app.route("/api/assignees", methods=["GET"])
def get_assignees():
    assignees = Assignee.query.order_by(Assignee.name.asc()).all()
    return jsonify([assignee.to_dict() for assignee in assignees])


@app.route("/api/assignees", methods=["POST"])
def add_assignee():
    data = request.json or {}
    name = normalize_text(data.get("name"))
    if not name:
        return jsonify({"error": "Assignee name is required."}), 400

    assignee = Assignee.query.filter_by(name=name).first()
    if assignee:
        return jsonify(assignee.to_dict()), 200

    assignee = Assignee(name=name)
    db.session.add(assignee)
    db.session.commit()
    return jsonify(assignee.to_dict()), 201


@app.route("/api/assignees/<int:id>", methods=["DELETE"])
def delete_assignee(id):
    assignee = Assignee.query.get_or_404(id)
    db.session.delete(assignee)
    db.session.commit()
    return "", 204


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    tasks = Task.query.order_by(Task.id.desc()).all()
    return jsonify([task.to_dict() for task in tasks])


@app.route("/api/tasks", methods=["POST"])
def add_task():
    data = request.json or {}
    title = normalize_text(data.get("title"))
    assignee_name = normalize_text(data.get("assignee"))

    if not title or not assignee_name:
        return jsonify({"error": "Title and assignee are required."}), 400

    countdown_seconds = normalize_countdown_seconds(data.get("countdown_seconds"))
    timer_end_at = None
    if countdown_seconds:
        timer_end_at = datetime.utcnow() + timedelta(seconds=countdown_seconds)

    new_task = Task(
        title=title,
        assignee=assignee_name,
        due_time=normalize_optional_text(data.get("due_time")),
        priority=normalize_text(data.get("priority")) or "Medium",
        countdown_seconds=countdown_seconds,
        timer_end_at=timer_end_at,
    )
    db.session.add(new_task)
    ensure_assignee(assignee_name)
    db.session.commit()
    return jsonify(new_task.to_dict()), 201


@app.route("/api/tasks/<int:id>", methods=["DELETE"])
def delete_task(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return "", 204


@app.route("/api/admin/restart-display", methods=["POST"])
def restart_display():
    return request_display_refresh()


@app.route("/api/admin/test-voice", methods=["POST"])
def test_voice():
    data = request.json or {}
    current_settings = get_settings_payload()

    try:
        voice = coerce_setting_value("pi_timer_voice", data.get("voice", current_settings["pi_timer_voice"]))
        speech_rate = coerce_setting_value(
            "pi_timer_speech_rate",
            data.get("speech_rate", current_settings["pi_timer_speech_rate"]),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    preview_text = normalize_text(data.get("text")) or "Hello team. This is a Noticeboard voice test."
    error_message, engine_name = start_speech_preview(voice, speech_rate, preview_text)
    if error_message:
        return jsonify({"error": error_message}), 500

    if engine_name in {"espeak-ng", "espeak"}:
        message = f"Voice test started on the Pi using {engine_name}."
    else:
        message = "Voice test started on the Pi."

    return jsonify({"message": message}), 202


if __name__ == "__main__":
    with app.app_context():
        initialize_database()

    host = os.environ.get("NOTICEBOARD_HOST", "0.0.0.0")
    port = int(os.environ.get("NOTICEBOARD_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug, use_reloader=False)
