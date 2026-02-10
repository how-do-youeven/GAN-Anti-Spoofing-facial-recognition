# Facial Recognition Service (InsightFace ArcFace)

This app implements a **full facial recognition service** using **InsightFace ArcFace** for both registration and verification. Face data is stored as 512-dimensional ArcFace embeddings.

## Pipeline

| Step | Component | Role |
|------|-----------|------|
| **Registration** | InsightFace `FaceAnalysis` | Detect face → extract **512D ArcFace embedding** → store (no spoof check at registration). |
| **Storage** | `FaceRepository` + `FaceEncoding` | One record per user: `encoding` (512 floats), optional `image_b64`, metadata `embedding_type` / `embedding_dim`. |
| **Verification (login)** | InsightFace + anti-spoof | Detect face → **anti-spoof** (Silent Face or GAN) → extract 512D embedding → **match** against stored embeddings (cosine distance). |

## Registration

- **Requires InsightFace.** If InsightFace is not loaded, registration returns an error and no face is stored.
- **Single face per image.** Multiple faces in the image are rejected.
- **Duplicate check.** New embedding is compared to all stored 512D embeddings (cosine distance). If too close to another user’s face, registration is rejected.
- **Stored data:** Only the **InsightFace ArcFace 512D** vector is stored (plus optional registration image). No dlib embeddings are written for new registrations.

## Storage format

**File:** `known_faces.json` (path set in `FaceRepository`).

**Per-user record:**

```json
{
  "user_id": "<uuid>",
  "encoding": [0.012, -0.034, ...],
  "embedding_type": "insightface_arcface",
  "embedding_dim": 512,
  "image_b64": "data:image/jpeg;base64,...",
  "encoding_dlib": null
}
```

- **`encoding`** – 512-dimensional InsightFace ArcFace embedding (list of floats).
- **`embedding_type`** – `"insightface_arcface"` for current registrations.
- **`embedding_dim`** – `512`.
- **`image_b64`** – Optional; registration image for display/admin.
- **`encoding_dlib`** – Legacy 128D dlib; not used for new registrations, may exist for old data.

## Verification (login)

1. **Face detection** – InsightFace detects the face and returns a bounding box and 512D embedding.
2. **Anti-spoof** – Silent Face (or GAN predictor) decides real vs spoof; spoof → login rejected.
3. **Matching** – The 512D embedding is compared to all stored `encoding` vectors using **cosine distance**. If the best match is below the threshold (0.38) and sufficiently better than the second-best, login succeeds for that user.

## Code locations

- **Entity:** `fyp_face_login/entities/face_encoding.py` – `FaceEncoding`, `EMBEDDING_TYPE`, `EMBEDDING_DIM`.
- **Repository:** `fyp_face_login/repositories/face_repository.py` – load/save `known_faces.json`.
- **Service:** `fyp_face_login/services/face_recognition_service.py` – `register_face()` (InsightFace only), `verify_face()`, `_verify_with_embedding()`.

## Dependencies

- **insightface** – Face detection + ArcFace 512D embedding.
- **onnxruntime** – Required by InsightFace for inference.
- Models (e.g. buffalo_l, antelopev2) are downloaded on first use when InsightFace runs.
