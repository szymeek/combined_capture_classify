# combined_capture_classify_esp.py
# -*- coding: utf-8 -*-

"""
Combined MTA screenshot capture, glyph classification, and ESP32-S3 communication.

Uses the existing keyboard_interface.py and esp_serial.py modules for ESP communication.

Dependencies: mss, opencv-python, pynput, pywin32, Pillow, numpy, pyserial

Usage:
python combined_capture_classify_esp.py --title "MTA: San Andreas" --save-dir screenshots --templates-path templates --esp-port COM3
"""

from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image
import cv2

from pynput import keyboard

from main_glyph_classifier import HybridGlyphClassifier
from window_finder import find_window, get_capture_bbox, ensure_foreground
from keyboard_interface import KeyboardInterface
from esp_serial import ESP32Serial
from config import MIN_CONFIDENCE_FOR_ESP_ACTION
import mss

class MTAESPAutomation:
    def __init__(
        self,
        title_contains: str,
        save_dir: str,
        templates_path: str,
        esp_port: Optional[str] = None,
        bring_foreground: bool = True,
        confidence_threshold: float = 0.7,
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

        # Crop coordinates for each position (26x26 crops)
        self._crop_coords = {
            1: (39, 943),   # Alt position
            2: (97, 943),   # First Q/E position  
            3: (155, 943),  # Second Q/E position
        }
        self._crop_size = 26

        self._lock = threading.Lock()
        self._cycle_position = 0
        self._total_processed = 0
        self._running = True

        self._last_ts = {"alt": 0.0, "q": 0.0, "e": 0.0}
        self._debounce_s = 0.08

        # Initialize hybrid glyph classifier
        print("Initializing hybrid glyph classifier...")
        self.classifier = HybridGlyphClassifier(templates_path, confidence_threshold)
        
        # Initialize keyboard interface (your existing system)
        print("Initializing ESP32-S3 keyboard interface...")
        self.keyboard = KeyboardInterface(esp_port if esp_port is not None else "")
        if not self.keyboard.initialize():
            raise SystemExit("Failed to initialize ESP32-S3 keyboard interface")
        
        print(f"🎮 MTA ESP Automation ready!")

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _get_cycle_position(self, keyname: str) -> int:
        with self._lock:
            if keyname == "alt":
                self._cycle_position = 1
            else:
                self._cycle_position += 1
                if self._cycle_position > 4:
                    self._cycle_position = 2
            return self._cycle_position

    def _safe_grab(self) -> Optional[np.ndarray]:
        try:
            if self.info is None:
                print("[warn] Window info is None, cannot capture.")
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
            print(f"[warn] capture failed: {e}")
            return None

    def _crop_frame(self, frame: np.ndarray, cycle_pos: int) -> Optional[np.ndarray]:
        if cycle_pos not in self._crop_coords:
            return None
        x, y = self._crop_coords[cycle_pos]
        size = self._crop_size
        if (y + size > frame.shape[0]) or (x + size > frame.shape[1]):
            print(f"[warn] crop coordinates ({x}, {y}) + {size}x{size} exceed frame bounds {frame.shape}")
            return None
        cropped = frame[y:y+size, x:x+size]
        return cropped

    def _process_classification(self, prediction: str, confidence: float, keyname: str, cycle_pos: int) -> bool:
        """Process classification result and send appropriate ESP commands"""
        
        if confidence < MIN_CONFIDENCE_FOR_ESP_ACTION:
            print(f"🔍 Confidence too low ({confidence:.3f}) - no ESP action taken")
            return False
        
        # Send appropriate key command to ESP32-S3
        esp_success = False
        
        if prediction == 'q':
            print(f"🎯 Detected Q glyph (conf: {confidence:.3f}) -> sending Q to ESP32")
            esp_success = self.keyboard.press_q()
        elif prediction == 'e':
            print(f"🎯 Detected E glyph (conf: {confidence:.3f}) -> sending E to ESP32") 
            esp_success = self.keyboard.press_e()
        else:
            print(f"❓ Unknown prediction: {prediction}")
            return False
        
        if esp_success:
            print(f"✅ Successfully sent {prediction.upper()} to ESP32-S3")
        else:
            print(f"❌ Failed to send {prediction.upper()} to ESP32-S3")
            
        return esp_success

    def _save_cropped_and_classify(self, cropped: np.ndarray, keyname: str, cycle_pos: int) -> str:
        ts = self._now_ms()
        with self._lock:
            self._total_processed += 1
            total_idx = self._total_processed

        # Save cropped image
        fname = f"{cycle_pos}_{keyname}_{ts}_{total_idx:04d}.png"
        path = self.save_dir / fname
        cv2.imwrite(str(path), cropped)

        # Convert cropped BGR to PIL grayscale for classification
        pil_img = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY))

        # Classify
        prediction, confidence, details = self.classifier.classify(pil_img)

        # Log results
        print(f"📸 {keyname} (pos {cycle_pos}) -> {path} | Prediction: {prediction} (conf: {confidence:.3f})")
        
        # Send to ESP32-S3 if we have Q or E detection at positions 2 or 3
        if cycle_pos in [2, 3] and prediction in ['q', 'e']:
            self._process_classification(prediction, confidence, keyname, cycle_pos)
        
        # Log to CSV
        self.classifier.log_result(str(path), prediction, confidence, details, 
                                 csv_path=str(self.save_dir / "results.csv"))

        return str(path)

    def _handle_keypress(self, keyname: str) -> None:
        now = time.perf_counter()
        last = self._last_ts.get(keyname, 0.0)
        if (now - last) < self._debounce_s:
            return
        self._last_ts[keyname] = now

        # Get cycle position before delays
        cycle_pos = self._get_cycle_position(keyname)

        # Position 4 is skipped
        if cycle_pos == 4:
            print(f"⏭️ {keyname} (pos {cycle_pos}) - skipping position 4")
            return

        # Apply custom delays based on cycle position
        if cycle_pos == 1:
            print(f"⏱️ Position 1 - waiting 500ms before capture")
            time.sleep(0.5)  # 500ms delay for the first screenshot
        else:
            print(f"⏱️ Position {cycle_pos} - waiting 200ms before capture")
            time.sleep(0.2)  # 200ms delay for rest

        frame = self._safe_grab()
        if frame is None:
            print(f"⚠️ No frame captured for key={keyname}")
            return

        cropped = self._crop_frame(frame, cycle_pos)
        if cropped is None:
            print(f"⚠️ Crop failed for key={keyname} at position {cycle_pos}")
            return

        self._save_cropped_and_classify(cropped, keyname, cycle_pos)

    def on_press(self, key) -> None:
        try:
            if hasattr(key, "char") and key.char is not None:
                ch = key.char.lower()
                if ch == "q":
                    self._handle_keypress("q")
                elif ch == "e":
                    self._handle_keypress("e")
            else:
                if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt):
                    self._handle_keypress("alt")
                elif key == keyboard.Key.esc:
                    print("🛑 ESC detected; exiting MTA ESP Automation...")
                    self._running = False
                    raise StopIteration
        except Exception as exc:
            print(f"❌ Keypress error: {exc}")
        return None

    def run(self) -> None:
        print("=" * 60)
        print("🎮 MTA ESP Automation Started")
        print("=" * 60)
        print("📝 Controls:")
        print("   - Alt/Q/E: Capture and classify glyphs")
        print("   - ESC: Exit the program")
        print()
        print("📊 Settings:")
        print(f"   - Crop coordinates: {self._crop_coords}")
        print(f"   - ESP32-S3 port: {self.keyboard.esp32.port}")
        print(f"   - Min confidence for ESP action: {MIN_CONFIDENCE_FOR_ESP_ACTION}")
        print()
        print("⏱️ Delays:")
        print("   - Position 1 (Alt): 500ms")
        print("   - Positions 2-3 (Q/E): 200ms")
        print("   - Position 4: Skipped")
        print("=" * 60)

        try:
            with keyboard.Listener(on_press=self.on_press) as listener:
                while self._running:
                    time.sleep(0.05)
                listener.stop()
        finally:
            # Clean up ESP connection
            self.keyboard.cleanup()
            print("👋 MTA ESP Automation stopped")


def main():
    ap = argparse.ArgumentParser(description="MTA ESP32-S3 Automation System")
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
    ap.add_argument("--list-ports", action="store_true",
                    help="List all available serial ports and exit")

    args = ap.parse_args()
    
    if args.list_ports:
        print("Available Serial Ports:")
        print("-" * 40)
        ports = ESP32Serial.list_available_ports()
        for port, description in ports:
            print(f"{port:<10} {description}")
        return

    try:
        automation = MTAESPAutomation(
            title_contains=args.title,
            save_dir=args.save_dir,
            bring_foreground=not args.no_foreground,
            templates_path=args.templates_path,
            esp_port=args.esp_port
        )

        automation.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
