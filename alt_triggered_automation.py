# alt_triggered_automation.py
# -*- coding: utf-8 -*-

"""
Simplified MTA ESP32-S3 Automation - Alt-triggered sequence with random ESP delays

Workflow:
1. Listen for Alt keypress (triggers MTA UI)
2. Sequentially capture and classify positions 1, 2, 3
3. Apply random delay before each ESP command (more human-like)
4. Send appropriate commands to ESP32-S3 for each detected glyph
5. Return to listening for next Alt press

Dependencies: mss, opencv-python, pynput, pywin32, Pillow, numpy, pyserial

Usage:
python alt_triggered_automation.py [--override-options]
"""

from __future__ import annotations

import argparse
import threading
import time
import random
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image
import cv2

from pynput import keyboard

from main_glyph_classifier import GlyphClassifier
from window_finder import find_window, get_capture_bbox, ensure_foreground
from keyboard_interface import KeyboardInterface
import config
import mss

from telegram_message import send_message
import asyncio

class AltTriggeredAutomation:
    def __init__(
        self,
        title_contains: Optional[str] = None,
        save_dir: Optional[str] = None,
        templates_path: Optional[str] = None,
        esp_port: Optional[str] = None,
        bring_foreground: Optional[bool] = None,
        confidence_threshold: Optional[float] = None,
        esp_delay_range: Optional[Tuple[int, int]] = None,
    ) -> None:
        # Use config values as defaults, allow overrides
        self.title_contains = title_contains or config.WINDOW_TITLE
        self.save_dir = Path(save_dir or config.SCREENSHOTS_DIR)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # Initialize window finder
        self.info = find_window(title_contains=self.title_contains)
        if self.info is None:
            raise SystemExit(f"Window not found containing title: {self.title_contains}")
        if bring_foreground if bring_foreground is not None else config.BRING_WINDOW_TO_FOREGROUND:
            ensure_foreground(self.info.hwnd)

        # Use config crop coordinates and size
        self._crop_coords = config.CROP_COORDINATES.copy()
        self._crop_size = config.CROP_SIZE

        self._lock = threading.Lock()
        self._total_processed = 0
        self._running = True
        self._processing_sequence = False  # Flag to prevent overlapping sequences

        self._last_alt_press = 0.0
        self._debounce_s = config.ALT_DEBOUNCE_TIME

        # MSS instance - will be created per thread due to thread-local storage requirements
        self._sct_lock = threading.Lock()
        self._sct_instances = {}  # Thread ID -> mss instance mapping

        # Timing settings from config
        self._initial_delay = config.INITIAL_DELAY
        self._capture_delays = config.CAPTURE_DELAYS.copy()

        # ESP random delay settings
        esp_range = esp_delay_range or (config.ESP_DELAY_MIN, config.ESP_DELAY_MAX)
        self._esp_delay_min, self._esp_delay_max = esp_range
        print(f"🎲 ESP random delay range: {self._esp_delay_min}-{self._esp_delay_max}ms")

        # Initialize random seed for ESP delays
        random.seed()

        # Initialize glyph classifier
        print("🔍 Initializing template-based glyph classifier...")
        templates_path = templates_path or config.TEMPLATES_PATH
        confidence_threshold = confidence_threshold or config.TEMPLATE_CONFIDENCE_THRESHOLD
        self.classifier = GlyphClassifier(templates_path, confidence_threshold)

        # Initialize ESP32-S3 keyboard interface
        print("🎮 Initializing ESP32-S3 keyboard interface...")
        esp_port = esp_port or config.ESP32_PORT
        self.keyboard = KeyboardInterface(esp_port or "")
        if not self.keyboard.initialize():
            raise SystemExit("❌ Failed to initialize ESP32-S3 keyboard interface")

        print("✅ Alt-triggered automation ready!")

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _get_random_esp_delay(self) -> int:
        """Generate random delay using normal distribution for more human-like timing"""
        # Use normal distribution instead of uniform for more realistic human-like delays
        mean = (self._esp_delay_min + self._esp_delay_max) / 2
        std_dev = (self._esp_delay_max - self._esp_delay_min) / 6  # 99.7% within range

        delay = int(random.gauss(mean, std_dev))
        # Clamp to min/max range
        return max(self._esp_delay_min, min(self._esp_delay_max, delay))

    def _get_thread_mss(self) -> mss.mss:
        """Get or create mss instance for current thread"""
        thread_id = threading.get_ident()

        with self._sct_lock:
            if thread_id not in self._sct_instances:
                self._sct_instances[thread_id] = mss.mss()

        return self._sct_instances[thread_id]

    def _safe_grab(self) -> Optional[np.ndarray]:
        """Capture screenshot of MTA window using thread-local mss instance"""
        try:
            if self.info is None:
                print("⚠️ Window info is None, cannot capture screen.")
                return None
            bbox = get_capture_bbox(self.info)
            monitor = {
                "left": bbox[0],
                "top": bbox[1],
                "width": bbox[2],
                "height": bbox[3]
            }
            # Get thread-local mss instance
            sct = self._get_thread_mss()
            screenshot = sct.grab(monitor)
            frame = np.asarray(screenshot, dtype=np.uint8)[..., :3]
            return frame
        except Exception as e:
            print(f"⚠️ Capture failed: {e}")
            return None

    def _crop_frame(self, frame: np.ndarray, position: int) -> Optional[np.ndarray]:
        """Crop frame to specified size at position coordinates from config"""
        if position not in self._crop_coords:
            return None
        x, y = self._crop_coords[position]
        size = self._crop_size

        if (y + size > frame.shape[0]) or (x + size > frame.shape[1]):
            print(f"⚠️ Crop coordinates ({x}, {y}) + {size}x{size} exceed frame bounds {frame.shape}")
            return None

        cropped = frame[y:y+size, x:x+size]
        return cropped

    def _process_classification(self, prediction: str, confidence: float, position: int) -> bool:
        """Process classification result and send appropriate ESP commands with random delay"""

        if confidence < config.MIN_CONFIDENCE_FOR_ESP_ACTION:
            print(f"   🔍 Confidence too low ({confidence:.3f}) - no ESP action")
            return False

        # Generate random delay before ESP command
        esp_delay = self._get_random_esp_delay()
        print(f"   🎲 Random ESP delay: {esp_delay}ms")
        time.sleep(esp_delay / 1000.0)  # Convert to seconds

        # Send appropriate key command to ESP32-S3
        esp_success = False

        if prediction == 'q':
            print(f"   🎯 Detected Q glyph (conf: {confidence:.3f}) -> sending Q to ESP32")
            esp_success = self.keyboard.press_q()
        elif prediction == 'e':
            print(f"   🎯 Detected E glyph (conf: {confidence:.3f}) -> sending E to ESP32") 
            esp_success = self.keyboard.press_e()
        else:
            print(f"   ❓ Unknown prediction: {prediction}")
            return False

        if esp_success:
            print(f"   ✅ Successfully sent {prediction.upper()} to ESP32-S3")
        else:
            print(f"   ❌ Failed to send {prediction.upper()} to ESP32-S3")

        return esp_success

    def _capture_classify_and_send(self, position: int) -> bool:
        """Capture, classify and send ESP command for a specific position"""

        # Apply position-specific delay
        if position <= len(self._capture_delays) and self._capture_delays[position-1] > 0:
            time.sleep(self._capture_delays[position-1])

        # Capture screenshot
        frame = self._safe_grab()
        if frame is None:
            print(f"   ❌ Failed to capture frame for position {position}")
            return False

        # Crop to glyph area
        cropped = self._crop_frame(frame, position)
        if cropped is None:
            print(f"   ❌ Failed to crop frame for position {position}")
            return False

        # Save cropped image if enabled
        if config.SAVE_CROPPED_IMAGES:
            ts = self._now_ms()
            with self._lock:
                self._total_processed += 1
                total_idx = self._total_processed

            fname = f"pos{position}_alt_seq_{ts}_{total_idx:04d}.png"
            path = self.save_dir / fname
            cv2.imwrite(str(path), cropped)
        else:
            fname = "not_saved"
            path = f"pos{position}_temp"

        # Convert to PIL for classification
        pil_img = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY))

        # Classify the glyph
        prediction, confidence, details = self.classifier.classify(pil_img)

        print(f"   📸 Position {position}: {prediction} (conf: {confidence:.3f}) -> {fname if config.SAVE_CROPPED_IMAGES else 'not saved'}")

        # Send to ESP32-S3 if confident enough (with random delay)
        esp_sent = self._process_classification(prediction, confidence, position)

        # Log to CSV if enabled
        if config.LOG_TO_CSV:
            csv_path = self.save_dir / config.RESULTS_CSV
            self.classifier.log_result(str(path), prediction, confidence, details, 
                                     csv_path=str(csv_path))

        return True

    def _execute_sequence(self):
        """Execute the full 3-position capture sequence"""
        with self._lock:
            if self._processing_sequence:
                print("⚠️ Sequence already in progress, ignoring Alt press")
                return
            self._processing_sequence = True

        try:
            print("🚀 Starting Alt-triggered sequence...")

            # Initial delay for UI to appear
            print(f"   ⏱️ Waiting {self._initial_delay}s for UI to appear...")
            time.sleep(self._initial_delay)

            # Process each position sequentially
            success_count = 0
            positions = list(self._crop_coords.keys())

            for position in positions:
                print(f"   🎯 Processing position {position}...")
                if self._capture_classify_and_send(position):
                    success_count += 1
                else:
                    print(f"   ⚠️ Position {position} processing failed")

            print(f"✅ Sequence completed! ({success_count}/{len(positions)} positions processed)")
            print("🔄 Ready for next Alt press...")

        except Exception as e:
            print(f"❌ Sequence error: {e}")
        finally:
            with self._lock:
                self._processing_sequence = False

    def _handle_alt_press(self):
        """Handle Alt key press - trigger the full sequence"""
        now = time.perf_counter()

        # Debounce check with thread safety
        with self._lock:
            if (now - self._last_alt_press) < self._debounce_s:
                return
            self._last_alt_press = now

        print(f"\n🎮 Alt pressed! Triggering capture sequence...")

        # Run sequence in a separate thread to avoid blocking key listener
        sequence_thread = threading.Thread(target=self._execute_sequence, daemon=True)
        sequence_thread.start()

    def on_press(self, key) -> None:
        """Handle key press events"""
        try:
            # Only listen for Alt and ESC keys
            if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt):
                self._handle_alt_press()
            elif key == keyboard.Key.esc:
                print("\n🛑 ESC detected; exiting Alt-triggered automation...")
                self._running = False
                raise StopIteration

        except Exception as exc:
            print(f"❌ Keypress error: {exc}")
        return None

    def run(self) -> None:
        """Main automation loop"""
        print("=" * 70)
        print("🎮 Alt-Triggered MTA ESP32-S3 Automation (Template Matching)")
        print("=" * 70)
        print("📝 Workflow:")
        print("   1. Press Alt to trigger MTA UI")
        print("   2. System captures & classifies glyph positions")
        print("   3. Random delay applied before each ESP command")
        print("   4. ESP32-S3 sends detected keys automatically")
        print("   5. Ready for next Alt press")
        print()
        print("⌨️ Controls:")
        print("   - Alt: Trigger capture sequence")
        print("   - ESC: Exit the program")
        print()
        print("📊 Settings:")
        print(f"   - Crop coordinates: {self._crop_coords}")
        print(f"   - Crop size: {self._crop_size}x{self._crop_size}")
        print(f"   - ESP32-S3 port: {self.keyboard.esp32.port}")
        print(f"   - Min confidence for ESP action: {config.MIN_CONFIDENCE_FOR_ESP_ACTION}")
        print(f"   - Initial delay: {self._initial_delay}s")
        print(f"   - Capture delays: {self._capture_delays}")
        print(f"   - ESP random delay range: {self._esp_delay_min}-{self._esp_delay_max}ms")
        print("=" * 70)
        print("🎯 Ready! Press Alt to start...")

        try:
            with keyboard.Listener(on_press=self.on_press) as listener:
                while self._running:
                    time.sleep(0.1)
                listener.stop()
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        finally:
            # Clean up resources
            self.keyboard.cleanup()

            # Close all thread-local mss instances
            with self._sct_lock:
                for sct_instance in self._sct_instances.values():
                    try:
                        sct_instance.close()
                    except:
                        pass
                self._sct_instances.clear()

            print("👋 Alt-triggered automation stopped")


