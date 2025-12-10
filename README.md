# Facial Recognition Login System - Student Portal

A full-stack web application implementing facial recognition authentication for a school management system. Students can create accounts, register their faces, and login using either facial recognition or traditional email/password authentication.

## 🚀 Features

- **Facial Recognition Authentication**: Secure login using face detection and matching
- **Traditional Login**: Email/password authentication as an alternative
- **User Account Management**: Create accounts, manage profiles
- **Admin Dashboard**: View all users, manage accounts, reset passwords
- **BCE Framework Architecture**: Clean, maintainable code structure
- **Responsive UI**: Modern, user-friendly interface

## 🏗️ Architecture

This project follows the **BCE (Business-Control-Entity) Framework**:

- **Entity Layer**: Domain models (User, FaceEncoding, Admin)
- **Repository Layer**: Data access operations
- **Service Layer**: Business logic and rules
- **Controller Layer**: Flow control and coordination
- **API Routes**: HTTP endpoint definitions

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## 📋 Prerequisites

- Python 3.13+
- CMake (for dlib installation)
- Web browser with camera access
- pip (Python package manager)

### Installing CMake (macOS)

```bash
brew install cmake
```

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd FYP
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Running the Application

### Start the Backend Server

```bash
cd fyp_face_login
python app.py
```

The server will start on `http://localhost:8000`

### Start the Frontend

**Option 1: Using Live Server (VS Code)**
- Right-click on `home page.html`
- Select "Open with Live Server"

**Option 2: Using Python HTTP Server**
```bash
python3 -m http.server 8080
```
Then open: `http://localhost:8080/home page.html`

**Option 3: Direct File Open**
- Simply double-click `home page.html` (some browsers may block CORS)

## 📁 Project Structure

```
FYP/
├── fyp_face_login/              # Backend (BCE Framework)
│   ├── app.py                   # Flask routes
│   ├── entities/                # Entity Layer
│   ├── repositories/            # Repository Layer
│   ├── services/                # Service Layer
│   ├── controllers/             # Controller Layer
│   ├── user_accounts.json       # User data (created on first run)
│   ├── known_faces.json         # Face encodings (created on first run)
│   └── admin_config.json       # Admin config (created on first run)
├── *.html                       # Frontend pages
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── ARCHITECTURE.md              # Architecture documentation
└── PROJECT_DOCUMENTATION.md     # Complete project documentation
```

## 🔐 Default Credentials

**Admin Account:**
- Email: `admin@school.edu`
- Password: `admin123`

**Note**: Change these credentials in production!

## 📚 Documentation

- **[PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)**: Complete project documentation
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: BCE framework architecture details
- **[AUTHENTICATION_LOGIC.md](AUTHENTICATION_LOGIC.md)**: Authentication logic explanation

## 🔧 Configuration

### Security Thresholds

Face recognition security thresholds are configured in `fyp_face_login/services/face_recognition_service.py`:

- `VERIFY_THRESHOLD`: 0.3 (for multi-face scenarios)
- `SINGLE_FACE_THRESHOLD`: 0.25 (for single-face scenarios)

Lower values = stricter matching (more secure)

### CORS Configuration

CORS is configured in `fyp_face_login/app.py` to allow all origins for development. **Change this in production!**

## 🧪 Testing

1. Create a test account via `RegisterAccount.html`
2. Register your face via `RegisterFace.html`
3. Test facial recognition login via `login.html`
4. Test email/password login via `ManualLogin.html`
5. Access admin dashboard via `AdminLogin.html`

## 📝 API Endpoints

### User Endpoints
- `POST /api/register_account` - Create new account
- `POST /api/login` - Login with email/password
- `POST /api/register_face` - Register face for account
- `POST /api/verify_face` - Login with facial recognition
- `POST /api/reset_face` - Reset facial recognition
- `POST /api/forgot_password` - Request password reset
- `POST /api/forgot_email` - Recover email address

### Admin Endpoints
- `POST /api/admin/login` - Admin authentication
- `GET /api/admin/users` - Get all users
- `DELETE /api/admin/users/<email>` - Delete user
- `POST /api/admin/users/<email>/reset-password` - Reset user password

## 🛡️ Security Considerations

- Passwords are hashed using SHA-256 (consider bcrypt for production)
- Face encodings are stored as numerical vectors (cannot be reverse-engineered)
- Strict matching thresholds prevent false positives
- CORS configured for development (update for production)
- Input validation on all endpoints

## 🐛 Troubleshooting

**Server won't start:**
- Check if port 8000 is already in use
- Ensure virtual environment is activated
- Verify all dependencies are installed

**Face recognition not working:**
- Grant camera permissions in browser
- Ensure good lighting
- Make sure only one face is visible
- Check browser console for errors

**Connection errors:**
- Ensure backend is running on port 8000
- Check that frontend is using HTTP (not file://)
- Verify CORS is enabled in backend

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
