"""
Spoof Detection Service
Uses GAN predictor model to detect if a face is real or spoofed
"""
import os
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import numpy as np
from typing import Tuple, Optional


class SpoofDetectionService:
    """Service for detecting spoofed faces using the GAN predictor model"""
    
    # Confidence threshold for real face detection
    # Higher value = stricter (more secure, but may reject some real faces)
    # Lower value = more lenient (may allow some spoofed faces)
    # NOTE: If you're getting false positives (real faces detected as spoofed),
    # try lowering this threshold (e.g., 0.5 or 0.3)
    # For security: Use higher threshold to block photos/videos
    REAL_FACE_THRESHOLD = 0.93  # Require 93% confidence that face is real (EXTREMELY STRICT for spoof detection)
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize spoof detection service
        
        Args:
            model_path: Path to the predictor model checkpoint. 
                       If None, uses default path relative to project root.
        """
        if model_path is None:
            # Default path: GAN_V1/ml/exports/predictor_best.pt
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            model_path = os.path.join(project_root, "GAN_V1", "ml", "exports", "predictor_best.pt")
        
        self.model_path = model_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.classes = None
        self.img_size = None
        self.mean = None
        self.std = None
        self.transform = None
        self._last_spoof_prob = None  # Store last spoof probability for additional checks
        
        # Load model on initialization
        self._load_model()
    
    def _build_model(self, num_classes: int = 2) -> nn.Module:
        """Build the predictor model (ResNet18)"""
        model = models.resnet18(weights=None)
        model.fc = nn.Linear(model.fc.in_features, num_classes)
        return model
    
    def _load_model(self):
        """Load the predictor model from checkpoint"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Spoof detection model not found at: {self.model_path}\n"
                f"Please ensure the model file exists."
            )
        
        try:
            ckpt = torch.load(self.model_path, map_location="cpu")
            
            # Extract model parameters
            self.classes = ckpt.get("classes", ["spoof", "real"])
            self.img_size = ckpt.get("img_size", 224)
            self.mean = ckpt.get("mean", (0.485, 0.456, 0.406))
            self.std = ckpt.get("std", (0.229, 0.224, 0.225))
            
            # Build and load model
            self.model = self._build_model(num_classes=len(self.classes))
            self.model.load_state_dict(ckpt["model_state"])
            self.model.to(self.device)
            self.model.eval()
            
            # Create transform pipeline
            self.transform = transforms.Compose([
                transforms.Resize((self.img_size, self.img_size)),
                transforms.ToTensor(),
                transforms.Normalize(self.mean, self.std),
            ])
            
        except Exception as e:
            raise RuntimeError(f"Failed to load spoof detection model: {str(e)}")
    
    def _numpy_to_pil(self, img_rgb: np.ndarray) -> Image.Image:
        """Convert numpy RGB array to PIL Image"""
        # Ensure values are in [0, 255] range and uint8
        if img_rgb.max() <= 1.0:
            img_rgb = (img_rgb * 255).astype(np.uint8)
        else:
            img_rgb = img_rgb.astype(np.uint8)
        
        return Image.fromarray(img_rgb)
    
    @torch.no_grad()
    def detect_spoof(self, img_rgb: np.ndarray) -> Tuple[bool, float, float]:
        """
        Detect if a face image is real or spoofed
        
        Args:
            img_rgb: RGB image as numpy array (H, W, 3)
        
        Returns:
            (is_real, real_probability, spoof_probability)
            - is_real: True if face is detected as real (above threshold)
            - real_probability: Confidence that face is real (0.0 to 1.0)
            - spoof_probability: Confidence that face is spoofed (0.0 to 1.0)
        """
        if self.model is None:
            raise RuntimeError("Spoof detection model not loaded")
        
        # Convert numpy array to PIL Image
        pil_image = self._numpy_to_pil(img_rgb)
        
        # Apply transforms and add batch dimension
        img_tensor = self.transform(pil_image).unsqueeze(0).to(self.device)
        
        # Run inference
        logits = self.model(img_tensor)
        probs = torch.softmax(logits, dim=1).squeeze(0).cpu()
        
        # Extract probabilities
        # Check actual class order from model
        if self.classes[0] == "spoof" and self.classes[1] == "real":
            spoof_prob = float(probs[0])
            real_prob = float(probs[1])
        elif self.classes[0] == "real" and self.classes[1] == "spoof":
            # Classes are reversed
            real_prob = float(probs[0])
            spoof_prob = float(probs[1])
        else:
            # Default assumption: ["spoof", "real"]
            spoof_prob = float(probs[0])
            real_prob = float(probs[1])
            print(f"WARNING: Unknown class order: {self.classes}, assuming [spoof, real]")
        
        # Determine if face is real - EXTREMELY STRICT criteria for spoof detection:
        # 1. real_prob must be >= threshold (extremely high confidence it's real)
        # 2. Block if spoof_prob > 0.08 (8%) - EXTREMELY STRICT to block spoofs
        # 3. Block if spoof_prob >= real_prob (spoof confidence >= real confidence)
        # 4. Require real_prob to be at least 0.30 (30%) higher than spoof_prob (EXTREMELY STRICT)
        # 5. Block if spoof_prob > 0.03 and real_prob < 0.97 (suspicious pattern - EXTREMELY STRICT)
        SPOOF_BLOCK_THRESHOLD = 0.08  # Block if spoof confidence > 8% (EXTREMELY STRICT for security)
        MIN_REAL_ADVANTAGE = 0.30  # Require real_prob to be at least 30% higher (EXTREMELY STRICT)
        SUSPICIOUS_THRESHOLD = 0.03  # If spoof > 3%, require real > 97% (EXTREMELY STRICT)
        
        # Block if spoof_prob is high OR if spoof_prob >= real_prob OR if advantage is too small OR suspicious pattern
        is_spoofed = (spoof_prob > SPOOF_BLOCK_THRESHOLD) or (spoof_prob >= real_prob) or ((real_prob - spoof_prob) < MIN_REAL_ADVANTAGE) or (spoof_prob > SUSPICIOUS_THRESHOLD and real_prob < 0.97)
        
        # Only allow if NOT spoofed AND real_prob is high enough (EXTREMELY STRICT)
        is_real = not is_spoofed and (real_prob >= self.REAL_FACE_THRESHOLD)
        
        return is_real, real_prob, spoof_prob
    
    def check_if_real(self, img_rgb: np.ndarray) -> Tuple[bool, Optional[str], float]:
        """
        Check if face is real (convenience method for integration)
        
        Args:
            img_rgb: RGB image as numpy array
        
        Returns:
            (is_real, error_message, real_probability)
            - is_real: True if face is real
            - error_message: Error message if detection failed, None otherwise
            - real_probability: Confidence that face is real
        """
        try:
            is_real, real_prob, spoof_prob = self.detect_spoof(img_rgb)
            
            # Store spoof_prob for later use
            self._last_spoof_prob = spoof_prob
            
            # Log the detection results for debugging
            SPOOF_BLOCK_THRESHOLD = 0.08
            MIN_REAL_ADVANTAGE = 0.30
            SUSPICIOUS_THRESHOLD = 0.03
            is_spoofed_check = (spoof_prob > SPOOF_BLOCK_THRESHOLD) or (spoof_prob >= real_prob) or ((real_prob - spoof_prob) < MIN_REAL_ADVANTAGE) or (spoof_prob > SUSPICIOUS_THRESHOLD and real_prob < 0.97)
            advantage = real_prob - spoof_prob
            suspicious = spoof_prob > SUSPICIOUS_THRESHOLD and real_prob < 0.97
            print(f"SPOOF DETECTION: real={real_prob:.2%}, spoof={spoof_prob:.2%}, threshold={self.REAL_FACE_THRESHOLD:.2%}, classes={self.classes}, result={'REAL' if is_real else 'SPOOFED'}")
            print(f"  -> real_prob >= threshold? {real_prob >= self.REAL_FACE_THRESHOLD} ({real_prob:.3f} >= {self.REAL_FACE_THRESHOLD:.3f})")
            print(f"  -> spoof_prob > {SPOOF_BLOCK_THRESHOLD:.2%}? {spoof_prob > SPOOF_BLOCK_THRESHOLD} ({spoof_prob:.3f} > {SPOOF_BLOCK_THRESHOLD:.3f})")
            print(f"  -> spoof_prob >= real_prob? {spoof_prob >= real_prob} ({spoof_prob:.3f} >= {real_prob:.3f})")
            print(f"  -> advantage (real-spoof) >= {MIN_REAL_ADVANTAGE:.2%}? {advantage >= MIN_REAL_ADVANTAGE} ({advantage:.3f} >= {MIN_REAL_ADVANTAGE:.3f})")
            print(f"  -> suspicious pattern (spoof>{SUSPICIOUS_THRESHOLD:.2%} & real<97%)? {suspicious}")
            print(f"  -> BLOCKED BY SPOOF CHECK? {is_spoofed_check}")
            
            if not is_real:
                return False, f"Spoofed face detected (real: {real_prob:.2%}, spoof: {spoof_prob:.2%})", real_prob
            
            return True, None, real_prob
            
        except Exception as e:
            print(f"SPOOF DETECTION ERROR: {str(e)}")
            return False, f"Spoof detection failed: {str(e)}", 0.0

