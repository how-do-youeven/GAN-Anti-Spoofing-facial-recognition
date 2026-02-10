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

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Import repositories
from repositories.user_repository import UserRepository
from repositories.face_repository import FaceRepository
from repositories.admin_repository import AdminRepository
from repositories.feedback_repository import FeedbackRepository

# Import services
from services.user_service import UserService
from services.face_recognition_service import FaceRecognitionService
from services.admin_service import AdminService
from services.spoof_detection_service import SpoofDetectionService
try:
    from services.silent_face_spoof_service import SilentFaceSpoofService
    SILENT_FACE_AVAILABLE = True
except Exception:
    SILENT_FACE_AVAILABLE = False

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
feedback_repo = FeedbackRepository("feedback.json")

# Initialize services: anti-spoofing (GAN or Silent Face). Set SPOOF_BACKEND=gan to skip Silent Face.
spoof_service = None
spoof_backend_errors = []
use_gan_only = os.environ.get("SPOOF_BACKEND", "").strip().lower() == "gan"
if not use_gan_only and SILENT_FACE_AVAILABLE:
    try:
        spoof_service = SilentFaceSpoofService()
        print("✅ Using Silent Face for anti-spoofing")
    except Exception as e:
        spoof_backend_errors.append(f"Silent Face: {e}")
        print(f"Silent Face not used: {e}")
if spoof_service is None:
    try:
        spoof_service = SpoofDetectionService()
        spoof_backend_errors = []
        print("✅ Using GAN predictor for anti-spoofing")
    except Exception as e:
        spoof_backend_errors.append(f"GAN: {e}")
        print(f"Spoof detection unavailable: {e}")
spoof_backend_error = "; ".join(spoof_backend_errors) if spoof_backend_errors else None
user_service = UserService(user_repo, face_repo)
face_service = FaceRecognitionService(face_repo, user_repo, spoof_detection=spoof_service)
admin_service = AdminService(admin_repo, user_repo, face_repo, user_service, feedback_repo)

# Initialize controllers
auth_controller = AuthController(user_service, face_service)
registration_controller = RegistrationController(user_service, face_service)
admin_controller = AdminController(admin_service)

# Initialize default admins if needed
if not os.path.exists("admin_config.json"):
    from entities.admin import Admin
    admin_password_hash = UserService.hash_password("admin123")
    
    # Create system admin
    system_admin = Admin("system@school.edu", admin_password_hash, Admin.SYSTEM_ADMIN)
    admin_repo.save(system_admin)
    
    # Create operations admin
    operations_admin = Admin("operations@school.edu", admin_password_hash, Admin.OPERATIONS_ADMIN)
    admin_repo.save(operations_admin)

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
    try:
        data = request.get_json(force=True)
        image_b64 = data.get("image")
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not image_b64:
            return jsonify({"success": False, "error": "image required"}), 400

        result = registration_controller.register_face(image_b64, email, password)
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
    except ValueError as e:
        # Handle image decoding errors
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        # Handle any other errors
        print(f"ERROR in register_face: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": "Internal server error processing face image"}), 500

def _client_ip():
    """Client IP for rate limit and audit (respect X-Forwarded-For behind proxy)."""
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()


@app.route("/api/verify_face", methods=["POST"])
def verify_face():
    """Login using facial recognition (rate-limited, audited)."""
    ip = _client_ip()
    try:
        from rate_limit import check_rate_limit
        allowed, retry_after = check_rate_limit(ip)
        if not allowed:
            resp = jsonify({
                "success": False,
                "error": "Too many face login attempts. Please try again later.",
                "retry_after_seconds": round(retry_after, 1),
            })
            resp.status_code = 429
            resp.headers["Retry-After"] = str(max(1, int(retry_after)))
            return resp
    except ImportError:
        pass

    try:
        data = request.get_json(force=True)
        image_b64 = data.get("image")

        if not image_b64:
            return jsonify({"success": False, "error": "image required"}), 400

        result = auth_controller.login_with_face(image_b64)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        print(f"ERROR in verify_face: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": "Internal server error processing face image"}), 500

    # Persistent audit log
    try:
        from audit_log import log_verification
        log_verification(
            ip=ip,
            success=result.get("success", False),
            user_id=result.get("user_id"),
            reason=result.get("reason"),
            distance=result.get("distance"),
        )
    except ImportError:
        pass

    if not result.get("success"):
        result["threshold"] = 0.38
        distance = result.get("distance")
        if distance is not None:
            result["message"] = f"Match distance: {distance:.3f} (must be ≤ 0.38)"
        else:
            result["message"] = "Face not detected or no faces registered"

    if result.get("success"):
        status_code = 200
    elif result.get("reason") in ("match_failed", "no_face_detected") or "not recognized" in result.get("error", ""):
        status_code = 401
    else:
        status_code = 400

    return jsonify(result), status_code

@app.route("/api/reset_face", methods=["POST"])
def reset_face():
    """Reset facial recognition for an account"""
    try:
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
    except ValueError as e:
        # Handle image decoding errors
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        # Handle any other errors
        print(f"ERROR in reset_face: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": "Internal server error processing face image"}), 500

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

