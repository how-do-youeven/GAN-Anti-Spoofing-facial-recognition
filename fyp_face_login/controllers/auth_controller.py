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
        success, user_id, distance = self.face_service.verify_face(image_b64)
        
        if not success:
            error_msg = "Face not recognized"
            if distance is not None:
                # Provide more helpful error message with distance info
                if distance > 0.5:
                    error_msg = "Face not recognized. Please ensure you are the registered user and try again."
                elif distance > 0.4:
                    error_msg = f"Face not recognized. Match quality too low (distance: {distance:.3f}). Please try again with better lighting."
                else:
                    error_msg = f"Face not recognized. Security check failed (distance: {distance:.3f}). Please ensure you are the registered user."
            
            return {
                "success": False,
                "error": error_msg,
                "distance": distance,
                "threshold": 0.3  # Include threshold in response for debugging
            }
        
        # Get user info
        users = self.user_service.user_repo.load_all()
        user = None
        for email, u in users.items():
            if u.user_id == user_id:
                user = u
                break
        
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

