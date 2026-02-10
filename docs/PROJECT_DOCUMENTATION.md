# Facial Recognition Login System - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Program Flow](#program-flow)
3. [BCE Framework Architecture](#bce-framework-architecture)
4. [Key Features](#key-features)
5. [Registration Process](#registration-process)
6. [Authentication Process](#authentication-process)
7. [Data Storage](#data-storage)
8. [How to Run the Program](#how-to-run-the-program)

---

## Overview

This is a full-stack web application that implements facial recognition authentication for a school management system. Users can create accounts, register their faces, and login using either facial recognition or traditional email/password authentication.

**Technology Stack:**
- **Backend**: Python Flask (REST API)
- **Frontend**: HTML, CSS, JavaScript
- **Face verification**: InsightFace (ArcFace 512D embeddings); optional dlib fallback
- **Anti-spoofing**: Silent Face (minivision-ai) by default, with GAN predictor fallback
- **Architecture**: BCE Framework (Business-Control-Entity)

---

## Program Flow

### High-Level Flow

```
User → Frontend (HTML/JS) → API Request → Controller → Service → Repository → Entity → Database
                                                                    ↓
User ← Frontend (HTML/JS) ← API Response ← Controller ← Service ← Repository ← Entity ← Database
```

### Detailed User Journey

#### 1. Account Registration Flow
```
User visits home page
    ↓
Clicks "Create Account"
    ↓
Fills registration form (name, email, password)
    ↓
Frontend sends POST /api/register_account
    ↓
Backend: RegistrationController → UserService → UserRepository
    ↓
Account created, user_id generated
    ↓
User chooses: "Register Face" or "Skip for Now"
    ↓
If "Register Face":
    - Camera captures face
    - POST /api/register_face
    - Face encoding extracted and linked to account
    - Face data stored in known_faces.json
```

#### 2. Login Flow (Facial Recognition)
```
User visits login page
    ↓
Camera starts automatically
    ↓
User clicks "Scan Face to Login"
    ↓
Frontend captures frame from video
    ↓
POST /api/verify_face with image data
    ↓
Backend: AuthController → FaceRecognitionService
    ↓
Face encoding extracted from image
    ↓
Compared against all registered faces
    ↓
If match found (distance ≤ threshold):
    - User authenticated
    - Session created
    - Redirect to home page
Else:
    - Error message shown
    - User can try again or use email/password
```

#### 3. Login Flow (Email/Password)
```
User clicks "Use Email / Password Instead"
    ↓
Enters email and password
    ↓
POST /api/login
    ↓
Backend: AuthController → UserService
    ↓
Password verified against hash
    ↓
If valid:
    - User authenticated
    - Session created
    - Redirect to home page
Else:
    - Error message shown
```

---

## BCE Framework Architecture

The project follows the **BCE (Business-Control-Entity) Framework**, which separates code into distinct layers for better organization, maintainability, and testability.

### Architecture Diagram

```
┌─────────────────────────────────────┐
│     API Routes (app.py)             │  ← HTTP endpoints, request handling
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Controller Layer                │  ← Flow control, coordinates services
│  • AuthController                   │
│  • RegistrationController            │
│  • AdminController                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Service Layer                    │  ← Business logic, rules, algorithms
│  • UserService                       │
│  • FaceRecognitionService            │
│  • AdminService                      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Repository Layer                 │  ← Data access, file I/O
│  • UserRepository                   │
│  • FaceRepository                   │
│  • AdminRepository                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Entity Layer                     │  ← Domain models, data structures
│  • User                             │
│  • FaceEncoding                      │
│  • Admin                            │
└─────────────────────────────────────┘
```

### Layer Responsibilities

#### 1. Entity Layer (`entities/`)
**Purpose**: Domain models representing core business objects

**Files:**
- `user.py` - User entity (email, user_id, password_hash, name, face_registered, created)
- `face_encoding.py` - Face encoding entity (user_id, encoding array)
- `admin.py` - Admin entity (email, password_hash)

**Responsibilities:**
- Define data structures
- Convert to/from dictionaries for storage
- No business logic

#### 2. Repository Layer (`repositories/`)
**Purpose**: Data access operations

**Files:**
- `user_repository.py` - CRUD operations for users
- `face_repository.py` - CRUD operations for face encodings
- `admin_repository.py` - Admin configuration access

**Responsibilities:**
- Load/save data from JSON files
- Handle file I/O
- No business logic, just data access

#### 3. Service Layer (`services/`)
**Purpose**: Business logic and rules

**Files:**
- `user_service.py` - User registration, login, password management
- `face_recognition_service.py` - Face detection, encoding, matching
- `admin_service.py` - Admin operations, user management

**Responsibilities:**
- Implement business rules
- Validate data
- Perform calculations (face matching, password hashing)
- Coordinate between repositories

#### 4. Controller Layer (`controllers/`)
**Purpose**: Flow control and request/response coordination

**Files:**
- `auth_controller.py` - Handles login flows
- `registration_controller.py` - Handles registration flows
- `admin_controller.py` - Handles admin operations

**Responsibilities:**
- Coordinate service calls
- Format responses
- Handle request/response flow
- No business logic

#### 5. API Routes (`app.py`)
**Purpose**: HTTP endpoint definitions

**Responsibilities:**
- Define REST API endpoints
- Parse HTTP requests
- Call appropriate controllers
- Return JSON responses
- No business logic

### Benefits of BCE Framework

1. **Separation of Concerns**: Each layer has one responsibility
2. **Testability**: Each layer can be tested independently
3. **Maintainability**: Changes in one layer don't affect others
4. **Scalability**: Easy to add features or change implementations
5. **Reusability**: Services can be reused across controllers
6. **Clear Structure**: Easy to understand and navigate

---

## Key Features

### 1. User Account Management
- ✅ Create account with email and password
- ✅ Email validation and duplicate checking
- ✅ Password hashing (SHA-256)
- ✅ Account information storage (name, email, user_id, creation date)

### 2. Facial Recognition Authentication
- ✅ Face registration linked to user accounts
- ✅ Face verification for login
- ✅ Duplicate face detection (prevents same face on multiple accounts)
- ✅ Secure matching with configurable thresholds
- ✅ Multiple face detection handling

### 3. Traditional Authentication
- ✅ Email/password login
- ✅ Password reset functionality (admin)
- ✅ Session management

### 4. Admin Dashboard
- ✅ View all registered users
- ✅ See face registration status
- ✅ Delete user accounts
- ✅ Reset user passwords
- ✅ Statistics (total users, face registered count)

### 5. User Interface
- ✅ Responsive design
- ✅ Camera integration
- ✅ Real-time face capture
- ✅ Error handling and user feedback
- ✅ Navigation between pages

### 6. Security Features
- ✅ Password hashing
- ✅ Strict face matching thresholds
- ✅ Ambiguity detection (prevents false matches)
- ✅ CORS configuration
- ✅ Input validation

---

## Registration Process

### Step-by-Step Registration Flow

#### Phase 1: Account Creation

1. **User Action**: Navigate to registration page
   - File: `RegisterAccount.html`
   - User fills: Name, Email, Password, Confirm Password

2. **Frontend Processing**:
   ```javascript
   - Validates password match
   - Validates password length (min 6 characters)
   - Sends POST request to /api/register_account
   ```

3. **Backend Processing**:
   ```
   API Route (app.py)
       ↓
   RegistrationController.register_account()
       ↓
   UserService.register_account()
       - Validates email not already exists
       - Generates unique user_id (u_xxxxxxxx)
       - Hashes password
       - Creates User entity
       ↓
   UserRepository.save()
       - Saves to user_accounts.json
   ```

4. **Response**: Success message, choice screen appears

#### Phase 2: Face Registration (Optional)

1. **User Action**: Chooses "Yes, Register Face"
   - File: `RegisterFace.html`
   - Camera starts automatically

2. **User Action**: Clicks "Capture Face"
   - Frontend captures video frame
   - Converts to base64 image

3. **Frontend Processing**:
   ```javascript
   - Sends POST /api/register_face
   - Includes: image, email, password (for verification)
   ```

4. **Backend Processing**:
   ```
   RegistrationController.register_face()
       ↓
   UserService.login() - Verifies credentials
       ↓
   FaceRecognitionService.register_face()
       - Decodes base64 image
       - Detects face in image
       - Extracts 128-dimensional face encoding
       - Checks for duplicates (if face already registered)
       - Creates FaceEncoding entity
       ↓
   FaceRepository.save()
       - Saves encoding to known_faces.json
   UserRepository - Updates user.face_registered = True
   ```

5. **Response**: Success, redirect to login

### Data Created During Registration

**In `user_accounts.json`:**
```json
{
  "user@example.com": {
    "user_id": "u_12345678",
    "email": "user@example.com",
    "password_hash": "hashed_password",
    "name": "John Doe",
    "face_registered": true,
    "created": "2025-12-10 21:00:00"
  }
}
```

**In `known_faces.json`:**
```json
{
  "u_12345678": [0.123, -0.456, 0.789, ...]  // 128-dimensional vector
}
```

---

## Authentication Process

### Facial Recognition Authentication

#### Process Flow

1. **Face Capture**:
   ```
   User → Camera → Video Stream → Frame Capture → Base64 Image
   ```

2. **Face Encoding Extraction**:
   ```
   Base64 Image → Decode → RGB Array → Face Detection → Face Encoding (128-dim vector)
   ```

3. **Face Matching**:
   ```
   Extracted Encoding → Compare with all registered encodings → Calculate distances
   ```

4. **Decision Logic**:

   **If Multiple Faces Registered:**
   - Find best match (lowest distance)
   - Find second-best match
   - **Accept if:**
     - Best distance ≤ 0.3
     - Best match is ≥ 0.2 better than second-best
   - **Reject if:** Above conditions not met

   **If Only One Face Registered:**
   - Calculate distance to registered face
   - **Accept if:** Distance ≤ 0.25 (stricter threshold)
   - **Reject if:** Distance > 0.25

5. **Authentication Result**:
   ```
   Match Found → Get User Info → Create Session → Redirect to Home
   No Match → Show Error → User can retry or use email/password
   ```

#### Security Thresholds

- **VERIFY_THRESHOLD**: 0.3 (for multi-face scenarios)
- **SINGLE_FACE_THRESHOLD**: 0.25 (for single-face scenarios)
- **Ambiguity Check**: 0.2 difference required between best and second-best

**Distance Values:**
- 0.0 - 0.25: Excellent match ✅
- 0.25 - 0.3: Good match (rejected for single-face) ⚠️
- 0.3+: Not a match ❌

### Email/Password Authentication

#### Process Flow

1. **User Input**: Email and password entered
2. **Request**: POST `/api/login` with credentials
3. **Backend Processing**:
   ```
   AuthController.login_with_credentials()
       ↓
   UserService.login()
       - Find user by email
       - Hash provided password
       - Compare with stored hash
       - Check face_registered status
   ```
4. **Result**: Success → Session created, redirect | Failure → Error message

---

## Data Storage

### Storage Mechanism

The system uses **JSON files** for data persistence (suitable for development/demo, should use proper database in production).

### File Locations

All data files are stored in: `fyp_face_login/`

#### 1. User Accounts (`user_accounts.json`)

**Structure:**
```json
{
  "email@example.com": {
    "user_id": "u_12345678",
    "email": "email@example.com",
    "password_hash": "sha256_hash_of_password",
    "name": "User Name",
    "face_registered": true,
    "created": "2025-12-10 21:00:00"
  }
}
```

**Access**: Via `UserRepository`
- Load: `load_all()` - Returns dictionary of User entities
- Save: `save_all()` - Saves User entities to file
- Find: `find_by_email()` - Returns User entity or None
- Delete: `delete()` - Removes user from file

#### 2. Face Encodings (`known_faces.json`)

**Structure:**
```json
{
  "u_12345678": [0.123, -0.456, 0.789, ...],  // 128 numbers
  "u_87654321": [0.234, -0.567, 0.890, ...]
}
```

**Access**: Via `FaceRepository`
- Load: `load_all()` - Returns dictionary of FaceEncoding entities
- Save: `save_all()` - Saves encodings to file
- Find: `find_by_user_id()` - Returns FaceEncoding or None
- Get Arrays: `get_all_encodings_array()` - Returns numpy arrays for matching

**Note**: Face encodings are 128-dimensional vectors (numpy arrays) that represent facial features.

#### 3. Admin Configuration (`admin_config.json`)

**Structure:**
```json
{
  "admin_email": "admin@school.edu",
  "admin_password_hash": "sha256_hash"
}
```

**Access**: Via `AdminRepository`
- Load: `load()` - Returns Admin entity
- Save: `save()` - Saves admin config

**Default Credentials:**
- Email: `admin@school.edu`
- Password: `admin123`

### Data Flow Example

**When registering a face:**
```
User captures face
    ↓
Face encoding extracted (128-dim vector)
    ↓
FaceEncoding entity created
    ↓
FaceRepository.save()
    ↓
Encoding converted to list (for JSON)
    ↓
Saved to known_faces.json as: {"user_id": [0.123, -0.456, ...]}
```

**When verifying a face:**
```
User scans face
    ↓
Face encoding extracted
    ↓
FaceRepository.load_all()
    ↓
Encodings loaded from JSON → converted to numpy arrays
    ↓
face_recognition.face_distance() calculates distances
    ↓
Best match found and compared against threshold
```

### Security Considerations

- **Passwords**: Stored as SHA-256 hashes (not plaintext)
- **Face Encodings**: Stored as numerical vectors (cannot be reverse-engineered to image)
- **File Access**: Only backend can read/write (frontend has no direct access)

---

## How to Run the Program

### Prerequisites

- Python 3.13+ installed
- CMake installed (for dlib)
- Web browser with camera access

### Step 1: Install Dependencies

Dependencies are already installed in the virtual environment. If you need to reinstall:

```bash
cd FYP-Facial-Recognition-Login   # or your clone path
source venv/bin/activate
pip install -r requirements.txt
```

**Required packages:** flask, flask-cors, insightface, onnxruntime, opencv-python, numpy, torch, torchvision; optional: face-recognition, dlib (for GAN spoof crop fallback).

### Step 2: Start the Backend Server

**Option A: Manual start (from project root)**
```bash
cd FYP-Facial-Recognition-Login
source venv/bin/activate
cd fyp_face_login
python app.py
```

**Option B: From project root with module**
```bash
cd FYP-Facial-Recognition-Login
source venv/bin/activate
python -m fyp_face_login.app
```

**Expected Output:**
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:8000
 * Running on http://0.0.0.0:8000
Press CTRL+C to quit
```

**Keep this terminal window open!** The server must stay running.

### Step 3: Start the Frontend

**Option A: Using Live Server (VS Code)**
1. Open project in VS Code
2. Right-click on `home page.html`
3. Select "Open with Live Server"
4. Browser opens automatically (usually port 5500)

**Option B: Using Python HTTP Server**
```bash
# Open a NEW terminal window
cd FYP-Facial-Recognition-Login
python3 -m http.server 5500
```
Then open: `http://localhost:5500/frontend/home page.html`

**Option C: Direct File Open**
- Simply double-click `home page.html`
- Note: Some browsers may block CORS requests with this method

### Step 4: Use the Application

1. **Create Account**:
   - Click "Create Account" on home page
   - Fill in details
   - Choose to register face or skip

2. **Login**:
   - Go to login page
   - Use facial recognition OR email/password

3. **Admin Access**:
   - Click "Admin Login" on login page
   - System Admin: `system@school.edu` / `admin123`
   - Operations Admin: `operations@school.edu` / `admin123`

### Stopping the Server

Press `Ctrl+C` in the terminal where Flask is running.

### Troubleshooting

**Server won't start:**
- Check if port 8000 is already in use: `lsof -ti:8000`
- Make sure virtual environment is activated
- Verify all dependencies are installed

**Connection errors:**
- Ensure backend is running on port 8000
- Check that frontend is using HTTP (not file://)
- Verify CORS is enabled in backend

**Face recognition not working:**
- Grant camera permissions in browser
- Ensure good lighting
- Make sure only one face is visible
- Check browser console for errors

---

## API Endpoints Reference

### User Endpoints

- `POST /api/register_account` - Create new account
- `POST /api/login` - Login with email/password
- `POST /api/register_face` - Register face for account
- `POST /api/verify_face` - Login with facial recognition (returns `real_prob`, `spoof_prob` when anti-spoof runs)
- `POST /api/reset_face` - Reset facial recognition
- `GET /api/activity-log` - Recent face verification activity
- `GET /api/status` - Backend status (InsightFace, spoof backend)
- `POST /api/forgot_password` - Request password reset
- `POST /api/forgot_email` - Recover email address

### Admin Endpoints

- `POST /api/admin/login` - Admin authentication
- `GET /api/admin/users` - Get all users
- `DELETE /api/admin/users/<email>` - Delete user
- `POST /api/admin/users/<email>/reset-password` - Reset user password

### Health Check

- `GET /` - Server health check

---

## File Structure

```
FYP/
├── fyp_face_login/              # Backend (BCE Framework)
│   ├── app.py                   # Flask routes
│   ├── entities/                # Entity Layer
│   │   ├── user.py
│   │   ├── face_encoding.py
│   │   └── admin.py
│   ├── repositories/            # Repository Layer
│   │   ├── user_repository.py
│   │   ├── face_repository.py
│   │   └── admin_repository.py
│   ├── services/                # Service Layer
│   │   ├── user_service.py
│   │   ├── face_recognition_service.py
│   │   └── admin_service.py
│   ├── controllers/            # Controller Layer
│   │   ├── auth_controller.py
│   │   ├── registration_controller.py
│   │   └── admin_controller.py
│   ├── user_accounts.json       # User data
│   ├── known_faces.json         # Face encodings
│   └── admin_config.json        # Admin config
├── home page.html               # Landing page
├── RegisterAccount.html         # Account registration
├── RegisterFace.html            # Face registration
├── login.html                   # Facial recognition login
├── ManualLogin.html             # Email/password login
├── ResetFacialRecognition.html  # Reset face data
├── AdminLogin.html              # Admin login
├── AdminDashboard.html          # Admin dashboard
├── ForgotPassword.html          # Password recovery
├── ForgotEmail.html             # Email recovery
├── requirements.txt             # Python dependencies
├── start_server.sh              # Server startup script
├── README.md                    # Main documentation
├── ARCHITECTURE.md              # BCE framework details
├── AUTHENTICATION_LOGIC.md      # Auth logic explanation
└── venv/                        # Virtual environment
```

---

## Summary

This project implements a complete facial recognition authentication system using the BCE framework. It provides:

- ✅ User account management
- ✅ Facial recognition authentication
- ✅ Traditional email/password login
- ✅ Admin dashboard for user management
- ✅ Secure face matching with configurable thresholds
- ✅ Clean, maintainable code structure following BCE principles

The system is production-ready for demonstration purposes, with JSON file storage. For production deployment, consider migrating to a proper database (PostgreSQL, MySQL) and implementing additional security measures (bcrypt for passwords, HTTPS, etc.).

