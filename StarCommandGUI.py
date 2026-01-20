#!/usr/bin/env python3
"""
Sky-Watcher Virtuoso GTi 150P Professional Controller
Full-featured GUI with configurable settings, themes, and keyboard controls

Version: 0.4.2

CHANGELOG v0.4.2:
  - FIXED: Activity log no longer floods with protocol traffic
  - FIXED: Separated UI logging from protocol logging (protocol → file only)
  - FIXED: ttkbootstrap deprecation warnings (updated imports)
  - FIXED: Removed invalid theme 'cerulean' from list
  - FIXED: Wild position values filtered out (sanity checking)
  - FIXED: Text contrast issues in dark themes
  - NEW: Collapsible activity log on Control tab
  - NEW: Dedicated "Comms Log" tab for protocol debugging with search/filter
  - NEW: Protocol logging toggle in settings
  - NEW: Position value sanity checking (filters corrupted packets)

PREVIOUS:
  - v0.4.1: Altitude limits, logging folder, ttkbootstrap
  - v0.4.0: SQLite persistence, momentary controls, combined diagnostics
  - v0.3.x: Status monitoring, file logging, protocol fixes

REQUIREMENTS:
  pip install ttkbootstrap   (optional but recommended)

Works with GTi 150P firmware using simple protocol without X10 prefix.
"""

import socket
import time
import sys
import threading
import sqlite3
import os
import re
from datetime import datetime
from pathlib import Path
from collections import deque

# Try to import ttkbootstrap with updated imports
TTKBOOTSTRAP_AVAILABLE = False
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    # Updated imports to avoid deprecation warnings
    try:
        from ttkbootstrap.widgets.scrolled import ScrolledText
    except (ImportError, AttributeError):
        try:
            from ttkbootstrap.scrolled import ScrolledText
        except ImportError:
            from ttkbootstrap.widgets import ScrolledText
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    pass

if not TTKBOOTSTRAP_AVAILABLE:
    import tkinter as tk
    from tkinter import ttk
    from tkinter.scrolledtext import ScrolledText as TkScrolledText
else:
    import tkinter as tk

from tkinter import messagebox

VERSION = "0.4.2"
DEFAULT_THEME = "darkly"

# Valid ttkbootstrap themes (verified to exist)
AVAILABLE_THEMES = [
    # Dark themes
    "darkly", "cyborg", "vapor", "solar", "superhero",
    # Light themes  
    "flatly", "journal", "litera", "minty", "pulse", 
    "sandstone", "united", "yeti", "morph", "simplex",
    "cosmo", "lumen"
]

# Status byte bit definitions
STATUS_RUNNING = 0x01
STATUS_BLOCKED = 0x02
STATUS_INIT = 0x04

# Position sanity limits (filter corrupted packets)
POSITION_SANITY_MIN_DEG = -720.0  # Allow 2 full rotations negative
POSITION_SANITY_MAX_DEG = 720.0   # Allow 2 full rotations positive
ALTITUDE_SANITY_MIN_DEG = -90.0
ALTITUDE_SANITY_MAX_DEG = 180.0   # Allow some overflow for wrap


