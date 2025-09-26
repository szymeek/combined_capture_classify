# glyph_classifier_template.py - Fixed version
from PIL import Image, ImageFilter
import numpy as np
import os
import pickle
from typing import List, Tuple, Dict, Optional
from config import (
    TEMPLATES_PATH,
    TEMPLATE_CONFIDENCE_THRESHOLD,
    CROP_SIZE
)


class TemplateGlyphClassifier:
    def __init__(self, templates_path: str, rotations: Optional[List[int]] = None):
        """
        Initialize classifier with template images from templates_path/q/ and templates_path/e/
        """
        self.templates: Dict[str, List[np.ndarray]] = {"q": [], "e": []}
        self.rotations = rotations if rotations is not None else [0, -15, 15, -30, 30, -45, 45]
        self.templates_path = templates_path
        self.load_templates()

    def load_templates(self):
        """Load and preprocess all template images with rotations"""
        print("Loading templates...")
        for glyph in ["q", "e"]:
            glyph_path = os.path.join(self.templates_path, glyph)
            if not os.path.exists(glyph_path):
                raise FileNotFoundError(f"Template directory not found: {glyph_path}")
            
            template_count = 0
            for filename in os.listdir(glyph_path):
                if filename.endswith(".png"):
                    img_path = os.path.join(glyph_path, filename)
                    img = Image.open(img_path).convert('L')
                    img = img.resize((26, 26), Image.Resampling.LANCZOS)
                    
                    # Add original and rotated versions
                    for rotation in self.rotations:
                        if rotation != 0:
                            rotated = img.rotate(rotation, resample=Image.Resampling.BILINEAR, 
                                               expand=False, fillcolor=255)
                        else:
                            rotated = img
                        
                        processed = self.preprocess_image(rotated)
                        self.templates[glyph].append(processed)
                        template_count += 1
            
            print(f"Loaded {template_count} templates for '{glyph}'")

    def preprocess_image(self, image: Image.Image) -> np.ndarray:
        """Enhanced preprocessing for noise reduction"""
        # Convert to numpy
        img_array = np.array(image)
        
        # Gaussian blur to reduce noise
        img_pil = Image.fromarray(img_array).filter(ImageFilter.GaussianBlur(radius=0.8))
        img_blurred = np.array(img_pil)
        
        # Adaptive-like thresholding using Otsu
        threshold = self.calculate_otsu_threshold(img_blurred)
        binary = (img_blurred > threshold).astype(np.uint8) * 255
        
        # Morphological operations to clean up
        binary = self.morphological_clean(binary)
        
        return binary.astype(np.float32) / 255.0

    def calculate_otsu_threshold(self, image: np.ndarray) -> int:
        """Calculate optimal threshold using Otsu's method"""
        histogram = np.bincount(image.flatten(), minlength=256)
        total_pixels = image.size
        
        sum_total = np.dot(np.arange(256), histogram)
        sum_background = 0
        weight_background = 0
        maximum_variance = 0
        optimal_threshold = 0
        
        for threshold in range(256):
            weight_background += histogram[threshold]
            if weight_background == 0:
                continue
                
            weight_foreground = total_pixels - weight_background
            if weight_foreground == 0:
                break
                
            sum_background += threshold * histogram[threshold]
            mean_background = sum_background / weight_background
            mean_foreground = (sum_total - sum_background) / weight_foreground
            
            variance_between = weight_background * weight_foreground * \
                             (mean_background - mean_foreground) ** 2
            
            if variance_between > maximum_variance:
                maximum_variance = variance_between
                optimal_threshold = threshold
                
        return optimal_threshold

    def morphological_clean(self, binary_image: np.ndarray) -> np.ndarray:
        """Simple morphological operations without OpenCV"""
        # Basic erosion followed by dilation (opening operation)
        kernel = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8)
        
        # Erosion
        eroded = np.zeros_like(binary_image)
        for i in range(1, binary_image.shape[0] - 1):
            for j in range(1, binary_image.shape[1] - 1):
                region = binary_image[i-1:i+2, j-1:j+2]
                if np.all(region * kernel == kernel * 255):
                    eroded[i, j] = 255
        
        # Dilation
        dilated = np.zeros_like(eroded)
        for i in range(1, eroded.shape[0] - 1):
            for j in range(1, eroded.shape[1] - 1):
                region = eroded[i-1:i+2, j-1:j+2]
                if np.any(region * kernel > 0):
                    dilated[i, j] = 255
                    
        return dilated

    def normalized_cross_correlation(self, image: np.ndarray, template: np.ndarray) -> float:
        """Calculate normalized cross correlation between image and template"""
        if image.shape != template.shape:
            return 0.0
            
        # Convert to mean-zero
        image_mean = image - np.mean(image)
        template_mean = template - np.mean(template)
        
        # Calculate correlation
        numerator = np.sum(image_mean * template_mean)
        denominator = np.sqrt(np.sum(image_mean ** 2) * np.sum(template_mean ** 2))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator

    def classify(self, image: Image.Image) -> Tuple[str, float, Dict[str, float]]:
        """
        Classify a single 26x26 glyph image
        Returns: (predicted_class, confidence, all_scores)
        """
        # Ensure proper size and format
        if image.size != (26, 26):
            image = image.resize((26, 26), Image.Resampling.LANCZOS)
        if image.mode != 'L':
            image = image.convert('L')
            
        # Preprocess input image
        processed_image = self.preprocess_image(image)
        
        # Match against all templates
        scores: Dict[str, float] = {}
        for glyph in ["q", "e"]:
            max_correlation = 0.0
            for template in self.templates[glyph]:
                correlation = self.normalized_cross_correlation(processed_image, template)
                max_correlation = max(max_correlation, correlation)
            scores[glyph] = max_correlation
        
        # Determine best match - Fixed the max function call
        predicted_glyph = max(scores.keys(), key=lambda k: scores[k])
        confidence = scores[predicted_glyph]
        
        return predicted_glyph, confidence, scores

    def classify_batch(self, images: List[Image.Image]) -> List[Tuple[str, float]]:
        """Classify multiple images at once"""
        results = []
        for img in images:
            glyph, confidence, _ = self.classify(img)
            results.append((glyph, confidence))
        return results

    def save_model(self, filepath: str):
        """Save preprocessed templates to disk"""
        with open(filepath, 'wb') as f:
            pickle.dump(self.templates, f)

    def load_model(self, filepath: str):
        """Load preprocessed templates from disk"""
        with open(filepath, 'rb') as f:
            self.templates = pickle.load(f)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python glyph_classifier_template.py <templates_path> <test_image_path>")
        print("Templates should be organized as: templates_path/q/*.png and templates_path/e/*.png")
        sys.exit(1)
    
    templates_path = sys.argv[1]
    test_image_path = sys.argv[2]
    
    # Initialize and test classifier
    classifier = TemplateGlyphClassifier(templates_path)
    
    # Test single image
    test_image = Image.open(test_image_path)
    glyph, confidence, all_scores = classifier.classify(test_image)
    
    print(f"Classification Results:")
    print(f"Predicted: {glyph}")
    print(f"Confidence: {confidence:.4f}")
    print(f"All scores: q={all_scores['q']:.4f}, e={all_scores['e']:.4f}")
    
    # Save model for faster future loading
    classifier.save_model("glyph_templates.pkl")
    print("Templates saved to glyph_templates.pkl")
