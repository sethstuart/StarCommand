#!/usr/bin/env python3
"""
SkyWatcher GTi Controller - ULTRA SIMPLE VERSION
Uses ONLY commands that work on your mount
"""

import socket
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime

class SimpleProtocol:
    """Ultra-simple protocol using only verified commands"""
    
    def __init__(self, ip='192.168.4.1', port=11880, log_callback=None):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2.0)
        self.log = log_callback
        
        self.AXIS_AZ = '1'
        self.AXIS_ALT = '2'
    
    def send(self, cmd):
        """Send command"""
        if not cmd.endswith('\r'):
            cmd += '\r'
        
        if self.log:
            self.log(f"→ {repr(cmd)}")
        
        try:
            self.sock.sendto(cmd.encode('ascii'), (self.ip, self.port))
            data, _ = self.sock.recvfrom(1024)
            resp = data.decode('ascii').strip()
            
            if self.log:
                self.log(f"← {repr(resp)}")
            
            return resp
        except Exception as e:
            if self.log:
                self.log(f"✗ {e}")
            return None
    
    def connect(self):
        """Test connection"""
        resp = self.send(':e1')
        return resp and resp.startswith('=')
    
    def get_position(self, axis):
        """Get position"""
        resp = self.send(f':j{axis}')
        if resp and resp.startswith('='):
            hex_str = resp[1:].replace('\r', '')
            reversed_str = ''.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)][::-1])
            try:
                return int(reversed_str, 16) - 0x800000
            except:
                return None
        return None
    
    def stop(self, axis):
        """Stop axis"""
        resp = self.send(f':K{axis}')
        return resp and resp.startswith('=')
    
    def instant_stop(self, axis):
        """Emergency stop"""
        resp = self.send(f':L{axis}')
        return resp and resp.startswith('=')
    
    # Try GOTO command instead of tracking mode
    def goto_slew(self, axis, steps_per_sec):
        """Try goto command format"""
        # Calculate target position far away to simulate continuous motion
        current = self.get_position(axis)
        if current is None:
            return False
        
        # Move "far" in the direction (simulate continuous)
        target = current + int(steps_per_sec * 3600)  # 1 hour worth of steps
        target_with_offset = (target + 0x800000) & 0xFFFFFF
        
        # Format as hex LSB first
        hex_str = f"{target_with_offset:06X}"
        hex_target = ''.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)][::-1])
        
        if self.log:
            self.log(f"  Trying GOTO to {target} (0x{hex_target})")
        
        # Try simple goto format
        resp = self.send(f':S{axis}{hex_target}')
        if not (resp and resp.startswith('=')):
            return False
        
        # Try to start motion
        resp = self.send(f':J{axis}')
        return resp and resp.startswith('=')
    
    def close(self):
        """Close socket"""
        self.sock.close()


class TestGUI:
    """Simple test GUI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("SkyWatcher Test - Simple Commands Only")
        self.root.geometry("800x600")
        
        self.protocol = None
        self.connected = False
        
        # Connection frame
        conn_frame = ttk.LabelFrame(root, text="Connection", padding=10)
        conn_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(conn_frame, text="IP:").grid(row=0, column=0)
        self.ip_entry = ttk.Entry(conn_frame, width=15)
        self.ip_entry.insert(0, "192.168.4.1")
        self.ip_entry.grid(row=0, column=1, padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect)
        self.connect_btn.grid(row=0, column=2, padx=5)
        
        self.status_label = ttk.Label(conn_frame, text="Disconnected", foreground="red")
        self.status_label.grid(row=0, column=3, padx=10)
        
        # Test buttons
        test_frame = ttk.LabelFrame(root, text="Test Commands", padding=10)
        test_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        ttk.Button(test_frame, text="Test 1: Query Position", 
                  command=self.test_position).pack(pady=5)
        ttk.Button(test_frame, text="Test 2: Try GOTO Slew (UP)", 
                  command=lambda: self.test_goto_slew('up')).pack(pady=5)
        ttk.Button(test_frame, text="Test 3: Try GOTO Slew (DOWN)", 
                  command=lambda: self.test_goto_slew('down')).pack(pady=5)
        ttk.Button(test_frame, text="Test 4: Try GOTO Slew (LEFT)", 
                  command=lambda: self.test_goto_slew('left')).pack(pady=5)
        ttk.Button(test_frame, text="Test 5: Try GOTO Slew (RIGHT)", 
                  command=lambda: self.test_goto_slew('right')).pack(pady=5)
        ttk.Button(test_frame, text="STOP ALL", 
                  command=self.stop_all).pack(pady=5)
        ttk.Button(test_frame, text="EMERGENCY STOP", 
                  command=self.estop).pack(pady=5)
        
        # Log
        log_frame = ttk.LabelFrame(root, text="Log", padding=5)
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=90, font=('Courier', 9))
        self.log_text.pack(fill='both', expand=True)
    
    def log(self, msg):
        """Add to log"""
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.insert('end', f"[{ts}] {msg}\n")
        self.log_text.see('end')
    
    def connect(self):
        """Connect"""
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
        self.protocol = SimpleProtocol(ip, 11880, self.log)
        
        if self.protocol.connect():
            self.connected = True
            self.connect_btn.configure(text="Disconnect")
            self.status_label.configure(text="Connected", foreground="green")
            self.log("✓ Connected!")
        else:
            messagebox.showerror("Error", "Could not connect")
            self.protocol = None
    
    def test_position(self):
        """Test position query"""
        if not self.connected:
            return
        
        self.log("=== Testing Position Query ===")
        az = self.protocol.get_position(self.protocol.AXIS_AZ)
        alt = self.protocol.get_position(self.protocol.AXIS_ALT)
        self.log(f"Azimuth: {az}")
        self.log(f"Altitude: {alt}")
    
    def test_goto_slew(self, direction):
        """Test goto command for slewing"""
        if not self.connected:
            return
        
        self.log(f"=== Testing GOTO Slew {direction.upper()} ===")
        
        if direction in ['up', 'down']:
            axis = self.protocol.AXIS_ALT
            steps_per_sec = 100 if direction == 'up' else -100
        else:
            axis = self.protocol.AXIS_AZ
            steps_per_sec = 100 if direction == 'right' else -100
        
        result = self.protocol.goto_slew(axis, steps_per_sec)
        
        if result:
            self.log("✓ GOTO command accepted! Mount should be moving.")
            self.log("  Watch the mount - is it moving?")
        else:
            self.log("✗ GOTO command failed")
    
    def stop_all(self):
        """Stop all"""
        if not self.connected:
            return
        
        self.log("=== STOP ALL ===")
        self.protocol.stop(self.protocol.AXIS_AZ)
        self.protocol.stop(self.protocol.AXIS_ALT)
        self.log("✓ Stop commands sent")
    
    def estop(self):
        """Emergency stop"""
        if not self.connected:
            return
        
        self.log("=== EMERGENCY STOP ===")
        self.protocol.instant_stop(self.protocol.AXIS_AZ)
        self.protocol.instant_stop(self.protocol.AXIS_ALT)
        self.log("✓ Emergency stop sent")


if __name__ == '__main__':
    root = tk.Tk()
    app = TestGUI(root)
    root.mainloop()
