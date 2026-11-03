from pydantic import BaseModel, Field

MAX_MESSAGE_CHARS = 500   # reject overly long messages (they cost tokens)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    session_id: str | None = None


class ChatOut(BaseModel):
    session_id: str
    reply: str


class ExpertIn(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    discord_id: str = Field(min_length=1, max_length=40)
    session_id: str | None = None