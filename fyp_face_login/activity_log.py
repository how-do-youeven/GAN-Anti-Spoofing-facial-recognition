"""
In-memory activity log for face login: spoof (real/fake) and verification.
"""
import time
from collections import deque
from typing import Any, Dict

# Keep last 200 entries
_MAX_ENTRIES = 200
_log: deque = deque(maxlen=_MAX_ENTRIES)


def log(
    event: str,
    real_prob: float = None,
    spoof_prob: float = None,
    spoof_passed: bool = None,
    verify_success: bool = None,
    user_id: str = None,
    distance: float = None,
    reason: str = None,
    message: str = None,
    **kwargs: Any,
) -> None:
    """Append one activity entry (e.g. one face verification attempt)."""
    entry = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "ts": time.time(),
        "event": event,
        **kwargs,
    }
    if real_prob is not None:
        entry["real_prob"] = round(real_prob, 4)
    if spoof_prob is not None:
        entry["spoof_prob"] = round(spoof_prob, 4)
    if spoof_passed is not None:
        entry["spoof_passed"] = spoof_passed
    if verify_success is not None:
        entry["verify_success"] = verify_success
    if user_id is not None:
        entry["user_id"] = user_id
    if distance is not None:
        entry["distance"] = round(distance, 4) if distance != int(distance) else distance
    if reason is not None:
        entry["reason"] = reason
    if message is not None:
        entry["message"] = message
    _log.append(entry)


def get_recent(limit: int = 100) -> list:
    """Return most recent entries (newest first)."""
    out = list(_log)
    out.reverse()
    return out[:limit]


def clear() -> None:
    """Clear the log."""
    _log.clear()
