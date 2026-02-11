# Suggested Improvements to CLAUDE.md

This document contains suggested additions and improvements to CLAUDE.md based on current codebase analysis.

## Critical Issues to Add

### 1. Known Bugs & Limitations Section

Add this new section after "Protocol Implementation Details":

```markdown
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
   - **Action Required**: Add comprehensive logging to verify correct direction selection

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
```

### 2. Testing & Quality Assurance Section

Add new section:

```markdown
## Testing & Quality Assurance

### Current State
**NO AUTOMATED TESTS EXIST**

This is a critical gap. The codebase has NO test suite despite controlling physical hardware with safety implications.

### Required Testing Framework

#### Unit Tests Needed
1. **Protocol Layer** (`SkyWatcherProtocol` class)
   - Command formatting (LSB-first hex encoding)
   - Response parsing (position decoding, status bits)
   - Degree/count conversions
   - Shortest path calculations (CRITICAL - currently failing)
   - Wrap-around logic at 0°/360° boundary

2. **Configuration Layer** (`DatabaseConfig` class)
   - Setting persistence and retrieval
   - Type conversions (int, float, bool)
   - Default value handling

3. **Goto Verification** (`GotoTracker` class)
   - Completion detection
   - Timeout handling
   - Wrap-around position comparison

#### Integration Tests Needed
1. **Mock Hardware Tests**
   - Create UDP server simulator mimicking mount behavior
   - Test command sequences without physical hardware
   - Verify initialization sequence
   - Test limit enforcement logic

2. **Safety Tests** (CRITICAL)
   - Altitude limit enforcement
   - Azimuth limit enforcement (once implemented)
   - Emergency stop functionality
   - Position sanity checking

3. **Edge Cases**
   - 0°/360° azimuth boundary
   - Negative altitude values
   - Maximum rotation limits
   - Network timeout scenarios
   - Corrupted packet handling

### Manual Testing Checklist

Before ANY release or significant change:

- [ ] **Azimuth Tests**
  - [ ] Goto across 0°/360° boundary (e.g., 350° → 10°)
  - [ ] Verify shortest path taken (should move 20° CW, not 340° CCW)
  - [ ] Test both CW and CCW movements
  - [ ] Verify goto completion notification

- [ ] **Altitude Tests**
  - [ ] Approach minimum limit (default -5°)
  - [ ] Verify auto-stop when limit reached
  - [ ] Approach maximum limit (default 90°)
  - [ ] Verify auto-stop when limit reached

- [ ] **Limit Enforcement Tests**
  - [ ] Enable limits, attempt to exceed → should stop
  - [ ] Disable limits, verify movement unrestricted
  - [ ] Test in both momentary and latching modes

- [ ] **Goto Verification Tests**
  - [ ] Short distance goto (within 10°)
  - [ ] Long distance goto (>180°)
  - [ ] Verify "Goto completed" notification appears
  - [ ] Interrupt goto mid-movement, verify timeout/cancellation

- [ ] **Position Display Tests**
  - [ ] Enable auto-update, verify smooth updates
  - [ ] Check all display formats (degrees, raw, both)
  - [ ] Verify position sanity checking filters bad values

- [ ] **Performance Tests**
  - [ ] Rapid keypresses in momentary mode
  - [ ] Tab switching responsiveness
  - [ ] Settings changes responsiveness

### Test Data Requirements

Create test position files for regression testing:

```json
{
  "shortest_path_tests": [
    {"current": 10, "target": 350, "expected_direction": "CCW", "expected_distance": 20},
    {"current": 350, "target": 10, "expected_direction": "CW", "expected_distance": 20},
    {"current": 0, "target": 180, "expected_direction": "CW", "expected_distance": 180},
    {"current": 180, "target": 0, "expected_direction": "CW", "expected_distance": 180}
  ]
}
```
```

### 3. Code Review Guidelines Section

Add new section:

```markdown
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
```

### 4. Development Workflow Section Enhancement

Replace the existing "Development Workflow Requirements" section with:

```markdown
## Development Workflow Requirements

### Every Code Change Must Include:

1. **Code Changes**
   - Implement feature/fix with proper comments
   - Follow code quality standards (see Code Review Guidelines)
   - Ensure azimuth/altitude symmetry where applicable

2. **Testing**
   - Manual testing checklist (see Testing & QA section)
   - Document test results in commit message
   - For bug fixes: Add test case to prevent regression

3. **Documentation Updates**
   - **CHANGELOG.md** - Add to current version under appropriate category
   - **todo.md** - Mark completed items, add new discovered issues
   - **CLAUDE.md** - Update if architecture/patterns changed
   - **Code comments** - Explain WHY not just WHAT

4. **Verification**
   - Test on actual hardware if possible
   - Check logs for unexpected errors
   - Verify no performance regression
   - Review comms log for protocol correctness

### Commit Message Format

```
<type>: <short summary> (<issue-ref>)

<detailed description>

Testing:
- <test performed>
- <test result>

Related: <related issues/PRs>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `perf`, `style`

