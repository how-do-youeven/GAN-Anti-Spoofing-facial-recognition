"""
User Service
Business logic for user operations
"""
import hashlib
import uuid
from typing import Optional, Tuple
from entities.user import User
from repositories.user_repository import UserRepository
from repositories.face_repository import FaceRepository


class UserService:
    """Service for user-related business logic"""
    
    def __init__(self, user_repo: UserRepository, face_repo: FaceRepository):
        self.user_repo = user_repo
        self.face_repo = face_repo
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password (use bcrypt in production)"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return UserService.hash_password(password) == hashed
    
    def generate_user_id(self) -> str:
        """Generate a unique user ID"""
        users = self.user_repo.load_all()
        existing_ids = {user.user_id for user in users.values()}
        
        while True:
            new_id = f"u_{uuid.uuid4().hex[:8]}"
            if new_id not in existing_ids:
                return new_id
    
    def register_account(self, email: str, password: str, name: str) -> Tuple[bool, Optional[User], Optional[str]]:
        """
        Register a new user account
        Returns: (success, user, error_message)
        """
        email_lower = email.strip().lower()
        
        # Validation
        if not email_lower or not password:
            return False, None, "Email and password required"
        
        if len(password) < 6:
            return False, None, "Password must be at least 6 characters"
        
        # Check if email already exists
        if self.user_repo.exists(email_lower):
            return False, None, "Email already registered"
        
        # Create new user with pending status (requires admin approval)
        user_id = self.generate_user_id()
        password_hash = self.hash_password(password)
        
        user = User(
            email=email_lower,
            user_id=user_id,
            password_hash=password_hash,
            name=name.strip(),
            face_registered=False,
            registration_status=User.STATUS_PENDING
        )
        
        self.user_repo.save(user)
        return True, user, None
    
    def login(self, email: str, password: str) -> Tuple[bool, Optional[User], Optional[str]]:
        """
        Authenticate user login
        Returns: (success, user, error_message)
        """
        email_lower = email.strip().lower()
        
        if not email_lower or not password:
            return False, None, "Email and password required"
        
        user = self.user_repo.find_by_email(email_lower)
        
        if not user:
            return False, None, "Invalid email or password"
        
        if not self.verify_password(password, user.password_hash):
            return False, None, "Invalid email or password"
        
        # Check registration approval status
        if user.is_pending():
            return False, None, "Your registration is pending approval. Please wait for admin approval before logging in."
        
        if user.is_rejected():
            return False, None, "Your registration has been rejected. Please contact support."
        
        # Check face registration status
        user.face_registered = self.face_repo.exists(user.user_id)
        
        return True, user, None
    
    def reset_password(self, email: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Reset user password
        Returns: (success, error_message)
        """
        email_lower = email.strip().lower()
        
        if not new_password:
            return False, "New password required"
        
        if len(new_password) < 6:
            return False, "Password must be at least 6 characters"
        
        user = self.user_repo.find_by_email(email_lower)
        if not user:
            return False, "User not found"
        
        user.password_hash = self.hash_password(new_password)
        self.user_repo.save(user)
        
        return True, None
    
    def get_user_info(self, email: str) -> Optional[User]:
        """Get user information"""
        user = self.user_repo.find_by_email(email.strip().lower())
        if user:
            user.face_registered = self.face_repo.exists(user.user_id)
        return user

