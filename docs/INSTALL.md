# SkyWatcher Controller v2.0 - Installation & Setup Guide

Complete professional telescope control suite with GUI and CLI interfaces.

## 🚀 Quick Start

### Method 1: Automated Installation (Recommended)

#### Linux / macOS

```bash
# Make install script executable
chmod +x install.sh

# Run installer
./install.sh

# Activate virtual environment
source venv/bin/activate

# Run GUI
skywatcher-gui

# OR run CLI
skywatcher-cli
```

#### Windows (PowerShell)

```powershell
# If you get execution policy errors, run PowerShell as Administrator:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run installer
.\install.ps1

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run GUI
skywatcher-gui

# OR run CLI
skywatcher-cli
```

#### Windows (Command Prompt / Batch)

```cmd
# Run installer
install.bat

# Activate virtual environment
venv\Scripts\activate.bat

# Run GUI
skywatcher-gui

# OR run CLI
skywatcher-cli
```

### Method 2: Manual Setup

#### Linux / macOS

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install in development mode
pip install -e .

# Run
skywatcher-gui  # or skywatcher-cli
```

#### Windows (PowerShell)

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install in development mode
pip install -e .

# Run
skywatcher-gui  # or skywatcher-cli
```

#### Windows (Command Prompt)

```cmd
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate.bat

# Install in development mode
pip install -e .

# Run
skywatcher-gui  # or skywatcher-cli
```

### Method 3: Direct Execution (No Installation)

#### Linux / macOS

```bash
# GUI
python3 telescope_gui_v2.py

# CLI
python3 telescope_control_v2.py [ip] [port]
```

#### Windows

```cmd
# GUI
python telescope_gui_v2.py

# CLI
python telescope_control_v2.py [ip] [port]
```

---

## 📋 Requirements

### Python Version
- Python 3.7 or higher
- Tested on Python 3.8, 3.9, 3.10, 3.11, 3.12

### System Packages

**For GUI (tkinter):**

**Linux:**

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora/RHEL
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

**macOS:**

```bash
# Usually pre-installed with Python
# If needed:
brew install python-tk
```

**Windows:**

tkinter is **included with the official Python installer** from python.org.

If you don't have tkinter:
1. Download Python from https://www.python.org/downloads/
2. Run installer
3. **Important**: Check "tcl/tk and IDLE" in Optional Features
4. Complete installation

To verify tkinter is installed:
```cmd
python -c "import tkinter; print('tkinter OK')"
```

**CLI version has no dependencies!** (Pure Python stdlib)

---

## 🎨 GUI Version Features

### Main Features
✅ **Tabbed Interface**
  - **Control Tab**: Direction pad, speed control, preset positions
  - **Status Tab**: Live mount status, auto-update capability
  - **Settings Tab**: Keyboard controls, themes, connection settings
  - **Info Tab**: Mount information, command log

✅ **Full Keyboard Support**
  - WASD or Arrow keys for movement
  - Space to stop
  - ESC for emergency stop
  - +/- for speed control
  - All keys configurable!

✅ **Configurable Themes**
  - Customize all colors
  - Dark mode by default
  - Persistent settings

✅ **Position Display Options**
  - Degrees
  - Raw counts
  - Both (degrees + counts)
  - Alt/Az coordinates

✅ **Preset Positions**
  - Home position (set/goto)
  - Stow position (set/goto)
  - Saved to config

✅ **Emergency Stop**
  - Large prominent button
  - ESC key hotkey
  - Instant stop both axes

✅ **Configuration Management**
  - All settings saved to `~/.skywatcher_controller/config.json`
  - Per-user configuration
  - Survives restarts

### Default Keyboard Controls

| Key | Action |
|-----|--------|
| W / ↑ | Move Up |
| S / ↓ | Move Down |
| A / ← | Move Left |
| D / → | Move Right |
| Space | Stop All |
| ESC | Emergency Stop |
| + | Speed Up |
| - | Speed Down |

**All configurable in Settings tab!**

---

## 💻 CLI Version Features

### Enhanced Commands

**Movement:**
```
w / up [seconds]     - Move up (optional timed)
s / down [seconds]   - Move down
a / left [seconds]   - Move left
d / right [seconds]  - Move right
x / stop             - Stop all
e / estop            - Emergency stop
```

**Speed:**
```
+                    - Increase speed by 0.5°/sec
-                    - Decrease speed by 0.5°/sec
speed [value]        - Set specific speed
speed                - Show current speed
```

**Position:**
```
p / pos              - Show position
format [type]        - Set display format (degrees/raw/both)
zero                 - Set position to 0,0
```

**Presets:**
```
home                 - Go to home position
sethome              - Set current as home
stow                 - Go to stow position
setstow              - Set current as stow
```

**Info:**
```
status               - Show mount status
info                 - Show mount information
version              - Show software & firmware versions
config               - Show configuration
```

**Other:**
```
help / ?             - Show help
quit / q             - Exit
```

### Configuration

CLI uses same config file as GUI: 

