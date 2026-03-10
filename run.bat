@echo off
REM OpenTree Git GUI Launcher for Windows
REM Usage: run.bat

cd /d "%~dp0"
python -m opentree %*

if errorlevel 1 (
    echo.
    echo Failed to start OpenTree. Make sure Python 3.11+ is installed.
    pause
)
