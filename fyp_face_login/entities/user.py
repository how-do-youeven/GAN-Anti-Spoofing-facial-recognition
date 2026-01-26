"""
User Entity
Represents a user account in the system
"""
from datetime import datetime
from typing import Optional


class User:
    """User entity representing a student account"""
    
    # Registration status constants
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    
    def __init__(self, email: str, user_id: str, password_hash: str, 
                 name: str = "", face_registered: bool = False, 
                 created: Optional[str] = None, face_login_failures: int = 0,
                 face_login_disabled: bool = False, registration_status: str = STATUS_PENDING):
        self.email = email
        self.user_id = user_id
        self.password_hash = password_hash
        self.name = name
        self.face_registered = face_registered
        self.created = created or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.face_login_failures = face_login_failures
        self.face_login_disabled = face_login_disabled
        self.registration_status = registration_status
    
    def to_dict(self) -> dict:
        """Convert user entity to dictionary"""
        return {
            "email": self.email,
            "user_id": self.user_id,
            "password_hash": self.password_hash,
            "name": self.name,
            "face_registered": self.face_registered,
            "created": self.created,
            "face_login_failures": self.face_login_failures,
            "face_login_disabled": self.face_login_disabled,
            "registration_status": self.registration_status
        }
    
    @classmethod
    def from_dict(cls, email: str, data: dict) -> 'User':
        """Create User entity from dictionary"""
        return cls(
            email=email,
            user_id=data.get("user_id", ""),
            password_hash=data.get("password_hash", ""),
            name=data.get("name", ""),
            face_registered=data.get("face_registered", False),
            created=data.get("created"),
            face_login_failures=data.get("face_login_failures", 0),
            face_login_disabled=data.get("face_login_disabled", False),
            registration_status=data.get("registration_status", User.STATUS_PENDING)
        )
    
    def is_approved(self) -> bool:
        """Check if user registration is approved"""
        return self.registration_status == User.STATUS_APPROVED
    
    def is_pending(self) -> bool:
        """Check if user registration is pending"""
        return self.registration_status == User.STATUS_PENDING
    
    def is_rejected(self) -> bool:
        """Check if user registration is rejected"""
        return self.registration_status == User.STATUS_REJECTED
    
    def __repr__(self):
        return f"User(email={self.email}, user_id={self.user_id}, name={self.name})"

