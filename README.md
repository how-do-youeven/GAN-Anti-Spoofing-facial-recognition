# Facial Recognition Login System - Student Portal

A full-stack web application implementing facial recognition authentication for a school management system. Students can create accounts, register their faces, and login using either facial recognition or traditional email/password authentication.

## 🚀 Features

### Student Features
- **Facial Recognition Authentication**: Secure login using face detection and matching
- **Traditional Login**: Email/password authentication as an alternative
- **Face Login Failure Protection**: Face login disabled after 5 failed attempts (requires password login and face reset)
- **Student Profile**: View account details, face registration status, and login history
- **Feedback Submission**: Submit feedback to operations admin directly from login page

### Admin Features
- **Dual Admin Roles**: 
  - **System Admin**: Approve/reject registrations, manage users, view logs
  - **Operations Admin**: Manage feedback, view student information, handle operations
- **Registration Approval Workflow**: New registrations require admin approval before login
- **Admin Dashboard**: Role-based dashboard with different features per admin type
- **Feedback Management**: Operations admin can view, filter, and update feedback status
- **User Management**: View all users, delete accounts, reset passwords

### Technical Features
- **BCE Framework Architecture**: Clean, maintainable code structure
- **Responsive UI**: Modern, user-friendly interface
- **Face verification**: InsightFace ArcFace (512D embeddings) for detection and matching
- **Anti-spoofing**: Silent Face (minivision-ai) by default, with GAN predictor fallback; blocks photo/screen attacks
- **Activity log**: Real/spoof probabilities and verification results (in-memory, viewable at `/activity-log`)
- **Audit log**: Persistent file log of verification attempts (`audit_face.jsonl`)
- **Rate limiting**: Per-IP limits on `/api/verify_face`

## 🏗️ Architecture

This project follows the **BCE (Business-Control-Entity) Framework**:

- **Entity Layer**: Domain models (User, FaceEncoding, Admin, Feedback)
- **Repository Layer**: Data access operations
- **Service Layer**: Business logic and rules
- **Controller Layer**: Flow control and coordination
- **API Routes**: HTTP endpoint definitions

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## 📋 Prerequisites

- Python 3.13+ (or Python 3.8+)
- CMake (for dlib installation)
- Web browser with camera access
- pip (Python package manager)

### Installing CMake

**macOS:**
```bash
brew install cmake
```

**Windows:**
1. Download CMake installer from: https://cmake.org/download/
2. Run the installer and select "Add CMake to system PATH"
3. Restart your terminal/command prompt after installation

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install cmake
```

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/timthemanpan/FYP-Facial-Recognition-Login.git
   cd FYP-Facial-Recognition-Login
   ```

2. **Create and activate virtual environment**

   **macOS/Linux:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   **Windows:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
   
   You should see `(venv)` in your terminal prompt when activated.

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Silent Face anti-spoof models** are included in `anti_spoof_models/` at the project root, so Silent Face works after clone. If you remove that folder, the app will fall back to the GAN predictor (if available) or run without anti-spoof; you can force GAN-only with `SPOOF_BACKEND=gan`.

## 🚀 Running the Application

### Start the Backend Server

From the project root (after cloning and installing dependencies):

**Option 1 – from inside the package (recommended):**
```bash
cd fyp_face_login
python app.py
```

**Option 2 – from project root:**
```bash
python fyp_face_login/app.py
```

The server will start on `http://localhost:8000`. Data files (`user_accounts.json`, `known_faces.json`, etc.) are created inside `fyp_face_login/` either way.

**Optional environment variables** (set before running):
- `SPOOF_BACKEND=gan` — Use only the GAN predictor for anti-spoof (skip Silent Face). Use if Silent Face models are not set up.
- `GAN_PREDICTOR_MODEL_PATH` — Full path to `predictor_best.pt` if not using the default `GAN_V1/ml/exports/predictor_best.pt`.
- `FACE_USE_CPU=1` — Force InsightFace to use CPU only (e.g. if ONNX GPU fails).

