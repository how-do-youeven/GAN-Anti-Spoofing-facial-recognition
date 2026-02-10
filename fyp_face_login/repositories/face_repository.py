"""
Face Repository
Persistence for InsightFace ArcFace face encodings (one per user).
Storage: JSON file; each record is one FaceEncoding (512D embedding + optional image).
"""
import json
import os
import numpy as np
from typing import Dict, Optional
from entities.face_encoding import FaceEncoding


# Storage schema (known_faces.json):
# {
#   "<user_id>": {
#     "user_id": "<user_id>",
#     "encoding": [float, ...],   # 512D InsightFace ArcFace vector
#     "embedding_type": "insightface_arcface",
#     "embedding_dim": 512,
#     "image_b64": "<optional base64 string>",
#     "encoding_dlib": [float, ...]  # optional, legacy 128D
#   }
# }


class FaceRepository:
    """Repository for InsightFace ArcFace face encodings (load/save by user_id)."""
    
    def __init__(self, db_path: str = "known_faces.json"):
        self.db_path = db_path
    
    def load_all(self) -> Dict[str, FaceEncoding]:
        """Load all face encodings from storage"""
        if not os.path.exists(self.db_path):
            return {}
        
        with open(self.db_path, "r") as f:
            raw_data = json.load(f)
        
        encodings = {}
        for user_id, data in raw_data.items():
            # Handle both old format (list) and new format (dict)
            encodings[user_id] = FaceEncoding.from_dict(user_id, data)
        
        return encodings
    
    def save_all(self, encodings: Dict[str, FaceEncoding]) -> None:
        """Save all face encodings to storage"""
        serializable = {}
        for user_id, encoding in encodings.items():
            serializable[user_id] = encoding.to_dict()
        
        with open(self.db_path, "w") as f:
            json.dump(serializable, f)
    
    def find_by_user_id(self, user_id: str) -> Optional[FaceEncoding]:
        """Find face encoding by user ID"""
        encodings = self.load_all()
        return encodings.get(user_id)
    
    def save(self, face_encoding: FaceEncoding) -> None:
        """Save a single face encoding"""
        encodings = self.load_all()
        encodings[face_encoding.user_id] = face_encoding
        self.save_all(encodings)
    
    def delete(self, user_id: str) -> bool:
        """Delete face encoding by user ID"""
        encodings = self.load_all()
        
        if user_id not in encodings:
            return False
        
        del encodings[user_id]
        self.save_all(encodings)
        return True
    
    def exists(self, user_id: str) -> bool:
        """Check if face encoding exists for user"""
        return self.find_by_user_id(user_id) is not None
    
    def get_all_encodings_array(self) -> tuple:
        """Get all encodings as numpy arrays for face recognition"""
        encodings = self.load_all()
        if not encodings:
            return None, None
        
        user_ids = list(encodings.keys())
        # Stack encodings - handles both 128D (dlib) and 512D (InsightFace) embeddings
        encoding_arrays = np.stack([enc.encoding for enc in encodings.values()], axis=0)
        
        return user_ids, encoding_arrays

