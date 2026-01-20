#!/usr/bin/env python3
"""
SkyWatcher Connection Diagnostic Tool
Tests various connection methods and protocols
"""

import socket
import time

def test_connection(ip, port):
    """Test basic UDP connectivity"""
    print(f"\n{'='*60}")
    print(f"Testing connection to {ip}:{port}")
    print(f"{'='*60}\n")
    
    # Test 1: Basic UDP socket
    print("Test 1: Basic UDP socket creation...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3.0)
        print("✓ Socket created successfully")
    except Exception as e:
        print(f"✗ Failed to create socket: {e}")
        return
    
    # Test 2: Send simple version query
    print("\nTest 2: Query motor board version (axis 1)...")
    try:
        # Command format: :X10e1\r (get version for axis 1)
        command = ":X10e1\r"
        print(f"  Sending: {repr(command)}")
        
        sock.sendto(command.encode('ascii'), (ip, port))
        print("  ✓ Command sent")
        
        try:
            data, addr = sock.recvfrom(1024)
            response = data.decode('ascii')
            print(f"  ✓ Response received from {addr}")
            print(f"  Response: {repr(response)}")
            print(f"  Response (hex): {data.hex()}")
        except socket.timeout:
            print("  ✗ Timeout - no response received")
            print("  This suggests:")
            print("    - Telescope might not be on")
            print("    - Wrong IP address")
            print("    - Firewall blocking")
            print("    - Wrong port")
            return
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return
    
    # Test 3: Try alternative command format (original research)
    print("\nTest 3: Try original command format...")
    try:
        # Original format from your pcap
        command = ":j1\r"
        print(f"  Sending: {repr(command)}")
        
        sock.sendto(command.encode('ascii'), (ip, port))
        
        try:
            data, addr = sock.recvfrom(1024)
            response = data.decode('ascii')
            print(f"  ✓ Response received: {repr(response)}")
        except socket.timeout:
            print("  ✗ Timeout")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Test 4: Query position
    print("\nTest 4: Query position (axis 1)...")
    try:
        command = ":X10j1\r"
        print(f"  Sending: {repr(command)}")
        
        sock.sendto(command.encode('ascii'), (ip, port))
        
        try:
            data, addr = sock.recvfrom(1024)
            response = data.decode('ascii')
            print(f"  ✓ Response: {repr(response)}")
            
            # Try to parse
            if response.startswith('='):
                hex_str = response[1:].replace('\r', '')
                print(f"  Hex data: {hex_str}")
        except socket.timeout:
            print("  ✗ Timeout")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Test 5: Try without X10 prefix (some mounts use different format)
    print("\nTest 5: Try without X10 prefix...")
    try:
        command = ":e1\r"
        print(f"  Sending: {repr(command)}")
        
        sock.sendto(command.encode('ascii'), (ip, port))
        
        try:
            data, addr = sock.recvfrom(1024)
            response = data.decode('ascii')
            print(f"  ✓ Response: {repr(response)}")
        except socket.timeout:
            print("  ✗ Timeout")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Test 6: Check what SynScan uses (port 11881 - app protocol)
    print("\nTest 6: Try SynScan App Protocol (port 11881)...")
    try:
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock2.settimeout(3.0)
        
        command = "ConnectedGet"
        print(f"  Sending: {repr(command)}")
        
        sock2.sendto(command.encode('ascii'), (ip, 11881))
        
        try:
            data, addr = sock2.recvfrom(1024)
            response = data.decode('ascii')
            print(f"  ✓ Response: {repr(response)}")
            print("  NOTE: Your mount might use SynScan App Protocol!")
        except socket.timeout:
            print("  ✗ Timeout on port 11881")
        
        sock2.close()
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    sock.close()
    
    print("\n" + "="*60)
    print("Diagnostic complete")
    print("="*60)

def main():
    print("\n" + "="*60)
    print("SkyWatcher Connection Diagnostic Tool")
    print("="*60)
    
    # Get connection info
    ip = input("\nEnter telescope IP address [192.168.4.1]: ").strip() or "192.168.4.1"
    port_str = input("Enter port [11880]: ").strip() or "11880"
    port = int(port_str)
    
    test_connection(ip, port)
    
    print("\n\nRECOMMENDATIONS:")
    print("-" * 60)
    print("If Test 2-5 ALL timed out:")
    print("  1. Check telescope is powered on")
    print("  2. Verify you're connected to telescope WiFi")
    print("  3. Ping the telescope: ping", ip)
    print("  4. Check Windows Firewall settings")
    print("")
    print("If Test 6 succeeded:")
    print("  Your mount uses SynScan App Protocol (port 11881)")
    print("  instead of direct motor controller protocol (port 11880)")
    print("")
    print("What works in YOUR SynScan app?")
    print("  - If SynScan mobile/desktop app works, they might use port 11881")
    print("")

if __name__ == '__main__':
    main()
