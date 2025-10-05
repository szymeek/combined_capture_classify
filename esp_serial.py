"""
ESP32-S3 Serial Communication Module - Optimized
"""

import serial
import serial.tools.list_ports
import time
from typing import Optional, List
import config

class ESP32Serial:
    def __init__(self, port: Optional[str] = None):
        self.port = port or config.ESP32_PORT
        self.connection: Optional[serial.Serial] = None
        self.is_connected = False
    
    @staticmethod
    def list_available_ports() -> List[tuple]:
        """List all available COM ports"""
        ports = serial.tools.list_ports.comports()
        return [(port.device, port.description) for port in ports]
    
    def auto_connect(self) -> bool:
        """Try to connect to ESP32 automatically"""
        if self.port:
            return self.connect(self.port)
        
        # Try to find ESP32 automatically
        ports = self.list_available_ports()
        for port_device, description in ports:
            if "USB" in description.upper() or "SERIAL" in description.upper():
                if self.connect(port_device):
                    return True
        return False
    
    def connect(self, port: str) -> bool:
        """Connect to specific COM port"""
        try:
            self.connection = serial.Serial(
                port, 
                config.ESP32_BAUDRATE, 
                timeout=config.ESP32_TIMEOUT
            )
            self.port = port
            self.is_connected = True
            time.sleep(2)  # ESP32 initialization delay
            if config.VERBOSE_LOGGING:
                print(f"✅ Connected to ESP32 on {port}")
            return True
        except Exception as e:
            if config.VERBOSE_LOGGING:
                print(f"❌ Failed to connect to {port}: {e}")
            self.is_connected = False
            return False
    
    def send_command(self, command: str, retries: int = 3) -> bool:
        """Send command to ESP32 with retry logic"""
        if not self.is_connected or not self.connection:
            if config.VERBOSE_LOGGING:
                print("❌ ESP32 not connected")
            return False

        for attempt in range(retries):
            try:
                self.connection.write(f"{command}\n".encode())
                self.connection.flush()

                # Reduced response wait time for speed
                time.sleep(0.05)  # Reduced from 0.1 to 0.05
                if self.connection.in_waiting > 0:
                    response = self.connection.readline().decode().strip()
                    if config.VERBOSE_LOGGING:
                        print(f"ESP32: {response}")

                return True
            except Exception as e:
                if attempt < retries - 1:
                    if config.VERBOSE_LOGGING:
                        print(f"⚠️ Error sending command '{command}' (attempt {attempt+1}/{retries}): {e}")
                    time.sleep(0.1)  # Brief delay before retry
                else:
                    if config.VERBOSE_LOGGING:
                        print(f"❌ Failed to send command '{command}' after {retries} attempts: {e}")
                    return False

        return False
    
    def disconnect(self):
        """Disconnect from ESP32"""
        if self.connection:
            self.connection.close()
            self.is_connected = False
            if config.VERBOSE_LOGGING:
                print("👋 ESP32 disconnected")