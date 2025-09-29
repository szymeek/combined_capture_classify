from pynput import keyboard
import time
import csv
import os

# Dictionary to store key press times
key_press_times = {}

# Keep track of last release time
last_release_time = None

# CSV file setup
csv_file = "key_log.csv"
file_exists = os.path.isfile(csv_file)

with open(csv_file, mode="a", newline="") as f:
    writer = csv.writer(f)
    # Write header if file is new
    if not file_exists:
        writer.writerow([
            "Key",
            "Press Time (ms)",
            "Release Time (ms)",
            "Duration (ms)",
            "Gap Since Last Release (ms)"
        ])

def on_press(key):
    global last_release_time
    try:
        press_time = time.time() * 1000  # ms

        # Measure gap from last release
        gap = None
        if last_release_time is not None:
            gap = press_time - last_release_time

        if key not in key_press_times:  # Only store if not already pressed
            key_press_times[key] = (press_time, gap)
    except Exception as e:
        print(f"Error on press: {e}")

def on_release(key):
    global last_release_time
    try:
        if key in key_press_times:
            press_time, gap = key_press_times.pop(key)
            release_time = time.time() * 1000  # in ms
            duration = release_time - press_time
            last_release_time = release_time

            # Print to console
            if gap is not None:
                print(f"Key {key} held for {duration:.2f} ms | Gap since last release: {gap:.2f} ms")
            else:
                print(f"Key {key} held for {duration:.2f} ms | First key, no gap")

            # Append to CSV
            with open(csv_file, mode="a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    key,
                    f"{press_time:.2f}",
                    f"{release_time:.2f}",
                    f"{duration:.2f}",
                    f"{gap:.2f}" if gap is not None else "N/A"
                ])
    except Exception as e:
        print(f"Error on release: {e}")

    # Stop listener if Esc is released
    if key == keyboard.Key.esc:
        return False

# Start listening
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
