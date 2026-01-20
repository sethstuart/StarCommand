# SkyWatcher Controller - User Guide

Complete guide for using the SkyWatcher Virtuoso GTi telescope controller software.

---

## Table of Contents

1. [Introduction](#introduction)
2. [GUI Application](#gui-application)
3. [CLI Application](#cli-application)
4. [Configuration](#configuration)
5. [Advanced Features](#advanced-features)
6. [Safety Guidelines](#safety-guidelines)
7. [Troubleshooting](#troubleshooting)

---

## Introduction

This software provides professional-grade control of Sky-Watcher Virtuoso GTi telescope mounts through:

- **StarCommandGUI.py** - Full-featured graphical interface
- **StarCommandCLI.py** - Powerful command-line interface

Both versions share compatible configuration systems and work with the same mount hardware.

### System Requirements

- Python 3.7 or higher
- For GUI: tkinter (pre-installed with Python on Windows/macOS)
- Optional: ttkbootstrap for modern themes
- Network connection to telescope mount

---

## GUI Application

### Starting the GUI

```bash
python StarCommandGUI.py
```

### Main Interface

The GUI uses a tabbed layout with four main sections:

#### 1. Control Tab

**Connection Panel:**
- Enter IP address (default: 192.168.4.1)
- Enter port (default: 11880)
- Click "Connect" to establish connection
- Status indicator shows connection state

**Motion Control:**
- Direction pad with UP/DOWN/LEFT/RIGHT buttons
- STOP button for normal stop
- EMERGENCY STOP button for instant stop
- Speed slider (0.1 - 10.0 degrees/second)
- Speed display showing current rate

**Keyboard Controls:**
- W / ↑ : Move Up
- S / ↓ : Move Down
- A / ← : Move Left
- D / → : Move Right
- Space : Stop All
- Esc : Emergency Stop

**Control Modes:**
- **Latching Mode** (default): Click to start moving, click STOP to end
- **Momentary Mode**: Hold button/key to move, release to stop

**Axis Status:**
- Real-time status for both axes
- Shows: Running/Stopped, Blocked detection
- Color-coded indicators:
  - Gray: Unknown/Stopped
  - Blue: Moving
  - Red: Blocked (obstacle detected)

**Preset Positions:**
- **Go to Home**: Slew to saved home position
- **Set as Home**: Save current position as home
- **Go to Stow**: Slew to stow position (default: Alt 90°)
- **Set as Stow**: Save current position as stow
- **Zero Position**: Set current position to 0,0
- **Re-initialize**: Re-initialize mount axes

**Position Display:**
- Toggle display on/off
- Format options:
  - **Degrees**: Position in degrees (e.g., 45.1234°)
  - **Raw**: Position in encoder counts (e.g., 1,234,567)
  - **Both**: Degrees and counts (e.g., 45.12° (1,234,567))
  - **Coordinates**: Alt/Az format
- Auto-updates every second when connected
- Manual refresh button

**Activity Log:**
- Shows recent commands and events
- Timestamped entries
- Scrollable history

#### 2. Diagnostics Tab

**Mount Information:**
- Query system parameters
- View CPR (counts per revolution)
- Check timer frequency
- Display motor board versions

**Status Display:**
- Real-time axis status
- Detailed status bit breakdown
- Position information

**Auto-Update:**
- Enable continuous status updates
- Adjustable update rate (0.1 - 10 Hz)
- Useful for monitoring during operations

**Status Bits:**
- Bit 0 (0x01): Running
- Bit 1 (0x02): Blocked
- Bit 2 (0x04): Initialized

#### 3. Settings Tab

**Controls Sub-tab:**
- **Control Mode**: Choose between Latching and Momentary
- **Altitude Limits**:
  - Enforce limits checkbox
  - Minimum altitude (-10° to 45°, default: -5°)
  - Maximum altitude (45° to 90°, default: 90°)
  - Prevents movement beyond safe range
- **Keyboard Bindings**:
  - Customize all keyboard controls
  - Set keys for up/down/left/right/stop/estop
  - Save and apply immediately

**Theme Sub-tab** (requires ttkbootstrap):
- Select from built-in themes:
  - **Dark**: darkly, cyborg, vapor, solar, superhero
  - **Light**: flatly, journal, litera, minty, pulse, yeti, cosmo
- Apply theme immediately
- Theme saved for next session

**Connection Sub-tab:**
- Set default IP address
- Set default port
- Set connection timeout
- Settings applied on next connection

**Logging Sub-tab:**
- **Debug Mode**: Log all commands and responses
- **Log Retention**: Number of log files to keep (0-500)
  - Default: 30 files
  - Set to 0 to disable file logging
- View log folder location
- Open log folder button

### Workflow Examples

#### Basic Operation

1. Start application
2. Enter connection details (or use defaults)
3. Click "Connect"
4. Wait for "Connected" status
5. Use direction pad or keyboard to move
6. Adjust speed as needed
7. Click "Stop" or press Space to stop motion

#### Setting Home Position

1. Move telescope to desired home position
2. Click "Set as Home"
3. Position saved automatically
4. Click "Go to Home" anytime to return

#### Using Altitude Limits

1. Go to Settings → Controls
2. Check "Enforce altitude limits"
3. Set minimum (e.g., -5° to avoid hitting tripod)
4. Set maximum (e.g., 90° for zenith limit)
5. Save settings
6. Mount will refuse movements outside these limits

#### Monitoring During Observation

1. Connect to mount
2. Go to Diagnostics tab
3. Enable "Auto-update"
4. Set update rate (1-2 Hz recommended)
5. Watch real-time status during observation
6. Check for blocked status if movement stops

---

## CLI Application

### Starting the CLI

```bash
# Default IP
python StarCommandCLI.py

# Custom IP
python StarCommandCLI.py 192.168.10.50

# Custom IP and port
python StarCommandCLI.py 192.168.10.50 11880
```

### Command Reference

#### Movement Commands

```
w / up [seconds]      Move altitude UP
s / down [seconds]    Move altitude DOWN
a / left [seconds]    Move azimuth LEFT (counter-clockwise)
d / right [seconds]   Move azimuth RIGHT (clockwise)
x / stop              Stop all motion
e / estop             Emergency stop (instant)
```

**Examples:**
```
> w              # Move up continuously
> w 2            # Move up for 2 seconds then auto-stop
> d 5            # Move right for 5 seconds
> x              # Stop immediately
```

#### Speed Commands

```
+                     Increase speed by 0.5°/sec
-                     Decrease speed by 0.5°/sec
speed [value]         Set speed to specific value
speed                 Show current speed
```

**Examples:**
```
> +              # Increase to 1.5°/sec
> -              # Decrease to 1.0°/sec
> speed 2.5      # Set speed to 2.5°/sec
> speed          # Display: Current speed: 2.50°/sec
```

Speed limits: 0.1 - 10.0 degrees/second (configurable)

#### Position Commands

```
p / pos / position    Show current position
format [type]         Set display format
zero                  Set current position to 0,0
```

**Format types:**
- `degrees` - Show only degrees
- `raw` - Show only encoder counts  
- `both` - Show both (default)

**Examples:**
```
> p
Current Position:
  Azimuth:  123,456 counts (0x0001E240)
  Azimuth:  51.234567°
  Altitude: 67,890 counts (0x00010932)
  Altitude: 28.234567°

> format degrees
Position format: degrees

> p
Current Position:
  Azimuth:  51.234567°
  Altitude: 28.234567°
```

#### Preset Positions

```
home                  Go to saved home position
sethome               Save current position as home
stow                  Go to saved stow position
setstow               Save current position as stow
```

**Examples:**
```
> sethome            # Save current position
HOME set: Az=45.23°, Alt=30.12°

> home               # Return to saved position
Going to HOME

> setstow            # Save stow position
STOW set: Az=0.00°, Alt=90.00°

> stow               # Go to stow
Going to STOW
```

#### Information Commands

```
status                Show axis status
info                  Show mount information
version               Show software and firmware versions
config                Show current configuration
help / ?              Show command help
```

**Examples:**
```
> status
Mount Status:
  Azimuth: Stopped, Tracking, CW, Init: Yes
  Altitude: Running, Tracking, CW, Init: Yes

> info
Mount Information:

Azimuth Axis:
  CPR: 865,050 (0.00041618°/count)
  Position: 123,456 (51.234567°)

Timer Frequency: 16,000,000 Hz

> version
Software: SkyWatcher Controller v2.0 CLI
Azimuth Motor Board: 0336CF
Altitude Motor Board: 0336CF
```

#### Other Commands

```
quit / q / exit       Exit program
```

### CLI Workflow Examples

#### Quick Movement Session

```
> w 3                # Move up 3 seconds
Moving UP at 1.00°/sec
Stopped

> speed 2            # Increase speed
Speed set to 2.00°/sec

> d 5                # Move right 5 seconds
Moving RIGHT at 2.00°/sec
Stopped

> p                  # Check position
Current Position:
  Azimuth:  145.67°
  Altitude: 35.23°
```

#### Setting Up Positions

```
> # Move to home position manually
> w
> x
> a
> x

> # Save as home
> sethome
HOME set: Az=180.00°, Alt=45.00°

> # Move somewhere else
> d 10

> # Return home
> home
Going to HOME
```

#### Monitoring During Operation

```
> status             # Check current status
> p                  # Check position
> info               # Full mount details
```

---

## Configuration

### GUI Configuration

Stored in SQLite database: `~/.skywatcher_controller/settings.db`

**Accessing Settings:**
- Use Settings tab in GUI
- Settings save automatically
- Database created on first run

**Key Settings:**

| Setting | Default | Description |
|---------|---------|-------------|
| connection.ip | 192.168.4.1 | Mount IP address |
| connection.port | 11880 | UDP port |
| connection.timeout | 2.0 | Command timeout (seconds) |
| controls.mode | latching | Button mode (latching/momentary) |
| controls.up | w | Key for up movement |
| controls.down | s | Key for down movement |
| controls.left | a | Key for left movement |
| controls.right | d | Key for right movement |
| controls.stop | space | Key to stop |
| controls.estop | Escape | Emergency stop key |
| limits.enforce | True | Enforce altitude limits |
| limits.alt_min | -5.0 | Minimum altitude (degrees) |
| limits.alt_max | 90.0 | Maximum altitude (degrees) |
| logging.debug_mode | False | Enable debug logging |
| logging.retention | 30 | Number of log files to keep |
| theme.name | darkly | GUI theme (if ttkbootstrap) |

### CLI Configuration

Stored in JSON file: `~/.skywatcher_controller/config.json`

**Example config.json:**

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
    "home_az": 0.0,
    "home_alt": 0.0,
    "stow_az": 0.0,
    "stow_alt": 90.0
  },
  "display": {
    "position_format": "both"
  }
}
```

**Manual Editing:**

Linux/macOS:
```bash
nano ~/.skywatcher_controller/config.json
```

Windows:
```cmd
notepad %USERPROFILE%\.skywatcher_controller\config.json
```

**Resetting Configuration:**

Delete the config file and restart the application to restore defaults.

---

## Advanced Features

### Status Monitoring (GUI)

The GUI includes real-time status monitoring:

**Features:**
- 200ms polling interval
- Detects blocked motion
- Monitors running state
- Logs status changes automatically

**Status Indicators:**
- **Gray "Unknown"**: Not yet queried
- **Gray "Stopped"**: Motor not running
- **Blue "Moving"**: Motor running normally
- **Red "BLOCKED"**: Obstacle detected!

**Reading Status:**
Status byte format (hex):
- 0x00: Stopped, not initialized
- 0x01: Running
- 0x02: Blocked
- 0x04: Initialized
- 0x05: Running + Initialized
- 0x06: Blocked + Initialized

### Altitude Limits (GUI)

Prevents dangerous movements:

**Setup:**
1. Go to Settings → Controls
2. Enable "Enforce altitude limits"
3. Set minimum (to avoid hitting tripod/horizon)
4. Set maximum (to avoid cable wrap at zenith)

**Behavior:**
- Limits checked before each movement
- Movement blocked if it would exceed limits
- Warning message displayed
- Manual override not possible (safety feature)

**Recommended Settings:**
- Minimum: -5° (allows slightly below horizon)
- Maximum: 90° (prevents cable wrap above zenith)
- Adjust based on your setup

### File Logging (GUI)

Automatic logging with intelligent management:

**Log Location:**
`[script_directory]/logs/telescope_control_YYYYMMDD_HHMMSS.log`

**Log Levels:**
- **INFO**: General events (connection, movements)
- **STATUS**: Status changes
- **DEBUG**: All commands and responses (if debug mode enabled)

**Retention Management:**
- Automatically deletes old logs
- Keeps most recent N files (default: 30)
- Set to 0 to disable file logging
- Configurable in Settings → Logging

**Debug Mode:**
Enable to log every command and response:
1. Settings → Logging
2. Check "Debug Mode"
3. All protocol communication logged
4. Useful for troubleshooting

### Themes (GUI with ttkbootstrap)

**Installing ttkbootstrap:**
```bash
pip install ttkbootstrap
```

**Selecting Theme:**
1. Settings → Theme
2. Choose from dropdown
3. Click "Apply Theme"
4. Theme changes immediately

**Theme Categories:**
- **Dark themes**: Better for night vision
  - darkly (default), cyborg, vapor, solar, superhero
- **Light themes**: Better for daytime
  - flatly, journal, litera, minty, pulse, yeti

**Night Vision Tip:**
Use dark themes and reduce screen brightness for better night adaptation.

---

## Safety Guidelines

### Before Each Session

1. **Check Balance**: Ensure telescope is properly balanced
2. **Verify Limits**: Check altitude limit settings
3. **Test Movement**: Low speed test in all directions
4. **Know E-Stop**: Familiarize with emergency stop location/key
5. **Clear Cables**: Ensure cables won't snag
6. **Check Battery**: Verify adequate power (7.5V minimum, 12V recommended)

### During Operation

1. **Start Slow**: Begin with low speeds (0.5-1.0°/sec)
2. **Monitor Status**: Watch for blocked indicators
3. **Avoid Limits**: Don't run into mechanical stops
4. **Watch Cables**: Prevent cable wrap
5. **Stay Alert**: Never leave mount moving unattended

### Emergency Procedures

**If Mount Becomes Stuck:**
1. Press ESC or Emergency Stop button
2. Power off mount if needed
3. Manually move to safe position
4. Check for obstructions
5. Verify clutches are properly engaged

**If Software Freezes:**
1. Close application
2. Power cycle mount
3. Restart software
4. Re-connect and test

---

## Troubleshooting

### Connection Problems

**"Could not connect to telescope"**

1. Verify WiFi connection:
   ```bash
   ping 192.168.4.1
   ```

2. Check mount is powered on

3. Try alternative IP addresses:
   - AP mode: 192.168.4.1
   - Station mode: Check router

4. Verify port 11880 is not blocked:
   - Windows: Check Windows Firewall
   - Linux: `sudo ufw allow 11880/udp`

5. Test with CLI first (simpler debugging)

### Movement Issues

**Mount doesn't move when commanded:**

1. **Check clutches**: Must be tightened for motors to engage

2. **Verify initialization**:
   - GUI: Happens automatically on connect
   - CLI: Should show "✓ Axis initialized"

3. **Check altitude limits**:
   - GUI: Settings → Controls → check limits
   - May be blocking movement

4. **Battery voltage**: Need minimum 7.5V
   - Low battery = weak or no movement

5. **Enable debug logging**:
   - See exact commands and responses
   - Check for error responses

**Mount moves erratically:**

1. Check cable connections
2. Verify battery voltage
3. Look for loose components
4. Update mount firmware if available

**Blocked status appears:**

1. Check for physical obstructions
2. Verify gears are properly engaged
3. Check for binding in motion
4. May indicate hardware issue

### GUI-Specific Issues

**tkinter not found (Linux):**
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

**Themes not working:**
```bash
# Install ttkbootstrap
pip install ttkbootstrap

# Restart application
```

**Settings not saving:**
1. Check permissions on config directory
2. Verify `~/.skywatcher_controller/` is writable
3. Check disk space
4. Look for errors in activity log

### CLI-Specific Issues

**Config file not found:**
```bash
# Create directory
mkdir -p ~/.skywatcher_controller

# CLI will create config.json automatically
```

**Position shows "None":**
1. Check connection
2. Run `info` command to verify mount communication
3. Enable more verbose output if available

### Logging Issues

**Log files growing too large:**
1. Reduce retention count
2. Disable debug mode
3. Set retention to fewer files

**Can't find logs:**
```bash
# GUI logs location
ls [script_directory]/logs/

# Check most recent
ls -lt [script_directory]/logs/ | head
```

---

## Best Practices

### For Imaging Sessions

1. Set home position at target start
2. Use low speeds (0.5-1.0°/sec) for fine adjustments
3. Enable position display to monitor drift
4. Set altitude limits to prevent cable wrap
5. Keep emergency stop readily accessible

### For Visual Observation

1. Use higher speeds (2-5°/sec) for object acquisition
2. Switch to low speed for tracking adjustments
3. Use momentary mode for fine control
4. Set home at zenith for quick resets

### For Maintenance

1. Enable debug logging
2. Test each axis independently
3. Verify CPR values match specifications
4. Check for blocked status during full range of motion
5. Document any issues in logs

---

## Keyboard Shortcut Reference

### GUI Default Shortcuts

| Key | Action |
|-----|--------|
| W / ↑ | Move Up |
| S / ↓ | Move Down |
| A / ← | Move Left |
| D / → | Move Right |
| Space | Stop All |
| Esc | Emergency Stop |

**Note**: All keys configurable in Settings → Controls

### CLI Commands Quick Reference

| Command | Shortcut | Action |
|---------|----------|--------|
| up | w | Move up |
| down | s | Move down |
| left | a | Move left |
| right | d | Move right |
| stop | x | Stop all |
| estop | e | Emergency stop |
| position | p | Show position |
| quit | q | Exit |

---

## Support Resources

- **Documentation**: Check docs/ folder
- **Protocol Reference**: See PROTOCOL_REFERENCE.md
- **Installation Guide**: See INSTALL.md
- **GitHub Issues**: Report bugs and request features
- **Community**: Join discussions for tips and help

---

## Tips and Tricks

1. **Quick Position Check**: Press 'p' (CLI) or click Refresh (GUI) anytime

2. **Speed Presets**: Save frequently-used speeds in config

3. **Night Vision**: Use dark theme with minimal brightness

4. **Battery Monitor**: Check voltage before long sessions

5. **Cable Management**: Note azimuth rotations to prevent wrap

6. **Home Position**: Set home at balanced position for easy setup

7. **Debug Mode**: Enable when troubleshooting, disable for normal use

8. **Timed Movements**: Use CLI for precise duration movements

9. **Auto-Update**: Enable in Diagnostics tab during long observations

10. **Log Review**: Check logs after session to diagnose issues

---

**Clear skies and happy observing!** 🔭✨
