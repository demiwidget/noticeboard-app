# Department Noticeboard System Architecture

## Overview
The system consists of three main components:
1. **Backend Server (Flask + SQLite)**: A lightweight REST API server that manages the data (notices, tasks, users). This can run on the Raspberry Pi or a separate server. For simplicity and self-containment, it will run on the Raspberry Pi alongside the display client.
2. **PC Management GUI (PyQt6)**: A modern, colorful desktop application for managers to add/edit/delete notices, assign tasks, set priorities, and manage users. It communicates with the backend via HTTP REST API.
3. **Raspberry Pi Display Client (PyQt6/Web)**: A fullscreen, auto-starting application that fetches data from the backend and displays it in an engaging, modern UI.

## Data Models
- **Notice**: ID, Title, Content, Priority (Low, Medium, High), Created At, Expiry Date, Color Theme.
- **Task**: ID, Title, Description, Assignee, Due Time, Priority, Status (Pending, Completed).
- **User/Assignee**: ID, Name, Department, Avatar/Color.

## Technology Stack
- **Backend**: Python, Flask, Flask-RESTful, SQLAlchemy (SQLite).
- **PC GUI**: Python, PyQt6 (or CustomTkinter for modern look), Requests.
- **Pi Display**: Python, PyQt6 (fullscreen mode) or a simple Flask-rendered HTML/JS page displayed via Chromium in kiosk mode. Given the requirement for "modern and pretty no boring colours", a web-based display (HTML/CSS/JS with animations) running in Chromium kiosk mode is often the most robust and visually appealing for a Pi display.
- **Auto-start**: systemd service on Raspberry Pi.

## Features
- **PC App**:
  - Dashboard with current notices and tasks.
  - Form to add new notice (Title, Content, Priority, Expiry).
  - Form to assign task (Title, Assignee, Time, Priority).
  - Settings page (Server IP configuration).
- **Pi Display**:
  - Auto-refreshing dashboard.
  - Split screen: Notices on one side, Tasks on the other.
  - Color-coded by priority (e.g., Red for High, Yellow for Medium, Green/Blue for Low).
  - Clock and date display.

## Deployment
- The Pi will host the Flask server and the Display client.
- The PC will run the Management GUI executable.
- A setup script will configure the Pi (install dependencies, setup systemd services for Flask and Chromium kiosk).
