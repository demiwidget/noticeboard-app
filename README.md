# Department Noticeboard System

A modern, dual-application noticeboard system designed for a Raspberry Pi display and PC management.

## Features
- **PC Management App**: Modern GUI to add/remove notices and tasks.
- **Pi Display App**: Fullscreen, auto-refreshing dashboard with high-contrast, colorful cards.
- **Priority System**: Color-coded notices and tasks (High, Medium, Low).
- **Task Assignment**: Assign tasks to specific people with due times.
- **Robustness**: Auto-starts on reboot or crash via systemd services.

## Components
1. `backend/`: Flask REST API and SQLite database.
2. `pc_app/`: PyQt6 management application for Windows/Linux.
3. `pi_display/`: PyQt6 fullscreen display client for Raspberry Pi.
4. `scripts/`: Installation and service configuration files.

## Setup Instructions

### 1. Raspberry Pi Setup
1. Use Raspberry Pi OS with Desktop enabled and make sure the Pi boots into the desktop session.
2. Copy or clone this repository to the Raspberry Pi. For example: `git clone https://github.com/demiwidget/noticeboard-app.git ~/noticeboard-app`.
3. Navigate to the installer: `cd ~/noticeboard-app/scripts`.
4. Make the install script executable: `chmod +x install_pi.sh`.
5. Run the script: `./install_pi.sh`.
6. The installer uses Raspberry Pi OS/Debian packages, writes systemd services with your actual username and clone path, then starts the backend and display.

Useful Pi checks:

```bash
sudo systemctl status noticeboard-backend.service
sudo systemctl status noticeboard-display.service
curl http://localhost:5000/api/notices
sudo journalctl -u noticeboard-backend -u noticeboard-display -f
```

### 2. PC Management Setup
1. Ensure you have Python installed.
2. Install dependencies: `python3 -m pip install PyQt6 requests qtawesome`.
3. Run the app: `python pc_app/main.py`.
4. Enter the IP address of your Raspberry Pi in the top bar and click "Connect".

## Usage
- **Adding Notices**: Use the "Manage Notices" tab in the PC app.
- **Assigning Tasks**: Use the "Assign Tasks" tab.
- **Priorities**: High priority items appear in Red, Medium in Orange/Yellow, and Low in Blue/Green.
- **Auto-Update**: The Pi display refreshes every 10 seconds to show new changes.
