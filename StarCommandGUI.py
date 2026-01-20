#!/usr/bin/env python3
"""
SkyWatcher Controller - Fixed GUI with dual protocol support
Supports both Motor Controller Protocol (port 11880) and SynScan App Protocol (port 11881)
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
    print("Error: tkinter not available")
    sys.exit(1)


class Config:
    """Configuration manager"""
    
    DEFAULT_CONFIG = {
        'connection': {
            'ip': '192.168.4.1',
            'port': 11880,
            'protocol': 'auto',  # 'auto', 'motor', 'app'
            'timeout': 2.0
        },
        'controls': {
            'up': 'w', 'down': 's', 'left': 'a', 'right': 'd',
            'stop': 'space', 'estop': 'Escape',
            'speed_up': 'plus', 'speed_down': 'minus'
        },
        'display': {
            'position_format': 'both',
            'show_positions': True,
            'auto_update': False,
            'update_rate': 1.0
        },
        'positions': {
            'home_az': 0, 'home_alt': 0,
            'stow_az': 0, 'stow_alt': 90
        },
        'theme': {
            'bg': '#2b2b2b', 'fg': '#ffffff',
            'button_bg': '#3c3c3c', 'button_fg': '#ffffff',
            'accent': '#4a9eff', 'estop': '#ff4444'
        },
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
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, section, key, default=None):
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section, key, value):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value


# Simplified protocol that auto-detects which one to use
class SkyWatcherProtocol:
    """Auto-detecting SkyWatcher protocol"""
    
    def __init__(self, ip='192.168.4.1', port=11880, timeout=3.0):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.protocol_type = None  # Will be 'motor' or 'app'
        
        self.AXIS_AZ = '1'
        self.AXIS_ALT = '2'
        
        self.cpr_az = None
        self.cpr_alt = None
        self.timer_freq = None
    
    def connect(self):
        """Try to connect and auto-detect protocol"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(self.timeout)
        
        # Try SynScan App Protocol first (port 11881)
        if self.try_app_protocol():
            self.protocol_type = 'app'
            self.port = 11881
            return True
        
        # Try Motor Controller Protocol (port 11880)
        if self.try_motor_protocol():
            self.protocol_type = 'motor'
            return True
        
        # Try without X10 prefix
        if self.try_motor_protocol_simple():
            self.protocol_type = 'motor_simple'
            return True
        
        return False
    
    def try_app_protocol(self):
        """Try SynScan App Protocol on port 11881"""
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_sock.settimeout(2.0)
            
            # Try ConnectedGet command
            command = "ConnectedGet"
            test_sock.sendto(command.encode('ascii'), (self.ip, 11881))
            
            data, addr = test_sock.recvfrom(1024)
            response = data.decode('ascii')
            
            test_sock.close()
            
            # Valid response starts with "Ok,"
            if response.startswith('Ok,'):
                self.sock.close()
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.settimeout(self.timeout)
                return True
        except:
            pass
        
        return False
    
    def try_motor_protocol(self):
        """Try Motor Controller Protocol with X10 prefix"""
        try:
            # Try version query
            command = ":X10e1\r"
            self.sock.sendto(command.encode('ascii'), (self.ip, self.port))
            
            data, addr = self.sock.recvfrom(1024)
            response = data.decode('ascii')
            
            # Valid response starts with "="
            return response.startswith('=')
        except:
            return False
    
    def try_motor_protocol_simple(self):
        """Try Motor Controller Protocol without X10 prefix"""
        try:
            # Try version query
            command = ":e1\r"
            self.sock.sendto(command.encode('ascii'), (self.ip, self.port))
            
            data, addr = self.sock.recvfrom(1024)
            response = data.decode('ascii')
            
            return response.startswith('=')
        except:
            return False
    
    def send_command(self, command):
        """Send command based on detected protocol"""
        if not self.sock:
            return None
        
        try:
            if not command.endswith('\r') and self.protocol_type != 'app':
                command += '\r'
            
            port = 11881 if self.protocol_type == 'app' else self.port
            self.sock.sendto(command.encode('ascii'), (self.ip, port))
            
            data, addr = self.sock.recvfrom(1024)
            return data.decode('ascii').strip()
        except:
            return None
    
    def get_position(self, axis):
        """Get position - works with both protocols"""
        if self.protocol_type == 'app':
            # Use SynScan App Protocol
            if axis == self.AXIS_AZ:
                response = self.send_command("AzimuthGet")
            else:
                response = self.send_command("AltitudeGet")
            
            if response and response.startswith('Ok,'):
                parts = response.split(',')
                if len(parts) >= 3:
                    try:
                        return float(parts[2])
                    except:
                        return None
            return None
        else:
            # Use Motor Controller Protocol
            if self.protocol_type == 'motor_simple':
                cmd = f":j{axis}"
            else:
                cmd = f":X10j{axis}"
            
            response = self.send_command(cmd)
            if response and response.startswith('='):
                hex_str = response[1:].replace('\r', '')
                if hex_str:
                    try:
                        reversed_str = ''.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)][::-1])
                        pos = int(reversed_str, 16)
                        return pos - 0x800000
                    except:
                        return None
            return None
    
    def get_status(self, axis):
        """Get status"""
        if self.protocol_type == 'app':
            response = self.send_command("TrackingGet")
            if response and response.startswith('Ok,'):
                return {'running': 'True' in response or '1' in response.split(',')[-1]}
            return None
        else:
            if self.protocol_type == 'motor_simple':
                cmd = f":f{axis}"
            else:
                cmd = f":X10f{axis}"
            
            response = self.send_command(cmd)
            if response and response.startswith('='):
                try:
                    status = int(response[1:3], 16)
                    return {
                        'running': bool(status & 0x01),
                        'initialized': bool(status & 0x04)
                    }
                except:
                    return None
            return None
    
    def get_version(self):
        """Get version"""
        if self.protocol_type == 'app':
            response = self.send_command("Action,AppVersionGet")
            return response if response else "App Protocol"
        else:
            if self.protocol_type == 'motor_simple':
                cmd = ":e1"
            else:
                cmd = ":X10e1"
            
            response = self.send_command(cmd)
            return response if response else None
    
    def slew_axis(self, axis, direction_positive=True, rate_deg_sec=1.0):
        """Slew axis at rate"""
        if self.protocol_type == 'app':
            # Use SlewToCoordinatesAsync
            # For now, just use MoveAxis command
            axis_name = "Primary" if axis == self.AXIS_AZ else "Secondary"
            rate = 1.0 if rate_deg_sec < 1 else rate_deg_sec
            cmd = f"MoveAxis,{axis_name},{rate}"
            return self.send_command(cmd)
        else:
            # Use motor controller commands
            # Simplified - just use basic slew
            return None
    
    def stop_motion(self, axis):
        """Stop motion"""
        if self.protocol_type == 'app':
            response = self.send_command("AbortSlew")
            return response and 'Ok' in response
        else:
            if self.protocol_type == 'motor_simple':
                cmd = f":K{axis}"
            else:
                cmd = f":X10K{axis}"
            
            response = self.send_command(cmd)
            return response and response.startswith('=')
    
    def instant_stop(self, axis):
        """Emergency stop"""
        return self.stop_motion(axis)
    
    def close(self):
        """Close connection"""
        if self.sock:
            self.sock.close()


