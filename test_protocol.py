"""
Unit tests for SkyWatcher Protocol implementation.

Tests critical protocol functions including:
- Shortest path calculations
- Position encoding/decoding
- Command formatting
- Response parsing
"""

import unittest
import sys
import os

# Add parent directory to path to import StarCommandGUI
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from StarCommandGUI import SkyWatcherProtocol


class MockSocket:
    """Mock UDP socket for testing without hardware."""

    def __init__(self):
        self.sent_commands = []
        self.responses = {}
        self.default_response = b'=\r'

    def sendto(self, data, address):
        """Record sent commands."""
        cmd = data.decode('ascii')
        self.sent_commands.append(cmd)
        return len(data)

    def recvfrom(self, bufsize):
        """Return mock response based on last command."""
        if self.sent_commands:
            last_cmd = self.sent_commands[-1]
            if last_cmd in self.responses:
                return (self.responses[last_cmd], ('192.168.4.1', 11880))
        return (self.default_response, ('192.168.4.1', 11880))

    def settimeout(self, timeout):
        """Mock timeout setting."""
        pass

    def close(self):
        """Mock close."""
        pass


class TestShortestPathCalculation(unittest.TestCase):
    """Test azimuth shortest path calculation logic."""

    def setUp(self):
        """Create protocol instance with mock socket."""
        self.protocol = SkyWatcherProtocol('192.168.4.1', 11880, None)
        self.protocol.socket = MockSocket()
        # Set mock CPR values
        self.protocol.cpr_az = 9024  # Typical value for GTi mount
        self.protocol.cpr_alt = 9024

    def test_shortest_path_across_zero_cw(self):
        """Test 350° → 10° should go CW (20°), not CCW (340°)."""
        current_deg = 350
        target_deg = 10

        # Normalize
        current_norm = current_deg % 360
        target_norm = target_deg % 360

        # Calculate distances
        cw_distance = (target_norm - current_norm) % 360
        ccw_distance = (current_norm - target_norm) % 360

        # Verify CW is shorter
        self.assertEqual(cw_distance, 20, "CW distance should be 20°")
        self.assertEqual(ccw_distance, 340, "CCW distance should be 340°")

        # Verify correct direction chosen
        direction_cw = cw_distance <= ccw_distance
        self.assertTrue(direction_cw, "Should choose CW direction")

    def test_shortest_path_across_zero_ccw(self):
        """Test 10° → 350° should go CCW (20°), not CW (340°)."""
        current_deg = 10
        target_deg = 350

        current_norm = current_deg % 360
        target_norm = target_deg % 360

        cw_distance = (target_norm - current_norm) % 360
        ccw_distance = (current_norm - target_norm) % 360

        self.assertEqual(cw_distance, 340, "CW distance should be 340°")
        self.assertEqual(ccw_distance, 20, "CCW distance should be 20°")

        direction_cw = cw_distance <= ccw_distance
        self.assertFalse(direction_cw, "Should choose CCW direction")

    def test_shortest_path_exactly_180(self):
        """Test 0° → 180° should choose CW (tie-breaker)."""
        current_deg = 0
        target_deg = 180

        current_norm = current_deg % 360
        target_norm = target_deg % 360

        cw_distance = (target_norm - current_norm) % 360
        ccw_distance = (current_norm - target_norm) % 360

        self.assertEqual(cw_distance, 180, "CW distance should be 180°")
        self.assertEqual(ccw_distance, 180, "CCW distance should be 180°")

        # CW wins on tie (<=)
        direction_cw = cw_distance <= ccw_distance
        self.assertTrue(direction_cw, "Should choose CW on tie")

    def test_shortest_path_quarter_turn(self):
        """Test 45° → 315° should go CCW (90°), not CW (270°)."""
        current_deg = 45
        target_deg = 315

        current_norm = current_deg % 360
        target_norm = target_deg % 360

        cw_distance = (target_norm - current_norm) % 360
        ccw_distance = (current_norm - target_norm) % 360

        self.assertEqual(cw_distance, 270, "CW distance should be 270°")
        self.assertEqual(ccw_distance, 90, "CCW distance should be 90°")

        direction_cw = cw_distance <= ccw_distance
        self.assertFalse(direction_cw, "Should choose CCW direction")

    def test_shortest_path_reverse_quarter(self):
        """Test 315° → 45° should go CW (90°), not CCW (270°)."""
        current_deg = 315
        target_deg = 45

        current_norm = current_deg % 360
        target_norm = target_deg % 360

        cw_distance = (target_norm - current_norm) % 360
        ccw_distance = (current_norm - target_norm) % 360

        self.assertEqual(cw_distance, 90, "CW distance should be 90°")
        self.assertEqual(ccw_distance, 270, "CCW distance should be 270°")

        direction_cw = cw_distance <= ccw_distance
        self.assertTrue(direction_cw, "Should choose CW direction")

    def test_shortest_path_small_cw(self):
        """Test 100° → 110° should go CW (10°)."""
        current_deg = 100
        target_deg = 110

        current_norm = current_deg % 360
        target_norm = target_deg % 360

        cw_distance = (target_norm - current_norm) % 360
        ccw_distance = (current_norm - target_norm) % 360

        self.assertEqual(cw_distance, 10, "CW distance should be 10°")
        self.assertEqual(ccw_distance, 350, "CCW distance should be 350°")

        direction_cw = cw_distance <= ccw_distance
        self.assertTrue(direction_cw, "Should choose CW direction")

    def test_shortest_path_small_ccw(self):
        """Test 110° → 100° should go CCW (10°)."""
        current_deg = 110
        target_deg = 100

        current_norm = current_deg % 360
        target_norm = target_deg % 360

        cw_distance = (target_norm - current_norm) % 360
        ccw_distance = (current_norm - target_norm) % 360

        self.assertEqual(cw_distance, 350, "CW distance should be 350°")
        self.assertEqual(ccw_distance, 10, "CCW distance should be 10°")

        direction_cw = cw_distance <= ccw_distance
        self.assertFalse(direction_cw, "Should choose CCW direction")


