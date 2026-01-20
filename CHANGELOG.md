# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Automated testing suite
- Configuration backup/restore
- Position history tracking
- ASCOM driver integration
- Multi-language support

---

## [0.4.2] - GUI - 2026-01-20

### Added
- Collapsible activity log on Control tab
- Dedicated "Comms Log" tab for protocol debugging with search/filter
- Protocol logging toggle in settings
- Position value sanity checking (filters corrupted packets)
- Search functionality in Comms Log (plain text and regex support)

### Changed
- Separated UI logging from protocol logging (protocol → file only)
- Updated ttkbootstrap imports to avoid deprecation warnings
- Removed invalid theme 'cerulean' from theme list
- Improved text contrast in dark themes

### Fixed
- Activity log no longer floods with protocol traffic
- Wild position values now filtered with sanity checking
- ttkbootstrap deprecation warnings resolved
- Text contrast issues in dark themes

---

## [0.4.1] - GUI - 2024-01-20

### Added
- Altitude movement limits with enforcement (min/max degrees)
- Dedicated `logs/` folder for automatic log storage
- Log retention setting (0-500 files, default: 30)
- Automatic cleanup of old log files
- Modern GUI styling with ttkbootstrap integration
- Theme selector with 15+ built-in themes
- Improved visual consistency and flat design
- Theme categories (dark/light) for easy selection

### Changed
- Logging now uses dedicated folder instead of script directory
- Modernized UI appearance with ttkbootstrap (optional dependency)
- Improved color scheme and button styling
- Enhanced visual feedback throughout interface

### Fixed
- Log file accumulation issue
- UI consistency across different themes
- Theme persistence between sessions

---

## [0.4.0] - GUI - 2024-01-15

### Added
- SQLite database for persistent configuration
- Momentary control mode (hold to move, release to stop)
- Latching control mode (click to start, click stop to end)
- Combined diagnostics tab
- Real-time status monitoring (200ms polling)
- Blocked motion detection
- Status change logging
- Comprehensive status display

### Changed
- Configuration moved from JSON to SQLite database
- Reorganized settings into sub-tabs
- Improved status indicators with color coding

### Fixed
- Status polling reliability
- Configuration persistence issues
- Memory usage from continuous monitoring

---

## [0.3.1] - GUI - 2024-01-10

### Added
- Real-time status monitoring
- File logging with timestamps
- Blocked motion detection alerts
- Status bit decoder
- Activity log in Control tab

### Changed
- Improved error handling
- Better connection feedback

### Fixed
- Protocol command format for GTi 150P
- Response parsing issues
- Connection stability

---

## [0.3.0] - GUI - 2024-01-05

### Added
- Fixed protocol commands for GTi 150P compatibility
- Proper initialization sequence
- Axis status querying
- Emergency stop functionality

### Changed
- Command format to match GTi 150P firmware
- Removed X10 prefix from commands
- Simplified protocol implementation

### Fixed
- Movement commands now work correctly
- Initialization issues
- Status query reliability

---

## [2.0.0] - CLI - 2024-01-20

### Added
- Enhanced command-line interface
- Timed movement execution (e.g., "w 2" for 2 seconds)
- Speed control with +/- shortcuts
- Multiple position display formats (degrees/raw/both)
- Home and stow position presets
- Configuration file support (JSON)
- Status and info commands
- Zero position command
- Format selection command
- Configuration display command

### Changed
- Completely redesigned command structure
- Improved user interface
- Better error messages
- More intuitive command names

### Fixed
- Connection handling
- Configuration persistence
- Position display accuracy

---

## [1.0.0] - Initial Release - 2024-01-01

### Added
- Basic GUI application
- Basic CLI application
- UDP communication with mount
- Position queries
- Movement commands
- Simple configuration

---

## Version History Summary

| Version | Application | Date | Key Features |
|---------|-------------|------|--------------|
| 0.4.1 | GUI | 2024-01-20 | Altitude limits, log management, modern themes |
| 0.4.0 | GUI | 2024-01-15 | SQLite config, control modes, status monitoring |
| 0.3.1 | GUI | 2024-01-10 | File logging, blocked detection |
| 0.3.0 | GUI | 2024-01-05 | GTi 150P protocol fixes |
| 2.0.0 | CLI | 2024-01-20 | Enhanced commands, presets, config |
| 1.0.0 | Both | 2024-01-01 | Initial release |

---

## Migration Guides

### Upgrading to 0.4.1 (GUI)

**New Features:**
- Set altitude limits in Settings → Controls
- Configure log retention in Settings → Logging
- Choose from new themes in Settings → Theme

**Breaking Changes:**
- None

**Notes:**
- Old config files automatically migrated to SQLite
- Logs moved to dedicated `logs/` folder
- Install ttkbootstrap for modern themes: `pip install ttkbootstrap`

### Upgrading to 0.4.0 (GUI)

**New Features:**
- Choose control mode (latching/momentary) in Settings
- Real-time status monitoring
- Blocked motion detection

**Breaking Changes:**
- Configuration moved from JSON to SQLite
- Old config.json automatically migrated on first run

**Migration:**
```bash
# Backup old config (optional)
cp ~/.skywatcher_controller/config.json ~/.skywatcher_controller/config.json.bak

# Start application - migration happens automatically
python StarCommandGUI.py
```

### Upgrading to 2.0.0 (CLI)

**New Features:**
- Timed movements
- Home/stow positions
- Multiple display formats

**Breaking Changes:**
- None - fully backward compatible

**New Config Options:**
```json
{
  "positions": {
    "home_az": 0.0,
    "home_alt": 0.0,
    "stow_az": 0.0,
    "stow_alt": 90.0
  }
}
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Reporting bugs
- Suggesting features  
- Submitting pull requests
- Development setup

---

## Support

- **Documentation**: See [docs/](docs/) folder
- **Issues**: [GitHub Issues](https://github.com/yourusername/skywatcher-controller/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/skywatcher-controller/discussions)

---

[Unreleased]: https://github.com/yourusername/skywatcher-controller/compare/v0.4.2...HEAD
[0.4.2]: https://github.com/yourusername/skywatcher-controller/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/yourusername/skywatcher-controller/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/yourusername/skywatcher-controller/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/yourusername/skywatcher-controller/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/yourusername/skywatcher-controller/compare/v1.0.0...v0.3.0
[2.0.0]: https://github.com/yourusername/skywatcher-controller/releases/tag/v2.0.0-cli
[1.0.0]: https://github.com/yourusername/skywatcher-controller/releases/tag/v1.0.0
