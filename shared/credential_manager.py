from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class CredentialManager:
    def __init__(self, rotation_interval_days: int = 90):
        self.rotation_interval_days = rotation_interval_days
        self.last_rotation: datetime = datetime.now(timezone.utc)
        self.rotation_history: List[Dict] = []
        self._current_creds_summary: Optional[str] = None

    def should_rotate(self) -> bool:
        now = datetime.now(timezone.utc)
        days_elapsed = (now - self.last_rotation).total_seconds() / 86400
        return days_elapsed >= self.rotation_interval_days

    def rotate_credentials(self, new_creds: Optional[Dict] = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        previous_summary = self._current_creds_summary

        if new_creds is not None:
            keys = list(new_creds.keys()) if isinstance(new_creds, dict) else []
            self._current_creds_summary = f"keys={keys}"

        record: Dict[str, Any] = {
            "timestamp": now.isoformat(),
            "previous_creds_summary": previous_summary,
            "new_creds_summary": self._current_creds_summary,
            "status": "manual" if new_creds is not None else "success",
        }
        self.rotation_history.append(record)
        self.last_rotation = now

        return {
            "rotated_at": now.isoformat(),
            "status": record["status"],
            "days_until_next_rotation": self.rotation_interval_days,
        }

    def get_rotation_info(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        days_since = (now - self.last_rotation).total_seconds() / 86400

        return {
            "last_rotation": self.last_rotation.isoformat(),
            "days_since_last_rotation": round(days_since, 2),
            "should_rotate": self.should_rotate(),
            "rotation_interval_days": self.rotation_interval_days,
            "total_rotations": len(self.rotation_history),
        }

    def get_history(self) -> List[Dict]:
        return list(self.rotation_history)
