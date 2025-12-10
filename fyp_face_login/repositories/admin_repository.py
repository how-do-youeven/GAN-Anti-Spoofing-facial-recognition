"""
Admin Repository
Handles data access operations for Admin entities
"""
import json
import os
from typing import Optional
from entities.admin import Admin


class AdminRepository:
    """Repository for Admin entity data access"""
    
    def __init__(self, db_path: str = "admin_config.json", 
                 default_email: str = "admin@school.edu",
                 default_password_hash: str = None):
        self.db_path = db_path
        self.default_email = default_email
        self.default_password_hash = default_password_hash
    
    def load(self) -> Optional[Admin]:
        """Load admin configuration"""
        if not os.path.exists(self.db_path):
            return None
        
        with open(self.db_path, "r") as f:
            data = json.load(f)
        
        return Admin.from_dict(data)
    
    def save(self, admin: Admin) -> None:
        """Save admin configuration"""
        with open(self.db_path, "w") as f:
            json.dump(admin.to_dict(), f, indent=2)

