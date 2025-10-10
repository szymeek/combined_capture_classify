# PM Templates

This folder contains template images for PM (Private Message) detection.

## Image Specifications

- **Resolution 1920x1080**: Crop region at (28, 23) with size 14x143 pixels
- **Resolution 1600x900**: Not yet configured (coordinates set to 0,0,0,0)

## Usage

Place PNG template images in this folder that represent the PM indicator as it appears on screen. The template matching system will use these images to detect when a PM is present after the Q/E sequence.

## Template Naming

- Files should be named descriptively, e.g., `pm_1.png`, `pm_2.png`, etc.
- All files must be in PNG format
- Images will be automatically resized to match the configured crop region size

## Detection Logic

After the Q/E sequence completes, the system will:
1. Capture a screenshot
2. Crop the PM region (coordinates from config)
3. Match against templates in this folder
4. If PM is detected with confidence >= STATUS_CONFIDENCE_THRESHOLD:
   - Skip status monitoring
   - Return to idle state
5. If no PM detected:
   - Proceed with normal status monitoring (alt/wait/end)
