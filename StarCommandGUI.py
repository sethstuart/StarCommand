#!/usr/bin/env python3
"""
Sky-Watcher Virtuoso GTi 150P Professional Controller
Full-featured GUI with configurable settings, themes, and keyboard controls

Version: 0.4.1

CHANGELOG v0.4.1:
  - Added altitude movement limits (min/max) with enforcement
  - Logging now uses dedicated 'logs' folder (auto-created)
  - Added log retention setting (0-500 files, default 30)
  - Modernized GUI using ttkbootstrap (falls back to ttk if not installed)
  - Added theme selector from ttkbootstrap's built-in themes
  - Improved visual consistency and modern flat design

PREVIOUS:
  - v0.4.0: SQLite persistence, momentary controls, combined diagnostics
  - v0.3.1: Status monitoring, file logging, blocked detection
  - v0.3.0: Fixed protocol commands for GTi 150P

REQUIREMENTS:
  pip install ttkbootstrap   (optional but recommended for modern look)

Works with GTi 150P firmware that uses simple protocol without X10 prefix.
"""

import socket
import time
import sys
import threading
import sqlite3
import os
from datetime import datetime
from pathlib import Path

# Try to import ttkbootstrap, fall back to standard ttk
TTKBOOTSTRAP_AVAILABLE = False
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    from ttkbootstrap.scrolled import ScrolledText
    from ttkbootstrap.tooltip import ToolTip
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import scrolledtext
    ScrolledText = None  # Will use tkinter's version

if not TTKBOOTSTRAP_AVAILABLE:
    import tkinter as tk
    from tkinter import messagebox, colorchooser
    from tkinter.scrolledtext import ScrolledText as TkScrolledText
else:
    import tkinter as tk
    from tkinter import messagebox, colorchooser

VERSION = "0.4.1"

# Default ttkbootstrap theme
DEFAULT_THEME = "darkly"

# Available ttkbootstrap themes
AVAILABLE_THEMES = [
    # Dark themes
    "darkly", "cyborg", "vapor", "solar", "superhero",
    # Light themes  
    "flatly", "journal", "litera", "minty", "pulse", 
    "sandstone", "united", "yeti", "morph", "simplex",
    "cosmo", "lumen", "cerulean"
]

# Status byte bit definitions (from SynScan protocol)
STATUS_RUNNING = 0x01
STATUS_BLOCKED = 0x02
STATUS_INIT = 0x04


class DatabaseConfig:
    """SQLite-based configuration manager for persistent settings."""
    
    DEFAULT_SETTINGS = {
        # Connection
        'connection.ip': '192.168.4.1',
        'connection.port': '11880',
        'connection.timeout': '2.0',
        # Controls
        'controls.up': 'w',
        'controls.down': 's',
        'controls.left': 'a',
        'controls.right': 'd',
        'controls.stop': 'space',
        'controls.estop': 'Escape',
        'controls.mode': 'latching',
        # Limits
        'limits.alt_min': '-5.0',
        'limits.alt_max': '90.0',
        'limits.enforce': 'True',
        # Display
        'display.position_format': 'both',
        'display.show_positions': 'True',
        'display.auto_update': 'False',
        'display.update_rate': '1.0',
        # Positions
        'positions.home_az': '0.0',
        'positions.home_alt': '0.0',
        'positions.stow_az': '0.0',
        'positions.stow_alt': '90.0',
        # Theme
        'theme.name': DEFAULT_THEME,
        # Speed
        'speed.default': '1.0',
        'speed.min': '0.1',
        'speed.max': '10.0',
        # Logging
        'logging.debug_mode': 'False',
        'logging.retention': '30',
    }
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            config_dir = Path.home() / '.skywatcher_controller'
            config_dir.mkdir(exist_ok=True)
            db_path = config_dir / 'settings.db'
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        for key, value in self.DEFAULT_SETTINGS.items():
            cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
            ''', (key, value))
        
        conn.commit()
        conn.close()
    
    def get(self, key: str, default=None):
        """Get a setting value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row[0]
        return default if default is not None else self.DEFAULT_SETTINGS.get(key)
    
    def get_int(self, key: str, default: int = 0) -> int:
        value = self.get(key)
        try:
            return int(value) if value else default
        except ValueError:
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        value = self.get(key)
        try:
            return float(value) if value else default
        except ValueError:
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes')
    
    def set(self, key: str, value):
        """Set a setting value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
        ''', (key, str(value)))
        conn.commit()
        conn.close()


