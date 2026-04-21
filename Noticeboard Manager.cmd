@echo off
setlocal

cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_pc_app.ps1"

if errorlevel 1 (
    echo.
    echo Noticeboard Manager could not start.
    echo Leave this window open and share the error message if you need help.
    pause
)
