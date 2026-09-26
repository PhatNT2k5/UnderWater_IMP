@echo off
setlocal
set "DASHBOARD_PYTHON=%USERPROFILE%\.conda\envs\mainenv\python.exe"
if not exist "%DASHBOARD_PYTHON%" (
    echo Python mainenv was not found. See README.md for launch instructions.
    pause
    exit /b 1
)
"%DASHBOARD_PYTHON%" "%~dp0run_dashboard.py" %*
if errorlevel 1 pause
