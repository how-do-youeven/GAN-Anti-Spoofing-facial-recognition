"""
User Repository
Handles data access operations for User entities
"""
import json
import os
from typing import Dict, Optional
from entities.user import User


class UserRepository:
    """Repository for User entity data access"""
    
    def __init__(self, db_path: str = "user_accounts.json"):
        self.db_path = db_path
    
    def load_all(self) -> Dict[str, User]:
        """Load all users from storage"""
        if not os.path.exists(self.db_path):
            return {}
        
        with open(self.db_path, "r") as f:
            raw_data = json.load(f)
        
        users = {}
        for email, data in raw_data.items():
            users[email] = User.from_dict(email, data)
        
        return users
    
    def save_all(self, users: Dict[str, User]) -> None:
        """Save all users to storage"""
        serializable = {}
        for email, user in users.items():
            serializable[email] = user.to_dict()
        
        with open(self.db_path, "w") as f:
            json.dump(serializable, f, indent=2)
    
    def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email"""
        users = self.load_all()
        return users.get(email.lower())
    
    def save(self, user: User) -> None:
        """Save a single user"""
        users = self.load_all()
        users[user.email.lower()] = user
        self.save_all(users)
    
    def delete(self, email: str) -> bool:
        """Delete a user by email"""
        users = self.load_all()
        email_lower = email.lower()
        
        if email_lower not in users:
            return False
        
        del users[email_lower]
        self.save_all(users)
        return True
    
    def exists(self, email: str) -> bool:
        """Check if user exists"""
        return self.find_by_email(email) is not None