def main():
    # Print config summary first
    if config.VERBOSE_LOGGING:
        config.print_config_summary()
        
        # Validate config
        errors = config.validate_config()
        if errors:
            print("❌ Configuration errors found:")
            for error in errors:
                print(f"  - {error}")
            return

    ap = argparse.ArgumentParser(description="Alt-Triggered MTA ESP32-S3 Automation with Random Delays")
    ap.add_argument("--title", default=None,
                    help=f"Window title to capture from (default: {config.WINDOW_TITLE})")
    ap.add_argument("--save-dir", default=None,
                    help=f"Directory to save screenshots (default: {config.SCREENSHOTS_DIR})")
    ap.add_argument("--templates-path", default=None,
                    help=f"Path to templates folder (default: {config.TEMPLATES_PATH})")
    ap.add_argument("--esp-port", default=None,
                    help="ESP32-S3 COM port (overrides config)")
    ap.add_argument("--no-foreground", action="store_true",
                    help="Don't bring MTA window to foreground")
    ap.add_argument("--initial-delay", type=float, default=None,
                    help=f"Delay after Alt press (default: {config.INITIAL_DELAY}s)")
    ap.add_argument("--capture-delay", type=float, default=None,
                    help="Delay between captures (overrides config)")
    ap.add_argument("--esp-delay-range", nargs=2, type=int, default=None, 
                    metavar=("MIN", "MAX"),
                    help=f"Random delay range in ms (default: {config.ESP_DELAY_MIN} {config.ESP_DELAY_MAX})")

    args = ap.parse_args()

    # Validate ESP delay range if provided
    if args.esp_delay_range:
        if args.esp_delay_range[0] >= args.esp_delay_range[1]:
            print("❌ Error: ESP delay minimum must be less than maximum")
            return
        if args.esp_delay_range[0] < 0:
            print("❌ Error: ESP delay values must be non-negative")
            return

    try:
        automation = AltTriggeredAutomation(
            title_contains=args.title,
            save_dir=args.save_dir,
            templates_path=args.templates_path,
            bring_foreground=not args.no_foreground if args.no_foreground else None,
            esp_port=args.esp_port,
            esp_delay_range=tuple(args.esp_delay_range) if args.esp_delay_range else None
        )

        # Apply custom timing if specified
        if args.initial_delay is not None:
            automation._initial_delay = args.initial_delay
        if args.capture_delay is not None:
            automation._capture_delays = [0.0, args.capture_delay, args.capture_delay]

        automation.run()

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()