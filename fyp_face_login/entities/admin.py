"""
Admin Entity
Represents admin account configuration
"""
from typing import Optional


class Admin:
    """Admin entity representing admin account"""
    
    # Admin types
    SYSTEM_ADMIN = "system_admin"
    OPERATIONS_ADMIN = "operations_admin"
    
    def __init__(self, email: str, password_hash: str, admin_type: str = SYSTEM_ADMIN):
        self.email = email
        self.password_hash = password_hash
        self.admin_type = admin_type  # system_admin or operations_admin
    
    def to_dict(self) -> dict:
        """Convert admin entity to dictionary"""
        return {
            "admin_email": self.email,
            "admin_password_hash": self.password_hash,
            "admin_type": self.admin_type
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Admin':
        """Create Admin entity from dictionary"""
        return cls(
            email=data.get("admin_email", ""),
            password_hash=data.get("admin_password_hash", ""),
            admin_type=data.get("admin_type", Admin.SYSTEM_ADMIN)
        )
    
    def is_system_admin(self) -> bool:
        """Check if this is a system admin"""
        return self.admin_type == Admin.SYSTEM_ADMIN
    
    def is_operations_admin(self) -> bool:
        """Check if this is an operations admin"""
        return self.admin_type == Admin.OPERATIONS_ADMIN
    
    def __repr__(self):
        return f"Admin(email={self.email}, type={self.admin_type})"

