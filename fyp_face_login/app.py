"""
Flask Application - API Routes Layer
Following BCE Framework Architecture

This file contains only route definitions that delegate to controllers.
All business logic is in the Service layer.
All data access is in the Repository layer.
All flow control is in the Controller layer.
"""
import warnings
import sys
import os

# Suppress face_recognition models warning
warnings.filterwarnings('ignore')

# Prevent face_recognition from calling sys.exit() when models aren't found
_original_exit = sys.exit
def _mock_exit(code=0):
    if code != 0:
        _original_exit(code)
sys.exit = _mock_exit

try:
    import cv2
    import face_recognition
    import numpy as np
finally:
    sys.exit = _original_exit

from flask import Flask, request, jsonify
from flask_cors import CORS

# Import repositories
from repositories.user_repository import UserRepository
from repositories.face_repository import FaceRepository
from repositories.admin_repository import AdminRepository

# Import services
from services.user_service import UserService
from services.face_recognition_service import FaceRecognitionService
from services.admin_service import AdminService

# Import controllers
from controllers.auth_controller import AuthController
from controllers.registration_controller import RegistrationController
from controllers.admin_controller import AdminController

# Initialize Flask app
app = Flask(__name__)
# Allow all origins for development (change in production!)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize repositories
user_repo = UserRepository("user_accounts.json")
face_repo = FaceRepository("known_faces.json")
admin_repo = AdminRepository("admin_config.json", 
                             default_email="admin@school.edu",
                             default_password_hash=None)

# Initialize services
user_service = UserService(user_repo, face_repo)
face_service = FaceRecognitionService(face_repo, user_repo)
admin_service = AdminService(admin_repo, user_repo, face_repo, user_service)

# Initialize controllers
auth_controller = AuthController(user_service, face_service)
registration_controller = RegistrationController(user_service, face_service)
admin_controller = AdminController(admin_service)

# Initialize default admin if needed
if not os.path.exists("admin_config.json"):
    from entities.admin import Admin
    admin_password_hash = UserService.hash_password("admin123")
    default_admin = Admin("admin@school.edu", admin_password_hash)
    admin_repo.save(default_admin)

# ========== API Routes ==========

@app.route("/api/register_account", methods=["POST"])
def register_account():
    """Create a new user account"""
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name = data.get("name", "").strip()

    result = registration_controller.register_account(email, password, name)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

@app.route("/api/login", methods=["POST"])
def login():
    """Login with email and password"""
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    result = auth_controller.login_with_credentials(email, password)
    status_code = 200 if result.get("success") else 401
    return jsonify(result), status_code

@app.route("/api/register_face", methods=["POST"])
def register_face():
    """Register face for an existing account"""
    data = request.get_json(force=True)
    image_b64 = data.get("image")
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not image_b64:
        return jsonify({"success": False, "error": "image required"}), 400

    result = registration_controller.register_face(image_b64, email, password)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

@app.route("/api/verify_face", methods=["POST"])
def verify_face():
    """Login using facial recognition"""
    data = request.get_json(force=True)
    image_b64 = data.get("image")

    if not image_b64:
        return jsonify({"success": False, "error": "image required"}), 400

    result = auth_controller.login_with_face(image_b64)
    
    # Add threshold info for debugging
    if not result.get("success"):
        result["threshold"] = 0.3
        distance = result.get("distance")
        if distance is not None:
            result["message"] = f"Match distance: {distance:.3f} (must be ≤ 0.3)"
        else:
            result["message"] = "Face not detected or no faces registered"
    
    if result.get("success"):
        status_code = 200
    elif result.get("error") == "Face not recognized":
        status_code = 401
    else:
        status_code = 400
    
    return jsonify(result), status_code

@app.route("/api/reset_face", methods=["POST"])
def reset_face():
    """Reset facial recognition for an account"""
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    image_b64 = data.get("image")

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password required"}), 400

    if not image_b64:
        return jsonify({"success": False, "error": "Image required"}), 400

    result = registration_controller.reset_face(image_b64, email, password)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

@app.route("/api/forgot_password", methods=["POST"])
def forgot_password():
    """Request password reset (simplified - in production would send email)"""
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"success": False, "error": "Email required"}), 400

    # Don't reveal if email exists (security best practice)
    return jsonify({
        "success": True,
        "message": "If this email exists, a password reset link has been sent."
    }), 200

@app.route("/api/forgot_email", methods=["POST"])
def forgot_email():
    """Recover email address using phone/student ID"""
    data = request.get_json(force=True)
    phone = data.get("phone", "").strip()
    student_id = data.get("studentId", "").strip()

    if not phone:
        return jsonify({"success": False, "error": "Phone number required"}), 400

    # Simplified version - not fully implemented
    return jsonify({
        "success": False,
        "error": "Email recovery not fully implemented. Please contact support."
    }), 501

# ========== Admin Routes ==========

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    """Admin login endpoint"""
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    result = admin_controller.login(email, password)
    status_code = 200 if result.get("success") else 401
    return jsonify(result), status_code

@app.route("/api/admin/users", methods=["GET"])
def get_all_users():
    """Get all users (admin only)"""
    result = admin_controller.get_all_users()
    return jsonify(result), 200

@app.route("/api/admin/users/<email>", methods=["DELETE"])
def delete_user(email):
    """Delete a user account (admin only)"""
    result = admin_controller.delete_user(email)
    status_code = 200 if result.get("success") else 404
    return jsonify(result), status_code

@app.route("/api/admin/users/<email>/reset-password", methods=["POST"])
def reset_user_password(email):
    """Reset a user's password (admin only)"""
    data = request.get_json(force=True)
    new_password = data.get("new_password", "")

    result = admin_controller.reset_user_password(email, new_password)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

# ========== Health Check ==========

@app.route("/")
def health():
    return "Face login backend running"

if __name__ == "__main__":
    # Use use_reloader=False to avoid issues with stdin/stderr redirection
    app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False)