Example:
```
fix: Add azimuth limit checking symmetry with altitude (#42)

Implemented check_azimuth_limits() to prevent cable wrapping.
Uses same logic as check_altitude_limits() for consistency.

Testing:
- Tested azimuth movement near 0°/360° boundary
- Verified auto-stop at configured limits
- Confirmed behavior matches altitude axis

Related: #38 (azimuth safety), todo.md line 23
```

### Git Workflow

1. **Before Starting Work**
   ```bash
   git pull origin main
   git checkout -b feature/descriptive-name
   ```

2. **During Development**
   - Commit frequently with descriptive messages
   - Test after each significant change
   - Update documentation as you go (not at the end)

3. **Before Committing**
   ```bash
   # Review your changes
   git diff

   # Check for debug code, commented lines, TODO markers
   grep -r "TODO\|FIXME\|XXX\|DEBUG" *.py

   # Verify no accidental file inclusions
   git status
   ```

4. **Creating Pull Request**
   - Fill out PR template with testing checklist
   - Reference related issues
   - Include before/after behavior description
   - Add screenshots/videos for UI changes
```

### 5. Critical Protocol Notes Section Addition

Add to "Protocol Implementation Details":

```markdown
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
```

## Additional Sections to Add

### Debug Mode Section

```markdown
## Debug Mode & Troubleshooting

### Enabling Verbose Logging

In GUI Settings → Logging:
1. Enable "Debug Mode" checkbox
2. Enable "Show Protocol Traffic"
3. Restart application

This logs ALL protocol commands at DEBUG level, including:
- Status polling (normally hidden)
- Position queries
- CPR/timer frequency queries

### Analyzing Goto Failures

When "shortest move calculations" fail:

1. **Check Comms Log** (Logs → Comms tab)
   - Search for `:S1` (azimuth goto command)
   - Verify position encoding is correct
   - Check response is `=\r` (success)

2. **Check Activity Log**
   - Look for "Goto completed" or "Goto failed" messages
   - Check for timeout warnings (>120 seconds)

3. **Check File Logs** (logs/ directory)
   - Open latest telescope_control_*.log
   - Search for "GotoTracker" entries
   - Look for wrap-around calculation debug messages:
     ```
     DEBUG: Azimuth goto: current=350.5°, target=10.2°
     DEBUG: CW distance=19.7°, CCW distance=340.3°
     DEBUG: Selected direction: CW
     ```

4. **Manual Calculation Verification**
   ```python
   current_deg = 350.5
   target_deg = 10.2

   cw_distance = (target_deg - current_deg) % 360  # Should be ~19.7
   ccw_distance = (current_deg - target_deg) % 360  # Should be ~340.3

   # If these don't match expected, formula is wrong
   ```

### Common Error Messages

| Message | Meaning | Solution |
|---------|---------|----------|
| "Position rejected: Az=XXX°" | Sanity check failed | Check for corrupted UDP packet, verify mount position |
| "Motion stopped at altitude limit" | Hit configured limit | Adjust limits in Settings or disable enforcement |
| "Goto failed: timeout" | 2 minutes elapsed | Check if mount is blocked, verify target is reachable |
| "Goto failed: position not reached" | Within tolerance but incomplete | Check tolerance setting, verify mount isn't stalled |
| "⚠ E-STOP ACTIVE" | Emergency stop triggered | Clear with regular Stop button |

### Performance Profiling

If experiencing UI sluggishness:

1. **Check Update Rate**
   - Logs → Diagnostics → Update Rate (Hz)
   - Default: 1.0 Hz (1000ms)
   - Lower values = less CPU usage but slower updates

2. **Monitor Position Query Time**
   - Enable debug mode
   - Check logs for "Position query took XXms"
   - Should be <60ms total (both axes)
   - If >100ms: Network issue or mount overloaded

3. **Check Database Operations**
   - Look for "Database query took XXms" in logs
   - Should be <10ms
   - If slow: Database file may be corrupted, delete settings.db and restart

4. **Profile Event Loop** (for developers)
   ```python
   import cProfile
   import pstats

   profiler = cProfile.Profile()
   profiler.enable()

   # Run problematic operation
   self.update_positions()

   profiler.disable()
   stats = pstats.Stats(profiler)
   stats.sort_stats('cumulative')
   stats.print_stats(20)  # Top 20 slowest functions
   ```
```

## Summary of Changes

The suggested improvements add:

1. **Known Bugs Section** - Documents critical azimuth limit checking gap
2. **Testing Section** - Provides testing framework, manual checklists, test data
3. **Code Review Section** - Standards, naming conventions, refactoring priorities
4. **Enhanced Workflow** - Commit format, git workflow, verification steps
5. **Protocol Pitfalls** - Common mistakes to avoid
6. **Debug Mode Section** - Troubleshooting guide, performance profiling

These additions directly address the issues raised:
- Azimuth checking asymmetry documented and flagged
- Shortest path calculation marked for verification with debug guidance
- Testing procedures comprehensively defined
- Code review standards established for future work
