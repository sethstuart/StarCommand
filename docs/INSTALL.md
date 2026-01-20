# SkyWatcher Controller - Installation & Setup Guide

Complete professional telescope control suite with GUI and CLI interfaces.

**Applications**:
- **StarCommandGUI.py** - Full-featured graphical interface (v0.4.1)
- **StarCommandCLI.py** - Command-line interface (v2.0)

---

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
python StarCommandGUI.py

# OR run CLI
python StarCommandCLI.py
```

#### Windows (PowerShell)

```powershell
# If you get execution policy errors, run PowerShell as Administrator:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run installer
.\install.ps1

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run GUI
python StarCommandGUI.py

# OR run CLI
python StarCommandCLI.py
```

#### Windows (Command Prompt / Batch)

```cmd
# Run installer
install.bat

# Activate virtual environment
venv\Scripts\activate.bat

# Run GUI
python StarCommandGUI.py

# OR run CLI
python StarCommandCLI.py
```

### Method 2: Direct Execution (No Virtual Environment)

#### Linux / macOS

```bash
# GUI
python3 StarCommandGUI.py

# CLI
python3 StarCommandCLI.py [ip] [port]
```

#### Windows

```cmd
# GUI
python StarCommandGUI.py

# CLI
python StarCommandCLI.py [ip] [port]
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

### Optional: Modern Themes (GUI)

For modern, professional themes in the GUI:

```bash
pip install ttkbootstrap
```

This provides beautiful dark and light themes. Without it, the GUI uses standard tkinter styling.

**CLI version has no dependencies!** (Pure Python stdlib)

---

## 🎨 GUI Version Features (StarCommandGUI.py)

### Main Features
✅ **Tabbed Interface**
  - **Control Tab**: Direction pad, speed control, preset positions
  - **Diagnostics Tab**: Mount status, auto-update capability  
  - **Settings Tab**: Keyboard controls, themes, connection settings, logging

✅ **Full Keyboard Support**
  - WASD or Arrow keys for movement
  - Space to stop
  - ESC for emergency stop
  - All keys configurable!

✅ **Control Modes**
  - **Latching**: Click to start, click stop to end
  - **Momentary**: Hold to move, release to stop

✅ **Safety Features**
  - Altitude limits (min/max) with enforcement
  - Emergency stop (button + ESC key)
  - Real-time blocked motion detection
  - Status monitoring (200ms polling)

✅ **Configurable Themes** (with ttkbootstrap)
  - Dark themes: darkly, cyborg, vapor, solar, superhero
  - Light themes: flatly, journal, litera, minty, pulse, yeti
  - Persistent theme selection

✅ **Position Display Options**
  - Degrees
  - Raw counts
  - Both (degrees + counts)
  - Alt/Az coordinates

✅ **Preset Positions**
  - Home position (set/goto)
  - Stow position (set/goto)
  - Saved to database

✅ **Comprehensive Logging**
  - Automatic file logging to `logs/` directory
  - Configurable retention (0-500 files, default 30)
  - Debug mode for detailed command logging
  - Automatic cleanup of old logs

✅ **SQLite Configuration**
  - All settings saved to database
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

**All configurable in Settings → Controls tab!**

---

## 💻 CLI Version Features (StarCommandCLI.py)

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

CLI uses JSON config file: 

**Linux/macOS**: `~/.skywatcher_controller/config.json`  
**Windows**: `%USERPROFILE%\.skywatcher_controller\config.json`

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

### Keyboard Controls (GUI)

**GUI:** Settings Tab → Controls

Configure any key for any action. Changes apply immediately after saving.

### Theme Customization (GUI)

**GUI:** Settings Tab → Theme

Choose from built-in ttkbootstrap themes (requires `pip install ttkbootstrap`):
- **Dark**: darkly, cyborg, vapor, solar, superhero  
- **Light**: flatly, journal, litera, minty, pulse, yeti

Theme changes apply immediately.

### Altitude Limits (GUI)

**GUI:** Settings Tab → Controls

Set minimum and maximum altitude limits to prevent dangerous movements:
- Default minimum: -5°
- Default maximum: 90°
- Enforcement can be toggled on/off

### Logging (GUI)

**GUI:** Settings Tab → Logging

Configure file logging:
- **Debug Mode**: Log all commands and responses
- **Retention**: Number of log files to keep (0-500)
  - Default: 30 files
  - Set to 0 to disable file logging

