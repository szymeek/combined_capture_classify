# config.py
"""
Configuration settings for ESP32-S3 communication
"""

# ESP32 Serial Configuration
ESP32_BAUDRATE = 115200
ESP32_TIMEOUT = 1.0

# Classification confidence thresholds
MIN_CONFIDENCE_FOR_ESP_ACTION = 0.6
HIGH_CONFIDENCE_THRESHOLD = 0.8

# Timing settings
KEYPRESS_DELAY_MS = 50  # Matches ESP32 delay
