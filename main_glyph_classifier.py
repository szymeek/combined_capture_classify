# main_glyph_classifier.py - Template-only version
from PIL import Image
import os
import sys
from glyph_classifier_template import TemplateGlyphClassifier
from typing import Tuple, Dict, Optional
import csv
from datetime import datetime
from config import (
    TEMPLATES_PATH,
    MIN_CONFIDENCE_FOR_ESP_ACTION,
    TEMPLATE_CONFIDENCE_THRESHOLD
)


class GlyphClassifier:
    def __init__(self, templates_path: str, confidence_threshold: float = 0.7):
        self.templates_path = templates_path
        self.confidence_threshold = confidence_threshold

        # Initialize template classifier
        print("Initializing template classifier...")
        self.template_classifier = TemplateGlyphClassifier(templates_path)

        # Try to load pre-trained model
        self.load_model()

    def load_model(self):
        """Load pre-trained template model if available"""
        try:
            if os.path.exists("glyph_templates.pkl"):
                self.template_classifier.load_model("glyph_templates.pkl")
                print("Loaded pre-trained template model")
        except Exception as e:
            print(f"Could not load template model: {e}")

    def classify(self, image: Image.Image) -> Tuple[str, float, Dict]:
        """
        Classify glyph using template matching
        Returns: (predicted_class, confidence, detailed_results)
        """
        results: Dict = {}

        # Template matching
        template_pred, template_conf, template_scores = self.template_classifier.classify(image)
        results['template'] = {
            'prediction': template_pred,
            'confidence': template_conf,
            'scores': template_scores
        }

        results['method_used'] = 'template_matching'
        results['final'] = {
            'prediction': template_pred,
            'confidence': template_conf
        }

        return template_pred, template_conf, results
    
    def classify_from_file(self, image_path: str) -> Tuple[str, float, Dict]:
        """Classify glyph from image file"""
        image = Image.open(image_path)
        return self.classify(image)
    
    def log_result(self, image_path: str, prediction: str, confidence: float,
                   details: Dict, csv_path: str = "results.csv"):
        """Log classification result to CSV"""
        file_exists = os.path.exists(csv_path)

        with open(csv_path, 'a', newline='') as csvfile:
            fieldnames = ['timestamp', 'image_path', 'prediction', 'confidence',
                         'method_used', 'template_confidence']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            template_conf = details.get('template', {}).get('confidence', 0)

            row = {
                'timestamp': datetime.now().isoformat(),
                'image_path': image_path,
                'prediction': prediction,
                'confidence': f"{confidence:.4f}",
                'method_used': details.get('method_used', 'unknown'),
                'template_confidence': f"{template_conf:.4f}"
            }

            writer.writerow(row)


def main():
    if len(sys.argv) < 3:
        print("Usage: python main_glyph_classifier.py <templates_path> <test_image_path>")
        print("Templates should be organized as:")
        print("  templates_path/q/*.png")
        print("  templates_path/e/*.png")
        sys.exit(1)

    templates_path = sys.argv[1]
    test_image_path = sys.argv[2]

    # Initialize classifier
    classifier = GlyphClassifier(templates_path)

    # Classify test image
    prediction, confidence, details = classifier.classify_from_file(test_image_path)

    # Display results
    print("\n=== Glyph Classification Results ===")
    print(f"Image: {test_image_path}")
    print(f"Prediction: {prediction}")
    print(f"Confidence: {confidence:.4f}")
    print(f"Method: {details['method_used']}")

    if 'template' in details:
        temp_scores = details['template']['scores']
        print(f"Template scores: q={temp_scores['q']:.4f}, e={temp_scores['e']:.4f}")

    # Log result
    classifier.log_result(test_image_path, prediction, confidence, details)
    print(f"\nResult logged to results.csv")


if __name__ == "__main__":
    main()
