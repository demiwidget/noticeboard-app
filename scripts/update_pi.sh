#!/usr/bin/env bash
set -Eeuo pipefail

log() {
    printf '\n[noticeboard-update] %s\n' "$*"
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
APP_USER="${NOTICEBOARD_APP_USER:-}"
LOCK_FILE="/tmp/noticeboard-update.lock"
DISPLAY_SERVICE="${NOTICEBOARD_DISPLAY_SERVICE:-noticeboard-display.service}"
SYSTEMCTL_BIN="${NOTICEBOARD_SYSTEMCTL:-$(command -v systemctl 2>/dev/null || true)}"
SCHEDULED_MODE=0
RESTART_DISPLAY_MODE=0

for arg in "$@"; do
    case "$arg" in
        --scheduled)
            SCHEDULED_MODE=1
            ;;
        --restart-display)
            RESTART_DISPLAY_MODE=1
            ;;
    esac
done

if [[ -z "$APP_USER" ]]; then
    if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]]; then
        APP_USER="$SUDO_USER"
    else
        APP_USER="$(stat -c '%U' "$APP_DIR")"
    fi
fi

run_git() {
    if [[ "$(id -u)" -eq 0 ]]; then
        runuser -u "$APP_USER" -- git -C "$APP_DIR" "$@"
    else
        git -C "$APP_DIR" "$@"
    fi
}

restart_display_service() {
    if [[ -z "$SYSTEMCTL_BIN" ]]; then
        log "Could not find systemctl; skipping display restart."
        return 1
    fi

    log "Restarting the Pi display service..."
    if [[ "$(id -u)" -eq 0 ]]; then
        "$SYSTEMCTL_BIN" restart "$DISPLAY_SERVICE"
    else
        sudo "$SYSTEMCTL_BIN" restart "$DISPLAY_SERVICE"
    fi
}

finish_without_update() {
    if [[ "$RESTART_DISPLAY_MODE" -eq 1 ]]; then
        restart_display_service
    fi
    return 0
}

main() {
    if ! command -v git >/dev/null 2>&1; then
        log "Git is not installed; skipping update."
        finish_without_update
        return 0
    fi

    if ! run_git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        log "This install is not a Git clone; skipping update."
        finish_without_update
        return 0
    fi

    if ! run_git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
        log "No upstream branch is configured; skipping update."
        finish_without_update
        return 0
    fi

    local tracked_changes
    tracked_changes="$(run_git status --porcelain --untracked-files=no)"
    if [[ -n "$tracked_changes" ]]; then
        log "Tracked local changes detected; skipping auto-update to avoid overwriting them."
        finish_without_update
        return 0
    fi

    if ! run_git fetch --quiet origin; then
        log "Could not reach origin; leaving the current version in place."
        finish_without_update
        return 0
    fi

    local behind_count
    behind_count="$(run_git rev-list --count HEAD..@{u})"
    if [[ "$behind_count" == "0" ]]; then
        if [[ "$SCHEDULED_MODE" -eq 0 ]]; then
            log "Already up to date."
        fi
        finish_without_update
        return 0
    fi

    log "Applying $behind_count update(s) from GitHub..."
    run_git pull --ff-only

    if [[ "$(id -u)" -eq 0 ]]; then
        NOTICEBOARD_APP_USER="$APP_USER" NOTICEBOARD_SKIP_APT=1 "$APP_DIR/scripts/install_pi.sh"
    else
        NOTICEBOARD_APP_USER="$APP_USER" NOTICEBOARD_SKIP_APT=1 sudo "$APP_DIR/scripts/install_pi.sh"
    fi

    log "Update complete."
}

if [[ ! -e "$LOCK_FILE" ]]; then
    : > "$LOCK_FILE"
    chmod 644 "$LOCK_FILE" || true
fi

exec 9<"$LOCK_FILE"
if ! flock -n 9; then
    if [[ "$SCHEDULED_MODE" -eq 0 ]]; then
        log "Another update process is already running."
    fi
    exit 0
fi

main
