"""
Admin Controller
Handles admin operations flow
"""
from typing import Dict, Any, List
from services.admin_service import AdminService


class AdminController:
    """Controller for admin operations"""
    
    def __init__(self, admin_service: AdminService):
        self.admin_service = admin_service
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Handle admin login
        Returns response dictionary
        """
        success, error = self.admin_service.authenticate(email, password)
        
        if not success:
            return {
                "success": False,
                "error": error
            }
        
        return {
            "success": True,
            "message": "Admin login successful"
        }
    
    def get_all_users(self) -> Dict[str, Any]:
        """
        Get all users for admin dashboard
        Returns response dictionary
        """
        users = self.admin_service.get_all_users()
        
        return {
            "success": True,
            "users": users,
            "total": len(users)
        }
    
    def delete_user(self, email: str) -> Dict[str, Any]:
        """
        Delete a user account
        Returns response dictionary
        """
        success, error = self.admin_service.delete_user(email)
        
        if not success:
            return {
                "success": False,
                "error": error
            }
        
        return {
            "success": True,
            "message": f"User {email} deleted successfully"
        }
    
    def reset_user_password(self, email: str, new_password: str) -> Dict[str, Any]:
        """
        Reset a user's password
        Returns response dictionary
        """
        success, error = self.admin_service.reset_user_password(email, new_password)
        
        if not success:
            return {
                "success": False,
                "error": error
            }
        
        return {
            "success": True,
            "message": f"Password reset successfully for {email}"
        }

