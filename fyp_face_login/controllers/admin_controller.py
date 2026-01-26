"""
Admin Controller
Handles admin operations flow
"""
from typing import Dict, Any, List, Optional
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
        success, error, admin = self.admin_service.authenticate(email, password)
        
        if not success:
            return {
                "success": False,
                "error": error
            }
        
        return {
            "success": True,
            "message": "Admin login successful",
            "admin_type": admin.admin_type,
            "email": admin.email
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
    
    def get_pending_registrations(self) -> Dict[str, Any]:
        """
        Get all pending user registrations
        Returns response dictionary
        """
        pending_users = self.admin_service.get_pending_registrations()
        
        return {
            "success": True,
            "pending_users": pending_users,
            "total": len(pending_users)
        }
    
    def approve_registration(self, email: str) -> Dict[str, Any]:
        """
        Approve a user registration
        Returns response dictionary
        """
        success, error = self.admin_service.approve_registration(email)
        
        if not success:
            return {
                "success": False,
                "error": error
            }
        
        return {
            "success": True,
            "message": f"User registration approved for {email}"
        }
    
    def reject_registration(self, email: str) -> Dict[str, Any]:
        """
        Reject a user registration
        Returns response dictionary
        """
        success, error = self.admin_service.reject_registration(email)
        
        if not success:
            return {
                "success": False,
                "error": error
            }
        
        return {
            "success": True,
            "message": f"User registration rejected for {email}"
        }
    
    def get_all_feedback(self, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all user feedback (operations admin)
        Returns response dictionary
        """
        if status_filter:
            feedback_list = self.admin_service.get_feedback_by_status(status_filter)
        else:
            feedback_list = self.admin_service.get_all_feedback()
        
        return {
            "success": True,
            "feedback": feedback_list,
            "total": len(feedback_list)
        }
    
    def update_feedback_status(self, feedback_id: str, new_status: str) -> Dict[str, Any]:
        """
        Update feedback status
        Returns response dictionary
        """
        success, error = self.admin_service.update_feedback_status(feedback_id, new_status)
        
        if not success:
            return {
                "success": False,
                "error": error
            }
        
        return {
            "success": True,
            "message": f"Feedback status updated to {new_status}"
        }

