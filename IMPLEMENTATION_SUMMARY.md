# Implementation Summary - Auto-Loop Status Monitoring

## Changes Made

### 1. Configuration (config.py)
Added new configuration section for status monitoring:

```python
# STATUS MONITORING (POST Q/E SEQUENCE)
STATUS_REGION_CROP = {
    'x': 634,
    'y': 60,
    'width': 331,
    'height': 14
}

STATUS_TEMPLATES_ALT = "templates/alt"
STATUS_TEMPLATES_WAIT = "templates/wait"

STATUS_CHECK_DELAY_MIN = 0.2  # seconds
STATUS_CHECK_DELAY_MAX = 0.3  # seconds
STATUS_INITIAL_WAIT = 2.5     # seconds

STATUS_CONFIDENCE_THRESHOLD = 0.8
STATUS_MAX_RETRIES = 5
STATUS_MAX_ITERATIONS = 50
```

### 2. New File: status_classifier.py
Created a new classifier for detecting 'alt' and 'wait' status templates.

**Key Classes:**
- `StatusClassifier` - Main interface for status detection
- `StatusTemplateClassifier` - Extends TemplateGlyphClassifier for alt/wait templates

**Features:**
- Loads templates from `templates/alt/` and `templates/wait/` folders
- Resizes templates to 331x14 pixels (status region size)
- Uses same template matching approach as Q/E classifier
- Higher confidence threshold (0.8 vs 0.7)

### 3. Updated: main_glyph_classifier.py
Removed CNN/hybrid approach, simplified to template-only:

**Changes:**
- Renamed `HybridGlyphClassifier` → `GlyphClassifier`
- Removed CNN imports and initialization
- Removed ensemble logic
- Always uses `method_used: 'template_matching'`
- Simplified CSV logging (removed cnn_confidence column)

### 4. Updated: alt_triggered_automation.py
Major automation flow changes:

**New Components:**
- `StatusClassifier` import and initialization
- `_crop_status_region()` - Crops 331x14 status region at (634, 60)
- `_status_monitoring_loop()` - Main auto-loop logic
- `_execute_qe_sequence()` - Separated Q/E sequence from monitoring

**Flow Changes:**

**Before:**
```
Human Alt → Q/E Sequence → Wait for next Human Alt
```

**After:**
```
Human Alt → Q/E Sequence → Status Monitoring Loop
                              ↓
                         Wait 2.5s
                              ↓
                    ┌─ Check status every 0.2-0.3s
                    │
                    ├─ "wait" → Continue loop
                    ├─ "alt" → Send Alt to ESP → Q/E Sequence → Loop
                    └─ No match (5 retries) → Exit to Idle
```

**Key Features:**
- Recursive loop: Alt detection triggers new Q/E sequence + monitoring
- Safety limits: Max 50 iterations, 5 retry attempts
- Random delays (0.2-0.3s) for human-like behavior
- Automatic Alt press via ESP32 when "alt" template detected

## New Automation Workflow

### State Flow Diagram

```
┌───────────────────────┐
│  IDLE                 │ ← Human presses Alt
│  (Wait for Alt)       │
└──────────┬────────────┘
           ↓
┌───────────────────────┐
│  Q/E SEQUENCE         │
│  - Wait 0.5s          │
│  - Capture pos 1→2→3  │
│  - Send Q/E to ESP32  │
└──────────┬────────────┘
           ↓
┌───────────────────────┐
│  POST-SEQUENCE WAIT   │
│  - Wait 2.5s          │
└──────────┬────────────┘
           ↓
    ┌─────────────────┐
    │ STATUS MONITOR  │
    │ iteration < 50? │
    └────────┬────────┘
             ↓
    ┌────────────────────┐
    │ Capture (634,60)   │
    │ 331x14 region      │
    └────────┬───────────┘
             ↓
    ┌────────────────────┐
    │ Classify: alt/wait │
    │ Conf >= 0.8?       │
    ├─ NO → retry (5x)  │
    │         ↓          │
    │    Exit to IDLE    │
    └────────┬───────────┘
             ↓ YES
    ┌────────────────────┐
    │ Which template?    │
    ├─ "wait" → loop ◄──┘
    │                    │
    ├─ "alt" → ESP Alt   │
    │    ↓               │
    │  Q/E SEQUENCE      │
    │    ↓               │
    │  STATUS MONITOR ◄──┘
    └────────────────────┘
```

