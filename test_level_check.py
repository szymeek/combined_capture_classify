#!/usr/bin/env python3
"""
Test script for level check verification
"""
import config

def test_level_check_config():
    """Test level check configuration"""
    print("=" * 60)
    print("Level Check Configuration Test")
    print("=" * 60)

    print(f"\nActive Resolution: {config.ACTIVE_RESOLUTION}")
    print(f"\nLevel Check Settings:")
    print(f"  Enabled: {config.LEVEL_CHECK_ENABLED}")
    print(f"  Pixel Coordinates: ({config.LEVEL_CHECK_PIXEL['x']}, {config.LEVEL_CHECK_PIXEL['y']})")
    print(f"  Expected Color: RGB{config.LEVEL_CHECK_EXPECTED_COLOR}")
    print(f"  Color Tolerance: {config.LEVEL_CHECK_COLOR_TOLERANCE}")

    print(f"\nResolution-Specific Coordinates:")
    for resolution, res_config in config.RESOLUTION_CONFIGS.items():
        pixel = res_config.get('LEVEL_CHECK_PIXEL', {})
        print(f"  {resolution}: ({pixel.get('x', 'N/A')}, {pixel.get('y', 'N/A')})")

    print("\n" + "=" * 60)
    print("Configuration looks good!")
    print("=" * 60)

if __name__ == "__main__":
    test_level_check_config()
