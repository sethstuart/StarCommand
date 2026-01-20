#!/usr/bin/env python3
"""
SkyWatcher Controller - Working Version for GTi 150P
Works with mounts that don't use X10 prefix (original protocol)
"""

import socket
import time
import sys
import threading
import json
from datetime import datetime
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
except ImportError:
    print("Error: tkinter not available")
    sys.exit(1)


class Config:
    """Configuration manager"""
    
    DEFAULT_CONFIG = {
        'connection': {'ip': '192.168.4.1', 'port': 11880, 'timeout': 2.0},
        'display': {'position_format': 'both', 'show_positions': True, 'auto_update': False},
        'positions': {'home_az': 0, 'home_alt': 0, 'stow_az': 0, 'stow_alt': 90},
        'theme': {'bg': '#2b2b2b', 'fg': '#ffffff', 'accent': '#4a9eff', 'estop': '#ff4444'},
        'speed': {'default': 1.0, 'min': 0.1, 'max': 10.0}
    }
    
    def __init__(self):
        self.config_dir = Path.home() / '.skywatcher_controller'
        self.config_file = self.config_dir / 'config.json'
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    for section in loaded:
                        if section in self.config:
                            self.config[section].update(loaded[section])
            except:
                pass
    
    def save(self):
        try:
            self.config_dir.mkdir(exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except:
            pass
    
    def get(self, section, key, default=None):
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section, key, value):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value


class SkyWatcherSimple:
    """Simple protocol for GTi mounts without X10 prefix"""
    
    def __init__(self, ip='192.168.4.1', port=11880, timeout=2.0):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        
        self.AXIS_AZ = '1'
        self.AXIS_ALT = '2'
        
        self.cpr_az = None
        self.cpr_alt = None
        self.timer_freq = None
    
    def send_command(self, command):
        """Send command and get response"""
        if not command.endswith('\r'):
            command += '\r'
        
        try:
            self.sock.sendto(command.encode('ascii'), (self.ip, self.port))
            data, addr = self.sock.recvfrom(1024)
            return data.decode('ascii').strip()
        except:
            return None
    
    def parse_hex_response(self, response):
        """Parse hex response (LSB first)"""
        if not response or not response.startswith('='):
            return None
        
        hex_str = response[1:].replace('\r', '')
        if not hex_str:
            return None
        
        # Reverse pairs for LSB-first format
        reversed_str = ''.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)][::-1])
        try:
            return int(reversed_str, 16)
        except:
            return None
    
    def format_hex_data(self, value, bytes_count=3):
        """Format value as hex in LSB-first format"""
        hex_str = f"{value:0{bytes_count*2}X}"
        return ''.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)][::-1])
    
    def get_version(self):
        """Get version"""
        response = self.send_command(":e1")
        return response if response and response.startswith('=') else None
    
    def get_position(self, axis):
        """Get position"""
        cmd = f":j{axis}"
        response = self.send_command(cmd)
        if response:
            pos = self.parse_hex_response(response)
            if pos is not None:
                return pos - 0x800000
        return None
    
    def set_position(self, axis, position):
        """Set position"""
        pos_with_offset = position + 0x800000
        hex_pos = self.format_hex_data(pos_with_offset, 3)
        cmd = f":E{axis}{hex_pos}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def get_counts_per_revolution(self, axis):
        """Get CPR"""
        cmd = f":a{axis}"
        response = self.send_command(cmd)
        cpr = self.parse_hex_response(response)
        if cpr:
            if axis == self.AXIS_AZ:
                self.cpr_az = cpr
            else:
                self.cpr_alt = cpr
        return cpr
    
    def get_timer_freq(self):
        """Get timer frequency"""
        if self.timer_freq:
            return self.timer_freq
        
        cmd = ":b1"
        response = self.send_command(cmd)
        freq = self.parse_hex_response(response)
        if freq:
            self.timer_freq = freq
        return freq
    
    def get_status(self, axis):
        """Get status"""
        cmd = f":f{axis}"
        response = self.send_command(cmd)
        
        if not response or not response.startswith('='):
            return None
        
        try:
            status = int(response[1:3], 16)
            return {
                'running': bool(status & 0x01),
                'initialized': bool(status & 0x04),
                'tracking_mode': bool(status & 0x01),
                'ccw': bool(status & 0x02)
            }
        except:
            return None
    
    def set_motion_mode(self, axis, goto_mode=False, direction_cw=True):
        """Set motion mode"""
        mode_byte = 0
        if not goto_mode:
            mode_byte |= 0x01  # Tracking
        if not direction_cw:
            mode_byte |= 0x02  # CCW
        
        mode_hex = f"{mode_byte:02X}"
        direction_byte = 0
        if not direction_cw:
            direction_byte |= 0x01
        dir_hex = f"{direction_byte:02X}"
        
        cmd = f":G{axis}{mode_hex}{dir_hex}"
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
        """Emergency stop"""
        cmd = f":L{axis}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def initialization_done(self):
        """Signal initialization"""
        cmd = ":F3"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def slew_fixed_rate(self, axis, direction_positive=True, speed_deg_per_sec=1.0):
        """Slew at fixed rate"""
        # Get CPR and timer freq
        if axis == self.AXIS_AZ:
            cpr = self.cpr_az or self.get_counts_per_revolution(axis)
        else:
            cpr = self.cpr_alt or self.get_counts_per_revolution(axis)
        
        timer_freq = self.timer_freq or self.get_timer_freq()
        
        if not cpr or not timer_freq:
            return False
        
        # Calculate step period
        step_period = int((timer_freq * 360.0) / (speed_deg_per_sec * cpr))
        
        # Set motion mode
        if not self.set_motion_mode(axis, goto_mode=False, direction_cw=direction_positive):
            return False
        
        # Set step period
        if not self.set_step_period(axis, step_period):
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
    
    def goto_position(self, axis, target_position):
        """Goto position"""
        target_with_offset = target_position + 0x800000
        hex_target = self.format_hex_data(target_with_offset, 3)
        
        current = self.get_position(axis)
        if current is None:
            return False
        
        direction_cw = target_position > current
        
        # Set goto mode
        if not self.set_motion_mode(axis, goto_mode=True, direction_cw=direction_cw):
            return False
        
        # Set target
        cmd = f":S{axis}{hex_target}"
        response = self.send_command(cmd)
        if not response or not response.startswith('='):
            return False
        
        # Start
        return self.start_motion(axis)
    
    def close(self):
        """Close socket"""
        self.sock.close()


