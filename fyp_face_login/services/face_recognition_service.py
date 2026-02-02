"""
Face Recognition Service
Business logic for facial recognition operations using InsightFace (ArcFace)
Better handling of glasses and occlusions compared to dlib
"""
import numpy as np
import cv2
from typing import Optional, Tuple
from entities.face_encoding import FaceEncoding
from repositories.face_repository import FaceRepository
from repositories.user_repository import UserRepository
from services.spoof_detection_service import SpoofDetectionService

# Try to import InsightFace, fallback to face_recognition if not available
try:
    import insightface
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False

# Always import face_recognition for spoof detection (model was trained on dlib crops)
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    if not INSIGHTFACE_AVAILABLE:
        print("WARNING: Neither InsightFace nor face_recognition available!")


class FaceRecognitionService:
    """Service for face recognition business logic"""
    
    # Thresholds for face matching using InsightFace (cosine similarity)
    # InsightFace uses cosine similarity: higher = more similar (opposite of distance)
    # We convert to distance: distance = 1 - cosine_similarity
    # Lower distance = better match
    # InsightFace typically uses threshold around 0.3-0.4 for cosine distance
    SAME_FACE_THRESHOLD = 0.35  # For duplicate detection during registration (balanced - allows new faces but detects duplicates)
    VERIFY_THRESHOLD = 0.38  # For login verification (InsightFace threshold)
    SINGLE_FACE_THRESHOLD = 0.38  # For single face verification (InsightFace threshold)
    
    def __init__(self, face_repo: FaceRepository, user_repo: UserRepository, 
                 spoof_detection: Optional[SpoofDetectionService] = None):
        self.face_repo = face_repo
        self.user_repo = user_repo
        self.use_insightface = INSIGHTFACE_AVAILABLE
        
        # Initialize InsightFace model if available
        if self.use_insightface:
            try:
                # Initialize InsightFace app
                # Try buffalo_l first (most accurate), fallback to antelopev2
                try:
                    self.face_app = insightface.app.FaceAnalysis(
                        name='buffalo_l',  # Best accuracy model
                        providers=['CPUExecutionProvider']
                    )
                    self.face_app.prepare(ctx_id=0, det_size=(640, 640))
                    print("✅ InsightFace initialized with buffalo_l model (best accuracy)")
                except Exception:
                    # Fallback to antelopev2
                    self.face_app = insightface.app.FaceAnalysis(
                        name='antelopev2',
                        providers=['CPUExecutionProvider']
                    )
                    self.face_app.prepare(ctx_id=0, det_size=(640, 640))
                    print("✅ InsightFace initialized with antelopev2 model")
            except Exception as e:
                print(f"WARNING: Failed to initialize InsightFace: {str(e)}")
                print("Falling back to face_recognition library (dlib)")
                self.use_insightface = False
                self.face_app = None
        else:
            self.face_app = None
            print("⚠️ Using face_recognition library (dlib) - InsightFace not installed")
        
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
    
    def register_face(self, image_b64: str, user_id: str, 
                     check_duplicates: bool = True) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Register face for a user
        NOTE: Spoof detection is NOT performed during registration - only during login
        Returns: (success, error_message, distance_if_duplicate)
        """
        # Decode and extract face
        try:
            img_rgb = self.decode_base64_image(image_b64)
            embedding, face_count = self.get_face_embedding(img_rgb)
            
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
        
        # Register the face (store image for later viewing)
        # Store both embeddings if both models are available (for dual-model verification)
        dlib_embedding = None
        if self.use_insightface and FACE_RECOGNITION_AVAILABLE:
            # If using InsightFace as primary, also extract dlib embedding for verification
            try:
                dlib_embedding, _ = self.get_face_embedding_dlib(img_rgb)
                if dlib_embedding is not None:
                    print(f"INFO: Storing both InsightFace (512D) and dlib (128D) embeddings for dual-model verification")
            except Exception as e:
                print(f"WARNING: Could not extract dlib embedding for dual-model verification: {str(e)}")
        
        face_encoding = FaceEncoding(user_id=user_id, encoding=embedding, image_b64=image_b64, encoding_dlib=dlib_embedding)
        self.face_repo.save(face_encoding)
        
        # Update user's face_registered status
        users = self.user_repo.load_all()
        for email, user in users.items():
            if user.user_id == user_id:
                user.face_registered = True
                self.user_repo.save(user)
                break
        
        return True, None, None
    
    def verify_face(self, image_b64: str) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Verify face for login
        Returns: (success, user_id_if_found, distance)
        Note: distance = -1.0 indicates spoofed face detected
        """
        # Decode and extract face
        img_rgb = self.decode_base64_image(image_b64)
        
        # IMPORTANT: For spoof detection, always use dlib face detection
        # because the GAN model was trained on dlib-style face crops
        # This ensures compatibility with the trained model
        if not FACE_RECOGNITION_AVAILABLE:
            return False, None, None
        
        # Use dlib for face detection (for spoof detection compatibility)
        locations = face_recognition.face_locations(img_rgb, model='hog')
        if len(locations) == 0:
            return False, None, None
        
        if len(locations) > 1:
            face_sizes = [(bottom - top) * (right - left) for top, right, bottom, left in locations]
            largest_face_idx = face_sizes.index(max(face_sizes))
            locations = [locations[largest_face_idx]]
        
        # Crop face for spoof detection using dlib coordinates (matches training data)
        top, right, bottom, left = locations[0]
        padding = 20
        face_crop = img_rgb[max(0, top-padding):min(img_rgb.shape[0], bottom+padding),
                           max(0, left-padding):min(img_rgb.shape[1], right+padding)]
        import sys
        sys.stdout.flush()
        
        # Now get embedding using InsightFace (if available) or dlib (fallback)
        if self.use_insightface:
            # Use InsightFace for better recognition accuracy
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            faces = self.face_app.get(img_bgr)
            
            if len(faces) == 0:
                return False, None, None
            
            if len(faces) > 1:
                face_sizes = [face.bbox[2] * face.bbox[3] for face in faces]
                largest_face_idx = face_sizes.index(max(face_sizes))
                face = faces[largest_face_idx]
            else:
                face = faces[0]
            
            # Get embedding from InsightFace
            embedding = face.embedding
            face_count = len(faces)
        else:
            # Fallback to dlib for embedding too
            embedding = face_recognition.face_encodings(img_rgb, locations)[0]
            face_count = len(locations)
        
        # Check face size first - prompt user to come closer if face is too small
        MIN_RECOMMENDED_FACE_SIZE = 100  # Recommended minimum face size for good quality detection
        face_height, face_width = face_crop.shape[0], face_crop.shape[1]
        
        if face_height < MIN_RECOMMENDED_FACE_SIZE or face_width < MIN_RECOMMENDED_FACE_SIZE:
            print(f"INFO: Face too small ({face_height}x{face_width}) - recommending user to come closer")
            # Return special distance -2.0 to indicate face too small (different from -1.0 for spoof)
            return False, None, -2.0
        
        # Check for spoofing on the cropped face (before face recognition)
        # IMPORTANT: Always run spoof detection - use STRICT thresholds for faces at right distance
        if self.spoof_detection is not None:
            # Ensure face crop is valid (minimum size for processing)
            MIN_FACE_SIZE_FOR_PROCESSING = 30  # Minimum size just to ensure we can process it
            if face_crop.size == 0 or face_crop.shape[0] < MIN_FACE_SIZE_FOR_PROCESSING or face_crop.shape[1] < MIN_FACE_SIZE_FOR_PROCESSING:
                print(f"WARNING: Face crop too small ({face_crop.shape[0]}x{face_crop.shape[1]}) to process - rejecting")
                return False, None, -2.0  # Return -2.0 to indicate face too small
            
            # Additional quality check: ensure face has reasonable variance (not a flat/blank image)
            face_gray = np.mean(face_crop, axis=2) if len(face_crop.shape) == 3 else face_crop
            face_variance = np.var(face_gray)
            MIN_VARIANCE = 200  # Minimum variance for a valid face image (EXTREMELY STRICT to reject flat images)
            if face_variance < MIN_VARIANCE:
                print(f"WARNING: Face image has low variance ({face_variance:.1f}) - possible flat/blank image - rejecting")
                return False, None, -1.0
            
            # Run spoof detection with STRICT thresholds
            is_real, error_msg, real_prob = self.spoof_detection.check_if_real(face_crop)
            spoof_prob = getattr(self.spoof_detection, '_last_spoof_prob', 1.0 - real_prob)
            print(f"SPOOF CHECK: is_real={is_real}, real_prob={real_prob:.3f}, spoof_prob={spoof_prob:.3f}, threshold={self.spoof_detection.REAL_FACE_THRESHOLD:.3f}, face_size={face_crop.shape[0]}x{face_crop.shape[1]}, variance={face_variance:.1f}")
            
            if not is_real:
                # Return False with special distance -1.0 to indicate spoofed face
                print(f"BLOCKED: Spoofed face detected - {error_msg}")
                return False, None, -1.0
            
            # For faces at the right distance (>= 100x100), apply ADDITIONAL EXTREMELY strict checks
            # Photos at the right distance can sometimes pass initial spoof detection
            if face_height >= MIN_RECOMMENDED_FACE_SIZE and face_width >= MIN_RECOMMENDED_FACE_SIZE:
                print(f"INFO: Face at recommended size ({face_height}x{face_width}) - applying additional EXTREMELY strict spoof checks")
                # Require extremely high real_prob for faces at right distance (they should be clearly real)
                if real_prob < 0.95:  # EXTREMELY strict - require 95% confidence for faces at right distance
                    print(f"BLOCKED: Face at right distance but insufficient real_prob ({real_prob:.2%} < 95%) - likely spoof")
                    return False, None, -1.0
                # Also check if spoof_prob is suspiciously high even if real_prob passes
                if spoof_prob > 0.08:  # If spoof confidence > 8%, block it (EXTREMELY strict)
                    print(f"BLOCKED: Face at right distance but spoof_prob too high ({spoof_prob:.2%} > 8%) - likely spoof")
                    return False, None, -1.0
                # Additional check: require even larger advantage for faces at right distance
                if (real_prob - spoof_prob) < 0.35:  # Require 35% advantage (EXTREMELY strict)
                    print(f"BLOCKED: Face at right distance but advantage too small ({(real_prob - spoof_prob):.2%} < 35%) - likely spoof")
                    return False, None, -1.0
            
            print(f"PASSED: Real face confirmed (confidence: {real_prob:.2%})")
        
        if embedding is None:
            return False, None, None
        
        # OPTION 4: Primary + Verification approach
        # Step 1: Run InsightFace as primary (faster, better accuracy)
        print("=" * 50)
        print("PRIMARY VERIFICATION: Running InsightFace...")
        primary_success, primary_user, primary_distance = self._verify_with_embedding(embedding, model_type='insightface')
        
        if not primary_success:
            print(f"PRIMARY FAILED: InsightFace did not find a match (distance: {primary_distance})")
            return False, primary_user, primary_distance
        
        print(f"PRIMARY PASSED: InsightFace found match - user: {primary_user}, distance: {primary_distance:.3f}")
        
        # Step 2: If primary passes, run dlib as verification (both must agree)
        # Check if user has dlib embedding stored (for backward compatibility)
        user_face_encoding = self.face_repo.find_by_user_id(primary_user)
        has_dlib_embedding = user_face_encoding and user_face_encoding.encoding_dlib is not None
        
        if FACE_RECOGNITION_AVAILABLE and has_dlib_embedding:
            print("VERIFICATION: Running dlib verification...")
            dlib_embedding, _ = self.get_face_embedding_dlib(img_rgb)
            
            if dlib_embedding is None:
                print("VERIFICATION FAILED: dlib could not extract embedding")
                return False, primary_user, primary_distance
            
            verification_success, verification_user, verification_distance = self._verify_with_embedding(dlib_embedding, model_type='dlib')
            
            if not verification_success:
                print(f"VERIFICATION FAILED: dlib did not find a match (distance: {verification_distance})")
                print(f"SECURITY: Models disagree - InsightFace found {primary_user} but dlib found no match")
                return False, primary_user, verification_distance
            
            # Both models must agree on the same user
            if primary_user != verification_user:
                print(f"VERIFICATION FAILED: Models disagree - InsightFace: {primary_user}, dlib: {verification_user}")
                print(f"SECURITY: Both models found matches but for different users - rejecting for security")
                return False, primary_user, max(primary_distance, verification_distance)
            
            print(f"VERIFICATION PASSED: Both models agree - user: {verification_user}")
            print(f"  InsightFace distance: {primary_distance:.3f}, dlib distance: {verification_distance:.3f}")
            print("=" * 50)
            # Return average distance from both models
            avg_distance = (primary_distance + verification_distance) / 2.0
            return True, verification_user, avg_distance
        else:
            # dlib not available or user doesn't have dlib embedding - use InsightFace only
            if not FACE_RECOGNITION_AVAILABLE:
                print("VERIFICATION SKIPPED: dlib not available, using InsightFace result only")
            else:
                print(f"VERIFICATION SKIPPED: User {primary_user} doesn't have dlib embedding (backward compatibility)")
            print("=" * 50)
            return primary_success, primary_user, primary_distance
    
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
