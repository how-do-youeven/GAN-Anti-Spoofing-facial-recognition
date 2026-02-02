# Face Recognition Authentication Logic

## Face Recognition Engine

**Current System:** Uses **InsightFace (ArcFace)** with automatic fallback to dlib's face_recognition library.

**InsightFace Benefits:**
- ✅ **Better glasses handling** - Handles occlusions (glasses, hats) much better than dlib
- ✅ **512-dimensional embeddings** - More accurate than 128D dlib embeddings
- ✅ **Deep learning model** - Trained on large datasets with diverse face variations
- ✅ **Automatic face alignment** - Better preprocessing for recognition

**Fallback:** If InsightFace is not available, system automatically falls back to face_recognition library (dlib).

## Current Authentication Flow

### Step 1: Face Detection
1. User scans face via camera
2. System extracts face embedding:
   - **InsightFace**: 512-dimensional vector (better accuracy)
   - **dlib fallback**: 128-dimensional vector
3. Validates exactly 1 face detected

### Step 2: Face Matching
System compares scanned face against all registered faces:

**If Multiple Faces Registered:**
- Calculates distance to ALL registered faces
  - **InsightFace**: Uses cosine distance (better for glasses)
  - **dlib**: Uses euclidean distance
- Finds best match (lowest distance)
- Finds second-best match
- **Requires:**
  - Best distance ≤ 0.35 (VERIFY_THRESHOLD for InsightFace, 0.3 for dlib)
  - Best match must be ≥ 0.15 better than second-best (InsightFace) or ≥ 0.2 (dlib)
  - This ensures unambiguous match

**If Only One Face Registered:**
- Calculates distance to the single registered face
- **Requires:**
  - Distance ≤ 0.30 (SINGLE_FACE_THRESHOLD for InsightFace - more lenient for glasses)
  - Distance ≤ 0.25 (SINGLE_FACE_THRESHOLD for dlib)
  - This prevents false matches when only one face exists

### Step 3: Decision

**ACCEPT Login If:**
- Distance ≤ threshold (0.3 for multi-face, 0.25 for single-face)
- AND (if multiple faces) best match is clearly better than others

**REJECT Login If:**
- Distance > threshold
- OR (if multiple faces) match is ambiguous (distances too close)
- OR face not detected properly

## Distance Values Explained

- **0.0 - 0.25**: Perfect to excellent match ✅ (ACCEPTED)
- **0.25 - 0.3**: Good match but rejected for single-face security ⚠️
- **0.3 - 0.4**: Moderate match ❌ (REJECTED - not registered)
- **0.4 - 0.5**: Poor match ❌ (REJECTED - definitely not registered)
- **0.5+**: Very poor match ❌ (REJECTED - not registered at all)

## Security Guarantees

### ✅ Unregistered Faces Are Rejected
- If someone isn't registered, their face will have distance > 0.25-0.3
- System will reject them
- Error message: "Face not recognized"

### ✅ Ambiguous Matches Are Rejected
- If two registered faces are similar, system requires clear best match
- Prevents false positives

### ✅ Stricter for Single Face
- When only one face registered, uses 0.25 threshold (stricter)
- Prevents false matches when no comparison available

## Example Scenarios

### Scenario 1: Your Face (Registered)
- Distance: ~0.15-0.25
- Result: ✅ ACCEPTED (distance ≤ 0.25)

### Scenario 2: Girlfriend's Face (Not Registered)
- Distance: ~0.45-0.6
- Result: ❌ REJECTED (distance > 0.25)

### Scenario 3: Similar Face (Not Registered)
- Distance: ~0.35
- Result: ❌ REJECTED (distance > 0.25)

### Scenario 4: Multiple Registered Faces
- Your face distance: 0.2
- Other face distance: 0.5
- Difference: 0.3 (≥ 0.2 required)
- Result: ✅ ACCEPTED (clear best match)

## Troubleshooting

**If unregistered face still logs in:**
1. Check distance value in error message
2. If distance < 0.25, threshold may need to be lower
3. Re-register your face to ensure quality encoding
4. Check server logs for "SECURITY:" messages

**If your face is rejected:**
1. Distance might be > 0.25
2. Re-register your face with better lighting
3. Ensure face is clearly visible and centered

