# config.py
"""
Centralized Configuration Settings for MTA ESP32-S3 Automation

All important configuration variables are defined here for easy modification.
Change values here instead of modifying individual source files.
"""

# ============================================================================
# TEMPLATES AND PATHS
# ============================================================================

# Path to templates folder containing 'q' and 'e' subdirectories
TEMPLATES_PATH = "templates"

# Directory to save screenshots and results
SCREENSHOTS_DIR = "screenshots"

# Results CSV filename
RESULTS_CSV = "results.csv"

# ============================================================================
# RESOLUTION SETTINGS
# ============================================================================

# Active resolution - Change this to switch between resolutions
# Options: "1920x1080" or "1600x900"
ACTIVE_RESOLUTION = "1920x1080"

# Resolution-specific coordinate configurations
RESOLUTION_CONFIGS = {
    "1920x1080": {
        # Crop coordinates for the 3 sequential glyph positions (x, y)
        "CROP_COORDINATES": {
            1: (39, 943),   # First glyph position
            2: (97, 943),   # Second glyph position
            3: (155, 943),  # Third glyph position
        },
        # Status monitoring region crop coordinates and size
        "STATUS_REGION_CROP": {
            'x': 761,
            'y': 72,
            'width': 397,
            'height': 16
        },
        # End detection region crop coordinates and size
        "END_REGION_CROP": {
            'x': 842,
            'y': 33,
            'width': 15,
            'height': 11
        },
        # PM detection region crop coordinates and size
        "PM_REGION_CROP": {
            'x': 28,
            'y': 23,
            'width': 14,
            'height': 143
        },
    },
    "1600x900": {
        # Crop coordinates for the 3 sequential glyph positions (x, y)
        # TODO: Update these coordinates for 1600x900 resolution
        "CROP_COORDINATES": {
            1: (38, 762),   # First glyph position (scaled from 1920x1080)
            2: (96, 762),   # Second glyph position
            3: (154, 762),  # Third glyph position
        },
        # Status monitoring region crop coordinates and size
        # TODO: Update these coordinates for 1600x900 resolution
        "STATUS_REGION_CROP": {
            'x': 634,
            'y': 60,
            'width': 331,
            'height': 14
        },
        # End detection region crop coordinates and size
        # TODO: Update these coordinates for 1600x900 resolution
        "END_REGION_CROP": {
            'x': 702,
            'y': 28,
            'width': 13,
            'height': 9
        },
        # PM detection region crop coordinates and size
        # TODO: Update these coordinates for 1600x900 resolution
        "PM_REGION_CROP": {
            'x': 0,
            'y': 0,
            'width': 0,
            'height': 0
        },
    }
}

# Get active resolution configuration
_active_config = RESOLUTION_CONFIGS.get(ACTIVE_RESOLUTION)
if _active_config is None:
    raise ValueError(f"Invalid ACTIVE_RESOLUTION: {ACTIVE_RESOLUTION}. Must be one of {list(RESOLUTION_CONFIGS.keys())}")

# Set current coordinates based on active resolution
CROP_COORDINATES = _active_config["CROP_COORDINATES"]
STATUS_REGION_CROP = _active_config["STATUS_REGION_CROP"]
END_REGION_CROP = _active_config["END_REGION_CROP"]
PM_REGION_CROP = _active_config["PM_REGION_CROP"]

# ============================================================================
# SCREEN CAPTURE SETTINGS
# ============================================================================

# Target window title to capture from
WINDOW_TITLE = "MTA: San Andreas"

# Size of each crop (width x height in pixels)
CROP_SIZE = 26

# ============================================================================
# TIMING SETTINGS
# ============================================================================

# Delay after Alt press before first capture (seconds)
INITIAL_DELAY = 0.4

# Delays before each capture as ranges [pos1, pos2, pos3] (seconds)
# Each entry is a tuple of (min, max) for random delay
CAPTURE_DELAYS = [
    (0.2, 0.4),  # First capture: 0.2-0.4s
    (0.4, 0.6),  # Second capture: 0.4-0.6s
    (0.4, 0.6),  # Third capture: 0.6s (fixed)
]

# Debounce time between Alt presses (seconds)
ALT_DEBOUNCE_TIME = 0.5

# ESP32 random delay range before sending commands (milliseconds)
ESP_DELAY_MIN = 50
ESP_DELAY_MAX = 200

# ============================================================================
# ESP32 COMMUNICATION
# ============================================================================

# ESP32 Serial Configuration
ESP32_BAUDRATE = 115200
ESP32_TIMEOUT = 1.0

# ESP32 port (None for auto-detection)
ESP32_PORT = None  # e.g., "COM3" or None for auto-detect

# Keypress delay on ESP32 side (milliseconds)
KEYPRESS_DELAY_MS = 50

# ============================================================================
# CLASSIFICATION SETTINGS
# ============================================================================

# Minimum confidence required to trigger ESP action
MIN_CONFIDENCE_FOR_ESP_ACTION = 0.6

# High confidence threshold for classification
HIGH_CONFIDENCE_THRESHOLD = 0.8

# Template matching confidence threshold
TEMPLATE_CONFIDENCE_THRESHOLD = 0.7

# ============================================================================
# STATUS MONITORING (POST Q/E SEQUENCE)
# ============================================================================

# Note: STATUS_REGION_CROP and END_REGION_CROP are now defined in RESOLUTION SETTINGS above

