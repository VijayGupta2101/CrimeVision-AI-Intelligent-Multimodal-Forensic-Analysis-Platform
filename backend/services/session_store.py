"""In-memory analysis session storage."""

from copy import deepcopy
from threading import RLock


class SessionStore:
    def __init__(self):
        self._sessions = {}
        self._lock = RLock()

    def create_session(self, session_id, data=None):
        with self._lock:
            self._sessions[session_id] = deepcopy(data or {})
            return True

    def update_session(self, session_id, data):
        with self._lock:
            self._sessions.setdefault(session_id, {})
            self._sessions[session_id].update(deepcopy(data))
            return True

    def get_session(self, session_id):
        with self._lock:
            value = self._sessions.get(session_id)

            if value is None:
                return None

            return deepcopy(value)

    def delete_session(self, session_id):
        with self._lock:
            return self._sessions.pop(session_id, None) is not None


session_store = SessionStore()