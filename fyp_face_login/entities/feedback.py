"""
Feedback Entity
Represents user feedback submitted to operations admin
"""
from datetime import datetime
from typing import Optional


class Feedback:
    """Feedback entity representing user feedback"""
    
    # Status constants
    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_NO_ACTION = "no_action_taken"
    
    def __init__(self, feedback_id: str, user_email: str, message: str, 
                 created: Optional[str] = None, status: str = STATUS_PENDING):
        self.feedback_id = feedback_id
        self.user_email = user_email
        self.message = message
        self.created = created or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status = status  # pending, in_progress, completed, no_action_taken
    
    def to_dict(self) -> dict:
        """Convert feedback entity to dictionary"""
        return {
            "feedback_id": self.feedback_id,
            "user_email": self.user_email,
            "message": self.message,
            "created": self.created,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Feedback':
        """Create Feedback entity from dictionary"""
        return cls(
            feedback_id=data.get("feedback_id", ""),
            user_email=data.get("user_email", ""),
            message=data.get("message", ""),
            created=data.get("created"),
            status=data.get("status", "pending")
        )
    
    def __repr__(self):
        return f"Feedback(id={self.feedback_id}, email={self.user_email}, status={self.status})"
