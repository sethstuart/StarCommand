#!/bin/bash
# SkyWatcher Controller Installation Script
# This script sets up a Python virtual environment and installs the controller

set -e

echo "================================================"
echo " SkyWatcher Telescope Controller Installation"
echo "================================================"
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
echo "Found Python $python_version"

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    exit 1
fi

# Check for tkinter (GUI only)
echo "Checking for tkinter..."
if python3 -c "import tkinter" 2>/dev/null; then
    echo "✓ tkinter found (GUI available)"
else
    echo "✗ tkinter not found (CLI only)"
    echo ""
    echo "To install tkinter:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-tk"
    echo "  Fedora:        sudo dnf install python3-tkinter"
    echo "  Arch:          sudo pacman -S tk"
    echo ""
    read -p "Continue without GUI? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install package in development mode
echo "Installing SkyWatcher Controller..."
pip install -e . > /dev/null 2>&1

echo ""
echo "================================================"
echo " Installation Complete!"
echo "================================================"
echo ""
echo "To use the controller:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Run the GUI:"
echo "   skywatcher-gui"
echo "   OR: python3 telescope_gui_v2.py"
echo ""
echo "3. Run the CLI:"
echo "   skywatcher-cli"
echo "   OR: python3 telescope_control_v2.py"
echo ""
echo "4. When done, deactivate:"
echo "   deactivate"
echo ""
echo "Configuration stored in: ~/.skywatcher_controller/"
echo ""
