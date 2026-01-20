# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

StarCommand is a professional telescope controller for Sky-Watcher Virtuoso GTi 150P mounts. Version 0.4.2 provides both GUI (StarCommandGUI.py) and CLI (StarCommandCLI.py) interfaces for WiFi-based telescope control with SQLite persistence, real-time protocol debugging, and customizable themes.

## Key Commands

### Installation & Setup

```bash
# Automated installation
./install.sh          # Linux/macOS
.\install.ps1         # Windows PowerShell
install.bat           # Windows Command Prompt

# Manual virtual environment setup
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate.bat  # Windows
pip install -e .

# Optional: Install ttkbootstrap for professional themes
pip install ttkbootstrap
```

### Running the Applications

```bash
# GUI (requires tkinter, optional ttkbootstrap)
python StarCommandGUI.py

# CLI (no dependencies - pure Python stdlib)
python StarCommandCLI.py [ip] [port]

# After pip install
starcommand-gui
starcommand-cli
```

### Development

```bash
# No build step required - pure Python
# No test suite currently in repository
# No linting configuration present

# View logs
ls logs/
tail -f logs/telescope_control_*.log
```

## Code Architecture

### High-Level Component Structure

```
StarCommandGUI.py (1890 lines)
├── DatabaseConfig - SQLite persistent settings
├── FileLogger - Timestamped file logging with retention
├── CommsBuffer - Thread-safe protocol communication log
├── StatusDecoder - Decodes motor status bytes
├── StatusMonitor - 200ms background status polling thread
├── SkyWatcherProtocol - Core UDP protocol implementation
└── TelescopeGUI - 4-tab tkinter interface

StarCommandCLI.py (600 lines)
├── Config - JSON configuration manager
├── SkyWatcherProtocol - Simplified protocol class
└── interactive_mode() - REPL command interface
```

### Main Classes & Responsibilities

**DatabaseConfig** (lines 90-184):
- SQLite database at `~/.skywatcher_controller/settings.db`
- Manages all persistent settings: connection, controls, limits, display, positions, theme, logging
- Methods: `get()`, `get_int()`, `get_float()`, `get_bool()`, `set()`

**FileLogger** (lines 186-264):
- Creates logs in `logs/` directory with format: `telescope_control_YYYYMMDD_HHMMSS.log`
- Automatic retention management (default: keep last 30 files)
- Thread-safe with millisecond timestamps

**CommsBuffer** (lines 267-327):
- Circular deque (5000 entry max) for protocol traffic
- Powers the "Comms Log" tab with search/filter capabilities
- Thread-safe for concurrent access from protocol and GUI threads

**StatusMonitor** (lines 352-402):
- Background thread polling axis status every 200ms
- Detects state changes (Running, Blocked, Initialized)
- Logs transitions to file for debugging

**SkyWatcherProtocol** (lines 405-629):
Core protocol handler - **14 key methods**:
- `send_command()` - UDP transmission with logging
- `get_position()` - Query axis position (24-bit with 0x800000 offset)
- `set_motion_mode()` - Configure tracking/GOTO, CW/CCW
- `set_step_period()` - Set speed via timer frequency
- `start_motion()`, `stop_motion()`, `emergency_stop()`
- `slew_fixed_rate()` - High-level speed control
- `goto_position()` - High-level position control
- `get_counts_per_revolution()`, `get_timer_frequency()`, `get_status()`

**TelescopeGUI** (lines 634-1890):
Main application with 4 tabs:
1. **Control** - Connection, motion pad, speed slider, presets, status display
2. **Comms Log** - Real-time protocol debugging with search/regex filter
3. **Diagnostics** - Mount info, status refresh, auto-update toggle
4. **Settings** - Controls, Theme, Connection, Logging configuration

### Data Flow

```
User Input (Button/Keyboard)
    → TelescopeGUI event handler
    → DatabaseConfig (load settings, check limits)
    → SkyWatcherProtocol calculation (degrees → motor counts)
    → UDP send to 192.168.4.1:11880
    → CommsBuffer logging (GUI display)
    → FileLogger logging (disk persistence)
    → Mount execution
    → Response reception & parsing
    → GUI update (position display, status)
    → DatabaseConfig save (if settings changed)
```

### Configuration System

**Two implementations:**
- GUI: SQLite database (`~/.skywatcher_controller/settings.db`)
- CLI: JSON file (`~/.skywatcher_controller/config.json`)

**Key settings:**
```python
connection.ip = '192.168.4.1'
connection.port = 11880
controls.up/down/left/right = 'w'/'s'/'a'/'d'
controls.stop = 'space'
controls.estop = 'Escape'
limits.alt_min/alt_max = -5.0 / 90.0
limits.enforce = True
theme.name = 'darkly'  # or cyborg, vapor, superhero, etc.
logging.retention = 30  # files to keep
```

### Dependencies

**Minimal dependency philosophy:**