class FileLogger:
    """Handles file logging with retention management."""
    
    def __init__(self, base_dir: Path, retention: int = 30):
        self.base_dir = base_dir
        self.log_dir = base_dir / 'logs'
        self.log_dir.mkdir(exist_ok=True)
        
        self.log_file = None
        self.log_path = None
        self.debug_mode = False
        self.retention = retention
        self._lock = threading.Lock()
        
        self._cleanup_old_logs()
        self._start_new_log()
    
    def _cleanup_old_logs(self):
        """Remove old log files based on retention setting."""
        if self.retention <= 0:
            return
        
        try:
            log_files = sorted(
                self.log_dir.glob('telescope_control_*.log'),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            
            # Keep only the most recent 'retention' files
            for old_file in log_files[self.retention:]:
                try:
                    old_file.unlink()
                except Exception:
                    pass
        except Exception:
            pass
    
    def set_retention(self, retention: int):
        """Update retention setting."""
        self.retention = retention
        self._cleanup_old_logs()
    
    def _start_new_log(self):
        """Create a new log file with timestamp."""
        if self.retention == 0:
            # Retention 0 means no logging to file
            self.log_file = None
            self.log_path = None
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"telescope_control_{timestamp}.log"
        self.log_path = self.log_dir / filename
        try:
            self.log_file = open(self.log_path, 'w', encoding='utf-8')
            self._write_header()
        except Exception as e:
            print(f"Warning: Could not create log file: {e}")
            self.log_file = None
    
    def _write_header(self):
        """Write log file header."""
        if not self.log_file:
            return
        self.log_file.write(f"Telescope Control Log - v{VERSION}\n")
        self.log_file.write(f"Started: {datetime.now().isoformat()}\n")
        self.log_file.write(f"Debug Mode: {self.debug_mode}\n")
        self.log_file.write(f"Retention: {self.retention} files\n")
        self.log_file.write("=" * 60 + "\n\n")
        self.log_file.flush()
    
    def set_debug_mode(self, enabled: bool):
        """Enable or disable debug mode."""
        self.debug_mode = enabled
        self.log(f"Debug mode {'enabled' if enabled else 'disabled'}", level='INFO')
    
    def log(self, message: str, level: str = 'INFO'):
        """Log a message to file."""
        if level == 'DEBUG' and not self.debug_mode:
            return
        
        if not self.log_file:
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with self._lock:
            try:
                line = f"[{timestamp}] [{level:7}] {message}\n"
                self.log_file.write(line)
                self.log_file.flush()
            except Exception:
                pass
    
    def log_command(self, cmd: str, response: str):
        """Log a command/response pair (debug level)."""
        cmd_display = repr(cmd).replace('\r', '\\r')
        resp_display = repr(response).replace('\r', '\\r') if response else "None"
        self.log(f"CMD: {cmd_display} -> {resp_display}", level='DEBUG')
    
    def log_status_change(self, axis: int, old_status: int, new_status: int, decoded: str):
        """Log a status change."""
        axis_name = "Azimuth" if axis == 1 else "Altitude"
        self.log(f"{axis_name} status: 0x{old_status:02X} -> 0x{new_status:02X} ({decoded})", level='STATUS')
    
    def close(self):
        """Close the log file."""
        if self.log_file:
            self.log(f"Log closed: {datetime.now().isoformat()}", level='INFO')
            try:
                self.log_file.close()
            except Exception:
                pass


class StatusDecoder:
    """Decodes SynScan status bytes into human-readable format."""
    
    @staticmethod
    def decode(status_byte: int) -> dict:
        return {
            'running': bool(status_byte & STATUS_RUNNING),
            'blocked': bool(status_byte & STATUS_BLOCKED),
            'initialized': bool(status_byte & STATUS_INIT),
            'raw': status_byte
        }
    
    @staticmethod
    def to_string(status_byte: int) -> str:
        d = StatusDecoder.decode(status_byte)
        parts = []
        if d['running']:
            parts.append("Running")
        else:
            parts.append("Stopped")
        if d['blocked']:
            parts.append("BLOCKED")
        if d['initialized']:
            parts.append("Init")
        return f"0x{status_byte:02X} ({', '.join(parts)})"


class StatusMonitor:
    """Monitors axis status during motion with 200ms polling."""
    
    def __init__(self, protocol, file_logger, gui_callback=None):
        self.protocol = protocol
        self.file_logger = file_logger
        self.gui_callback = gui_callback
        self.monitoring = False
        self._thread = None
        self._last_status = {1: None, 2: None}
    
    def start(self):
        if self.monitoring:
            return
        self.monitoring = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        if self.file_logger:
            self.file_logger.log("Status monitoring started (200ms polling)", level='INFO')
    
    def stop(self):
        self.monitoring = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self.file_logger:
            self.file_logger.log("Status monitoring stopped", level='INFO')
    
    def _monitor_loop(self):
        while self.monitoring:
            if self.protocol:
                for axis in [1, 2]:
                    try:
                        status = self.protocol.get_status(str(axis))
                        if status:
                            raw = status.get('raw', 0)
                            old = self._last_status.get(axis)
                            
                            if old is not None and raw != old:
                                decoded = StatusDecoder.to_string(raw)
                                if self.file_logger:
                                    self.file_logger.log_status_change(axis, old, raw, decoded)
                            
                            self._last_status[axis] = raw
                            
                            if self.gui_callback:
                                try:
                                    self.gui_callback(axis, status)
                                except Exception:
                                    pass
                    except Exception:
                        pass
            time.sleep(0.2)


class SkyWatcherProtocol:
    """Implementation of SkyWatcher Motor Controller Protocol"""
    
    def __init__(self, ip='192.168.4.1', port=11880, timeout=2.0, log_callback=None):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        self.log_callback = log_callback
        
        self.AXIS_AZ = '1'
        self.AXIS_ALT = '2'
        self.AXIS_BOTH = '3'
        
        self.cpr_az = None
        self.cpr_alt = None
        self.timer_freq = None
    
    def send_command(self, command):
        """Send command and receive response."""
        if not command.endswith('\r'):
            command += '\r'
        
        if self.log_callback:
            self.log_callback(f"→ SEND: {repr(command)}")
        
        try:
            self.sock.sendto(command.encode('ascii'), (self.ip, self.port))
            data, addr = self.sock.recvfrom(1024)
            response = data.decode('ascii').strip()
            
            if self.log_callback:
                self.log_callback(f"← RECV: {repr(response)}")
            
            return response
        except socket.timeout:
            if self.log_callback:
                self.log_callback(f"✗ TIMEOUT")
            return None
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"✗ ERROR: {e}")
            return None
    
    def parse_hex_response(self, response):
        """Parse hex data from response (LSB first format)"""
        if not response or not response.startswith('='):
            return None
        
        hex_str = response[1:].replace('\r', '')
        if len(hex_str) == 0:
            return None
        
        reversed_str = ''.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)][::-1])
        try:
            return int(reversed_str, 16)
        except ValueError:
            return None
    
    def format_hex_data(self, value, bytes_count=3):
        """Format value as hex string in LSB-first format"""
        hex_str = f"{value:0{bytes_count*2}X}"
        return ''.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)][::-1])
    
    def get_position(self, axis):
        """Get current position"""
        cmd = f":j{axis}"
        response = self.send_command(cmd)
        if response:
            pos = self.parse_hex_response(response)
            if pos is not None:
                return pos - 0x800000
        return None
    
    def set_position(self, axis, position):
        """Set current position"""
        pos_with_offset = position + 0x800000
        hex_pos = self.format_hex_data(pos_with_offset, 3)
        cmd = f":E{axis}{hex_pos}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def set_motion_mode(self, axis, goto_mode=False, direction_cw=True, high_speed=False):
        """Set motion mode"""
        if goto_mode:
            if high_speed:
                mode_code = "00" if direction_cw else "01"
            else:
                mode_code = "20" if direction_cw else "21"  
        else:
            mode_code = "10" if direction_cw else "11"
        
        cmd = f":G{axis}{mode_code}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def set_step_period(self, axis, period):
        """Set step period"""
        hex_period = self.format_hex_data(period, 3)
        cmd = f":I{axis}{hex_period}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def start_motion(self, axis):
        """Start motion"""
        cmd = f":J{axis}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def stop_motion(self, axis):
        """Stop motion"""
        cmd = f":K{axis}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def instant_stop(self, axis):
        """Instant stop"""
        cmd = f":L{axis}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def get_counts_per_revolution(self, axis):
        """Get CPR"""
        cmd = f":a{axis}"
        response = self.send_command(cmd)
        cpr = self.parse_hex_response(response)
        if cpr and axis == self.AXIS_AZ:
            self.cpr_az = cpr
        elif cpr and axis == self.AXIS_ALT:
            self.cpr_alt = cpr
        return cpr
    
    def get_timer_freq(self):
        """Get timer frequency"""
        if self.timer_freq:
            return self.timer_freq
        cmd = f":b1"
        response = self.send_command(cmd)
        freq = self.parse_hex_response(response)
        if freq:
            self.timer_freq = freq
        return freq
    
    def get_status(self, axis):
        """Get motor status."""
        cmd = f":f{axis}"
        response = self.send_command(cmd)
        if not response or not response.startswith('='):
            return None
        
        status_hex = response[1:3]
        try:
            status = int(status_hex, 16)
            return {
                'running': bool(status & 0x01),
                'blocked': bool(status & 0x02),
                'initialized': bool(status & 0x04),
                'raw': status
            }
        except ValueError:
            return None
    
    def get_motor_board_version(self, axis):
        """Get motor board version"""
        cmd = f":e{axis}"
        response = self.send_command(cmd)
        if response and response.startswith('='):
            return response[1:].replace('\r', '')
        return None
    
    def initialization_done(self):
        """Signal initialization done"""
        cmd = f":F3"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def slew_fixed_rate(self, axis, direction_positive=True, speed_deg_per_sec=1.0):
        """Slew at fixed rate"""
        if axis == self.AXIS_AZ:
            cpr = self.cpr_az or self.get_counts_per_revolution(axis)
        else:
            cpr = self.cpr_alt or self.get_counts_per_revolution(axis)
        
        timer_freq = self.timer_freq or self.get_timer_freq()
        
        if not cpr or not timer_freq:
            return False
        
        step_period = int((timer_freq * 360.0) / (speed_deg_per_sec * cpr))
        
        if not self.set_motion_mode(axis, goto_mode=False, direction_cw=direction_positive):
            return False
        
        if not self.set_step_period(axis, step_period):
            return False
        
        return self.start_motion(axis)
    
    def goto_position(self, axis, target_position):
        """Goto specific position"""
        target_with_offset = target_position + 0x800000
        hex_target = self.format_hex_data(target_with_offset, 3)
        
        current = self.get_position(axis)
        if current is None:
            return False
        
        direction_cw = target_position > current
        
        if not self.set_motion_mode(axis, goto_mode=True, direction_cw=direction_cw):
            return False
        
        cmd = f":S{axis}{hex_target}"
        response = self.send_command(cmd)
        if not response or not response.startswith('='):
            return False
        
        return self.start_motion(axis)
    
    def counts_to_degrees(self, counts, axis):
        """Convert counts to degrees"""
        if axis == self.AXIS_AZ:
            cpr = self.cpr_az or self.get_counts_per_revolution(axis)
        else:
            cpr = self.cpr_alt or self.get_counts_per_revolution(axis)
        
        if not cpr:
            return None
        
        return (counts / cpr) * 360.0
    
    def degrees_to_counts(self, degrees, axis):
        """Convert degrees to counts"""
        if axis == self.AXIS_AZ:
            cpr = self.cpr_az or self.get_counts_per_revolution(axis)
        else:
            cpr = self.cpr_alt or self.get_counts_per_revolution(axis)
        
        if not cpr:
            return None
        
        return int((degrees / 360.0) * cpr)
    
    def close(self):
        """Close socket"""
        self.sock.close()


