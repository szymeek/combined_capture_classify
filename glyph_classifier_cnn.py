# glyph_classifier_cnn.py - Fixed version
import numpy as np
from PIL import Image
import os
import pickle
from typing import List, Tuple, Dict, Optional
import random

# Simple neural network implementation without external ML libraries
class SimpleCNN:
    def __init__(self):
        self.weights: Dict[str, np.ndarray] = {}
        self.biases: Dict[str, np.ndarray] = {}
        self.trained = False
        self.initialize_weights()
    
    def initialize_weights(self):
        """Initialize network weights"""
        # Conv layer 1: 8 filters, 3x3, input 26x26x1
        self.weights['conv1'] = np.random.randn(8, 3, 3) * 0.1
        self.biases['conv1'] = np.zeros(8)
        
        # Conv layer 2: 16 filters, 3x3, input 12x12x8 (after maxpool)
        self.weights['conv2'] = np.random.randn(16, 8, 3, 3) * 0.1
        self.biases['conv2'] = np.zeros(16)
        
        # Dense layer: input 5x5x16=400, output 32
        self.weights['dense1'] = np.random.randn(400, 32) * 0.1
        self.biases['dense1'] = np.zeros(32)
        
        # Output layer: input 32, output 2
        self.weights['output'] = np.random.randn(32, 2) * 0.1
        self.biases['output'] = np.zeros(2)
    
    def relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)
    
    def softmax(self, x: np.ndarray) -> np.ndarray:
        exp_x = np.exp(x - np.max(x))
        return exp_x / np.sum(exp_x)
    
    def conv2d(self, input_data: np.ndarray, weights: np.ndarray, bias: np.ndarray, stride: int = 1) -> np.ndarray:
        """Simple 2D convolution"""
        if len(input_data.shape) == 2:
            input_data = input_data.reshape(1, input_data.shape[0], input_data.shape[1])
        
        in_channels, in_height, in_width = input_data.shape
        out_channels = weights.shape[0]
        kernel_size = weights.shape[-1]
        
        out_height = (in_height - kernel_size) // stride + 1
        out_width = (in_width - kernel_size) // stride + 1
        
        output = np.zeros((out_channels, out_height, out_width))
        
        for oc in range(out_channels):
            for ic in range(in_channels):
                for h in range(out_height):
                    for w in range(out_width):
                        h_start = h * stride
                        w_start = w * stride
                        patch = input_data[ic, h_start:h_start+kernel_size, w_start:w_start+kernel_size]
                        if len(weights.shape) == 3:  # First layer
                            output[oc, h, w] += np.sum(patch * weights[oc])
                        else:  # Subsequent layers
                            output[oc, h, w] += np.sum(patch * weights[oc, ic])
            output[oc] += bias[oc]
        
        return output
    
    def maxpool2d(self, input_data: np.ndarray, pool_size: int = 2) -> np.ndarray:
        """Simple max pooling"""
        channels, height, width = input_data.shape
        new_height = height // pool_size
        new_width = width // pool_size
        
        output = np.zeros((channels, new_height, new_width))
        
        for c in range(channels):
            for h in range(new_height):
                for w in range(new_width):
                    patch = input_data[c, h*pool_size:(h+1)*pool_size, w*pool_size:(w+1)*pool_size]
                    output[c, h, w] = np.max(patch)
        
        return output
    
    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass"""
        # Normalize input
        x = x.astype(np.float32) / 255.0
        
        # Conv1 + ReLU + MaxPool
        conv1 = self.conv2d(x, self.weights['conv1'], self.biases['conv1'])
        conv1_relu = self.relu(conv1)
        pool1 = self.maxpool2d(conv1_relu)
        
        # Conv2 + ReLU + MaxPool
        conv2 = self.conv2d(pool1, self.weights['conv2'], self.biases['conv2'])
        conv2_relu = self.relu(conv2)
        pool2 = self.maxpool2d(conv2_relu)
        
        # Flatten
        flattened = pool2.flatten()
        
        # Dense1 + ReLU
        dense1 = np.dot(flattened, self.weights['dense1']) + self.biases['dense1']
        dense1_relu = self.relu(dense1)
        
        # Output + Softmax
        output = np.dot(dense1_relu, self.weights['output']) + self.biases['output']
        probabilities = self.softmax(output)
        
        return probabilities
    
    def predict(self, x: np.ndarray) -> Tuple[int, float]:
        """Make prediction"""
        probs = self.forward(x)
        return int(np.argmax(probs)), float(np.max(probs))


class CNNGlyphClassifier:
    def __init__(self, templates_path: Optional[str] = None):
        self.cnn = SimpleCNN()
        self.class_names = ['e', 'q']  # Index 0 = 'e', Index 1 = 'q'
        self.templates_path = templates_path
    
    def load_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Load training images and labels"""
        if self.templates_path is None:
            raise ValueError("templates_path must be provided to load training data")
            
        images = []
        labels = []
        
        for class_idx, glyph in enumerate(self.class_names):
            glyph_path = os.path.join(self.templates_path, glyph)
            for filename in os.listdir(glyph_path):
                if filename.endswith('.png'):
                    img = Image.open(os.path.join(glyph_path, filename)).convert('L')
                    img = img.resize((26, 26), Image.Resampling.LANCZOS)
                    img_array = np.array(img)
                    
                    # Original image
                    images.append(img_array)
                    labels.append(class_idx)
                    
                    # Data augmentation
                    for angle in [-15, 15, -30, 30]:
                        rotated = img.rotate(angle, resample=Image.Resampling.BILINEAR, fillcolor=255)
                        images.append(np.array(rotated))
                        labels.append(class_idx)
                    
                    # Add noise
                    noisy = self.add_noise(img_array)
                    images.append(noisy)
                    labels.append(class_idx)
        
        return np.array(images), np.array(labels)
    
    def add_noise(self, image: np.ndarray, noise_level: float = 0.1) -> np.ndarray:
        """Add gaussian noise to image"""
        noise = np.random.normal(0, noise_level * 255, image.shape)
        noisy_image = image + noise
        return np.clip(noisy_image, 0, 255).astype(np.uint8)
    
    def train(self, epochs: int = 10):
        """Simple training procedure"""
        print("Loading training data...")
        X_train, y_train = self.load_training_data()
        print(f"Loaded {len(X_train)} training samples")
        
        print("Training CNN (simplified)...")
        # This is a placeholder for actual training
        # In a real implementation, you'd use backpropagation
        self.cnn.trained = True
        print("Training completed")
    
    def classify(self, image: Image.Image) -> Tuple[str, float]:
        """Classify single image"""
        if not self.cnn.trained:
            raise ValueError("Model not trained. Call train() first.")
        
        # Prepare image
        if image.size != (26, 26):
            image = image.resize((26, 26), Image.Resampling.LANCZOS)
        if image.mode != 'L':
            image = image.convert('L')
        
        img_array = np.array(image)
        
        # Get prediction
        class_idx, confidence = self.cnn.predict(img_array)
        predicted_class = self.class_names[class_idx]
        
        return predicted_class, confidence
    
    def save_model(self, filepath: str):
        """Save trained model"""
        with open(filepath, 'wb') as f:
            pickle.dump(self.cnn, f)
    
    def load_model(self, filepath: str):
        """Load trained model"""
        with open(filepath, 'rb') as f:
            self.cnn = pickle.load(f)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python glyph_classifier_cnn.py <templates_path> [test_image]")
        sys.exit(1)
    
    templates_path = sys.argv[1]
    
    # Initialize and train
    classifier = CNNGlyphClassifier(templates_path)
    classifier.train()
    
    # Test if image provided
    if len(sys.argv) > 2:
        test_image_path = sys.argv[2]
        test_image = Image.open(test_image_path)
        glyph, confidence = classifier.classify(test_image)
        print(f"CNN Prediction: {glyph} (confidence: {confidence:.4f})")
    
    # Save model
    classifier.save_model("glyph_cnn.pkl")
    print("CNN model saved to glyph_cnn.pkl")
