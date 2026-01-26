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
- **Spoof Detection**: Protection against photo/video spoofing attacks

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
   git clone <repository-url>
   cd FYP
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

## 🚀 Running the Application

### Start the Backend Server

**macOS/Linux:**
```bash
cd fyp_face_login
python app.py
```

**Windows:**
```bash
cd fyp_face_login
python app.py
```

The server will start on `http://localhost:8000`

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
python3 -m http.server 8080
```

**Windows:**
```bash
python -m http.server 8080
```

Then open: `http://localhost:8080/frontend/home page.html`

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
│   │   └── spoof_detection_service.py
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
│   ├── PROJECT_DOCUMENTATION.md # Complete documentation
│   ├── GITHUB_SETUP.md          # GitHub setup guide
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
- **[docs/AUTHENTICATION_LOGIC.md](docs/AUTHENTICATION_LOGIC.md)**: Authentication logic explanation
- **[docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md)**: GitHub repository setup guide

## 🔧 Configuration

### Security Thresholds

Face recognition security thresholds are configured in `fyp_face_login/services/face_recognition_service.py`:

- `VERIFY_THRESHOLD`: 0.3 (for multi-face scenarios)
- `SINGLE_FACE_THRESHOLD`: 0.25 (for single-face scenarios)

Lower values = stricter matching (more secure)

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
- `POST /api/verify_face` - Login with facial recognition (tracks failures, disables after 5)
- `POST /api/reset_face` - Reset facial recognition (re-enables face login)
- `POST /api/forgot_password` - Request password reset
- `POST /api/forgot_email` - Recover email address
- `POST /api/feedback` - Submit feedback to operations admin

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
- **Input Validation**: All endpoints validate input data
- **Data Protection**: Sensitive files (user accounts, face data, admin config, feedback) are gitignored

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
- Adding rate limiting
- Implementing proper session management
- Adding email verification
- Setting up proper logging and monitoring
