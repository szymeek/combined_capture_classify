#!/usr/bin/env python3
# crop_64x64_from_184_814.py

from pathlib import Path
from PIL import Image

def main():
    # Crop parameters
    x, y = 50, 901           # top-left corner
    w, h = 36, 36             # crop size
    box = (x, y, x + w, y + h)  # (left, upper, right, lower)

    folder = Path(__file__).parent
    png_files = sorted(p for p in folder.glob("*.png"))

    if not png_files:
        print("No .png files found in the script directory.")
        return

    for src_path in png_files:
        try:
            with Image.open(src_path) as im:
                # Optional: check size if strictly expecting 1920x1080
                if im.width != 1920 or im.height != 1080:
                    print(f"Skipping {src_path.name}: size is {im.width}x{im.height}, expected 1920x1080.")
                    continue

                # Ensure crop box fits within the image
                if not (0 <= x < im.width and 0 <= y < im.height and x + w <= im.width and y + h <= im.height):
                    print(f"Skipping {src_path.name}: crop box {box} is outside image bounds {im.size}.")
                    continue

                cropped = im.crop(box)  # Pillow crop uses (left, upper, right, lower)
                dst_path = src_path.with_name(f"{src_path.stem}_crop{src_path.suffix}")
                # Save as PNG; Pillow infers from suffix
                cropped.save(dst_path, format="PNG")
                print(f"Cropped saved: {dst_path.name}")
        except Exception as e:
            print(f"Error processing {src_path.name}: {e}")

if __name__ == "__main__":
    main()
