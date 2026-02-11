# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

StarCommand is a telescope controller for Sky-Watcher Virtuoso GTi dobsonian mounts. Version 0.4.2 provides both GUI (StarCommandGUI.py) and CLI (StarCommandCLI.py) interfaces for WiFi-based telescope control with SQLite persistence, real-time protocol debugging, and customizable themes.

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
starcommand
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

### Common Protocol Pitfalls

1. **Axis Parameter Inconsistency**
   - Some code uses '1'/'2' (string)
   - Some code uses AXIS_AZ/AXIS_ALT constants
   - **Always check both** when writing conditionals:
   ```python
   if axis == self.AXIS_ALT or axis == '2':
   ```

2. **Position Offset Confusion**
   - Raw positions are signed 24-bit integers
   - Protocol transmits as unsigned with 0x800000 offset
   - **Always add offset before sending, subtract after receiving**
   - **Never** use raw count value directly in calculations

3. **LSB-First Encoding**
   - Hex values must be byte-reversed
   - Example: 0x123456 → "563412"
   - Use `format_hex_data()` method, never manual string concatenation

4. **Direction Bit Confusion**
   - set_motion_mode() has TWO direction parameters
   - `direction_cw` in function parameter (True = clockwise)
   - Direction bit in mode byte (different encoding)
   - **Always use the method, never construct mode byte manually**

5. **Command vs Response Termination**
   - Commands MUST end with '\r' (carriage return)
   - Responses include '\r' which must be stripped
   - Some responses include '=' prefix, some don't
   - **Always check response format** before parsing

## Known Bugs & Limitations

### Critical Issues Requiring Attention