**Note:** If you encounter issues with `dlib` installation on Windows:
1. Make sure CMake is installed and added to PATH
2. You may need Visual Studio Build Tools (C++ compiler)
3. Alternative: Use pre-built wheels: `pip install dlib` (may require specific Python version)

### Start the Frontend

**Option 1: Using Live Server (VS Code)**
- Right-click on `frontend/home page.html`
- Select "Open with Live Server"

**Option 2: Using Python HTTP Server**

**macOS/Linux:**
```bash
python3 -m http.server 5500
```

**Windows:**
```bash
python -m http.server 5500
```

Then open: `http://localhost:5500/frontend/home page.html`

**Option 3: Direct File Open**
- Navigate to `frontend/` folder and double-click `home page.html` (some browsers may block CORS)

## 📁 Project Structure

```
FYP-Facial-Recognition-Login/
├── frontend/                    # Frontend HTML pages
│   ├── home page.html          # Landing page
│   ├── login.html              # Facial recognition login (with feedback form)
│   ├── ManualLogin.html        # Email/password login
│   ├── RegisterAccount.html    # Account registration
│   ├── RegisterFace.html       # Face registration
│   ├── Profile.html            # Student profile page
│   ├── ActivityLog.html        # Activity log (real/spoof probs, verification results)
│   ├── ResetFacialRecognition.html
│   ├── AdminLogin.html         # Admin login
│   ├── AdminDashboard.html     # Admin dashboard (role-based)
│   ├── ForgotPassword.html
│   └── ForgotEmail.html
├── fyp_face_login/              # Backend (BCE Framework)
│   ├── app.py                   # Flask routes
│   ├── entities/                # Entity Layer
│   │   ├── user.py             # User entity (with registration_status, face_login_failures)
│   │   ├── admin.py            # Admin entity (with admin_type)
│   │   ├── face_encoding.py    # Face encoding entity
│   │   └── feedback.py         # Feedback entity
│   ├── repositories/            # Repository Layer
│   │   ├── user_repository.py
│   │   ├── admin_repository.py
│   │   ├── face_repository.py
│   │   └── feedback_repository.py
│   ├── services/                # Service Layer
│   │   ├── user_service.py
│   │   ├── admin_service.py
│   │   ├── face_recognition_service.py
│   │   ├── spoof_detection_service.py   # GAN predictor (face-crop)
│   │   └── silent_face_spoof_service.py # Silent Face anti-spoof (full frame + bbox)
│   ├── vendor/                  # Vendored code (Silent Face crop + MiniFASNet)
│   ├── activity_log.py          # In-memory activity log for face verify
│   ├── audit_log.py             # Persistent audit log (audit_face.jsonl)
│   ├── rate_limit.py            # Per-IP rate limiting for verify_face
│   ├── controllers/             # Controller Layer
│   │   ├── auth_controller.py
│   │   ├── registration_controller.py
│   │   └── admin_controller.py
│   ├── user_accounts.json       # User data (created on first run, gitignored)
│   ├── known_faces.json         # Face encodings (created on first run, gitignored)
│   ├── admin_config.json       # Admin config (created on first run, gitignored)
│   └── feedback.json           # Feedback data (created on first run, gitignored)
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md          # Architecture documentation
│   ├── AUTHENTICATION_LOGIC.md  # Authentication logic
│   ├── FACIAL_RECOGNITION_SERVICE.md  # Face verification & storage
│   ├── BEST_FACIAL_RECOGNITION_SERVICE.md # Checklist & features
│   ├── PROJECT_DOCUMENTATION.md # Complete documentation
│   └── ...
├── requirements.txt             # Python dependencies
├── README.md                    # This file
└── .gitignore                   # Git ignore rules
```

## 🔐 Default Credentials

**System Admin:**
- Email: `system@school.edu`
- Password: `admin123`
- Capabilities: Approve/reject registrations, manage users, view all accounts

**Operations Admin:**
- Email: `operations@school.edu`
- Password: `admin123`
- Capabilities: Manage feedback, view student information, handle operations

**Note**: Change these credentials in production!

