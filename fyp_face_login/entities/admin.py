"""
Admin Entity
Represents admin account configuration
"""
from typing import Optional


class Admin:
    """Admin entity representing admin account"""
    
    def __init__(self, email: str, password_hash: str):
        self.email = email
        self.password_hash = password_hash
    
    def to_dict(self) -> dict:
        """Convert admin entity to dictionary"""
        return {
            "admin_email": self.email,
            "admin_password_hash": self.password_hash
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Admin':
        """Create Admin entity from dictionary"""
        return cls(
            email=data.get("admin_email", ""),
            password_hash=data.get("admin_password_hash", "")
        )
    
    def __repr__(self):
        return f"Admin(email={self.email})"

