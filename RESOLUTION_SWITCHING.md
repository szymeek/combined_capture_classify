# Resolution Switching Guide

## Overview
The automation now supports multiple game resolutions with easy switching between them.

## Supported Resolutions
- **1920x1080** (default)
- **1600x900**

## How to Switch Resolutions

### Method: Edit config.py

1. Open `config.py` in your editor
2. Find the line (around line 28):
   ```python
   ACTIVE_RESOLUTION = "1920x1080"
   ```
3. Change it to your desired resolution:
   ```python
   ACTIVE_RESOLUTION = "1600x900"
   ```
4. Save the file
5. Restart the automation

That's it! The automation will automatically use the correct coordinates for your selected resolution.

## Resolution-Specific Coordinates

Each resolution has its own set of coordinates defined in `RESOLUTION_CONFIGS`:

### 1920x1080 Configuration
- **Glyph Positions:** (39, 943), (97, 943), (155, 943)
- **Status Region:** x=761, y=72, size=397x16
- **End Region:** x=842, y=33, size=15x11

### 1600x900 Configuration
- **Glyph Positions:** (33, 786), (81, 786), (129, 786)
- **Status Region:** x=634, y=60, size=331x14
- **End Region:** x=702, y=28, size=13x9

## Adjusting Coordinates for 1600x900

The 1600x900 coordinates are currently scaled estimates from 1920x1080. If they don't work perfectly:

1. Open `config.py`
2. Find the `"1600x900"` section in `RESOLUTION_CONFIGS`
3. Update the coordinates as needed:
   - `CROP_COORDINATES`: The Q/E glyph positions
   - `STATUS_REGION_CROP`: The status text region
   - `END_REGION_CROP`: The end detection region

## Verification

To verify your configuration is valid, run:
```bash
python config.py
```

This will display the current active resolution and all coordinates being used.

## Adding New Resolutions

To add support for a new resolution (e.g., 2560x1440):

1. Open `config.py`
2. Add a new entry to `RESOLUTION_CONFIGS`:
   ```python
   "2560x1440": {
       "CROP_COORDINATES": {
           1: (x1, y1),
           2: (x2, y2),
           3: (x3, y3),
       },
       "STATUS_REGION_CROP": {
           'x': x,
           'y': y,
           'width': w,
           'height': h
       },
       "END_REGION_CROP": {
           'x': x,
           'y': y,
           'width': w,
           'height': h
       },
   }
   ```
3. Set `ACTIVE_RESOLUTION = "2560x1440"`
4. Test and adjust coordinates as needed
