"""
Admin Repository
Handles data access operations for Admin entities
"""
import json
import os
from typing import Optional, Dict
from entities.admin import Admin


class AdminRepository:
    """Repository for Admin entity data access"""
    
    def __init__(self, db_path: str = "admin_config.json", 
                 default_email: str = "admin@school.edu",
                 default_password_hash: str = None):
        self.db_path = db_path
        self.default_email = default_email
        self.default_password_hash = default_password_hash
    
    def load_all(self) -> Dict[str, Admin]:
        """Load all admins from storage"""
        if not os.path.exists(self.db_path):
            return {}
        
        with open(self.db_path, "r") as f:
            raw_data = json.load(f)
        
        # Handle both old format (single admin) and new format (multiple admins)
        admins = {}
        if isinstance(raw_data, dict):
            if "admin_email" in raw_data:
                # Old format - single admin
                admin = Admin.from_dict(raw_data)
                admins[admin.email] = admin
            else:
                # New format - multiple admins
                for email, data in raw_data.items():
                    admins[email] = Admin.from_dict(data)
        
        return admins
    
    def save_all(self, admins: Dict[str, Admin]) -> None:
        """Save all admins to storage"""
        serializable = {}
        for email, admin in admins.items():
            serializable[email] = admin.to_dict()
        
        with open(self.db_path, "w") as f:
            json.dump(serializable, f, indent=2)
    
    def find_by_email(self, email: str) -> Optional[Admin]:
        """Find admin by email"""
        admins = self.load_all()
        return admins.get(email.lower())
    
    def save(self, admin: Admin) -> None:
        """Save a single admin"""
        admins = self.load_all()
        admins[admin.email.lower()] = admin
        self.save_all(admins)
    
    def load(self) -> Optional[Admin]:
        """Load first admin (for backward compatibility)"""
        admins = self.load_all()
        if admins:
            return list(admins.values())[0]
        return None