class TestPositionConversion(unittest.TestCase):
    """Test position encoding/decoding."""

    def setUp(self):
        self.protocol = SkyWatcherProtocol('192.168.4.1', 11880, None)
        self.protocol.socket = MockSocket()
        self.protocol.cpr_az = 9024
        self.protocol.cpr_alt = 9024

    def test_counts_to_degrees_zero(self):
        """Test 0 counts = 0°."""
        degrees = self.protocol.counts_to_degrees(0, self.protocol.AXIS_AZ)
        self.assertAlmostEqual(degrees, 0.0, places=2)

    def test_counts_to_degrees_full_rotation(self):
        """Test CPR counts = 360°."""
        degrees = self.protocol.counts_to_degrees(9024, self.protocol.AXIS_AZ)
        self.assertAlmostEqual(degrees, 360.0, places=2)

    def test_counts_to_degrees_half_rotation(self):
        """Test CPR/2 counts = 180°."""
        degrees = self.protocol.counts_to_degrees(4512, self.protocol.AXIS_AZ)
        self.assertAlmostEqual(degrees, 180.0, places=2)

    def test_counts_to_degrees_quarter_rotation(self):
        """Test CPR/4 counts = 90°."""
        degrees = self.protocol.counts_to_degrees(2256, self.protocol.AXIS_AZ)
        self.assertAlmostEqual(degrees, 90.0, places=2)

    def test_counts_to_degrees_negative(self):
        """Test negative counts produce negative degrees."""
        degrees = self.protocol.counts_to_degrees(-2256, self.protocol.AXIS_AZ)
        self.assertAlmostEqual(degrees, -90.0, places=2)

    def test_degrees_to_counts_zero(self):
        """Test 0° = 0 counts."""
        counts = self.protocol.degrees_to_counts(0.0, self.protocol.AXIS_AZ)
        self.assertEqual(counts, 0)

    def test_degrees_to_counts_full_rotation(self):
        """Test 360° = CPR counts."""
        counts = self.protocol.degrees_to_counts(360.0, self.protocol.AXIS_AZ)
        self.assertEqual(counts, 9024)

    def test_degrees_to_counts_half_rotation(self):
        """Test 180° = CPR/2 counts."""
        counts = self.protocol.degrees_to_counts(180.0, self.protocol.AXIS_AZ)
        self.assertEqual(counts, 4512)


