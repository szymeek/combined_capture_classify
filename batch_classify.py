# batch_classify.py - Process all images in screenshots folder
import os
import glob
from main_glyph_classifier import HybridGlyphClassifier
from PIL import Image
import csv
from datetime import datetime

def batch_classify(templates_path: str, screenshots_path: str, output_csv: str = "batch_results.csv"):
    """Process all PNG images in screenshots folder"""
    
    # Initialize classifier
    print("Initializing classifier...")
    classifier = HybridGlyphClassifier(templates_path)
    
    # Find all PNG images
    image_pattern = os.path.join(screenshots_path, "*.png")
    image_files = glob.glob(image_pattern)
    
    if not image_files:
        print(f"No PNG images found in {screenshots_path}")
        return
    
    print(f"Found {len(image_files)} images to classify")
    
    # Process each image
    results = []
    for i, image_path in enumerate(image_files, 1):
        try:
            print(f"Processing {i}/{len(image_files)}: {os.path.basename(image_path)}")
            
            # Classify image
            prediction, confidence, details = classifier.classify_from_file(image_path)
            
            # Store result
            result = {
                'filename': os.path.basename(image_path),
                'filepath': image_path,
                'prediction': prediction,
                'confidence': confidence,
                'method_used': details['method_used'],
                'template_confidence': details['template']['confidence'],
                'cnn_confidence': details.get('cnn', {}).get('confidence', 0.0),
                'timestamp': datetime.now().isoformat()
            }
            results.append(result)
            
            # Print quick result
            print(f"  → {prediction} (confidence: {confidence:.3f})")
            
        except Exception as e:
            print(f"  → ERROR: {str(e)}")
            results.append({
                'filename': os.path.basename(image_path),
                'filepath': image_path,
                'prediction': 'ERROR',
                'confidence': 0.0,
                'method_used': 'error',
                'template_confidence': 0.0,
                'cnn_confidence': 0.0,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    # Save results to CSV
    print(f"\nSaving results to {output_csv}...")
    with open(output_csv, 'w', newline='') as csvfile:
        fieldnames = ['filename', 'filepath', 'prediction', 'confidence', 
                     'method_used', 'template_confidence', 'cnn_confidence', 'timestamp']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    # Print summary
    print(f"\n=== BATCH CLASSIFICATION SUMMARY ===")
    print(f"Total images processed: {len(results)}")
    
    predictions = [r['prediction'] for r in results if r['prediction'] != 'ERROR']
    if predictions:
        q_count = predictions.count('q')
        e_count = predictions.count('e')
        error_count = len([r for r in results if r['prediction'] == 'ERROR'])
        
        print(f"Q glyphs detected: {q_count}")
        print(f"E glyphs detected: {e_count}")
        print(f"Errors: {error_count}")
        
        avg_confidence = sum(r['confidence'] for r in results if r['prediction'] != 'ERROR') / len(predictions)
        print(f"Average confidence: {avg_confidence:.3f}")
    
    print(f"Detailed results saved to: {output_csv}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python batch_classify.py <templates_path> <screenshots_path>")
        print("Example: python batch_classify.py ./templates ./screenshots")
        sys.exit(1)
    
    templates_path = sys.argv[1]
    screenshots_path = sys.argv[2]
    
    batch_classify(templates_path, screenshots_path)
