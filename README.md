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
1. Copy the `backend/`, `pi_display/`, and `scripts/` folders to your Raspberry Pi (e.g., to `/home/pi/noticeboard_app`).
2. Navigate to the `scripts/` folder.
3. Make the install script executable: `chmod +x install_pi.sh`.
4. Run the script: `./install_pi.sh`.
5. The backend and display will now start automatically on every boot.

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