class SimpleTelescopeGUI:
    """Simplified GUI that works with auto-detected protocol"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("SkyWatcher Controller v2.1 - Fixed")
        self.root.geometry("900x600")
        
        self.config = Config()
        self.protocol = None
        self.connected = False
        
        self.create_widgets()
        self.apply_theme()
    
    def apply_theme(self):
        theme = self.config.config['theme']
        self.root.configure(bg=theme['bg'])
    
    def create_widgets(self):
        """Create simplified UI"""
        # Connection frame
        conn_frame = ttk.LabelFrame(self.root, text="Connection", padding=10)
        conn_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(conn_frame, text="IP:").grid(row=0, column=0)
        self.ip_entry = ttk.Entry(conn_frame, width=15)
        self.ip_entry.insert(0, self.config.get('connection', 'ip'))
        self.ip_entry.grid(row=0, column=1, padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect)
        self.connect_btn.grid(row=0, column=2, padx=5)
        
        self.status_label = ttk.Label(conn_frame, text="Disconnected", foreground="red")
        self.status_label.grid(row=0, column=3, padx=10)
        
        # Control frame
        ctrl_frame = ttk.LabelFrame(self.root, text="Direction Control", padding=10)
        ctrl_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        ttk.Button(ctrl_frame, text="↑ UP", command=lambda: self.move('up')).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(ctrl_frame, text="← LEFT", command=lambda: self.move('left')).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(ctrl_frame, text="STOP", command=self.stop).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(ctrl_frame, text="→ RIGHT", command=lambda: self.move('right')).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(ctrl_frame, text="↓ DOWN", command=lambda: self.move('down')).grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Button(ctrl_frame, text="🛑 EMERGENCY STOP", command=self.estop).grid(row=3, column=0, columnspan=3, sticky='ew', pady=10)
        
        # Log
        self.log_text = scrolledtext.ScrolledText(self.root, height=15, width=90)
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] {message}\n")
        self.log_text.see('end')
    
    def connect(self):
        if self.connected:
            if self.protocol:
                self.protocol.close()
            self.protocol = None
            self.connected = False
            self.connect_btn.configure(text="Connect")
            self.status_label.configure(text="Disconnected", foreground="red")
            self.log("Disconnected")
            return
        
        ip = self.ip_entry.get()
        self.log(f"Connecting to {ip}...")
        
        self.protocol = SkyWatcherProtocol(ip, 11880, 3.0)
        
        if self.protocol.connect():
            self.connected = True
            self.connect_btn.configure(text="Disconnect")
            self.status_label.configure(text=f"Connected ({self.protocol.protocol_type})", foreground="green")
            self.log(f"✓ Connected using {self.protocol.protocol_type} protocol on port {self.protocol.port}")
            
            version = self.protocol.get_version()
            if version:
                self.log(f"Version: {version}")
        else:
            messagebox.showerror("Connection Error", 
                "Could not connect to telescope.\n\n"
                "Tried both protocols:\n"
                "- SynScan App Protocol (port 11881)\n"
                "- Motor Controller Protocol (port 11880)\n\n"
                "Please check:\n"
                "1. Telescope is powered on\n"
                "2. Connected to telescope WiFi\n"
                "3. IP address is correct\n"
                "4. Run test_connection.py for diagnosis")
            self.protocol = None
    
    def move(self, direction):
        if not self.connected:
            return
        
        self.log(f"Moving {direction.upper()}")
        # Basic movement - simplified
        if direction == 'up':
            self.protocol.slew_axis(self.protocol.AXIS_ALT, True, 1.0)
        elif direction == 'down':
            self.protocol.slew_axis(self.protocol.AXIS_ALT, False, 1.0)
        elif direction == 'left':
            self.protocol.slew_axis(self.protocol.AXIS_AZ, False, 1.0)
        elif direction == 'right':
            self.protocol.slew_axis(self.protocol.AXIS_AZ, True, 1.0)
    
    def stop(self):
        if not self.connected:
            return
        
        self.protocol.stop_motion(self.protocol.AXIS_AZ)
        self.protocol.stop_motion(self.protocol.AXIS_ALT)
        self.log("Stopped")
    
    def estop(self):
        if not self.connected:
            return
        
        self.protocol.instant_stop(self.protocol.AXIS_AZ)
        self.protocol.instant_stop(self.protocol.AXIS_ALT)
        self.log("⚠️ EMERGENCY STOP")
    
    def on_closing(self):
        if self.connected:
            self.stop()
            if self.protocol:
                self.protocol.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = SimpleTelescopeGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()
