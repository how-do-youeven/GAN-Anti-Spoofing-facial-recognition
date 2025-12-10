"""
User Entity
Represents a user account in the system
"""
from datetime import datetime
from typing import Optional


class User:
    """User entity representing a student account"""
    
    def __init__(self, email: str, user_id: str, password_hash: str, 
                 name: str = "", face_registered: bool = False, 
                 created: Optional[str] = None):
        self.email = email
        self.user_id = user_id
        self.password_hash = password_hash
        self.name = name
        self.face_registered = face_registered
        self.created = created or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def to_dict(self) -> dict:
        """Convert user entity to dictionary"""
        return {
            "email": self.email,
            "user_id": self.user_id,
            "password_hash": self.password_hash,
            "name": self.name,
            "face_registered": self.face_registered,
            "created": self.created
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
            created=data.get("created")
        )
    
    def __repr__(self):
        return f"User(email={self.email}, user_id={self.user_id}, name={self.name})"

