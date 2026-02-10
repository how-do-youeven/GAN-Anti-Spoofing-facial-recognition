# Face Recognition Authentication Logic

## Stack Overview

| Role | Technology | Purpose |
|------|------------|---------|
| **Anti-spoofing** | **Silent Face** (minivision-ai) | Silent liveness: detect real face vs photo/screen spoof. Uses full frame + face bbox. |
| **Fallback anti-spoof** | GAN predictor (ResNet18) | If Silent Face models are not set up, uses pre-cropped face crop. |
| **Verification** | **InsightFace ArcFace** | 512D embeddings, cosine distance; single source of truth for “who is this?” |

**InsightFace (ArcFace) benefits:**
- 512-dimensional embeddings, state-of-the-art accuracy
- Good handling of glasses and occlusions
- Used for both face detection (bbox for Silent Face) and identity verification

**Silent Face:** Silent liveness (no gestures); when available the app uses it on the full image with the face bbox from InsightFace. If Silent Face model files are not present, the app falls back to the GAN-based spoof detector on a face crop.

## Current Authentication Flow

### Step 1: Face detection (InsightFace)
1. User scans face via camera.
2. InsightFace detects face(s) and returns bbox + 512D embedding.
3. Exactly one face required; largest face used if multiple.

### Step 2: Anti-spoofing
- **If Silent Face is active:** Run Silent Face on full frame + InsightFace bbox → real vs spoof.
- **Else (GAN):** Crop face (dlib locations), run GAN predictor on crop → real vs spoof.
- If classified as spoof → login rejected (distance = -1.0).

### Step 3: Face matching (InsightFace ArcFace only)
System compares the 512D embedding to all registered faces (cosine distance):

**If multiple faces registered:**
- Best distance ≤ VERIFY_THRESHOLD (0.38)
- Best match ≥ 0.15 better than second-best (unambiguous match)

**If only one face registered:**
- Distance ≤ SINGLE_FACE_THRESHOLD (0.38)

### Step 4: Decision

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

## Optional: Silent Face anti-spoofing setup

To use **Silent Face** for anti-spoofing (silent liveness):

1. Clone [minivision-ai/Silent-Face-Anti-Spoofing](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing) next to or inside the project.
2. Download the anti-spoof `.pth` models (see that repo’s README; e.g. Baidu link or `resources/anti_spoof_models`).
3. Point the app at the model directory, or place models in:
   `Silent-Face-Anti-Spoofing/resources/anti_spoof_models/`.

If the directory or `.pth` files are missing, the app uses the GAN predictor (face-crop spoof detection) instead.
