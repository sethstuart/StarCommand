# Troubleshooting Guide

Comprehensive troubleshooting for the SkyWatcher telescope controller software.

---

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Movement Problems](#movement-problems)
3. [Platform-Specific Issues](#platform-specific-issues)
4. [Configuration Problems](#configuration-problems)
5. [Performance Issues](#performance-issues)
6. [Error Messages](#error-messages)
7. [Hardware Issues](#hardware-issues)
8. [Diagnostic Tools](#diagnostic-tools)

---

## Connection Issues

### Cannot Connect to Telescope

**Symptom**: "Could not connect to telescope" error

**Solutions**:

1. **Verify WiFi Connection**
   ```bash
   # Test connectivity
   ping 192.168.4.1
   ```
   - Should get replies
   - If timeout, not connected to mount WiFi

2. **Check Mount Power**
   - Is mount powered on?
   - Battery voltage adequate (7.5V minimum)?
   - Power LED lit?

3. **Verify IP Address**
   - **AP Mode**: 192.168.4.1 (default)
   - **Station Mode**: Check your router
   - Try both possibilities

4. **Check Port Number**
   - Default: 11880 (motor control)
   - Some apps use: 11881 (SynScan protocol)
   - Try both if unsure

5. **Firewall Settings**
   
   Windows:
   ```powershell
   # Allow UDP port 11880
   New-NetFirewallRule -DisplayName "SkyWatcher" -Direction Outbound -LocalPort 11880 -Protocol UDP -Action Allow
   ```
   
   Linux:
   ```bash
   # Ubuntu/Debian
   sudo ufw allow 11880/udp
   
   # Check status
   sudo ufw status
   ```

6. **Try CLI First**
   ```bash
   python StarCommandCLI.py
   ```
   - Simpler debugging
   - More detailed error messages

### Connected But No Response

**Symptom**: Connection succeeds but commands fail or timeout

**Solutions**:

1. **Check Debug Logs**
   - GUI: Enable debug mode in Settings → Logging
   - Look for response patterns
   - Check for error codes

2. **Verify Protocol**
   - Mount must use standard SynScan protocol
   - Some mounts have different firmware
   - Check your model compatibility

3. **Test Basic Command**
   ```python
   # Manually test version query
   python -c "
   import socket
   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   s.settimeout(2.0)
   s.sendto(b':e1\r', ('192.168.4.1', 11880))
   print(s.recvfrom(1024)[0].decode('ascii'))
   "
   ```
   - Should return version string like "=0336CF"

4. **Power Cycle Mount**
   - Turn off completely
   - Wait 10 seconds
   - Power back on
   - Reconnect

5. **Reset Network**
   - Disconnect from mount WiFi
   - Forget network
   - Reconnect fresh

### Intermittent Connection

**Symptom**: Connection drops randomly

**Solutions**:

1. **Check Signal Strength**
   - Move closer to mount
   - Remove obstacles
   - Check for interference

2. **Battery Voltage**
   - Low battery can cause WiFi issues
   - Check voltage under load
   - Replace/recharge if below 11V

3. **Timeout Setting**
   - Increase timeout in settings
   - Default: 2.0 seconds
   - Try: 3.0-5.0 seconds

4. **Other WiFi Devices**
   - Disconnect other devices from mount WiFi
   - Check for conflicting networks nearby

---

## Movement Problems

### Mount Doesn't Move

**Symptom**: Commands accepted but mount doesn't physically move

**Checklist**:

1. **Clutches**
   - ✓ Azimuth clutch tightened
   - ✓ Altitude clutch tightened
   - **Most common issue!**

2. **Battery Voltage**
   - Need minimum 7.5V
   - Recommended: 12V
   - Check voltage under load
   - Low voltage = weak/no movement

3. **Initialization**
   - GUI: Automatic on connect
   - CLI: Check for "✓ Axis initialized" message
   - Try reconnecting if missing

4. **Altitude Limits** (GUI only)
   - Check Settings → Controls
   - "Enforce altitude limits" may be blocking
   - Verify current position within limits
   - Temporarily disable to test

5. **Blocked Status**
   - Check status indicators
   - Red "BLOCKED" means obstruction detected
   - Clear obstruction and retry

6. **Debug Logging**
   ```
   Enable debug mode:
   - GUI: Settings → Logging → Debug Mode
   - Check logs for command responses
   - Look for error codes (!0, !1, !2, etc.)
   ```

### Movement in Wrong Direction

**Symptom**: Mount moves opposite to commanded direction

**Solutions**:

1. **Check Orientation**
   - Is mount oriented correctly?
   - Azimuth axis vertical?
   - Altitude axis horizontal?

2. **Hemisphere Setting**
   - Some mounts have N/S hemisphere setting
   - Check mount manual
   - May affect direction interpretation

3. **Swap Commands**
   - If consistent, you can swap key bindings
   - GUI: Settings → Controls
   - Swap up/down or left/right as needed

### Erratic Movement

**Symptom**: Mount moves unpredictably or jerkily

**Solutions**:

1. **Cable Issues**
   - Check all cable connections
   - Look for loose connectors
   - Wiggle test each cable

2. **Battery Problems**
   - Voltage dropping under load
   - Check connections
   - Try different power source

3. **Mechanical Issues**
   - Listen for grinding noises
   - Check gear mesh
   - Look for debris in gears
   - Check for binding

4. **Firmware**
   - Check for firmware updates
   - May need official SynScan update

### Speed Issues

**Symptom**: Mount moves too slow/fast or speed doesn't change

**Solutions**:

1. **Speed Limits**
   - Check min/max in config
   - Default range: 0.1 - 10.0°/sec
   - Adjust if needed

2. **CPR Verification**
   - Query CPR value: `info` command (CLI) or Diagnostics tab (GUI)
   - Should be 865,050 for GTi 150P
   - If wrong, may indicate communication issue

3. **Timer Frequency**
   - Should be 16,000,000 Hz
   - Check in diagnostics
   - If wrong, power cycle mount

### Emergency Stop Not Working

**Symptom**: E-stop doesn't immediately stop mount

**Solutions**:

1. **Network Latency**
   - Command must travel over WiFi
   - Can have slight delay
   - Expected: <100ms

2. **Power Kill**
   - If E-stop fails, turn off mount power
   - This is ultimate safety backup

3. **Check Key Binding**
   - Verify ESC key mapped correctly
   - GUI: Settings → Controls
   - Test mapping with normal stop first

---

## Platform-Specific Issues

### Windows Issues

#### PowerShell Execution Policy

**Error**: "cannot be loaded because running scripts is disabled"

**Solution**:
```powershell
# Set policy for current user (no admin needed)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or use batch file instead
install.bat
```

#### Python Not Found

**Error**: "'python' is not recognized"

**Solutions**:

1. **Reinstall Python**
   - Download from python.org
   - **Check "Add Python to PATH"** during install
   - Restart terminal after install

2. **Manual PATH**
   ```cmd
   # Find Python
   where python
   
   # If not found, add to PATH manually
   # Control Panel → System → Advanced → Environment Variables
   # Add: C:\Users\YourName\AppData\Local\Programs\Python\Python3X
   ```

#### tkinter Not Available

**Error**: "No module named 'tkinter'"

**Solution**:
1. Reinstall Python from python.org
2. During installation, click "Customize"
3. Ensure "tcl/tk and IDLE" is checked
4. Complete installation
5. Verify: `python -c "import tkinter; print('OK')"`

### Linux Issues

#### tkinter Not Installed

**Error**: "No module named 'tkinter'"

**Solutions**:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-tk

# Fedora/RHEL
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk

# Verify
python3 -c "import tkinter; print('OK')"
```

#### Permission Errors

**Error**: "Permission denied" on config directory

**Solution**:
```bash
# Fix permissions
chmod 755 ~/.skywatcher_controller

# If needed, recreate directory
rm -rf ~/.skywatcher_controller
mkdir ~/.skywatcher_controller
chmod 755 ~/.skywatcher_controller
```

#### Firewall (UFW)

**Error**: Connection works initially then fails

**Solution**:
```bash
# Allow UDP port
sudo ufw allow 11880/udp

# Check rule added
sudo ufw status

# If UFW disabled
sudo ufw enable
```

### macOS Issues

#### Python/tkinter Version

**Error**: GUI crashes or displays incorrectly

**Solutions**:

1. **Update Python**
   ```bash
   # Using Homebrew
   brew install python-tk
   
   # Or download from python.org
   # Official builds include tkinter
   ```

2. **Use System Python**
   ```bash
   # macOS includes Python 3
   /usr/bin/python3 StarCommandGUI.py
   ```

#### Network Connection

**Symptom**: Can't ping mount

**Solution**:
1. Check WiFi priority in Network preferences
2. Ensure mount WiFi is preferred network
3. May need to disable VPN
4. Check "Auto-join" is enabled for mount network

---

## Configuration Problems

### Settings Not Saving

**GUI**: Settings revert after restart

**Solutions**:

1. **Check Database File**
   ```bash
   # Linux/macOS
   ls -la ~/.skywatcher_controller/settings.db
   
   # Windows
   dir %USERPROFILE%\.skywatcher_controller\settings.db
   ```

2. **Permissions**
   ```bash
   # Linux/macOS - should be writable
   chmod 644 ~/.skywatcher_controller/settings.db
   ```

3. **Disk Space**
   ```bash
   # Check available space
   df -h ~
   ```

4. **Recreate Database**
   ```bash
   # Backup old
   mv ~/.skywatcher_controller/settings.db ~/.skywatcher_controller/settings.db.bak
   
   # Restart application to create new
   ```

**CLI**: config.json changes ignored

**Solutions**:

1. **JSON Syntax**
   - Validate JSON syntax
   - Use online JSON validator
   - Common errors: missing commas, quotes

2. **File Location**
   ```bash
   # Verify correct location
   cat ~/.skywatcher_controller/config.json
   ```

3. **Reset to Defaults**
   ```bash
   rm ~/.skywatcher_controller/config.json
   # Restart to generate new defaults
   ```

### Keyboard Shortcuts Not Working

**Symptom**: Keys don't trigger movement

**Solutions**:

1. **Window Focus**
   - Application window must have focus
   - Click in window before using keys

2. **Key Bindings**
   - Check Settings → Controls
   - Verify key names correct
   - Special keys: "space", "Escape", etc.

3. **Conflicting Software**
   - Other apps may capture keys
   - Try different keys
   - Close other applications

4. **Input Method**
   - Check keyboard layout
   - Some layouts remap keys
   - Try with US keyboard layout

### Theme Not Applying

**Symptom**: Selected theme doesn't change appearance

**Solutions**:

1. **Install ttkbootstrap**
   ```bash
   pip install ttkbootstrap
   ```

2. **Restart Application**
   - Theme changes require restart
   - Save settings
   - Close and reopen

3. **Check Installation**
   ```python
   python -c "import ttkbootstrap; print('OK')"
   ```

4. **Fallback Mode**
   - Without ttkbootstrap, uses standard tkinter
   - Theme selector won't appear
   - Basic functionality still works

---

## Performance Issues

### Slow Response

**Symptom**: Commands take long time to execute

**Solutions**:

1. **Network Latency**
   - Check WiFi signal strength
   - Move closer to mount
   - Reduce interference

2. **Timeout Setting**
   - Lower timeout may cause delays
   - Increase in settings
   - Recommended: 2.0-3.0 seconds

3. **CPU Usage**
   - Check system resources
   - Close unnecessary applications
   - Especially on older hardware

4. **Debug Logging**
   - Disable if enabled unnecessarily
   - Debug mode creates I/O overhead
   - Only enable when troubleshooting

### High CPU Usage

**Symptom**: Application uses excessive CPU

**Solutions**:

1. **Auto-Update Rate** (GUI)
   - Lower update frequency
   - Default: 1 Hz
   - Try: 0.5 Hz

2. **Status Monitor** (GUI)
   - Polls every 200ms
   - This is normal
   - Not configurable (required for safety)

3. **Log File Size**
   - Large logs slow disk I/O
   - Reduce retention count
   - Delete old logs manually

### GUI Lag

**Symptom**: GUI feels sluggish or unresponsive

**Solutions**:

1. **Python Version**
   - Update to latest Python 3.x
   - Newer versions have performance improvements

2. **ttkbootstrap**
   - Some themes are heavier
   - Try different theme
   - Or disable ttkbootstrap

3. **Screen Resolution**
   - High DPI may cause issues
   - Try lower resolution
   - Or adjust scaling

---

## Error Messages

### Command Error Codes

**Error !0**: Invalid command
- Command format incorrect
- Check protocol reference
- Enable debug logging to see exact command

**Error !1**: Invalid parameter
- Parameter out of range
- Check value bounds
- Verify hex formatting

**Error !2**: Motor not initialized
- Need to initialize axes
- Reconnect to auto-initialize
- Or send :F1 and :F2 manually

**Error !3**: Motor still running
- Must stop before certain commands
- Stop motion first
- Then retry command

### Python Errors

**ModuleNotFoundError: No module named 'tkinter'**
- See platform-specific sections above
- Need to install tkinter

**ModuleNotFoundError: No module named 'ttkbootstrap'**
- Optional module for themes
- Install with: `pip install ttkbootstrap`
- Or use without themes

**socket.timeout**
- Mount not responding
- Check connection
- Increase timeout setting

**PermissionError**
- Can't write to config directory
- Check permissions
- See platform-specific sections

---

## Hardware Issues

### Battery Problems

**Symptoms**:
- Weak or no movement
- Erratic behavior
- WiFi drops

**Solutions**:

1. **Check Voltage**
   - Use multimeter
   - Measure under load
   - Need >7.5V, prefer 12V

2. **Battery Type**
   - Use recommended battery
   - Check polarity
   - Verify connector

3. **Power Supply**
   - Try different power source
   - Check for voltage sag
   - Use regulated supply if possible

### Mechanical Issues

**Grinding Noise**:
1. Check gear mesh
2. Look for debris
3. Verify lubrication
4. May need service

**Binding**:
1. Check balance
2. Look for obstructions
3. Verify clutches not over-tightened
4. Check for bent parts

**Slipping**:
1. Tighten clutches
2. Check gear condition
3. Verify motor shaft coupling
4. May indicate wear

### WiFi Module

**Can't connect to mount WiFi**:
1. Reset WiFi module (see mount manual)
2. Check WiFi password
3. Verify module powered
4. May need firmware update

**Weak Signal**:
1. Check antenna connection
2. Avoid metal obstacles
3. Keep devices close
4. Check for interference (2.4GHz)

---

## Diagnostic Tools

### Built-in Diagnostics

**GUI Diagnostics Tab**:
```
1. Click "Query Mount Info"
2. Check all values returned
3. Verify:
   - CPR: 865,050 (GTi 150P)
   - Timer: 16,000,000 Hz
   - Version: Should return hex string
```

**CLI info Command**:
```bash
> info
# Should show complete mount parameters
```

### Manual Protocol Test

**Test Basic Communication**:
```python
#!/usr/bin/env python3
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(2.0)

# Test version query
s.sendto(b':e1\r', ('192.168.4.1', 11880))
data, addr = s.recvfrom(1024)
print(f"Version: {data.decode('ascii')}")

# Test position query
s.sendto(b':j1\r', ('192.168.4.1', 11880))
data, addr = s.recvfrom(1024)
print(f"Position: {data.decode('ascii')}")

s.close()
```

### Network Diagnostics

**Test Connectivity**:
```bash
# Ping mount
ping 192.168.4.1

# Check route
traceroute 192.168.4.1  # Linux/macOS
tracert 192.168.4.1     # Windows

# Check port (requires nmap)
nmap -sU -p 11880 192.168.4.1
```

### Log Analysis

**GUI Logs**:
```bash
# Location
cd [script_directory]/logs/

# View most recent
tail -f telescope_control_*.log | grep ERROR

# Search for errors
grep -i error telescope_control_*.log
grep -i blocked telescope_control_*.log
```

**Common Patterns**:
```
Good:
  → ':e1\r'
  ← '=0336CF'

Bad - Timeout:
  → ':e1\r'
  ← None

Bad - Error:
  → ':G210\r'
  ← '!1'
```

---

## Getting Help

### Before Asking for Help

1. **Check Logs**
   - Enable debug mode
   - Reproduce problem
   - Review log file

2. **Test Both Versions**
   - Try CLI if GUI fails (or vice versa)
   - Helps isolate GUI vs protocol issue

3. **Document Setup**
   - Mount model
   - Python version
   - Operating system
   - Network configuration

4. **Gather Info**
   ```bash
   # Python version
   python --version
   
   # Check tkinter
   python -c "import tkinter; print('OK')"
   
   # Check ttkbootstrap
   python -c "import ttkbootstrap; print('OK')"
   
   # Config location
   ls ~/.skywatcher_controller/
   ```

### Reporting Issues

**Include**:
1. Detailed problem description
2. Steps to reproduce
3. Error messages (exact text)
4. Log excerpts (debug mode enabled)
5. System information
6. What you've already tried

**GitHub Issues**:
- Use issue templates if provided
- One issue per problem
- Search existing issues first
- Be responsive to questions

---

## Common Solutions Summary

| Problem | Quick Fix |
|---------|-----------|
| Can't connect | Check WiFi, ping mount, verify power |
| No movement | Check clutches, battery, initialization |
| Wrong direction | Check orientation, swap keys if needed |
| Settings not saved | Check permissions, recreate config |
| Keys don't work | Check window focus, verify bindings |
| Slow response | Check WiFi signal, increase timeout |
| Python errors | Update Python, install missing modules |
| High CPU | Lower update rate, disable debug |

---

## Advanced Troubleshooting

### Protocol Debugging

**Capture Raw Communication**:
```python
# Add to protocol class
def send_command(self, command):
    print(f"SEND: {command.encode().hex()}")
    # ... existing code
    print(f"RECV: {data.hex()}")
```

### Database Inspection

**Check GUI Settings**:
```bash
# Install sqlite3
sudo apt-get install sqlite3  # Linux

# Open database
sqlite3 ~/.skywatcher_controller/settings.db

# List tables
.tables

# View settings
SELECT * FROM settings;

# Exit
.quit
```

### Network Packet Capture

**Using Wireshark**:
1. Install Wireshark
2. Capture on WiFi interface
3. Filter: `udp.port == 11880`
4. Analyze command/response pattern

### Reset Everything

**Complete Reset**:
```bash
# Stop application
# Delete all config
rm -rf ~/.skywatcher_controller/

# Delete virtual environment
rm -rf venv/

# Reinstall
./install.sh
source venv/bin/activate

# Start fresh
python StarCommandGUI.py
```

---

**Still having issues? Check GitHub Discussions or open an Issue with detailed information.**

Clear skies! 🔭