**Linux/macOS**: `~/.skywatcher_controller/config.json`  
**Windows**: `%USERPROFILE%\.skywatcher_controller\config.json`

(Typically: `C:\Users\YourName\.skywatcher_controller\config.json`)

Settings include:
- Default IP and port
- Speed limits
- Home and stow positions
- Position display format

---

## ⚙️ Configuration

### Connection Settings

**GUI:** Settings Tab → Connection
**CLI:** Edit `~/.skywatcher_controller/config.json`

```json
{
  "connection": {
    "ip": "192.168.4.1",
    "port": 11880,
    "timeout": 2.0
  }
}
```

**Default IP:** 192.168.4.1 (AP mode)
**Default Port:** 11880 (UDP)

### Keyboard Controls

**GUI:** Settings Tab → Keyboard

Configure any key for any action. Changes take effect after restart.

### Theme Customization

**GUI:** Settings Tab → Theme

Customize:
- Background color
- Foreground color
- Button colors
- Accent color
- Emergency stop color

Click color pickers to choose colors, save, and restart to apply.

### Speed Settings

```json
{
  "speed": {
    "default": 1.0,
    "min": 0.1,
    "max": 10.0
  }
}
```

Adjust in config file and restart, or use GUI speed slider.

### Position Display

```json
{
  "display": {
    "position_format": "both",
    "show_positions": true,
    "auto_update": false,
    "update_rate": 1.0
  }
}
```

**Formats:**
- `degrees` - Show in degrees only
- `raw` - Show raw counts only
- `both` - Show both (default)
- `coordinates` - Show as Alt/Az coordinates

### Preset Positions

```json
{
  "positions": {
    "home_az": 0,
    "home_alt": 0,
    "stow_az": 0,
    "stow_alt": 90
  }
}
```

Set via "Set Current as Home/Stow" buttons or edit config directly.

---

## 🔧 Troubleshooting

### Windows-Specific Issues

#### PowerShell Execution Policy Error

If you get an error like "cannot be loaded because running scripts is disabled":

**Solution 1: Current User (Recommended)**
```powershell
# Run in PowerShell (no admin needed)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Solution 2: Use Batch File Instead**
```cmd
# Use install.bat instead of install.ps1
install.bat
```

#### Python Not Found

**Error**: `'python' is not recognized as an internal or external command`

**Solution**:
1. Download Python from https://www.python.org/downloads/
2. During installation, **check "Add Python to PATH"**
3. Restart Command Prompt/PowerShell
4. Verify: `python --version`

#### tkinter Not Available

**Error**: `No module named 'tkinter'`

**Solution**:
1. Reinstall Python from python.org
2. In installer, click "Modify"
3. Check "tcl/tk and IDLE" under Optional Features
4. Complete installation

#### Virtual Environment Activation Issues

**PowerShell**:
```powershell
# If venv activation fails
.\venv\Scripts\Activate.ps1

# Alternative
python -m venv --clear venv
.\venv\Scripts\Activate.ps1
```

**Command Prompt**:
```cmd
# Use .bat instead of .ps1
venv\Scripts\activate.bat
```

#### Path Too Long Errors

Windows has a 260 character path limit (older versions).

**Solution**:
1. Install in a shorter path (e.g., `C:\skywatcher\`)
2. Or enable long paths in Windows 10+:
   - Run as Admin: `New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force`
   - Restart computer

### Linux/macOS Issues

#### tkinter not found

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-tk

# Verify
python3 -c "import tkinter; print('OK')"
```

### Connection Issues

1. **Verify WiFi connection:**
   ```bash
   ping 192.168.4.1
   ```

2. **Check correct IP:**
   - AP mode: 192.168.4.1
   - Station mode: Check router

3. **Test with CLI first:**
   ```bash
   python3 telescope_control_v2.py 192.168.4.1 11880
   ```

4. **Check firewall:**
   ```bash
   # Ubuntu
   sudo ufw allow 11880/udp
   ```

### Configuration Issues

**Reset to defaults:**

Linux/macOS:
```bash
rm ~/.skywatcher_controller/config.json
```

Windows (PowerShell):
```powershell
Remove-Item $env:USERPROFILE\.skywatcher_controller\config.json
```

Windows (Command Prompt):
```cmd
del %USERPROFILE%\.skywatcher_controller\config.json
```

**Check config location:**

Linux/macOS:
```bash
ls -la ~/.skywatcher_controller/
cat ~/.skywatcher_controller/config.json
```

Windows (PowerShell):
```powershell
Get-ChildItem $env:USERPROFILE\.skywatcher_controller\
Get-Content $env:USERPROFILE\.skywatcher_controller\config.json
```

Windows (Command Prompt):
```cmd
dir %USERPROFILE%\.skywatcher_controller\
type %USERPROFILE%\.skywatcher_controller\config.json
```

### Import Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Verify Python version
python --version  # Should be 3.7+

