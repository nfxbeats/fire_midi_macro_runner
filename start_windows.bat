@echo off
setlocal enabledelayedexpansion

rem Fire MIDI Macro Runner - Launch Script
rem This batch file runs the Fire MIDI Macro Runner application
rem using relative paths so it can be used from any location.

rem Change to the directory containing this batch file
cd /d "%~dp0"

rem Set Python command - check for virtual environment first
set PYTHON_CMD=python

rem Check for common virtual environment paths
if exist "venv\Scripts\python.exe" (
    echo Using virtual environment: venv
    set PYTHON_CMD=venv\Scripts\python.exe
) else if exist ".venv\Scripts\python.exe" (
    echo Using virtual environment: .venv
    set PYTHON_CMD=.venv\Scripts\python.exe
) else if exist "env\Scripts\python.exe" (
    echo Using virtual environment: env
    set PYTHON_CMD=env\Scripts\python.exe
)

rem Check if Python is available
%PYTHON_CMD% --version >nul 2>&1
set PYTHON_CHECK=!ERRORLEVEL!
if !PYTHON_CHECK! neq 0 (
    echo Python is not installed or not in your PATH.
    echo Please install Python 3.6+ and run setup_environment.bat before trying again.
    pause
    exit /b 1
)

rem Check if required modules are installed
%PYTHON_CMD% -c "import mido, keyboard, rtmidi" >nul 2>&1
set MODULE_ERROR=!ERRORLEVEL!
if !MODULE_ERROR! neq 0 (
    echo Required Python modules are missing.
    echo .
    echo Please run setup_env.bat first to set up the environment.
    echo .
    pause
    exit /b 1
)

echo Starting Fire MIDI Macro Runner...
%PYTHON_CMD% fire_midi_macro_runner.py
set RUN_ERROR=!ERRORLEVEL!
if !RUN_ERROR! neq 0 (
    echo Program exited with an error (code !RUN_ERROR!).
    pause
)

endlocal
