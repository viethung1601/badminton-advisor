import os
import re

import httpx

# [0-9], not \d, because \d also matches other Unicode digits
DISCORD_ID_RE = re.compile(r"[0-9]{17,20}")


def webhook_url() -> str | None:
    return os.getenv("N8N_WEBHOOK_URL")   # set only in .env


def post_question(url: str, question: str, discord_id: str) -> None:
    """Raises httpx.HTTPError on failure."""
    r = httpx.post(
        url,
        json={
            "question": question,
            "discord_id": discord_id,
            # built by the server so users cannot inject their own link
            "discord_url": f"https://discord.com/users/{discord_id}",
        },
        timeout=10,
    )
    r.raise_for_status()