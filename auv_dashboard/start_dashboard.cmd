@echo off
setlocal
rem Python lookup order: DASHBOARD_PYTHON, %USERPROFILE%\.conda\envs\mainenv, active conda env "mainenv".
if not defined DASHBOARD_PYTHON (
    if exist "%USERPROFILE%\.conda\envs\mainenv\python.exe" (
        set "DASHBOARD_PYTHON=%USERPROFILE%\.conda\envs\mainenv\python.exe"
    ) else if /i "%CONDA_DEFAULT_ENV%"=="mainenv" (
        set "DASHBOARD_PYTHON=%CONDA_PREFIX%\python.exe"
    )
)
if not exist "%DASHBOARD_PYTHON%" (
    echo Python mainenv was not found.
    echo Activate it first ^(conda activate mainenv^) or set DASHBOARD_PYTHON to its python.exe.
    pause
    exit /b 1
)
"%DASHBOARD_PYTHON%" "%~dp0run_dashboard.py" %*
if errorlevel 1 pause
