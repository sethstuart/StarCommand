#!/usr/bin/env python3
"""
Sky-Watcher Virtuoso GTi 150P Professional Controller
Full-featured GUI with configurable settings, themes, and keyboard controls

Version: 2.0 WORKING - Fixed for GTi 150P
FIXED: 
  - Removed X10 prefix (GTi doesn't support it)
  - Fixed :G command format (was :G{axis}{mode}{dir}, now :G{axis}{2-digit-code})
  - Added :F1 and :F2 initialization (CRITICAL - mount won't move without this!)
  - Comprehensive logging to debug issues

Works with GTi 150P firmware that uses simple protocol without X10 prefix.

LOGGING: Every command sent/received is logged with timestamps
         Check the "Mount Info" tab -> "Command Log" section to see all activity
"""

import socket
import time
import sys
import threading
import json
import os
from datetime import datetime
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox, colorchooser
except ImportError:
    print("Error: tkinter not available. Install with: sudo apt-get install python3-tk")
    sys.exit(1)


class Config:
    """Configuration manager"""
    
    DEFAULT_CONFIG = {
        'connection': {
            'ip': '192.168.4.1',
            'port': 11880,
            'timeout': 2.0
        },
        'controls': {
            'up': 'w',
            'down': 's',
            'left': 'a',
            'right': 'd',
            'stop': 'space',
            'estop': 'Escape',
            'speed_up': 'plus',
            'speed_down': 'minus'
        },
        'display': {
            'position_format': 'both',  # 'degrees', 'raw', 'both', 'coordinates'
            'show_positions': True,
            'auto_update': False,
            'update_rate': 1.0
        },
        'positions': {
            'home_az': 0,
            'home_alt': 0,
            'stow_az': 0,
            'stow_alt': 90
        },
        'theme': {
            'bg': '#2b2b2b',
            'fg': '#ffffff',
            'button_bg': '#3c3c3c',
            'button_fg': '#ffffff',
            'accent': '#4a9eff',
            'estop': '#ff4444'
        },
        'speed': {
            'default': 1.0,
            'min': 0.1,
            'max': 10.0
        }
    }
    
    def __init__(self):
        self.config_dir = Path.home() / '.skywatcher_controller'
        self.config_file = self.config_dir / 'config.json'
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    # Deep merge
                    for section in loaded:
                        if section in self.config:
                            self.config[section].update(loaded[section])
            except Exception as e:
                print(f"Error loading config: {e}")
    
    def save(self):
        """Save configuration to file"""
        try:
            self.config_dir.mkdir(exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, section, key, default=None):
        """Get config value"""
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section, key, value):
        """Set config value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value


class SkyWatcherProtocol:
    """Implementation of SkyWatcher Motor Controller Protocol"""
    
    def __init__(self, ip='192.168.4.1', port=11880, timeout=2.0, log_callback=None):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        self.log_callback = log_callback
        
        # Axis IDs
        self.AXIS_AZ = '1'
        self.AXIS_ALT = '2'
        self.AXIS_BOTH = '3'
        
        # Cache for mount parameters
        self.cpr_az = None
        self.cpr_alt = None
        self.timer_freq = None
    
    def send_command(self, command):
        """Send command and receive response - with logging"""
        if not command.endswith('\r'):
            command += '\r'
        
        # Log the command being sent
        if self.log_callback:
            self.log_callback(f"→ SEND: {repr(command)}")
        
        try:
            self.sock.sendto(command.encode('ascii'), (self.ip, self.port))
            data, addr = self.sock.recvfrom(1024)
            response = data.decode('ascii').strip()
            
            # Log the response received
            if self.log_callback:
                self.log_callback(f"← RECV: {repr(response)} (hex: {data.hex()})")
            
            return response
        except socket.timeout:
            if self.log_callback:
                self.log_callback(f"✗ TIMEOUT waiting for response to {repr(command)}")
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
        """Set motion mode - FIXED FORMAT"""
        # Mode codes (2 hex digits):
        # 00 = High-speed GOTO, CW
        # 01 = High-speed GOTO, CCW  
        # 10 = Low-speed tracking/slew, CW
        # 11 = Low-speed tracking/slew, CCW
        # 20 = Low-speed GOTO, CW
        # 30 = High-speed slewing, CW
        
        if goto_mode:
            if high_speed:
                mode_code = "00" if direction_cw else "01"
            else:
                mode_code = "20" if direction_cw else "21"  
        else:
            # Tracking/slew mode
            mode_code = "10" if direction_cw else "11"
        
        if self.log_callback:
            mode_desc = "GOTO" if goto_mode else "TRACKING"
            speed_desc = "HIGH" if high_speed else "LOW"
            dir_desc = "CW" if direction_cw else "CCW"
            self.log_callback(f"  Set motion mode: {mode_desc}, {speed_desc}, {dir_desc}, code={mode_code}")
        
        cmd = f":G{axis}{mode_code}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def set_step_period(self, axis, period):
        """Set step period"""
        hex_period = self.format_hex_data(period, 3)
        if self.log_callback:
            self.log_callback(f"  Set step period: {period} (0x{hex_period})")
        cmd = f":I{axis}{hex_period}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def start_motion(self, axis):
        """Start motion"""
        if self.log_callback:
            axis_name = "Azimuth" if axis == self.AXIS_AZ else "Altitude"
            self.log_callback(f"  Starting motion on {axis_name}...")
        cmd = f":J{axis}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def stop_motion(self, axis):
        """Stop motion"""
        if self.log_callback:
            axis_name = "Azimuth" if axis == self.AXIS_AZ else "Altitude"
            self.log_callback(f"■ STOP: {axis_name}")
        cmd = f":K{axis}"
        response = self.send_command(cmd)
        result = response and response.startswith('=')
        if self.log_callback:
            if result:
                self.log_callback(f"  ✓ Stop command successful")
            else:
                self.log_callback(f"  ✗ Stop command failed: {repr(response)}")
        return result
    
    def instant_stop(self, axis):
        """Instant stop"""
        if self.log_callback:
            axis_name = "Azimuth" if axis == self.AXIS_AZ else "Altitude"
            self.log_callback(f"⚠ INSTANT STOP: {axis_name}")
        cmd = f":L{axis}"
        response = self.send_command(cmd)
        result = response and response.startswith('=')
        if self.log_callback:
            if result:
                self.log_callback(f"  ✓ Instant stop successful")
            else:
                self.log_callback(f"  ✗ Instant stop failed: {repr(response)}")
        return result
    
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
        """Get motor status"""
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
                'tracking_mode': bool(status & 0x01),
                'goto_mode': not bool(status & 0x01),
                'ccw': bool(status & 0x02),
                'fast': bool(status & 0x04),
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
        if self.log_callback:
            axis_name = "Azimuth" if axis == self.AXIS_AZ else "Altitude"
            direction = "CW/UP" if direction_positive else "CCW/DOWN"
            self.log_callback(f"▶ SLEW: {axis_name} {direction} at {speed_deg_per_sec:.2f}°/sec")
        
        # Get or use cached parameters
        if axis == self.AXIS_AZ:
            cpr = self.cpr_az or self.get_counts_per_revolution(axis)
        else:
            cpr = self.cpr_alt or self.get_counts_per_revolution(axis)
        
        timer_freq = self.timer_freq or self.get_timer_freq()
        
        if not cpr or not timer_freq:
            if self.log_callback:
                self.log_callback(f"✗ Missing parameters: CPR={cpr}, TimerFreq={timer_freq}")
            return False
        
        step_period = int((timer_freq * 360.0) / (speed_deg_per_sec * cpr))
        if self.log_callback:
            self.log_callback(f"  Calculated step_period={step_period} (CPR={cpr}, Freq={timer_freq})")
        
        if not self.set_motion_mode(axis, goto_mode=False, direction_cw=direction_positive):
            if self.log_callback:
                self.log_callback(f"✗ Failed to set motion mode")
            return False
        
        if not self.set_step_period(axis, step_period):
            if self.log_callback:
                self.log_callback(f"✗ Failed to set step period")
            return False
        
        result = self.start_motion(axis)
        if self.log_callback:
            if result:
                self.log_callback(f"✓ Motion started successfully")
            else:
                self.log_callback(f"✗ Failed to start motion")
        
        return result
    
    def goto_position(self, axis, target_position):
        """Goto specific position"""
        target_with_offset = target_position + 0x800000
        hex_target = self.format_hex_data(target_with_offset, 3)
        
        # Set goto mode
        current = self.get_position(axis)
        if current is None:
            return False
        
        direction_cw = target_position > current
        
        if not self.set_motion_mode(axis, goto_mode=True, direction_cw=direction_cw):
            return False
        
        # Set target
        cmd = f":S{axis}{hex_target}"
        if not self.send_command(cmd) or not self.send_command(cmd).startswith('='):
            return False
        
        # Start motion
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
        self.root.title("SkyWatcher Controller v2.0")
        self.root.geometry("1000x750")
        
        # Configuration
        self.config = Config()
        
        # Protocol instance
        self.protocol = None
        self.connected = False
        
        # Position update thread
        self.update_thread = None
        self.update_running = False
        
        # Emergency stop flag
        self.estop_active = False
        
        # Apply theme
        self.apply_theme()
        
        # Create GUI
        self.create_widgets()
        
        # Bind keyboard controls
        self.bind_keyboard_controls()
        
    def apply_theme(self):
        """Apply color theme"""
        theme = self.config.config['theme']
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure styles
        style.configure('TFrame', background=theme['bg'])
        style.configure('TLabel', background=theme['bg'], foreground=theme['fg'])
        style.configure('TButton', background=theme['button_bg'], foreground=theme['button_fg'])
        style.map('TButton', background=[('active', theme['accent'])])
        
        # E-Stop style
        style.configure('EStop.TButton', background=theme['estop'], foreground='white', font=('Arial', 12, 'bold'))
        
        self.root.configure(bg=theme['bg'])
        
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Main notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.create_control_tab()
        self.create_status_tab()
        self.create_settings_tab()
        self.create_info_tab()
        
    def create_control_tab(self):
        """Create control tab"""
        control_tab = ttk.Frame(self.notebook)
        self.notebook.add(control_tab, text="Control")
        
        # Top frame - Connection
        conn_frame = ttk.LabelFrame(control_tab, text="Connection", padding=10)
        conn_frame.grid(row=0, column=0, columnspan=3, sticky='ew', padx=5, pady=5)
        
        ttk.Label(conn_frame, text="IP:").grid(row=0, column=0, sticky='e')
        self.ip_entry = ttk.Entry(conn_frame, width=15)
        self.ip_entry.insert(0, self.config.get('connection', 'ip'))
        self.ip_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky='e')
        self.port_entry = ttk.Entry(conn_frame, width=8)
        self.port_entry.insert(0, str(self.config.get('connection', 'port')))
        self.port_entry.grid(row=0, column=3, padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=4, padx=5)
        
        self.status_label = ttk.Label(conn_frame, text="Disconnected", foreground="red")
        self.status_label.grid(row=0, column=5, padx=10)
        
        # Left frame - Direction controls
        dir_frame = ttk.LabelFrame(control_tab, text="Direction Control", padding=10)
        dir_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        
        # Direction pad
        ttk.Button(dir_frame, text="↑\nUP", command=lambda: self.move('up')).grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        ttk.Button(dir_frame, text="←\nLEFT", command=lambda: self.move('left')).grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
        ttk.Button(dir_frame, text="STOP", command=self.stop_all).grid(row=1, column=1, padx=5, pady=5, sticky='nsew')
        ttk.Button(dir_frame, text="→\nRIGHT", command=lambda: self.move('right')).grid(row=1, column=2, padx=5, pady=5, sticky='nsew')
        ttk.Button(dir_frame, text="↓\nDOWN", command=lambda: self.move('down')).grid(row=2, column=1, padx=5, pady=5, sticky='nsew')
        
        # Emergency Stop - Large and prominent
        self.estop_btn = ttk.Button(dir_frame, text="🛑 EMERGENCY STOP", style='EStop.TButton', command=self.emergency_stop)
        self.estop_btn.grid(row=3, column=0, columnspan=3, sticky='ew', pady=10)
        
        # Speed control
        speed_frame = ttk.Frame(dir_frame)
        speed_frame.grid(row=4, column=0, columnspan=3, pady=10, sticky='ew')
        
        ttk.Label(speed_frame, text="Speed (°/sec):").pack(side='left', padx=5)
        self.speed_var = tk.DoubleVar(value=self.config.get('speed', 'default'))
        self.speed_scale = ttk.Scale(speed_frame, from_=self.config.get('speed', 'min'), 
                                     to=self.config.get('speed', 'max'),
                                     variable=self.speed_var, orient='horizontal')
        self.speed_scale.pack(side='left', fill='x', expand=True, padx=5)
        
        self.speed_label = ttk.Label(speed_frame, text=f"{self.speed_var.get():.2f}")
        self.speed_label.pack(side='left', padx=5)
        self.speed_var.trace('w', self.update_speed_label)
        
        # Keyboard hints
        hint_text = f"Keyboard: {self.config.get('controls', 'up').upper()}/{self.config.get('controls', 'down').upper()}/{self.config.get('controls', 'left').upper()}/{self.config.get('controls', 'right').upper()}, SPACE=Stop, ESC=E-Stop"
        ttk.Label(dir_frame, text=hint_text, font=('Arial', 8)).grid(row=5, column=0, columnspan=3, pady=5)
        
        # Center frame - Preset positions
        preset_frame = ttk.LabelFrame(control_tab, text="Preset Positions", padding=10)
        preset_frame.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)
        
        ttk.Button(preset_frame, text="Go to Home", command=self.goto_home, width=20).pack(pady=5)
        ttk.Button(preset_frame, text="Set Current as Home", command=self.set_home, width=20).pack(pady=5)
        ttk.Button(preset_frame, text="Go to Stow", command=self.goto_stow, width=20).pack(pady=5)
        ttk.Button(preset_frame, text="Set Current as Stow", command=self.set_stow, width=20).pack(pady=5)
        
        ttk.Separator(preset_frame, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Button(preset_frame, text="Set Position to Zero", command=self.zero_position, width=20).pack(pady=5)
        ttk.Button(preset_frame, text="Re-initialize Mount", command=self.reinitialize, width=20).pack(pady=5)
        
        # Right frame - Position display
        self.pos_frame = ttk.LabelFrame(control_tab, text="Position Display", padding=10)
        self.pos_frame.grid(row=1, column=2, sticky='nsew', padx=5, pady=5)
        
        # Show/hide positions toggle
        self.show_pos_var = tk.BooleanVar(value=self.config.get('display', 'show_positions'))
        ttk.Checkbutton(self.pos_frame, text="Show Positions", variable=self.show_pos_var,
                       command=self.toggle_position_display).pack(anchor='w', pady=5)
        
        # Position format selector
        ttk.Label(self.pos_frame, text="Display Format:").pack(anchor='w', pady=5)
        self.pos_format_var = tk.StringVar(value=self.config.get('display', 'position_format'))
        
        formats = [
            ('Degrees', 'degrees'),
            ('Raw Counts', 'raw'),
            ('Both', 'both'),
            ('Alt/Az Coords', 'coordinates')
        ]
        
        for text, value in formats:
            ttk.Radiobutton(self.pos_frame, text=text, variable=self.pos_format_var,
                          value=value, command=self.update_position_display).pack(anchor='w')
        
        # Position labels (will be populated based on format)
        self.pos_display_frame = ttk.Frame(self.pos_frame)
        self.pos_display_frame.pack(fill='both', expand=True, pady=10)
        
        self.create_position_labels()
        
        # Configure grid weights
        control_tab.columnconfigure(0, weight=1)
        control_tab.columnconfigure(1, weight=1)
        control_tab.columnconfigure(2, weight=1)
        control_tab.rowconfigure(1, weight=1)
        
    def create_status_tab(self):
        """Create status tab"""
        status_tab = ttk.Frame(self.notebook)
        self.notebook.add(status_tab, text="Status")
        
        # Auto-update control
        auto_frame = ttk.Frame(status_tab)
        auto_frame.pack(fill='x', padx=10, pady=10)
        
        self.auto_update_var = tk.BooleanVar(value=self.config.get('display', 'auto_update'))
        ttk.Checkbutton(auto_frame, text="Auto-update", variable=self.auto_update_var,
                       command=self.toggle_auto_update).pack(side='left', padx=5)
        
        ttk.Label(auto_frame, text="Rate (Hz):").pack(side='left', padx=5)
        self.update_rate_var = tk.DoubleVar(value=self.config.get('display', 'update_rate'))
        rate_spin = ttk.Spinbox(auto_frame, from_=0.1, to=10, increment=0.1, 
                               textvariable=self.update_rate_var, width=5)
        rate_spin.pack(side='left', padx=5)
        
        ttk.Button(auto_frame, text="Refresh Now", command=self.refresh_status).pack(side='left', padx=20)
        
        # Status display
        self.status_text = scrolledtext.ScrolledText(status_tab, height=25, width=90,
                                                     font=('Courier', 10))
        self.status_text.pack(fill='both', expand=True, padx=10, pady=10)
        
    def create_settings_tab(self):
        """Create settings tab"""
        settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(settings_tab, text="Settings")
        
        # Create notebook for settings sections
        settings_notebook = ttk.Notebook(settings_tab)
        settings_notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Keyboard controls settings
        kb_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(kb_frame, text="Keyboard")
        
        ttk.Label(kb_frame, text="Configure Keyboard Controls", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        controls_grid = ttk.Frame(kb_frame)
        controls_grid.pack(pady=10)
        
        self.key_entries = {}
        controls = [
            ('up', 'Move Up'),
            ('down', 'Move Down'),
            ('left', 'Move Left'),
            ('right', 'Move Right'),
            ('stop', 'Stop'),
            ('estop', 'Emergency Stop'),
            ('speed_up', 'Speed Up'),
            ('speed_down', 'Speed Down')
        ]
        
        for i, (key, label) in enumerate(controls):
            ttk.Label(controls_grid, text=label + ":").grid(row=i, column=0, sticky='e', padx=5, pady=5)
            entry = ttk.Entry(controls_grid, width=15)
            entry.insert(0, self.config.get('controls', key))
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.key_entries[key] = entry
        
        ttk.Button(kb_frame, text="Save Keyboard Settings", 
                  command=self.save_keyboard_settings).pack(pady=10)
        
        # Theme settings
        theme_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(theme_frame, text="Theme")
        
        ttk.Label(theme_frame, text="Configure Color Theme", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        theme_grid = ttk.Frame(theme_frame)
        theme_grid.pack(pady=10)
        
        self.theme_buttons = {}
        theme_items = [
            ('bg', 'Background'),
            ('fg', 'Foreground'),
            ('button_bg', 'Button Background'),
            ('button_fg', 'Button Foreground'),
            ('accent', 'Accent Color'),
            ('estop', 'E-Stop Color')
        ]
        
        for i, (key, label) in enumerate(theme_items):
            ttk.Label(theme_grid, text=label + ":").grid(row=i, column=0, sticky='e', padx=5, pady=5)
            btn = ttk.Button(theme_grid, text="Choose Color", 
                           command=lambda k=key: self.choose_color(k))
            btn.grid(row=i, column=1, padx=5, pady=5)
            self.theme_buttons[key] = btn
        
        ttk.Button(theme_frame, text="Save Theme Settings", 
                  command=self.save_theme_settings).pack(pady=10)
        ttk.Button(theme_frame, text="Reset to Default Theme", 
                  command=self.reset_theme).pack(pady=5)
        
        # Connection settings
        conn_settings_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(conn_settings_frame, text="Connection")
        
        ttk.Label(conn_settings_frame, text="Default Connection Settings", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        conn_grid = ttk.Frame(conn_settings_frame)
        conn_grid.pack(pady=10)
        
        ttk.Label(conn_grid, text="Default IP:").grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.default_ip_entry = ttk.Entry(conn_grid, width=20)
        self.default_ip_entry.insert(0, self.config.get('connection', 'ip'))
        self.default_ip_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(conn_grid, text="Default Port:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.default_port_entry = ttk.Entry(conn_grid, width=20)
        self.default_port_entry.insert(0, str(self.config.get('connection', 'port')))
        self.default_port_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(conn_grid, text="Timeout (sec):").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.timeout_entry = ttk.Entry(conn_grid, width=20)
        self.timeout_entry.insert(0, str(self.config.get('connection', 'timeout')))
        self.timeout_entry.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Button(conn_settings_frame, text="Save Connection Settings", 
                  command=self.save_connection_settings).pack(pady=10)
        
    def create_info_tab(self):
        """Create info tab"""
        info_tab = ttk.Frame(self.notebook)
        self.notebook.add(info_tab, text="Mount Info")
        
        ttk.Button(info_tab, text="Query Mount Information", 
                  command=self.query_system_info).pack(pady=10)
        
        self.info_text = scrolledtext.ScrolledText(info_tab, height=30, width=90,
                                                   font=('Courier', 10))
        self.info_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Command log
        log_frame = ttk.LabelFrame(info_tab, text="Command Log", padding=5)
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=90,
                                                  font=('Courier', 9))
        self.log_text.pack(fill='both', expand=True)
        
    def create_position_labels(self):
        """Create position display labels based on format"""
        # Clear existing
        for widget in self.pos_display_frame.winfo_children():
            widget.destroy()
        
        if not self.show_pos_var.get():
            return
        
        format_type = self.pos_format_var.get()
        
        if format_type == 'degrees':
            ttk.Label(self.pos_display_frame, text="Azimuth:").grid(row=0, column=0, sticky='e', pady=5)
            self.az_deg_label = ttk.Label(self.pos_display_frame, text="---°", font=('Courier', 11))
            self.az_deg_label.grid(row=0, column=1, sticky='w', padx=5)
            
            ttk.Label(self.pos_display_frame, text="Altitude:").grid(row=1, column=0, sticky='e', pady=5)
            self.alt_deg_label = ttk.Label(self.pos_display_frame, text="---°", font=('Courier', 11))
            self.alt_deg_label.grid(row=1, column=1, sticky='w', padx=5)
            
        elif format_type == 'raw':
            ttk.Label(self.pos_display_frame, text="Az (counts):").grid(row=0, column=0, sticky='e', pady=5)
            self.az_raw_label = ttk.Label(self.pos_display_frame, text="---", font=('Courier', 11))
            self.az_raw_label.grid(row=0, column=1, sticky='w', padx=5)
            
            ttk.Label(self.pos_display_frame, text="Alt (counts):").grid(row=1, column=0, sticky='e', pady=5)
            self.alt_raw_label = ttk.Label(self.pos_display_frame, text="---", font=('Courier', 11))
            self.alt_raw_label.grid(row=1, column=1, sticky='w', padx=5)
            
        elif format_type == 'both':
            ttk.Label(self.pos_display_frame, text="Azimuth:").grid(row=0, column=0, sticky='e', pady=5)
            self.az_both_label = ttk.Label(self.pos_display_frame, text="---", font=('Courier', 10))
            self.az_both_label.grid(row=0, column=1, sticky='w', padx=5)
            
            ttk.Label(self.pos_display_frame, text="Altitude:").grid(row=1, column=0, sticky='e', pady=5)
            self.alt_both_label = ttk.Label(self.pos_display_frame, text="---", font=('Courier', 10))
            self.alt_both_label.grid(row=1, column=1, sticky='w', padx=5)
            
        elif format_type == 'coordinates':
            ttk.Label(self.pos_display_frame, text="Position:").grid(row=0, column=0, sticky='ne', pady=5)
            self.coord_label = ttk.Label(self.pos_display_frame, text="---", font=('Courier', 10), justify='left')
            self.coord_label.grid(row=0, column=1, sticky='w', padx=5)
    
    def bind_keyboard_controls(self):
        """Bind keyboard controls"""
        controls = self.config.config['controls']
        
        # Bind each control
        self.root.bind(f"<KeyPress-{controls['up']}>", lambda e: self.move('up'))
        self.root.bind(f"<KeyPress-{controls['down']}>", lambda e: self.move('down'))
        self.root.bind(f"<KeyPress-{controls['left']}>", lambda e: self.move('left'))
        self.root.bind(f"<KeyPress-{controls['right']}>", lambda e: self.move('right'))
        
        # Arrow keys
        self.root.bind("<Up>", lambda e: self.move('up'))
        self.root.bind("<Down>", lambda e: self.move('down'))
        self.root.bind("<Left>", lambda e: self.move('left'))
        self.root.bind("<Right>", lambda e: self.move('right'))
        
        # Stop and E-stop
        self.root.bind(f"<KeyPress-{controls['stop']}>", lambda e: self.stop_all())
        self.root.bind(f"<KeyPress-{controls['estop']}>", lambda e: self.emergency_stop())
        
        # Speed controls
        self.root.bind(f"<KeyPress-{controls['speed_up']}>", lambda e: self.adjust_speed(0.5))
        self.root.bind(f"<KeyPress-{controls['speed_down']}>", lambda e: self.adjust_speed(-0.5))
    
    def log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.insert('end', f"[{timestamp}] {message}\n")
        self.log_text.see('end')
    
    def toggle_connection(self):
        """Connect or disconnect"""
        if self.connected:
            self.stop_all()
            if self.protocol:
                self.protocol.close()
            self.protocol = None
            self.connected = False
            self.connect_btn.configure(text="Connect")
            self.status_label.configure(text="Disconnected", foreground="red")
            self.log("Disconnected")
            
            if self.auto_update_var.get():
                self.auto_update_var.set(False)
                self.toggle_auto_update()
        else:
            ip = self.ip_entry.get()
            port = int(self.port_entry.get())
            timeout = self.config.get('connection', 'timeout')
            
            self.log(f"Connecting to {ip}:{port} with timeout={timeout}s...")
            self.protocol = SkyWatcherProtocol(ip, port, timeout, log_callback=self.log)
            
            try:
                version = self.protocol.get_motor_board_version('1')
                if version is not None:
                    self.connected = True
                    self.connect_btn.configure(text="Disconnect")
                    self.status_label.configure(text="Connected", foreground="green")
                    self.log(f"✓ Connected to {ip}:{port}")
                    self.log(f"Motor board version: {version}")
                    
                    self.log("Initializing axes...")
                    # CRITICAL: Initialize both axes before they will move!
                    init1 = self.protocol.send_command(":F1")
                    init2 = self.protocol.send_command(":F2")
                    
                    if init1 and init1.startswith('='):
                        self.log("✓ Axis 1 (Azimuth) initialized")
                    else:
                        self.log(f"⚠ Axis 1 init: {repr(init1)}")
                    
                    if init2 and init2.startswith('='):
                        self.log("✓ Axis 2 (Altitude) initialized")
                    else:
                        self.log(f"⚠ Axis 2 init: {repr(init2)}")
                    
                    # Query parameters
                    self.log("Querying mount parameters...")
                    cpr_az = self.protocol.get_counts_per_revolution(self.protocol.AXIS_AZ)
                    cpr_alt = self.protocol.get_counts_per_revolution(self.protocol.AXIS_ALT)
                    timer_freq = self.protocol.get_timer_freq()
                    
                    if cpr_az:
                        self.log(f"Azimuth CPR: {cpr_az:,}")
                    if cpr_alt:
                        self.log(f"Altitude CPR: {cpr_alt:,}")
                    if timer_freq:
                        self.log(f"Timer Frequency: {timer_freq:,} Hz")
                    
                    self.log("✓ Mount ready! Press W/A/S/D or use buttons to move.")
                else:
                    self.log("✗ Failed to get version from mount")
                    messagebox.showerror("Connection Error", 
                                       "Could not connect to telescope.")
                    self.protocol.close()
                    self.protocol = None
            except Exception as e:
                self.log(f"✗ Connection error: {e}")
                messagebox.showerror("Connection Error", str(e))
                if self.protocol:
                    self.protocol.close()
                self.protocol = None
    
    def move(self, direction):
        """Start moving in direction"""
        if not self.connected:
            self.log("✗ Not connected - cannot move")
            return
        
        if self.estop_active:
            self.log("✗ E-Stop active - click STOP button to clear")
            return
        
        speed = self.speed_var.get()
        self.log(f"=== MOVE {direction.upper()} requested at {speed:.2f}°/sec ===")
        
        if direction == 'up':
            self.protocol.slew_fixed_rate(self.protocol.AXIS_ALT, True, speed)
        elif direction == 'down':
            self.protocol.slew_fixed_rate(self.protocol.AXIS_ALT, False, speed)
        elif direction == 'left':
            self.protocol.slew_fixed_rate(self.protocol.AXIS_AZ, False, speed)
        elif direction == 'right':
            self.protocol.slew_fixed_rate(self.protocol.AXIS_AZ, True, speed)
    
    def stop_all(self):
        """Stop all motion"""
        if not self.connected:
            self.log("✗ Not connected")
            return
        
        self.log("=== STOP ALL requested ===")
        self.protocol.stop_motion(self.protocol.AXIS_AZ)
        self.protocol.stop_motion(self.protocol.AXIS_ALT)
        self.estop_active = False
        self.estop_btn.configure(text="🛑 EMERGENCY STOP")
        self.log("✓ All axes stopped, E-Stop cleared")
    
    def emergency_stop(self):
        """Emergency stop - instant stop both axes"""
        if not self.connected:
            return
        
        self.estop_active = True
        self.protocol.instant_stop(self.protocol.AXIS_AZ)
        self.protocol.instant_stop(self.protocol.AXIS_ALT)
        self.estop_btn.configure(text="⚠️ E-STOP ACTIVE - Click STOP to Clear")
        self.log("⚠️ EMERGENCY STOP ACTIVATED")
        messagebox.showwarning("Emergency Stop", "Emergency stop activated!\nClick STOP button to clear.")
    
    def goto_home(self):
        """Go to home position"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        home_az = self.protocol.degrees_to_counts(
            self.config.get('positions', 'home_az'), self.protocol.AXIS_AZ)
        home_alt = self.protocol.degrees_to_counts(
            self.config.get('positions', 'home_alt'), self.protocol.AXIS_ALT)
        
        if home_az is not None and home_alt is not None:
            self.protocol.goto_position(self.protocol.AXIS_AZ, home_az)
            self.protocol.goto_position(self.protocol.AXIS_ALT, home_alt)
            self.log("Going to HOME position")
    
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
            
            self.config.set('positions', 'home_az', az_deg)
            self.config.set('positions', 'home_alt', alt_deg)
            self.config.save()
            
            self.log(f"Set HOME: Az={az_deg:.2f}°, Alt={alt_deg:.2f}°")
            messagebox.showinfo("Home Set", f"Home position set to:\nAz: {az_deg:.2f}°\nAlt: {alt_deg:.2f}°")
    
    def goto_stow(self):
        """Go to stow position"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        stow_az = self.protocol.degrees_to_counts(
            self.config.get('positions', 'stow_az'), self.protocol.AXIS_AZ)
        stow_alt = self.protocol.degrees_to_counts(
            self.config.get('positions', 'stow_alt'), self.protocol.AXIS_ALT)
        
        if stow_az is not None and stow_alt is not None:
            self.protocol.goto_position(self.protocol.AXIS_AZ, stow_az)
            self.protocol.goto_position(self.protocol.AXIS_ALT, stow_alt)
            self.log("Going to STOW position")
    
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
            
            self.config.set('positions', 'stow_az', az_deg)
            self.config.set('positions', 'stow_alt', alt_deg)
            self.config.save()
            
            self.log(f"Set STOW: Az={az_deg:.2f}°, Alt={alt_deg:.2f}°")
            messagebox.showinfo("Stow Set", f"Stow position set to:\nAz: {az_deg:.2f}°\nAlt: {alt_deg:.2f}°")
    
    def zero_position(self):
        """Set current position to zero"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        if messagebox.askyesno("Confirm", "Set current position to 0,0?"):
            self.protocol.set_position(self.protocol.AXIS_AZ, 0)
            self.protocol.set_position(self.protocol.AXIS_ALT, 0)
            self.log("Position set to 0,0")
    
    def reinitialize(self):
        """Re-initialize mount"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        if messagebox.askyesno("Confirm", "Re-initialize mount?"):
            self.protocol.initialization_done()
            self.log("Mount re-initialized")
    
    def toggle_position_display(self):
        """Toggle position display"""
        self.config.set('display', 'show_positions', self.show_pos_var.get())
        self.create_position_labels()
    
    def update_position_display(self):
        """Update position display format"""
        self.config.set('display', 'position_format', self.pos_format_var.get())
        self.create_position_labels()
    
    def update_positions(self):
        """Update position displays"""
        if not self.connected or not self.show_pos_var.get():
            return
        
        az_pos = self.protocol.get_position(self.protocol.AXIS_AZ)
        alt_pos = self.protocol.get_position(self.protocol.AXIS_ALT)
        
        if az_pos is None or alt_pos is None:
            return
        
        format_type = self.pos_format_var.get()
        
        if format_type == 'degrees':
            az_deg = self.protocol.counts_to_degrees(az_pos, self.protocol.AXIS_AZ)
            alt_deg = self.protocol.counts_to_degrees(alt_pos, self.protocol.AXIS_ALT)
            
            if az_deg is not None:
                self.az_deg_label.configure(text=f"{az_deg:.4f}°")
            if alt_deg is not None:
                self.alt_deg_label.configure(text=f"{alt_deg:.4f}°")
                
        elif format_type == 'raw':
            self.az_raw_label.configure(text=f"{az_pos:,} (0x{az_pos:08X})")
            self.alt_raw_label.configure(text=f"{alt_pos:,} (0x{alt_pos:08X})")
            
        elif format_type == 'both':
            az_deg = self.protocol.counts_to_degrees(az_pos, self.protocol.AXIS_AZ)
            alt_deg = self.protocol.counts_to_degrees(alt_pos, self.protocol.AXIS_ALT)
            
            if az_deg is not None:
                self.az_both_label.configure(text=f"{az_deg:.4f}° ({az_pos:,})")
            if alt_deg is not None:
                self.alt_both_label.configure(text=f"{alt_deg:.4f}° ({alt_pos:,})")
                
        elif format_type == 'coordinates':
            az_deg = self.protocol.counts_to_degrees(az_pos, self.protocol.AXIS_AZ)
            alt_deg = self.protocol.counts_to_degrees(alt_pos, self.protocol.AXIS_ALT)
            
            if az_deg is not None and alt_deg is not None:
                # Normalize to 0-360
                az_deg = az_deg % 360
                coord_text = f"Az: {az_deg:.4f}°\nAlt: {alt_deg:.4f}°"
                self.coord_label.configure(text=coord_text)
    
    def refresh_status(self):
        """Refresh status display"""
        if not self.connected:
            return
        
        self.status_text.delete('1.0', 'end')
        
        # Get status for both axes
        for axis_name, axis_id in [("AZIMUTH", '1'), ("ALTITUDE", '2')]:
            self.status_text.insert('end', f"\n{'='*50}\n")
            self.status_text.insert('end', f"{axis_name} AXIS\n")
            self.status_text.insert('end', f"{'='*50}\n\n")
            
            # Position
            pos = self.protocol.get_position(axis_id)
            if pos is not None:
                deg = self.protocol.counts_to_degrees(pos, axis_id)
                self.status_text.insert('end', f"Position (counts): {pos:,} (0x{pos:08X})\n")
                if deg is not None:
                    self.status_text.insert('end', f"Position (degrees): {deg:.6f}°\n")
            
            # Status
            status = self.protocol.get_status(axis_id)
            if status:
                self.status_text.insert('end', f"\nStatus:\n")
                self.status_text.insert('end', f"  Running:     {status['running']}\n")
                self.status_text.insert('end', f"  Initialized: {status['initialized']}\n")
                self.status_text.insert('end', f"  Mode:        {'Tracking' if status['tracking_mode'] else 'Goto'}\n")
                self.status_text.insert('end', f"  Direction:   {'CCW' if status['ccw'] else 'CW'}\n")
                self.status_text.insert('end', f"  Speed:       {'Fast' if status['fast'] else 'Slow'}\n")
                self.status_text.insert('end', f"  Blocked:     {status['blocked']}\n")
        
        # Update position displays
        self.update_positions()
    
    def toggle_auto_update(self):
        """Toggle auto-update"""
        if self.auto_update_var.get():
            self.update_running = True
            self.update_thread = threading.Thread(target=self.auto_update_loop, daemon=True)
            self.update_thread.start()
            self.log("Auto-update enabled")
            self.config.set('display', 'auto_update', True)
        else:
            self.update_running = False
            if self.update_thread:
                self.update_thread.join(timeout=2)
            self.log("Auto-update disabled")
            self.config.set('display', 'auto_update', False)
    
    def auto_update_loop(self):
        """Auto-update loop"""
        while self.update_running and self.connected:
            self.root.after(0, self.refresh_status)
            time.sleep(1.0 / self.update_rate_var.get())
    
    def query_system_info(self):
        """Query system information"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        self.info_text.delete('1.0', 'end')
        
        for axis_name, axis_id in [("AZIMUTH", '1'), ("ALTITUDE", '2')]:
            self.info_text.insert('end', f"\n{'='*60}\n")
            self.info_text.insert('end', f"{axis_name} AXIS (ID: {axis_id})\n")
            self.info_text.insert('end', f"{'='*60}\n\n")
            
            # Version
            version = self.protocol.get_motor_board_version(axis_id)
            self.info_text.insert('end', f"Motor Board Version: {version}\n")
            
            # CPR
            cpr = self.protocol.get_counts_per_revolution(axis_id)
            if cpr:
                self.info_text.insert('end', f"Counts Per Revolution: {cpr:,} (0x{cpr:08X})\n")
                self.info_text.insert('end', f"Resolution: {360.0/cpr:.8f} deg/count\n")
                self.info_text.insert('end', f"Arc-seconds per count: {(360.0*3600)/cpr:.4f}\"\n")
            
            # Timer frequency (once)
            if axis_id == '1':
                timer_freq = self.protocol.get_timer_freq()
                if timer_freq:
                    self.info_text.insert('end', f"\nTimer Frequency: {timer_freq:,} Hz (0x{timer_freq:08X})\n")
            
            # Position
            pos = self.protocol.get_position(axis_id)
            if pos is not None:
                deg = self.protocol.counts_to_degrees(pos, axis_id)
                self.info_text.insert('end', f"\nCurrent Position: {pos:,} (0x{pos:08X})\n")
                if deg is not None:
                    self.info_text.insert('end', f"Current Position: {deg:.6f}°\n")
            
            # Status
            status = self.protocol.get_status(axis_id)
            if status:
                self.info_text.insert('end', f"\nStatus:\n")
                self.info_text.insert('end', f"  Running:     {status['running']}\n")
                self.info_text.insert('end', f"  Initialized: {status['initialized']}\n")
                self.info_text.insert('end', f"  Blocked:     {status['blocked']}\n")
                self.info_text.insert('end', f"  Mode:        {'Tracking' if status['tracking_mode'] else 'Goto'}\n")
        
        self.log("System information queried")
    
    def adjust_speed(self, delta):
        """Adjust speed by delta"""
        new_speed = max(self.config.get('speed', 'min'),
                       min(self.config.get('speed', 'max'),
                           self.speed_var.get() + delta))
        self.speed_var.set(new_speed)
    
    def update_speed_label(self, *args):
        """Update speed label"""
        self.speed_label.configure(text=f"{self.speed_var.get():.2f}")
    
    def save_keyboard_settings(self):
        """Save keyboard settings"""
        for key, entry in self.key_entries.items():
            self.config.set('controls', key, entry.get())
        self.config.save()
        
        # Rebind
        self.bind_keyboard_controls()
        
        messagebox.showinfo("Saved", "Keyboard settings saved!\nRestart recommended.")
        self.log("Keyboard settings saved")
    
    def choose_color(self, theme_key):
        """Choose color for theme element"""
        current = self.config.get('theme', theme_key)
        color = colorchooser.askcolor(current)[1]
        if color:
            self.config.set('theme', theme_key, color)
    
    def save_theme_settings(self):
        """Save theme settings"""
        self.config.save()
        messagebox.showinfo("Saved", "Theme settings saved!\nRestart to apply.")
        self.log("Theme settings saved")
    
    def reset_theme(self):
        """Reset theme to default"""
        self.config.config['theme'] = Config.DEFAULT_CONFIG['theme'].copy()
        self.config.save()
        messagebox.showinfo("Reset", "Theme reset to default!\nRestart to apply.")
    
    def save_connection_settings(self):
        """Save connection settings"""
        self.config.set('connection', 'ip', self.default_ip_entry.get())
        self.config.set('connection', 'port', int(self.default_port_entry.get()))
        self.config.set('connection', 'timeout', float(self.timeout_entry.get()))
        self.config.save()
        
        # Update main entries
        self.ip_entry.delete(0, 'end')
        self.ip_entry.insert(0, self.default_ip_entry.get())
        self.port_entry.delete(0, 'end')
        self.port_entry.insert(0, self.default_port_entry.get())
        
        messagebox.showinfo("Saved", "Connection settings saved!")
        self.log("Connection settings saved")
    
    def on_closing(self):
        """Handle window closing"""
        if self.connected:
            self.stop_all()
            if self.protocol:
                self.protocol.close()
        
        # Save current state
        self.config.set('display', 'position_format', self.pos_format_var.get())
        self.config.set('display', 'show_positions', self.show_pos_var.get())
        self.config.set('speed', 'default', self.speed_var.get())
        self.config.save()
        
        self.root.destroy()


def main():
    root = tk.Tk()
    app = TelescopeGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
