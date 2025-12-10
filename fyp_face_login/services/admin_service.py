"""
Admin Service
Business logic for admin operations
"""
from typing import List, Dict, Optional, Tuple
from entities.user import User
from repositories.user_repository import UserRepository
from repositories.face_repository import FaceRepository
from repositories.admin_repository import AdminRepository
from services.user_service import UserService


class AdminService:
    """Service for admin-related business logic"""
    
    def __init__(self, admin_repo: AdminRepository, user_repo: UserRepository, 
                 face_repo: FaceRepository, user_service: UserService):
        self.admin_repo = admin_repo
        self.user_repo = user_repo
        self.face_repo = face_repo
        self.user_service = user_service
    
    def authenticate(self, email: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        Authenticate admin login
        Returns: (success, error_message)
        """
        email_lower = email.strip().lower()
        
        if not email_lower or not password:
            return False, "Email and password required"
        
        admin = self.admin_repo.load()
        if not admin:
            return False, "Admin configuration not found"
        
        if email_lower != admin.email:
            return False, "Invalid credentials"
        
        if not UserService.verify_password(password, admin.password_hash):
            return False, "Invalid credentials"
        
        return True, None
    
    def get_all_users(self) -> List[Dict]:
        """
        Get all users with their information
        Returns list of user dictionaries
        """
        users = self.user_repo.load_all()
        users_list = []
        
        for email, user in users.items():
            face_registered = self.face_repo.exists(user.user_id)
            
            users_list.append({
                "email": user.email,
                "user_id": user.user_id,
                "name": user.name,
                "face_registered": face_registered,
                "created": user.created
            })
        
        return users_list
    
    def delete_user(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a user account
        Returns: (success, error_message)
        """
        email_lower = email.strip().lower()
        user = self.user_repo.find_by_email(email_lower)
        
        if not user:
            return False, "User not found"
        
        # Delete face data if exists
        self.face_repo.delete(user.user_id)
        
        # Delete user account
        success = self.user_repo.delete(email_lower)
        
        if not success:
            return False, "Failed to delete user"
        
        return True, None
    
    def reset_user_password(self, email: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Reset a user's password
        Returns: (success, error_message)
        """
        return self.user_service.reset_password(email, new_password)

