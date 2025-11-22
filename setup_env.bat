@echo off
setlocal enabledelayedexpansion

rem Fire MIDI Macro Runner - Environment Setup Script
rem This batch file creates a virtual environment and installs all required libraries

rem Change to the directory containing this batch file
cd /d "%~dp0"

echo ===================================================
echo Fire MIDI Macro Runner - Environment Setup
echo ===================================================
echo.

rem Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed or not in your PATH.
    echo Please install Python 3.6 or newer before continuing.
    pause
    exit /b 1
)

rem Check Python version
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo Found Python %PYTHON_VERSION%

rem Check for existing virtual environments in common paths
if exist "venv\Scripts\python.exe" (
    echo Found existing virtual environment: venv
    choice /C YN /M "Do you want to use the existing virtual environment? (Y/N)"
    if !ERRORLEVEL! equ 1 (
        echo Using existing virtual environment: venv
        call venv\Scripts\activate.bat
    ) else (
        echo Removing existing environment...
        rmdir /S /Q venv
        goto create_venv
    )
) else if exist ".venv\Scripts\python.exe" (
    echo Found existing virtual environment: .venv
    choice /C YN /M "Do you want to use the existing virtual environment? (Y/N)"
    if !ERRORLEVEL! equ 1 (
        echo Using existing virtual environment: .venv
        call .venv\Scripts\activate.bat
    ) else (
        echo Removing existing environment...
        rmdir /S /Q .venv
        goto create_venv
    )
) else if exist "env\Scripts\python.exe" (
    echo Found existing virtual environment: env
    choice /C YN /M "Do you want to use the existing virtual environment? (Y/N)"
    if !ERRORLEVEL! equ 1 (
        echo Using existing virtual environment: env
        call env\Scripts\activate.bat
    ) else (
        echo Removing existing environment...
        rmdir /S /Q env
        goto create_venv
    )
) else (
    goto create_venv
)
goto install_deps

:create_venv
echo.
echo Creating new virtual environment...
python -m venv venv
if !ERRORLEVEL! neq 0 (
    echo Failed to create virtual environment.
    echo Please make sure you have the venv module installed:
    echo   pip install --user virtualenv
    pause
    exit /b 1
)
echo Virtual environment created successfully.
call venv\Scripts\activate.bat

:install_deps
echo.
echo Installing required dependencies...
python -m pip install --quiet --upgrade pip
echo Installing required packages...
python -m pip install --quiet -r requirements.txt

if !ERRORLEVEL! neq 0 (
    echo Failed to install dependencies.
    pause
    exit /b !ERRORLEVEL!
)

echo.
echo ===================================================
echo Environment setup complete!
echo.
echo Your virtual environment has been created and all
echo required dependencies have been installed.
echo.
echo You can now run the program using:
echo   run_fire_midi_macro_runner.bat
echo ===================================================
echo.

pause
