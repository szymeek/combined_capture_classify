"""
High-Level Keyboard Interface using centralized config
"""

from esp_serial import ESP32Serial
from config import ESP32_PORT
from typing import Optional

class KeyboardInterface:
    def __init__(self, esp_port: Optional[str] = None):
        # Use centralized config if no specific port provided
        port = esp_port or ESP32_PORT
        self.esp32 = ESP32Serial(port=port)
        self.connected = False

    def initialize(self) -> bool:
        if self.esp32.auto_connect():
            self.connected = True
            print("🎮 Keyboard interface ready")
            return True
        else:
            print("❌ Failed to initialize keyboard interface")
            return False

    def press_alt(self) -> bool:
        if not self.connected:
            print("❌ Keyboard not connected")
            return False
        print("⌨️  Pressing Alt key...")
        return self.esp32.send_command("ALT")

    def press_e(self) -> bool:
        if not self.connected:
            print("❌ Keyboard not connected") 
            return False
        print("⌨️  Pressing E key...")
        return self.esp32.send_command("E")

    def press_q(self) -> bool:
        if not self.connected:
            print("❌ Keyboard not connected")
            return False
        print("⌨️  Pressing Q key...")
        return self.esp32.send_command("Q")

    def press_character_key(self, character: str) -> bool:
        if character == 'E':
            return self.press_e()
        elif character == 'Q':
            return self.press_q()
        else:
            print(f"❌ Invalid character: {character}")
            return False

    def cleanup(self):
        if self.esp32:
            self.esp32.disconnect()
            self.connected = False
