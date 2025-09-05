# -*- coding: utf-8 -*-

"""
Combined MTA screenshot capture and glyph classification.

Captures screenshots on keypresses (Alt, Q, E) in the MTA window client area,
crops the relevant glyph area, and classifies using a hybrid template + CNN classifier.

Custom delays: Position 1 (Alt) = 500ms, Positions 2-3 (Q/E) = 200ms

Dependencies: mss, opencv-python, pynput, pywin32, Pillow, numpy

Usage:
python combined_capture_classify.py --title "MTA: San Andreas" --save-dir screenshots --templates-path templates
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
import mss

class KeypressCaptureClassifier:
    def __init__(
        self,
        title_contains: str,
        save_dir: str,
        templates_path: str,
        bring_foreground: bool = True,
        confidence_threshold: float = 0.7,
    ) -> None:
        self.title_contains = title_contains
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.info = find_window(title_contains=self.title_contains)
        if self.info is None:
            raise SystemExit(f"Window not found containing title: {self.title_contains}")
        if bring_foreground:
            ensure_foreground(self.info.hwnd)

        # Crop coordinates for each position (26x26 crops)
        self._crop_coords = {
            1: (39, 943),  # Alt position
            2: (97, 943),  # First Q/E position
            3: (155, 943), # Second Q/E position
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
        print(f"[ok] {keyname} (pos {cycle_pos}) -> {path} | Prediction: {prediction} (conf: {confidence:.3f})")
        self.classifier.log_result(str(path), prediction, confidence, details, csv_path=str(self.save_dir / "results.csv"))

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
            print(f"[skip] {keyname} (pos {cycle_pos}) - not saving position 4")
            return

        # Apply custom delays based on cycle position
        if cycle_pos == 1:
            print(f"[delay] Position 1 - waiting 500ms before capture")
            time.sleep(0.5)  # 500ms delay for the first screenshot
        else:
            print(f"[delay] Position {cycle_pos} - waiting 200ms before capture")
            time.sleep(0.2)  # 200ms delay for rest

        frame = self._safe_grab()
        if frame is None:
            print(f"[warn] no frame for key={keyname}")
            return

        cropped = self._crop_frame(frame, cycle_pos)
        if cropped is None:
            print(f"[warn] crop failed for key={keyname} at position {cycle_pos}")
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
                    print("[info] ESC detected; exiting.")
                    self._running = False
                    raise StopIteration
        except Exception as exc:
            print(f"[err] on_press error: {exc}")
        return None

    def run(self) -> None:
        print("[info] Listening for Alt / Q / E ... (ESC to quit)")
        print(f"[info] Saving and classifying positions 1-3 as 26x26 crops at coords: {self._crop_coords}")
        print("[info] Position 4 is skipped")
        print("[info] Delays: Position 1 (Alt) = 500ms, Positions 2-3 (Q/E) = 200ms")

        with keyboard.Listener(on_press=self.on_press) as listener:
            while self._running:
                time.sleep(0.05)
            listener.stop()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="MTA: San Andreas")
    ap.add_argument("--save-dir", default="screenshots")
    ap.add_argument("--templates-path", required=True,
                    help="Path to templates folder containing 'q' and 'e' subdirectories")
    ap.add_argument("--no-foreground", action="store_true")

    args = ap.parse_args()

    kc = KeypressCaptureClassifier(
        title_contains=args.title,
        save_dir=args.save_dir,
        bring_foreground=not args.no_foreground,
        templates_path=args.templates_path
    )

    kc.run()


if __name__ == "__main__":
    main()
