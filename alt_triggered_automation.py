
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
python alt_triggered_automation.py --templates-path templates --esp-port COM3 --esp-delay-range 50 150
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

from main_glyph_classifier import HybridGlyphClassifier
from window_finder import find_window, get_capture_bbox, ensure_foreground
from keyboard_interface import KeyboardInterface
from config import MIN_CONFIDENCE_FOR_ESP_ACTION
import mss

class AltTriggeredAutomation:
    def __init__(
        self,
        title_contains: str,
        save_dir: str,
        templates_path: str,
        esp_port: Optional[str] = None,
        bring_foreground: bool = True,
        confidence_threshold: float = 0.7,
        esp_delay_range: Tuple[int, int] = (50, 200),  # Default 50-200ms random delay
    ) -> None:
        self.title_contains = title_contains
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # Initialize window finder
        self.info = find_window(title_contains=self.title_contains)
        if self.info is None:
            raise SystemExit(f"Window not found containing title: {self.title_contains}")
        if bring_foreground:
            ensure_foreground(self.info.hwnd)

        # Crop coordinates for the 3 sequential positions (26x26 crops)
        self._crop_coords = {
            1: (39, 943),   # First glyph position
            2: (97, 943),   # Second glyph position  
            3: (155, 943),  # Third glyph position
        }
        self._crop_size = 26

        self._lock = threading.Lock()
        self._total_processed = 0
        self._running = True
        self._processing_sequence = False  # Flag to prevent overlapping sequences

        self._last_alt_press = 0.0
        self._debounce_s = 0.5  # Longer debounce to prevent accidental double-triggers

        # Timing settings
        self._initial_delay = 0.5    # Wait after Alt press for UI to appear
        self._capture_delays = [0.0, 0.2, 0.2]  # Delays before each capture

        # ESP random delay settings
        self._esp_delay_min, self._esp_delay_max = esp_delay_range
        print(f"🎲 ESP random delay range: {self._esp_delay_min}-{self._esp_delay_max}ms")

        # Initialize random seed for ESP delays
        random.seed()

        # Initialize hybrid glyph classifier
        print("🔍 Initializing hybrid glyph classifier...")
        self.classifier = HybridGlyphClassifier(templates_path, confidence_threshold)

        # Initialize ESP32-S3 keyboard interface
        print("🎮 Initializing ESP32-S3 keyboard interface...")
        self.keyboard = KeyboardInterface(esp_port if esp_port is not None else "")
        if not self.keyboard.initialize():
            raise SystemExit("❌ Failed to initialize ESP32-S3 keyboard interface")

        print("✅ Alt-triggered automation ready!")

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _get_random_esp_delay(self) -> int:
        """Generate random delay in milliseconds for ESP command"""
        return random.randint(self._esp_delay_min, self._esp_delay_max)

    def _safe_grab(self) -> Optional[np.ndarray]:
        """Capture screenshot of MTA window"""
        try:
            if self.info is None:
                print("⚠️ Window info is None, cannot capture screen.")
                return None
            bbox = get_capture_bbox(self.info)
            with mss.mss() as sct:
                monitor = {
                    "left": bbox[0],
                    "top": bbox[1],
                    "width": bbox[2],
                    "height": bbox[3]
                }
                screenshot = sct.grab(monitor)
                frame = np.asarray(screenshot, dtype=np.uint8)[..., :3]
                return frame
        except Exception as e:
            print(f"⚠️ Capture failed: {e}")
            return None

    def _crop_frame(self, frame: np.ndarray, position: int) -> Optional[np.ndarray]:
        """Crop frame to 26x26 at specified position coordinates"""
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

        if confidence < MIN_CONFIDENCE_FOR_ESP_ACTION:
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
        if self._capture_delays[position-1] > 0:
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

        # Save cropped image
        ts = self._now_ms()
        with self._lock:
            self._total_processed += 1
            total_idx = self._total_processed

        fname = f"pos{position}_alt_seq_{ts}_{total_idx:04d}.png"
        path = self.save_dir / fname
        cv2.imwrite(str(path), cropped)

        # Convert to PIL for classification
        pil_img = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY))

        # Classify the glyph
        prediction, confidence, details = self.classifier.classify(pil_img)

        print(f"   📸 Position {position}: {prediction} (conf: {confidence:.3f}) -> {fname}")

        # Send to ESP32-S3 if confident enough (with random delay)
        esp_sent = self._process_classification(prediction, confidence, position)

        # Log to CSV
        self.classifier.log_result(str(path), prediction, confidence, details, 
                                 csv_path=str(self.save_dir / "results.csv"))

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
            esp_commands_sent = 0

            for position in [1, 2, 3]:
                print(f"   🎯 Processing position {position}...")
                if self._capture_classify_and_send(position):
                    success_count += 1
                    # Note: ESP command success is handled inside _process_classification
                else:
                    print(f"   ⚠️ Position {position} processing failed")

            print(f"✅ Sequence completed! ({success_count}/3 positions processed)")
            print("🔄 Ready for next Alt press...")

        except Exception as e:
            print(f"❌ Sequence error: {e}")
        finally:
            with self._lock:
                self._processing_sequence = False

    def _handle_alt_press(self):
        """Handle Alt key press - trigger the full sequence"""
        now = time.perf_counter()

        # Debounce check
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
        print("🎮 Alt-Triggered MTA ESP32-S3 Automation (with Random Delays)")
        print("=" * 70)
        print("📝 Workflow:")
        print("   1. Press Alt to trigger MTA UI")
        print("   2. System captures & classifies 3 glyph positions")
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
        print(f"   - ESP32-S3 port: {self.keyboard.esp32.port}")
        print(f"   - Min confidence for ESP action: {MIN_CONFIDENCE_FOR_ESP_ACTION}")
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
            # Clean up ESP connection
            self.keyboard.cleanup()
            print("👋 Alt-triggered automation stopped")


def main():
    ap = argparse.ArgumentParser(description="Alt-Triggered MTA ESP32-S3 Automation with Random Delays")
    ap.add_argument("--title", default="MTA: San Andreas",
                    help="Window title to capture from")
    ap.add_argument("--save-dir", default="screenshots",
                    help="Directory to save screenshots")
    ap.add_argument("--templates-path", required=True,
                    help="Path to templates folder containing 'q' and 'e' subdirectories")
    ap.add_argument("--esp-port", default=None,
                    help="ESP32-S3 COM port (auto-detect if not specified)")
    ap.add_argument("--no-foreground", action="store_true",
                    help="Don't bring MTA window to foreground")
    ap.add_argument("--initial-delay", type=float, default=0.5,
                    help="Delay after Alt press before first capture (seconds)")
    ap.add_argument("--capture-delay", type=float, default=0.2,
                    help="Delay between captures (seconds)")
    ap.add_argument("--esp-delay-range", nargs=2, type=int, default=[50, 200], 
                    metavar=("MIN", "MAX"),
                    help="Random delay range before ESP commands in milliseconds (default: 50 200)")

    args = ap.parse_args()

    # Validate ESP delay range
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
            bring_foreground=not args.no_foreground,
            templates_path=args.templates_path,
            esp_port=args.esp_port,
            esp_delay_range=tuple(args.esp_delay_range)
        )

        # Apply custom timing if specified
        if args.initial_delay != 0.5:
            automation._initial_delay = args.initial_delay
        if args.capture_delay != 0.2:
            automation._capture_delays = [0.0, args.capture_delay, args.capture_delay]

        automation.run()

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
