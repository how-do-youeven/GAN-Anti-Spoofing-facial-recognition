"""
Admin Service
Business logic for admin operations
"""
from typing import List, Dict, Optional, Tuple
from entities.user import User
from repositories.user_repository import UserRepository
from repositories.face_repository import FaceRepository
from repositories.admin_repository import AdminRepository
from repositories.feedback_repository import FeedbackRepository
from services.user_service import UserService


class AdminService:
    """Service for admin-related business logic"""
    
    def __init__(self, admin_repo: AdminRepository, user_repo: UserRepository, 
                 face_repo: FaceRepository, user_service: UserService,
                 feedback_repo: Optional[FeedbackRepository] = None):
        self.admin_repo = admin_repo
        self.user_repo = user_repo
        self.face_repo = face_repo
        self.user_service = user_service
        self.feedback_repo = feedback_repo
    
    def authenticate(self, email: str, password: str) -> Tuple[bool, Optional[str], Optional['Admin']]:
        """
        Authenticate admin login
        Returns: (success, error_message, admin)
        """
        from entities.admin import Admin
        
        email_lower = email.strip().lower()
        
        if not email_lower or not password:
            return False, "Email and password required", None
        
        admin = self.admin_repo.find_by_email(email_lower)
        if not admin:
            return False, "Invalid credentials", None
        
        if not UserService.verify_password(password, admin.password_hash):
            return False, "Invalid credentials", None
        
        return True, None, admin
    
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
                "created": user.created,
                "registration_status": user.registration_status
            })
        
        return users_list
    
    def get_pending_registrations(self) -> List[Dict]:
        """
        Get all pending user registrations
        Returns list of pending user dictionaries
        """
        users = self.user_repo.load_all()
        pending_users = []
        
        for email, user in users.items():
            if user.is_pending():
                pending_users.append({
                    "email": user.email,
                    "user_id": user.user_id,
                    "name": user.name,
                    "created": user.created,
                    "registration_status": user.registration_status
                })
        
        return pending_users
    
    def approve_registration(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Approve a user registration
        Returns: (success, error_message)
        """
        email_lower = email.strip().lower()
        user = self.user_repo.find_by_email(email_lower)
        
        if not user:
            return False, "User not found"
        
        if user.is_approved():
            return False, "User registration is already approved"
        
        user.registration_status = User.STATUS_APPROVED
        self.user_repo.save(user)
        
        return True, None
    
    def reject_registration(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Reject a user registration
        Returns: (success, error_message)
        """
        email_lower = email.strip().lower()
        user = self.user_repo.find_by_email(email_lower)
        
        if not user:
            return False, "User not found"
        
        if user.is_rejected():
            return False, "User registration is already rejected"
        
        user.registration_status = User.STATUS_REJECTED
        self.user_repo.save(user)
        
        return True, None
    
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
    
    def get_all_feedback(self) -> List[Dict]:
        """
        Get all user feedback
        Returns list of feedback dictionaries
        """
        if not self.feedback_repo:
            return []
        
        feedback_list = self.feedback_repo.get_all()
        return [f.to_dict() for f in feedback_list]
    
    def get_feedback_by_status(self, status: str) -> List[Dict]:
        """
        Get feedback filtered by status
        Returns list of feedback dictionaries
        """
        if not self.feedback_repo:
            return []
        
        feedback_list = self.feedback_repo.get_by_status(status)
        return [f.to_dict() for f in feedback_list]
    
    def update_feedback_status(self, feedback_id: str, new_status: str) -> Tuple[bool, Optional[str]]:
        """
        Update feedback status
        Returns: (success, error_message)
        """
        if not self.feedback_repo:
            return False, "Feedback repository not available"
        
        feedback = self.feedback_repo.find_by_id(feedback_id)
        if not feedback:
            return False, "Feedback not found"
        
        # Validate status
        valid_statuses = ["pending", "in_progress", "completed", "no_action_taken"]
        if new_status not in valid_statuses:
            return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        
        feedback.status = new_status
        self.feedback_repo.save(feedback)
        
        return True, None