1. **Azimuth Limit Checking Missing** (HIGH PRIORITY)
   - **Issue**: Altitude limits are enforced (lines 1905-1927, 1931-1953) but azimuth has NO limit checking
   - **Impact**: Mount can rotate indefinitely, potentially wrapping cables
   - **Location**: [StarCommandGUI.py:1905-1953](StarCommandGUI.py#L1905-L1953)
   - **Required Fix**: Implement `check_azimuth_limits()` similar to `check_altitude_limits()`
   - **Safety Risk**: Cable damage, mount damage

2. **Goto Verification Inconsistency**
   - **Issue**: GotoTracker verifies completion but may have logic errors in wrap-around calculation
   - **Location**: [StarCommandGUI.py:472-596](StarCommandGUI.py#L472-L596)
   - **Reported Symptom**: "Shortest move calculations still seem to be failing"
   - **Test Required**: Manual testing of goto operations across 0°/360° boundary

3. **Shortest Path Calculation Uncertainty**
   - **Issue**: goto_position() implements shortest path (lines 822-839) but effectiveness unclear
   - **Location**: [StarCommandGUI.py:816-849](StarCommandGUI.py#L816-L849)
   - **Formula**:
     ```python
     cw_distance = (target_deg - current_deg) % 360
     ccw_distance = (current_deg - target_deg) % 360
     direction_cw = cw_distance <= ccw_distance
     ```
   - **Action Required**: Verify calculation logic is correct for all edge cases

4. **Error Handling Asymmetry**
   - **Issue**: Altitude moves have failure checking, azimuth moves do not
   - **Impact**: Azimuth failures may go undetected
   - **Required**: Implement equivalent error detection for azimuth axis

### Performance Issues

1. **UI Responsiveness** (Partially addressed in v0.4.4)
   - **Issue**: Keypresses can be missed in momentary mode, tab switching has delays
   - **Status**: Position query optimization improved latency by 60-70% but more work needed
   - **Remaining Work**: Profile event loop, identify remaining bottlenecks

### CLI vs GUI Feature Parity

1. **StarCommandCLI.py Outdated**
   - **Issue**: CLI lacks many GUI improvements from v0.4.x
   - **Missing Features**: Limit enforcement, goto verification, position caching
   - **Action Required**: Comprehensive CLI review and update

## Code Review Guidelines

### Before Implementing ANY Feature

1. **Read Existing Code First**
   - Understand current implementation
   - Check for similar patterns elsewhere
   - Review related classes/methods
   - Check CHANGELOG.md for historical context

2. **Identify Safety Implications**
   - Does this control motor movement?
   - Can this cause cable wrapping?
   - Could this damage hardware?
   - Does this bypass safety limits?

3. **Check Symmetry**
   - **CRITICAL**: If implementing for azimuth, also implement for altitude (and vice versa)
   - Example: Altitude has limit checking → azimuth MUST also have limit checking
   - Example: Goto verification for one axis → must verify BOTH axes

4. **Consider Error Cases**
   - What if UDP packet is lost?
   - What if position value is corrupted?
   - What if mount is blocked/stalled?
   - What if user disconnects during operation?

### Code Quality Standards

#### Comments Required For:
1. **All Protocol Commands**
   ```python
   # Send goto target position: :S<axis><24-bit position with LSB-first encoding>
   # Position is offset by 0x800000 to represent signed values
   response = self.send_command(f":S{axis}{hex_target}")
   ```

2. **All Safety-Critical Logic**
   ```python
   # SAFETY: Stop altitude motion if limit reached to prevent cable wrapping
   if self.last_valid_alt_deg >= alt_max or self.last_valid_alt_deg <= alt_min:
       self.stop_axis(2)
   ```

3. **All Calculations**
   ```python
   # Calculate shortest azimuth path:
   # CW distance: (target - current) mod 360
   # CCW distance: (current - target) mod 360
   # Choose direction with smaller distance
   cw_distance = (target_deg - current_deg) % 360
   ccw_distance = (current_deg - target_deg) % 360
   direction_cw = cw_distance <= ccw_distance
   ```

4. **All Magic Numbers**
   ```python
   self.tolerance_deg = 0.5  # Within 0.5° = successful goto completion
   self.timeout_sec = 120    # 2 minutes max for goto operations
   ```

#### Naming Conventions

- Use descriptive names: `check_altitude_limits()` not `check_lim()`
- Match existing patterns: `goto_position()` not `go_to_pos()`
- Axis references: Use `axis` parameter, check for both '1'/'2' and AXIS_AZ/AXIS_ALT
- Degree vs count: Suffix variables with `_deg` or `_counts` for clarity

### Refactoring Priorities

1. **Extract Duplicate Code**
   - Position querying (azimuth vs altitude) - DONE in v0.4.4
   - Limit checking (create unified `check_axis_limits(axis, direction)`)
   - Preset button handling (home vs stow nearly identical)

2. **Improve Separation of Concerns**
   - Protocol layer should not know about GUI
   - GUI should not construct protocol commands directly
   - Configuration should be injectable, not global

3. **Add Type Hints**
   ```python
   def goto_position(self, axis: str, target_position: int) -> bool:
       """Goto specific position with shortest path calculation."""
   ```

4. **Reduce Nesting Depth**
   - Current: Up to 5-6 levels in some methods
   - Target: Maximum 3 levels
   - Use early returns, extract methods

## Development Workflow Requirements

### When Making Changes

**ALWAYS** update these files after implementing changes:

1. **CHANGELOG.md**:
   - Add changes to the appropriate version section
   - Use categories: Added, Changed, Fixed, Removed
   - Follow semantic versioning (major.minor.patch)
   - Update version history table at bottom
   - Include line number references for code changes where applicable

2. **todo.md**:
   - Mark completed items with [x] and strikethrough
   - Move completed items to "Completed Tasks" section with version number
   - Remove items that are no longer relevant
   - Add new items as they are discovered during development
   - Use bold for task names and include context/reasoning

3. **Version Bumping**:
   - Update version in README.md if applicable
   - Update version in setup.py if applicable
   - Ensure CHANGELOG.md reflects new version
   - Update version history table in CHANGELOG.md

### Workflow Example

After implementing a feature or fix:
1. Make code changes with proper comments
2. **Test changes** (manual testing checklist - see Testing & QA section)
3. Update CHANGELOG.md with changes under current/unreleased version
4. Update todo.md to mark items complete
5. Commit with descriptive message (see format below)
6. For releases: Update version numbers across all files

### Commit Message Format

```
<type>: <short summary>

<detailed description>

Testing:
- <test performed>
- <test result>

Related: <related issues/PRs>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `perf`, `style`

Example:
```
fix: Add azimuth limit checking symmetry with altitude

Implemented check_azimuth_limits() to prevent cable wrapping.
Uses same logic as check_altitude_limits() for consistency.

Testing:
- Tested azimuth movement near 0°/360° boundary
- Verified auto-stop at configured limits
- Confirmed behavior matches altitude axis

Related: todo.md known bugs section
```

### Pre-Commit Verification

Before committing, verify:
```bash
# Review your changes
git diff

# Check for debug code, commented lines, TODO markers
grep -r "TODO\|FIXME\|XXX\|DEBUG" StarCommand*.py

# Verify no accidental file inclusions
git status

# Check for trailing whitespace, syntax errors
python -m py_compile StarCommand*.py
```

### Critical Files to Update

| File | Update Trigger | What to Update |
|------|----------------|----------------|
| CHANGELOG.md | Any code change | Add to version section with category |
| todo.md | Feature/fix completion | Mark complete, move to "Completed Tasks" |
| README.md | Version release | Update version number and feature list |
| setup.py | Version release | Update version number |

## Important Development Notes

### File Organization

**Current working files:**
- [StarCommandGUI.py](StarCommandGUI.py) - Primary GUI application (v0.4.3)
- [StarCommandCLI.py](StarCommandCLI.py) - CLI alternative
- [logs/](logs/) - Runtime logs with automatic retention
- [setup.py](setup.py) - Package installation configuration (updated v0.4.3)

**Files to ignore/regenerate:**
- `venv/` - May be out of date, regenerate with install scripts
- `tools_old/` - Legacy development files
- `*.egg-info/` - Build artifacts, automatically generated

### Version History

**v0.4.3 (current):**
- QOL improvements: tooltips, read-only log, disabled connection fields
- Limit enforcement in momentary mode with auto-stop
- Sanity checks for preset buttons
- Motion control centering
- Fixed ttkbootstrap deprecation warning
- Updated install scripts and setup.py

**v0.4.2:**
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

### Testing & Quality Assurance

#### Current State
**NO AUTOMATED TESTS EXIST**

This is a critical gap. The codebase has NO test suite despite controlling physical hardware with safety implications.

#### Manual Testing Checklist

Before ANY release or significant change:

**Azimuth Tests:**
- [ ] Goto across 0°/360° boundary (e.g., 350° → 10°)
- [ ] Verify shortest path taken (should move 20° CW, not 340° CCW)
- [ ] Test both CW and CCW movements
- [ ] Verify goto completion notification
- [ ] Test azimuth limits once implemented

**Altitude Tests:**
- [ ] Approach minimum limit (default -5°)
- [ ] Verify auto-stop when limit reached
- [ ] Approach maximum limit (default 90°)
- [ ] Verify auto-stop when limit reached
- [ ] Test in both momentary and latching modes

**Limit Enforcement Tests:**
- [ ] Enable limits, attempt to exceed → should stop
- [ ] Disable limits, verify movement unrestricted
- [ ] Test momentary mode limit checking (100ms polling)
- [ ] Test latching mode limit checking

**Goto Verification Tests:**
- [ ] Short distance goto (within 10°)
- [ ] Long distance goto (>180°)
- [ ] Verify "Goto completed" notification appears
- [ ] Interrupt goto mid-movement, verify timeout/cancellation
- [ ] Test goto across 0°/360° boundary

**Position Display Tests:**
- [ ] Enable auto-update, verify smooth updates
- [ ] Check all display formats (degrees, raw, both)
- [ ] Verify position sanity checking filters bad values
- [ ] Test update rate changes (0.1 Hz to 10 Hz)

**Performance Tests:**
- [ ] Rapid keypresses in momentary mode (should not miss inputs)
- [ ] Tab switching responsiveness (should be immediate)
- [ ] Settings changes responsiveness
- [ ] Monitor position query latency (<60ms typical)

**Protocol Tests:**
- [ ] Enable protocol logging, verify commands are correct
- [ ] Check LSB-first encoding in Comms Log
- [ ] Verify position offset (0x800000) applied correctly
- [ ] Test network timeout handling (disconnect mount temporarily)

#### Required Testing Framework (Future Work)

**Unit Tests Needed:**
1. Protocol Layer (`SkyWatcherProtocol`)
   - Command formatting (LSB-first hex encoding)
   - Response parsing (position decoding, status bits)
   - Degree/count conversions
   - Shortest path calculations (CRITICAL)
   - Wrap-around logic at 0°/360° boundary

2. Configuration Layer (`DatabaseConfig`)
   - Setting persistence and retrieval
   - Type conversions (int, float, bool)
   - Default value handling

3. Goto Verification (`GotoTracker`)
   - Completion detection
   - Timeout handling
   - Wrap-around position comparison

**Integration Tests Needed:**
1. Mock Hardware Tests
   - Create UDP server simulator mimicking mount behavior
   - Test command sequences without physical hardware
   - Verify initialization sequence
   - Test limit enforcement logic

2. Safety Tests (CRITICAL)
   - Altitude limit enforcement
   - Azimuth limit enforcement (once implemented)
   - Emergency stop functionality
   - Position sanity checking

3. Edge Cases
   - 0°/360° azimuth boundary
   - Negative altitude values
   - Maximum rotation limits
   - Network timeout scenarios
   - Corrupted packet handling

#### Test Data for Shortest Path Validation

Expected results for goto direction selection:
```python
test_cases = [
    {"current": 10, "target": 350, "expected_dir": "CCW", "expected_dist": 20},
    {"current": 350, "target": 10, "expected_dir": "CW", "expected_dist": 20},
    {"current": 0, "target": 180, "expected_dir": "CW", "expected_dist": 180},
    {"current": 180, "target": 0, "expected_dir": "CW", "expected_dist": 180},
    {"current": 45, "target": 315, "expected_dir": "CCW", "expected_dist": 90},
    {"current": 315, "target": 45, "expected_dir": "CW", "expected_dist": 90},
]
```

## Related Documentation

- [docs/INSTALL.md](docs/INSTALL.md) - Comprehensive installation guide (695 lines)
- [docs/FINAL_FIX_SUMMARY.md](docs/FINAL_FIX_SUMMARY.md) - Protocol bug fixes from v0.4.2
- [docs/SUMMARY.md](docs/SUMMARY.md) - Version changelog
- `docs/skywatcher_motor_controller_command_set.pdf` - Official motor protocol
- `docs/synscan_app_protocol_20250930.pdf` - Complete SynScan spec
