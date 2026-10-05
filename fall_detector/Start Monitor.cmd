@echo off
if not exist "%~dp0.venv\Scripts\pythonw.exe" (
  echo The isolated detector environment is missing. See fall_detector README.md.
  pause
  exit /b 1
)
start "" "%~dp0.venv\Scripts\pythonw.exe" -m tyler_safety_monitor
