"""
Face Encoding Entity
Represents facial recognition data for a user
"""
import numpy as np
from typing import Optional


class FaceEncoding:
    """Face encoding entity representing facial recognition data"""
    
    def __init__(self, user_id: str, encoding: np.ndarray, image_b64: Optional[str] = None):
        self.user_id = user_id
        self.encoding = encoding  # numpy array of face encoding
        self.image_b64 = image_b64  # base64 encoded image used for registration
    
    def to_dict(self) -> dict:
        """Convert face encoding to dictionary (for JSON storage)"""
        return {
            "user_id": self.user_id,
            "encoding": self.encoding.tolist(),
            "image_b64": self.image_b64
        }
    
    @classmethod
    def from_dict(cls, user_id: str, data: dict) -> 'FaceEncoding':
        """Create FaceEncoding entity from dictionary"""
        if isinstance(data, list):
            # Old format - just encoding list
            encoding = np.array(data, dtype="float32")
            return cls(user_id=user_id, encoding=encoding, image_b64=None)
        else:
            # New format - dict with encoding and image
            encoding = np.array(data.get("encoding", []), dtype="float32")
            return cls(user_id=user_id, encoding=encoding, image_b64=data.get("image_b64"))
    
    def __repr__(self):
        return f"FaceEncoding(user_id={self.user_id}, encoding_shape={self.encoding.shape})"

