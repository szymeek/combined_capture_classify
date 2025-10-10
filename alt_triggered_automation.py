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
from status_classifier import StatusClassifier
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
        self._stop_monitoring = False  # Flag to immediately stop monitoring loop (S key pressed)

        self._last_alt_press = 0.0
        self._debounce_s = config.ALT_DEBOUNCE_TIME

        # MSS instance - will be created per thread due to thread-local storage requirements
        self._sct_lock = threading.Lock()
        self._sct_instances = {}  # Thread ID -> mss instance mapping

        # Timing settings from config
        self._initial_delay = config.INITIAL_DELAY
        self._capture_delays = config.CAPTURE_DELAYS.copy()  # List of (min, max) tuples

        # ESP random delay settings
        esp_range = esp_delay_range or (config.ESP_DELAY_MIN, config.ESP_DELAY_MAX)
        self._esp_delay_min, self._esp_delay_max = esp_range
        print(f"ESP random delay range: {self._esp_delay_min}-{self._esp_delay_max}ms")

        # Initialize random seed for ESP delays
        random.seed()

        # Initialize glyph classifier
        print(" Initializing template-based glyph classifier...")
        templates_path = templates_path or config.TEMPLATES_PATH
        confidence_threshold = confidence_threshold or config.TEMPLATE_CONFIDENCE_THRESHOLD
        self.classifier = GlyphClassifier(templates_path, confidence_threshold)

        # Initialize status classifier for alt/wait detection
        print(" Initializing status classifier...")
        self.status_classifier = StatusClassifier()

        # Initialize ESP32-S3 keyboard interface
        print(" Initializing ESP32-S3 keyboard interface...")
        esp_port = esp_port or config.ESP32_PORT
        self.keyboard = KeyboardInterface(esp_port or "")
        if not self.keyboard.initialize():
            raise SystemExit(" Failed to initialize ESP32-S3 keyboard interface")

        print(" Alt-triggered automation ready!")

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

    def _crop_status_region(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Crop frame to status region for alt/wait detection"""
        x = config.STATUS_REGION_CROP['x']
        y = config.STATUS_REGION_CROP['y']
        width = config.STATUS_REGION_CROP['width']
        height = config.STATUS_REGION_CROP['height']

        if (y + height > frame.shape[0]) or (x + width > frame.shape[1]):
            print(f" Status crop coordinates ({x}, {y}) + {width}x{height} exceed frame bounds {frame.shape}")
            return None

        cropped = frame[y:y+height, x:x+width]
        return cropped

    def _crop_end_region(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Crop frame to end region for end detection"""
        x = config.END_REGION_CROP['x']
        y = config.END_REGION_CROP['y']
        width = config.END_REGION_CROP['width']
        height = config.END_REGION_CROP['height']

        if (y + height > frame.shape[0]) or (x + width > frame.shape[1]):
            print(f" End crop coordinates ({x}, {y}) + {width}x{height} exceed frame bounds {frame.shape}")
            return None

        cropped = frame[y:y+height, x:x+width]
        return cropped

    def _process_classification(self, prediction: str, confidence: float, position: int) -> bool:
        """Process classification result and send appropriate ESP commands with random delay"""

        if confidence < config.MIN_CONFIDENCE_FOR_ESP_ACTION:
            print(f"    Confidence too low ({confidence:.3f}) - no ESP action")
            return False

        # Generate random delay before ESP command
        esp_delay = self._get_random_esp_delay()
        print(f"    Random ESP delay: {esp_delay}ms")
        time.sleep(esp_delay / 1000.0)  # Convert to seconds

        # Send appropriate key command to ESP32-S3
        esp_success = False

        if prediction == 'q':
            print(f"    Detected Q glyph (conf: {confidence:.3f}) -> sending Q to ESP32")
            esp_success = self.keyboard.press_q()
        elif prediction == 'e':
            print(f"    Detected E glyph (conf: {confidence:.3f}) -> sending E to ESP32") 
            esp_success = self.keyboard.press_e()
        else:
            print(f"    Unknown prediction: {prediction}")
            return False

        if esp_success:
            print(f"    Successfully sent {prediction.upper()} to ESP32-S3")
        else:
            print(f"    Failed to send {prediction.upper()} to ESP32-S3")

        return esp_success

    def _capture_classify_and_send(self, position: int) -> bool:
        """Capture, classify and send ESP command for a specific position"""

        # Apply position-specific random delay from range
        if position <= len(self._capture_delays):
            delay_min, delay_max = self._capture_delays[position-1]
            random_delay = random.uniform(delay_min, delay_max)
            print(f"    Capture delay for position {position}: {random_delay:.3f}s")
            time.sleep(random_delay)

        # Capture screenshot
        frame = self._safe_grab()
        if frame is None:
            print(f"    Failed to capture frame for position {position}")
            return False

        # Crop to glyph area
        cropped = self._crop_frame(frame, position)
        if cropped is None:
            print(f"    Failed to crop frame for position {position}")
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

        print(f"    Position {position}: {prediction} (conf: {confidence:.3f}) -> {fname if config.SAVE_CROPPED_IMAGES else 'not saved'}")

        # Send to ESP32-S3 if confident enough (with random delay)
        esp_sent = self._process_classification(prediction, confidence, position)

        # Log to CSV if enabled
        if config.LOG_TO_CSV:
            csv_path = self.save_dir / config.RESULTS_CSV
            self.classifier.log_result(str(path), prediction, confidence, details, 
                                     csv_path=str(csv_path))

        return True

    def _status_monitoring_loop(self):
        """Monitor status region for alt/wait detection after Q/E sequence"""
        print(f"\n Starting status monitoring loop...")
        print(f"   ⏱️ Initial wait: {config.STATUS_INITIAL_WAIT}s")
        time.sleep(config.STATUS_INITIAL_WAIT)

        no_match_count = 0
        iteration_count = 0
        exit_reason = ""  # Track why we're exiting

        while iteration_count < config.STATUS_MAX_ITERATIONS and self._running and not self._stop_monitoring:
            # Random delay between checks
            delay = random.uniform(config.STATUS_CHECK_DELAY_MIN, config.STATUS_CHECK_DELAY_MAX)
            time.sleep(delay)

            # Capture screenshot
            frame = self._safe_grab()
            if frame is None:
                print(f"    Failed to capture frame in status monitoring")
                no_match_count += 1
                if no_match_count >= config.STATUS_MAX_RETRIES:
                    print(f"    Too many capture failures, exiting monitoring loop")
                    exit_reason = f"Too many capture failures ({config.STATUS_MAX_RETRIES} retries)"
                    break
                continue

            # FIRST: Check for 'end' status (takes priority)
            end_cropped = self._crop_end_region(frame)
            if end_cropped is not None:
                try:
                    pil_end_img = Image.fromarray(cv2.cvtColor(end_cropped, cv2.COLOR_BGR2GRAY))
                    end_prediction, end_confidence, end_details = self.status_classifier.classify(pil_end_img, region_type="end")

                    iteration_count += 1
                    print(f"    Iteration {iteration_count}: Checking END - {end_prediction} (conf: {end_confidence:.3f})")

                    if end_prediction == "end" and end_confidence >= config.STATUS_CONFIDENCE_THRESHOLD:
                        print(f"    END detected! Exiting to idle state...")

                        # Send telegram message
                        try:
                            message = f"END detected! Confidence: {end_confidence:.3f}\nExiting to idle state."
                            asyncio.run(send_message(message))
                            print(f"    Telegram message sent: END detected")
                        except Exception as telegram_error:
                            print(f"    Failed to send Telegram message: {telegram_error}")

                        break  # Exit monitoring loop, return to idle

                except Exception as e:
                    print(f"    End classification error: {e}")

            # SECOND: Check for 'alt' or 'wait' status
            cropped = self._crop_status_region(frame)
            if cropped is None:
                print(f"    Failed to crop status region")
                no_match_count += 1
                if no_match_count >= config.STATUS_MAX_RETRIES:
                    print(f"    Too many crop failures, exiting monitoring loop")
                    exit_reason = f"Too many crop failures ({config.STATUS_MAX_RETRIES} retries)"
                    break
                continue

            # Convert to PIL for classification
            pil_img = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY))

            # Classify status region
            try:
                prediction, confidence, details = self.status_classifier.classify(pil_img, region_type="status")

                print(f"    Status check: {prediction} (conf: {confidence:.3f})")

                # Check if confident match
                if confidence >= config.STATUS_CONFIDENCE_THRESHOLD:
                    no_match_count = 0  # Reset retry counter

                    if prediction == "wait":
                        # Keep waiting
                        print(f"    Status: WAIT - continuing monitoring...")
                        continue

                    elif prediction == "alt":
                        # Trigger Alt and restart Q/E sequence
                        print(f"    Status: ALT detected - triggering automated Alt press!")

                        # Send Alt to ESP32
                        if self.keyboard.press_alt():
                            print(f"    Alt signal sent to ESP32")
                        else:
                            print(f"    Failed to send Alt to ESP32")

                        # Execute Q/E sequence
                        self._execute_qe_sequence()

                        # After sequence, restart monitoring (recursive call)
                        print(f"    Restarting status monitoring after Q/E sequence...")
                        self._status_monitoring_loop()
                        return  # Exit this loop instance

                else:
                    # Low confidence - no clear match
                    no_match_count += 1
                    print(f"    Low confidence ({confidence:.3f}) - no match count: {no_match_count}/{config.STATUS_MAX_RETRIES}")

                    if no_match_count >= config.STATUS_MAX_RETRIES:
                        print(f"    Max retries reached, exiting monitoring loop")
                        exit_reason = f"Max retries reached - low confidence matches ({config.STATUS_MAX_RETRIES} retries)"
                        break

            except Exception as e:
                print(f"    Status classification error: {e}")
                no_match_count += 1
                if no_match_count >= config.STATUS_MAX_RETRIES:
                    print(f"    Too many errors, exiting monitoring loop")
                    exit_reason = f"Too many classification errors ({config.STATUS_MAX_RETRIES} retries)"
                    break

        # Exit monitoring loop - set reason if not already set
        if not exit_reason and iteration_count >= config.STATUS_MAX_ITERATIONS:
            print(f"    Max iterations ({config.STATUS_MAX_ITERATIONS}) reached, exiting monitoring")
            exit_reason = f"Max iterations ({config.STATUS_MAX_ITERATIONS}) reached"

        with self._lock:
            if self._stop_monitoring:
                print(f"    Monitoring stopped by S key")
                exit_reason = "Monitoring stopped by S key"
                self._stop_monitoring = False  # Reset flag

        # Send telegram message when returning to idle state (except for S key stop)
        if exit_reason and exit_reason != "Monitoring stopped by S key":
            try:
                message = f"Returning to IDLE state.\nReason: {exit_reason}"
                asyncio.run(send_message(message))
                print(f"    Telegram message sent: Returning to idle")
            except Exception as telegram_error:
                print(f"    Failed to send Telegram message: {telegram_error}")

        print(f"    Returning to idle state - waiting for human Alt press...")

    def _execute_qe_sequence(self):
        """Execute the Q/E capture sequence (positions 1, 2, 3)"""
        print(" Starting Q/E capture sequence...")

        # Initial delay for UI to appear
        print(f"   ⏱️ Waiting {self._initial_delay}s for UI to appear...")
        time.sleep(self._initial_delay)

        # Process each position sequentially
        success_count = 0
        positions = list(self._crop_coords.keys())

        for position in positions:
            print(f"    Processing position {position}...")
            if self._capture_classify_and_send(position):
                success_count += 1
            else:
                print(f"   ⚠️ Position {position} processing failed")

        print(f" Q/E sequence completed! ({success_count}/{len(positions)} positions processed)")

    def _execute_sequence(self):
        """Execute the full 3-position capture sequence followed by status monitoring"""
        with self._lock:
            if self._processing_sequence:
                print(" Sequence already in progress, ignoring Alt press")
                return
            self._processing_sequence = True
            # Reset stop monitoring flag for new sequence
            self._stop_monitoring = False

        try:
            # Execute Q/E sequence
            self._execute_qe_sequence()

            # Start status monitoring loop
            self._status_monitoring_loop()

        except Exception as e:
            print(f" Sequence error: {e}")
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

        print(f"\n Alt pressed! Triggering capture sequence...")

        # Run sequence in a separate thread to avoid blocking key listener
        sequence_thread = threading.Thread(target=self._execute_sequence, daemon=True)
        sequence_thread.start()

    def on_press(self, key) -> None:
        """Handle key press events"""
        try:
            # Listen for Alt, S, and ESC keys
            if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt):
                self._handle_alt_press()
            elif hasattr(key, 'char') and key.char and key.char.lower() == 's':
                # S key pressed - immediately stop monitoring and return to idle
                print("\n S key pressed - stopping monitoring and returning to idle...")
                with self._lock:
                    self._stop_monitoring = True
                print(" Ready for next Alt press...")
            elif key == keyboard.Key.esc:
                print("\n ESC detected; exiting Alt-triggered automation...")
                self._running = False
                raise StopIteration

        except Exception as exc:
            print(f" Keypress error: {exc}")
        return None

    def run(self) -> None:
        """Main automation loop"""
        print("=" * 70)
        print(" Alt-Triggered MTA ESP32-S3 Automation (Auto-Loop)")
        print("=" * 70)
        print(" Workflow:")
        print("   1. Press Alt to trigger MTA UI (human or auto)")
        print("   2. System captures & classifies Q/E glyph positions")
        print("   3. Random delay applied before each ESP command")
        print("   4. After 3rd Q/E press: Wait 2.5s -> Status monitoring")
        print("   5. Monitor status every 0.2-0.3s (priority order):")
        print("      - 'end' (701,27 28x10) -> Send Telegram + Exit to idle")
        print("      - 'wait' (634,60 331x14) -> Keep monitoring")
        print("      - 'alt' (634,60 331x14) -> Auto-trigger Alt -> Repeat from step 2")
        print("      - No match (5 retries) -> Return to idle")
        print("   6. Max 50 iterations before forced exit to idle")
        print()
        print(" Controls:")
        print("   - Alt: Trigger capture sequence")
        print("   - S: IMMEDIATELY stop and return to idle (await Alt)")
        print("   - ESC: Exit the program")
        print()
        print(" Q/E Settings:")
        print(f"   - Crop coordinates: {self._crop_coords}")
        print(f"   - Crop size: {self._crop_size}x{self._crop_size}")
        print(f"   - Min confidence: {config.MIN_CONFIDENCE_FOR_ESP_ACTION}")
        print(f"   - Initial delay: {self._initial_delay}s")
        print(f"   - Capture delays: {self._capture_delays}")
        print()
        print(" Status Monitoring Settings:")
        print(f"   - End region: ({config.END_REGION_CROP['x']}, {config.END_REGION_CROP['y']}) "
              f"{config.END_REGION_CROP['width']}x{config.END_REGION_CROP['height']}")
        print(f"   - Alt/Wait region: ({config.STATUS_REGION_CROP['x']}, {config.STATUS_REGION_CROP['y']}) "
              f"{config.STATUS_REGION_CROP['width']}x{config.STATUS_REGION_CROP['height']}")
        print(f"   - Check interval: {config.STATUS_CHECK_DELAY_MIN}-{config.STATUS_CHECK_DELAY_MAX}s")
        print(f"   - Initial wait: {config.STATUS_INITIAL_WAIT}s")
        print(f"   - Confidence threshold: {config.STATUS_CONFIDENCE_THRESHOLD}")
        print(f"   - Max retries: {config.STATUS_MAX_RETRIES}")
        print(f"   - Max iterations: {config.STATUS_MAX_ITERATIONS}")
        print()
        print(" ESP32 Settings:")
        print(f"   - Port: {self.keyboard.esp32.port}")
        print(f"   - Random delay range: {self._esp_delay_min}-{self._esp_delay_max}ms")
        print("=" * 70)
        print(" Ready! Press Alt to start...")

        try:
            with keyboard.Listener(on_press=self.on_press) as listener:
                while self._running:
                    time.sleep(0.1)
                listener.stop()
        except KeyboardInterrupt:
            print("\n Interrupted by user")
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

            print(" Alt-triggered automation stopped")


def main():
    # Print config summary first
    if config.VERBOSE_LOGGING:
        config.print_config_summary()
        
        # Validate config
        errors = config.validate_config()
        if errors:
            print(" Configuration errors found:")
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
            print(" Error: ESP delay minimum must be less than maximum")
            return
        if args.esp_delay_range[0] < 0:
            print(" Error: ESP delay values must be non-negative")
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
            # If capture_delay is specified, use it as fixed delay (min=max)
            automation._capture_delays = [(0.0, 0.0), (args.capture_delay, args.capture_delay), (args.capture_delay, args.capture_delay)]

        automation.run()

    except KeyboardInterrupt:
        print("\n Interrupted by user")
    except Exception as e:
        print(f" Error: {e}")


if __name__ == "__main__":
    main()