@app.route("/api/admin/registrations/pending", methods=["GET"])
def get_pending_registrations():
    """Get all pending user registrations (system admin only)"""
    result = admin_controller.get_pending_registrations()
    return jsonify(result), 200

@app.route("/api/admin/registrations/<email>/approve", methods=["POST"])
def approve_registration(email):
    """Approve a user registration (system admin only)"""
    result = admin_controller.approve_registration(email)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

@app.route("/api/admin/registrations/<email>/reject", methods=["POST"])
def reject_registration(email):
    """Reject a user registration (system admin only)"""
    result = admin_controller.reject_registration(email)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

# ========== User Profile Routes ==========

@app.route("/api/user/profile", methods=["GET"])
def get_user_profile():
    """Get user profile information"""
    # Get email from query parameter or session (simplified for now)
    email = request.args.get("email", "").strip().lower()
    
    if not email:
        return jsonify({"success": False, "error": "Email required"}), 400
    
    user = user_service.get_user_info(email)
    
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    
    # Get face registration status
    face_registered = face_repo.exists(user.user_id)
    
    return jsonify({
        "success": True,
        "user": {
            "email": user.email,
            "user_id": user.user_id,
            "name": user.name,
            "face_registered": face_registered,
            "created": user.created,
            "face_login_disabled": user.face_login_disabled,
            "face_login_failures": user.face_login_failures
        }
    }), 200

@app.route("/api/user/face-login/disable", methods=["POST"])
def disable_face_login():
    """Disable face login for the current user"""
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    
    if not email:
        return jsonify({"success": False, "error": "Email required"}), 400
    
    success, error = user_service.disable_face_login(email)
    
    if not success:
        return jsonify({"success": False, "error": error}), 400
    
    return jsonify({
        "success": True,
        "message": "Face login has been disabled. You can re-enable it anytime from your profile."
    }), 200

@app.route("/api/user/face-login/enable", methods=["POST"])
def enable_face_login():
    """Re-enable face login for the current user (requires password)"""
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"success": False, "error": "Email and password required"}), 400
    
    success, error = user_service.enable_face_login(email, password)
    
    if not success:
        return jsonify({"success": False, "error": error}), 400
    
    return jsonify({
        "success": True,
        "message": "Face login has been re-enabled. Failure count has been reset."
    }), 200

@app.route("/api/user/face-image", methods=["GET"])
def get_face_image():
    """Get the registered face image for a user"""
    email = request.args.get("email", "").strip().lower()
    
    if not email:
        return jsonify({"success": False, "error": "Email required"}), 400
    
    user = user_service.get_user_info(email)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    
    # Get face image
    face_image = face_service.get_face_image(user.user_id)
    
    if not face_image:
        return jsonify({"success": False, "error": "No face image found. Please register your face first."}), 404
    
    return jsonify({
        "success": True,
        "image": face_image
    }), 200

# ========== Feedback Routes ==========

@app.route("/api/feedback", methods=["POST"])
def submit_feedback():
    """Submit user feedback"""
    import uuid
    from entities.feedback import Feedback
    
    data = request.get_json(force=True)
    user_email = data.get("email", "").strip().lower()
    message = data.get("message", "").strip()
    
    if not user_email or not message:
        return jsonify({"success": False, "error": "Email and message required"}), 400
    
    if len(message) < 10:
        return jsonify({"success": False, "error": "Message must be at least 10 characters"}), 400
    
    # Create feedback
    feedback_id = f"fb_{uuid.uuid4().hex[:8]}"
    feedback = Feedback(
        feedback_id=feedback_id,
        user_email=user_email,
        message=message
    )
    
    feedback_repo.save(feedback)
    
    return jsonify({
        "success": True,
        "message": "Feedback submitted successfully. Operations admin will review it."
    }), 200

@app.route("/api/admin/feedback", methods=["GET"])
def get_all_feedback():
    """Get all user feedback (operations admin only)"""
    status_filter = request.args.get("status", None)
    result = admin_controller.get_all_feedback(status_filter=status_filter)
    return jsonify(result), 200

@app.route("/api/admin/feedback/<feedback_id>/status", methods=["POST"])
def update_feedback_status(feedback_id):
    """Update feedback status (operations admin only)"""
    data = request.get_json(force=True)
    new_status = data.get("status", "").strip()
    
    if not new_status:
        return jsonify({"success": False, "error": "Status is required"}), 400
    
    result = admin_controller.update_feedback_status(feedback_id, new_status)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

# ========== Health & Status ==========

@app.route("/api/status", methods=["GET"])
def status():
    """Check if the app is configured correctly for face login (for debugging)."""
    try:
        spoof_backend = "none"
        if face_service.spoof_detection is not None:
            spoof_backend = "silent_face" if getattr(face_service.spoof_detection, "uses_full_frame", False) else "gan"
        registered = face_repo.load_all() or {}
        out = {
            "ok": True,
            "insightface": face_service.use_insightface,
            "insightface_model": getattr(face_service, "insightface_model_name", None),
            "embedding_type": "insightface_arcface" if face_service.use_insightface else "legacy",
            "spoof_backend": spoof_backend,
            "registered_face_count": len(registered),
            "message": "Backend is running. Ensure you have registered your face (after account approval) to use face login."
        }
        if not face_service.use_insightface and getattr(face_service, "insightface_error", None):
            out["insightface_error"] = face_service.insightface_error
        if spoof_backend == "none" and spoof_backend_error:
            out["spoof_backend_error"] = spoof_backend_error
        return jsonify(out), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/diagnose/insightface", methods=["GET"])