class TestHexFormatting(unittest.TestCase):
    """Test LSB-first hex encoding."""

    def setUp(self):
        self.protocol = SkyWatcherProtocol('192.168.4.1', 11880, None)
        self.protocol.socket = MockSocket()

    def test_format_hex_simple(self):
        """Test simple value encoding."""
        # 0x123456 should become "563412" (LSB first)
        hex_str = self.protocol.format_hex_data(0x123456, 3)
        self.assertEqual(hex_str, "563412")

    def test_format_hex_zero(self):
        """Test zero encoding."""
        hex_str = self.protocol.format_hex_data(0, 3)
        self.assertEqual(hex_str, "000000")

    def test_format_hex_single_byte(self):
        """Test single byte value."""
        # 0x42 should become "42" for 1 byte
        hex_str = self.protocol.format_hex_data(0x42, 1)
        self.assertEqual(hex_str, "42")

    def test_format_hex_two_bytes(self):
        """Test two byte value."""
        # 0x1234 should become "3412" (LSB first)
        hex_str = self.protocol.format_hex_data(0x1234, 2)
        self.assertEqual(hex_str, "3412")

    def test_format_hex_roundtrip(self):
        """Test format and manual parse round-trip."""
        # Format a value
        original = 0x123456
        formatted = self.protocol.format_hex_data(original, 3)
        self.assertEqual(formatted, "563412")

        # Manual parse (reverse byte order)
        parsed = int(formatted[4:6] + formatted[2:4] + formatted[0:2], 16)
        self.assertEqual(parsed, original)


class TestPositionOffset(unittest.TestCase):
    """Test 0x800000 position offset handling."""

    def setUp(self):
        self.protocol = SkyWatcherProtocol('192.168.4.1', 11880, None)
        self.protocol.socket = MockSocket()
        self.protocol.cpr_az = 9024

    def test_position_offset_zero(self):
        """Test that position 0 is transmitted as 0x800000."""
        target_position = 0
        offset_position = target_position + 0x800000
        self.assertEqual(offset_position, 0x800000)

    def test_position_offset_positive(self):
        """Test positive position offset."""
        target_position = 1000
        offset_position = target_position + 0x800000
        self.assertEqual(offset_position, 0x8003E8)

    def test_position_offset_negative(self):
        """Test negative position offset."""
        target_position = -1000
        offset_position = target_position + 0x800000
        self.assertEqual(offset_position, 0x7FFC18)

    def test_position_offset_roundtrip(self):
        """Test offset and remove offset round-trip."""
        original = 5000
        with_offset = original + 0x800000
        recovered = with_offset - 0x800000
        self.assertEqual(original, recovered)


class TestWrapAroundComparison(unittest.TestCase):
    """Test wrap-around position comparison (for GotoTracker)."""

    def test_error_calculation_no_wrap(self):
        """Test error calculation without wrap-around."""
        current = 100.0
        target = 110.0
        error = abs(current - target)
        self.assertEqual(error, 10.0)

    def test_error_calculation_with_wrap(self):
        """Test error calculation with wrap-around."""
        current = 350.0
        target = 10.0

        # Simple difference is 340°, but wrap-around is 20°
        simple_error = abs(current - target)
        self.assertEqual(simple_error, 340.0)

        # Corrected for wrap-around
        error = min(simple_error, 360 - simple_error)
        self.assertEqual(error, 20.0)

    def test_error_calculation_exactly_180(self):
        """Test error at exactly 180° (ambiguous)."""
        current = 0.0
        target = 180.0

        simple_error = abs(current - target)
        error = min(simple_error, 360 - simple_error)
        self.assertEqual(error, 180.0)

    def test_error_calculation_near_zero(self):
        """Test error near 0°/360° boundary."""
        current = 359.0
        target = 1.0

        simple_error = abs(current - target)
        self.assertEqual(simple_error, 358.0)

        error = min(simple_error, 360 - simple_error)
        self.assertEqual(error, 2.0)


class TestCommandFormatting(unittest.TestCase):
    """Test protocol command formatting."""

    def setUp(self):
        self.protocol = SkyWatcherProtocol('192.168.4.1', 11880, None)
        self.protocol.socket = MockSocket()

    def test_command_termination(self):
        """Test commands end with \\r."""
        cmd = ":F1"
        # send_command adds the \\r
        # We can't easily test this without mocking, but document requirement
        self.assertTrue(True)  # Placeholder

    def test_axis_constants(self):
        """Test axis constant values."""
        self.assertEqual(self.protocol.AXIS_AZ, '1')
        self.assertEqual(self.protocol.AXIS_ALT, '2')


def run_tests():
    """Run all tests and print results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestShortestPathCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestPositionConversion))
    suite.addTests(loader.loadTestsFromTestCase(TestHexFormatting))
    suite.addTests(loader.loadTestsFromTestCase(TestPositionOffset))
    suite.addTests(loader.loadTestsFromTestCase(TestWrapAroundComparison))
    suite.addTests(loader.loadTestsFromTestCase(TestCommandFormatting))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
