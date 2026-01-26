"""
Feedback Repository
Handles data access operations for Feedback entities
"""
import json
import os
from typing import Dict, List, Optional
from entities.feedback import Feedback


class FeedbackRepository:
    """Repository for Feedback entity data access"""
    
    def __init__(self, db_path: str = "feedback.json"):
        self.db_path = db_path
    
    def load_all(self) -> Dict[str, Feedback]:
        """Load all feedback from storage"""
        if not os.path.exists(self.db_path):
            return {}
        
        with open(self.db_path, "r") as f:
            raw_data = json.load(f)
        
        feedback_items = {}
        for feedback_id, data in raw_data.items():
            feedback_items[feedback_id] = Feedback.from_dict(data)
        
        return feedback_items
    
    def save_all(self, feedback_items: Dict[str, Feedback]) -> None:
        """Save all feedback to storage"""
        serializable = {}
        for feedback_id, feedback in feedback_items.items():
            serializable[feedback_id] = feedback.to_dict()
        
        with open(self.db_path, "w") as f:
            json.dump(serializable, f, indent=2)
    
    def find_by_id(self, feedback_id: str) -> Optional[Feedback]:
        """Find feedback by ID"""
        feedback_items = self.load_all()
        return feedback_items.get(feedback_id)
    
    def save(self, feedback: Feedback) -> None:
        """Save a single feedback"""
        feedback_items = self.load_all()
        feedback_items[feedback.feedback_id] = feedback
        self.save_all(feedback_items)
    
    def get_all(self) -> List[Feedback]:
        """Get all feedback as a list"""
        return list(self.load_all().values())
    
    def get_by_status(self, status: str) -> List[Feedback]:
        """Get all feedback with a specific status"""
        all_feedback = self.get_all()
        return [f for f in all_feedback if f.status == status]