## 📚 Documentation

- **[docs/PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md)**: Complete project documentation
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: BCE framework architecture details
- **[docs/AUTHENTICATION_LOGIC.md](docs/AUTHENTICATION_LOGIC.md)**: Authentication logic (InsightFace, Silent Face, GAN)
- **[docs/FACIAL_RECOGNITION_SERVICE.md](docs/FACIAL_RECOGNITION_SERVICE.md)**: Face verification and storage
- **[docs/BEST_FACIAL_RECOGNITION_SERVICE.md](docs/BEST_FACIAL_RECOGNITION_SERVICE.md)**: Feature checklist and behaviour

## 🔧 Configuration

### Security Thresholds

Face recognition security thresholds are configured in `fyp_face_login/services/face_recognition_service.py`:

**InsightFace (Primary - Better glasses handling):**
- `VERIFY_THRESHOLD`: 0.35 (for multi-face scenarios)
- `SINGLE_FACE_THRESHOLD`: 0.30 (for single-face scenarios - more lenient for glasses)

**dlib fallback:**
- `VERIFY_THRESHOLD`: 0.3 (for multi-face scenarios)
- `SINGLE_FACE_THRESHOLD`: 0.25 (for single-face scenarios)

Lower values = stricter matching (more secure)

**Anti-spoofing:** By default the app tries **Silent Face** (minivision-ai) first; place `.pth` models in `Silent-Face-Anti-Spoofing/resources/anti_spoof_models/` (see that repo's README). If Silent Face is not available, it uses the **GAN predictor** (`GAN_V1/ml/exports/predictor_best.pt`). Set `SPOOF_BACKEND=gan` to use only the GAN predictor.

**Note:** The system uses **InsightFace (ArcFace)** for face detection and verification (512D embeddings). If InsightFace is not available (e.g. missing `onnxruntime`), the app reports this on `/api/status` and `/api/diagnose/insightface`.

### Anti-spoof (Silent Face vs GAN)

- **Default:** App tries **Silent Face** first (needs `Silent-Face-Anti-Spoofing` clone and `.pth` models in `Silent-Face-Anti-Spoofing/resources/anti_spoof_models/`). See [minivision-ai/Silent-Face-Anti-Spoofing](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing) for model download.
- **Fallback:** If Silent Face is not available, **GAN predictor** is used (`GAN_V1/ml/exports/predictor_best.pt`). Requires `torch` and `torchvision`.
- **Force GAN only:** Set `SPOOF_BACKEND=gan` to skip Silent Face and use only the GAN predictor.
- **Check status:** `GET http://localhost:8000/api/status` shows `insightface`, `spoof_backend` (`silent_face` / `gan` / `none`), and any `spoof_backend_error` or `insightface_error`.

### CORS Configuration

CORS is configured in `fyp_face_login/app.py` to allow all origins for development. **Change this in production!**

## 🧪 Testing

### Student Workflow
1. Create a test account via `frontend/RegisterAccount.html` (status will be "pending")
2. Log in as System Admin and approve the registration
3. Register your face via `frontend/RegisterFace.html`
4. Test facial recognition login via `frontend/login.html`
5. Test email/password login via `frontend/ManualLogin.html`
6. View your profile via `frontend/Profile.html`
7. Submit feedback from the login page

### Admin Workflow
1. Log in as System Admin (`system@school.edu` / `admin123`)
   - View and approve/reject pending registrations
   - Manage user accounts
2. Log in as Operations Admin (`operations@school.edu` / `admin123`)
   - View and manage student feedback
   - Filter feedback by status (pending/in_progress/completed/no_action_taken)
   - Update feedback status

## 📝 API Endpoints

### User Endpoints
- `POST /api/register_account` - Create new account (status: pending, requires approval)
- `POST /api/login` - Login with email/password (only if approved)
- `GET /api/user/profile` - Get user profile information
- `POST /api/register_face` - Register face for account (only if approved)
- `POST /api/verify_face` - Login with facial recognition (rate-limited; returns `real_prob`, `spoof_prob` when anti-spoof runs; tracks failures, disables after 5)
- `POST /api/reset_face` - Reset facial recognition (re-enables face login)
- `POST /api/forgot_password` - Request password reset
- `POST /api/forgot_email` - Recover email address
- `POST /api/feedback` - Submit feedback to operations admin
- `GET /api/activity-log` - Recent face verification activity (real/spoof probs, spoof check, verification result)
- `POST /api/activity-log/clear` - Clear in-memory activity log
- `GET /api/status` - Backend status (InsightFace, spoof backend, registered face count, optional `insightface_error` / `spoof_backend_error`)
- `GET /api/diagnose/insightface` - Step-by-step InsightFace diagnostics

### Admin Endpoints

#### Authentication
- `POST /api/admin/login` - Admin authentication (returns admin_type)

#### System Admin Endpoints
- `GET /api/admin/users` - Get all users
- `GET /api/admin/registrations/pending` - Get pending registrations
- `POST /api/admin/registrations/<email>/approve` - Approve user registration
- `POST /api/admin/registrations/<email>/reject` - Reject user registration
- `DELETE /api/admin/users/<email>` - Delete user
- `POST /api/admin/users/<email>/reset-password` - Reset user password

#### Operations Admin Endpoints
- `GET /api/admin/feedback` - Get all feedback (optional: `?status=<status>` filter)
- `POST /api/admin/feedback/<feedback_id>/status` - Update feedback status

## 🛡️ Security Considerations

- **Password Security**: Passwords are hashed using SHA-256 (consider bcrypt for production)
- **Face Recognition Security**: 
  - Face encodings are stored as numerical vectors (cannot be reverse-engineered)
  - Strict matching thresholds prevent false positives (0.3 for multi-face, 0.25 for single-face)
  - Spoof detection prevents photo/video attacks
  - Face login disabled after 5 failed attempts
- **Registration Approval**: New accounts require admin approval before access
- **Role-Based Access**: Separate admin roles with different permissions
- **CORS**: Configured for development (update for production)
- **Rate limiting**: Per-IP limits on `/api/verify_face` to reduce abuse
- **Audit log**: Verification attempts logged to `audit_face.jsonl` (gitignored)
- **Input Validation**: All endpoints validate input data
- **Data Protection**: Sensitive files (user accounts, face data, admin config, feedback, audit log) are gitignored

## 🐛 Troubleshooting

### Server won't start:
- Check if port 8000 is already in use
- Ensure virtual environment is activated
- Verify all dependencies are installed
- **Windows:** Make sure Python is added to PATH

### Face recognition not working:
- Grant camera permissions in browser
- Ensure good lighting
- Make sure only one face is visible
- Check browser console for errors

### Connection errors:
- Ensure backend is running on port 8000
- Check that frontend is using HTTP (not file://)
- Verify CORS is enabled in backend

### Windows-specific issues:

**dlib installation fails:**
- Install Visual Studio Build Tools (C++ compiler)
- Download from: https://visualstudio.microsoft.com/downloads/
- Select "Desktop development with C++" workload
- Restart terminal and try: `pip install dlib`

**CMake not found:**
- Make sure CMake is installed and added to system PATH
- Restart terminal/command prompt after installation
- Verify: `cmake --version` in command prompt

**Python command not found:**
- Use `python` instead of `python3` on Windows
- Make sure Python is added to PATH during installation
- Try: `py -m pip install -r requirements.txt`

## 📄 License

This project is part of a Final Year Project (FYP) for academic purposes.

## 👥 Contributors

- [Your Name]
- [Groupmate 1]
- [Groupmate 2]

## 📞 Support

For technical support or questions, please contact the development team.

---

**Note**: This is a demonstration project. For production deployment, consider:
- Migrating to a proper database (PostgreSQL, MySQL)
- Using bcrypt for password hashing
- Implementing HTTPS
- Tightening rate limits and CORS
- Implementing proper session management
- Adding email verification
- Setting up proper logging and monitoring (audit log is already persisted to file)
