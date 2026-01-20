# SkyWatcher Virtuoso GTi Controller

Professional telescope control software for Sky-Watcher Virtuoso GTi mounts with both GUI and CLI interfaces.

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)]()

---

## 🌟 Features

### GUI Version (StarCommandGUI.py)
- **Modern Interface** - Clean tabbed layout with optional ttkbootstrap themes
- **Full Motion Control** - Direction pad with keyboard shortcuts (WASD/arrows)
- **Dual Control Modes** - Latching or momentary button operation
- **Safety Features** - Altitude limits, emergency stop, blocked motion detection
- **Real-time Monitoring** - Live status display with 200ms polling
- **Persistent Settings** - SQLite database for all configurations
- **Comprehensive Logging** - Automatic file logging with configurable retention
- **Position Management** - Home/stow positions, multiple display formats
- **Customizable** - Themes, keyboard bindings, connection settings

### CLI Version (StarCommandCLI.py)
- **Interactive Terminal** - Full-featured command-line interface
- **Timed Movements** - Execute movements for specific durations
- **Speed Control** - Adjustable slew rates with +/- shortcuts
- **Position Presets** - Save and recall home/stow positions
- **Multiple Formats** - Display positions as degrees, raw counts, or both
- **Configuration** - JSON-based settings that persist across sessions
- **Minimal Dependencies** - Pure Python with no external packages

---

## 🚀 Quick Start

### Installation

**Option 1: Automated (Recommended)**

Linux/macOS:
```bash
chmod +x install.sh
./install.sh
source venv/bin/activate
python StarCommandGUI.py
```

Windows (PowerShell):
```powershell
.\install.ps1
.\venv\Scripts\Activate.ps1
python StarCommandGUI.py
```

Windows (Command Prompt):
```cmd
install.bat
venv\Scripts\activate.bat
python StarCommandGUI.py
```

**Option 2: Direct Execution**

```bash
# GUI
python StarCommandGUI.py

# CLI
python StarCommandCLI.py [ip] [port]
```

### First Connection

1. Power on your Sky-Watcher mount
2. Connect to the mount's WiFi network (usually "SynScan_XXX")
3. Run the application
4. Default IP: `192.168.4.1`, Port: `11880`
5. Click "Connect" and start exploring!

---

## 📖 Documentation

- **[Installation Guide](docs/INSTALL.md)** - Detailed setup instructions for all platforms
- **[User Guide](docs/USER_GUIDE.md)** - Complete feature documentation
- **[Protocol Reference](docs/PROTOCOL_REFERENCE.md)** - Technical protocol details
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

---

## 🎮 Usage

### GUI Controls

**Keyboard Shortcuts:**
- `W` / `↑` - Move Up
- `S` / `↓` - Move Down  
- `A` / `←` - Move Left
- `D` / `→` - Move Right
- `Space` - Stop All Motion
- `Esc` - Emergency Stop

**Control Modes:**
- **Latching** - Click to start, click stop to end
- **Momentary** - Hold button/key to move, release to stop

### CLI Commands

```
Movement:
  w/up [seconds]     Move up (optional timed duration)
  s/down [seconds]   Move down
  a/left [seconds]   Move left
  d/right [seconds]  Move right
  x/stop             Stop all motion
  e/estop            Emergency stop

Speed:
  +                  Increase speed
  -                  Decrease speed
  speed [value]      Set specific speed

Position:
  p                  Show current position
  format [type]      Set display format (degrees/raw/both)
  zero               Set current position to 0,0

Presets:
  home               Go to home position
  sethome            Set current position as home
  stow               Go to stow position
  setstow            Set current position as stow

Info:
  status             Show mount status
  info               Show mount information
  version            Show version info
  config             Show configuration

help/?               Show this help
quit/q               Exit program
```

---

## ⚙️ Configuration

Configuration is stored in:
- **Linux/macOS:** `~/.skywatcher_controller/`
- **Windows:** `%USERPROFILE%\.skywatcher_controller\`

### GUI Settings

Located in SQLite database (`settings.db`):

```python
# Connection settings
connection.ip = "192.168.4.1"
connection.port = "11880"
connection.timeout = "2.0"

# Control settings
controls.mode = "latching"  # or "momentary"
controls.up = "w"
controls.down = "s"
# ... etc

# Altitude limits
limits.enforce = True
limits.alt_min = -5.0
limits.alt_max = 90.0

