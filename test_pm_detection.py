#!/usr/bin/env python3
"""
Test script for PM detection debugging
"""
from PIL import Image
from status_classifier import StatusClassifier
import config

def test_pm_template():
    """Test PM template loading"""
    print("=" * 60)
    print("PM Detection Diagnostic Test")
    print("=" * 60)

    # Check configuration
    print("\nConfiguration:")
    print(f"  PM_REGION_CROP: {config.PM_REGION_CROP}")
    print(f"  STATUS_TEMPLATES_PM: {config.STATUS_TEMPLATES_PM}")
    print(f"  STATUS_CONFIDENCE_THRESHOLD: {config.STATUS_CONFIDENCE_THRESHOLD}")

    # Check template file
    import os
    pm_path = config.STATUS_TEMPLATES_PM
    print(f"\nPM Templates Path: {pm_path}")
    if os.path.exists(pm_path):
        files = [f for f in os.listdir(pm_path) if f.endswith('.png')]
        print(f"  Found {len(files)} PNG files:")
        for f in files:
            img_path = os.path.join(pm_path, f)
            img = Image.open(img_path)
            print(f"    - {f}: {img.size} ({img.mode})")
    else:
        print(f"  ERROR: Path does not exist!")
        return

    # Try to initialize classifier
    print("\nInitializing StatusClassifier...")
    try:
        classifier = StatusClassifier()
        print("  [OK] Classifier initialized successfully")
    except Exception as e:
        print(f"  [ERROR] Failed to initialize: {e}")
        return

    # Test with the actual template
    print("\nTesting PM classification with template image...")
    for f in files:
        img_path = os.path.join(pm_path, f)
        test_img = Image.open(img_path).convert('L')

        # Resize to expected size
        expected_size = (config.PM_REGION_CROP['width'], config.PM_REGION_CROP['height'])
        print(f"\n  Template: {f} (original size: {test_img.size})")
        print(f"  Expected size: {expected_size}")

        if test_img.size != expected_size:
            print(f"  WARNING: Size mismatch! Resizing...")
            test_img_resized = test_img.resize(expected_size, Image.Resampling.LANCZOS)
        else:
            test_img_resized = test_img

        try:
            prediction, confidence, details = classifier.classify(test_img_resized, region_type="pm")
            print(f"  Prediction: {prediction}")
            print(f"  Confidence: {confidence:.4f}")
            print(f"  Threshold: {config.STATUS_CONFIDENCE_THRESHOLD}")
            print(f"  Will trigger: {'YES' if (prediction == 'pm' and confidence >= config.STATUS_CONFIDENCE_THRESHOLD) else 'NO'}")
        except Exception as e:
            print(f"  ERROR during classification: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_pm_template()
