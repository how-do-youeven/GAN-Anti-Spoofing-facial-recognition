"""
Silent Face Anti-Spoofing Service
Uses Silent-Face-Anti-Spoofing (minivision-ai) style models for silent liveness detection.
Expects full-frame image + face bbox (from InsightFace); runs MiniFASNet fusion on cropped patches.
"""
import os
import torch
import torch.nn.functional as F
import numpy as np
import cv2
from typing import Optional, Tuple, List

from vendor.silent_face_crop import CropImage
from vendor.silent_face_models import (
    parse_model_name,
    get_kernel,
    MODEL_MAPPING,
)


# Same interface as SpoofDetectionService for drop-in use
class SilentFaceSpoofService:
    """
    Anti-spoofing using Silent Face (MiniFASNet). Operates on full image + bbox.
    Label 1 = real face, 0 = fake (and optionally other classes in multi-class models).
    """

    uses_full_frame = True  # Caller passes full image + bbox (from InsightFace)
    REAL_FACE_THRESHOLD = 0.998  # Minimum score for "real" class after softmax sum
    _last_spoof_prob = None

    def __init__(self, model_dir: Optional[str] = None, device_id: int = 0):
        if model_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            model_dir = os.path.join(project_root, "Silent-Face-Anti-Spoofing", "resources", "anti_spoof_models")
        self.model_dir = os.path.abspath(model_dir)
        self.device = torch.device(f"cuda:{device_id}" if torch.cuda.is_available() else "cpu")
        self.image_cropper = CropImage()
        self._model_paths: List[str] = []
        self._load_model_paths()

    def _load_model_paths(self) -> None:
        if not os.path.isdir(self.model_dir):
            raise FileNotFoundError(
                f"Silent Face anti-spoof model dir not found: {self.model_dir}\n"
                "Clone https://github.com/minivision-ai/Silent-Face-Anti-Spoofing and download "
                "models into resources/anti_spoof_models (see repo README / Baidu link)."
            )
        self._model_paths = [
            os.path.join(self.model_dir, f)
            for f in os.listdir(self.model_dir)
            if f.endswith(".pth")
        ]
        if not self._model_paths:
            raise FileNotFoundError(
                f"No .pth models found in {self.model_dir}. "
                "Download anti-spoof .pth models (see Silent-Face-Anti-Spoofing README)."
            )

    def _load_model(self, model_path: str) -> torch.nn.Module:
        model_name = os.path.basename(model_path)
        h_input, w_input, model_type, _ = parse_model_name(model_name)
        kernel_size = get_kernel(h_input, w_input)
        model_cls = MODEL_MAPPING.get(model_type)
        if model_cls is None:
            raise ValueError(f"Unknown Silent Face model type: {model_type}")
        model = model_cls(conv6_kernel=kernel_size).to(self.device)
        state_dict = torch.load(model_path, map_location=self.device)
        keys_iter = iter(state_dict)
        first_key = next(keys_iter)
        if "module." in first_key:
            from collections import OrderedDict
            new_state_dict = OrderedDict()
            for k, v in state_dict.items():
                new_state_dict[k.replace("module.", "")] = v
            state_dict = new_state_dict
        # Some checkpoints (e.g. 4_0_0_80x80_MiniFASNetV1SE.pth) use se_fc1/se_bn1 instead of se_module.fc1/bn1
        from collections import OrderedDict
        remapped = OrderedDict()
        for k, v in state_dict.items():
            if "num_batches_tracked" in k:
                continue
            k2 = k.replace(".se_fc1.", ".se_module.fc1.").replace(".se_bn1.", ".se_module.bn1.").replace(".se_fc2.", ".se_module.fc2.").replace(".se_bn2.", ".se_module.bn2.")
            remapped[k2] = v
        model.load_state_dict(remapped, strict=False)
        model.eval()
        return model

    def _predict_one(self, patch_bgr: np.ndarray, model_path: str) -> np.ndarray:
        """Run one MiniFASNet model on a pre-cropped patch. patch_bgr: (H,W,3) BGR.
        Input range must match official repo: [0, 255] float (they use ToTensor without /255)."""
        h_input, w_input, _, _ = parse_model_name(model_path)
        patch = cv2.resize(patch_bgr, (w_input, h_input))
        # Official Silent-Face ToTensor returns img.float() without /255; model expects [0,255]
        patch = torch.from_numpy(patch).permute(2, 0, 1).float().unsqueeze(0).to(self.device)
        model = self._load_model(model_path)
        with torch.no_grad():
            logits = model(patch)
            probs = F.softmax(logits, dim=1).cpu().numpy()
        return probs

    def predict_with_bbox(self, img_bgr: np.ndarray, bbox: List[float]) -> Tuple[bool, float, float]:
        """
        Run Silent Face fusion on image with given face bbox.
        bbox: [x1, y1, x2, y2] (InsightFace style) or [left, top, width, height].
        Returns (is_real, real_prob, spoof_prob). Class index 1 = real in typical Silent Face models.
        """
        # Support [x1, y1, x2, y2] (InsightFace) or [left, top, width, height]
        if len(bbox) >= 4 and bbox[2] > bbox[0] and bbox[3] > bbox[1]:
            left = int(bbox[0])
            top = int(bbox[1])
            width = int(bbox[2] - bbox[0])
            height = int(bbox[3] - bbox[1])
        else:
            left, top, width, height = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        bbox_sf = [left, top, width, height]
        prediction = np.zeros((1, 4))  # Support up to 4 classes
        for model_path in self._model_paths:
            h_input, w_input, _, scale = parse_model_name(model_path)
            param = {
                "org_img": img_bgr,
                "bbox": bbox_sf,
                "scale": scale,
                "out_w": w_input,
                "out_h": h_input,
                "crop": scale is not None,
            }
            patch = self.image_cropper.crop(**param)
            probs = self._predict_one(patch, model_path)
            # Accumulate into same shape (probs may be (1,3) or (1,4))
            prediction[0, : probs.shape[1]] += probs[0]
        # Normalize by number of models
        n_models = len(self._model_paths)
        prediction /= n_models
        num_classes = min(4, prediction.shape[1])
        # Official minivision: 0=2D spoof, 1=live, 2=3D spoof. Always use index 1 = real (no env override).
        real_idx = 1 if num_classes >= 2 else 0
        spoof_idx = 0
        real_prob = float(prediction[0, real_idx])
        if num_classes >= 3:
            spoof_prob = float(1.0 - real_prob)
        else:
            spoof_prob = float(prediction[0, spoof_idx])
        is_real = real_prob >= self.REAL_FACE_THRESHOLD and real_prob >= spoof_prob
        self._last_spoof_prob = spoof_prob
        return is_real, real_prob, spoof_prob

    def check_if_real(
        self, img_rgb: np.ndarray, face_bbox: Optional[List[float]] = None
    ) -> Tuple[bool, Optional[str], float]:
        """
        Same interface as SpoofDetectionService.
        For Silent Face: pass full-frame img_rgb and face_bbox from InsightFace [x1,y1,x2,y2].
        """
        if face_bbox is None or len(face_bbox) < 4:
            self._last_spoof_prob = 1.0
            return False, "No face bbox provided for Silent Face anti-spoof", 0.0
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        try:
            is_real, real_prob, spoof_prob = self.predict_with_bbox(img_bgr, face_bbox)
            self._last_spoof_prob = spoof_prob
            if not is_real:
                return False, f"Spoofed face (real: {real_prob:.2%}, spoof: {spoof_prob:.2%})", real_prob
            return True, None, real_prob
        except Exception as e:
            self._last_spoof_prob = 1.0
            return False, f"Silent Face anti-spoof failed: {str(e)}", 0.0

    def detect_spoof(self, img_rgb: np.ndarray, face_bbox: Optional[List[float]] = None) -> Tuple[bool, float, float]:
        """Raw detection result. If no bbox, returns (False, 0.0, 1.0)."""
        if face_bbox is None or len(face_bbox) < 4:
            return False, 0.0, 1.0
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        return self.predict_with_bbox(img_bgr, face_bbox)