# Reinstall
pip install -e .
```

---

## 📁 File Structure

```
skywatcher-controller/
├── telescope_gui_v2.py       # GUI application
├── telescope_control_v2.py   # CLI application
├── setup.py                  # Package setup
├── requirements.txt          # Dependencies (empty!)
├── install.sh               # Linux/Mac installer
├── install.ps1              # Windows PowerShell installer
├── install.bat              # Windows batch installer
├── INSTALL.md               # This file
├── README_FULL.md           # User guide
├── PROTOCOL_REFERENCE.md    # Protocol docs
├── WHATS_NEW.md             # Changes from v1
└── venv/                    # Virtual environment (created)

~/.skywatcher_controller/     # Linux/Mac config location
└── config.json              # User configuration

%USERPROFILE%\.skywatcher_controller\  # Windows config location
└── config.json              # User configuration
```

---

## 🚦 Usage Examples

### GUI

**Linux/macOS:**
```bash
# Direct run
python3 telescope_gui_v2.py

# From venv
source venv/bin/activate
skywatcher-gui
```

**Windows:**
```cmd
# Direct run
python telescope_gui_v2.py

# From venv
venv\Scripts\activate.bat
skywatcher-gui
```

**Workflow:**
1. Enter IP (defaults to 192.168.4.1)
2. Click "Connect"
3. Use direction pad or WASD keys
4. Adjust speed slider
5. Set home position
6. Enable auto-update to monitor

### CLI

**Linux/macOS:**
```bash
# Default IP
python3 telescope_control_v2.py

# Custom IP
python3 telescope_control_v2.py 192.168.10.50

# Custom IP and port
python3 telescope_control_v2.py 192.168.10.50 11880

# From venv
source venv/bin/activate
skywatcher-cli
```

**Windows:**
```cmd
# Default IP
python telescope_control_v2.py

# Custom IP
python telescope_control_v2.py 192.168.10.50

# Custom IP and port  
python telescope_control_v2.py 192.168.10.50 11880

# From venv
venv\Scripts\activate.bat
skywatcher-cli
```

**Example session:**
```
> w 2              # Move up 2 seconds
> speed 2.5        # Set speed to 2.5°/sec
> d                # Move right (continuous)
> x                # Stop
> sethome          # Save current as home
> home             # Return to home
> p                # Show position
> info             # Mount details
> quit             # Exit
```

---

## 🔒 Safety

⚠️ **Important Safety Notes:**

1. **Always start with low speed** (0.5-1.0°/sec)
2. **Test movements** in safe area first
3. **Know your limit stops** - don't run into them
4. **Emergency stop** is always available (ESC key or E-Stop button)
5. **Monitor cable wrap** - avoid tangling
6. **Balanced mount** - ensure proper balance before slewing
7. **Clear obstacles** - check for obstructions
8. **Never leave unattended** while moving

---

## 🆘 Support

### Documentation
- README_FULL.md - Complete user guide
- PROTOCOL_REFERENCE.md - Technical protocol details
- WHATS_NEW.md - Version 2.0 changes

### Community
- GitHub: https://github.com/skywatcher-pacific/skywatcher_open
- Issues: Report bugs on GitHub

### Logs
Enable auto-update and check command log for debugging.

---

## 🪟 Windows Command Reference

### Virtual Environment

**Create:**
```cmd
python -m venv venv
```

**Activate (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Activate (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**Deactivate (both):**
```cmd
deactivate
```

### Running Applications

**After activating venv:**
```cmd
skywatcher-gui
skywatcher-cli
```

**Direct execution (no venv):**
```cmd
python telescope_gui_v2.py
python telescope_control_v2.py
```

### Common Tasks

**Check Python version:**
```cmd
python --version
```

**Check if tkinter is installed:**
```cmd
python -c "import tkinter; print('tkinter OK')"
```

**Find config file:**
```cmd
echo %USERPROFILE%\.skywatcher_controller\config.json
```

**View config file:**
```cmd
type %USERPROFILE%\.skywatcher_controller\config.json
```

**Open config folder in Explorer:**
```cmd
explorer %USERPROFILE%\.skywatcher_controller
```

### Troubleshooting

**Reset Python cache:**
```cmd
del /s /q __pycache__
del /s /q *.pyc
```

**Reinstall package:**
```cmd
venv\Scripts\activate.bat
pip uninstall skywatcher-controller
pip install -e .
```

**Full clean reinstall:**
```cmd
rmdir /s /q venv
python -m venv venv
venv\Scripts\activate.bat
pip install -e .
```

---

## 📝 License

MIT License - Free to use and modify

**Disclaimer:** This software is provided as-is with no warranty. Use at your own risk. Not affiliated with or endorsed by Sky-Watcher/Synta.

---

## 🎯 Tips

1. **First time setup:**
   - Connect in GUI
   - Query mount info
   - Set home position
   - Test all directions at low speed

2. **Regular use:**
   - Enable auto-update for monitoring
   - Use keyboard controls for quick moves
   - Save presets for common positions

3. **Advanced:**
   - Customize theme for night vision
   - Configure keyboard shortcuts
   - Adjust speed range for your needs

---

Clear skies! 🌟
