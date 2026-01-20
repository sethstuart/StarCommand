#!/usr/bin/env python3
"""
Sky-Watcher Telescope Controller - Enhanced CLI Version
Command-line interface with advanced features

Version: 2.0
"""

import socket
import time
import sys
import json
import os
from pathlib import Path
from datetime import datetime


class Config:
    """Simple configuration manager for CLI"""
    
    DEFAULT_CONFIG = {
        'connection': {'ip': '192.168.4.1', 'port': 11880, 'timeout': 2.0},
        'speed': {'default': 1.0, 'min': 0.1, 'max': 10.0},
        'positions': {'home_az': 0, 'home_alt': 0, 'stow_az': 0, 'stow_alt': 90},
        'display': {'position_format': 'both'}  # 'degrees', 'raw', 'both'
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
            print(f"Warning: Could not save config: {e}")
    
    def get(self, section, key, default=None):
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section, key, value):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value


class SkyWatcherProtocol:
    """SkyWatcher protocol implementation"""
    
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
        if not command.endswith('\r'):
            command += '\r'
        try:
            self.sock.sendto(command.encode('ascii'), (self.ip, self.port))
            data, addr = self.sock.recvfrom(1024)
            return data.decode('ascii').strip()
        except:
            return None
    
    def parse_hex_response(self, response):
        if not response or not response.startswith('='):
            return None
        hex_str = response[1:].replace('\r', '')
        if not hex_str:
            return None
        reversed_str = ''.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)][::-1])
        try:
            return int(reversed_str, 16)
        except:
            return None
    
    def format_hex_data(self, value, bytes_count=3):
        hex_str = f"{value:0{bytes_count*2}X}"
        return ''.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)][::-1])
    
    def get_position(self, axis):
        cmd = f":X10j{axis}"
        response = self.send_command(cmd)
        if response:
            pos = self.parse_hex_response(response)
            if pos is not None:
                return pos - 0x800000
        return None
    
    def set_position(self, axis, position):
        pos_with_offset = position + 0x800000
        hex_pos = self.format_hex_data(pos_with_offset, 3)
        cmd = f":X10E{axis}{hex_pos}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def set_motion_mode(self, axis, goto_mode=False, direction_cw=True, high_speed=False):
        mode_byte = 0
        if not goto_mode:
            mode_byte |= 0x01
        if not direction_cw:
            mode_byte |= 0x02
        if high_speed and not goto_mode:
            mode_byte |= 0x04
        elif not high_speed and goto_mode:
            mode_byte |= 0x04
        mode_hex = f"{mode_byte:02X}"
        direction_byte = 0
        if not direction_cw:
            direction_byte |= 0x01
        dir_hex = f"{direction_byte:02X}"
        cmd = f":X10G{axis}{mode_hex}{dir_hex}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def set_step_period(self, axis, period):
        hex_period = self.format_hex_data(period, 3)
        cmd = f":X10I{axis}{hex_period}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def start_motion(self, axis):
        cmd = f":X10J{axis}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def stop_motion(self, axis):
        cmd = f":X10K{axis}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def instant_stop(self, axis):
        cmd = f":X10L{axis}"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def get_counts_per_revolution(self, axis):
        cmd = f":X10a{axis}"
        response = self.send_command(cmd)
        cpr = self.parse_hex_response(response)
        if cpr and axis == self.AXIS_AZ:
            self.cpr_az = cpr
        elif cpr and axis == self.AXIS_ALT:
            self.cpr_alt = cpr
        return cpr
    
    def get_timer_freq(self):
        if self.timer_freq:
            return self.timer_freq
        cmd = f":X10b1"
        response = self.send_command(cmd)
        freq = self.parse_hex_response(response)
        if freq:
            self.timer_freq = freq
        return freq
    
    def get_status(self, axis):
        cmd = f":X10f{axis}"
        response = self.send_command(cmd)
        if not response or not response.startswith('='):
            return None
        status_hex = response[1:3]
        try:
            status = int(status_hex, 16)
            return {
                'running': bool(status & 0x01),
                'initialized': bool(status & 0x04),
                'tracking_mode': bool(status & 0x01),
                'ccw': bool(status & 0x02)
            }
        except:
            return None
    
    def get_motor_board_version(self, axis):
        cmd = f":X10e{axis}"
        response = self.send_command(cmd)
        if response and response.startswith('='):
            return response[1:].replace('\r', '')
        return None
    
    def initialization_done(self):
        cmd = f":X10F3"
        response = self.send_command(cmd)
        return response and response.startswith('=')
    
    def slew_fixed_rate(self, axis, direction_positive=True, speed_deg_per_sec=1.0):
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
        target_with_offset = target_position + 0x800000
        hex_target = self.format_hex_data(target_with_offset, 3)
        current = self.get_position(axis)
        if current is None:
            return False
        direction_cw = target_position > current
        if not self.set_motion_mode(axis, goto_mode=True, direction_cw=direction_cw):
            return False
        cmd = f":X10S{axis}{hex_target}"
        if not self.send_command(cmd) or not self.send_command(cmd).startswith('='):
            return False
        return self.start_motion(axis)
    
    def counts_to_degrees(self, counts, axis):
        if axis == self.AXIS_AZ:
            cpr = self.cpr_az or self.get_counts_per_revolution(axis)
        else:
            cpr = self.cpr_alt or self.get_counts_per_revolution(axis)
        if not cpr:
            return None
        return (counts / cpr) * 360.0
    
    def degrees_to_counts(self, degrees, axis):
        if axis == self.AXIS_AZ:
            cpr = self.cpr_az or self.get_counts_per_revolution(axis)
        else:
            cpr = self.cpr_alt or self.get_counts_per_revolution(axis)
        if not cpr:
            return None
        return int((degrees / 360.0) * cpr)
    
    def close(self):
        self.sock.close()