class TelescopeGUI:
    """Working GUI for GTi 150P"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("SkyWatcher GTi Controller - Working Version")
        self.root.geometry("1000x700")
        
        self.config = Config()
        self.protocol = None
        self.connected = False
        
        self.update_thread = None
        self.update_running = False
        
        self.create_widgets()
        self.bind_keyboard()
    
    def create_widgets(self):
        """Create UI"""
        # Create notebook
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Control tab
        control_tab = ttk.Frame(notebook)
        notebook.add(control_tab, text="Control")
        
        # Connection
        conn_frame = ttk.LabelFrame(control_tab, text="Connection", padding=10)
        conn_frame.grid(row=0, column=0, columnspan=3, sticky='ew', padx=5, pady=5)
        
        ttk.Label(conn_frame, text="IP:").grid(row=0, column=0)
        self.ip_entry = ttk.Entry(conn_frame, width=15)
        self.ip_entry.insert(0, self.config.get('connection', 'ip'))
        self.ip_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2)
        self.port_entry = ttk.Entry(conn_frame, width=8)
        self.port_entry.insert(0, "11880")
        self.port_entry.grid(row=0, column=3, padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=4, padx=5)
        
        self.status_label = ttk.Label(conn_frame, text="Disconnected", foreground="red")
        self.status_label.grid(row=0, column=5, padx=10)
        
        # Direction controls
        dir_frame = ttk.LabelFrame(control_tab, text="Direction Control", padding=10)
        dir_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        
        ttk.Button(dir_frame, text="↑\nUP", command=lambda: self.move('up')).grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        ttk.Button(dir_frame, text="←\nLEFT", command=lambda: self.move('left')).grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
        ttk.Button(dir_frame, text="STOP", command=self.stop_all).grid(row=1, column=1, padx=5, pady=5, sticky='nsew')
        ttk.Button(dir_frame, text="→\nRIGHT", command=lambda: self.move('right')).grid(row=1, column=2, padx=5, pady=5, sticky='nsew')
        ttk.Button(dir_frame, text="↓\nDOWN", command=lambda: self.move('down')).grid(row=2, column=1, padx=5, pady=5, sticky='nsew')
        
        # E-Stop
        self.estop_btn = ttk.Button(dir_frame, text="🛑 EMERGENCY STOP", command=self.emergency_stop)
        self.estop_btn.grid(row=3, column=0, columnspan=3, sticky='ew', pady=10)
        
        # Speed control
        ttk.Label(dir_frame, text="Speed (°/sec):").grid(row=4, column=0, sticky='e', pady=5)
        self.speed_var = tk.DoubleVar(value=self.config.get('speed', 'default'))
        self.speed_scale = ttk.Scale(dir_frame, from_=self.config.get('speed', 'min'),
                                     to=self.config.get('speed', 'max'),
                                     variable=self.speed_var, orient='horizontal')
        self.speed_scale.grid(row=4, column=1, sticky='ew', pady=5)
        
        self.speed_label = ttk.Label(dir_frame, text=f"{self.speed_var.get():.2f}")
        self.speed_label.grid(row=4, column=2, sticky='w', padx=5)
        self.speed_var.trace('w', lambda *args: self.speed_label.configure(text=f"{self.speed_var.get():.2f}"))
        
        ttk.Label(dir_frame, text="Keys: W/A/S/D, Space=Stop, ESC=E-Stop", 
                 font=('Arial', 8)).grid(row=5, column=0, columnspan=3, pady=5)
        
        # Preset positions
        preset_frame = ttk.LabelFrame(control_tab, text="Preset Positions", padding=10)
        preset_frame.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)
        
        ttk.Button(preset_frame, text="Go to Home", command=self.goto_home, width=20).pack(pady=5)
        ttk.Button(preset_frame, text="Set Current as Home", command=self.set_home, width=20).pack(pady=5)
        ttk.Button(preset_frame, text="Go to Stow", command=self.goto_stow, width=20).pack(pady=5)
        ttk.Button(preset_frame, text="Set Current as Stow", command=self.set_stow, width=20).pack(pady=5)
        ttk.Separator(preset_frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Button(preset_frame, text="Set Position to Zero", command=self.zero_position, width=20).pack(pady=5)
        
        # Position display
        pos_frame = ttk.LabelFrame(control_tab, text="Position Display", padding=10)
        pos_frame.grid(row=1, column=2, sticky='nsew', padx=5, pady=5)
        
        self.show_pos_var = tk.BooleanVar(value=self.config.get('display', 'show_positions'))
        ttk.Checkbutton(pos_frame, text="Show Positions", variable=self.show_pos_var,
                       command=self.toggle_position_display).pack(anchor='w', pady=5)
        
        ttk.Label(pos_frame, text="Format:").pack(anchor='w', pady=5)
        self.pos_format_var = tk.StringVar(value=self.config.get('display', 'position_format'))
        
        for text, value in [('Degrees', 'degrees'), ('Raw Counts', 'raw'), 
                           ('Both', 'both'), ('Coordinates', 'coordinates')]:
            ttk.Radiobutton(pos_frame, text=text, variable=self.pos_format_var,
                          value=value, command=self.update_position_display).pack(anchor='w')
        
        self.pos_display_frame = ttk.Frame(pos_frame)
        self.pos_display_frame.pack(fill='both', expand=True, pady=10)
        
        self.create_position_labels()
        
        # Status tab
        status_tab = ttk.Frame(notebook)
        notebook.add(status_tab, text="Status")
        
        auto_frame = ttk.Frame(status_tab)
        auto_frame.pack(fill='x', padx=10, pady=10)
        
        self.auto_update_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(auto_frame, text="Auto-update (1 Hz)", 
                       variable=self.auto_update_var,
                       command=self.toggle_auto_update).pack(side='left', padx=5)
        
        ttk.Button(auto_frame, text="Refresh Now", command=self.refresh_status).pack(side='left', padx=20)
        
        self.status_text = scrolledtext.ScrolledText(status_tab, height=25, width=90, font=('Courier', 10))
        self.status_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Info tab
        info_tab = ttk.Frame(notebook)
        notebook.add(info_tab, text="Mount Info")
        
        ttk.Button(info_tab, text="Query Mount Information", 
                  command=self.query_system_info).pack(pady=10)
        
        self.info_text = scrolledtext.ScrolledText(info_tab, height=25, width=90, font=('Courier', 10))
        self.info_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Log
        log_frame = ttk.LabelFrame(info_tab, text="Command Log", padding=5)
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=90, font=('Courier', 9))
        self.log_text.pack(fill='both', expand=True)
        
        # Configure grid weights
        control_tab.columnconfigure(0, weight=1)
        control_tab.columnconfigure(1, weight=1)
        control_tab.columnconfigure(2, weight=1)
        control_tab.rowconfigure(1, weight=1)
    
    def create_position_labels(self):
        """Create position labels based on format"""
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
    
    def bind_keyboard(self):
        """Bind keyboard controls"""
        self.root.bind("<w>", lambda e: self.move('up'))
        self.root.bind("<s>", lambda e: self.move('down'))
        self.root.bind("<a>", lambda e: self.move('left'))
        self.root.bind("<d>", lambda e: self.move('right'))
        self.root.bind("<Up>", lambda e: self.move('up'))
        self.root.bind("<Down>", lambda e: self.move('down'))
        self.root.bind("<Left>", lambda e: self.move('left'))
        self.root.bind("<Right>", lambda e: self.move('right'))
        self.root.bind("<space>", lambda e: self.stop_all())
        self.root.bind("<Escape>", lambda e: self.emergency_stop())
        self.root.bind("<plus>", lambda e: self.adjust_speed(0.5))
        self.root.bind("<minus>", lambda e: self.adjust_speed(-0.5))
    
    def log(self, message):
        """Add to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] {message}\n")
        self.log_text.see('end')
    
    def toggle_connection(self):
        """Connect/disconnect"""
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
            
            self.protocol = SkyWatcherSimple(ip, port, 2.0)
            
            try:
                version = self.protocol.get_version()
                if version and version.startswith('='):
                    self.connected = True
                    self.connect_btn.configure(text="Disconnect")
                    self.status_label.configure(text="Connected (Simple Protocol)", foreground="green")
                    self.log(f"Connected to {ip}:{port}")
                    self.log(f"Version response: {version}")
                    
                    self.protocol.initialization_done()
                    self.protocol.get_counts_per_revolution(self.protocol.AXIS_AZ)
                    self.protocol.get_counts_per_revolution(self.protocol.AXIS_ALT)
                    self.protocol.get_timer_freq()
                else:
                    messagebox.showerror("Connection Error", "Could not connect to telescope")
                    self.protocol.close()
                    self.protocol = None
            except Exception as e:
                messagebox.showerror("Connection Error", str(e))
                if self.protocol:
                    self.protocol.close()
                self.protocol = None
    
    def move(self, direction):
        """Move"""
        if not self.connected:
            return
        
        speed = self.speed_var.get()
        
        if direction == 'up':
            self.protocol.slew_fixed_rate(self.protocol.AXIS_ALT, True, speed)
            self.log(f"Moving UP at {speed:.2f}°/sec")
        elif direction == 'down':
            self.protocol.slew_fixed_rate(self.protocol.AXIS_ALT, False, speed)
            self.log(f"Moving DOWN at {speed:.2f}°/sec")
        elif direction == 'left':
            self.protocol.slew_fixed_rate(self.protocol.AXIS_AZ, False, speed)
            self.log(f"Moving LEFT at {speed:.2f}°/sec")
        elif direction == 'right':
            self.protocol.slew_fixed_rate(self.protocol.AXIS_AZ, True, speed)
            self.log(f"Moving RIGHT at {speed:.2f}°/sec")
    
    def stop_all(self):
        """Stop all"""
        if not self.connected:
            return
        
        self.protocol.stop_motion(self.protocol.AXIS_AZ)
        self.protocol.stop_motion(self.protocol.AXIS_ALT)
        self.log("Stopped all motion")
    
    def emergency_stop(self):
        """Emergency stop"""
        if not self.connected:
            return
        
        self.protocol.instant_stop(self.protocol.AXIS_AZ)
        self.protocol.instant_stop(self.protocol.AXIS_ALT)
        self.log("⚠️ EMERGENCY STOP")
        messagebox.showwarning("Emergency Stop", "Emergency stop activated!")
    
    def goto_home(self):
        """Go to home"""
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
        """Set home"""
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
            
            self.log(f"HOME set: Az={az_deg:.2f}°, Alt={alt_deg:.2f}°")
            messagebox.showinfo("Home Set", f"Home set to:\nAz: {az_deg:.2f}°\nAlt: {alt_deg:.2f}°")
    
    def goto_stow(self):
        """Go to stow"""
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
        """Set stow"""
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
            
            self.log(f"STOW set: Az={az_deg:.2f}°, Alt={alt_deg:.2f}°")
            messagebox.showinfo("Stow Set", f"Stow set to:\nAz: {az_deg:.2f}°\nAlt: {alt_deg:.2f}°")
    
    def zero_position(self):
        """Zero position"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        if messagebox.askyesno("Confirm", "Set current position to 0,0?"):
            self.protocol.set_position(self.protocol.AXIS_AZ, 0)
            self.protocol.set_position(self.protocol.AXIS_ALT, 0)
            self.log("Position set to 0,0")
    
    def toggle_position_display(self):
        """Toggle position display"""
        self.config.set('display', 'show_positions', self.show_pos_var.get())
        self.create_position_labels()
    
    def update_position_display(self):
        """Update format"""
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
                az_deg = az_deg % 360
                coord_text = f"Az: {az_deg:.4f}°\nAlt: {alt_deg:.4f}°"
                self.coord_label.configure(text=coord_text)
    
    def refresh_status(self):
        """Refresh status"""
        if not self.connected:
            return
        
        self.status_text.delete('1.0', 'end')
        
        for axis_name, axis_id in [("AZIMUTH", '1'), ("ALTITUDE", '2')]:
            self.status_text.insert('end', f"\n{'='*50}\n")
            self.status_text.insert('end', f"{axis_name} AXIS\n")
            self.status_text.insert('end', f"{'='*50}\n\n")
            
            pos = self.protocol.get_position(axis_id)
            if pos is not None:
                deg = self.protocol.counts_to_degrees(pos, axis_id)
                self.status_text.insert('end', f"Position (counts): {pos:,} (0x{pos:08X})\n")
                if deg is not None:
                    self.status_text.insert('end', f"Position (degrees): {deg:.6f}°\n")
            
            status = self.protocol.get_status(axis_id)
            if status:
                self.status_text.insert('end', f"\nStatus:\n")
                self.status_text.insert('end', f"  Running:     {status['running']}\n")
                self.status_text.insert('end', f"  Initialized: {status['initialized']}\n")
                self.status_text.insert('end', f"  Mode:        {'Tracking' if status['tracking_mode'] else 'Goto'}\n")
                self.status_text.insert('end', f"  Direction:   {'CCW' if status['ccw'] else 'CW'}\n")
        
        self.update_positions()
    
    def toggle_auto_update(self):
        """Toggle auto-update"""
        if self.auto_update_var.get():
            self.update_running = True
            self.update_thread = threading.Thread(target=self.auto_update_loop, daemon=True)
            self.update_thread.start()
            self.log("Auto-update enabled")
        else:
            self.update_running = False
            if self.update_thread:
                self.update_thread.join(timeout=2)
            self.log("Auto-update disabled")
    
    def auto_update_loop(self):
        """Auto-update loop"""
        while self.update_running and self.connected:
            self.root.after(0, self.refresh_status)
            time.sleep(1.0)
    
    def query_system_info(self):
        """Query system info"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Connect first")
            return
        
        self.info_text.delete('1.0', 'end')
        
        for axis_name, axis_id in [("AZIMUTH", '1'), ("ALTITUDE", '2')]:
            self.info_text.insert('end', f"\n{'='*60}\n")
            self.info_text.insert('end', f"{axis_name} AXIS (ID: {axis_id})\n")
            self.info_text.insert('end', f"{'='*60}\n\n")
            
            version = self.protocol.get_version()
            self.info_text.insert('end', f"Version Response: {version}\n")
            
            cpr = self.protocol.get_counts_per_revolution(axis_id)
            if cpr:
                self.info_text.insert('end', f"Counts Per Revolution: {cpr:,} (0x{cpr:08X})\n")
                self.info_text.insert('end', f"Resolution: {360.0/cpr:.8f} deg/count\n")
            
            if axis_id == '1':
                timer_freq = self.protocol.get_timer_freq()
                if timer_freq:
                    self.info_text.insert('end', f"\nTimer Frequency: {timer_freq:,} Hz\n")
            
            pos = self.protocol.get_position(axis_id)
            if pos is not None:
                deg = self.protocol.counts_to_degrees(pos, axis_id)
                self.info_text.insert('end', f"\nCurrent Position: {pos:,} (0x{pos:08X})\n")
                if deg is not None:
                    self.info_text.insert('end', f"Current Position: {deg:.6f}°\n")
            
            status = self.protocol.get_status(axis_id)
            if status:
                self.info_text.insert('end', f"\nStatus:\n")
                self.info_text.insert('end', f"  Running:     {status['running']}\n")
                self.info_text.insert('end', f"  Initialized: {status['initialized']}\n")
        
        self.log("System information queried")
    
    def adjust_speed(self, delta):
        """Adjust speed"""
        new_speed = max(self.config.get('speed', 'min'),
                       min(self.config.get('speed', 'max'),
                           self.speed_var.get() + delta))
        self.speed_var.set(new_speed)
    
    def on_closing(self):
        """Handle close"""
        if self.connected:
            self.stop_all()
            if self.protocol:
                self.protocol.close()
        
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