StarCommandGUI.py:
- `tkinter` (bundled with Python)
- `sqlite3` (Python stdlib)
- `ttkbootstrap` (OPTIONAL - graceful fallback to vanilla tkinter)

StarCommandCLI.py:
- **Zero external dependencies** - pure Python stdlib

If ttkbootstrap unavailable, GUI uses plain ttk styling but remains fully functional.

## Protocol Implementation Details

### Critical Protocol Facts

1. **Initialization is mandatory**: After connection, send `:F1\r` (azimuth) and `:F2\r` (altitude) or mount ignores commands
2. **`:G` command format**: 3 characters after axis, e.g., `:G210\r` NOT `:G20100\r` (common bug in older versions)
3. **Position encoding**: 24-bit signed integer with 0x800000 offset (add before send, subtract on receive)
4. **Byte order**: LSB-first hexadecimal (e.g., 0x1A02 becomes "021A00")
5. **Command termination**: All commands end with `\r` (carriage return only, no `\n`)

### Mode Codes (for `:G` command)

```python
# Format: :G<axis><mode_code>\r
"00" = High-speed GOTO, clockwise
"01" = High-speed GOTO, counter-clockwise
"10" = Low-speed tracking, clockwise
"11" = Low-speed tracking, counter-clockwise
"20" = Low-speed GOTO, clockwise
"21" = Low-speed GOTO, counter-clockwise
```

### Axis Mapping

- Axis 1: Azimuth (horizontal rotation)
- Axis 2: Altitude (vertical rotation)

### Position Sanity Checking

GUI implements corruption filtering (lines 1285-1293):
- Azimuth: -720° to +720° (allows 2 full rotations)
- Altitude: -90° to +180° (allows some overflow)
- Rejects wild values from corrupted UDP packets

## Important Development Notes

### File Organization

**Current working files:**
- [StarCommandGUI.py](StarCommandGUI.py) - Primary GUI application (v0.4.2)
- [StarCommandCLI.py](StarCommandCLI.py) - CLI alternative
- [logs/](logs/) - Runtime logs with automatic retention

**Outdated files to ignore:**
- `venv/` - May be out of date, regenerate with install scripts
- `tools_old/` - Legacy development files
- `setup.py` - References old module names (`telescope_gui_v2`, `telescope_control_v2`)

### Version History

**v0.4.2 (current):**
- Fixed activity log flooding
- Separated UI vs protocol logging
- Position sanity checking for corrupted packets
- Collapsible activity log
- Dedicated Comms Log tab with search

**v0.4.1:**
- Altitude limits enforcement
- ttkbootstrap theme support

**v0.4.0:**
- SQLite configuration persistence
- Momentary vs latching control modes

### Common Gotchas

1. **setup.py is outdated** - References `telescope_gui_v2.py` and `telescope_control_v2.py` which don't exist in this repo (renamed to StarCommand*.py)
2. **Altitude limits** - Default enforcement prevents movement below -5° or above 90° (configurable)
3. **Thread safety** - StatusMonitor runs in background, always use locks when updating shared state
4. **Logging retention** - Default 30 files, but large test sessions can accumulate quickly (check logs/ directory size)
5. **ttkbootstrap deprecation** - Import paths changed; code uses fallback (lines 42-61)

### Safety Features

- Emergency stop on both axes (ESC key binding)
- Altitude limit enforcement to prevent cable wrapping
- Socket timeout (2 seconds default)
- Position validation with sanity checking
- Status monitoring for blocked/stalled conditions

## Testing & Debugging

### Enable Protocol Logging

In GUI:
1. Settings tab → Logging sub-tab → Enable "Show Protocol Traffic"
2. View real-time in Comms Log tab
3. Search using plain text or regex

In CLI:
- Protocol logging prints to stdout during commands

### Log Analysis

```bash
# View latest log
tail -n 100 logs/telescope_control_$(ls -t logs/ | head -1)

# Search for errors
grep -i error logs/*.log

# Find connection issues
grep "SEND\|RECV" logs/telescope_control_*.log | less
```

### Common Debug Scenarios

**Mount not responding:**
1. Check connection (ping 192.168.4.1)
2. Verify initialization commands sent (`:F1\r`, `:F2\r`)
3. Review Comms Log for error responses (`!1` = invalid command)

**Position drift:**
1. Enable auto-update in Diagnostics tab
2. Monitor status byte changes
3. Check for BLOCKED status (0x02 bit set)

**Wild position values:**
1. Check Comms Log for malformed responses
2. Sanity checker should filter (see logs for "rejected position")

## Related Documentation

- [docs/INSTALL.md](docs/INSTALL.md) - Comprehensive installation guide (695 lines)
- [docs/FINAL_FIX_SUMMARY.md](docs/FINAL_FIX_SUMMARY.md) - Protocol bug fixes from v0.4.2
- [docs/SUMMARY.md](docs/SUMMARY.md) - Version changelog
- `docs/skywatcher_motor_controller_command_set.pdf` - Official motor protocol
- `docs/synscan_app_protocol_20250930.pdf` - Complete SynScan spec