def print_banner():
    """Print welcome banner"""
    print("\n" + "="*60)
    print("  SkyWatcher Virtuoso GTi Controller v2.0 - CLI Edition")
    print("="*60 + "\n")


def print_help():
    """Print help"""
    print("\nCOMMANDS:")
    print("  Movement:")
    print("    w/up    - Move UP          s/down  - Move DOWN")
    print("    a/left  - Move LEFT        d/right - Move RIGHT")
    print("    x/stop  - STOP             e/estop - EMERGENCY STOP")
    print("")
    print("  Speed:")
    print("    +       - Increase speed   -       - Decrease speed")
    print("    speed N - Set speed to N degrees/sec")
    print("")
    print("  Position:")
    print("    p       - Show positions   format [degrees|raw|both]")
    print("    zero    - Set position to 0,0")
    print("")
    print("  Presets:")
    print("    home    - Go to home       sethome - Set current as home")
    print("    stow    - Go to stow       setstow - Set current as stow")
    print("")
    print("  Info:")
    print("    status  - Show status      info    - Mount information")
    print("    version - Show version     config  - Show configuration")
    print("")
    print("  Other:")
    print("    help/?  - This help        quit/q  - Exit")
    print("")
    print("TIMED MOVEMENTS:")
    print("  <direction> <seconds>  -  e.g. 'w 2' moves up for 2 seconds")
    print("")


