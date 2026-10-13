"""FastAPI bọc chat_turn. Chạy từ thư mục gốc: uvicorn api:app --app-dir src"""
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi import Query
from catalog import list_rackets, SORTS
from clean_rackets import ALLOWED
from pydantic import BaseModel, Field
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from agent import chat_turn

WEB_DIR = Path(__file__).resolve().parent.parent / "web" 

MAX_MESSAGE_CHARS = 500   # chặn tin nhắn quá dài (tốn token)
MAX_USER_TURNS = 1       # số lượt người dùng tối đa mỗi session
SESSION_TTL_SEC = 30 * 60
MAX_SESSIONS = 100

app = FastAPI(title="Badminton Advisor")


class Session:
    def __init__(self):
        self.messages: list = []
        self.turns = 0
        self.last_used = time.time()
        self.lock = threading.Lock()


_sessions: dict[str, Session] = {}
_sessions_lock = threading.Lock()


def _get_session(session_id: str | None) -> tuple[str, Session]:
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

def _enum(col: str, vals: list[str]) -> list[str]:
    bad = [v for v in vals if v not in ALLOWED[col]]
    if bad:
        raise HTTPException(status_code=422, detail=f"{col} không hợp lệ : {bad}")
    return vals


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    session_id: str | None = None


class ChatOut(BaseModel):
    session_id: str
    reply: str


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/rackets")
def rackets(
    q: str | None = Query(None, max_length=100),
    brand: list[str] = Query(default=[]),
    level: list[str] = Query(default=[]),
    play_style: list[str] = Query(default=[]),
    balance: list[str] = Query(default=[]),
    stiffness: list[str] = Query(default=[]),
    weight_class: list[str] = Query(default=[]),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    sort: str = "price_asc",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    if sort not in SORTS:
        raise HTTPException(status_code=422, detail=f"sort không hợp lệ: {sorted(SORTS)}")
    filters = {c: _enum(c,v) for c, v in (
        ("level", level),("play_style", play_style),("balance", balance),("stiffness", stiffness), ("weight_class", weight_class)
    )}
    return list_rackets(q=q, brands=brand, filters=filters, min_price=min_price, max_price=max_price, sort=sort, limit=limit, offset=offset)

@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn):
    text = body.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Tin nhắn trống.")

    sid, session = _get_session(body.session_id)
    with session.lock:
        if session.turns >= MAX_USER_TURNS:
            raise HTTPException(status_code=429, detail="Hội thoại đã đạt giới hạn lượt, hãy bắt đầu hội thoại mới.")
        working = list(session.messages)          # bản sao: lỗi giữa chừng không làm hỏng session
        working.append({"role": "user", "content": text})
        try:
            reply = chat_turn(working)
        except Exception as e:
            print(f"[error] {type(e).__name__}: {e}")
            raise HTTPException(status_code=502, detail="Lỗi khi gọi mô hình, thử lại sau.")
        session.messages = working                # chỉ ghi khi cả lượt thành công
        session.turns += 1
        session.last_used = time.time()
    return ChatOut(session_id=sid, reply=reply)


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")