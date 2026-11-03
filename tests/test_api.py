import pytest
from fastapi.testclient import TestClient

import badminton.presentation.api.app as api_app
from badminton.presentation.api import expert, sessions

client = TestClient(api_app.app)


@pytest.fixture(autouse=True)
def _clean_sessions():
    sessions.clear()
    yield
    sessions.clear()


def _fake_turn(messages):
    messages.append({"role": "assistant", "content": "hi"})
    return "hi"


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_rackets_validation():
    assert client.get("/rackets?sort=bogus").status_code == 422
    assert client.get("/rackets?level=bogus").status_code == 422
    assert client.get("/rackets?limit=5").status_code == 200


def test_chat_keeps_history_per_session(monkeypatch):
    seen = []
    def fake(messages):
        seen.append(len(messages))
        return _fake_turn(messages)
    monkeypatch.setattr(api_app, "chat_turn", fake)
    sid = client.post("/chat", json={"message": "a"}).json()["session_id"]
    client.post("/chat", json={"message": "b", "session_id": sid})
    assert seen == [1, 3]


def test_chat_error_does_not_corrupt_session(monkeypatch):
    monkeypatch.setattr(api_app, "chat_turn", _fake_turn)
    sid = client.post("/chat", json={"message": "a"}).json()["session_id"]
    def boom(messages):
        raise RuntimeError("x")
    monkeypatch.setattr(api_app, "chat_turn", boom)
    r = client.post("/chat", json={"message": "b", "session_id": sid})
    assert r.status_code == 502
    s = sessions.find(sid)
    assert s.turns == 1 and len(s.messages) == 2


def test_chat_turn_limit(monkeypatch):
    monkeypatch.setattr(api_app, "chat_turn", _fake_turn)
    monkeypatch.setattr(sessions, "MAX_USER_TURNS", 1)
    sid = client.post("/chat", json={"message": "a"}).json()["session_id"]
    r = client.post("/chat", json={"message": "b", "session_id": sid})
    assert r.status_code == 429


GOOD = {"question": "Which racket?", "discord_id": "123456789012345678"}


def test_expert_not_configured(monkeypatch):
    monkeypatch.delenv("N8N_WEBHOOK_URL", raising=False)
    assert client.post("/ask-expert", json=GOOD).status_code == 503


def test_expert_flow(monkeypatch):
    monkeypatch.setenv("N8N_WEBHOOK_URL", "http://example.invalid/hook")
    assert client.post("/ask-expert", json={**GOOD, "discord_id": "abc"}).status_code == 422
    assert client.post("/ask-expert", json=GOOD).status_code == 404   # no session

    monkeypatch.setattr(api_app, "chat_turn", _fake_turn)
    sid = client.post("/chat", json={"message": "a"}).json()["session_id"]

    sent = []
    monkeypatch.setattr(expert, "post_question", lambda url, q, d: sent.append((q, d)))
    for _ in range(3):
        assert client.post("/ask-expert", json={**GOOD, "session_id": sid}).status_code == 200
    assert client.post("/ask-expert", json={**GOOD, "session_id": sid}).status_code == 429
    assert len(sent) == 3