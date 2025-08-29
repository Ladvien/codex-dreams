@echo off
REM Codex Dreams Daemon Service Batch File
REM This file is used as a service wrapper for Windows

REM Set working directory to project root
cd /d "%~dp0..\.."

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run the daemon scheduler
python -m src.daemon.scheduler --daemon

REM If the python command fails, try the installed command
if %errorlevel% neq 0 (
    codex-scheduler --daemon
)