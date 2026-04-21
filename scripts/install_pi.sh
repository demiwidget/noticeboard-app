#!/usr/bin/env bash
set -Eeuo pipefail

log() {
    printf '\n[noticeboard] %s\n' "$*"
}

fail() {
    printf '\n[noticeboard] ERROR: %s\n' "$*" >&2
    exit 1
}

if ! command -v apt-get >/dev/null 2>&1; then
    fail "This installer is intended for Raspberry Pi OS or another Debian-based system."
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$APP_DIR/backend"
DISPLAY_DIR="$APP_DIR/pi_display"
PYTHON_BIN="/usr/bin/python3"

if [[ ! -f "$BACKEND_DIR/app.py" || ! -f "$DISPLAY_DIR/main.py" ]]; then
    fail "Cannot find backend/app.py and pi_display/main.py. Run this from the repository's scripts directory."
fi

chmod +x "$SCRIPT_DIR/update_pi.sh"

if [[ -n "${NOTICEBOARD_APP_USER:-}" ]]; then
    APP_USER="$NOTICEBOARD_APP_USER"
elif [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]]; then
    APP_USER="$SUDO_USER"
else
    APP_USER="$(id -un)"
fi

APP_HOME="$(getent passwd "$APP_USER" | cut -d: -f6)"
APP_UID="$(id -u "$APP_USER")"

if [[ -z "$APP_HOME" || ! -d "$APP_HOME" ]]; then
    fail "Could not determine the home directory for user '$APP_USER'."
fi

if [[ "$(id -u)" -eq 0 ]]; then
    SUDO=()
else
    SUDO=(sudo)
fi

log "Installing Noticeboard from: $APP_DIR"
log "Services will run as user: $APP_USER"

BASE_PACKAGES=(
    git
    python3
    python3-flask
    python3-flask-sqlalchemy
    python3-flask-cors
    python3-requests
)

QT_PLATFORM="xcb"
QT_PACKAGES=()
OPTIONAL_QT_PACKAGES=()

if apt-cache show python3-pyqt6 >/dev/null 2>&1; then
    QT_PACKAGES+=(python3-pyqt6)
    QT_PLATFORM="wayland;xcb"
    if apt-cache show qt6-wayland >/dev/null 2>&1; then
        OPTIONAL_QT_PACKAGES+=(qt6-wayland)
    fi
elif apt-cache show python3-pyqt5 >/dev/null 2>&1; then
    QT_PACKAGES+=(python3-pyqt5)
    QT_PLATFORM="xcb"
    if apt-cache show qtwayland5 >/dev/null 2>&1; then
        OPTIONAL_QT_PACKAGES+=(qtwayland5)
    fi
else
    fail "Could not find python3-pyqt6 or python3-pyqt5 in apt. Use Raspberry Pi OS Bookworm/Bullseye with Desktop enabled."
fi

if [[ "${NOTICEBOARD_SKIP_APT:-0}" != "1" ]]; then
    log "Updating package lists..."
    "${SUDO[@]}" apt-get update

    log "Installing Python and Qt packages from apt..."
    "${SUDO[@]}" apt-get install -y "${BASE_PACKAGES[@]}" "${QT_PACKAGES[@]}" "${OPTIONAL_QT_PACKAGES[@]}"
else
    log "Skipping apt package installation because NOTICEBOARD_SKIP_APT=1"
fi

log "Writing updater environment..."
"${SUDO[@]}" tee /etc/default/noticeboard >/dev/null <<ENVFILE
NOTICEBOARD_APP_DIR=$APP_DIR
NOTICEBOARD_APP_USER=$APP_USER
ENVFILE

log "Writing systemd services with the detected user and project path..."
"${SUDO[@]}" tee /etc/systemd/system/noticeboard-backend.service >/dev/null <<SERVICE
[Unit]
Description=Noticeboard Backend API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$BACKEND_DIR
Environment=NOTICEBOARD_HOST=0.0.0.0
Environment=NOTICEBOARD_PORT=5000
ExecStart=$PYTHON_BIN "$BACKEND_DIR/app.py"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

"${SUDO[@]}" tee /etc/systemd/system/noticeboard-display.service >/dev/null <<SERVICE
[Unit]
Description=Noticeboard Display Client
After=graphical.target noticeboard-backend.service
Wants=noticeboard-backend.service

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$DISPLAY_DIR
Environment=DISPLAY=:0
Environment=XAUTHORITY=$APP_HOME/.Xauthority
Environment=XDG_RUNTIME_DIR=/run/user/$APP_UID
Environment=WAYLAND_DISPLAY=wayland-0
Environment="QT_QPA_PLATFORM=$QT_PLATFORM"
Environment=NOTICEBOARD_API_URL=http://127.0.0.1:5000/api
ExecStart=$PYTHON_BIN "$DISPLAY_DIR/main.py"
Restart=always
RestartSec=10

[Install]
WantedBy=graphical.target
SERVICE

"${SUDO[@]}" tee /etc/systemd/system/noticeboard-update.service >/dev/null <<SERVICE
[Unit]
Description=Noticeboard Auto Update
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/default/noticeboard
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/env bash $APP_DIR/scripts/update_pi.sh --scheduled
SERVICE

"${SUDO[@]}" tee /etc/systemd/system/noticeboard-update.timer >/dev/null <<SERVICE
[Unit]
Description=Run Noticeboard Auto Update Regularly

[Timer]
OnBootSec=10min
OnUnitActiveSec=6h
RandomizedDelaySec=15min
Persistent=true
Unit=noticeboard-update.service

[Install]
WantedBy=timers.target
SERVICE

log "Enabling and starting services..."
"${SUDO[@]}" systemctl daemon-reload
"${SUDO[@]}" systemctl enable noticeboard-backend.service
"${SUDO[@]}" systemctl enable noticeboard-display.service
"${SUDO[@]}" systemctl enable noticeboard-update.timer
"${SUDO[@]}" systemctl start noticeboard-update.timer
"${SUDO[@]}" systemctl restart noticeboard-backend.service

if ! "${SUDO[@]}" systemctl restart noticeboard-display.service; then
    log "The backend was installed, but the display service did not start yet."
    log "This usually means the Raspberry Pi desktop session is not running or auto-login is disabled."
fi

log "Installation complete."
log "Check the backend with: curl http://localhost:5000/api/notices"
log "Check logs with: sudo journalctl -u noticeboard-backend -u noticeboard-display -f"
log "Manual update: $APP_DIR/scripts/update_pi.sh"
