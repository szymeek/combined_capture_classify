# test_esp_keyboard.py
"""
Test utility for ESP32-S3 keyboard interface using your existing modules
"""

import time
from keyboard_interface import KeyboardInterface
from esp_serial import ESP32Serial

def test_keyboard_interface():
    """Test the keyboard interface with your ESP32-S3"""
    
    print("🧪 ESP32-S3 Keyboard Interface Test")
    print("=" * 40)
    
    # Initialize keyboard interface
    keyboard = KeyboardInterface()
    
    if not keyboard.initialize():
        print("❌ Failed to initialize keyboard interface")
        return False
    
    print("✅ Keyboard interface initialized successfully")
    print()
    
    # Test each key function
    test_keys = [
        ("ALT", keyboard.press_alt),
        ("Q", keyboard.press_q),
        ("E", keyboard.press_e)
    ]
    
    for key_name, key_func in test_keys:
        print(f"🔧 Testing {key_name} key...")
        result = key_func()
        
        if result:
            print(f"✅ {key_name} key test passed")
        else:
            print(f"❌ {key_name} key test failed")
        
        time.sleep(1)  # Wait between tests
        print()
    
    # Test character key method
    print("🔧 Testing press_character_key method...")
    for char in ['Q', 'E']:
        print(f"   Testing character: {char}")
        result = keyboard.press_character_key(char)
        if result:
            print(f"   ✅ Character {char} test passed")
        else:
            print(f"   ❌ Character {char} test failed")
        time.sleep(0.5)
    
    # Test invalid character
    print("   Testing invalid character: X")
    result = keyboard.press_character_key('X')
    if not result:
        print("   ✅ Invalid character handling works correctly")
    else:
        print("   ❌ Invalid character should have failed")
    
    # Cleanup
    keyboard.cleanup()
    print("🧹 Cleanup completed")
    return True

def interactive_test():
    """Interactive test mode"""
    print("🎮 Interactive ESP32-S3 Test Mode")
    print("=" * 40)
    print("Commands:")
    print("  alt  - Press Alt key")
    print("  q    - Press Q key")
    print("  e    - Press E key")
    print("  quit - Exit")
    print()
    
    keyboard = KeyboardInterface()
    if not keyboard.initialize():
        print("❌ Failed to initialize keyboard interface")
        return
    
    try:
        while True:
            cmd = input("Test> ").strip().lower()
            
            if cmd == "quit":
                break
            elif cmd == "alt":
                result = keyboard.press_alt()
                print("✅ Alt pressed" if result else "❌ Alt failed")
            elif cmd == "q":
                result = keyboard.press_q()
                print("✅ Q pressed" if result else "❌ Q failed")
            elif cmd == "e":
                result = keyboard.press_e()
                print("✅ E pressed" if result else "❌ E failed")
            else:
                print("❓ Unknown command. Available: alt, q, e, quit")
                
    except KeyboardInterrupt:
        print("\n🛑 Interrupted")
    finally:
        keyboard.cleanup()

def list_ports():
    """List available serial ports"""
    print("📋 Available Serial Ports")
    print("=" * 40)
    
    ports = ESP32Serial.list_available_ports()
    
    if not ports:
        print("❌ No serial ports found")
        return
    
    for i, (port, description) in enumerate(ports, 1):
        print(f"{i}. {port}")
        print(f"   Description: {description}")
        print()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ESP32-S3 Keyboard Test Utility")
    parser.add_argument("--interactive", action="store_true", 
                       help="Run in interactive test mode")
    parser.add_argument("--list-ports", action="store_true", 
                       help="List available serial ports")
    
    args = parser.parse_args()
    
    if args.list_ports:
        list_ports()
    elif args.interactive:
        interactive_test()
    else:
        test_keyboard_interface()
