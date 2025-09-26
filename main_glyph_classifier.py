# main_glyph_classifier.py - Fixed version
from PIL import Image
import os
import sys
from glyph_classifier_template import TemplateGlyphClassifier
from glyph_classifier_cnn import CNNGlyphClassifier
from typing import Tuple, Dict, Optional
import csv
from datetime import datetime
from config import (
    TEMPLATES_PATH, 
    MIN_CONFIDENCE_FOR_ESP_ACTION,
    TEMPLATE_CONFIDENCE_THRESHOLD
)


class HybridGlyphClassifier:
    def __init__(self, templates_path: str, confidence_threshold: float = 0.7):
        self.templates_path = templates_path
        self.confidence_threshold = confidence_threshold
        
        # Initialize classifiers
        print("Initializing template classifier...")
        self.template_classifier = TemplateGlyphClassifier(templates_path)
        
        print("Initializing CNN classifier...")
        self.cnn_classifier = CNNGlyphClassifier(templates_path)
        
        # Try to load pre-trained models
        self.load_models()
    
    def load_models(self):
        """Load pre-trained models if available"""
        try:
            if os.path.exists("glyph_templates.pkl"):
                self.template_classifier.load_model("glyph_templates.pkl")
                print("Loaded pre-trained template model")
        except Exception as e:
            print(f"Could not load template model: {e}")
            
        try:
            if os.path.exists("glyph_cnn.pkl"):
                self.cnn_classifier.load_model("glyph_cnn.pkl")
                print("Loaded pre-trained CNN model")
            else:
                self.cnn_classifier.train()
        except Exception as e:
            print(f"Could not load/train CNN model: {e}")
    
    def classify(self, image: Image.Image, use_ensemble: bool = True) -> Tuple[str, float, Dict]:
        """
        Classify glyph with hybrid approach
        Returns: (predicted_class, confidence, detailed_results)
        """
        results: Dict = {}
        
        # Primary: Template matching
        template_pred, template_conf, template_scores = self.template_classifier.classify(image)
        results['template'] = {
            'prediction': template_pred,
            'confidence': template_conf,
            'scores': template_scores
        }
        
        # If template confidence is high, use it
        if template_conf >= self.confidence_threshold:
            final_pred = template_pred
            final_conf = template_conf
            results['method_used'] = 'template_only'
        else:
            # Use CNN as backup
            try:
                cnn_pred, cnn_conf = self.cnn_classifier.classify(image)
                results['cnn'] = {
                    'prediction': cnn_pred,
                    'confidence': cnn_conf
                }
                
                if use_ensemble:
                    # Ensemble voting
                    if template_pred == cnn_pred:
                        final_pred = template_pred
                        final_conf = (template_conf + cnn_conf) / 2
                        results['method_used'] = 'ensemble_agreement'
                    else:
                        # Choose higher confidence
                        if template_conf >= cnn_conf:
                            final_pred = template_pred
                            final_conf = template_conf
                            results['method_used'] = 'template_preferred'
                        else:
                            final_pred = cnn_pred
                            final_conf = cnn_conf
                            results['method_used'] = 'cnn_preferred'
                else:
                    final_pred = cnn_pred
                    final_conf = cnn_conf
                    results['method_used'] = 'cnn_fallback'
                    
            except Exception as e:
                final_pred = template_pred
                final_conf = template_conf
                results['method_used'] = 'template_fallback'
                results['cnn_error'] = str(e)
        
        results['final'] = {
            'prediction': final_pred,
            'confidence': final_conf
        }
        
        return final_pred, final_conf, results
    
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
                         'method_used', 'template_confidence', 'cnn_confidence']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            template_conf = details.get('template', {}).get('confidence', 0)
            cnn_conf = details.get('cnn', {}).get('confidence', 0)
            
            row = {
                'timestamp': datetime.now().isoformat(),
                'image_path': image_path,
                'prediction': prediction,
                'confidence': f"{confidence:.4f}",
                'method_used': details.get('method_used', 'unknown'),
                'template_confidence': f"{template_conf:.4f}",
                'cnn_confidence': f"{cnn_conf:.4f}"
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
    
    # Initialize hybrid classifier
    classifier = HybridGlyphClassifier(templates_path)
    
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
    
    if 'cnn' in details:
        print(f"CNN prediction: {details['cnn']['prediction']} (conf: {details['cnn']['confidence']:.4f})")
    
    # Log result
    classifier.log_result(test_image_path, prediction, confidence, details)
    print(f"\nResult logged to results.csv")


if __name__ == "__main__":
    main()
