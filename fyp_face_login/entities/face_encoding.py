"""
Face Encoding Entity
Represents facial recognition data for a user
"""
import numpy as np
from typing import Optional


class FaceEncoding:
    """Face encoding entity representing facial recognition data"""
    
    def __init__(self, user_id: str, encoding: np.ndarray, image_b64: Optional[str] = None, 
                 encoding_dlib: Optional[np.ndarray] = None):
        self.user_id = user_id
        self.encoding = encoding  # Primary encoding (InsightFace 512D or dlib 128D)
        self.image_b64 = image_b64  # base64 encoded image used for registration
        self.encoding_dlib = encoding_dlib  # Optional dlib encoding (128D) for dual-model verification
    
    def to_dict(self) -> dict:
        """Convert face encoding to dictionary (for JSON storage)"""
        result = {
            "user_id": self.user_id,
            "encoding": self.encoding.tolist(),
            "image_b64": self.image_b64
        }
        if self.encoding_dlib is not None:
            result["encoding_dlib"] = self.encoding_dlib.tolist()
        return result
    
    @classmethod
    def from_dict(cls, user_id: str, data: dict) -> 'FaceEncoding':
        """Create FaceEncoding entity from dictionary"""
        if isinstance(data, list):
            # Old format - just encoding list
            encoding = np.array(data, dtype="float32")
            return cls(user_id=user_id, encoding=encoding, image_b64=None, encoding_dlib=None)
        else:
            # New format - dict with encoding and image
            encoding = np.array(data.get("encoding", []), dtype="float32")
            encoding_dlib = None
            if "encoding_dlib" in data:
                encoding_dlib = np.array(data.get("encoding_dlib", []), dtype="float32")
            return cls(user_id=user_id, encoding=encoding, image_b64=data.get("image_b64"), encoding_dlib=encoding_dlib)
    
    def __repr__(self):
        return f"FaceEncoding(user_id={self.user_id}, encoding_shape={self.encoding.shape})"

