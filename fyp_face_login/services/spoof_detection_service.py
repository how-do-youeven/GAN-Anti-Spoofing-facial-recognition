"""
Spoof Detection Service
Uses GAN predictor model to detect if a face is real or spoofed
"""
import os
import sys
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import numpy as np
from typing import Tuple, Optional


class SpoofDetectionService:
    """Service for detecting spoofed faces using the GAN predictor model (face-crop based)."""

    uses_full_frame = False  # This backend expects a pre-cropped face image, not full frame + bbox
    
    # Confidence threshold for real face detection
    # Higher value = stricter (more secure, but may reject some real faces)
    # Lower value = more lenient (may allow some spoofed faces)
    # NOTE: If real faces are rejected as spoof, lower this (e.g. 0.7). For production, use 0.85–0.93.
    REAL_FACE_THRESHOLD = 0.80  # Require 80% confidence that face is real (balanced for usability)
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize spoof detection service
        
        Args:
            model_path: Path to the predictor model checkpoint. 
                       If None, uses default path relative to project root.
        """
        if model_path is None:
            # Allow override via env (e.g. when running from another cwd or different layout)
            model_path = os.environ.get("GAN_PREDICTOR_MODEL_PATH")
        if model_path is None or model_path == "":
            # Default path: GAN_V1/ml/exports/predictor_best.pt relative to repo root
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
        """Load the predictor model from checkpoint. Supports both plain ResNet18 and GAN_V1 AntiSpoofAndIDModel (backbone+pool+spoof_head)."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Spoof detection model not found at: {self.model_path}\n"
                f"Please ensure the model file exists."
            )
        
        try:
            ckpt = torch.load(self.model_path, map_location="cpu")
            state = ckpt.get("model_state", ckpt)
            first_key = next(iter(state.keys()))
            
            # Extract metadata
            self.classes = ckpt.get("classes", ["spoof", "real"])
            self.img_size = ckpt.get("img_size", 224)
            self.mean = tuple(ckpt.get("mean", (0.485, 0.456, 0.406)))
            self.std = tuple(ckpt.get("std", (0.229, 0.224, 0.225)))
            
            if "backbone." in first_key:
                # GAN_V1 predictor: AntiSpoofAndIDModel (backbone + pool + spoof_head)
                self.model = self._load_gan_predictor(ckpt)
            else:
                # Plain ResNet18 + fc
                self.model = self._build_model(num_classes=len(self.classes))
                self.model.load_state_dict(state)
            
            self.model.to(self.device)
            self.model.eval()
            
            self.transform = transforms.Compose([
                transforms.Resize((self.img_size, self.img_size)),
                transforms.ToTensor(),
                transforms.Normalize(self.mean, self.std),
            ])
            
        except Exception as e:
            raise RuntimeError(f"Failed to load spoof detection model: {str(e)}")
    
    def _load_gan_predictor(self, ckpt: dict) -> nn.Module:
        """Load GAN_V1 AntiSpoofAndIDModel and return a module that forwards to spoof logits only."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        gan_src = os.path.join(project_root, "GAN_V1", "ml", "src")
        if gan_src not in sys.path:
            sys.path.insert(0, gan_src)
        from predictor.model import AntiSpoofAndIDModel
        
        full_model = AntiSpoofAndIDModel(num_spoof_classes=len(ckpt.get("classes", ["spoof", "real"])), emb_dim=256, pretrained=False)
        state = ckpt["model_state"]
        # Drop num_batches_tracked so load_state_dict doesn't complain if we use strict=False
        state = {k: v for k, v in state.items() if "num_batches_tracked" not in k}
        full_model.load_state_dict(state, strict=False)
        
        class SpoofLogitsOnly(nn.Module):
            def __init__(self, inner):
                super().__init__()
                self.inner = inner
            def forward(self, x):
                return self.inner(x)[0]
        
        return SpoofLogitsOnly(full_model)
    
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
            
            self._last_spoof_prob = spoof_prob
            if not is_real:
                return False, f"Spoofed face detected (real: {real_prob:.2%}, spoof: {spoof_prob:.2%})", real_prob
            
            return True, None, real_prob
            
        except Exception as e:
            print(f"SPOOF DETECTION ERROR: {str(e)}")
            return False, f"Spoof detection failed: {str(e)}", 0.0

