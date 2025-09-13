# esp_test.py
#!/usr/bin/env python3
"""
ESP32-S3 HID Keyboard Test Utility

Test communication with your ESP board and verify key commands work correctly.
"""

import argparse
import time
from esp_communicator import ESPCommunicator
from esp_finder import ESPFinder

def test_basic_communication(esp: ESPCommunicator):
    """Test basic communication with ESP board"""
    print("\n=== Basic Communication Test ===")
    
    # Test ping
    print("Testing PING command...")
    if esp.send_command("PING"):
        print("✓ PING successful")
    else:
        print("✗ PING failed")
        return False
    
    return True

def test_key_commands(esp: ESPCommunicator):
    """Test key press/release commands"""
    print("\n=== Key Command Test ===")
    
    test_keys = ['Q', 'E', 'ALT']
    
    for key in test_keys:
        print(f"Testing {key} key...")
        
        # Test press
        if esp.press_key(key):
            print(f"✓ PRESS {key} successful")
        else:
            print(f"✗ PRESS {key} failed")
            continue
            
        time.sleep(0.1)
        
        # Test release
        if esp.release_key(key):
            print(f"✓ RELEASE {key} successful")
        else:
            print(f"✗ RELEASE {key} failed")
            
        time.sleep(0.5)

def test_tap_commands(esp: ESPCommunicator):
    """Test tap (press+release) commands"""
    print("\n=== Tap Command Test ===")
    
    test_keys = ['Q', 'E']
    
    for key in test_keys:
        print(f"Testing TAP {key}...")
        if esp.tap_key(key, 0.1):
            print(f"✓ TAP {key} successful")
        else:
            print(f"✗ TAP {key} failed")
        time.sleep(0.5)

def interactive_mode(esp: ESPCommunicator):
    """Interactive command mode"""
    print("\n=== Interactive Mode ===")
    print("Available commands:")
    print("  press <key>   - Press and hold key")
    print("  release <key> - Release key") 
    print("  tap <key>     - Tap key (press+release)")
    print("  ping          - Test connection")
    print("  quit          - Exit interactive mode")
    print()
    
    while True:
        try:
            cmd = input("ESP> ").strip().lower()
            
            if cmd == "quit":
                break
            elif cmd == "ping":
                result = esp.send_command("PING")
                print("✓ PONG" if result else "✗ No response")
            elif cmd.startswith("press "):
                key = cmd.split()[1].upper()
                result = esp.press_key(key)
                print(f"✓ Pressed {key}" if result else f"✗ Failed to press {key}")
            elif cmd.startswith("release "):
                key = cmd.split()[1].upper()
                result = esp.release_key(key)
                print(f"✓ Released {key}" if result else f"✗ Failed to release {key}")
            elif cmd.startswith("tap "):
                key = cmd.split()[1].upper()
                result = esp.tap_key(key, 0.1)
                print(f"✓ Tapped {key}" if result else f"✗ Failed to tap {key}")
            else:
                print("Unknown command. Type 'quit' to exit.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="ESP32-S3 HID Keyboard Test Utility")
    parser.add_argument("--port", default=None, help="ESP board COM port (auto-detect if not specified)")
    parser.add_argument("--list-ports", action="store_true", help="List available serial ports")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--basic-test", action="store_true", help="Run basic communication test")
    parser.add_argument("--key-test", action="store_true", help="Run key command test")
    parser.add_argument("--all-tests", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    if args.list_ports:
        ESPFinder.list_all_ports()
        return
    
    # Find ESP port
    port = args.port
    if port is None:
        port = ESPFinder.auto_find_esp()
        if port:
            print(f"Auto-detected ESP port: {port}")
        else:
            print("No ESP port found. Use --list-ports to see available ports.")
            return
    
    # Connect to ESP
    esp = ESPCommunicator(port)
    if not esp.connect():
        print(f"Failed to connect to ESP board on {port}")
        return
    
    try:
        if args.all_tests or args.basic_test:
            if not test_basic_communication(esp):
                print("Basic communication failed. Check your ESP board and try again.")
                return
                
        if args.all_tests or args.key_test:
            test_key_commands(esp)
            test_tap_commands(esp)
        
        if args.interactive:
            interactive_mode(esp)
            
        if not any([args.all_tests, args.basic_test, args.key_test, args.interactive]):
            print("No test specified. Use --help to see available options.")
            
    finally:
        esp.disconnect()

if __name__ == "__main__":
    main()
