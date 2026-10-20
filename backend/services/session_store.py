"""Persistent session storage for CrimeVision AI."""

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
SESSION_DIR = Path(
    os.getenv("CRIMEVISION_SESSION_DIR", str(BASE_DIR / "temp" / "sessions"))
)
SESSION_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.RLock()
_sessions: dict[str, dict[str, Any]] = {}


class SessionStore:
    """Store forensic analysis results in memory and JSON files."""

    def __init__(self, storage_dir: Path = SESSION_DIR):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def create_session(self, data: dict[str, Any]) -> str:
        """Create and persist a new analysis session."""
        session_id = str(uuid.uuid4())

        entry = {
            "session_id": session_id,
            "created_at": time.time(),
            "data": data,
        }

        with self._lock:
            self._sessions[session_id] = entry
            self._write_session(session_id, entry)

        return session_id

    def save_session(
        self,
        session_id: str,
        data: dict[str, Any],
    ) -> bool:
        """Save or update an existing session."""
        if not session_id or not isinstance(data, dict):
            return False

        with self._lock:
            existing = self.get_session(session_id)

            if existing is None:
                entry = {
                    "session_id": session_id,
                    "created_at": time.time(),
                    "data": data,
                }
            else:
                entry = existing
                entry["data"] = data
                entry["updated_at"] = time.time()

            self._sessions[session_id] = entry
            self._write_session(session_id, entry)

        return True

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve a session, loading it from disk if necessary."""
        if not session_id:
            return None

        with self._lock:
            entry = self._sessions.get(session_id)

            if entry is None:
                path = self._session_path(session_id)

                if not path.is_file():
                    return None

                try:
                    with path.open("r", encoding="utf-8") as file:
                        entry = json.load(file)
                except (OSError, json.JSONDecodeError):
                    return None

                self._sessions[session_id] = entry

            data = entry.get("data", {})

            if not isinstance(data, dict):
                return None

            # Return analysis data directly for chatbot compatibility.
            result = dict(data)
            result.setdefault("session_id", session_id)
            result.setdefault("created_at", entry.get("created_at"))
            return result

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from memory and disk."""
        with self._lock:
            self._sessions.pop(session_id, None)
            path = self._session_path(session_id)

            try:
                if path.exists():
                    path.unlink()
                return True
            except OSError:
                return False

    def _session_path(self, session_id: str) -> Path:
        """Build a safe filename for a session ID."""
        safe_id = str(session_id)

        if not safe_id or any(
            character not in
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
            for character in safe_id
        ):
            raise ValueError("Invalid session ID.")

        return self.storage_dir / f"{safe_id}.json"

    def _write_session(
        self,
        session_id: str,
        entry: dict[str, Any],
    ) -> None:
        """Write session JSON safely using a temporary file."""
        path = self._session_path(session_id)
        temporary_path = path.with_suffix(".tmp")

        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(
                entry,
                file,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        temporary_path.replace(path)


# Shared session-store instance.
session_store = SessionStore()


# Module-level functions used by existing services.
def create_session(data: dict[str, Any]) -> str:
    return session_store.create_session(data)


def save_session(session_id: str, data: dict[str, Any]) -> bool:
    return session_store.save_session(session_id, data)


def get_session(session_id: str) -> dict[str, Any] | None:
    return session_store.get_session(session_id)


def delete_session(session_id: str) -> bool:
    return session_store.delete_session(session_id)