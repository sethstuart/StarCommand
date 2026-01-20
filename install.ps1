# SkyWatcher Controller Installation Script for Windows
# PowerShell script to set up Python virtual environment and install the controller

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host " SkyWatcher Telescope Controller Installation" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python installation
Write-Host "Checking for Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+\.\d+)") {
        $version = $matches[1]
        Write-Host "Found Python $version" -ForegroundColor Green
    } else {
        throw "Python not found"
    }
} catch {
    Write-Host "Error: Python 3 is required but not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation!" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Check for tkinter (comes with Python on Windows usually)
Write-Host "Checking for tkinter..." -ForegroundColor Yellow
try {
    python -c "import tkinter" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "tkinter found (GUI available)" -ForegroundColor Green
    } else {
        Write-Host "tkinter not found (CLI only)" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Note: tkinter usually comes with Python on Windows." -ForegroundColor Yellow
        Write-Host "If you need GUI support, reinstall Python with tcl/tk option." -ForegroundColor Yellow
        Write-Host ""
        $response = Read-Host "Continue without GUI? (y/n)"
        if ($response -ne 'y') {
            exit 1
        }
    }
} catch {
    Write-Host "Warning: Could not check for tkinter" -ForegroundColor Yellow
}

# Create virtual environment
Write-Host ""
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv

if (-not $?) {
    Write-Host "Error: Failed to create virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet

# Install package in development mode
Write-Host "Installing Star Command..." -ForegroundColor Yellow
pip install -e . --quiet

if (-not $?) {
    Write-Host "Error: Installation failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host " Installation Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To use the controller:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Activate the virtual environment:" -ForegroundColor White
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Run the GUI:" -ForegroundColor White
Write-Host "   python StarCommandGUI.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Run the CLI:" -ForegroundColor White
Write-Host "   python StarCommandCLI.py [ip] [port]" -ForegroundColor Yellow
Write-Host ""
Write-Host "4. When done, deactivate:" -ForegroundColor White
Write-Host "   deactivate" -ForegroundColor Yellow
Write-Host ""
Write-Host "Configuration stored in: $env:USERPROFILE\.skywatcher_controller\" -ForegroundColor Cyan
Write-Host ""
Write-Host "NOTE: If you get execution policy errors, run PowerShell as Administrator and execute:" -ForegroundColor Yellow
Write-Host "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to exit"
