"""
Simple per-IP rate limiter for /api/verify_face.
Configurable via FACE_RATE_LIMIT_PER_MIN and FACE_RATE_LIMIT_DISABLED.
"""
import os
import time
from collections import defaultdict
from typing import Tuple

# Default: 20 verify attempts per IP per minute
LIMIT_PER_MINUTE = int(os.environ.get("FACE_RATE_LIMIT_PER_MIN", "20"))
DISABLED = os.environ.get("FACE_RATE_LIMIT_DISABLED", "").strip().lower() in ("1", "true", "yes")

_store: defaultdict = defaultdict(list)
_WINDOW_SEC = 60.0


def _prune(ts_list: list) -> list:
    now = time.time()
    return [t for t in ts_list if now - t < _WINDOW_SEC]


def check_rate_limit(ip: str) -> Tuple[bool, float]:
    """
    Returns (allowed, retry_after_seconds).
    retry_after_seconds is 0 if allowed, else seconds until a slot frees up.
    """
    if DISABLED:
        return True, 0.0
    now = time.time()
    _store[ip] = _prune(_store[ip])
    if len(_store[ip]) < LIMIT_PER_MINUTE:
        _store[ip].append(now)
        return True, 0.0
    oldest = min(_store[ip])
    retry_after = max(0.0, _WINDOW_SEC - (now - oldest))
    return False, retry_after
