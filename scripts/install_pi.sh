#!/bin/bash

# Installation script for Raspberry Pi Noticeboard
echo "Starting Noticeboard Installation..."

# Update and install dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-pyqt6

# Install python packages
pip3 install flask flask-sqlalchemy flask-cors requests qtawesome

# Create directory structure if not exists
mkdir -p ~/noticeboard_app

# Copy service files
sudo cp noticeboard-backend.service /etc/systemd/system/
sudo cp noticeboard-display.service /etc/systemd/system/

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable noticeboard-backend.service
sudo systemctl enable noticeboard-display.service

# Start services
sudo systemctl start noticeboard-backend.service
sudo systemctl start noticeboard-display.service

echo "Installation complete! The display should start shortly."
echo "If it doesn't show up, ensure you are in a graphical session (X11)."
