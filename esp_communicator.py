# esp_communicator.py
import serial
import time
import threading
from typing import Optional, List
from dataclasses import dataclass

@dataclass
class KeyCommand:
    action: str  # "PRESS", "RELEASE", "TAP"
    key: str     # "ALT", "Q", "E", etc.
    duration: float = 0.0  # For TAP commands

class ESPCommunicator:
    def __init__(self, port: str = "COM3", baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
        self.is_connected = False
        self._lock = threading.Lock()
        
    def connect(self) -> bool:
        """Establish connection to ESP board"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            time.sleep(2)  # Allow ESP to initialize
            
            # Test connection
            if self.send_command("PING"):
                self.is_connected = True
                print(f"[ESP] Connected to {self.port}")
                return True
            else:
                print(f"[ESP] Failed to get response from {self.port}")
                return False
                
        except Exception as e:
            print(f"[ESP] Connection error: {e}")
            return False
    
    def disconnect(self):
        """Close connection to ESP board"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.is_connected = False
            print("[ESP] Disconnected")
    
    def send_command(self, command: str) -> bool:
        """Send command to ESP and wait for acknowledgment"""
        if not self.is_connected or not self.serial_conn:
            return False
            
        try:
            with self._lock:
                # Send command
                cmd_bytes = f"{command}\n".encode('utf-8')
                self.serial_conn.write(cmd_bytes)
                self.serial_conn.flush()
                
                # Wait for acknowledgment
                response = self.serial_conn.readline().decode('utf-8').strip()
                
                if response == "OK":
                    return True
                elif response == "ERROR":
                    print(f"[ESP] Command failed: {command}")
                    return False
                else:
                    print(f"[ESP] Unexpected response: {response}")
                    return False
                    
        except Exception as e:
            print(f"[ESP] Send error: {e}")
            return False
    
    def press_key(self, key: str) -> bool:
        """Press and hold a key"""
        return self.send_command(f"PRESS {key.upper()}")
    
    def release_key(self, key: str) -> bool:
        """Release a key"""
        return self.send_command(f"RELEASE {key.upper()}")
    
    def tap_key(self, key: str, duration: float = 0.1) -> bool:
        """Tap a key (press and release with specified duration)"""
        if self.press_key(key):
            time.sleep(duration)
            return self.release_key(key)
        return False
    
    def send_key_sequence(self, keys: List[KeyCommand]) -> bool:
        """Send a sequence of key commands"""
        success = True
        for cmd in keys:
            if cmd.action == "PRESS":
                success &= self.press_key(cmd.key)
            elif cmd.action == "RELEASE":
                success &= self.release_key(cmd.key)
            elif cmd.action == "TAP":
                success &= self.tap_key(cmd.key, cmd.duration)
            
            if not success:
                break
                
        return success
