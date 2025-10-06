# status_classifier.py - Status template classifier for end/alt/wait detection
from PIL import Image
import os
import numpy as np
from typing import Tuple, Dict, Optional
from glyph_classifier_template import TemplateGlyphClassifier
from config import (
    STATUS_TEMPLATES_END,
    STATUS_TEMPLATES_ALT,
    STATUS_TEMPLATES_WAIT,
    STATUS_CONFIDENCE_THRESHOLD,
    STATUS_REGION_CROP,
    END_REGION_CROP
)


class StatusClassifier:
    def __init__(self, end_templates_path: Optional[str] = None,
                 alt_templates_path: Optional[str] = None,
                 wait_templates_path: Optional[str] = None,
                 confidence_threshold: Optional[float] = None):
        """
        Initialize status classifier for end/alt/wait detection

        Args:
            end_templates_path: Path to 'end' templates folder
            alt_templates_path: Path to 'alt' templates folder
            wait_templates_path: Path to 'wait' templates folder
            confidence_threshold: Minimum confidence for classification
        """
        self.end_path = end_templates_path or STATUS_TEMPLATES_END
        self.alt_path = alt_templates_path or STATUS_TEMPLATES_ALT
        self.wait_path = wait_templates_path or STATUS_TEMPLATES_WAIT
        self.confidence_threshold = confidence_threshold or STATUS_CONFIDENCE_THRESHOLD

        # Create a temporary structure for the template classifier
        # The TemplateGlyphClassifier expects folders named by class
        self.class_names = ['end', 'alt', 'wait']

        # We'll use the base TemplateGlyphClassifier with custom template loading
        self._load_templates()

    def _load_templates(self):
        """Load end, alt and wait templates"""
        print(f"Loading status templates...")
        print(f"  End templates: {self.end_path}")
        print(f"  Alt templates: {self.alt_path}")
        print(f"  Wait templates: {self.wait_path}")

        # Verify paths exist
        if not os.path.exists(self.end_path):
            raise FileNotFoundError(f"End templates directory not found: {self.end_path}")

        if not os.path.exists(self.alt_path):
            raise FileNotFoundError(f"Alt templates directory not found: {self.alt_path}")

        if not os.path.exists(self.wait_path):
            raise FileNotFoundError(f"Wait templates directory not found: {self.wait_path}")

        # Create parent directory structure for TemplateGlyphClassifier
        # We need a temporary parent that contains both 'alt' and 'wait' subdirs
        parent_dir = os.path.dirname(self.alt_path.rstrip('/\\'))

        # Initialize the template classifier with the parent directory
        # It will look for 'alt' and 'wait' subdirectories
        try:
            # Create a custom templates path structure
            from glyph_classifier_template import TemplateGlyphClassifier

            # Temporarily modify to support alt/wait instead of q/e
            self.template_classifier = StatusTemplateClassifier(parent_dir)
            print(f"✅ Status templates loaded successfully")

        except Exception as e:
            print(f"❌ Failed to load status templates: {e}")
            raise

    def classify(self, image: Image.Image, region_type: str = "status") -> Tuple[str, float, Dict]:
        """
        Classify status image as 'end', 'alt', 'wait', or neither

        Args:
            image: Input image to classify
            region_type: "end" for end region (28x10), "status" for alt/wait region (331x14)

        Returns:
            (prediction, confidence, details)
        """
        # Ensure proper image format based on region type
        if region_type == "end":
            expected_height = END_REGION_CROP['height']
            expected_width = END_REGION_CROP['width']
        else:
            expected_height = STATUS_REGION_CROP['height']
            expected_width = STATUS_REGION_CROP['width']

        if image.size != (expected_width, expected_height):
            image = image.resize((expected_width, expected_height), Image.Resampling.LANCZOS)

        if image.mode != 'L':
            image = image.convert('L')

        # Use template classifier
        prediction, confidence, scores = self.template_classifier.classify(image, region_type=region_type)

        details = {
            'prediction': prediction,
            'confidence': confidence,
            'scores': scores,
            'threshold': self.confidence_threshold,
            'method_used': 'status_template_matching',
            'region_type': region_type
        }

        return prediction, confidence, details

    def classify_from_crop(self, cropped_image: Image.Image, region_type: str = "status") -> Tuple[str, float, Dict]:
        """Classify from already cropped region"""
        return self.classify(cropped_image, region_type=region_type)


