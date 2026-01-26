"""
Registration Controller
Handles user registration and face registration flow
"""
from typing import Dict, Any
from services.user_service import UserService
from services.face_recognition_service import FaceRecognitionService


class RegistrationController:
    """Controller for registration operations"""
    
    def __init__(self, user_service: UserService, face_service: FaceRecognitionService):
        self.user_service = user_service
        self.face_service = face_service
    
    def register_account(self, email: str, password: str, name: str) -> Dict[str, Any]:
        """
        Handle account registration
        Returns response dictionary
        """
        success, user, error = self.user_service.register_account(email, password, name)
        
        if not success:
            return {
                "success": False,
                "error": error
            }
        
        return {
            "success": True,
            "user_id": user.user_id,
            "email": user.email,
            "message": "Account created successfully. Your registration is pending admin approval. You will be able to login and register your face once approved.",
            "registration_status": user.registration_status
        }
    
    def register_face(self, image_b64: str, email: str, password: str) -> Dict[str, Any]:
        """
        Handle face registration for an account
        Returns response dictionary
        """
        # Verify account credentials first
        email_lower = email.strip().lower()
        user = self.user_service.user_repo.find_by_email(email_lower)
        
        if not user:
            return {
                "success": False,
                "error": "User not found"
            }
        
        # Check if user is approved
        if not user.is_approved():
            if user.is_pending():
                return {
                    "success": False,
                    "error": "Your registration is pending approval. Please wait for admin approval before registering your face."
                }
            elif user.is_rejected():
                return {
                    "success": False,
                    "error": "Your registration has been rejected. Please contact support."
                }
        
        # Verify password
        if not self.user_service.verify_password(password, user.password_hash):
            return {
                "success": False,
                "error": "Invalid password"
            }
        
        # Register face
        success, error_msg, distance = self.face_service.register_face(
            image_b64, user.user_id, check_duplicates=True
        )
        
        if not success:
            return {
                "success": False,
                "error": error_msg
            }
        
        return {
            "success": True,
            "user_id": user.user_id,
            "is_new": error_msg != "Face already registered to this account",
            "message": error_msg or "Face registered successfully"
        }
    
    def reset_face(self, image_b64: str, email: str, password: str) -> Dict[str, Any]:
        """
        Handle face reset for an account
        Returns response dictionary
        """
        # Verify account credentials first
        success, user, error = self.user_service.login(email, password)
        
        if not success:
            return {
                "success": False,
                "error": error
            }
        
        # Reset face
        success, error_msg = self.face_service.reset_face(image_b64, user.user_id)
        
        if not success:
            return {
                "success": False,
                "error": error_msg
            }
        
        # Reset failure count and re-enable face login
        user.face_login_failures = 0
        user.face_login_disabled = False
        self.user_service.user_repo.save(user)
        
        return {
            "success": True,
            "message": "Facial recognition reset successfully. Face login has been re-enabled."
        }

