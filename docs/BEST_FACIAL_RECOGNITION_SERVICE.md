# Best Possible Facial Recognition Service (Target Design)

This document describes the **best service we can build** in this project: accuracy, security, reliability, and operability.

---

## 1. Recognition pipeline (accuracy)

| Layer | Best choice | What we have / can add |
|-------|-------------|-------------------------|
| **Detection** | InsightFace RetinaFace (in FaceAnalysis) | ✅ Already (buffalo_l / antelopev2). |
| **Embedding** | InsightFace ArcFace 512D | ✅ Already. |
| **Anti-spoof** | Silent Face (silent liveness) | ✅ When models present; else GAN. |
| **Matching** | Cosine distance, tuned threshold | ✅ 0.38; make configurable. |
| **Quality gate** | Blur + size + lighting checks before accepting registration | ➕ Add. |

**Improvements:**

- **Registration quality gate:** Reject bad photos (blur, too small, too dark/bright) so we never store weak templates.
- **Configurable thresholds:** `VERIFY_THRESHOLD`, `SAME_FACE_THRESHOLD` from env/config so you can tune without code change.
- **GPU when available:** Use `CUDAExecutionProvider` for InsightFace when possible (faster, same accuracy).

---

## 2. Security

| Concern | Best practice | What we can do here |
|---------|----------------|---------------------|
| **Spoofing** | Liveness + anti-spoof model | ✅ Silent Face or GAN. |
| **Template protection** | Store only embeddings, optional encryption | ✅ Embeddings only; optional encrypt at rest. |
| **Brute-force** | Rate limit verify attempts | ➕ Add per-IP or per-account rate limit. |
| **Audit** | Log all verification attempts (success/fail, reason) | ➕ Persist to file or DB. |
| **Face login lockout** | Disable after N failures | ✅ Already (5 failures). |

**Improvements:**

- **Rate limiting:** Limit calls to `/api/verify_face` per IP (and optionally per user) to slow down enumeration.
- **Audit log:** Append each verify attempt (timestamp, success, user_id, reason, distance) to a file or table for review.

---

## 3. Reliability and operations

| Area | Best practice | What we can do |
|------|----------------|----------------|
| **Model load** | Clear error if InsightFace fails; optional dlib fallback for verify only | ✅ Init fallback; registration requires InsightFace. |
| **Storage** | Durable, backup-friendly | ✅ JSON file; document backup. |
| **Health** | Expose model status and version | ➕ `/api/status` with model name and embedding type. |
| **Config** | No hardcoded magic numbers | ➕ Env vars for thresholds and paths. |

---

## 4. User experience

| Area | Best practice | What we have / can add |
|------|----------------|-------------------------|
| **Feedback** | “Move closer”, “Better lighting”, “One face only” | ✅ Reason codes; frontend can map to messages. |
| **Activity log** | Real-time view of attempts and scores | ✅ Activity log page. |
| **Registration** | Only accept good-quality faces | ➕ Quality gate (blur/size/light). |

---

## 5. Target architecture (best we can build here)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (browser)                          │
│  Login page │ Register face │ Activity log │ Admin               │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Flask API (this app)                         │
│  /api/verify_face │ /api/register_face │ /api/status │ ...       │
│  + rate limiting  + audit log write                              │
└─────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ FaceRecognition│         │ SpoofDetection  │         │ FaceRepository  │
│ Service       │         │ (Silent Face /  │         │ (known_faces    │
│               │         │  GAN)            │         │  .json)         │
│ • InsightFace │         │                 │         │                 │
│   ArcFace     │         │ Real vs spoof   │         │ 512D + metadata │
│ • Quality gate│         │                 │         │ optional encrypt│
│ • Configurable│         │                 │         │                 │
│   thresholds  │         │                 │         │                 │
└───────────────┘         └─────────────────┘         └─────────────────┘
        │
        ▼
┌───────────────┐         ┌─────────────────┐
│ Audit log     │         │ Activity log    │
│ (persistent) │         │ (in-memory, UI)  │
└───────────────┘         └─────────────────┘
```

---

## 6. Implementation checklist

- [x] InsightFace ArcFace only for registration and verification  
- [x] Silent Face / GAN anti-spoof at login  
- [x] Stored format: 512D + embedding_type + embedding_dim  
- [x] Activity log (real-time)  
- [x] **Registration quality gate** (blur, min size, brightness)  
- [x] **Configurable thresholds** (env)  
- [x] **GPU provider** when available (CUDA then CPU fallback)  
- [x] **Status endpoint** with model name and embedding_type  
- [x] **Rate limiting** on verify_face (per-IP, configurable)  
- [x] **Persistent audit log** (file: `audit_face.jsonl`)  

## 7. Environment variables (tuning)

| Variable | Default | Description |
|----------|---------|-------------|
| `FACE_VERIFY_THRESHOLD` | 0.38 | Max cosine distance to accept a match at login. Lower = stricter. |
| `FACE_SAME_THRESHOLD` | 0.35 | Max distance to consider "same face" (duplicate check at registration). |
| `FACE_USE_CPU` | (unset) | Set to `1` or `true` to force CPU; otherwise GPU is tried first. |
| `FACE_MIN_LAPLACIAN_VAR` | 100 | Min Laplacian variance (blur). Lower = allow more blur. |
| `FACE_MIN_FACE_SIZE_REG` | 80 | Min image side (px) for registration. |
| `FACE_MIN_BRIGHTNESS` | 40 | Min mean brightness (0–255). |
| `FACE_MAX_BRIGHTNESS` | 220 | Max mean brightness (0–255). |
| `FACE_RATE_LIMIT_PER_MIN` | 20 | Max verify_face requests per IP per minute. |
| `FACE_RATE_LIMIT_DISABLED` | (unset) | Set to `1` or `true` to disable rate limiting. |
| `FACE_AUDIT_LOG_PATH` | `fyp_face_login/audit_face.jsonl` | Path to the audit JSONL file. |
| `FACE_AUDIT_LOG_DISABLED` | (unset) | Set to `1` or `true` to disable writing the audit log. |

**Rate limiting:** Each IP is limited to `FACE_RATE_LIMIT_PER_MIN` requests per minute to `/api/verify_face`. When exceeded, the API returns `429 Too Many Requests` with a `Retry-After` header. Client IP is taken from `X-Forwarded-For` (if set) or `request.remote_addr`.

**Audit log:** Every call to `/api/verify_face` appends one line to the audit file (JSONL). Each line has `time`, `ip`, `success`, `user_id`, `reason`, `distance`. Use it for security review and analytics. The file path is `FACE_AUDIT_LOG_PATH` (default: `fyp_face_login/audit_face.jsonl`); it is listed in `.gitignore`.