@app.route("/api/insightface-diagnose", methods=["GET"])  # alternate URL (no slash in path)
def diagnose_insightface():
    """Run step-by-step InsightFace diagnostics and return the first failure reason."""
    steps = []
    try:
        # Step 1: import insightface
        try:
            import insightface
            steps.append({"step": "import_insightface", "ok": True})
        except ImportError as e:
            steps.append({"step": "import_insightface", "ok": False, "error": str(e)})
            return jsonify({"ok": False, "steps": steps, "fix": "Run: pip install insightface"}), 200

        # Step 2: import onnxruntime
        try:
            import onnxruntime as ort
            steps.append({"step": "import_onnxruntime", "ok": True, "version": getattr(ort, "__version__", "?")})
        except ImportError as e:
            steps.append({"step": "import_onnxruntime", "ok": False, "error": str(e)})
            return jsonify({"ok": False, "steps": steps, "fix": "Run: pip install onnxruntime"}), 200

        # Step 3: list available providers
        try:
            providers = ort.get_available_providers()
            steps.append({"step": "onnx_providers", "ok": True, "providers": providers})
        except Exception as e:
            steps.append({"step": "onnx_providers", "ok": False, "error": str(e)})

        # Step 4: FaceAnalysis with CPU only (most compatible)
        try:
            app = insightface.app.FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
            steps.append({"step": "FaceAnalysis_CPU", "ok": True})
        except Exception as e:
            steps.append({"step": "FaceAnalysis_CPU", "ok": False, "error": str(e)})
            return jsonify({"ok": False, "steps": steps, "fix": "Check that insightface and onnxruntime versions are compatible. Try: pip install -U insightface onnxruntime"}), 200

        # Step 5: prepare() - downloads models on first run
        try:
            app.prepare(ctx_id=0, det_size=(640, 640))
            steps.append({"step": "prepare", "ok": True})
        except Exception as e:
            steps.append({"step": "prepare", "ok": False, "error": str(e)})
            return jsonify({
                "ok": False,
                "steps": steps,
                "fix": "Model download may have failed (network/firewall?). First run needs internet. Or set FACE_USE_CPU=1 and restart."
            }), 200

        steps.append({"step": "all", "ok": True})
        return jsonify({"ok": True, "steps": steps, "message": "InsightFace is ready. Restart the server to use it."}), 200
    except Exception as e:
        import traceback
        return jsonify({"ok": False, "error": str(e), "steps": steps, "traceback": traceback.format_exc()}), 200


def _get_activity_log_module():
    """Import activity_log from same package or current dir."""
    try:
        from activity_log import get_recent, clear
        return get_recent, clear
    except ImportError:
        import sys
        import os
        app_dir = os.path.dirname(os.path.abspath(__file__))
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)
        from activity_log import get_recent, clear
        return get_recent, clear


@app.route("/api/activity-log", methods=["GET"])
def get_activity_log():
    """Return recent face verification activity (spoof + verification) for the log page."""
    try:
        get_recent, _ = _get_activity_log_module()
        limit = min(int(request.args.get("limit", 100)), 200)
        return jsonify({"entries": get_recent(limit=limit)}), 200
    except Exception as e:
        return jsonify({"error": str(e), "entries": []}), 200  # 200 + JSON so frontend never gets HTML


@app.route("/api/activity-log/clear", methods=["POST"])
def clear_activity_log():
    """Clear the in-memory activity log."""
    try:
        _, clear = _get_activity_log_module()
        clear()
        return jsonify({"success": True, "message": "Log cleared"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200


_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")


@app.route("/activity-log")
def activity_log_page():
    """Serve the activity log HTML page."""
    return send_from_directory(_FRONTEND_DIR, "ActivityLog.html")


@app.route("/login")
@app.route("/login.html")
def login_page():
    """Serve the face login page."""
    return send_from_directory(_FRONTEND_DIR, "login.html")


@app.route("/")
def index():
    """Serve login page at root."""
    return send_from_directory(_FRONTEND_DIR, "login.html")


@app.route("/health")
def health():
    """Health check (plain text)."""
    return "Face login backend running", 200


@app.route("/<path:filename>")
def frontend_file(filename):
    """Serve other frontend HTML/files (e.g. ManualLogin.html, RegisterAccount.html)."""
    if ".." in filename or filename.startswith("/"):
        from flask import abort
        abort(404)
    path = os.path.join(_FRONTEND_DIR, filename)
    if os.path.isfile(path):
        return send_from_directory(_FRONTEND_DIR, filename)
    from flask import abort
    abort(404)


if __name__ == "__main__":
    # Use use_reloader=False to avoid issues with stdin/stderr redirection
    app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False)
