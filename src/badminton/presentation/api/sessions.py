import threading
import time
import uuid

MAX_USER_TURNS = 20       # maximum user turns per session
SESSION_TTL_SEC = 30 * 60
MAX_SESSIONS = 100
MAX_EXPERT_PER_SESSION = 3


class Session:
    def __init__(self):
        self.messages: list = []
        self.turns = 0
        self.expert_sent = 0
        self.last_used = time.time()
        self.lock = threading.Lock()


_sessions: dict[str, Session] = {}
_sessions_lock = threading.Lock()


def get_or_create(session_id: str | None) -> tuple[str, Session]:
    now = time.time()
    with _sessions_lock:
        for sid in [s for s, v in _sessions.items() if now - v.last_used > SESSION_TTL_SEC]:
            del _sessions[sid]
        if session_id in _sessions:
            return session_id, _sessions[session_id]
        if len(_sessions) >= MAX_SESSIONS:
            oldest = min(_sessions, key=lambda s: _sessions[s].last_used)
            del _sessions[oldest]
        sid = uuid.uuid4().hex
        _sessions[sid] = Session()
        return sid, _sessions[sid]


def find(session_id: str | None) -> Session | None:
    """Lookup only, never creates a session."""
    if not session_id:
        return None
    with _sessions_lock:
        return _sessions.get(session_id)


def clear() -> None:   # for tests
    with _sessions_lock:
        _sessions.clear()