# Logging
logging.debug_mode = False
logging.retention = 30  # Keep last 30 log files
```

### CLI Settings

Located in JSON file (`config.json`):

```json
{
  "connection": {
    "ip": "192.168.4.1",
    "port": 11880,
    "timeout": 2.0
  },
  "speed": {
    "default": 1.0,
    "min": 0.1,
    "max": 10.0
  },
  "positions": {
    "home_az": 0,
    "home_alt": 0,
    "stow_az": 0,
    "stow_alt": 90
  },
  "display": {
    "position_format": "both"
  }
}
```

---

## 🎨 Themes (GUI Only)

### Built-in Themes (with ttkbootstrap)

Install ttkbootstrap for modern themes:
```bash
pip install ttkbootstrap
```

**Dark Themes:** darkly, cyborg, vapor, solar, superhero
**Light Themes:** flatly, journal, litera, minty, pulse, yeti

Select theme in **Settings → Theme** tab.

### Without ttkbootstrap

Standard tkinter interface with classic styling.

---

## 🔧 Technical Details

### Supported Hardware
- Sky-Watcher Virtuoso GTi 150P
- Sky-Watcher Virtuoso GTi mounts
- Other SynScan-compatible mounts (may require testing)

### Protocol
- UDP communication on port 11880
- SynScan motor controller protocol (simplified format)
- Commands: `:j`, `:e`, `:G`, `:I`, `:J`, `:K`, `:L`, etc.
- See [Protocol Reference](docs/PROTOCOL_REFERENCE.md) for details

### Requirements
- **Python:** 3.7 or higher
- **GUI:** tkinter (usually pre-installed)
- **Optional:** ttkbootstrap for modern themes
- **No other dependencies!**

---

## 🛡️ Safety Features

### GUI
- **Altitude Limits** - Prevent movement beyond safe altitude range
- **Emergency Stop** - Instant stop button + ESC key
- **Status Monitoring** - Real-time blocked motion detection
- **Visual Feedback** - Status indicators show mount state

### CLI
- **Emergency Stop** - Dedicated `e` command
- **Speed Limits** - Configurable min/max speeds
- **Confirmation** - Critical actions require confirmation

---

## 📊 Logging (GUI Only)

Logs are automatically saved to `logs/` directory with:
- Timestamped filenames
- Configurable retention (default: 30 files)
- Debug mode for detailed command logging
- Automatic cleanup of old logs

Log location: `[script directory]/logs/telescope_control_YYYYMMDD_HHMMSS.log`

---

## 🐛 Troubleshooting

### Connection Issues

**Mount not responding:**
1. Verify WiFi connection to mount
2. Check IP address (try `192.168.4.1`)
3. Ensure mount is powered on
4. Try pinging: `ping 192.168.4.1`
5. Check firewall settings

**Commands fail with error `!1`:**
- Ensure axes are initialized (happens automatically on connect)
- Power cycle the mount
- Check command format in debug logs

**Mount doesn't move:**
1. Check clutches are tightened
2. Verify battery voltage (minimum 7.5V recommended)
3. Enable debug logging to see command responses
4. Check altitude limits aren't blocking movement

### GUI Issues

**tkinter not found:**
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# macOS
brew install python-tk

# Windows - reinstall Python with tcl/tk option
```

**ttkbootstrap themes not working:**
```bash
pip install ttkbootstrap
# Restart application
```

### CLI Issues

**Config file not saving:**
- Check permissions on `~/.skywatcher_controller/`
- Ensure directory exists and is writable

**Position display shows "None":**
- Connection issue - check mount communication
- Try querying mount info with `info` command

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Test your changes thoroughly
4. Submit a pull request with clear description

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/skywatcher-controller.git
cd skywatcher-controller

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install in development mode
pip install -e .

# Run tests
python -m pytest  # if you add tests
```

---

## 📝 Version History

### v0.4.2 (Current - GUI)
- Fixed activity log flooding with protocol traffic
- Separated UI logging from protocol logging (protocol → file only)
- Fixed ttkbootstrap deprecation warnings (updated imports)
- Removed invalid theme 'cerulean' from list
- Wild position values filtered out (sanity checking)
- Fixed text contrast issues in dark themes
- Added collapsible activity log on Control tab
- Added dedicated "Comms Log" tab for protocol debugging with search/filter
- Added protocol logging toggle in settings
- Added position value sanity checking (filters corrupted packets)

### v0.4.1 (GUI)
- Added altitude movement limits with enforcement
- Logging uses dedicated 'logs' folder (auto-created)
- Added log retention setting (0-500 files, default 30)
- Modernized GUI using ttkbootstrap (optional)
- Added theme selector for built-in themes
- Improved visual consistency and flat design

### v0.4.0 (GUI)
- SQLite persistence for settings
- Momentary/latching control modes
- Combined diagnostics tab
- Status monitoring with 200ms polling

### v2.0 (CLI)
- Enhanced command set
- Configuration file support
- Home/stow position presets
- Multiple position display formats
- Timed movement execution

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

**Disclaimer:** This software is provided as-is with no warranty. Use at your own risk. Not affiliated with or endorsed by Sky-Watcher/Synta Technology.

---

## 🙏 Acknowledgments

- Sky-Watcher/Synta Technology for the SynScan protocol
- ttkbootstrap project for modern tkinter themes
- Community contributors and testers

---

## 📧 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/skywatcher-controller/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/skywatcher-controller/discussions)
- **Documentation:** [Wiki](https://github.com/yourusername/skywatcher-controller/wiki)

---

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

---

**Clear skies!** 🔭✨
