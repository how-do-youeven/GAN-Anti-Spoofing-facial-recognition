# BCE Framework Architecture

This project follows the **BCE (Business-Control-Entity) Framework** architecture pattern, which separates concerns into distinct layers for better maintainability, testability, and scalability.

## Architecture Overview

```
┌─────────────────────────────────────────┐
│         API Routes (app.py)            │  ← Entry point, HTTP handling
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         Controller Layer                │  ← Flow control, coordination
│  - AuthController                       │
│  - RegistrationController               │
│  - AdminController                      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         Service Layer                   │  ← Business logic, rules
│  - UserService                          │
│  - FaceRecognitionService               │
│  - AdminService                         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         Repository Layer                │  ← Data access
│  - UserRepository                       │
│  - FaceRepository                       │
│  - AdminRepository                      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         Entity Layer                    │  ← Domain models
│  - User                                 │
│  - FaceEncoding                         │
│  - Admin                                │
└─────────────────────────────────────────┘
```

## Layer Responsibilities

### 1. Entity Layer (`entities/`)
**Purpose**: Domain models representing core business objects

- **User** (`entities/user.py`): Represents a user account
  - Properties: email, user_id, password_hash, name, face_registered, created
  - Methods: `to_dict()`, `from_dict()`

- **FaceEncoding** (`entities/face_encoding.py`): Represents facial recognition data
  - Properties: user_id, encoding (numpy array)
  - Methods: `to_dict()`, `from_dict()`

- **Admin** (`entities/admin.py`): Represents admin account
  - Properties: email, password_hash
  - Methods: `to_dict()`, `from_dict()`

### 2. Repository Layer (`repositories/`)
**Purpose**: Data access operations (database/file I/O)

- **UserRepository**: CRUD operations for User entities
  - `load_all()`, `save_all()`, `find_by_email()`, `save()`, `delete()`, `exists()`

- **FaceRepository**: CRUD operations for FaceEncoding entities
  - `load_all()`, `save_all()`, `find_by_user_id()`, `save()`, `delete()`, `exists()`
  - `get_all_encodings_array()`: Returns numpy arrays for face recognition

- **AdminRepository**: Admin configuration access
  - `load()`, `save()`

### 3. Service Layer (`services/`)
**Purpose**: Business logic and rules

- **UserService**: User-related business logic
  - `register_account()`: Validate and create new account
  - `login()`: Authenticate user credentials
  - `reset_password()`: Change user password
  - `hash_password()`, `verify_password()`: Password security
  - `generate_user_id()`: Create unique user IDs

- **FaceRecognitionService**: Face verification and anti-spoof coordination
  - Uses **InsightFace** (ArcFace 512D) for detection and matching
  - Delegates anti-spoof to **SilentFaceSpoofService** (full frame + bbox) or **SpoofDetectionService** (GAN predictor on face crop)
  - `register_face()`: Register face for user (InsightFace embedding only)
  - `verify_face()`: Verify face for login (anti-spoof then match; returns real_prob, spoof_prob)
  - `reset_face()`: Update face encoding
  - Logs to activity_log and audit_log on verify

- **SilentFaceSpoofService** (`silent_face_spoof_service.py`): Silent Face (minivision-ai) anti-spoof; full image + face bbox.

- **SpoofDetectionService** (`spoof_detection_service.py`): GAN predictor anti-spoof; pre-cropped face image.

- **AdminService**: Admin operations business logic
  - `authenticate()`: Admin login validation
  - `get_all_users()`: Retrieve all users for admin dashboard
  - `delete_user()`: Remove user account and face data
  - `reset_user_password()`: Admin password reset

### 4. Controller Layer (`controllers/`)
**Purpose**: Flow control and request/response coordination

- **AuthController**: Authentication flow
  - `login_with_credentials()`: Handle email/password login
  - `login_with_face()`: Handle facial recognition login

- **RegistrationController**: Registration flow
  - `register_account()`: Handle account creation
  - `register_face()`: Handle face registration (with credential verification)
  - `reset_face()`: Handle face reset

- **AdminController**: Admin operations flow
  - `login()`: Handle admin authentication
  - `get_all_users()`: Handle user listing
  - `delete_user()`: Handle user deletion
  - `reset_user_password()`: Handle password reset

### 5. API Routes (`app.py`)
**Purpose**: HTTP endpoint definitions

- Routes delegate to controllers
- Handle HTTP request/response
- No business logic (only routing)
- Rate limiting applied to `/api/verify_face`

### 6. Supporting modules (same package)
- **activity_log.py**: In-memory log of face verification attempts (real/spoof probs, spoof check, verification result); served at `GET /api/activity-log`.
- **audit_log.py**: Persistent file log (`audit_face.jsonl`) for verification attempts.
- **rate_limit.py**: Per-IP rate limiting for verify_face.
- **vendor/**: Vendored Silent Face crop and MiniFASNet model code.

## Benefits of BCE Framework

1. **Separation of Concerns**: Each layer has a single responsibility
2. **Testability**: Each layer can be tested independently
3. **Maintainability**: Changes in one layer don't affect others
4. **Scalability**: Easy to add new features or change implementations
5. **Reusability**: Services can be reused across different controllers
6. **Clear Structure**: Easy to understand and navigate codebase

## File Structure

```
fyp_face_login/
├── app.py                    # API routes (entry point)
├── entities/                 # Entity Layer
│   ├── __init__.py
│   ├── user.py
│   ├── face_encoding.py
│   └── admin.py
├── repositories/             # Repository Layer
│   ├── __init__.py
│   ├── user_repository.py
│   ├── face_repository.py
│   └── admin_repository.py
├── services/                 # Service Layer
│   ├── __init__.py
│   ├── user_service.py
│   ├── face_recognition_service.py
│   ├── spoof_detection_service.py   # GAN predictor
│   ├── silent_face_spoof_service.py # Silent Face anti-spoof
│   └── admin_service.py
├── vendor/                   # Vendored code (Silent Face)
├── activity_log.py           # In-memory activity log
├── audit_log.py              # Persistent audit log
└── rate_limit.py             # Per-IP rate limiting
└── controllers/             # Controller Layer
    ├── __init__.py
    ├── auth_controller.py
    ├── registration_controller.py
    └── admin_controller.py
```

## Data Flow Example: User Registration

1. **API Route** (`app.py`): Receives HTTP POST request
2. **Controller** (`RegistrationController.register_account()`): Extracts data, coordinates flow
3. **Service** (`UserService.register_account()`): Validates, applies business rules
4. **Repository** (`UserRepository.save()`): Persists data to storage
5. **Entity** (`User`): Represents the data model