def interactive_mode(controller, config):
    """Interactive control mode"""
    print_banner()
    print(f"Connected to {controller.ip}:{controller.port}")
    
    # Get version
    version = controller.get_motor_board_version('1')
    if version:
        print(f"Motor Board Version: {version}")
    
    # Initialize mount
    controller.initialization_done()
    
    # Cache parameters
    controller.get_counts_per_revolution(controller.AXIS_AZ)
    controller.get_counts_per_revolution(controller.AXIS_ALT)
    controller.get_timer_freq()
    
    print("\nType 'help' for commands, 'quit' to exit")
    print("="*60 + "\n")
    
    current_speed = config.get('speed', 'default')
    position_format = config.get('display', 'position_format')
    
    while True:
        try:
            cmd = input("> ").strip().lower().split()
            
            if not cmd:
                continue
            
            command = cmd[0]
            args = cmd[1:] if len(cmd) > 1 else []
            
            # Exit commands
            if command in ['q', 'quit', 'exit']:
                print("Stopping all motion and exiting...")
                controller.stop_motion(controller.AXIS_AZ)
                controller.stop_motion(controller.AXIS_ALT)
                break
            
            # Help
            elif command in ['help', '?']:
                print_help()
            
            # Movement with optional duration
            elif command in ['w', 'up']:
                duration = float(args[0]) if args else None
                controller.slew_fixed_rate(controller.AXIS_ALT, True, current_speed)
                print(f"Moving UP at {current_speed:.2f}°/sec")
                if duration:
                    time.sleep(duration)
                    controller.stop_motion(controller.AXIS_ALT)
                    print("Stopped")
            
            elif command in ['s', 'down']:
                duration = float(args[0]) if args else None
                controller.slew_fixed_rate(controller.AXIS_ALT, False, current_speed)
                print(f"Moving DOWN at {current_speed:.2f}°/sec")
                if duration:
                    time.sleep(duration)
                    controller.stop_motion(controller.AXIS_ALT)
                    print("Stopped")
            
            elif command in ['a', 'left']:
                duration = float(args[0]) if args else None
                controller.slew_fixed_rate(controller.AXIS_AZ, False, current_speed)
                print(f"Moving LEFT at {current_speed:.2f}°/sec")
                if duration:
                    time.sleep(duration)
                    controller.stop_motion(controller.AXIS_AZ)
                    print("Stopped")
            
            elif command in ['d', 'right']:
                duration = float(args[0]) if args else None
                controller.slew_fixed_rate(controller.AXIS_AZ, True, current_speed)
                print(f"Moving RIGHT at {current_speed:.2f}°/sec")
                if duration:
                    time.sleep(duration)
                    controller.stop_motion(controller.AXIS_AZ)
                    print("Stopped")
            
            # Stop
            elif command in ['x', 'stop']:
                controller.stop_motion(controller.AXIS_AZ)
                controller.stop_motion(controller.AXIS_ALT)
                print("Stopped all motion")
            
            # Emergency stop
            elif command in ['e', 'estop', 'emergency']:
                controller.instant_stop(controller.AXIS_AZ)
                controller.instant_stop(controller.AXIS_ALT)
                print("⚠️  EMERGENCY STOP ACTIVATED")
            
            # Speed
            elif command == '+':
                current_speed = min(config.get('speed', 'max'), current_speed + 0.5)
                print(f"Speed: {current_speed:.2f}°/sec")
            
            elif command == '-':
                current_speed = max(config.get('speed', 'min'), current_speed - 0.5)
                print(f"Speed: {current_speed:.2f}°/sec")
            
            elif command == 'speed':
                if args:
                    try:
                        new_speed = float(args[0])
                        if config.get('speed', 'min') <= new_speed <= config.get('speed', 'max'):
                            current_speed = new_speed
                            print(f"Speed set to {current_speed:.2f}°/sec")
                        else:
                            print(f"Speed must be between {config.get('speed', 'min')} and {config.get('speed', 'max')}")
                    except ValueError:
                        print("Invalid speed value")
                else:
                    print(f"Current speed: {current_speed:.2f}°/sec")
            
            # Position display
            elif command in ['p', 'pos', 'position']:
                az_pos = controller.get_position(controller.AXIS_AZ)
                alt_pos = controller.get_position(controller.AXIS_ALT)
                
                if az_pos is not None and alt_pos is not None:
                    print(f"\nCurrent Position:")
                    
                    if position_format in ['raw', 'both']:
                        print(f"  Azimuth:  {az_pos:,} counts (0x{az_pos:08X})")
                        print(f"  Altitude: {alt_pos:,} counts (0x{alt_pos:08X})")
                    
                    if position_format in ['degrees', 'both']:
                        az_deg = controller.counts_to_degrees(az_pos, controller.AXIS_AZ)
                        alt_deg = controller.counts_to_degrees(alt_pos, controller.AXIS_ALT)
                        if az_deg is not None and alt_deg is not None:
                            print(f"  Azimuth:  {az_deg:.6f}°")
                            print(f"  Altitude: {alt_deg:.6f}°")
                    print()
                else:
                    print("Error reading position")
            
            # Format
            elif command == 'format':
                if args and args[0] in ['degrees', 'raw', 'both']:
                    position_format = args[0]
                    config.set('display', 'position_format', position_format)
                    print(f"Position format: {position_format}")
                else:
                    print(f"Current format: {position_format}")
                    print("Available: degrees, raw, both")
            
            # Zero position
            elif command == 'zero':
                controller.set_position(controller.AXIS_AZ, 0)
                controller.set_position(controller.AXIS_ALT, 0)
                print("Position set to 0,0")
            
            # Home
            elif command == 'home':
                home_az = controller.degrees_to_counts(
                    config.get('positions', 'home_az'), controller.AXIS_AZ)
                home_alt = controller.degrees_to_counts(
                    config.get('positions', 'home_alt'), controller.AXIS_ALT)
                if home_az is not None and home_alt is not None:
                    controller.goto_position(controller.AXIS_AZ, home_az)
                    controller.goto_position(controller.AXIS_ALT, home_alt)
                    print("Going to HOME position")
            
            elif command == 'sethome':
                az_pos = controller.get_position(controller.AXIS_AZ)
                alt_pos = controller.get_position(controller.AXIS_ALT)
                if az_pos is not None and alt_pos is not None:
                    az_deg = controller.counts_to_degrees(az_pos, controller.AXIS_AZ)
                    alt_deg = controller.counts_to_degrees(alt_pos, controller.AXIS_ALT)
                    config.set('positions', 'home_az', az_deg)
                    config.set('positions', 'home_alt', alt_deg)
                    config.save()
                    print(f"HOME set: Az={az_deg:.2f}°, Alt={alt_deg:.2f}°")
            
            # Stow
            elif command == 'stow':
                stow_az = controller.degrees_to_counts(
                    config.get('positions', 'stow_az'), controller.AXIS_AZ)
                stow_alt = controller.degrees_to_counts(
                    config.get('positions', 'stow_alt'), controller.AXIS_ALT)
                if stow_az is not None and stow_alt is not None:
                    controller.goto_position(controller.AXIS_AZ, stow_az)
                    controller.goto_position(controller.AXIS_ALT, stow_alt)
                    print("Going to STOW position")
            
            elif command == 'setstow':
                az_pos = controller.get_position(controller.AXIS_AZ)
                alt_pos = controller.get_position(controller.AXIS_ALT)
                if az_pos is not None and alt_pos is not None:
                    az_deg = controller.counts_to_degrees(az_pos, controller.AXIS_AZ)
                    alt_deg = controller.counts_to_degrees(alt_pos, controller.AXIS_ALT)
                    config.set('positions', 'stow_az', az_deg)
                    config.set('positions', 'stow_alt', alt_deg)
                    config.save()
                    print(f"STOW set: Az={az_deg:.2f}°, Alt={alt_deg:.2f}°")
            
            # Status
            elif command == 'status':
                print("\nMount Status:")
                for axis_name, axis_id in [("Azimuth", '1'), ("Altitude", '2')]:
                    status = controller.get_status(axis_id)
                    if status:
                        state = "Running" if status['running'] else "Stopped"
                        mode = "Tracking" if status['tracking_mode'] else "Goto"
                        direction = "CCW" if status['ccw'] else "CW"
                        init = "Yes" if status['initialized'] else "No"
                        print(f"  {axis_name}: {state}, {mode}, {direction}, Init: {init}")
                print()
            
            # Info
            elif command == 'info':
                print("\nMount Information:")
                for axis_name, axis_id in [("Azimuth", '1'), ("Altitude", '2')]:
                    print(f"\n{axis_name} Axis:")
                    
                    cpr = controller.get_counts_per_revolution(axis_id)
                    if cpr:
                        print(f"  CPR: {cpr:,} ({360.0/cpr:.8f}°/count)")
                    
                    pos = controller.get_position(axis_id)
                    if pos is not None:
                        deg = controller.counts_to_degrees(pos, axis_id)
                        print(f"  Position: {pos:,} ({deg:.6f}°)")
                
                if axis_id == '1':
                    timer_freq = controller.get_timer_freq()
                    if timer_freq:
                        print(f"\nTimer Frequency: {timer_freq:,} Hz")
                print()
            
            # Version
            elif command == 'version':
                print("\nSoftware: SkyWatcher Controller v2.0 CLI")
                for axis_name, axis_id in [("Azimuth", '1'), ("Altitude", '2')]:
                    version = controller.get_motor_board_version(axis_id)
                    if version:
                        print(f"{axis_name} Motor Board: {version}")
                print()
            
            # Config
            elif command == 'config':
                print("\nConfiguration:")
                print(f"  Connection: {config.get('connection', 'ip')}:{config.get('connection', 'port')}")
                print(f"  Speed range: {config.get('speed', 'min')} - {config.get('speed', 'max')}°/sec")
                print(f"  Current speed: {current_speed:.2f}°/sec")
                print(f"  Position format: {position_format}")
                print(f"  Home: Az={config.get('positions', 'home_az')}°, Alt={config.get('positions', 'home_alt')}°")
                print(f"  Stow: Az={config.get('positions', 'stow_az')}°, Alt={config.get('positions', 'stow_alt')}°")
                print(f"  Config file: {config.config_file}")
                print()
            
            else:
                print(f"Unknown command: {command}. Type 'help' for commands.")
        
        except KeyboardInterrupt:
            print("\n\nStopping all motion and exiting...")
            controller.stop_motion(controller.AXIS_AZ)
            controller.stop_motion(controller.AXIS_ALT)
            break
        except Exception as e:
            print(f"Error: {e}")
    
    # Save final state
    config.set('speed', 'default', current_speed)
    config.save()


def main():
    """Main entry point"""
    # Load configuration
    config = Config()
    
    # Parse command line arguments
    ip = sys.argv[1] if len(sys.argv) > 1 else config.get('connection', 'ip')
    port = int(sys.argv[2]) if len(sys.argv) > 2 else config.get('connection', 'port')
    
    print(f"\nConnecting to {ip}:{port}...")
    
    # Create controller
    controller = SkyWatcherProtocol(ip, port, config.get('connection', 'timeout'))
    
    # Test connection
    try:
        version = controller.get_motor_board_version('1')
        if version is None:
            print("Error: Could not connect to telescope")
            print("Check IP address and ensure telescope is powered on")
            sys.exit(1)
    except Exception as e:
        print(f"Connection error: {e}")
        sys.exit(1)
    
    try:
        interactive_mode(controller, config)
    finally:
        controller.close()
        print("\nConnection closed. Clear skies!")


if __name__ == '__main__':
    main()
