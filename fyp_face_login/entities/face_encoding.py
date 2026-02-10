"""
Face Encoding Entity
Stores InsightFace ArcFace face recognition data for one user.
All embeddings are 512-dimensional ArcFace vectors (cosine similarity).
"""
import numpy as np
from typing import Optional

# Storage format constants
EMBEDDING_TYPE = "insightface_arcface"
EMBEDDING_DIM = 512


class FaceEncoding:
    """
    Face encoding for one user: InsightFace ArcFace 512D embedding only.
    Used for registration and verification; comparison uses cosine distance.
    """

    def __init__(
        self,
        user_id: str,
        encoding: np.ndarray,
        image_b64: Optional[str] = None,
        encoding_dlib: Optional[np.ndarray] = None,
    ):
        self.user_id = user_id
        # Primary embedding: InsightFace ArcFace 512D (or legacy dlib 128D from old data)
        self.encoding = np.asarray(encoding, dtype="float32")
        self.image_b64 = image_b64
        self.encoding_dlib = np.asarray(encoding_dlib, dtype="float32") if encoding_dlib is not None else None

    @property
    def is_insightface(self) -> bool:
        """True if primary encoding is InsightFace 512D."""
        return len(self.encoding) == EMBEDDING_DIM

    def to_dict(self) -> dict:
        """Serialize for JSON storage. Schema includes embedding_type for clarity."""
        result = {
            "user_id": self.user_id,
            "encoding": self.encoding.tolist(),
            "embedding_type": EMBEDDING_TYPE,
            "embedding_dim": len(self.encoding),
            "image_b64": self.image_b64,
        }
        if self.encoding_dlib is not None:
            result["encoding_dlib"] = self.encoding_dlib.tolist()
        return result

    @classmethod
    def from_dict(cls, user_id: str, data: dict) -> "FaceEncoding":
        """Deserialize from JSON (supports legacy format without embedding_type)."""
        if isinstance(data, list):
            encoding = np.array(data, dtype="float32")
            return cls(user_id=user_id, encoding=encoding, image_b64=None, encoding_dlib=None)
        encoding = np.array(data.get("encoding", []), dtype="float32")
        encoding_dlib = None
        if "encoding_dlib" in data:
            encoding_dlib = np.array(data["encoding_dlib"], dtype="float32")
        return cls(
            user_id=user_id,
            encoding=encoding,
            image_b64=data.get("image_b64"),
            encoding_dlib=encoding_dlib,
        )

    def __repr__(self) -> str:
        return f"FaceEncoding(user_id={self.user_id}, dim={len(self.encoding)}, type={'ArcFace' if self.is_insightface else 'legacy'})"
