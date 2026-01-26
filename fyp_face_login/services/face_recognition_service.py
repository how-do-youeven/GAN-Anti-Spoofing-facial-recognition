"""
Face Recognition Service
Business logic for facial recognition operations
"""
import numpy as np
import face_recognition
from typing import Optional, Tuple
from entities.face_encoding import FaceEncoding
from repositories.face_repository import FaceRepository
from repositories.user_repository import UserRepository
from services.spoof_detection_service import SpoofDetectionService


class FaceRecognitionService:
    """Service for face recognition business logic"""
    
    # Thresholds for face matching
    # Lower values = stricter matching (more secure)
    # face_recognition default is 0.6, but we use much stricter values for security
    # 0.25-0.3 = extremely strict (maximum security)
    # 0.3-0.35 = very strict (recommended for security)
    # 0.4 = moderate strictness
    SAME_FACE_THRESHOLD = 0.35  # For duplicate detection during registration
    VERIFY_THRESHOLD = 0.3  # For login verification (extremely strict for maximum security)
    
    def __init__(self, face_repo: FaceRepository, user_repo: UserRepository, 
                 spoof_detection: Optional[SpoofDetectionService] = None):
        self.face_repo = face_repo
        self.user_repo = user_repo
        
        # Initialize spoof detection service
        # If not provided, create a new instance with default settings
        if spoof_detection is None:
            try:
                self.spoof_detection = SpoofDetectionService()
            except Exception as e:
                # If spoof detection fails to load, log warning but continue
                # This allows the system to work even if model is missing
                print(f"WARNING: Spoof detection model not available: {str(e)}")
                print("WARNING: Continuing without spoof detection. System may be vulnerable to spoofing attacks.")
                self.spoof_detection = None
        else:
            self.spoof_detection = spoof_detection
    
    @staticmethod
    def decode_base64_image(b64_str: str) -> np.ndarray:
        """Decode base64 image string to RGB numpy array"""
        import base64
        import cv2
        
        # Strip dataURL header: "data:image/jpeg;base64,..."
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        
        img_bytes = base64.b64decode(b64_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        return rgb
    
    @staticmethod
    def get_face_embedding(img_rgb: np.ndarray) -> Tuple[Optional[np.ndarray], int]:
        """
        Extract face embedding from image
        Returns: (embedding, face_count)
        """
        locations = face_recognition.face_locations(img_rgb, model='hog')
        
        if len(locations) == 0:
            return None, 0
        
        if len(locations) > 1:
            # Multiple faces detected - use the largest face (most centered)
            # Calculate face sizes and pick the largest
            face_sizes = [(bottom - top) * (right - left) for top, right, bottom, left in locations]
            largest_face_idx = face_sizes.index(max(face_sizes))
            locations = [locations[largest_face_idx]]
        
        encoding = face_recognition.face_encodings(img_rgb, locations)[0]
        return encoding, len(locations)
    
    def register_face(self, image_b64: str, user_id: str, 
                     check_duplicates: bool = True) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Register face for a user
        NOTE: Spoof detection is NOT performed during registration - only during login
        Returns: (success, error_message, distance_if_duplicate)
        """
        print("DEBUG: register_face called - NO spoof detection during registration")
        # Decode and extract face
        img_rgb = self.decode_base64_image(image_b64)
        embedding, face_count = self.get_face_embedding(img_rgb)
        
        if embedding is None:
            return False, f"Expected 1 face, found {face_count}", None
        
        # Check for duplicates if requested
        if check_duplicates:
            user_ids, known_embeddings = self.face_repo.get_all_encodings_array()
            
            if user_ids and len(user_ids) > 0:
                distances = face_recognition.face_distance(known_embeddings, embedding)
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
        face_encoding = FaceEncoding(user_id=user_id, encoding=embedding, image_b64=image_b64)
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
        
        # First detect face location
        locations = face_recognition.face_locations(img_rgb, model='hog')
        if len(locations) == 0:
            return False, None, None
        
        if len(locations) > 1:
            # Multiple faces detected - use the largest face (most centered)
            face_sizes = [(bottom - top) * (right - left) for top, right, bottom, left in locations]
            largest_face_idx = face_sizes.index(max(face_sizes))
            locations = [locations[largest_face_idx]]
        
        # Crop face for spoof detection (model expects cropped face, not full image)
        top, right, bottom, left = locations[0]
        # Add some padding around the face
        padding = 20
        face_crop = img_rgb[max(0, top-padding):min(img_rgb.shape[0], bottom+padding),
                           max(0, left-padding):min(img_rgb.shape[1], right+padding)]
        
        # Check for spoofing on the cropped face (before face recognition)
        if self.spoof_detection is not None:
            is_real, error_msg, real_prob = self.spoof_detection.check_if_real(face_crop)
            if not is_real:
                # Return False with special distance -1.0 to indicate spoofed face
                # This allows the controller to distinguish spoofing from other failures
                return False, None, -1.0
        
        # Now get face embedding for verification
        embedding = face_recognition.face_encodings(img_rgb, locations)[0]
        face_count = len(locations)
        
        if embedding is None:
            return False, None, None
        
        # Get all registered faces
        user_ids, known_embeddings = self.face_repo.get_all_encodings_array()
        
        if user_ids is None or len(user_ids) == 0:
            return False, None, None
        
        # Find best match
        distances = face_recognition.face_distance(known_embeddings, embedding)
        best_idx = int(np.argmin(distances))
        best_distance = float(distances[best_idx])
        best_user = user_ids[best_idx]
        
        # Very strict matching for security
        # Must be below threshold AND (if multiple faces) significantly better than second best
        if len(distances) > 1:
            # Get second best distance
            sorted_distances = np.sort(distances)
            second_best_distance = float(sorted_distances[1])
            
            # Check if best match is significantly better than second best
            # This prevents false matches when multiple faces are similar
            distance_difference = second_best_distance - best_distance
            
            # Best match must be below threshold AND at least 0.2 better than second best
            # Increased to 0.2 for maximum security - ensures unambiguous match
            if best_distance <= self.VERIFY_THRESHOLD:
                if distance_difference >= 0.2:
                    # Clear best match - significantly better than others
                    return True, best_user, best_distance
                else:
                    # Ambiguous match - distances too close, reject for security
                    # This prevents false positives when faces are somewhat similar
                    # Log for debugging (can be removed in production)
                    print(f"SECURITY: Ambiguous match rejected. Best: {best_distance:.3f}, Second: {second_best_distance:.3f}, Diff: {distance_difference:.3f}")
                    # Return best_user for failure tracking (even though match failed)
                    return False, best_user, best_distance
            else:
                # Best match is above threshold - not close enough
                # Return best_user for failure tracking (even though match failed)
                return False, best_user, best_distance
        else:
            # Only one registered face - EXTREMELY strict matching
            # When only one face is registered, we must be VERY confident it's the right person
            # Use an even stricter threshold (0.25) for single-face scenarios
            SINGLE_FACE_THRESHOLD = 0.25  # Stricter than multi-face threshold
            
            if best_distance <= SINGLE_FACE_THRESHOLD:
                # Distance is very low - confident match
                print(f"SECURITY: Single face match accepted - distance {best_distance:.3f} (threshold: {SINGLE_FACE_THRESHOLD})")
                return True, best_user, best_distance
            else:
                # Distance too high - reject (person not registered or wrong person)
                print(f"SECURITY: Single face match REJECTED - distance {best_distance:.3f} exceeds strict threshold {SINGLE_FACE_THRESHOLD}")
                if best_distance > 0.4:
                    print(f"SECURITY: Distance {best_distance:.3f} indicates this face is NOT registered")
                # Return best_user for failure tracking (even though match failed)
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