class StatusTemplateClassifier(TemplateGlyphClassifier):
    """
    Custom template classifier for status detection (end/alt/wait)
    Extends the base TemplateGlyphClassifier to use 'end', 'alt' and 'wait' instead of 'q' and 'e'
    """

    def __init__(self, templates_path: str, rotations: Optional[list] = None):
        """Initialize with end/alt/wait templates"""
        # Override class names
        self.templates = {"end": [], "alt": [], "wait": []}
        self.rotations = rotations if rotations is not None else [0, -15, 15, -30, 30, -45, 45]
        self.templates_path = templates_path
        self._template_stats = {"end": [], "alt": [], "wait": []}
        self.load_templates()

    def load_templates(self):
        """Load and preprocess end/alt/wait template images with rotations"""
        print("Loading status templates...")
        for status in ["end", "alt", "wait"]:
            status_path = os.path.join(self.templates_path, status)
            if not os.path.exists(status_path):
                raise FileNotFoundError(f"Status template directory not found: {status_path}")

            template_count = 0
            for filename in os.listdir(status_path):
                if filename.endswith(".png"):
                    img_path = os.path.join(status_path, filename)
                    img = Image.open(img_path).convert('L')

                    # Resize to appropriate region size based on status type
                    from config import STATUS_REGION_CROP, END_REGION_CROP
                    if status == "end":
                        target_size = (END_REGION_CROP['width'], END_REGION_CROP['height'])
                    else:
                        target_size = (STATUS_REGION_CROP['width'], STATUS_REGION_CROP['height'])
                    img = img.resize(target_size, Image.Resampling.LANCZOS)

                    # Add original and rotated versions
                    for rotation in self.rotations:
                        if rotation != 0:
                            rotated = img.rotate(rotation, resample=Image.Resampling.BILINEAR,
                                               expand=False, fillcolor=255)
                        else:
                            rotated = img

                        processed = self.preprocess_image(rotated)
                        self.templates[status].append(processed)

                        # Pre-compute template statistics for faster correlation
                        flat = processed.flatten()
                        mean = np.mean(flat)
                        centered = flat - mean
                        norm = np.sqrt(np.dot(centered, centered))
                        self._template_stats[status].append((centered, mean, norm))

                        template_count += 1

            print(f"Loaded {template_count} templates for '{status}'")

    def classify(self, image: Image.Image, region_type: str = "status") -> Tuple[str, float, Dict[str, float]]:
        """
        Classify a status region image
        Args:
            image: Input image to classify
            region_type: "end" for end region (28x10), "status" for alt/wait region (331x14)
        Returns: (predicted_class, confidence, all_scores)
        """
        import numpy as np
        from config import STATUS_REGION_CROP, END_REGION_CROP

        # Ensure proper size and format based on region type
        if region_type == "end":
            target_size = (END_REGION_CROP['width'], END_REGION_CROP['height'])
            status_list = ["end"]
        else:
            target_size = (STATUS_REGION_CROP['width'], STATUS_REGION_CROP['height'])
            status_list = ["alt", "wait"]

        if image.size != target_size:
            image = image.resize(target_size, Image.Resampling.LANCZOS)
        if image.mode != 'L':
            image = image.convert('L')

        # Preprocess input image
        processed_image = self.preprocess_image(image)

        # Pre-compute image statistics once
        img_flat = processed_image.flatten()
        img_mean = np.mean(img_flat)
        img_centered = img_flat - img_mean
        img_norm = np.sqrt(np.dot(img_centered, img_centered))

        # Match against all templates using optimized correlation
        scores: Dict[str, float] = {}
        for status in status_list:
            max_correlation = 0.0
            for temp_centered, temp_mean, temp_norm in self._template_stats[status]:
                correlation = self.fast_correlation(img_centered, img_norm, temp_centered, temp_norm)
                max_correlation = max(max_correlation, correlation)
            scores[status] = max_correlation

        # Determine best match
        predicted_status = max(scores.keys(), key=lambda k: scores[k])
        confidence = scores[predicted_status]

        return predicted_status, confidence, scores


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python status_classifier.py <test_image_path>")
        print("Templates should be organized as:")
        print("  templates/alt/*.png")
        print("  templates/wait/*.png")
        sys.exit(1)

    test_image_path = sys.argv[1]

    # Initialize classifier
    classifier = StatusClassifier()

    # Test image
    test_image = Image.open(test_image_path)
    prediction, confidence, details = classifier.classify(test_image)

    print(f"\n=== Status Classification Results ===")
    print(f"Image: {test_image_path}")
    print(f"Prediction: {prediction}")
    print(f"Confidence: {confidence:.4f}")
    print(f"Scores: alt={details['scores']['alt']:.4f}, wait={details['scores']['wait']:.4f}")
    print(f"Threshold: {details['threshold']}")
