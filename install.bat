@echo off
REM SkyWatcher Controller Installation Script for Windows
REM Batch file for compatibility with older Windows systems

echo.
echo ================================================
echo  SkyWatcher Telescope Controller Installation
echo ================================================
echo.

REM Check Python installation
echo Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3 is required but not found
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check 'Add Python to PATH' during installation!
    echo.
    pause
    exit /b 1
)

python --version
echo Python found!

REM Check for tkinter
echo.
echo Checking for tkinter...
python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo Warning: tkinter not found (CLI only)
    echo.
    echo Note: tkinter usually comes with Python on Windows.
    echo If you need GUI support, reinstall Python with tcl/tk option.
    echo.
    set /p continue="Continue without GUI? (y/n): "
    if /i not "%continue%"=="y" exit /b 1
) else (
    echo tkinter found (GUI available)
)

REM Create virtual environment
echo.
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Error: Failed to create virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt --quiet

REM Install package
echo.
echo Installing Star Command...
pip install -e . --quiet
if errorlevel 1 (
    echo Error: Installation failed
    pause
    exit /b 1
)

echo.
echo ================================================
echo  Installation Complete!
echo ================================================
echo.
echo To use the controller:
echo.
echo 1. Activate the virtual environment:
echo    venv\Scripts\activate.bat
echo.
echo 2. Run the GUI:
echo    python StarCommandGUI.py
echo.
echo 3. Run the CLI:
echo    python StarCommandCLI.py [ip] [port]
echo.
echo 4. When done, deactivate:
echo    deactivate
echo.
echo Configuration stored in: %USERPROFILE%\.skywatcher_controller\
echo.
pause
