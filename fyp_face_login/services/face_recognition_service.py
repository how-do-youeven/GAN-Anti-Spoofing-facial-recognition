"""
Face Recognition Service
- Anti-spoofing: Silent Face (silent liveness) when available, else GAN predictor on face crop.
- Verification: InsightFace ArcFace only (512D embeddings, cosine distance).
- Thresholds and GPU are configurable via environment variables.
"""
import os
import numpy as np
import cv2
from typing import Optional, Tuple
from entities.face_encoding import FaceEncoding
from repositories.face_repository import FaceRepository
from repositories.user_repository import UserRepository
from services.spoof_detection_service import SpoofDetectionService


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default

# Try to import InsightFace (ArcFace for verification)
try:
    import insightface
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False

# face_recognition (dlib) only used for GAN spoof crop when spoof backend is crop-based
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    if not INSIGHTFACE_AVAILABLE:
        print("WARNING: Neither InsightFace nor face_recognition available!")


class FaceRecognitionService:
    """Service for face recognition: InsightFace ArcFace + optional GPU + configurable thresholds."""

    # Thresholds (override via env: FACE_SAME_THRESHOLD, FACE_VERIFY_THRESHOLD)
    SAME_FACE_THRESHOLD = _float_env("FACE_SAME_THRESHOLD", 0.35)
    VERIFY_THRESHOLD = _float_env("FACE_VERIFY_THRESHOLD", 0.38)
    SINGLE_FACE_THRESHOLD = _float_env("FACE_VERIFY_THRESHOLD", 0.38)
    # Registration quality: min Laplacian variance (blur), min face size, brightness range
    MIN_LAPLACIAN_VAR = _float_env("FACE_MIN_LAPLACIAN_VAR", 100.0)
    MIN_FACE_SIZE_REG = int(_float_env("FACE_MIN_FACE_SIZE_REG", 80))
    MIN_MEAN_BRIGHTNESS = _float_env("FACE_MIN_BRIGHTNESS", 40.0)
    MAX_MEAN_BRIGHTNESS = _float_env("FACE_MAX_BRIGHTNESS", 220.0)

    def __init__(self, face_repo: FaceRepository, user_repo: UserRepository,
                 spoof_detection: Optional[SpoofDetectionService] = None):
        self.face_repo = face_repo
        self.user_repo = user_repo
        self.use_insightface = INSIGHTFACE_AVAILABLE
        self.insightface_model_name: Optional[str] = None
        self.insightface_error: Optional[str] = None  # Set when init fails, for diagnostics

        if not INSIGHTFACE_AVAILABLE:
            self.face_app = None
            self.insightface_error = "insightface package not installed (ImportError). Run: pip install insightface onnxruntime"
            print("⚠️ InsightFace not installed; using dlib for face verification.")
        else:
            try:
                use_cpu_only = os.environ.get("FACE_USE_CPU", "").strip().lower() in ("1", "true", "yes")
                for model_name in ("buffalo_l", "antelopev2", "buffalo_s"):
                    providers_list = [["CPUExecutionProvider"]] if use_cpu_only else [["CUDAExecutionProvider", "CPUExecutionProvider"], ["CPUExecutionProvider"]]
                    for providers in providers_list:
                        try:
                            self.face_app = insightface.app.FaceAnalysis(name=model_name, providers=providers)
                            self.face_app.prepare(ctx_id=0, det_size=(640, 640))
                            self.insightface_model_name = model_name
                            print(f"✅ InsightFace initialized with {model_name} (providers: {providers})")
                            break
                        except Exception as e1:
                            if providers == ["CUDAExecutionProvider", "CPUExecutionProvider"] and "CUDA" in str(e1):
                                continue
                            raise e1
                    else:
                        continue
                    break
            except Exception as e:
                import traceback
                self.insightface_error = f"{type(e).__name__}: {e}"
                self.use_insightface = False
                self.face_app = None
                print(f"WARNING: InsightFace failed to load: {e}")
                traceback.print_exc()
                print("Tip: pip install onnxruntime. Set FACE_USE_CPU=1 for CPU-only. Run GET /api/diagnose/insightface for details.")
        
        # Initialize spoof detection service
        if spoof_detection is None:
            try:
                self.spoof_detection = SpoofDetectionService()
                print("✅ Spoof detection service initialized successfully")
            except Exception as e:
                print(f"WARNING: Spoof detection model not available: {str(e)}")
                print("WARNING: Continuing without spoof detection. System may be vulnerable to spoofing attacks.")
                self.spoof_detection = None
        else:
            self.spoof_detection = spoof_detection
            print("✅ Spoof detection service provided externally")
    
    @staticmethod
    def decode_base64_image(b64_str: str) -> np.ndarray:
        """Decode base64 image string to RGB numpy array"""
        import base64
        
        try:
            # Strip dataURL header: "data:image/jpeg;base64,..."
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            
            img_bytes = base64.b64decode(b64_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if bgr is None or bgr.size == 0:
                raise ValueError("Failed to decode image - invalid image data")
            
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            return rgb
        except Exception as e:
            raise ValueError(f"Failed to decode base64 image: {str(e)}")
    
    def get_face_embedding_insightface(self, img_rgb: np.ndarray) -> Tuple[Optional[np.ndarray], int]:
        """
        Extract face embedding using InsightFace
        Returns: (embedding, face_count)
        InsightFace returns 512-dimensional embeddings
        """
        if self.face_app is None:
            return None, 0
        
        # InsightFace expects BGR format
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        
        # Detect and extract faces
        faces = self.face_app.get(img_bgr)
        
        if len(faces) == 0:
            return None, 0
        
        if len(faces) > 1:
            # Multiple faces detected - use the largest face
            face_sizes = [face.bbox[2] * face.bbox[3] for face in faces]
            largest_face_idx = face_sizes.index(max(face_sizes))
            face = faces[largest_face_idx]
        else:
            face = faces[0]
        
        # Get embedding (512-dimensional)
        embedding = face.embedding
        return embedding, len(faces)
    
    def get_face_embedding_dlib(self, img_rgb: np.ndarray) -> Tuple[Optional[np.ndarray], int]:
        """
        Extract face embedding using dlib (fallback)
        Returns: (embedding, face_count)
        """
        locations = face_recognition.face_locations(img_rgb, model='hog')
        
        if len(locations) == 0:
            return None, 0
        
        if len(locations) > 1:
            # Multiple faces detected - use the largest face
            face_sizes = [(bottom - top) * (right - left) for top, right, bottom, left in locations]
            largest_face_idx = face_sizes.index(max(face_sizes))
            locations = [locations[largest_face_idx]]
        
        encoding = face_recognition.face_encodings(img_rgb, locations)[0]
        return encoding, len(locations)
    
    def get_face_embedding(self, img_rgb: np.ndarray) -> Tuple[Optional[np.ndarray], int]:
        """
        Extract face embedding from image
        Uses InsightFace if available, otherwise falls back to dlib
        Returns: (embedding, face_count)
        """
        if self.use_insightface:
            return self.get_face_embedding_insightface(img_rgb)
        else:
            return self.get_face_embedding_dlib(img_rgb)
    
    @staticmethod
    def cosine_distance(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine distance between two embeddings"""
        # Normalize embeddings
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 1.0
        
        # Cosine similarity
        cosine_sim = np.dot(embedding1, embedding2) / (norm1 * norm2)
        
        # Convert to distance (0 = identical, 1 = completely different)
        distance = 1.0 - cosine_sim
        
        return float(distance)
    
    @staticmethod
    def euclidean_distance(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate euclidean distance between two embeddings (for dlib)"""
        return float(np.linalg.norm(embedding1 - embedding2))

    def _check_registration_quality(self, img_rgb: np.ndarray) -> Tuple[bool, Optional[str]]:
        """Reject very blurry, tiny, or badly lit images so we don't store weak templates."""
        h, w = img_rgb.shape[:2]
        if min(w, h) < self.MIN_FACE_SIZE_REG:
            return False, f"Image too small ({w}x{h}). Use at least {self.MIN_FACE_SIZE_REG}px on each side."
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < self.MIN_LAPLACIAN_VAR:
            return False, f"Image too blurry. Please use a clearer photo (quality: {laplacian_var:.0f}, min: {self.MIN_LAPLACIAN_VAR:.0f})."
        mean_bright = float(np.mean(gray))
        if mean_bright < self.MIN_MEAN_BRIGHTNESS:
            return False, "Image too dark. Please improve lighting."
        if mean_bright > self.MAX_MEAN_BRIGHTNESS:
            return False, "Image too bright. Please reduce glare or use softer lighting."
        return True, None

    def register_face(self, image_b64: str, user_id: str, 
                     check_duplicates: bool = True) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Register face for a user using InsightFace ArcFace.
        Only 512D ArcFace embeddings are stored. Spoof detection is not run at registration.
        Returns: (success, error_message, distance_if_duplicate)
        """
        if not self.use_insightface:
            return False, (
                "Face registration requires InsightFace. Please install: pip install insightface onnxruntime. "
                "Then restart the server."
            ), None

        # Decode, quality check, then extract face with InsightFace only
        try:
            img_rgb = self.decode_base64_image(image_b64)
            ok, msg = self._check_registration_quality(img_rgb)
            if not ok:
                return False, msg, None
            embedding, face_count = self.get_face_embedding_insightface(img_rgb)
            
            if embedding is None:
                if face_count == 0:
                    return False, "No face detected in image. Please ensure your face is clearly visible and try again.", None
                elif face_count > 1:
                    return False, f"Multiple faces detected ({face_count}). Please ensure only one face is visible in the image.", None
                else:
                    return False, f"Failed to extract face embedding. Face count: {face_count}", None
        except Exception as e:
            print(f"ERROR in register_face: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Error processing face image: {str(e)}", None
        
        # Check for duplicates if requested
        if check_duplicates:
            user_ids, known_embeddings = self.face_repo.get_all_encodings_array()
            
            if user_ids and len(user_ids) > 0:
                # Detect embedding dimension
                current_embedding_dim = len(embedding)
                
                # Calculate distances - handle dimension mismatches
                distances = []
                for known_emb in known_embeddings:
                    known_dim = len(known_emb)
                    
                    # Only compare if dimensions match
                    if current_embedding_dim != known_dim:
                        distances.append(1.0)  # Skip mismatched dimensions
                        continue
                    
                    # Calculate distance based on dimension
                    if current_embedding_dim == 512:
                        distances.append(self.cosine_distance(embedding, known_emb))
                    elif current_embedding_dim == 128:
                        if self.use_insightface:
                            distances.append(1.0)  # Can't compare InsightFace with dlib
                        else:
                            distances.append(self.euclidean_distance(embedding, known_emb))
                    else:
                        distances.append(1.0)
                
                if len(distances) > 0:
                    best_idx = int(np.argmin(distances))
                    best_distance = float(distances[best_idx])
                    best_user = user_ids[best_idx]
                    
                    if best_distance <= self.SAME_FACE_THRESHOLD:
                        if best_user == user_id:
                            # Face already registered to this account
                            return True, "Face already registered to this account", best_distance
                        else:
                            # Face registered to another account
                            return False, "This face is already registered to another account", best_distance
        
        # Store only InsightFace ArcFace 512D
        if len(embedding) != 512:
            return False, f"Invalid embedding dimension ({len(embedding)}). InsightFace ArcFace must be 512D.", None
        face_encoding = FaceEncoding(user_id=user_id, encoding=embedding, image_b64=image_b64, encoding_dlib=None)
        self.face_repo.save(face_encoding)
        
        # Update user's face_registered status
        users = self.user_repo.load_all()
        for email, user in users.items():
            if user.user_id == user_id:
                user.face_registered = True
                self.user_repo.save(user)
                break
        
        return True, None, None
    
    def verify_face(self, image_b64: str) -> Tuple[bool, Optional[str], Optional[float], Optional[float], Optional[float]]:
        """
        Verify face for login.
        Anti-spoof: Silent Face (full frame + bbox) or GAN (face crop).
        Verification: InsightFace ArcFace only.
        Returns: (success, user_id_if_found, distance, real_prob, spoof_prob).
        distance = -1.0 => spoof; -2.0 => face too small. real_prob/spoof_prob from anti-spoof model when available.
        """
        try:
            from activity_log import log as activity_log
        except ImportError:
            activity_log = None

        def _log(reason=None, real_prob=None, spoof_prob=None, spoof_passed=None, verify_success=None, user_id=None, distance=None):
            if activity_log is None:
                return
            if spoof_prob is None and self.spoof_detection:
                spoof_prob = getattr(self.spoof_detection, "_last_spoof_prob", None)
            activity_log(
                event="face_verify",
                reason=reason,
                real_prob=real_prob,
                spoof_prob=spoof_prob,
                spoof_passed=spoof_passed,
                verify_success=verify_success,
                user_id=user_id,
                distance=distance,
            )

        img_rgb = self.decode_base64_image(image_b64)
        uses_full_frame = getattr(self.spoof_detection, "uses_full_frame", False)

        # --- Get face and embedding from InsightFace (required for verification) ---
        if not self.use_insightface:
            _log(reason="insightface_unavailable")
            return False, None, None, None, None
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        faces = self.face_app.get(img_bgr)
        if len(faces) == 0:
            _log(reason="no_face_detected")
            return False, None, None, None, None
        if len(faces) > 1:
            face_sizes = [f.bbox[2] * f.bbox[3] for f in faces]
            face = faces[int(np.argmax(face_sizes))]
        else:
            face = faces[0]
        embedding = face.embedding
        bbox = face.bbox
        face_w = int(bbox[2] - bbox[0])
        face_h = int(bbox[3] - bbox[1])
        MIN_RECOMMENDED_FACE_SIZE = 100
        if face_w < MIN_RECOMMENDED_FACE_SIZE or face_h < MIN_RECOMMENDED_FACE_SIZE:
            print(f"INFO: Face too small ({face_w}x{face_h}) - come closer")
            _log(reason="face_too_small", distance=-2.0)
            return False, None, -2.0, None, None

        # --- Anti-spoof ---
        real_prob, spoof_passed = None, True
        if self.spoof_detection is not None:
            if uses_full_frame:
                is_real, error_msg, real_prob = self.spoof_detection.check_if_real(img_rgb, face_bbox=bbox.tolist())
            else:
                if not FACE_RECOGNITION_AVAILABLE:
                    _log(reason="dlib_unavailable")
                    return False, None, None, None, None
                locations = face_recognition.face_locations(img_rgb, model="hog")
                if len(locations) == 0:
                    _log(reason="no_face_detected")
                    return False, None, None, None, None
                if len(locations) > 1:
                    sizes = [(b - t) * (r - l) for t, r, b, l in locations]
                    locations = [locations[np.argmax(sizes)]]
                top, right, bottom, left = locations[0]
                padding = 20
                face_crop = img_rgb[
                    max(0, top - padding) : min(img_rgb.shape[0], bottom + padding),
                    max(0, left - padding) : min(img_rgb.shape[1], right + padding),
                ]
                if face_crop.size == 0 or face_crop.shape[0] < 30 or face_crop.shape[1] < 30:
                    _log(reason="face_too_small", distance=-2.0)
                    return False, None, -2.0, None, None
                face_gray = np.mean(face_crop, axis=2) if len(face_crop.shape) == 3 else face_crop
                if np.var(face_gray) < 200:
                    _log(reason="spoof_detected", spoof_passed=False, distance=-1.0)
                    return False, None, -1.0, None, None
                is_real, error_msg, real_prob = self.spoof_detection.check_if_real(face_crop)
            spoof_passed = is_real
            if not is_real:
                spoof_prob = getattr(self.spoof_detection, "_last_spoof_prob", None)
                print(f"BLOCKED: Spoof detected - {error_msg}")
                _log(real_prob=real_prob, spoof_prob=spoof_prob, spoof_passed=False, reason="spoof_detected", distance=-1.0)
                return False, None, -1.0, real_prob, spoof_prob
            print(f"PASSED: Real face (confidence: {real_prob:.2%})")

        # --- Verification: InsightFace ArcFace only ---
        all_encodings = self.face_repo.load_all()
        if not all_encodings or len(all_encodings) == 0:
            _log(real_prob=real_prob, spoof_passed=spoof_passed, reason="no_registered_faces", distance=-3.0)
            return False, None, -3.0, real_prob, None

        success, user_id, distance = self._verify_with_embedding(embedding, model_type="insightface")
        spoof_prob = getattr(self.spoof_detection, "_last_spoof_prob", None) if self.spoof_detection else None
        _log(real_prob=real_prob, spoof_prob=spoof_prob, spoof_passed=spoof_passed, verify_success=success, user_id=user_id, distance=distance, reason=None if success else "match_failed")
        if success:
            print(f"VERIFY: InsightFace ArcFace match - user: {user_id}, distance: {distance:.3f}")
        return success, user_id, distance, real_prob, spoof_prob
    
    def _verify_with_embedding(self, embedding: np.ndarray, model_type: str = 'insightface') -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Verify face using a specific embedding and model type
        Helper method for dual-model verification
        
        Args:
            embedding: Face embedding (128D for dlib or 512D for InsightFace)
            model_type: 'insightface' or 'dlib'
        
        Returns:
            (success, user_id_if_found, distance)
        """
        # Get all registered faces
        all_encodings = self.face_repo.load_all()
        
        if not all_encodings or len(all_encodings) == 0:
            return False, None, None
        
        # Detect embedding dimension
        current_embedding_dim = len(embedding)
        
        # Calculate distances - handle dimension mismatches and dual-model storage
        distances = []
        user_ids = []
        
        for user_id, face_encoding in all_encodings.items():
            # Get the appropriate embedding based on model type
            if model_type == 'insightface':
                # Use primary encoding (should be InsightFace 512D)
                known_emb = face_encoding.encoding
            else:  # dlib
                # Use dlib encoding if available, otherwise skip this user
                if face_encoding.encoding_dlib is not None:
                    known_emb = face_encoding.encoding_dlib
                else:
                    # User doesn't have dlib embedding - skip for dlib verification
                    distances.append(1.0)
                    user_ids.append(user_id)
                    continue
            
            user_ids.append(user_id)
            known_dim = len(known_emb)
            
            # Only compare embeddings of the same dimension
            if current_embedding_dim != known_dim:
                distances.append(1.0)  # Maximum distance = no match
                continue
            
            # Dimensions match - calculate distance based on model type
            if current_embedding_dim == 512:
                # Both are InsightFace - use cosine distance
                distances.append(self.cosine_distance(embedding, known_emb))
            elif current_embedding_dim == 128:
                # Both are dlib - use euclidean distance
                distances.append(self.euclidean_distance(embedding, known_emb))
            else:
                # Unknown dimension
                distances.append(1.0)
        
        if len(distances) == 0:
            return False, None, None
        
        # Find best match
        best_idx = int(np.argmin(distances))
        best_distance = float(distances[best_idx])
        best_user = user_ids[best_idx]
        
        # Matching logic based on model type
        if model_type == 'insightface':
            threshold = self.VERIFY_THRESHOLD  # 0.38
            single_threshold = self.SINGLE_FACE_THRESHOLD  # 0.38
        else:  # dlib
            threshold = 0.38  # Same threshold as InsightFace
            single_threshold = 0.38  # Same threshold as InsightFace
        
        # Very strict matching for security
        # Must be below threshold AND (if multiple faces) significantly better than second best
        if len(distances) > 1:
            # Get second best distance
            sorted_distances = sorted(distances)
            second_best_distance = float(sorted_distances[1])
            
            # Check if best match is significantly better than second best
            distance_difference = second_best_distance - best_distance
            
            # Best match must be below threshold AND at least 0.15 better than second best
            if best_distance <= threshold:
                if distance_difference >= 0.15:
                    # Clear best match - significantly better than others
                    return True, best_user, best_distance
                else:
                    # Ambiguous match - distances too close, reject for security
                    return False, best_user, best_distance
            else:
                # Best match is above threshold - not close enough
                return False, best_user, best_distance
        else:
            # Only one registered face - strict matching
            if best_distance <= single_threshold:
                # Distance is low - confident match
                return True, best_user, best_distance
            else:
                # Distance too high - reject
                return False, best_user, best_distance
    
    def reset_face(self, image_b64: str, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Reset face encoding for a user
        Returns: (success, error_message)
        """
        # Delete old face data
        self.face_repo.delete(user_id)
        
        # Register new face (without duplicate check since we're resetting)
        success, error_msg, _ = self.register_face(image_b64, user_id, check_duplicates=False)
        
        return success, error_msg
    
    def get_face_image(self, user_id: str) -> Optional[str]:
        """
        Get the registered face image for a user
        Returns: base64 image string or None if not found
        """
        face_encoding = self.face_repo.find_by_user_id(user_id)
        if face_encoding and face_encoding.image_b64:
            return face_encoding.image_b64
        return None
