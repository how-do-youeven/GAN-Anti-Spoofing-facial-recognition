"""
Face Encoding Entity
Represents facial recognition data for a user
"""
import numpy as np
from typing import Optional


class FaceEncoding:
    """Face encoding entity representing facial recognition data"""
    
    def __init__(self, user_id: str, encoding: np.ndarray):
        self.user_id = user_id
        self.encoding = encoding  # numpy array of face encoding
    
    def to_dict(self) -> dict:
        """Convert face encoding to dictionary (for JSON storage)"""
        return {
            "user_id": self.user_id,
            "encoding": self.encoding.tolist()
        }
    
    @classmethod
    def from_dict(cls, user_id: str, encoding_list: list) -> 'FaceEncoding':
        """Create FaceEncoding entity from dictionary"""
        encoding = np.array(encoding_list, dtype="float32")
        return cls(user_id=user_id, encoding=encoding)
    
    def __repr__(self):
        return f"FaceEncoding(user_id={self.user_id}, encoding_shape={self.encoding.shape})"

