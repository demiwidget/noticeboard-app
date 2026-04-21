# Department Noticeboard System: Comprehensive Setup Tutorial

This tutorial provides detailed, step-by-step instructions for setting up your Department Noticeboard System, encompassing both the Raspberry Pi display client and the PC management application.

## Table of Contents
1.  [Prerequisites](#1-prerequisites)
2.  [Raspberry Pi Setup](#2-raspberry-pi-setup)
    *   [Hardware Requirements](#hardware-requirements)
    *   [Software Preparation](#software-preparation)
    *   [Transferring Files](#transferring-files)
    *   [Running the Installation Script](#running-the-installation-script)
    *   [Verifying Services](#verifying-services)
3.  [PC Management Application Setup](#3-pc-management-application-setup)
    *   [Software Requirements](#software-requirements)
    *   [Installation](#installation)
    *   [Running the Application](#running-the-application)
    *   [Connecting to the Raspberry Pi Backend](#connecting-to-the-raspberry-pi-backend)
4.  [Usage Guide](#4-usage-guide)
5.  [Troubleshooting](#5-troubleshooting)

## 1. Prerequisites

Before you begin, ensure you have the following:

### Hardware Requirements
*   **Raspberry Pi**: Any model capable of running a graphical desktop environment (e.g., Raspberry Pi 3, 4, or 5). A display connected to the Pi is essential.
*   **MicroSD Card**: At least 16GB, with Raspberry Pi OS (formerly Raspbian) installed. A desktop version is recommended for easier initial setup.
*   **Power Supply**: Appropriate for your Raspberry Pi model.
*   **Ethernet Cable or Wi-Fi**: For network connectivity on both the Raspberry Pi and your PC.
*   **PC**: A Windows, macOS, or Linux machine to run the management application.

### Software Preparation
*   **Python 3**: Installed on both your Raspberry Pi and PC. Raspberry Pi OS comes with Python pre-installed.
*   **Git**: Installed on your PC to clone the project repository.
*   **SSH Client (Optional but Recommended)**: For remote access to your Raspberry Pi (e.g., PuTTY on Windows, or the built-in terminal on Linux/macOS).
*   **File Transfer Tool (Optional)**: Such as SCP or SFTP client (e.g., WinSCP on Windows) if not using Git directly on the Pi.

## 2. Raspberry Pi Setup

This section guides you through setting up the display client and backend server on your Raspberry Pi.

### Software Preparation
1.  **Update your Raspberry Pi OS**: Open a terminal on your Raspberry Pi and run:
    ```bash
    sudo apt update && sudo apt upgrade -y
    ```
2.  **Install Git (if not already installed)**:
    ```bash
    sudo apt install git -y
    ```
3.  **Leave Python packages to the installer**: The installer uses Raspberry Pi OS/Debian `apt` packages for the backend and Qt display dependencies.
    ```bash
    # No manual pip install is needed on the Raspberry Pi.
    ```

### Transferring Files

There are a few ways to get the project files onto your Raspberry Pi. The easiest is to clone the GitHub repository directly on the Pi.

1.  **Clone the Repository**: Open a terminal on your Raspberry Pi and run:
    ```bash
    git clone https://github.com/demiwidget/noticeboard-app.git ~/noticeboard-app
    ```
    *Note: You can choose a different install path. The installer detects the actual path and current user when it generates the systemd services.*

### Running the Installation Script

Navigate to the `scripts` directory within the cloned repository and run the installation script.

1.  **Navigate to scripts directory**:
    ```bash
    cd ~/noticeboard-app/scripts
    ```
2.  **Make the script executable**:
    ```bash
    chmod +x install_pi.sh
    ```
3.  **Run the installation script**:
    ```bash
    ./install_pi.sh
    ```
    This script will:
    *   Install necessary Raspberry Pi OS/Debian packages (`python3-flask`, `python3-flask-sqlalchemy`, `python3-flask-cors`, `python3-requests`, and either `python3-pyqt6` or `python3-pyqt5`).
    *   Generate `noticeboard-backend.service` and `noticeboard-display.service` in `/etc/systemd/system/` with the correct username and project path.
    *   Add a tightly scoped sudoers rule so the backend can start only the Pi refresh service on request from the PC app.
    *   Reload systemd, enable, and start both services.

### Verifying Services

After running the installation script, the backend server and display client should start automatically. You can verify their status:

1.  **Check Backend Service Status**:
    ```bash
    sudo systemctl status noticeboard-backend.service
    ```
    You should see `Active: active (running)`.

2.  **Check Display Service Status**:
    ```bash
    sudo systemctl status noticeboard-display.service
    ```
    You should see `Active: active (running)`.

3.  **Verify Display**: The Raspberry Pi's connected display should now show the Noticeboard application in fullscreen mode.

## 3. PC Management Application Setup

This section details how to set up and run the PC application to manage your noticeboard.

### Software Requirements
*   **Python 3**: Ensure Python 3 is installed on your PC.
*   **Pip**: Python's package installer, usually included with Python 3.

### Installation

1.  **Clone the Repository**: On your PC, clone the GitHub repository:
    ```bash
    git clone https://github.com/demiwidget/noticeboard-app.git
    ```
2.  **Navigate to the PC App Directory**:
    ```bash
    cd noticeboard-app
    ```
3.  **Windows quick start**: Double-click `Noticeboard Manager.vbs` in the project folder. It launches without a console window, creates a virtual environment on first run, installs the PC dependencies automatically, and checks for Git updates before startup when the repo is a clean clone.

    `Noticeboard Manager.cmd` remains available as a debug launcher if you ever want to see startup output.

Manual fallback:
    ```bash
    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install PyQt6 requests qtawesome
    ```

### Running the Application

1.  **Execute the PC Application**:
    ```bash
    python pc_app\main.py
    ```
    The Noticeboard Manager GUI should now appear.

### Automatic Updates

*   **PC app**: Launching via `Noticeboard Manager.vbs` checks the GitHub clone for updates before the app opens. If the local repo has tracked file changes, the update step is skipped to avoid overwriting local edits.
*   **Raspberry Pi**: `install_pi.sh` now installs `noticeboard-update.timer`, which runs every 6 hours, checks for repo updates, pulls them, reruns the Pi installer in update mode, and restarts the backend and display services.
*   **Restarting the Pi display after updates**: Use the `Restart Pi Display` button in the PC app header to check GitHub for updates immediately and then refresh the fullscreen display.
*   **LAN access note**: The Pi display restart endpoint is intentionally open on the local network for this setup. Keep the Pi backend reachable only from devices you trust.
*   **Manual Pi update**:
    ```bash
    ~/noticeboard-app/scripts/update_pi.sh
    ```

### Connecting to the Raspberry Pi Backend

1.  **Find Raspberry Pi's IP Address**: On your Raspberry Pi, open a terminal and type `hostname -I` to find its IP address.
2.  **Enter IP in PC App**: In the PC Management Application, locate the "Server IP" input field (usually at the top right).
3.  **Enter IP and Connect**: Type the Raspberry Pi's IP address into the field and click the "Connect" button. The application will attempt to connect to the Flask backend running on the Pi.

## 4. Usage Guide

Once connected, you can start managing your noticeboard:

*   **Manage Notices Tab**:
    *   **Add New Notice**: Enter a title, content, and select a priority (Low, Medium, High). Click "Post Notice".
    *   **Remove Notice**: Select a notice from the list and click "Remove Selected".
*   **Assign Tasks Tab**:
    *   **Assign New Task**: Enter a title, assignee's name, due time, and priority. Click "Assign Task".
    *   **Remove Task**: Select a task from the list and click "Remove Selected".
*   **Refresh All Data**: Click the "Refresh All Data" button to manually update the lists in the PC app and trigger a refresh on the Pi display.

## 5. Troubleshooting

*   **Pi Display Not Showing**: 
    *   Ensure the Raspberry Pi is connected to a display and is powered on.
    *   Check service status (`sudo systemctl status noticeboard-display.service`).
    *   View display logs with `sudo journalctl -u noticeboard-display -n 100 --no-pager`.
    *   Ensure the Pi boots into the graphical desktop, preferably with auto-login enabled for the same user that ran the installer.
    *   If your Pi uses an older Raspberry Pi OS release, the display can fall back to `python3-pyqt5`; Bookworm systems should use `python3-pyqt6`.
*   **PC App Cannot Connect to Pi**: 
    *   Verify the Raspberry Pi's IP address is correct and that both devices are on the same network.
    *   Check if the backend service is running on the Pi (`sudo systemctl status noticeboard-backend.service`).
    *   Ensure no firewall is blocking port 5000 on the Raspberry Pi.
*   **No Notices/Tasks Appearing on Pi**: 
    *   Confirm that you have added notices/tasks using the PC app.
    *   Check the backend service status on the Pi.
    *   Ensure the PC app successfully connected to the Pi's backend.

If you encounter persistent issues, please provide details of the error messages and steps you've taken for further assistance.
