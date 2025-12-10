"""
Repository Layer - Data Access
Handles all database/file operations
"""
from .user_repository import UserRepository
from .face_repository import FaceRepository
from .admin_repository import AdminRepository

__all__ = ['UserRepository', 'FaceRepository', 'AdminRepository']

