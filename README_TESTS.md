# StarCommand Test Suite

## Overview

This test suite validates critical protocol functions without requiring physical hardware.

## Running Tests

```bash
# Run all tests
python test_protocol.py

# Run with verbose output (default)
python test_protocol.py -v

# Run specific test class
python -m unittest test_protocol.TestShortestPathCalculation
```

## Test Coverage

### 1. Shortest Path Calculation (7 tests)
Tests the azimuth goto direction selection algorithm:
- **350° → 10°**: Should go CW (20°), not CCW (340°)
- **10° → 350°**: Should go CCW (20°), not CW (340°)
- **0° → 180°**: CW wins on tie (both 180°)
- **45° → 315°**: Should go CCW (90°)
- **315° → 45°**: Should go CW (90°)
- **100° → 110°**: Should go CW (10°)
- **110° → 100°**: Should go CCW (10°)

### 2. Position Conversion (6 tests)
Tests counts ↔ degrees conversion:
- Zero position
- Full rotation (360° = 9024 counts)
- Half rotation (180° = 4512 counts)
- Quarter rotation (90° = 2256 counts)
- Negative positions

### 3. Hex Formatting (5 tests)
Tests LSB-first hex encoding:
- 0x123456 → "563412" (byte reversal)
- Zero handling
- Single/double byte values
- Round-trip encoding/decoding

### 4. Position Offset (4 tests)
Tests 0x800000 offset handling:
- Position 0 transmitted as 0x800000
- Positive/negative position offsets
- Round-trip offset application

### 5. Wrap-Around Comparison (4 tests)
Tests error calculation for GotoTracker:
- Simple error (no wrap)
- Wrap-around error (350° vs 10° = 20° not 340°)
- Exactly 180° (ambiguous)
- Near 0°/360° boundary

### 6. Command Formatting (2 tests)
Tests protocol constants:
- Axis values ('1' = azimuth, '2' = altitude)
- Command termination

## Test Results

All 30 tests pass:
- ✅ Shortest path calculation verified mathematically correct
- ✅ Position conversion accurate
- ✅ Hex encoding matches LSB-first requirement
- ✅ Position offset applied correctly
- ✅ Wrap-around logic handles 0°/360° boundary

## What's NOT Tested (Future Work)

1. **Hardware Integration**
   - Actual UDP communication
   - Mount response parsing
   - Network timeouts

2. **GUI Components**
   - Button handling
   - Status updates
   - Limit enforcement

3. **Database Layer**
   - SQLite persistence
   - Settings migration

4. **GotoTracker**
   - Completion detection
   - Timeout handling

5. **Safety Features**
   - Emergency stop
   - Limit checking
   - Position sanity validation

## Adding New Tests

```python
class TestNewFeature(unittest.TestCase):
    def setUp(self):
        """Create protocol instance with mock socket."""
        self.protocol = SkyWatcherProtocol('192.168.4.1', 11880, None)
        self.protocol.socket = MockSocket()
        self.protocol.cpr_az = 9024
        self.protocol.cpr_alt = 9024

    def test_something(self):
        """Test description."""
        # Arrange
        input_value = 123

        # Act
        result = self.protocol.some_method(input_value)

        # Assert
        self.assertEqual(result, expected_value)
```

## Continuous Integration

To add automated testing:

1. **Create `.github/workflows/test.yml`:**
   ```yaml
   name: Tests
   on: [push, pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
           with:
             python-version: '3.9'
         - run: python test_protocol.py
   ```

2. **Require tests to pass before merging**

## Mock Hardware Simulator (Future)

Create `mock_mount.py` to simulate UDP responses:

```python
# Simulate GTi mount for integration testing
import socket
import threading

class MockGTiMount:
    def __init__(self, port=11880):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', port))
        self.position_az = 0
        self.position_alt = 0
        # ...handle commands, send responses
```

This would enable full integration testing without physical hardware.
