"""
Persistent audit log for face verification attempts.
Appends one JSON line per attempt to a file (audit_face.jsonl).
"""
import json
import os
import time
from typing import Any, Optional

# Default path: same directory as this module, then 'audit_face.jsonl'
_AUDIT_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_FILE = os.environ.get("FACE_AUDIT_LOG_PATH", os.path.join(_AUDIT_DIR, "audit_face.jsonl"))


def log_verification(
    ip: str,
    success: bool,
    user_id: Optional[str] = None,
    reason: Optional[str] = None,
    distance: Optional[float] = None,
    real_prob: Optional[float] = None,
    spoof_prob: Optional[float] = None,
    extra: Optional[dict] = None,
) -> None:
    """Append one verification attempt to the audit log (JSONL)."""
    if os.environ.get("FACE_AUDIT_LOG_DISABLED", "").strip().lower() in ("1", "true", "yes"):
        return
    entry = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ts": time.time(),
        "ip": ip,
        "success": success,
        "user_id": user_id,
        "reason": reason,
        "distance": distance,
        "real_prob": real_prob,
        "spoof_prob": spoof_prob,
    }
    if extra:
        entry["extra"] = extra
    try:
        with open(AUDIT_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"WARNING: Could not write audit log: {e}")
