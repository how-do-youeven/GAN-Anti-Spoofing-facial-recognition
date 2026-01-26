"""
Auth Controller
Handles authentication flow
"""
from typing import Dict, Any
from services.user_service import UserService
from services.face_recognition_service import FaceRecognitionService
from repositories.user_repository import UserRepository


class AuthController:
    """Controller for authentication operations"""
    
    def __init__(self, user_service: UserService, face_service: FaceRecognitionService):
        self.user_service = user_service
        self.face_service = face_service
    
    def login_with_credentials(self, email: str, password: str) -> Dict[str, Any]:
        """
        Handle login with email/password
        Returns response dictionary
        """
        success, user, error = self.user_service.login(email, password)
        
        if not success:
            return {
                "success": False,
                "error": error
            }
        
        return {
            "success": True,
            "user_id": user.user_id,
            "email": user.email,
            "name": user.name,
            "face_registered": user.face_registered
        }
    
    def login_with_face(self, image_b64: str) -> Dict[str, Any]:
        """
        Handle login with facial recognition
        Returns response dictionary
        """
        # Attempt face verification (returns user_id even on failure for tracking)
        success, user_id, distance = self.face_service.verify_face(image_b64)
        
        # Get all users to check face login status
        users = self.user_service.user_repo.load_all()
        user = None
        
        # Find the user if we got a user_id (even from failed attempt)
        if user_id:
            for email, u in users.items():
                if u.user_id == user_id:
                    user = u
                    break
        
        # If face login is disabled for this user, reject immediately
        if user and user.face_login_disabled:
            return {
                "success": False,
                "error": "Facial recognition login has been disabled due to multiple failed attempts. Please use password login and reset your facial recognition.",
                "face_login_disabled": True,
                "requires_password_login": True
            }
        
        if not success:
            error_msg = "Face not recognized"
            
            # Check if spoofed face was detected (distance = -1.0)
            if distance == -1.0:
                error_msg = "Spoofed face detected. Please use a real face for authentication."
            elif distance is not None and distance > 0:
                # Provide more helpful error message with distance info
                if distance > 0.5:
                    error_msg = "Face not recognized. Please ensure you are the registered user and try again."
                elif distance > 0.4:
                    error_msg = f"Face not recognized. Match quality too low (distance: {distance:.3f}). Please try again with better lighting."
                else:
                    error_msg = f"Face not recognized. Security check failed (distance: {distance:.3f}). Please ensure you are the registered user."
            
            # Track failure if we identified a user (even if match failed, we track the closest match)
            if user_id and user:
                user.face_login_failures += 1
                
                # Disable face login after 5 failures
                if user.face_login_failures >= 5:
                    user.face_login_disabled = True
                    error_msg = "Facial recognition login has been disabled due to multiple failed attempts. Please use password login and reset your facial recognition."
                
                self.user_service.user_repo.save(user)
            
            return {
                "success": False,
                "error": error_msg,
                "distance": distance if distance != -1.0 else None,  # Don't expose -1.0 to client
                "threshold": 0.3,  # Include threshold in response for debugging
                "spoof_detected": distance == -1.0,  # Flag to indicate spoofing
                "face_login_disabled": user.face_login_disabled if user else False,
                "failures_remaining": max(0, 5 - (user.face_login_failures if user else 0))
            }
        
        # Success - reset failure count and ensure face login is enabled
        if user:
            user.face_login_failures = 0
            user.face_login_disabled = False
            self.user_service.user_repo.save(user)
        
        if not user:
            return {
                "success": False,
                "error": "User account not found"
            }
        
        return {
            "success": True,
            "user_id": user.user_id,
            "email": user.email,
            "name": user.name,
            "distance": distance
        }