class TelescopeGUI:
    """Professional GUI for telescope controller"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"SkyWatcher Controller v{VERSION}")
        self.root.geometry("1050x900")
        
        # Database configuration
        self.db = DatabaseConfig()
        
        # Determine directories
        script_path = Path(__file__).resolve()
        self.base_dir = script_path.parent
        
        # Initialize file logger with retention
        retention = self.db.get_int('logging.retention', 30)
        self.file_logger = FileLogger(self.base_dir, retention=retention)
        self.file_logger.set_debug_mode(self.db.get_bool('logging.debug_mode'))
        self.file_logger.log(f"Application started v{VERSION}", level='INFO')
        self.file_logger.log(f"ttkbootstrap available: {TTKBOOTSTRAP_AVAILABLE}", level='INFO')
        
        # Protocol instance
        self.protocol = None
        self.connected = False
        
        # Status monitor
        self.status_monitor = None
        
        # Track which axes are moving
        self.axes_moving = {1: False, 2: False}
        
        # Position update thread
        self.update_thread = None
        self.update_running = False
        
        # Emergency stop flag
        self.estop_active = False
        
        # Key press tracking for momentary mode
        self.keys_pressed = set()
        
        # Current altitude (for limit checking)
        self.current_alt_deg = None
        
        # Create GUI
        self.create_widgets()
        
        # Bind keyboard controls
        self.bind_keyboard_controls()
        
        # Start position update timer
        self.start_position_updates()
    
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Main notebook
        if TTKBOOTSTRAP_AVAILABLE:
            self.notebook = ttk.Notebook(self.root, bootstyle="dark")
        else:
            self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_control_tab()
        self.create_diagnostics_tab()
        self.create_settings_tab()
    
    def create_control_tab(self):
        """Create control tab"""
        control_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(control_tab, text="  Control  ")
        
        # Top frame - Connection
        if TTKBOOTSTRAP_AVAILABLE:
            conn_frame = ttk.Labelframe(control_tab, text="Connection", padding=15, bootstyle="info")
        else:
            conn_frame = ttk.LabelFrame(control_tab, text="Connection", padding=15)
        conn_frame.grid(row=0, column=0, columnspan=3, sticky='ew', padx=5, pady=5)
        
        ttk.Label(conn_frame, text="IP:").grid(row=0, column=0, sticky='e', padx=5)
        self.ip_entry = ttk.Entry(conn_frame, width=15)
        self.ip_entry.insert(0, self.db.get('connection.ip'))
        self.ip_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky='e', padx=5)
        self.port_entry = ttk.Entry(conn_frame, width=8)
        self.port_entry.insert(0, self.db.get('connection.port'))
        self.port_entry.grid(row=0, column=3, padx=5)
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.connect_btn = ttk.Button(conn_frame, text="Connect", 
                                         command=self.toggle_connection, bootstyle="success")
        else:
            self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=4, padx=10)
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.status_label = ttk.Label(conn_frame, text="● Disconnected", bootstyle="danger")
        else:
            self.status_label = ttk.Label(conn_frame, text="● Disconnected", foreground="red")
        self.status_label.grid(row=0, column=5, padx=10)
        
        # Left frame - Direction controls
        if TTKBOOTSTRAP_AVAILABLE:
            dir_frame = ttk.Labelframe(control_tab, text="Motion Control", padding=15, bootstyle="primary")
        else:
            dir_frame = ttk.LabelFrame(control_tab, text="Motion Control", padding=15)
        dir_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        
        # Direction pad
        btn_width = 10
        if TTKBOOTSTRAP_AVAILABLE:
            self.btn_up = ttk.Button(dir_frame, text="▲\nUP", width=btn_width, bootstyle="info-outline")
            self.btn_left = ttk.Button(dir_frame, text="◄\nLEFT", width=btn_width, bootstyle="info-outline")
            self.btn_stop = ttk.Button(dir_frame, text="■\nSTOP", width=btn_width, 
                                       command=self.stop_all, bootstyle="warning")
            self.btn_right = ttk.Button(dir_frame, text="►\nRIGHT", width=btn_width, bootstyle="info-outline")
            self.btn_down = ttk.Button(dir_frame, text="▼\nDOWN", width=btn_width, bootstyle="info-outline")
        else:
            self.btn_up = ttk.Button(dir_frame, text="▲\nUP", width=btn_width)
            self.btn_left = ttk.Button(dir_frame, text="◄\nLEFT", width=btn_width)
            self.btn_stop = ttk.Button(dir_frame, text="■\nSTOP", width=btn_width, command=self.stop_all)
            self.btn_right = ttk.Button(dir_frame, text="►\nRIGHT", width=btn_width)
            self.btn_down = ttk.Button(dir_frame, text="▼\nDOWN", width=btn_width)
        
        self.btn_up.grid(row=0, column=1, padx=5, pady=5)
        self.btn_left.grid(row=1, column=0, padx=5, pady=5)
        self.btn_stop.grid(row=1, column=1, padx=5, pady=5)
        self.btn_right.grid(row=1, column=2, padx=5, pady=5)
        self.btn_down.grid(row=2, column=1, padx=5, pady=5)
        
        self.setup_button_bindings()
        
        # Emergency Stop
        if TTKBOOTSTRAP_AVAILABLE:
            self.estop_btn = ttk.Button(dir_frame, text="🛑 EMERGENCY STOP", 
                                        command=self.emergency_stop, bootstyle="danger", width=30)
        else:
            self.estop_btn = ttk.Button(dir_frame, text="🛑 EMERGENCY STOP", command=self.emergency_stop)
        self.estop_btn.grid(row=3, column=0, columnspan=3, sticky='ew', pady=15)
        
        # Speed control
        speed_frame = ttk.Frame(dir_frame)
        speed_frame.grid(row=4, column=0, columnspan=3, pady=10, sticky='ew')
        
        ttk.Label(speed_frame, text="Speed (°/sec):").pack(side='left', padx=5)
        self.speed_var = tk.DoubleVar(value=self.db.get_float('speed.default', 1.0))
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.speed_scale = ttk.Scale(speed_frame, 
                                        from_=self.db.get_float('speed.min', 0.1), 
                                        to=self.db.get_float('speed.max', 10.0),
                                        variable=self.speed_var, bootstyle="info")
        else:
            self.speed_scale = ttk.Scale(speed_frame, 
                                        from_=self.db.get_float('speed.min', 0.1), 
                                        to=self.db.get_float('speed.max', 10.0),
                                        variable=self.speed_var)
        self.speed_scale.pack(side='left', fill='x', expand=True, padx=5)
        
        self.speed_label = ttk.Label(speed_frame, text=f"{self.speed_var.get():.2f}", width=6)
        self.speed_label.pack(side='left', padx=5)
        self.speed_var.trace_add('write', self.update_speed_label)
        
        # Control mode & keyboard hints
        control_mode = self.db.get('controls.mode', 'latching')
        mode_text = "Latching" if control_mode == 'latching' else "Momentary"
        ttk.Label(dir_frame, text=f"Mode: {mode_text}  |  Keys: W/A/S/D, Space=Stop, Esc=E-Stop",
                 font=('TkDefaultFont', 9)).grid(row=5, column=0, columnspan=3, pady=5)
        
        # Axis status indicators
        if TTKBOOTSTRAP_AVAILABLE:
            indicator_frame = ttk.Labelframe(dir_frame, text="Axis Status", bootstyle="secondary")
        else:
            indicator_frame = ttk.LabelFrame(dir_frame, text="Axis Status")
        indicator_frame.grid(row=6, column=0, columnspan=3, sticky='ew', pady=10)
        
        ttk.Label(indicator_frame, text="Azimuth:").grid(row=0, column=0, padx=10, pady=5, sticky='e')
        self.az_status_indicator = ttk.Label(indicator_frame, text="● Unknown", foreground='gray')
        self.az_status_indicator.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.az_status_raw = ttk.Label(indicator_frame, text="", font=('Consolas', 9))
        self.az_status_raw.grid(row=0, column=2, padx=5, pady=5, sticky='w')
        
        ttk.Label(indicator_frame, text="Altitude:").grid(row=1, column=0, padx=10, pady=5, sticky='e')
        self.alt_status_indicator = ttk.Label(indicator_frame, text="● Unknown", foreground='gray')
        self.alt_status_indicator.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        self.alt_status_raw = ttk.Label(indicator_frame, text="", font=('Consolas', 9))
        self.alt_status_raw.grid(row=1, column=2, padx=5, pady=5, sticky='w')
        
        # Center frame - Preset positions
        if TTKBOOTSTRAP_AVAILABLE:
            preset_frame = ttk.Labelframe(control_tab, text="Presets", padding=15, bootstyle="success")
        else:
            preset_frame = ttk.LabelFrame(control_tab, text="Presets", padding=15)
        preset_frame.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)
        
        btn_style = "outline" if TTKBOOTSTRAP_AVAILABLE else None
        
        for text, cmd in [("Go to Home", self.goto_home), 
                          ("Set as Home", self.set_home),
                          ("Go to Stow", self.goto_stow), 
                          ("Set as Stow", self.set_stow)]:
            if TTKBOOTSTRAP_AVAILABLE:
                ttk.Button(preset_frame, text=text, command=cmd, width=18, 
                          bootstyle="success-outline").pack(pady=5)
            else:
                ttk.Button(preset_frame, text=text, command=cmd, width=18).pack(pady=5)
        
        ttk.Separator(preset_frame, orient='horizontal').pack(fill='x', pady=15)
        
        for text, cmd in [("Zero Position", self.zero_position), 
                          ("Re-initialize", self.reinitialize)]:
            if TTKBOOTSTRAP_AVAILABLE:
                ttk.Button(preset_frame, text=text, command=cmd, width=18, 
                          bootstyle="secondary-outline").pack(pady=5)
            else:
                ttk.Button(preset_frame, text=text, command=cmd, width=18).pack(pady=5)
        
        # Right frame - Position display
        if TTKBOOTSTRAP_AVAILABLE:
            self.pos_frame = ttk.Labelframe(control_tab, text="Position", padding=15, bootstyle="warning")
        else:
            self.pos_frame = ttk.LabelFrame(control_tab, text="Position", padding=15)
        self.pos_frame.grid(row=1, column=2, sticky='nsew', padx=5, pady=5)
        
        self.show_pos_var = tk.BooleanVar(value=self.db.get_bool('display.show_positions', True))
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Checkbutton(self.pos_frame, text="Show Positions", variable=self.show_pos_var,
                           command=self.toggle_position_display, bootstyle="warning-round-toggle").pack(anchor='w', pady=5)
        else:
            ttk.Checkbutton(self.pos_frame, text="Show Positions", variable=self.show_pos_var,
                           command=self.toggle_position_display).pack(anchor='w', pady=5)
        
        ttk.Label(self.pos_frame, text="Format:").pack(anchor='w', pady=5)
        self.pos_format_var = tk.StringVar(value=self.db.get('display.position_format', 'both'))
        
        for text, value in [('Degrees', 'degrees'), ('Raw', 'raw'), ('Both', 'both'), ('Coords', 'coordinates')]:
            if TTKBOOTSTRAP_AVAILABLE:
                ttk.Radiobutton(self.pos_frame, text=text, variable=self.pos_format_var,
                              value=value, command=self.update_position_format, 
                              bootstyle="warning").pack(anchor='w')
            else:
                ttk.Radiobutton(self.pos_frame, text=text, variable=self.pos_format_var,
                              value=value, command=self.update_position_format).pack(anchor='w')
        
        self.pos_display_frame = ttk.Frame(self.pos_frame)
        self.pos_display_frame.pack(fill='both', expand=True, pady=10)
        
        self.create_position_labels()
        
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(self.pos_frame, text="Refresh", command=self.refresh_positions,
                      bootstyle="warning-outline").pack(pady=5)
        else:
            ttk.Button(self.pos_frame, text="Refresh", command=self.refresh_positions).pack(pady=5)
        
        # Configure grid weights
        control_tab.columnconfigure(0, weight=1)
        control_tab.columnconfigure(1, weight=1)
        control_tab.columnconfigure(2, weight=1)
        control_tab.rowconfigure(1, weight=1)
        
        # Log frame at bottom
        if TTKBOOTSTRAP_AVAILABLE:
            log_frame = ttk.Labelframe(control_tab, text="Activity Log", padding=5, bootstyle="dark")
        else:
            log_frame = ttk.LabelFrame(control_tab, text="Activity Log", padding=5)
        log_frame.grid(row=2, column=0, columnspan=3, sticky='ew', padx=5, pady=5)
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.log_text = ScrolledText(log_frame, height=5, autohide=True)
        else:
            self.log_text = TkScrolledText(log_frame, height=5, font=('Consolas', 9), state='disabled')
        self.log_text.pack(fill='both', expand=True)
    
    def setup_button_bindings(self):
        """Setup button bindings based on control mode."""
        control_mode = self.db.get('controls.mode', 'latching')
        
        if control_mode == 'momentary':
            self.btn_up.bind('<ButtonPress-1>', lambda e: self.move('up'))
            self.btn_up.bind('<ButtonRelease-1>', lambda e: self.stop_axis(2))
            self.btn_down.bind('<ButtonPress-1>', lambda e: self.move('down'))
            self.btn_down.bind('<ButtonRelease-1>', lambda e: self.stop_axis(2))
            self.btn_left.bind('<ButtonPress-1>', lambda e: self.move('left'))
            self.btn_left.bind('<ButtonRelease-1>', lambda e: self.stop_axis(1))
            self.btn_right.bind('<ButtonPress-1>', lambda e: self.move('right'))
            self.btn_right.bind('<ButtonRelease-1>', lambda e: self.stop_axis(1))
        else:
            self.btn_up.configure(command=lambda: self.move('up'))
            self.btn_down.configure(command=lambda: self.move('down'))
            self.btn_left.configure(command=lambda: self.move('left'))
            self.btn_right.configure(command=lambda: self.move('right'))
    
    def create_position_labels(self):
        """Create position display labels based on format"""
        for widget in self.pos_display_frame.winfo_children():
            widget.destroy()
        
        if not self.show_pos_var.get():
            return
        
        format_type = self.pos_format_var.get()
        font = ('Consolas', 11)
        
        if format_type == 'degrees':
            ttk.Label(self.pos_display_frame, text="Az:").grid(row=0, column=0, sticky='e', pady=3)
            self.az_deg_label = ttk.Label(self.pos_display_frame, text="---°", font=font)
            self.az_deg_label.grid(row=0, column=1, sticky='w', padx=5)
            
            ttk.Label(self.pos_display_frame, text="Alt:").grid(row=1, column=0, sticky='e', pady=3)
            self.alt_deg_label = ttk.Label(self.pos_display_frame, text="---°", font=font)
            self.alt_deg_label.grid(row=1, column=1, sticky='w', padx=5)
            
        elif format_type == 'raw':
            ttk.Label(self.pos_display_frame, text="Az:").grid(row=0, column=0, sticky='e', pady=3)
            self.az_raw_label = ttk.Label(self.pos_display_frame, text="---", font=font)
            self.az_raw_label.grid(row=0, column=1, sticky='w', padx=5)
            
            ttk.Label(self.pos_display_frame, text="Alt:").grid(row=1, column=0, sticky='e', pady=3)
            self.alt_raw_label = ttk.Label(self.pos_display_frame, text="---", font=font)
            self.alt_raw_label.grid(row=1, column=1, sticky='w', padx=5)
            
        elif format_type == 'both':
            ttk.Label(self.pos_display_frame, text="Az:").grid(row=0, column=0, sticky='e', pady=3)
            self.az_both_label = ttk.Label(self.pos_display_frame, text="---", font=font)
            self.az_both_label.grid(row=0, column=1, sticky='w', padx=5)
            
            ttk.Label(self.pos_display_frame, text="Alt:").grid(row=1, column=0, sticky='e', pady=3)
            self.alt_both_label = ttk.Label(self.pos_display_frame, text="---", font=font)
            self.alt_both_label.grid(row=1, column=1, sticky='w', padx=5)
            
        elif format_type == 'coordinates':
            self.coord_label = ttk.Label(self.pos_display_frame, text="---", font=font, justify='left')
            self.coord_label.pack(pady=10)
    
    def create_diagnostics_tab(self):
        """Create diagnostics tab"""
        diag_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(diag_tab, text="  Diagnostics  ")
        
        # Top controls
        control_frame = ttk.Frame(diag_tab)
        control_frame.pack(fill='x', pady=10)
        
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(control_frame, text="Query Mount Info", command=self.query_system_info,
                      bootstyle="info").pack(side='left', padx=5)
            ttk.Button(control_frame, text="Refresh Status", command=self.refresh_diagnostics,
                      bootstyle="info-outline").pack(side='left', padx=5)
        else:
            ttk.Button(control_frame, text="Query Mount Info", command=self.query_system_info).pack(side='left', padx=5)
            ttk.Button(control_frame, text="Refresh Status", command=self.refresh_diagnostics).pack(side='left', padx=5)
        
        ttk.Separator(control_frame, orient='vertical').pack(side='left', fill='y', padx=15)
        
        self.auto_update_var = tk.BooleanVar(value=self.db.get_bool('display.auto_update'))
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Checkbutton(control_frame, text="Auto-update", variable=self.auto_update_var,
                           command=self.toggle_auto_update, bootstyle="info-round-toggle").pack(side='left', padx=5)
        else:
            ttk.Checkbutton(control_frame, text="Auto-update", variable=self.auto_update_var,
                           command=self.toggle_auto_update).pack(side='left', padx=5)
        
        ttk.Label(control_frame, text="Rate:").pack(side='left', padx=5)
        self.update_rate_var = tk.DoubleVar(value=self.db.get_float('display.update_rate', 1.0))
        ttk.Spinbox(control_frame, from_=0.1, to=10, increment=0.1, 
                   textvariable=self.update_rate_var, width=5).pack(side='left', padx=5)
        ttk.Label(control_frame, text="Hz").pack(side='left')
        
        # Main content
        if TTKBOOTSTRAP_AVAILABLE:
            self.diag_text = ScrolledText(diag_tab, height=30, autohide=True)
        else:
            self.diag_text = TkScrolledText(diag_tab, height=30, font=('Consolas', 10), state='disabled')
        self.diag_text.pack(fill='both', expand=True, pady=10)
        
        # Legend
        if TTKBOOTSTRAP_AVAILABLE:
            legend_frame = ttk.Labelframe(diag_tab, text="Status Legend", bootstyle="secondary")
        else:
            legend_frame = ttk.LabelFrame(diag_tab, text="Status Legend")
        legend_frame.pack(fill='x', pady=5)
        
        ttk.Label(legend_frame, text="Bit 0 (0x01): Running  |  Bit 1 (0x02): Blocked  |  Bit 2 (0x04): Initialized",
                 font=('Consolas', 9)).pack(pady=5)
    
    def create_settings_tab(self):
        """Create settings tab"""
        settings_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(settings_tab, text="  Settings  ")
        
        # Settings notebook
        if TTKBOOTSTRAP_AVAILABLE:
            settings_notebook = ttk.Notebook(settings_tab, bootstyle="secondary")
        else:
            settings_notebook = ttk.Notebook(settings_tab)
        settings_notebook.pack(fill='both', expand=True)
        
        self.create_controls_settings(settings_notebook)
        self.create_theme_settings(settings_notebook)
        self.create_connection_settings(settings_notebook)
        self.create_logging_settings(settings_notebook)
    
    def create_controls_settings(self, parent_notebook):
        """Create controls settings sub-tab"""
        controls_frame = ttk.Frame(parent_notebook, padding=15)
        parent_notebook.add(controls_frame, text="  Controls  ")
        
        # Control mode
        if TTKBOOTSTRAP_AVAILABLE:
            mode_frame = ttk.Labelframe(controls_frame, text="Control Mode", padding=10, bootstyle="info")
        else:
            mode_frame = ttk.LabelFrame(controls_frame, text="Control Mode", padding=10)
        mode_frame.pack(fill='x', pady=10)
        
        self.control_mode_var = tk.StringVar(value=self.db.get('controls.mode', 'latching'))
        
        for text, value in [("Latching - Click to start, click Stop to stop", 'latching'),
                           ("Momentary - Hold to move, release to stop", 'momentary')]:
            if TTKBOOTSTRAP_AVAILABLE:
                ttk.Radiobutton(mode_frame, text=text, variable=self.control_mode_var, 
                               value=value, bootstyle="info").pack(anchor='w', pady=3)
            else:
                ttk.Radiobutton(mode_frame, text=text, variable=self.control_mode_var, 
                               value=value).pack(anchor='w', pady=3)
        
        # Altitude Limits
        if TTKBOOTSTRAP_AVAILABLE:
            limits_frame = ttk.Labelframe(controls_frame, text="Altitude Limits", padding=10, bootstyle="warning")
        else:
            limits_frame = ttk.LabelFrame(controls_frame, text="Altitude Limits", padding=10)
        limits_frame.pack(fill='x', pady=10)
        
        self.enforce_limits_var = tk.BooleanVar(value=self.db.get_bool('limits.enforce', True))
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Checkbutton(limits_frame, text="Enforce altitude limits", 
                           variable=self.enforce_limits_var, bootstyle="warning-round-toggle").pack(anchor='w', pady=5)
        else:
            ttk.Checkbutton(limits_frame, text="Enforce altitude limits", 
                           variable=self.enforce_limits_var).pack(anchor='w', pady=5)
        
        # Min altitude
        min_frame = ttk.Frame(limits_frame)
        min_frame.pack(fill='x', pady=5)
        ttk.Label(min_frame, text="Minimum altitude:").pack(side='left', padx=5)
        self.alt_min_var = tk.DoubleVar(value=self.db.get_float('limits.alt_min', -5.0))
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Scale(min_frame, from_=-10, to=45, variable=self.alt_min_var, 
                     bootstyle="warning").pack(side='left', fill='x', expand=True, padx=5)
        else:
            ttk.Scale(min_frame, from_=-10, to=45, variable=self.alt_min_var).pack(side='left', fill='x', expand=True, padx=5)
        self.alt_min_label = ttk.Label(min_frame, text=f"{self.alt_min_var.get():.1f}°", width=6)
        self.alt_min_label.pack(side='left', padx=5)
        self.alt_min_var.trace_add('write', lambda *a: self.alt_min_label.configure(text=f"{self.alt_min_var.get():.1f}°"))
        
        # Max altitude
        max_frame = ttk.Frame(limits_frame)
        max_frame.pack(fill='x', pady=5)
        ttk.Label(max_frame, text="Maximum altitude:").pack(side='left', padx=5)
        self.alt_max_var = tk.DoubleVar(value=self.db.get_float('limits.alt_max', 90.0))
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Scale(max_frame, from_=45, to=90, variable=self.alt_max_var, 
                     bootstyle="warning").pack(side='left', fill='x', expand=True, padx=5)
        else:
            ttk.Scale(max_frame, from_=45, to=90, variable=self.alt_max_var).pack(side='left', fill='x', expand=True, padx=5)
        self.alt_max_label = ttk.Label(max_frame, text=f"{self.alt_max_var.get():.1f}°", width=6)
        self.alt_max_label.pack(side='left', padx=5)
        self.alt_max_var.trace_add('write', lambda *a: self.alt_max_label.configure(text=f"{self.alt_max_var.get():.1f}°"))
        
        ttk.Label(limits_frame, text="Movement will be blocked if it would exceed these limits.",
                 font=('TkDefaultFont', 9)).pack(anchor='w', pady=5)
        
        # Key bindings
        if TTKBOOTSTRAP_AVAILABLE:
            kb_frame = ttk.Labelframe(controls_frame, text="Keyboard Bindings", padding=10, bootstyle="secondary")
        else:
            kb_frame = ttk.LabelFrame(controls_frame, text="Keyboard Bindings", padding=10)
        kb_frame.pack(fill='x', pady=10)
        
        kb_grid = ttk.Frame(kb_frame)
        kb_grid.pack()
        
        self.key_entries = {}
        for i, (key, label) in enumerate([('up', 'Up'), ('down', 'Down'), ('left', 'Left'), 
                                          ('right', 'Right'), ('stop', 'Stop'), ('estop', 'E-Stop')]):
            ttk.Label(kb_grid, text=f"{label}:").grid(row=i//3, column=(i%3)*2, sticky='e', padx=5, pady=3)
            entry = ttk.Entry(kb_grid, width=10)
            entry.insert(0, self.db.get(f'controls.{key}', ''))
            entry.grid(row=i//3, column=(i%3)*2+1, padx=5, pady=3)
            self.key_entries[key] = entry
        
        # Save button
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(controls_frame, text="Save Control Settings", 
                      command=self.save_control_settings, bootstyle="success").pack(pady=15)
        else:
            ttk.Button(controls_frame, text="Save Control Settings", 
                      command=self.save_control_settings).pack(pady=15)
    
    def create_theme_settings(self, parent_notebook):
        """Create theme settings sub-tab"""
        theme_frame = ttk.Frame(parent_notebook, padding=15)
        parent_notebook.add(theme_frame, text="  Theme  ")
        
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Label(theme_frame, text="Select Theme", font=('TkDefaultFont', 12, 'bold')).pack(pady=10)
            
            self.theme_var = tk.StringVar(value=self.db.get('theme.name', DEFAULT_THEME))
            
            # Theme selector
            theme_select_frame = ttk.Frame(theme_frame)
            theme_select_frame.pack(fill='x', pady=10)
            
            ttk.Label(theme_select_frame, text="Theme:").pack(side='left', padx=10)
            theme_combo = ttk.Combobox(theme_select_frame, textvariable=self.theme_var, 
                                       values=AVAILABLE_THEMES, state='readonly', width=20)
            theme_combo.pack(side='left', padx=5)
            
            ttk.Button(theme_select_frame, text="Apply Theme", command=self.apply_theme_selection,
                      bootstyle="success").pack(side='left', padx=10)
            
            # Theme preview
            preview_frame = ttk.Labelframe(theme_frame, text="Theme Categories", padding=10)
            preview_frame.pack(fill='x', pady=20)
            
            ttk.Label(preview_frame, text="Dark themes: darkly, cyborg, vapor, solar, superhero").pack(anchor='w', pady=2)
            ttk.Label(preview_frame, text="Light themes: flatly, journal, litera, minty, pulse, yeti, cosmo").pack(anchor='w', pady=2)
            
            ttk.Label(theme_frame, text="Theme changes take effect immediately.",
                     font=('TkDefaultFont', 9)).pack(pady=10)
        else:
            ttk.Label(theme_frame, text="Theme customization requires ttkbootstrap", 
                     font=('TkDefaultFont', 12)).pack(pady=20)
            ttk.Label(theme_frame, text="Install with: pip install ttkbootstrap").pack()
            ttk.Label(theme_frame, text="Then restart the application.").pack(pady=10)
    
    def create_connection_settings(self, parent_notebook):
        """Create connection settings sub-tab"""
        conn_frame = ttk.Frame(parent_notebook, padding=15)
        parent_notebook.add(conn_frame, text="  Connection  ")
        
        ttk.Label(conn_frame, text="Default Connection Settings", 
                 font=('TkDefaultFont', 12, 'bold')).pack(pady=10)
        
        grid_frame = ttk.Frame(conn_frame)
        grid_frame.pack(pady=10)
        
        ttk.Label(grid_frame, text="Default IP:").grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.default_ip_entry = ttk.Entry(grid_frame, width=20)
        self.default_ip_entry.insert(0, self.db.get('connection.ip'))
        self.default_ip_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(grid_frame, text="Default Port:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.default_port_entry = ttk.Entry(grid_frame, width=20)
        self.default_port_entry.insert(0, self.db.get('connection.port'))
        self.default_port_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(grid_frame, text="Timeout (sec):").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.timeout_entry = ttk.Entry(grid_frame, width=20)
        self.timeout_entry.insert(0, self.db.get('connection.timeout'))
        self.timeout_entry.grid(row=2, column=1, padx=5, pady=5)
        
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(conn_frame, text="Save Connection Settings", 
                      command=self.save_connection_settings, bootstyle="success").pack(pady=15)
        else:
            ttk.Button(conn_frame, text="Save Connection Settings", 
                      command=self.save_connection_settings).pack(pady=15)
    
    def create_logging_settings(self, parent_notebook):
        """Create logging settings sub-tab"""
        logging_frame = ttk.Frame(parent_notebook, padding=15)
        parent_notebook.add(logging_frame, text="  Logging  ")
        
        ttk.Label(logging_frame, text="Logging Configuration", 
                 font=('TkDefaultFont', 12, 'bold')).pack(pady=10)
        
        # Debug mode
        self.debug_mode_var = tk.BooleanVar(value=self.db.get_bool('logging.debug_mode'))
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Checkbutton(logging_frame, text="Debug Mode (log all commands/responses)", 
                           variable=self.debug_mode_var, command=self.toggle_debug_mode,
                           bootstyle="info-round-toggle").pack(anchor='w', padx=20, pady=5)
        else:
            ttk.Checkbutton(logging_frame, text="Debug Mode (log all commands/responses)", 
                           variable=self.debug_mode_var, command=self.toggle_debug_mode).pack(anchor='w', padx=20, pady=5)
        
        # Log retention
        if TTKBOOTSTRAP_AVAILABLE:
            retention_frame = ttk.Labelframe(logging_frame, text="Log Retention", padding=10, bootstyle="secondary")
        else:
            retention_frame = ttk.LabelFrame(logging_frame, text="Log Retention", padding=10)
        retention_frame.pack(fill='x', padx=20, pady=15)
        
        ret_control = ttk.Frame(retention_frame)
        ret_control.pack(fill='x', pady=5)
        
        ttk.Label(ret_control, text="Keep last").pack(side='left', padx=5)
        self.retention_var = tk.IntVar(value=self.db.get_int('logging.retention', 30))
        retention_spin = ttk.Spinbox(ret_control, from_=0, to=500, textvariable=self.retention_var, width=5)
        retention_spin.pack(side='left', padx=5)
        ttk.Label(ret_control, text="log files").pack(side='left', padx=5)
        
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(ret_control, text="Apply", command=self.apply_retention,
                      bootstyle="info-outline").pack(side='left', padx=10)
        else:
            ttk.Button(ret_control, text="Apply", command=self.apply_retention).pack(side='left', padx=10)
        
        ttk.Label(retention_frame, text="Set to 0 to disable file logging (not recommended).",
                 font=('TkDefaultFont', 9)).pack(anchor='w', pady=5)
        
        # Log location
        ttk.Separator(logging_frame, orient='horizontal').pack(fill='x', padx=20, pady=15)
        
        ttk.Label(logging_frame, text="Log Folder:").pack(anchor='w', padx=20)
        log_dir_text = str(self.file_logger.log_dir) if self.file_logger.log_dir else "N/A"
        ttk.Label(logging_frame, text=log_dir_text, font=('Consolas', 9)).pack(anchor='w', padx=40, pady=5)
        
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(logging_frame, text="Open Log Folder", command=self.open_log_folder,
                      bootstyle="secondary-outline").pack(anchor='w', padx=20, pady=10)
        else:
            ttk.Button(logging_frame, text="Open Log Folder", command=self.open_log_folder).pack(anchor='w', padx=20, pady=10)
    
    def bind_keyboard_controls(self):
        """Bind keyboard controls"""
        control_mode = self.db.get('controls.mode', 'latching')
        
        up_key = self.db.get('controls.up', 'w')
        down_key = self.db.get('controls.down', 's')
        left_key = self.db.get('controls.left', 'a')
        right_key = self.db.get('controls.right', 'd')
        stop_key = self.db.get('controls.stop', 'space')
        estop_key = self.db.get('controls.estop', 'Escape')
        
        # Clear existing
        for key in ['w', 's', 'a', 'd', 'space', 'Escape', 'Up', 'Down', 'Left', 'Right']:
            try:
                self.root.unbind(f"<KeyPress-{key}>")
                self.root.unbind(f"<KeyRelease-{key}>")
            except:
                pass
        
        if control_mode == 'momentary':
            self.root.bind(f"<KeyPress-{up_key}>", lambda e: self.key_move('up'))
            self.root.bind(f"<KeyRelease-{up_key}>", lambda e: self.key_release('up'))
            self.root.bind(f"<KeyPress-{down_key}>", lambda e: self.key_move('down'))
            self.root.bind(f"<KeyRelease-{down_key}>", lambda e: self.key_release('down'))
            self.root.bind(f"<KeyPress-{left_key}>", lambda e: self.key_move('left'))
            self.root.bind(f"<KeyRelease-{left_key}>", lambda e: self.key_release('left'))
            self.root.bind(f"<KeyPress-{right_key}>", lambda e: self.key_move('right'))
            self.root.bind(f"<KeyRelease-{right_key}>", lambda e: self.key_release('right'))
            
            self.root.bind("<KeyPress-Up>", lambda e: self.key_move('up'))
            self.root.bind("<KeyRelease-Up>", lambda e: self.key_release('up'))
            self.root.bind("<KeyPress-Down>", lambda e: self.key_move('down'))
            self.root.bind("<KeyRelease-Down>", lambda e: self.key_release('down'))
            self.root.bind("<KeyPress-Left>", lambda e: self.key_move('left'))
            self.root.bind("<KeyRelease-Left>", lambda e: self.key_release('left'))
            self.root.bind("<KeyPress-Right>", lambda e: self.key_move('right'))
            self.root.bind("<KeyRelease-Right>", lambda e: self.key_release('right'))
        else:
            self.root.bind(f"<KeyPress-{up_key}>", lambda e: self.move('up'))
            self.root.bind(f"<KeyPress-{down_key}>", lambda e: self.move('down'))
            self.root.bind(f"<KeyPress-{left_key}>", lambda e: self.move('left'))
            self.root.bind(f"<KeyPress-{right_key}>", lambda e: self.move('right'))
            
            self.root.bind("<Up>", lambda e: self.move('up'))
            self.root.bind("<Down>", lambda e: self.move('down'))
            self.root.bind("<Left>", lambda e: self.move('left'))
            self.root.bind("<Right>", lambda e: self.move('right'))
        
        self.root.bind(f"<KeyPress-{stop_key}>", lambda e: self.stop_all())
        self.root.bind(f"<KeyPress-{estop_key}>", lambda e: self.emergency_stop())
    
    def key_move(self, direction):
        """Handle key press for movement (momentary mode)"""
        if direction not in self.keys_pressed:
            self.keys_pressed.add(direction)
            self.move(direction)
    
    def key_release(self, direction):
        """Handle key release (momentary mode)"""
        if direction in self.keys_pressed:
            self.keys_pressed.discard(direction)
            if direction in ('up', 'down'):
                self.stop_axis(2)
            else:
                self.stop_axis(1)
    
    def stop_axis(self, axis):
        """Stop a single axis"""
        if not self.connected:
            return
        self.protocol.stop_motion(str(axis))
        self.axes_moving[axis] = False
    
    def check_altitude_limits(self, direction):
        """Check if movement would violate altitude limits. Returns True if OK to move."""
        if not self.db.get_bool('limits.enforce', True):
            return True
        
        if self.current_alt_deg is None:
            return True
        
        alt_min = self.db.get_float('limits.alt_min', -5.0)
        alt_max = self.db.get_float('limits.alt_max', 90.0)
        
        if direction == 'up' and self.current_alt_deg >= alt_max:
            self.log(f"⚠ Altitude limit reached ({alt_max}°) - cannot move up")
            return False
        elif direction == 'down' and self.current_alt_deg <= alt_min:
            self.log(f"⚠ Altitude limit reached ({alt_min}°) - cannot move down")
            return False
        
        return True
    
    def log(self, message):
        """Add message to activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.log_text.insert('end', f"[{timestamp}] {message}\n")
            self.log_text.see('end')
        else:
            self.log_text.configure(state='normal')
            self.log_text.insert('end', f"[{timestamp}] {message}\n")
            self.log_text.see('end')
            self.log_text.configure(state='disabled')
        
        self.file_logger.log(message, level='INFO')
    
    def toggle_connection(self):
        """Connect or disconnect"""
        if self.connected:
            if self.status_monitor:
                self.status_monitor.stop()
                self.status_monitor = None
            
            self.stop_all()
            if self.protocol:
                self.protocol.close()
            self.protocol = None
            self.connected = False
            
            if TTKBOOTSTRAP_AVAILABLE:
                self.connect_btn.configure(text="Connect", bootstyle="success")
                self.status_label.configure(text="● Disconnected", bootstyle="danger")
            else:
                self.connect_btn.configure(text="Connect")
                self.status_label.configure(text="● Disconnected", foreground="red")
            
            self.log("Disconnected")
            
            if self.auto_update_var.get():
                self.auto_update_var.set(False)
                self.toggle_auto_update()
        else:
            ip = self.ip_entry.get()
            port = int(self.port_entry.get())
            timeout = self.db.get_float('connection.timeout', 2.0)
            
            self.log(f"Connecting to {ip}:{port}...")
            self.protocol = SkyWatcherProtocol(ip, port, timeout, log_callback=self.log)
            
            try:
                version = self.protocol.get_motor_board_version('1')
                if version is not None:
                    self.connected = True
                    
                    if TTKBOOTSTRAP_AVAILABLE:
                        self.connect_btn.configure(text="Disconnect", bootstyle="danger")
                        self.status_label.configure(text="● Connected", bootstyle="success")
                    else:
                        self.connect_btn.configure(text="Disconnect")
                        self.status_label.configure(text="● Connected", foreground="green")
                    
                    self.log(f"✓ Connected - Version: {version}")
                    
                    # Initialize axes
                    self.protocol.send_command(":F1")
                    self.protocol.send_command(":F2")
                    self.log("✓ Axes initialized")
                    
                    # Query parameters
                    self.protocol.get_counts_per_revolution(self.protocol.AXIS_AZ)
                    self.protocol.get_counts_per_revolution(self.protocol.AXIS_ALT)
                    self.protocol.get_timer_freq()
                    
                    # Start status monitor
                    self.status_monitor = StatusMonitor(self.protocol, self.file_logger, self.on_status_update)
                    self.status_monitor.start()
                    
                    self.log("✓ Ready!")
                else:
                    self.log("✗ Failed to connect")
                    messagebox.showerror("Connection Error", "Could not connect to telescope.")
                    self.protocol.close()
                    self.protocol = None
            except Exception as e:
                self.log(f"✗ Error: {e}")
                messagebox.showerror("Connection Error", str(e))
                if self.protocol:
                    self.protocol.close()
                self.protocol = None
    
    def move(self, direction):
        """Start moving in direction"""
        if not self.connected:
            return
        
        if self.estop_active:
            self.log("✗ E-Stop active")
            return
        
        # Check altitude limits for up/down
        if direction in ('up', 'down') and not self.check_altitude_limits(direction):
            return
        
        speed = self.speed_var.get()
        self.log(f"Move {direction} @ {speed:.1f}°/s")
        
        if direction == 'up':
            self.axes_moving[2] = True
            self.protocol.slew_fixed_rate(self.protocol.AXIS_ALT, True, speed)
        elif direction == 'down':
            self.axes_moving[2] = True
            self.protocol.slew_fixed_rate(self.protocol.AXIS_ALT, False, speed)
        elif direction == 'left':
            self.axes_moving[1] = True
            self.protocol.slew_fixed_rate(self.protocol.AXIS_AZ, False, speed)
        elif direction == 'right':
            self.axes_moving[1] = True
            self.protocol.slew_fixed_rate(self.protocol.AXIS_AZ, True, speed)
    
    def stop_all(self):
        """Stop all motion"""
        if not self.connected:
            return
        
        self.log("STOP ALL")
        self.protocol.stop_motion(self.protocol.AXIS_AZ)
        self.protocol.stop_motion(self.protocol.AXIS_ALT)
        self.axes_moving = {1: False, 2: False}
        self.keys_pressed.clear()
        self.estop_active = False
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.estop_btn.configure(text="🛑 EMERGENCY STOP", bootstyle="danger")
        else:
            self.estop_btn.configure(text="🛑 EMERGENCY STOP")
    
    def emergency_stop(self):
        """Emergency stop"""
        if not self.connected:
            return
        
        self.estop_active = True
        self.axes_moving = {1: False, 2: False}
        self.keys_pressed.clear()
        self.protocol.instant_stop(self.protocol.AXIS_AZ)
        self.protocol.instant_stop(self.protocol.AXIS_ALT)
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.estop_btn.configure(text="⚠️ E-STOP ACTIVE", bootstyle="warning")
        else:
            self.estop_btn.configure(text="⚠️ E-STOP ACTIVE")
        
        self.log("⚠️ EMERGENCY STOP")
        messagebox.showwarning("Emergency Stop", "E-Stop activated!\nClick STOP to clear.")
    
    def on_status_update(self, axis: int, status: dict):
        """Callback from StatusMonitor"""
        self.root.after(0, lambda: self._update_status_display(axis, status))
    
    def _update_status_display(self, axis: int, status: dict):
        """Update status indicator display"""
        raw = status.get('raw', 0)
        running = status.get('running', False)
        blocked = status.get('blocked', False)
        
        if blocked:
            indicator_text = "⚠ BLOCKED"
            color = 'red'
        elif running:
            indicator_text = "● Moving"
            color = 'blue'
        else:
            indicator_text = "● Stopped"
            color = 'gray'
        
        raw_text = StatusDecoder.to_string(raw)
        
        if axis == 1:
            self.az_status_indicator.configure(text=indicator_text, foreground=color)
            self.az_status_raw.configure(text=raw_text)
        else:
            self.alt_status_indicator.configure(text=indicator_text, foreground=color)
            self.alt_status_raw.configure(text=raw_text)
    
    def start_position_updates(self):
        """Start position update timer"""
        self.update_position_display()
        self.root.after(1000, self.start_position_updates)
    
    def update_position_display(self):
        """Update position display"""
        if not self.connected or not self.show_pos_var.get():
            return
        
        try:
            az_pos = self.protocol.get_position(self.protocol.AXIS_AZ)
            alt_pos = self.protocol.get_position(self.protocol.AXIS_ALT)
            
            if az_pos is None or alt_pos is None:
                return
            
            az_deg = self.protocol.counts_to_degrees(az_pos, self.protocol.AXIS_AZ)
            alt_deg = self.protocol.counts_to_degrees(alt_pos, self.protocol.AXIS_ALT)
            
            # Store current altitude for limit checking
            self.current_alt_deg = alt_deg
            
            format_type = self.pos_format_var.get()
            
            if format_type == 'degrees' and az_deg is not None and alt_deg is not None:
                if hasattr(self, 'az_deg_label'):
                    self.az_deg_label.configure(text=f"{az_deg:.4f}°")
                if hasattr(self, 'alt_deg_label'):
                    self.alt_deg_label.configure(text=f"{alt_deg:.4f}°")
                    
            elif format_type == 'raw':
                if hasattr(self, 'az_raw_label'):
                    self.az_raw_label.configure(text=f"{az_pos:,}")
                if hasattr(self, 'alt_raw_label'):
                    self.alt_raw_label.configure(text=f"{alt_pos:,}")
                
            elif format_type == 'both' and az_deg is not None and alt_deg is not None:
                if hasattr(self, 'az_both_label'):
                    self.az_both_label.configure(text=f"{az_deg:.2f}° ({az_pos:,})")
                if hasattr(self, 'alt_both_label'):
                    self.alt_both_label.configure(text=f"{alt_deg:.2f}° ({alt_pos:,})")
                    
            elif format_type == 'coordinates' and az_deg is not None and alt_deg is not None:
                if hasattr(self, 'coord_label'):
                    self.coord_label.configure(text=f"Az: {az_deg % 360:.4f}°\nAlt: {alt_deg:.4f}°")
        except Exception:
            pass
    
    def refresh_positions(self):
        """Manual position refresh"""
        self.update_position_display()
    
    def toggle_position_display(self):
        """Toggle position display"""
        self.db.set('display.show_positions', str(self.show_pos_var.get()))
        self.create_position_labels()
    
    def update_position_format(self):
        """Update position format"""
        self.db.set('display.position_format', self.pos_format_var.get())
        self.create_position_labels()
    
    def refresh_diagnostics(self):
        """Refresh diagnostics display"""
        if not self.connected:
            return
        
        text = ""
        
        for axis_name, axis_id in [("AZIMUTH (Axis 1)", '1'), ("ALTITUDE (Axis 2)", '2')]:
            text += f"\n{'='*50}\n{axis_name}\n{'='*50}\n\n"
            
            pos = self.protocol.get_position(axis_id)
            if pos is not None:
                deg = self.protocol.counts_to_degrees(pos, axis_id)
                text += f"Position: {pos:,} counts"
                if deg is not None:
                    text += f" ({deg:.4f}°)"
                text += "\n"
            
            status = self.protocol.get_status(axis_id)
            if status:
                text += f"\nStatus (0x{status['raw']:02X}):\n"
                text += f"  Running:     {status['running']}\n"
                text += f"  Blocked:     {status['blocked']}\n"
                text += f"  Initialized: {status['initialized']}\n"
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.diag_text.delete('1.0', 'end')
            self.diag_text.insert('1.0', text)
        else:
            self.diag_text.configure(state='normal')
            self.diag_text.delete('1.0', 'end')
            self.diag_text.insert('1.0', text)
            self.diag_text.configure(state='disabled')
    
    def query_system_info(self):
        """Query system information"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        text = "MOUNT SYSTEM INFORMATION\n" + "=" * 50 + "\n\n"
        
        timer_freq = self.protocol.get_timer_freq()
        if timer_freq:
            text += f"Timer Frequency: {timer_freq:,} Hz\n\n"
        
        for axis_name, axis_id in [("AZIMUTH (Axis 1)", '1'), ("ALTITUDE (Axis 2)", '2')]:
            text += f"{'-'*50}\n{axis_name}\n{'-'*50}\n\n"
            
            version = self.protocol.get_motor_board_version(axis_id)
            text += f"Board Version: {version}\n"
            
            cpr = self.protocol.get_counts_per_revolution(axis_id)
            if cpr:
                text += f"CPR: {cpr:,}\n"
                text += f"Resolution: {360.0/cpr:.6f}°/count\n"
            
            pos = self.protocol.get_position(axis_id)
            if pos is not None:
                deg = self.protocol.counts_to_degrees(pos, axis_id)
                text += f"\nPosition: {pos:,} counts"
                if deg is not None:
                    text += f" ({deg:.4f}°)"
                text += "\n"
            
            status = self.protocol.get_status(axis_id)
            if status:
                text += f"\nStatus: 0x{status['raw']:02X}\n"
            
            text += "\n"
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.diag_text.delete('1.0', 'end')
            self.diag_text.insert('1.0', text)
        else:
            self.diag_text.configure(state='normal')
            self.diag_text.delete('1.0', 'end')
            self.diag_text.insert('1.0', text)
            self.diag_text.configure(state='disabled')
        
        self.log("System info queried")
    
    def toggle_auto_update(self):
        """Toggle auto-update"""
        if self.auto_update_var.get():
            self.update_running = True
            self.update_thread = threading.Thread(target=self.auto_update_loop, daemon=True)
            self.update_thread.start()
            self.db.set('display.auto_update', 'True')
        else:
            self.update_running = False
            self.db.set('display.auto_update', 'False')
    
    def auto_update_loop(self):
        """Auto-update loop"""
        while self.update_running and self.connected:
            self.root.after(0, self.refresh_diagnostics)
            time.sleep(1.0 / max(0.1, self.update_rate_var.get()))
    
    def goto_home(self):
        """Go to home position"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        home_az = self.protocol.degrees_to_counts(self.db.get_float('positions.home_az'), self.protocol.AXIS_AZ)
        home_alt = self.protocol.degrees_to_counts(self.db.get_float('positions.home_alt'), self.protocol.AXIS_ALT)
        
        if home_az is not None and home_alt is not None:
            self.protocol.goto_position(self.protocol.AXIS_AZ, home_az)
            self.protocol.goto_position(self.protocol.AXIS_ALT, home_alt)
            self.log("Going to HOME")
    
    def set_home(self):
        """Set current position as home"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        az_pos = self.protocol.get_position(self.protocol.AXIS_AZ)
        alt_pos = self.protocol.get_position(self.protocol.AXIS_ALT)
        
        if az_pos is not None and alt_pos is not None:
            az_deg = self.protocol.counts_to_degrees(az_pos, self.protocol.AXIS_AZ)
            alt_deg = self.protocol.counts_to_degrees(alt_pos, self.protocol.AXIS_ALT)
            
            if az_deg is not None and alt_deg is not None:
                self.db.set('positions.home_az', str(az_deg))
                self.db.set('positions.home_alt', str(alt_deg))
                self.log(f"HOME set: Az={az_deg:.2f}°, Alt={alt_deg:.2f}°")
                messagebox.showinfo("Home Set", f"Az: {az_deg:.2f}°\nAlt: {alt_deg:.2f}°")
    
    def goto_stow(self):
        """Go to stow position"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        stow_az = self.protocol.degrees_to_counts(self.db.get_float('positions.stow_az'), self.protocol.AXIS_AZ)
        stow_alt = self.protocol.degrees_to_counts(self.db.get_float('positions.stow_alt'), self.protocol.AXIS_ALT)
        
        if stow_az is not None and stow_alt is not None:
            self.protocol.goto_position(self.protocol.AXIS_AZ, stow_az)
            self.protocol.goto_position(self.protocol.AXIS_ALT, stow_alt)
            self.log("Going to STOW")
    
    def set_stow(self):
        """Set current position as stow"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        az_pos = self.protocol.get_position(self.protocol.AXIS_AZ)
        alt_pos = self.protocol.get_position(self.protocol.AXIS_ALT)
        
        if az_pos is not None and alt_pos is not None:
            az_deg = self.protocol.counts_to_degrees(az_pos, self.protocol.AXIS_AZ)
            alt_deg = self.protocol.counts_to_degrees(alt_pos, self.protocol.AXIS_ALT)
            
            if az_deg is not None and alt_deg is not None:
                self.db.set('positions.stow_az', str(az_deg))
                self.db.set('positions.stow_alt', str(alt_deg))
                self.log(f"STOW set: Az={az_deg:.2f}°, Alt={alt_deg:.2f}°")
                messagebox.showinfo("Stow Set", f"Az: {az_deg:.2f}°\nAlt: {alt_deg:.2f}°")
    
    def zero_position(self):
        """Set current position to zero"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        if messagebox.askyesno("Confirm", "Set current position to 0,0?"):
            self.protocol.set_position(self.protocol.AXIS_AZ, 0)
            self.protocol.set_position(self.protocol.AXIS_ALT, 0)
            self.log("Position zeroed")
    
    def reinitialize(self):
        """Re-initialize mount"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        if messagebox.askyesno("Confirm", "Re-initialize mount?"):
            self.protocol.initialization_done()
            self.log("Mount re-initialized")
    
    def update_speed_label(self, *args):
        """Update speed label"""
        self.speed_label.configure(text=f"{self.speed_var.get():.2f}")
        self.db.set('speed.default', str(self.speed_var.get()))
    
    def save_control_settings(self):
        """Save control settings"""
        self.db.set('controls.mode', self.control_mode_var.get())
        self.db.set('limits.enforce', str(self.enforce_limits_var.get()))
        self.db.set('limits.alt_min', str(self.alt_min_var.get()))
        self.db.set('limits.alt_max', str(self.alt_max_var.get()))
        
        for key, entry in self.key_entries.items():
            self.db.set(f'controls.{key}', entry.get())
        
        self.bind_keyboard_controls()
        self.setup_button_bindings()
        
        messagebox.showinfo("Saved", "Control settings saved!")
        self.log("Control settings saved")
    
    def apply_theme_selection(self):
        """Apply selected theme"""
        if not TTKBOOTSTRAP_AVAILABLE:
            return
        
        theme_name = self.theme_var.get()
        try:
            self.root.style.theme_use(theme_name)
            self.db.set('theme.name', theme_name)
            self.log(f"Theme changed to: {theme_name}")
        except Exception as e:
            messagebox.showerror("Theme Error", f"Could not apply theme: {e}")
    
    def save_connection_settings(self):
        """Save connection settings"""
        self.db.set('connection.ip', self.default_ip_entry.get())
        self.db.set('connection.port', self.default_port_entry.get())
        self.db.set('connection.timeout', self.timeout_entry.get())
        
        self.ip_entry.delete(0, 'end')
        self.ip_entry.insert(0, self.default_ip_entry.get())
        self.port_entry.delete(0, 'end')
        self.port_entry.insert(0, self.default_port_entry.get())
        
        messagebox.showinfo("Saved", "Connection settings saved!")
        self.log("Connection settings saved")
    
    def toggle_debug_mode(self):
        """Toggle debug mode"""
        enabled = self.debug_mode_var.get()
        self.file_logger.set_debug_mode(enabled)
        self.db.set('logging.debug_mode', str(enabled))
        self.log(f"Debug mode {'enabled' if enabled else 'disabled'}")
    
    def apply_retention(self):
        """Apply log retention setting"""
        retention = self.retention_var.get()
        
        if retention == 0:
            if not messagebox.askyesno("Warning", 
                "Setting retention to 0 will disable file logging.\n"
                "Logs will not be preserved.\n\nContinue?"):
                self.retention_var.set(self.db.get_int('logging.retention', 30))
                return
        
        self.db.set('logging.retention', str(retention))
        self.file_logger.set_retention(retention)
        self.log(f"Log retention set to {retention} files")
    
    def open_log_folder(self):
        """Open log folder"""
        import subprocess
        import platform
        
        folder = str(self.file_logger.log_dir)
        system = platform.system()
        
        try:
            if system == 'Windows':
                subprocess.run(['explorer', folder])
            elif system == 'Darwin':
                subprocess.run(['open', folder])
            else:
                subprocess.run(['xdg-open', folder])
        except Exception as e:
            messagebox.showinfo("Log Folder", f"Logs are in:\n{folder}")
    
    def on_closing(self):
        """Handle window close"""
        if self.status_monitor:
            self.status_monitor.stop()
        
        self.update_running = False
        
        if self.connected:
            self.stop_all()
            if self.protocol:
                self.protocol.close()
        
        if self.file_logger:
            self.file_logger.close()
        
        self.root.destroy()


def main():
    if TTKBOOTSTRAP_AVAILABLE:
        # Get saved theme
        db = DatabaseConfig()
        theme = db.get('theme.name', DEFAULT_THEME)
        root = ttk.Window(themename=theme)
    else:
        root = tk.Tk()
    
    app = TelescopeGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