class ToolTip:
    """Simple tooltip class for widgets."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind('<Enter>', self.show_tooltip)
        self.widget.bind('<Leave>', self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tooltip, text=self.text, justify='left',
                        background="#ffffe0", relief='solid', borderwidth=1,
                        font=("TkDefaultFont", 9))
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def update_text(self, new_text):
        """Update tooltip text dynamically."""
        self.text = new_text


class DatabaseConfig:
    """SQLite-based configuration manager."""
    
    DEFAULT_SETTINGS = {
        'connection.ip': '192.168.4.1',
        'connection.port': '11880',
        'connection.timeout': '2.0',
        'controls.up': 'w',
        'controls.down': 's',
        'controls.left': 'a',
        'controls.right': 'd',
        'controls.stop': 'space',
        'controls.estop': 'Escape',
        'controls.mode': 'latching',
        'limits.alt_min': '-5.0',
        'limits.alt_max': '90.0',
        'limits.enforce': 'True',
        'display.position_format': 'both',
        'display.show_positions': 'True',
        'display.auto_update': 'False',
        'display.update_rate': '1.0',
        'display.log_expanded': 'True',
        'positions.home_az': '0.0',
        'positions.home_alt': '0.0',
        'positions.stow_az': '0.0',
        'positions.stow_alt': '90.0',
        'theme.name': DEFAULT_THEME,
        'speed.default': '1.0',
        'speed.min': '0.1',
        'speed.max': '10.0',
        'logging.debug_mode': 'False',
        'logging.retention': '30',
        'logging.show_protocol': 'False',  # Show protocol in Comms Log tab
    }
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            config_dir = Path.home() / '.skywatcher_controller'
            config_dir.mkdir(exist_ok=True)
            db_path = config_dir / 'settings.db'
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        for key, value in self.DEFAULT_SETTINGS.items():
            cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
        conn.commit()
        conn.close()
    
    def get(self, key: str, default=None):
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
        conn.commit()
        conn.close()


class FileLogger:
    """File logging with retention management."""
    
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
        if self.retention <= 0:
            return
        try:
            log_files = sorted(
                self.log_dir.glob('telescope_control_*.log'),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            for old_file in log_files[self.retention:]:
                try:
                    old_file.unlink()
                except Exception:
                    pass
        except Exception:
            pass
    
    def set_retention(self, retention: int):
        self.retention = retention
        self._cleanup_old_logs()
    
    def _start_new_log(self):
        if self.retention == 0:
            self.log_file = None
            self.log_path = None
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = self.log_dir / f"telescope_control_{timestamp}.log"
        try:
            self.log_file = open(self.log_path, 'w', encoding='utf-8')
            self.log_file.write(f"Telescope Control Log - v{VERSION}\n")
            self.log_file.write(f"Started: {datetime.now().isoformat()}\n")
            self.log_file.write("=" * 60 + "\n\n")
            self.log_file.flush()
        except Exception as e:
            print(f"Warning: Could not create log file: {e}")
            self.log_file = None
    
    def set_debug_mode(self, enabled: bool):
        self.debug_mode = enabled
    
    def log(self, message: str, level: str = 'INFO'):
        if level == 'DEBUG' and not self.debug_mode:
            return
        if not self.log_file:
            return
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with self._lock:
            try:
                self.log_file.write(f"[{timestamp}] [{level:7}] {message}\n")
                self.log_file.flush()
            except Exception:
                pass
    
    def close(self):
        if self.log_file:
            self.log(f"Log closed: {datetime.now().isoformat()}", level='INFO')
            try:
                self.log_file.close()
            except Exception:
                pass


class CommsBuffer:
    """Thread-safe buffer for protocol communications logging."""
    
    def __init__(self, maxlen: int = 5000):
        self.buffer = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self.callbacks = []
    
    def add(self, direction: str, message: str):
        """Add a communication entry."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{timestamp}] {direction} {message}"
        with self._lock:
            self.buffer.append(entry)
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(entry)
            except Exception:
                pass
    
    def get_all(self) -> list:
        """Get all entries."""
        with self._lock:
            return list(self.buffer)
    
    def clear(self):
        """Clear the buffer."""
        with self._lock:
            self.buffer.clear()
    
    def search(self, pattern: str, regex: bool = False) -> list:
        """Search entries with optional regex."""
        with self._lock:
            entries = list(self.buffer)
        
        if not pattern:
            return entries
        
        results = []
        if regex:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                results = [e for e in entries if compiled.search(e)]
            except re.error:
                results = []
        else:
            pattern_lower = pattern.lower()
            results = [e for e in entries if pattern_lower in e.lower()]
        
        return results
    
    def register_callback(self, callback):
        """Register a callback for new entries."""
        self.callbacks.append(callback)
    
    def unregister_callback(self, callback):
        """Unregister a callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)


class StatusDecoder:
    """Decodes SynScan status bytes."""
    
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
        parts = ["Running" if d['running'] else "Stopped"]
        if d['blocked']:
            parts.append("BLOCKED")
        if d['initialized']:
            parts.append("Init")
        return f"0x{status_byte:02X} ({', '.join(parts)})"


class StatusMonitor:
    """Monitors axis status with 200ms polling."""
    
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
    
    def stop(self):
        self.monitoring = False
        if self._thread:
            self._thread.join(timeout=1.0)
    
    def _monitor_loop(self):
        while self.monitoring:
            if self.protocol:
                for axis in [1, 2]:
                    try:
                        status = self.protocol.get_status(str(axis), log_to_ui=False)
                        if status:
                            raw = status.get('raw', 0)
                            old = self._last_status.get(axis)
                            
                            # Log status changes to file
                            if old is not None and raw != old and self.file_logger:
                                axis_name = "Azimuth" if axis == 1 else "Altitude"
                                self.file_logger.log(
                                    f"{axis_name} status: 0x{old:02X} -> 0x{raw:02X}",
                                    level='STATUS'
                                )
                            
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
    """SkyWatcher Motor Controller Protocol implementation."""
    
    def __init__(self, ip='192.168.4.1', port=11880, timeout=2.0, 
                 file_logger=None, comms_buffer=None):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        self.file_logger = file_logger
        self.comms_buffer = comms_buffer
        
        self.AXIS_AZ = '1'
        self.AXIS_ALT = '2'
        self.AXIS_BOTH = '3'
        
        self.cpr_az = None
        self.cpr_alt = None
        self.timer_freq = None
    
    def send_command(self, command, log_to_ui=True):
        """Send command and receive response."""
        if not command.endswith('\r'):
            command += '\r'
        
        # Log to file (debug level)
        if self.file_logger:
            self.file_logger.log(f"SEND: {repr(command)}", level='DEBUG')
        
        # Log to comms buffer for UI
        if log_to_ui and self.comms_buffer:
            self.comms_buffer.add("→", repr(command))
        
        try:
            self.sock.sendto(command.encode('ascii'), (self.ip, self.port))
            data, addr = self.sock.recvfrom(1024)
            response = data.decode('ascii').strip()
            
            if self.file_logger:
                self.file_logger.log(f"RECV: {repr(response)}", level='DEBUG')
            
            if log_to_ui and self.comms_buffer:
                self.comms_buffer.add("←", repr(response))
            
            return response
        except socket.timeout:
            if self.file_logger:
                self.file_logger.log("TIMEOUT", level='DEBUG')
            if log_to_ui and self.comms_buffer:
                self.comms_buffer.add("✗", "TIMEOUT")
            return None
        except Exception as e:
            if self.file_logger:
                self.file_logger.log(f"ERROR: {e}", level='ERROR')
            if log_to_ui and self.comms_buffer:
                self.comms_buffer.add("✗", f"ERROR: {e}")
            return None
    
    def parse_hex_response(self, response):
        """Parse hex data (LSB first)."""
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
        """Format value as hex (LSB first)."""
        hex_str = f"{value:0{bytes_count*2}X}"
        return ''.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)][::-1])
    
    def get_position(self, axis, log_to_ui=True):
        """Get current position."""
        response = self.send_command(f":j{axis}", log_to_ui=log_to_ui)
        if response:
            pos = self.parse_hex_response(response)
            if pos is not None:
                return pos - 0x800000
        return None
    
    def set_position(self, axis, position):
        """Set current position."""
        hex_pos = self.format_hex_data(position + 0x800000, 3)
        response = self.send_command(f":E{axis}{hex_pos}")
        return response and response.startswith('=')
    
    def set_motion_mode(self, axis, goto_mode=False, direction_cw=True, high_speed=False):
        """Set motion mode."""
        if goto_mode:
            mode_code = ("00" if direction_cw else "01") if high_speed else ("20" if direction_cw else "21")
        else:
            mode_code = "10" if direction_cw else "11"
        response = self.send_command(f":G{axis}{mode_code}")
        return response and response.startswith('=')
    
    def set_step_period(self, axis, period):
        """Set step period."""
        hex_period = self.format_hex_data(period, 3)
        response = self.send_command(f":I{axis}{hex_period}")
        return response and response.startswith('=')
    
    def start_motion(self, axis):
        """Start motion."""
        response = self.send_command(f":J{axis}")
        return response and response.startswith('=')
    
    def stop_motion(self, axis):
        """Stop motion."""
        response = self.send_command(f":K{axis}")
        return response and response.startswith('=')
    
    def instant_stop(self, axis):
        """Instant stop."""
        response = self.send_command(f":L{axis}")
        return response and response.startswith('=')
    
    def get_counts_per_revolution(self, axis):
        """Get CPR."""
        response = self.send_command(f":a{axis}")
        cpr = self.parse_hex_response(response)
        if cpr:
            if axis == self.AXIS_AZ:
                self.cpr_az = cpr
            else:
                self.cpr_alt = cpr
        return cpr
    
    def get_timer_freq(self):
        """Get timer frequency."""
        if self.timer_freq:
            return self.timer_freq
        response = self.send_command(":b1")
        freq = self.parse_hex_response(response)
        if freq:
            self.timer_freq = freq
        return freq
    
    def get_status(self, axis, log_to_ui=True):
        """Get motor status."""
        response = self.send_command(f":f{axis}", log_to_ui=log_to_ui)
        if not response or not response.startswith('='):
            return None
        try:
            status = int(response[1:3], 16)
            return {
                'running': bool(status & 0x01),
                'blocked': bool(status & 0x02),
                'initialized': bool(status & 0x04),
                'raw': status
            }
        except ValueError:
            return None
    
    def get_motor_board_version(self, axis):
        """Get motor board version."""
        response = self.send_command(f":e{axis}")
        if response and response.startswith('='):
            return response[1:].replace('\r', '')
        return None
    
    def initialization_done(self):
        """Signal initialization done."""
        response = self.send_command(":F3")
        return response and response.startswith('=')
    
    def slew_fixed_rate(self, axis, direction_positive=True, speed_deg_per_sec=1.0):
        """Slew at fixed rate."""
        cpr = self.cpr_az if axis == self.AXIS_AZ else self.cpr_alt
        if not cpr:
            cpr = self.get_counts_per_revolution(axis)
        
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
        """Goto specific position."""
        current = self.get_position(axis)
        if current is None:
            return False
        
        direction_cw = target_position > current
        if not self.set_motion_mode(axis, goto_mode=True, direction_cw=direction_cw):
            return False
        
        hex_target = self.format_hex_data(target_position + 0x800000, 3)
        response = self.send_command(f":S{axis}{hex_target}")
        if not response or not response.startswith('='):
            return False
        
        return self.start_motion(axis)
    
    def counts_to_degrees(self, counts, axis):
        """Convert counts to degrees."""
        cpr = self.cpr_az if axis == self.AXIS_AZ else self.cpr_alt
        if not cpr:
            cpr = self.get_counts_per_revolution(axis)
        if not cpr:
            return None
        return (counts / cpr) * 360.0
    
    def degrees_to_counts(self, degrees, axis):
        """Convert degrees to counts."""
        cpr = self.cpr_az if axis == self.AXIS_AZ else self.cpr_alt
        if not cpr:
            cpr = self.get_counts_per_revolution(axis)
        if not cpr:
            return None
        return int((degrees / 360.0) * cpr)
    
    def close(self):
        """Close socket."""
        self.sock.close()


class TelescopeGUI:
    """Professional GUI for telescope controller."""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"SkyWatcher Controller v{VERSION}")
        self.root.geometry("1100x900")
        
        # Database config
        self.db = DatabaseConfig()
        
        # Directories
        script_path = Path(__file__).resolve()
        self.base_dir = script_path.parent
        
        # File logger
        retention = self.db.get_int('logging.retention', 30)
        self.file_logger = FileLogger(self.base_dir, retention=retention)
        self.file_logger.set_debug_mode(self.db.get_bool('logging.debug_mode'))
        self.file_logger.log(f"Application started v{VERSION}", level='INFO')
        
        # Comms buffer for protocol logging
        self.comms_buffer = CommsBuffer(maxlen=10000)
        
        # Protocol
        self.protocol = None
        self.connected = False
        
        # Status monitor
        self.status_monitor = None
        
        # State
        self.axes_moving = {1: False, 2: False}
        self.keys_pressed = set()
        self.estop_active = False
        self.limit_check_job = None  # Job ID for limit checking
        self.update_thread = None
        self.update_running = False
        self.estop_active = False
        self.keys_pressed = set()
        
        # Last valid positions (for filtering corrupted packets)
        self.last_valid_az_deg = None
        self.last_valid_alt_deg = None
        
        # Build GUI
        self.create_widgets()
        self.bind_keyboard_controls()
        self.start_position_updates()
    
    def create_widgets(self):
        """Create all widgets."""
        # Main notebook
        if TTKBOOTSTRAP_AVAILABLE:
            self.notebook = ttk.Notebook(self.root, bootstyle="dark")
        else:
            self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.create_control_tab()
        self.create_comms_tab()
        self.create_diagnostics_tab()
        self.create_settings_tab()
    
    def create_control_tab(self):
        """Create control tab."""
        control_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(control_tab, text="  Control  ")
        
        # Connection frame
        if TTKBOOTSTRAP_AVAILABLE:
            conn_frame = ttk.Labelframe(control_tab, text="Connection", padding=15, bootstyle="info")
        else:
            conn_frame = ttk.LabelFrame(control_tab, text="Connection", padding=15)
        conn_frame.grid(row=0, column=0, columnspan=3, sticky='ew', padx=5, pady=5)
        
        ttk.Label(conn_frame, text="IP:").grid(row=0, column=0, padx=5)
        self.ip_entry = ttk.Entry(conn_frame, width=15)
        self.ip_entry.insert(0, self.db.get('connection.ip'))
        self.ip_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, padx=5)
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
            self.status_label = ttk.Label(conn_frame, text="● Disconnected", 
                                         font=('TkDefaultFont', 10, 'bold'), bootstyle="danger")
        else:
            self.status_label = ttk.Label(conn_frame, text="● Disconnected", foreground="red")
        self.status_label.grid(row=0, column=5, padx=10)
        
        # Motion control frame
        if TTKBOOTSTRAP_AVAILABLE:
            dir_frame = ttk.Labelframe(control_tab, text="Motion Control", padding=15, bootstyle="primary")
        else:
            dir_frame = ttk.LabelFrame(control_tab, text="Motion Control", padding=15)
        dir_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        
        # Center the direction pad grid within dir_frame
        dir_frame.columnconfigure(0, weight=1)
        dir_frame.columnconfigure(1, weight=0)  # Center column (buttons)
        dir_frame.columnconfigure(2, weight=1)

        # Direction buttons
        btn_width = 10
        if TTKBOOTSTRAP_AVAILABLE:
            self.btn_up = ttk.Button(dir_frame, text="▲ UP", width=btn_width, bootstyle="info-outline")
            self.btn_left = ttk.Button(dir_frame, text="◄ LEFT", width=btn_width, bootstyle="info-outline")
            self.btn_stop = ttk.Button(dir_frame, text="■ STOP", width=btn_width,
                                       command=self.stop_all, bootstyle="warning")
            self.btn_right = ttk.Button(dir_frame, text="► RIGHT", width=btn_width, bootstyle="info-outline")
            self.btn_down = ttk.Button(dir_frame, text="▼ DOWN", width=btn_width, bootstyle="info-outline")
        else:
            self.btn_up = ttk.Button(dir_frame, text="▲ UP", width=btn_width)
            self.btn_left = ttk.Button(dir_frame, text="◄ LEFT", width=btn_width)
            self.btn_stop = ttk.Button(dir_frame, text="■ STOP", width=btn_width, command=self.stop_all)
            self.btn_right = ttk.Button(dir_frame, text="► RIGHT", width=btn_width)
            self.btn_down = ttk.Button(dir_frame, text="▼ DOWN", width=btn_width)

        self.btn_up.grid(row=0, column=1, padx=5, pady=5)
        self.btn_left.grid(row=1, column=0, padx=5, pady=5)
        self.btn_stop.grid(row=1, column=1, padx=5, pady=5)
        self.btn_right.grid(row=1, column=2, padx=5, pady=5)
        self.btn_down.grid(row=2, column=1, padx=5, pady=5)
        
        self.setup_button_bindings()
        
        # E-Stop
        if TTKBOOTSTRAP_AVAILABLE:
            self.estop_btn = ttk.Button(dir_frame, text="🛑 EMERGENCY STOP", 
                                        command=self.emergency_stop, bootstyle="danger", width=30)
        else:
            self.estop_btn = ttk.Button(dir_frame, text="🛑 EMERGENCY STOP", command=self.emergency_stop)
        self.estop_btn.grid(row=3, column=0, columnspan=3, sticky='ew', pady=15)
        
        # Speed control
        speed_frame = ttk.Frame(dir_frame)
        speed_frame.grid(row=4, column=0, columnspan=3, pady=10, sticky='ew')
        
        ttk.Label(speed_frame, text="Speed (°/s):").pack(side='left', padx=5)
        self.speed_var = tk.DoubleVar(value=self.db.get_float('speed.default', 1.0))
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.speed_scale = ttk.Scale(speed_frame, from_=0.1, to=10.0,
                                        variable=self.speed_var, bootstyle="info")
        else:
            self.speed_scale = ttk.Scale(speed_frame, from_=0.1, to=10.0, variable=self.speed_var)
        self.speed_scale.pack(side='left', fill='x', expand=True, padx=5)
        
        self.speed_label = ttk.Label(speed_frame, text=f"{self.speed_var.get():.2f}", width=6)
        self.speed_label.pack(side='left', padx=5)
        self.speed_var.trace_add('write', self.update_speed_label)
        
        # Mode indicator
        control_mode = self.db.get('controls.mode', 'latching')
        ttk.Label(dir_frame, text=f"Mode: {control_mode.title()} | W/A/S/D, Space=Stop, Esc=E-Stop",
                 font=('TkDefaultFont', 9)).grid(row=5, column=0, columnspan=3, pady=5)
        
        # Axis status
        if TTKBOOTSTRAP_AVAILABLE:
            status_frame = ttk.Labelframe(dir_frame, text="Axis Status", bootstyle="secondary")
        else:
            status_frame = ttk.LabelFrame(dir_frame, text="Axis Status")
        status_frame.grid(row=6, column=0, columnspan=3, sticky='ew', pady=10)
        
        ttk.Label(status_frame, text="Azimuth:").grid(row=0, column=0, padx=10, pady=3, sticky='e')
        self.az_status_indicator = ttk.Label(status_frame, text="● Unknown")
        self.az_status_indicator.grid(row=0, column=1, padx=5, sticky='w')
        self.az_status_raw = ttk.Label(status_frame, text="", font=('Consolas', 9))
        self.az_status_raw.grid(row=0, column=2, padx=5, sticky='w')
        
        ttk.Label(status_frame, text="Altitude:").grid(row=1, column=0, padx=10, pady=3, sticky='e')
        self.alt_status_indicator = ttk.Label(status_frame, text="● Unknown")
        self.alt_status_indicator.grid(row=1, column=1, padx=5, sticky='w')
        self.alt_status_raw = ttk.Label(status_frame, text="", font=('Consolas', 9))
        self.alt_status_raw.grid(row=1, column=2, padx=5, sticky='w')
        
        # Presets frame
        if TTKBOOTSTRAP_AVAILABLE:
            preset_frame = ttk.Labelframe(control_tab, text="Presets", padding=15, bootstyle="success")
        else:
            preset_frame = ttk.LabelFrame(control_tab, text="Presets", padding=15)
        preset_frame.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)

        # Create preset buttons with tooltips
        self.home_tooltip = None
        self.stow_tooltip = None

        if TTKBOOTSTRAP_AVAILABLE:
            self.btn_goto_home = ttk.Button(preset_frame, text="Go to Home", command=self.goto_home,
                                            width=18, bootstyle="success-outline")
        else:
            self.btn_goto_home = ttk.Button(preset_frame, text="Go to Home", command=self.goto_home, width=18)
        self.btn_goto_home.pack(pady=5)
        self.home_tooltip = ToolTip(self.btn_goto_home, "Loading...")

        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(preset_frame, text="Set as Home", command=self.set_home,
                      width=18, bootstyle="success-outline").pack(pady=5)
        else:
            ttk.Button(preset_frame, text="Set as Home", command=self.set_home, width=18).pack(pady=5)

        if TTKBOOTSTRAP_AVAILABLE:
            self.btn_goto_stow = ttk.Button(preset_frame, text="Go to Stow", command=self.goto_stow,
                                            width=18, bootstyle="success-outline")
        else:
            self.btn_goto_stow = ttk.Button(preset_frame, text="Go to Stow", command=self.goto_stow, width=18)
        self.btn_goto_stow.pack(pady=5)
        self.stow_tooltip = ToolTip(self.btn_goto_stow, "Loading...")

        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(preset_frame, text="Set as Stow", command=self.set_stow,
                      width=18, bootstyle="success-outline").pack(pady=5)
        else:
            ttk.Button(preset_frame, text="Set as Stow", command=self.set_stow, width=18).pack(pady=5)
        
        ttk.Separator(preset_frame, orient='horizontal').pack(fill='x', pady=15)
        
        for text, cmd in [("Zero Position", self.zero_position), ("Re-initialize", self.reinitialize)]:
            if TTKBOOTSTRAP_AVAILABLE:
                ttk.Button(preset_frame, text=text, command=cmd, width=18, 
                          bootstyle="secondary-outline").pack(pady=5)
            else:
                ttk.Button(preset_frame, text=text, command=cmd, width=18).pack(pady=5)
        
        # Position frame
        if TTKBOOTSTRAP_AVAILABLE:
            pos_frame = ttk.Labelframe(control_tab, text="Position", padding=15, bootstyle="warning")
        else:
            pos_frame = ttk.LabelFrame(control_tab, text="Position", padding=15)
        pos_frame.grid(row=1, column=2, sticky='nsew', padx=5, pady=5)
        
        self.show_pos_var = tk.BooleanVar(value=self.db.get_bool('display.show_positions', True))
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Checkbutton(pos_frame, text="Show Positions", variable=self.show_pos_var,
                           command=self.toggle_position_display, bootstyle="warning-round-toggle").pack(anchor='w')
        else:
            ttk.Checkbutton(pos_frame, text="Show Positions", variable=self.show_pos_var,
                           command=self.toggle_position_display).pack(anchor='w')
        
        ttk.Label(pos_frame, text="Format:").pack(anchor='w', pady=(10, 5))
        self.pos_format_var = tk.StringVar(value=self.db.get('display.position_format', 'both'))
        
        for text, value in [('Degrees', 'degrees'), ('Raw', 'raw'), ('Both', 'both'), ('Coords', 'coordinates')]:
            ttk.Radiobutton(pos_frame, text=text, variable=self.pos_format_var,
                          value=value, command=self.update_position_format).pack(anchor='w')
        
        self.pos_display_frame = ttk.Frame(pos_frame)
        self.pos_display_frame.pack(fill='both', expand=True, pady=10)
        self.create_position_labels()
        
        # Grid weights
        control_tab.columnconfigure(0, weight=1)
        control_tab.columnconfigure(1, weight=1)
        control_tab.columnconfigure(2, weight=1)
        control_tab.rowconfigure(1, weight=1)
        
        # Collapsible activity log
        self.log_expanded = tk.BooleanVar(value=self.db.get_bool('display.log_expanded', True))
        
        log_header = ttk.Frame(control_tab)
        log_header.grid(row=2, column=0, columnspan=3, sticky='ew', padx=5, pady=(10, 0))
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.log_toggle_btn = ttk.Button(log_header, text="▼ Activity Log", 
                                            command=self.toggle_log_expanded, bootstyle="dark-outline")
        else:
            self.log_toggle_btn = ttk.Button(log_header, text="▼ Activity Log", 
                                            command=self.toggle_log_expanded)
        self.log_toggle_btn.pack(side='left')
        
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(log_header, text="Clear", command=self.clear_activity_log,
                      bootstyle="secondary-outline").pack(side='right')
        else:
            ttk.Button(log_header, text="Clear", command=self.clear_activity_log).pack(side='right')
        
        self.log_frame = ttk.Frame(control_tab)
        self.log_frame.grid(row=3, column=0, columnspan=3, sticky='ew', padx=5, pady=(0, 5))
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.log_text = ScrolledText(self.log_frame, height=4, autohide=True, state='disabled')
        else:
            self.log_text = TkScrolledText(self.log_frame, height=4, font=('Consolas', 9), state='disabled')
        self.log_text.pack(fill='both', expand=True)
        
        if not self.log_expanded.get():
            self.log_frame.grid_remove()
            self.log_toggle_btn.configure(text="► Activity Log")
    
    def create_comms_tab(self):
        """Create communications log tab with search/filter."""
        comms_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(comms_tab, text="  Comms Log  ")
        
        # Controls
        control_frame = ttk.Frame(comms_tab)
        control_frame.pack(fill='x', pady=(0, 10))
        
        # Enable/disable
        self.show_protocol_var = tk.BooleanVar(value=self.db.get_bool('logging.show_protocol'))
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Checkbutton(control_frame, text="Enable Protocol Logging", 
                           variable=self.show_protocol_var, command=self.toggle_protocol_logging,
                           bootstyle="info-round-toggle").pack(side='left', padx=5)
        else:
            ttk.Checkbutton(control_frame, text="Enable Protocol Logging", 
                           variable=self.show_protocol_var, command=self.toggle_protocol_logging).pack(side='left', padx=5)
        
        ttk.Separator(control_frame, orient='vertical').pack(side='left', fill='y', padx=10)
        
        # Search
        ttk.Label(control_frame, text="Search:").pack(side='left', padx=5)
        self.comms_search_var = tk.StringVar()
        self.comms_search_entry = ttk.Entry(control_frame, textvariable=self.comms_search_var, width=30)
        self.comms_search_entry.pack(side='left', padx=5)
        
        self.comms_regex_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame, text="Regex", variable=self.comms_regex_var).pack(side='left', padx=5)
        
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(control_frame, text="Search", command=self.search_comms,
                      bootstyle="info-outline").pack(side='left', padx=5)
            ttk.Button(control_frame, text="Clear Filter", command=self.clear_comms_filter,
                      bootstyle="secondary-outline").pack(side='left', padx=5)
            ttk.Button(control_frame, text="Clear Log", command=self.clear_comms_log,
                      bootstyle="warning-outline").pack(side='right', padx=5)
        else:
            ttk.Button(control_frame, text="Search", command=self.search_comms).pack(side='left', padx=5)
            ttk.Button(control_frame, text="Clear Filter", command=self.clear_comms_filter).pack(side='left', padx=5)
            ttk.Button(control_frame, text="Clear Log", command=self.clear_comms_log).pack(side='right', padx=5)
        
        # Stats
        self.comms_stats_label = ttk.Label(comms_tab, text="Entries: 0")
        self.comms_stats_label.pack(anchor='w', pady=5)
        
        # Log display
        if TTKBOOTSTRAP_AVAILABLE:
            self.comms_text = ScrolledText(comms_tab, height=35, autohide=True)
        else:
            self.comms_text = TkScrolledText(comms_tab, height=35, font=('Consolas', 9), state='disabled')
        self.comms_text.pack(fill='both', expand=True)
        
        # Auto-scroll toggle
        self.comms_autoscroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(comms_tab, text="Auto-scroll", variable=self.comms_autoscroll_var).pack(anchor='w', pady=5)
        
        # Register callback for live updates
        if self.show_protocol_var.get():
            self.comms_buffer.register_callback(self.on_comms_entry)
    
    def create_diagnostics_tab(self):
        """Create diagnostics tab."""
        diag_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(diag_tab, text="  Diagnostics  ")
        
        control_frame = ttk.Frame(diag_tab)
        control_frame.pack(fill='x', pady=(0, 10))
        
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
                   textvariable=self.update_rate_var, width=5).pack(side='left')
        ttk.Label(control_frame, text="Hz").pack(side='left', padx=5)
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.diag_text = ScrolledText(diag_tab, height=30, autohide=True)
        else:
            self.diag_text = TkScrolledText(diag_tab, height=30, font=('Consolas', 10), state='disabled')
        self.diag_text.pack(fill='both', expand=True)
    
    def create_settings_tab(self):
        """Create settings tab."""
        settings_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(settings_tab, text="  Settings  ")
        
        if TTKBOOTSTRAP_AVAILABLE:
            settings_notebook = ttk.Notebook(settings_tab, bootstyle="secondary")
        else:
            settings_notebook = ttk.Notebook(settings_tab)
        settings_notebook.pack(fill='both', expand=True)
        
        self.create_controls_settings(settings_notebook)
        self.create_theme_settings(settings_notebook)
        self.create_connection_settings(settings_notebook)
        self.create_logging_settings(settings_notebook)
    
    def create_controls_settings(self, parent):
        """Create controls settings."""
        frame = ttk.Frame(parent, padding=15)
        parent.add(frame, text="  Controls  ")
        
        # Control mode
        if TTKBOOTSTRAP_AVAILABLE:
            mode_frame = ttk.Labelframe(frame, text="Control Mode", padding=10, bootstyle="info")
        else:
            mode_frame = ttk.LabelFrame(frame, text="Control Mode", padding=10)
        mode_frame.pack(fill='x', pady=10)
        
        self.control_mode_var = tk.StringVar(value=self.db.get('controls.mode', 'latching'))
        for text, value in [("Latching - Click to start, click Stop to stop", 'latching'),
                           ("Momentary - Hold to move, release to stop", 'momentary')]:
            ttk.Radiobutton(mode_frame, text=text, variable=self.control_mode_var, value=value).pack(anchor='w', pady=3)
        
        # Altitude limits
        if TTKBOOTSTRAP_AVAILABLE:
            limits_frame = ttk.Labelframe(frame, text="Altitude Limits", padding=10, bootstyle="warning")
        else:
            limits_frame = ttk.LabelFrame(frame, text="Altitude Limits", padding=10)
        limits_frame.pack(fill='x', pady=10)
        
        self.enforce_limits_var = tk.BooleanVar(value=self.db.get_bool('limits.enforce', True))
        ttk.Checkbutton(limits_frame, text="Enforce altitude limits", variable=self.enforce_limits_var).pack(anchor='w')
        
        min_frame = ttk.Frame(limits_frame)
        min_frame.pack(fill='x', pady=5)
        ttk.Label(min_frame, text="Minimum:").pack(side='left')
        self.alt_min_var = tk.DoubleVar(value=self.db.get_float('limits.alt_min', -5.0))
        ttk.Scale(min_frame, from_=-30, to=30, variable=self.alt_min_var).pack(side='left', fill='x', expand=True, padx=5)
        self.alt_min_label = ttk.Label(min_frame, text=f"{self.alt_min_var.get():.1f}°", width=6)
        self.alt_min_label.pack(side='left')
        self.alt_min_var.trace_add('write', lambda *a: self.alt_min_label.configure(text=f"{self.alt_min_var.get():.1f}°"))
        
        max_frame = ttk.Frame(limits_frame)
        max_frame.pack(fill='x', pady=5)
        ttk.Label(max_frame, text="Maximum:").pack(side='left')
        self.alt_max_var = tk.DoubleVar(value=self.db.get_float('limits.alt_max', 90.0))
        ttk.Scale(max_frame, from_=60, to=120, variable=self.alt_max_var).pack(side='left', fill='x', expand=True, padx=5)
        self.alt_max_label = ttk.Label(max_frame, text=f"{self.alt_max_var.get():.1f}°", width=6)
        self.alt_max_label.pack(side='left')
        self.alt_max_var.trace_add('write', lambda *a: self.alt_max_label.configure(text=f"{self.alt_max_var.get():.1f}°"))
        
        # Key bindings
        if TTKBOOTSTRAP_AVAILABLE:
            kb_frame = ttk.Labelframe(frame, text="Key Bindings", padding=10, bootstyle="secondary")
        else:
            kb_frame = ttk.LabelFrame(frame, text="Key Bindings", padding=10)
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
        
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(frame, text="Save Control Settings", command=self.save_control_settings,
                      bootstyle="success").pack(pady=15)
        else:
            ttk.Button(frame, text="Save Control Settings", command=self.save_control_settings).pack(pady=15)
    
    def create_theme_settings(self, parent):
        """Create theme settings."""
        frame = ttk.Frame(parent, padding=15)
        parent.add(frame, text="  Theme  ")
        
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Label(frame, text="Select Theme", font=('TkDefaultFont', 12, 'bold')).pack(pady=10)
            
            self.theme_var = tk.StringVar(value=self.db.get('theme.name', DEFAULT_THEME))
            
            theme_frame = ttk.Frame(frame)
            theme_frame.pack(pady=10)
            
            ttk.Label(theme_frame, text="Theme:").pack(side='left', padx=5)
            ttk.Combobox(theme_frame, textvariable=self.theme_var, 
                        values=AVAILABLE_THEMES, state='readonly', width=20).pack(side='left', padx=5)
            ttk.Button(theme_frame, text="Apply", command=self.apply_theme_selection,
                      bootstyle="success").pack(side='left', padx=10)
            
            ttk.Label(frame, text="Dark: darkly, cyborg, vapor, solar, superhero").pack(anchor='w', pady=5)
            ttk.Label(frame, text="Light: flatly, journal, litera, minty, yeti, cosmo").pack(anchor='w', pady=5)
        else:
            ttk.Label(frame, text="Theme settings require ttkbootstrap").pack(pady=20)
            ttk.Label(frame, text="Install: pip install ttkbootstrap").pack()
    
    def create_connection_settings(self, parent):
        """Create connection settings."""
        frame = ttk.Frame(parent, padding=15)
        parent.add(frame, text="  Connection  ")
        
        ttk.Label(frame, text="Default Connection", font=('TkDefaultFont', 12, 'bold')).pack(pady=10)
        
        grid = ttk.Frame(frame)
        grid.pack(pady=10)
        
        ttk.Label(grid, text="IP:").grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.default_ip_entry = ttk.Entry(grid, width=20)
        self.default_ip_entry.insert(0, self.db.get('connection.ip'))
        self.default_ip_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(grid, text="Port:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.default_port_entry = ttk.Entry(grid, width=20)
        self.default_port_entry.insert(0, self.db.get('connection.port'))
        self.default_port_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(grid, text="Timeout:").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.timeout_entry = ttk.Entry(grid, width=20)
        self.timeout_entry.insert(0, self.db.get('connection.timeout'))
        self.timeout_entry.grid(row=2, column=1, padx=5, pady=5)
        
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(frame, text="Save", command=self.save_connection_settings,
                      bootstyle="success").pack(pady=15)
        else:
            ttk.Button(frame, text="Save", command=self.save_connection_settings).pack(pady=15)
    
    def create_logging_settings(self, parent):
        """Create logging settings."""
        frame = ttk.Frame(parent, padding=15)
        parent.add(frame, text="  Logging  ")
        
        ttk.Label(frame, text="Logging Configuration", font=('TkDefaultFont', 12, 'bold')).pack(pady=10)
        
        # Debug mode
        self.debug_mode_var = tk.BooleanVar(value=self.db.get_bool('logging.debug_mode'))
        ttk.Checkbutton(frame, text="Debug Mode (detailed file logging)", 
                       variable=self.debug_mode_var, command=self.toggle_debug_mode).pack(anchor='w', padx=20, pady=5)
        
        # Retention
        if TTKBOOTSTRAP_AVAILABLE:
            ret_frame = ttk.Labelframe(frame, text="Log Retention", padding=10, bootstyle="secondary")
        else:
            ret_frame = ttk.LabelFrame(frame, text="Log Retention", padding=10)
        ret_frame.pack(fill='x', padx=20, pady=15)
        
        ret_ctrl = ttk.Frame(ret_frame)
        ret_ctrl.pack(fill='x', pady=5)
        
        ttk.Label(ret_ctrl, text="Keep last").pack(side='left', padx=5)
        self.retention_var = tk.IntVar(value=self.db.get_int('logging.retention', 30))
        ttk.Spinbox(ret_ctrl, from_=0, to=500, textvariable=self.retention_var, width=5).pack(side='left', padx=5)
        ttk.Label(ret_ctrl, text="log files").pack(side='left', padx=5)
        
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(ret_ctrl, text="Apply", command=self.apply_retention,
                      bootstyle="info-outline").pack(side='left', padx=10)
        else:
            ttk.Button(ret_ctrl, text="Apply", command=self.apply_retention).pack(side='left', padx=10)
        
        ttk.Label(ret_frame, text="Set to 0 to disable file logging.", font=('TkDefaultFont', 9)).pack(anchor='w')
        
        # Location
        ttk.Separator(frame, orient='horizontal').pack(fill='x', padx=20, pady=15)
        
        ttk.Label(frame, text="Log folder:").pack(anchor='w', padx=20)
        ttk.Label(frame, text=str(self.file_logger.log_dir), font=('Consolas', 9)).pack(anchor='w', padx=40, pady=5)
        
        if TTKBOOTSTRAP_AVAILABLE:
            ttk.Button(frame, text="Open Folder", command=self.open_log_folder,
                      bootstyle="secondary-outline").pack(anchor='w', padx=20, pady=10)
        else:
            ttk.Button(frame, text="Open Folder", command=self.open_log_folder).pack(anchor='w', padx=20, pady=10)
    
    # -------------------- Button Bindings --------------------
    
    def setup_button_bindings(self):
        """Setup button bindings based on mode."""
        mode = self.db.get('controls.mode', 'latching')
        
        if mode == 'momentary':
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
    
    def bind_keyboard_controls(self):
        """Bind keyboard controls."""
        mode = self.db.get('controls.mode', 'latching')
        keys = {k: self.db.get(f'controls.{k}', v) for k, v in 
                [('up', 'w'), ('down', 's'), ('left', 'a'), ('right', 'd'), ('stop', 'space'), ('estop', 'Escape')]}
        
        if mode == 'momentary':
            for direction in ['up', 'down', 'left', 'right']:
                self.root.bind(f"<KeyPress-{keys[direction]}>", lambda e, d=direction: self.key_move(d))
                self.root.bind(f"<KeyRelease-{keys[direction]}>", lambda e, d=direction: self.key_release(d))
            
            for key, direction in [('Up', 'up'), ('Down', 'down'), ('Left', 'left'), ('Right', 'right')]:
                self.root.bind(f"<KeyPress-{key}>", lambda e, d=direction: self.key_move(d))
                self.root.bind(f"<KeyRelease-{key}>", lambda e, d=direction: self.key_release(d))
        else:
            for direction in ['up', 'down', 'left', 'right']:
                self.root.bind(f"<KeyPress-{keys[direction]}>", lambda e, d=direction: self.move(d))
            
            self.root.bind("<Up>", lambda e: self.move('up'))
            self.root.bind("<Down>", lambda e: self.move('down'))
            self.root.bind("<Left>", lambda e: self.move('left'))
            self.root.bind("<Right>", lambda e: self.move('right'))
        
        self.root.bind(f"<KeyPress-{keys['stop']}>", lambda e: self.stop_all())
        self.root.bind(f"<KeyPress-{keys['estop']}>", lambda e: self.emergency_stop())
    
    def key_move(self, direction):
        if direction not in self.keys_pressed:
            self.keys_pressed.add(direction)
            self.move(direction)
    
    def key_release(self, direction):
        if direction in self.keys_pressed:
            self.keys_pressed.discard(direction)
            self.stop_axis(2 if direction in ('up', 'down') else 1)
    
    # -------------------- Position Display --------------------
    
    def create_position_labels(self):
        """Create position labels."""
        for w in self.pos_display_frame.winfo_children():
            w.destroy()
        
        if not self.show_pos_var.get():
            return
        
        fmt = self.pos_format_var.get()
        font = ('Consolas', 11)
        
        if fmt == 'degrees':
            ttk.Label(self.pos_display_frame, text="Az:").grid(row=0, column=0, sticky='e', pady=3)
            self.az_deg_label = ttk.Label(self.pos_display_frame, text="---°", font=font)
            self.az_deg_label.grid(row=0, column=1, sticky='w', padx=5)
            ttk.Label(self.pos_display_frame, text="Alt:").grid(row=1, column=0, sticky='e', pady=3)
            self.alt_deg_label = ttk.Label(self.pos_display_frame, text="---°", font=font)
            self.alt_deg_label.grid(row=1, column=1, sticky='w', padx=5)
        elif fmt == 'raw':
            ttk.Label(self.pos_display_frame, text="Az:").grid(row=0, column=0, sticky='e', pady=3)
            self.az_raw_label = ttk.Label(self.pos_display_frame, text="---", font=font)
            self.az_raw_label.grid(row=0, column=1, sticky='w', padx=5)
            ttk.Label(self.pos_display_frame, text="Alt:").grid(row=1, column=0, sticky='e', pady=3)
            self.alt_raw_label = ttk.Label(self.pos_display_frame, text="---", font=font)
            self.alt_raw_label.grid(row=1, column=1, sticky='w', padx=5)
        elif fmt == 'both':
            ttk.Label(self.pos_display_frame, text="Az:").grid(row=0, column=0, sticky='e', pady=3)
            self.az_both_label = ttk.Label(self.pos_display_frame, text="---", font=font)
            self.az_both_label.grid(row=0, column=1, sticky='w', padx=5)
            ttk.Label(self.pos_display_frame, text="Alt:").grid(row=1, column=0, sticky='e', pady=3)
            self.alt_both_label = ttk.Label(self.pos_display_frame, text="---", font=font)
            self.alt_both_label.grid(row=1, column=1, sticky='w', padx=5)
        elif fmt == 'coordinates':
            self.coord_label = ttk.Label(self.pos_display_frame, text="---", font=font, justify='left')
            self.coord_label.pack(pady=10)
    
    def is_position_sane(self, deg: float, is_altitude: bool = False) -> bool:
        """Check if position value is sane (not corrupted)."""
        if deg is None:
            return False
        if is_altitude:
            return ALTITUDE_SANITY_MIN_DEG <= deg <= ALTITUDE_SANITY_MAX_DEG
        else:
            return POSITION_SANITY_MIN_DEG <= deg <= POSITION_SANITY_MAX_DEG
    
    def start_position_updates(self):
        """Start position update timer."""
        self.update_position_display()
        self.root.after(1000, self.start_position_updates)
    
    def update_position_display(self):
        """Update position display with sanity checking."""
        if not self.connected or not self.show_pos_var.get():
            return
        
        try:
            az_pos = self.protocol.get_position(self.protocol.AXIS_AZ, log_to_ui=False)
            alt_pos = self.protocol.get_position(self.protocol.AXIS_ALT, log_to_ui=False)
            
            if az_pos is None or alt_pos is None:
                return
            
            az_deg = self.protocol.counts_to_degrees(az_pos, self.protocol.AXIS_AZ)
            alt_deg = self.protocol.counts_to_degrees(alt_pos, self.protocol.AXIS_ALT)
            
            # Sanity check - filter corrupted packets
            if az_deg is not None and self.is_position_sane(az_deg, False):
                self.last_valid_az_deg = az_deg
            else:
                az_deg = self.last_valid_az_deg
                if az_deg is None:
                    return
            
            if alt_deg is not None and self.is_position_sane(alt_deg, True):
                self.last_valid_alt_deg = alt_deg
            else:
                alt_deg = self.last_valid_alt_deg
                if alt_deg is None:
                    return
            
            # Update display
            fmt = self.pos_format_var.get()
            
            if fmt == 'degrees':
                if hasattr(self, 'az_deg_label'):
                    self.az_deg_label.configure(text=f"{az_deg:.4f}°")
                if hasattr(self, 'alt_deg_label'):
                    self.alt_deg_label.configure(text=f"{alt_deg:.4f}°")
            elif fmt == 'raw':
                if hasattr(self, 'az_raw_label'):
                    self.az_raw_label.configure(text=f"{az_pos:,}")
                if hasattr(self, 'alt_raw_label'):
                    self.alt_raw_label.configure(text=f"{alt_pos:,}")
            elif fmt == 'both':
                if hasattr(self, 'az_both_label'):
                    self.az_both_label.configure(text=f"{az_deg:.2f}° ({az_pos:,})")
                if hasattr(self, 'alt_both_label'):
                    self.alt_both_label.configure(text=f"{alt_deg:.2f}° ({alt_pos:,})")
            elif fmt == 'coordinates':
                if hasattr(self, 'coord_label'):
                    self.coord_label.configure(text=f"Az: {az_deg % 360:.4f}°\nAlt: {alt_deg:.4f}°")

            # Update preset button tooltips with current position
            self.update_preset_tooltips()
        except Exception:
            pass
    
    # -------------------- Logging --------------------
    
    def log(self, message, level='INFO'):
        """Log to activity log (user events only)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"

        # Temporarily enable editing to insert log entry, then disable
        self.log_text.configure(state='normal')
        self.log_text.insert('end', entry + "\n")
        self.log_text.see('end')
        self.log_text.configure(state='disabled')

        self.file_logger.log(message, level=level)
    
    def toggle_log_expanded(self):
        """Toggle activity log expansion."""
        if self.log_expanded.get():
            self.log_frame.grid_remove()
            self.log_toggle_btn.configure(text="► Activity Log")
            self.log_expanded.set(False)
        else:
            self.log_frame.grid()
            self.log_toggle_btn.configure(text="▼ Activity Log")
            self.log_expanded.set(True)
        self.db.set('display.log_expanded', str(self.log_expanded.get()))
    
    def clear_activity_log(self):
        """Clear activity log."""
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.configure(state='disabled')
    
    # -------------------- Comms Log --------------------
    
    def toggle_protocol_logging(self):
        """Toggle protocol logging to comms tab."""
        enabled = self.show_protocol_var.get()
        self.db.set('logging.show_protocol', str(enabled))
        
        if enabled:
            self.comms_buffer.register_callback(self.on_comms_entry)
        else:
            self.comms_buffer.unregister_callback(self.on_comms_entry)
    
    def on_comms_entry(self, entry):
        """Handle new comms entry."""
        if not self.show_protocol_var.get():
            return
        
        def update():
            if TTKBOOTSTRAP_AVAILABLE:
                self.comms_text.insert('end', entry + "\n")
                if self.comms_autoscroll_var.get():
                    self.comms_text.see('end')
            else:
                self.comms_text.configure(state='normal')
                self.comms_text.insert('end', entry + "\n")
                if self.comms_autoscroll_var.get():
                    self.comms_text.see('end')
                self.comms_text.configure(state='disabled')
            
            self.comms_stats_label.configure(text=f"Entries: {len(self.comms_buffer.buffer)}")
        
        self.root.after(0, update)
    
    def search_comms(self):
        """Search comms log."""
        pattern = self.comms_search_var.get()
        use_regex = self.comms_regex_var.get()
        
        results = self.comms_buffer.search(pattern, regex=use_regex)
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.comms_text.delete('1.0', 'end')
            self.comms_text.insert('1.0', '\n'.join(results))
        else:
            self.comms_text.configure(state='normal')
            self.comms_text.delete('1.0', 'end')
            self.comms_text.insert('1.0', '\n'.join(results))
            self.comms_text.configure(state='disabled')
        
        self.comms_stats_label.configure(text=f"Results: {len(results)} / {len(self.comms_buffer.buffer)}")
    
    def clear_comms_filter(self):
        """Clear comms filter and show all."""
        self.comms_search_var.set('')
        entries = self.comms_buffer.get_all()
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.comms_text.delete('1.0', 'end')
            self.comms_text.insert('1.0', '\n'.join(entries))
        else:
            self.comms_text.configure(state='normal')
            self.comms_text.delete('1.0', 'end')
            self.comms_text.insert('1.0', '\n'.join(entries))
            self.comms_text.configure(state='disabled')
        
        self.comms_stats_label.configure(text=f"Entries: {len(entries)}")
    
    def clear_comms_log(self):
        """Clear comms log."""
        self.comms_buffer.clear()
        if TTKBOOTSTRAP_AVAILABLE:
            self.comms_text.delete('1.0', 'end')
        else:
            self.comms_text.configure(state='normal')
            self.comms_text.delete('1.0', 'end')
            self.comms_text.configure(state='disabled')
        self.comms_stats_label.configure(text="Entries: 0")
    
    # -------------------- Connection --------------------
    
    def toggle_connection(self):
        """Connect or disconnect."""
        if self.connected:
            if self.status_monitor:
                self.status_monitor.stop()
                self.status_monitor = None
            
            self.stop_all()
            if self.protocol:
                self.protocol.close()
            self.protocol = None
            self.connected = False

            # Re-enable IP/Port fields when disconnected
            self.ip_entry.configure(state='normal')
            self.port_entry.configure(state='normal')

            if TTKBOOTSTRAP_AVAILABLE:
                self.connect_btn.configure(text="Connect", bootstyle="success")
                self.status_label.configure(text="● Disconnected", bootstyle="danger")
            else:
                self.connect_btn.configure(text="Connect")
                self.status_label.configure(text="● Disconnected", foreground="red")

            self.log("Disconnected")
        else:
            ip = self.ip_entry.get()
            port = int(self.port_entry.get())
            timeout = self.db.get_float('connection.timeout', 2.0)
            
            self.log(f"Connecting to {ip}:{port}...")
            self.protocol = SkyWatcherProtocol(ip, port, timeout, 
                                               file_logger=self.file_logger,
                                               comms_buffer=self.comms_buffer)
            
            try:
                version = self.protocol.get_motor_board_version('1')
                if version:
                    self.connected = True

                    # Disable IP/Port fields during connection
                    self.ip_entry.configure(state='disabled')
                    self.port_entry.configure(state='disabled')

                    if TTKBOOTSTRAP_AVAILABLE:
                        self.connect_btn.configure(text="Disconnect", bootstyle="danger")
                        self.status_label.configure(text="● Connected", bootstyle="success")
                    else:
                        self.connect_btn.configure(text="Disconnect")
                        self.status_label.configure(text="● Connected", foreground="green")

                    self.log(f"✓ Connected - Version: {version}")
                    
                    self.protocol.send_command(":F1")
                    self.protocol.send_command(":F2")
                    self.log("✓ Axes initialized")
                    
                    self.protocol.get_counts_per_revolution(self.protocol.AXIS_AZ)
                    self.protocol.get_counts_per_revolution(self.protocol.AXIS_ALT)
                    self.protocol.get_timer_freq()
                    
                    self.status_monitor = StatusMonitor(self.protocol, self.file_logger, self.on_status_update)
                    self.status_monitor.start()
                    
                    self.log("✓ Ready!")
                else:
                    self.log("✗ Failed to connect")
                    messagebox.showerror("Error", "Could not connect")
                    self.protocol.close()
                    self.protocol = None
            except Exception as e:
                self.log(f"✗ Error: {e}")
                messagebox.showerror("Error", str(e))
                if self.protocol:
                    self.protocol.close()
                self.protocol = None
    
    # -------------------- Motion Control --------------------
    
    def check_altitude_limits(self, direction):
        """Check if movement would violate limits."""
        if not self.db.get_bool('limits.enforce', True):
            return True
        
        if self.last_valid_alt_deg is None:
            return True
        
        alt_min = self.db.get_float('limits.alt_min', -5.0)
        alt_max = self.db.get_float('limits.alt_max', 90.0)
        
        if direction == 'up' and self.last_valid_alt_deg >= alt_max:
            self.log(f"⚠ Altitude limit ({alt_max}°)")
            return False
        elif direction == 'down' and self.last_valid_alt_deg <= alt_min:
            self.log(f"⚠ Altitude limit ({alt_min}°)")
            return False
        
        return True

    def start_limit_checking(self):
        """Start periodic limit checking for momentary mode."""
        if self.limit_check_job:
            self.root.after_cancel(self.limit_check_job)
        self.limit_check_job = self.root.after(100, self.check_limits_during_motion)

    def check_limits_during_motion(self):
        """Continuously check limits during motion in momentary mode."""
        if not self.connected or not self.db.get_bool('limits.enforce', True):
            self.limit_check_job = None
            return

        # Check if altitude axis is moving
        if self.axes_moving.get(2, False):
            if self.last_valid_alt_deg is not None:
                alt_min = self.db.get_float('limits.alt_min', -5.0)
                alt_max = self.db.get_float('limits.alt_max', 90.0)

                # Stop if limits exceeded
                if self.last_valid_alt_deg >= alt_max or self.last_valid_alt_deg <= alt_min:
                    self.stop_axis(2)
                    self.log(f"⚠ Motion stopped at altitude limit")

        # Continue checking if any axis is still moving
        if any(self.axes_moving.values()):
            self.limit_check_job = self.root.after(100, self.check_limits_during_motion)
        else:
            self.limit_check_job = None

    def move(self, direction):
        """Start moving."""
        if not self.connected or self.estop_active:
            return

        if direction in ('up', 'down') and not self.check_altitude_limits(direction):
            return

        speed = self.speed_var.get()
        self.log(f"Move {direction} @ {speed:.1f}°/s")

        axis_map = {'up': (2, True), 'down': (2, False), 'left': (1, False), 'right': (1, True)}
        axis, positive = axis_map[direction]

        self.axes_moving[axis] = True
        self.protocol.slew_fixed_rate(str(axis), positive, speed)

        # Start continuous limit checking in momentary mode
        if self.db.get('controls.mode', 'latching') == 'momentary':
            self.start_limit_checking()
    
    def stop_axis(self, axis):
        """Stop single axis."""
        if self.connected:
            self.protocol.stop_motion(str(axis))
            self.axes_moving[axis] = False
    
    def stop_all(self):
        """Stop all motion."""
        if not self.connected:
            return

        self.log("STOP")
        self.protocol.stop_motion('1')
        self.protocol.stop_motion('2')
        self.axes_moving = {1: False, 2: False}
        self.keys_pressed.clear()
        self.estop_active = False

        # Cancel limit checking
        if self.limit_check_job:
            self.root.after_cancel(self.limit_check_job)
            self.limit_check_job = None

        if TTKBOOTSTRAP_AVAILABLE:
            self.estop_btn.configure(text="🛑 EMERGENCY STOP", bootstyle="danger")
    
    def emergency_stop(self):
        """Emergency stop."""
        if not self.connected:
            return
        
        self.estop_active = True
        self.axes_moving = {1: False, 2: False}
        self.keys_pressed.clear()
        self.protocol.instant_stop('1')
        self.protocol.instant_stop('2')
        
        if TTKBOOTSTRAP_AVAILABLE:
            self.estop_btn.configure(text="⚠️ E-STOP ACTIVE", bootstyle="warning")
        
        self.log("⚠️ EMERGENCY STOP")
        messagebox.showwarning("E-Stop", "Emergency stop activated!")
    
    def on_status_update(self, axis, status):
        """Handle status update from monitor."""
        self.root.after(0, lambda: self._update_status_display(axis, status))
    
    def _update_status_display(self, axis, status):
        """Update status display."""
        raw = status.get('raw', 0)
        running = status.get('running', False)
        blocked = status.get('blocked', False)
        
        if blocked:
            text, color = "⚠ BLOCKED", "red"
        elif running:
            text, color = "● Moving", "blue"
        else:
            text, color = "● Stopped", "gray"
        
        raw_text = StatusDecoder.to_string(raw)
        
        if axis == 1:
            self.az_status_indicator.configure(text=text, foreground=color)
            self.az_status_raw.configure(text=raw_text)
        else:
            self.alt_status_indicator.configure(text=text, foreground=color)
            self.alt_status_raw.configure(text=raw_text)
    
    # -------------------- Presets --------------------

    def update_preset_tooltips(self):
        """Update tooltips for preset buttons with target positions."""
        if not self.connected or not self.protocol:
            return

        try:
            # Get current position
            current_az = self.protocol.get_position('1')
            current_alt = self.protocol.get_position('2')

            if current_az is not None and current_alt is not None:
                current_az_deg = self.protocol.counts_to_degrees(current_az, '1')
                current_alt_deg = self.protocol.counts_to_degrees(current_alt, '2')

                # Update Home tooltip
                home_az = self.db.get_float('positions.home_az', 0)
                home_alt = self.db.get_float('positions.home_alt', 0)
                if current_az_deg is not None and current_alt_deg is not None:
                    delta_az = home_az - current_az_deg
                    delta_alt = home_alt - current_alt_deg
                    if self.home_tooltip:
                        self.home_tooltip.update_text(
                            f"Target: Az={home_az:.1f}°, Alt={home_alt:.1f}°\n"
                            f"Move: ΔAz={delta_az:+.1f}°, ΔAlt={delta_alt:+.1f}°"
                        )

                    # Update Stow tooltip
                    stow_az = self.db.get_float('positions.stow_az', 0)
                    stow_alt = self.db.get_float('positions.stow_alt', 90)
                    delta_az = stow_az - current_az_deg
                    delta_alt = stow_alt - current_alt_deg
                    if self.stow_tooltip:
                        self.stow_tooltip.update_text(
                            f"Target: Az={stow_az:.1f}°, Alt={stow_alt:.1f}°\n"
                            f"Move: ΔAz={delta_az:+.1f}°, ΔAlt={delta_alt:+.1f}°"
                        )
        except Exception as e:
            self.file_logger.log(f"Error updating tooltips: {e}", level='DEBUG')

    def goto_home(self):
        if not self.connected:
            return
        home_az = self.protocol.degrees_to_counts(self.db.get_float('positions.home_az'), '1')
        home_alt = self.protocol.degrees_to_counts(self.db.get_float('positions.home_alt'), '2')
        if home_az is not None and home_alt is not None:
            self.protocol.goto_position('1', home_az)
            self.protocol.goto_position('2', home_alt)
            self.log("Going to HOME")
    
    def set_home(self):
        if not self.connected:
            return
        az = self.protocol.get_position('1')
        alt = self.protocol.get_position('2')
        if az is not None and alt is not None:
            az_deg = self.protocol.counts_to_degrees(az, '1')
            alt_deg = self.protocol.counts_to_degrees(alt, '2')
            if az_deg is not None and alt_deg is not None:
                # Sanity check positions before saving
                if not self.is_position_sane(az_deg, False):
                    self.log("⚠️ Azimuth position out of range, waiting for valid value...")
                    return
                if not self.is_position_sane(alt_deg, True):
                    self.log("⚠️ Altitude position out of range, waiting for valid value...")
                    return

                self.db.set('positions.home_az', str(az_deg))
                self.db.set('positions.home_alt', str(alt_deg))
                self.log(f"HOME set: Az={az_deg:.2f}°, Alt={alt_deg:.2f}°")
                self.update_preset_tooltips()  # Update tooltips immediately
    
    def goto_stow(self):
        if not self.connected:
            return
        stow_az = self.protocol.degrees_to_counts(self.db.get_float('positions.stow_az'), '1')
        stow_alt = self.protocol.degrees_to_counts(self.db.get_float('positions.stow_alt'), '2')
        if stow_az is not None and stow_alt is not None:
            self.protocol.goto_position('1', stow_az)
            self.protocol.goto_position('2', stow_alt)
            self.log("Going to STOW")
    
    def set_stow(self):
        if not self.connected:
            return
        az = self.protocol.get_position('1')
        alt = self.protocol.get_position('2')
        if az is not None and alt is not None:
            az_deg = self.protocol.counts_to_degrees(az, '1')
            alt_deg = self.protocol.counts_to_degrees(alt, '2')
            if az_deg is not None and alt_deg is not None:
                # Sanity check positions before saving
                if not self.is_position_sane(az_deg, False):
                    self.log("⚠️ Azimuth position out of range, waiting for valid value...")
                    return
                if not self.is_position_sane(alt_deg, True):
                    self.log("⚠️ Altitude position out of range, waiting for valid value...")
                    return

                self.db.set('positions.stow_az', str(az_deg))
                self.db.set('positions.stow_alt', str(alt_deg))
                self.log(f"STOW set: Az={az_deg:.2f}°, Alt={alt_deg:.2f}°")
                self.update_preset_tooltips()  # Update tooltips immediately
    
    def zero_position(self):
        if not self.connected:
            return
        if messagebox.askyesno("Confirm", "Zero position?"):
            self.protocol.set_position('1', 0)
            self.protocol.set_position('2', 0)
            self.log("Position zeroed")
    
    def reinitialize(self):
        if not self.connected:
            return
        if messagebox.askyesno("Confirm", "Re-initialize?"):
            self.protocol.initialization_done()
            self.log("Re-initialized")
    
    # -------------------- Diagnostics --------------------
    
    def refresh_diagnostics(self):
        if not self.connected:
            return
        
        text = ""
        for name, axis in [("AZIMUTH", '1'), ("ALTITUDE", '2')]:
            text += f"\n{'='*50}\n{name}\n{'='*50}\n"
            
            pos = self.protocol.get_position(axis)
            if pos is not None:
                deg = self.protocol.counts_to_degrees(pos, axis)
                text += f"Position: {pos:,}"
                if deg is not None:
                    text += f" ({deg:.4f}°)"
                text += "\n"
            
            status = self.protocol.get_status(axis)
            if status:
                text += f"Status: 0x{status['raw']:02X}\n"
                text += f"  Running: {status['running']}\n"
                text += f"  Blocked: {status['blocked']}\n"
                text += f"  Init: {status['initialized']}\n"
        
        self._set_diag_text(text)
    
    def query_system_info(self):
        if not self.connected:
            return
        
        text = "MOUNT INFO\n" + "="*50 + "\n\n"
        
        freq = self.protocol.get_timer_freq()
        if freq:
            text += f"Timer: {freq:,} Hz\n\n"
        
        for name, axis in [("AZIMUTH", '1'), ("ALTITUDE", '2')]:
            text += f"{'-'*50}\n{name}\n"
            ver = self.protocol.get_motor_board_version(axis)
            text += f"Version: {ver}\n"
            cpr = self.protocol.get_counts_per_revolution(axis)
            if cpr:
                text += f"CPR: {cpr:,}\n"
                text += f"Resolution: {360.0/cpr:.6f}°/count\n"
            text += "\n"
        
        self._set_diag_text(text)
        self.log("System info queried")
    
    def _set_diag_text(self, text):
        if TTKBOOTSTRAP_AVAILABLE:
            self.diag_text.delete('1.0', 'end')
            self.diag_text.insert('1.0', text)
        else:
            self.diag_text.configure(state='normal')
            self.diag_text.delete('1.0', 'end')
            self.diag_text.insert('1.0', text)
            self.diag_text.configure(state='disabled')
    
    def toggle_auto_update(self):
        if self.auto_update_var.get():
            self.update_running = True
            self.update_thread = threading.Thread(target=self._auto_update_loop, daemon=True)
            self.update_thread.start()
            self.db.set('display.auto_update', 'True')
        else:
            self.update_running = False
            self.db.set('display.auto_update', 'False')
    
    def _auto_update_loop(self):
        while self.update_running and self.connected:
            self.root.after(0, self.refresh_diagnostics)
            time.sleep(1.0 / max(0.1, self.update_rate_var.get()))
    
    # -------------------- Settings --------------------
    
    def toggle_position_display(self):
        self.db.set('display.show_positions', str(self.show_pos_var.get()))
        self.create_position_labels()
    
    def update_position_format(self):
        self.db.set('display.position_format', self.pos_format_var.get())
        self.create_position_labels()
    
    def update_speed_label(self, *args):
        self.speed_label.configure(text=f"{self.speed_var.get():.2f}")
        self.db.set('speed.default', str(self.speed_var.get()))
    
    def save_control_settings(self):
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
        if not TTKBOOTSTRAP_AVAILABLE:
            return
        theme = self.theme_var.get()
        try:
            self.root.style.theme_use(theme)
            self.db.set('theme.name', theme)
            self.log(f"Theme: {theme}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not apply theme: {e}")
    
    def save_connection_settings(self):
        self.db.set('connection.ip', self.default_ip_entry.get())
        self.db.set('connection.port', self.default_port_entry.get())
        self.db.set('connection.timeout', self.timeout_entry.get())
        
        self.ip_entry.delete(0, 'end')
        self.ip_entry.insert(0, self.default_ip_entry.get())
        self.port_entry.delete(0, 'end')
        self.port_entry.insert(0, self.default_port_entry.get())
        
        messagebox.showinfo("Saved", "Connection settings saved!")
    
    def toggle_debug_mode(self):
        enabled = self.debug_mode_var.get()
        self.file_logger.set_debug_mode(enabled)
        self.db.set('logging.debug_mode', str(enabled))
        self.log(f"Debug mode {'enabled' if enabled else 'disabled'}")
    
    def apply_retention(self):
        retention = self.retention_var.get()
        if retention == 0:
            if not messagebox.askyesno("Warning", "Disable file logging?"):
                self.retention_var.set(self.db.get_int('logging.retention', 30))
                return
        self.db.set('logging.retention', str(retention))
        self.file_logger.set_retention(retention)
        self.log(f"Retention: {retention} files")
    
    def open_log_folder(self):
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
        except Exception:
            messagebox.showinfo("Log Folder", f"Logs: {folder}")
    
    def on_closing(self):
        if self.status_monitor:
            self.status_monitor.stop()
        self.update_running = False
        if self.connected:
            self.stop_all()
            if self.protocol:
                self.protocol.close()
        self.file_logger.close()
        self.root.destroy()


def main():
    if TTKBOOTSTRAP_AVAILABLE:
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