Logs stored in: `[script_directory]/logs/`

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
   python StarCommandCLI.py 192.168.4.1 11880
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
rm -rf ~/.skywatcher_controller/
```

Windows (PowerShell):
```powershell
Remove-Item -Recurse -Force $env:USERPROFILE\.skywatcher_controller
```

**Check config location:**

Linux/macOS:
```bash
ls -la ~/.skywatcher_controller/
```

Windows:
```cmd
dir %USERPROFILE%\.skywatcher_controller\
```

---

## 📁 File Structure

```
skywatcher-controller/
├── StarCommandGUI.py         # GUI application (v0.4.1)
├── StarCommandCLI.py         # CLI application (v2.0)
├── setup.py                  # Package setup (optional)
├── requirements.txt          # Dependencies (optional for themes)
├── install.sh               # Linux/Mac installer
├── install.ps1              # Windows PowerShell installer
├── install.bat              # Windows batch installer
├── README.md                # Project overview
├── docs/
│   ├── INSTALL.md           # This file
│   ├── USER_GUIDE.md        # Complete user guide
│   ├── PROTOCOL_REFERENCE.md # Protocol documentation
│   ├── TROUBLESHOOTING.md   # Troubleshooting guide
│   └── FINAL_FIX_SUMMARY.md # Technical fixes summary
└── logs/                    # Created automatically by GUI
    └── telescope_control_*.log

~/.skywatcher_controller/     # Linux/Mac config location
├── settings.db              # GUI configuration (SQLite)
└── config.json              # CLI configuration

%USERPROFILE%\.skywatcher_controller\  # Windows config location
├── settings.db              # GUI configuration
└── config.json              # CLI configuration
```

---

## 🚦 Usage Examples

### GUI

**Linux/macOS:**
```bash
# Direct run
python3 StarCommandGUI.py

# From venv
source venv/bin/activate
python StarCommandGUI.py
```

**Windows:**
```cmd
# Direct run
python StarCommandGUI.py

# From venv
venv\Scripts\activate.bat
python StarCommandGUI.py
```

**Workflow:**
1. Enter IP (defaults to 192.168.4.1)
2. Click "Connect"
3. Use direction pad or WASD keys
4. Adjust speed slider
5. Set home position
6. Configure settings as needed

### CLI

**Linux/macOS:**
```bash
# Default IP
python3 StarCommandCLI.py

# Custom IP
python3 StarCommandCLI.py 192.168.10.50

# Custom IP and port
python3 StarCommandCLI.py 192.168.10.50 11880
```

**Windows:**
```cmd
# Default IP
python StarCommandCLI.py

# Custom IP
python StarCommandCLI.py 192.168.10.50
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
9. **Altitude limits** - set appropriate limits in GUI
10. **Battery voltage** - maintain adequate power (7.5V minimum)

---

## 🆘 Support

### Documentation
- [User Guide](USER_GUIDE.md) - Complete feature documentation
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
- [Protocol Reference](PROTOCOL_REFERENCE.md) - Technical protocol details

### Community
- GitHub Issues: Report bugs
- GitHub Discussions: Ask questions and share tips

### Logs (GUI)
Located in `[script_directory]/logs/`
- Enable debug mode for detailed troubleshooting
- Check logs after any issues
- Include relevant log excerpts when reporting problems

---

## 📝 License

MIT License - Free to use and modify

**Disclaimer:** This software is provided as-is with no warranty. Use at your own risk. Not affiliated with or endorsed by Sky-Watcher/Synta.

---

## 🎯 Tips

1. **First time setup:**
   - Connect with GUI first (easier)
   - Query mount info in Diagnostics tab
   - Set home position
   - Test all directions at low speed
   - Configure altitude limits for safety

2. **Regular use:**
   - Use keyboard controls for quick moves
   - CLI for scripting and automation
   - GUI for interactive control and monitoring
   - Save presets for common positions

3. **Advanced:**
   - Customize theme for night vision
   - Configure keyboard shortcuts to your preference
   - Adjust altitude limits for your setup
   - Use debug logging when troubleshooting

4. **Performance:**
   - Disable debug mode when not needed
   - Adjust auto-update rate if needed
   - Reduce log retention for less disk usage

---

Clear skies! 🌟