## Template Folder Structure

You need to create these template folders:

```
templates/
├── q/              # Existing Q glyph templates
├── e/              # Existing E glyph templates
├── alt/            # NEW - Alt status indicator templates (331x14 PNG)
└── wait/           # NEW - Wait status indicator templates (331x14 PNG)
```

## Usage

### Running the Automation

```bash
python alt_triggered_automation.py
```

### Expected Console Output

```
======================================================================
🎮 Alt-Triggered MTA ESP32-S3 Automation (Auto-Loop)
======================================================================
📝 Workflow:
   1. Press Alt to trigger MTA UI (human or auto)
   2. System captures & classifies Q/E glyph positions
   3. Random delay applied before each ESP command
   4. After 3rd Q/E press: Wait 2.5s → Status monitoring
   5. Monitor status region every 0.2-0.3s:
      - 'wait' detected → Keep monitoring
      - 'alt' detected → Auto-trigger Alt → Repeat from step 2
      - No match (5 retries) → Return to idle
   6. Max 50 iterations before forced exit to idle

⌨️ Controls:
   - Alt: Trigger capture sequence
   - ESC: Exit the program

📊 Q/E Settings:
   - Crop coordinates: {1: (39, 943), 2: (97, 943), 3: (155, 943)}
   - Crop size: 26x26
   - Min confidence: 0.6
   - Initial delay: 0.5s
   - Capture delays: [0.0, 0.2, 0.2]

📊 Status Monitoring Settings:
   - Status region: (634, 60) 331x14
   - Check interval: 0.2-0.3s
   - Initial wait: 2.5s
   - Confidence threshold: 0.8
   - Max retries: 5
   - Max iterations: 50

📊 ESP32 Settings:
   - Port: COM3 (or auto-detect)
   - Random delay range: 50-200ms
======================================================================
🎯 Ready! Press Alt to start...
```

## Testing Steps

1. **Create template folders:**
   - Create `templates/alt/` folder
   - Create `templates/wait/` folder
   - Add PNG template images (331x14 pixels)

2. **Test status classifier standalone:**
   ```bash
   python status_classifier.py <test_status_image.png>
   ```

3. **Test Q/E classifier (template-only):**
   ```bash
   python main_glyph_classifier.py templates <test_glyph_image.png>
   ```

4. **Run full automation:**
   - Ensure ESP32 is connected
   - Ensure MTA: San Andreas window is open
   - Run: `python alt_triggered_automation.py`
   - Press Alt to start

## Configuration Tuning

Adjust in `config.py`:

### Timing
- `STATUS_INITIAL_WAIT` - Delay after Q/E sequence (default: 2.5s)
- `STATUS_CHECK_DELAY_MIN/MAX` - Random check interval (default: 0.2-0.3s)

### Thresholds
- `STATUS_CONFIDENCE_THRESHOLD` - Status detection confidence (default: 0.8)
- `TEMPLATE_CONFIDENCE_THRESHOLD` - Q/E detection confidence (default: 0.7)

### Safety Limits
- `STATUS_MAX_RETRIES` - No-match retries before exit (default: 5)
- `STATUS_MAX_ITERATIONS` - Max loop cycles (default: 50)

## Important Notes

1. **Template Quality:** Status templates (alt/wait) must be high quality 331x14 PNG images
2. **Screen Resolution:** Status crop coordinates (634, 60) are for specific resolution
3. **Recursion Safety:** Loop uses recursion but limited by max iterations
4. **ESP32 Required:** Alt auto-trigger requires working ESP32 connection
5. **Thread Safety:** All operations are thread-safe with proper locking

## Files Modified

✅ config.py - Added status monitoring config
✅ main_glyph_classifier.py - Simplified to template-only
✅ alt_triggered_automation.py - Added auto-loop logic
✅ status_classifier.py - NEW FILE for alt/wait detection

## Files Unchanged

- glyph_classifier_template.py
- glyph_classifier_cnn.py (present but unused)
- window_finder.py
- keyboard_interface.py
- esp_serial.py
- telegram_message.py

---

*Implementation completed: 2025-10-05*
