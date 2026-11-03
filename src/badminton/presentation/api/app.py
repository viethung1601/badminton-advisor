import time

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from badminton.config import ROOT
from badminton.container import get_usecases
from badminton.domain.contracts import (
    RACKET_ALLOWED, RACKET_SORTS, SHOE_ALLOWED, SHOE_SORTS,
)
from badminton.presentation.agent import chat_turn
from badminton.presentation.api import expert, sessions
from badminton.presentation.api.schemas import ChatIn, ChatOut, ExpertIn

load_dotenv(ROOT / ".env")

app = FastAPI(title="Badminton Advisor")


def _enum(col: str, vals: list[str], allowed: dict) -> list[str]:
    bad = [v for v in vals if v not in allowed[col]]
    if bad:
        raise HTTPException(status_code=422, detail=f"Invalid {col}: {bad}")
    return vals


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
    if sort not in RACKET_SORTS:
        raise HTTPException(
            status_code=422, detail=f"Invalid sort, allowed: {sorted(RACKET_SORTS)}")
    filters = {c: _enum(c, v, RACKET_ALLOWED) for c, v in (
        ("level", level), ("play_style", play_style), ("balance", balance),
        ("stiffness", stiffness), ("weight_class", weight_class),
    )}
    return get_usecases().list_rackets(
        q=q, brands=brand, filters=filters, min_price=min_price,
        max_price=max_price, sort=sort, limit=limit, offset=offset)


@app.get("/shoes")
def shoes(
    q: str | None = Query(None, max_length=100),
    brand: list[str] = Query(default=[]),
    gender: list[str] = Query(default=[]),
    width: list[str] = Query(default=[]),
    size_eu: float | None = Query(None, ge=30, le=55),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    max_weight_g: float | None = Query(None, gt=0),
    sort: str = "price_asc",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    if sort not in SHOE_SORTS:
        raise HTTPException(
            status_code=422, detail=f"Invalid sort, allowed: {sorted(SHOE_SORTS)}")
    filters = {c: _enum(c, v, SHOE_ALLOWED)
               for c, v in (("gender", gender), ("width", width))}
    return get_usecases().list_shoes(
        q=q, brands=brand, filters=filters, size_eu=size_eu, min_price=min_price,
        max_price=max_price, max_weight_g=max_weight_g, sort=sort,
        limit=limit, offset=offset)


@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn):
    text = body.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message.")

    sid, session = sessions.get_or_create(body.session_id)
    with session.lock:
        if session.turns >= sessions.MAX_USER_TURNS:
            raise HTTPException(
                status_code=429,
                detail="This conversation has reached its turn limit. Please start a new one.")
        # work on a copy: an error midway must not corrupt the session
        working = list(session.messages)
        working.append({"role": "user", "content": text})
        try:
            reply = chat_turn(working)
        except Exception as e:
            print(f"[error] {type(e).__name__}: {e}")
            raise HTTPException(
                status_code=502, detail="Error while calling the model. Please try again later.")
        session.messages = working          # write back only if the whole turn succeeded
        session.turns += 1
        session.last_used = time.time()
    return ChatOut(session_id=sid, reply=reply)


@app.post("/ask-expert")
def ask_expert(body: ExpertIn):
    question = body.question.strip()
    discord_id = body.discord_id.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Empty question.")
    if not expert.DISCORD_ID_RE.fullmatch(discord_id):
        raise HTTPException(status_code=422, detail="Invalid Discord ID.")
    url = expert.webhook_url()
    if not url:
        raise HTTPException(
            status_code=503, detail="The ask-an-expert feature is not configured.")

    session = sessions.find(body.session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please chat again, then resubmit.")

    with session.lock:
        if session.expert_sent >= sessions.MAX_EXPERT_PER_SESSION:
            raise HTTPException(
                status_code=429,
                detail="You have reached the maximum number of expert questions for this session.")
        try:
            expert.post_question(url, question, discord_id)
        except httpx.HTTPError as e:
            # do not log the question or any email
            print(f"[error] ask-expert: {type(e).__name__}")
            raise HTTPException(
                status_code=502, detail="Could not send the question. Please try again later.")
        session.expert_sent += 1
        session.last_used = time.time()
    return {"status": "sent"}


# must stay last: the "/" mount would shadow routes registered after it
app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")