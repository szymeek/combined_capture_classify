# esp_finder.py
import serial.tools.list_ports
from typing import List, Optional

class ESPFinder:
    """Utility to find and identify ESP boards connected via USB"""
    
    # Common ESP32/ESP8266 USB-to-serial chip VID:PID combinations
    ESP_IDENTIFIERS = [
        # ESP32-S3 native USB
        (0x303A, 0x1001),  # Espressif ESP32-S3
        # Common USB-to-serial chips used with ESP boards
        (0x10C4, 0xEA60),  # Silicon Labs CP2102/CP2104
        (0x0403, 0x6001),  # FTDI FT232
        (0x1A86, 0x7523),  # QinHeng CH340
        (0x067B, 0x2303),  # Prolific PL2303
    ]
    
    @classmethod
    def find_esp_ports(cls) -> List[dict]:
        """Find all potential ESP board ports"""
        esp_ports = []
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            port_info = {
                'port': port.device,
                'description': port.description,
                'manufacturer': port.manufacturer,
                'vid': port.vid,
                'pid': port.pid,
                'is_esp': False
            }
            
            # Check if this looks like an ESP board
            if port.vid and port.pid:
                for vid, pid in cls.ESP_IDENTIFIERS:
                    if port.vid == vid and port.pid == pid:
                        port_info['is_esp'] = True
                        break
            
            # Also check description for ESP-related keywords
            if any(keyword in port.description.lower() for keyword in ['esp', 'cp21', 'ch340', 'ft232']):
                port_info['is_esp'] = True
                
            esp_ports.append(port_info)
            
        return esp_ports
    
    @classmethod
    def auto_find_esp(cls) -> Optional[str]:
        """Automatically find the first likely ESP board port"""
        ports = cls.find_esp_ports()
        
        # First, try ports that are definitely ESP boards
        for port in ports:
            if port['is_esp']:
                return port['port']
        
        # If none found, return the first available port
        if ports:
            return ports[0]['port']
            
        return None
    
    @classmethod
    def list_all_ports(cls):
        """Print all available serial ports"""
        ports = cls.find_esp_ports()
        print("\nAvailable Serial Ports:")
        print("-" * 60)
        
        for port in ports:
            esp_indicator = " [ESP?]" if port['is_esp'] else ""
            print(f"{port['port']:<10} {port['description']:<30} {esp_indicator}")
            if port['manufacturer']:
                print(f"           Manufacturer: {port['manufacturer']}")
            if port['vid'] and port['pid']:
                print(f"           VID:PID = {port['vid']:04X}:{port['pid']:04X}")
            print()