# Status templates paths
STATUS_TEMPLATES_END = "templates/end"
STATUS_TEMPLATES_ALT = "templates/alt"
STATUS_TEMPLATES_WAIT = "templates/wait"
STATUS_TEMPLATES_PM = "templates/pm"

# Status monitoring timing
STATUS_CHECK_DELAY_MIN = 2.3  # seconds - minimum delay between checks
STATUS_CHECK_DELAY_MAX = 4.4  # seconds - maximum delay between checks
STATUS_INITIAL_WAIT = 0.2     # seconds - wait after last Q/E press before monitoring

# Status monitoring thresholds and limits
STATUS_CONFIDENCE_THRESHOLD = 0.8  # Higher threshold for status detection
STATUS_MAX_RETRIES = 5             # Max retries before exiting on no match
STATUS_MAX_ITERATIONS = 50         # Max loop iterations before forced exit

# ============================================================================
# WINDOW MANAGEMENT
# ============================================================================

# Whether to bring MTA window to foreground on startup
BRING_WINDOW_TO_FOREGROUND = True

# ============================================================================
# LOGGING AND DEBUG
# ============================================================================

# Enable verbose logging
VERBOSE_LOGGING = True

# Save cropped images for debugging
SAVE_CROPPED_IMAGES = False

# Log classification details to CSV
LOG_TO_CSV = True

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_config():
    """Validate configuration settings"""
    errors = []
    
    # Validate ESP delay range
    if ESP_DELAY_MIN >= ESP_DELAY_MAX:
        errors.append("ESP_DELAY_MIN must be less than ESP_DELAY_MAX")
    
    if ESP_DELAY_MIN < 0 or ESP_DELAY_MAX < 0:
        errors.append("ESP delay values must be non-negative")
    
    # Validate crop size
    if CROP_SIZE <= 0:
        errors.append("CROP_SIZE must be positive")
    
    # Validate timing settings
    if INITIAL_DELAY < 0:
        errors.append("INITIAL_DELAY must be non-negative")

    # Validate CAPTURE_DELAYS ranges
    for i, delay_range in enumerate(CAPTURE_DELAYS):
        if not isinstance(delay_range, tuple) or len(delay_range) != 2:
            errors.append(f"CAPTURE_DELAYS[{i}] must be a tuple of (min, max)")
        else:
            min_delay, max_delay = delay_range
            if min_delay < 0 or max_delay < 0:
                errors.append(f"CAPTURE_DELAYS[{i}] values must be non-negative")
            if min_delay > max_delay:
                errors.append(f"CAPTURE_DELAYS[{i}] min must be less than or equal to max")
    
    # Validate confidence thresholds
    if not (0 <= MIN_CONFIDENCE_FOR_ESP_ACTION <= 1):
        errors.append("MIN_CONFIDENCE_FOR_ESP_ACTION must be between 0 and 1")

    if not (0 <= HIGH_CONFIDENCE_THRESHOLD <= 1):
        errors.append("HIGH_CONFIDENCE_THRESHOLD must be between 0 and 1")

    if not (0 <= TEMPLATE_CONFIDENCE_THRESHOLD <= 1):
        errors.append("TEMPLATE_CONFIDENCE_THRESHOLD must be between 0 and 1")

    if not (0 <= STATUS_CONFIDENCE_THRESHOLD <= 1):
        errors.append("STATUS_CONFIDENCE_THRESHOLD must be between 0 and 1")

    # Validate status monitoring settings
    if STATUS_CHECK_DELAY_MIN >= STATUS_CHECK_DELAY_MAX:
        errors.append("STATUS_CHECK_DELAY_MIN must be less than STATUS_CHECK_DELAY_MAX")

    if STATUS_CHECK_DELAY_MIN < 0 or STATUS_CHECK_DELAY_MAX < 0:
        errors.append("Status check delay values must be non-negative")

    if STATUS_INITIAL_WAIT < 0:
        errors.append("STATUS_INITIAL_WAIT must be non-negative")

    if STATUS_MAX_RETRIES < 1:
        errors.append("STATUS_MAX_RETRIES must be at least 1")

    if STATUS_MAX_ITERATIONS < 1:
        errors.append("STATUS_MAX_ITERATIONS must be at least 1")

    return errors

# ============================================================================
# CONFIGURATION SUMMARY
# ============================================================================

def print_config_summary():
    """Print a summary of current configuration"""
    print("=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    print(f"Active Resolution: {ACTIVE_RESOLUTION}")
    print(f"Templates Path: {TEMPLATES_PATH}")
    print(f"Window Title: {WINDOW_TITLE}")
    print(f"Crop Size: {CROP_SIZE}x{CROP_SIZE}")
    print(f"Crop Coordinates: {CROP_COORDINATES}")
    print(f"Status Region: {STATUS_REGION_CROP}")
    print(f"End Region: {END_REGION_CROP}")
    print(f"Initial Delay: {INITIAL_DELAY}s")
    print(f"Capture Delays: {CAPTURE_DELAYS}")
    print(f"ESP Delay Range: {ESP_DELAY_MIN}-{ESP_DELAY_MAX}ms")
    print(f"ESP Port: {ESP32_PORT or 'Auto-detect'}")
    print(f"Min Confidence: {MIN_CONFIDENCE_FOR_ESP_ACTION}")
    print(f"Template Threshold: {TEMPLATE_CONFIDENCE_THRESHOLD}")
    print("=" * 60)

if __name__ == "__main__":
    # Validate configuration when run directly
    errors = validate_config()
    if errors:
        print("Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Configuration is valid")
        print_config_summary()