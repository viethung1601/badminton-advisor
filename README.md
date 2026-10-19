# Badminton Advisor

A gear advisor for badminton players. Currently it recommends rackets; shoes and shuttles are planned.

## Who is it for?

Beginner, intermediate and advanced players who want to upgrade their gear but are unsure which racket, shoes or shuttles suit them.

## How do users filter?

Self-estimated level (a future version may estimate it from uploaded videos), play style (aggressive attack, attack, control, defense, balance...), budget, grip strength, colors, etc.

## What does the user get?

The 3 best options for the item they ask about.

## Limits of the recommender

- Content-based ranking (weighted Manhattan distance); no model is trained on data.
- The weights and the `min_score` threshold are set by the author from badminton knowledge and have not been validated with user feedback.
- Small dataset (26 rackets): some level × style × balance combinations are empty. In that case `status = "approximate"`.
- Many rackets can tie at 1.0; the order currently depends only on ascending price.

## Agent evaluation

The test suite `src/eval_agent.py` has 18 questions in 6 groups (complete information, missing information, lookup by racket name, value ranges, budget too low, off-topic), each run 5 times. It checks facts, not exact wording: whether the tool was called, whether the arguments are correct, and whether racket names and numbers in the answer appear in the tool result (or in the question).

**Result:** 90/90 runs passed. This does not mean the true error rate is zero; with 90 runs we can only say the error rate on this question set is low (roughly under 3%).

**Bugs found and fixed thanks to the test suite:**
- Low budget: the bot stated a budget level that is not in the data (~9% of runs, group E). Fixed in 3 rounds: a prompt instruction, then adding the lowest price to the tool result, then adding that racket's details (level, style, `is_exact`) so the bot no longer calls an approximate match "suitable".
- Lookup by name: the tool missed when the user typed the brand together with the name. Fixed the SQL query.

**Limits:**
- "Close enough" depends on `MIN_SCORE = 0.5` and author-chosen weights, not on an objective truth. With this threshold, a racket for a lower level can appear in the "closest" list of an advanced player.
- The script checks numbers and racket names, not the wording of descriptions. Wording errors (such as calling an approximate racket "suitable") only show up when reading real answers.

## Embedding model evaluation

- Retrieval: 10/11 on a self-written set of 11 questions. The remaining failure: "nhẹ đầu hợp với ai" ("who suits a head-light racket") ranks k02 fifth.

## Answer correctness against knowledge.csv

- Groups A-F: 95/95 after adding RAG (same as before RAG, so no regression on this set).
- Group G: 40/40 on 8 questions × 5 runs, after fixes to k02, k09 and the tool description.
- Retrieval alone (`probe_eval`): 10/11. The remaining failure is "nhẹ đầu hợp với ai", which ranks k02 fifth.
- Note: D2 fluctuates between 7/10 and 10/10 across runs, even before RAG. A before/after baseline exists only for G3; the other groups have none.
- Overall: 135/135 does not mean zero errors. The knowledge source is shop blogs, and there are no real users yet.

## Ask an expert (n8n + Discord)

Users can send a question to a human expert from the web page. The question goes through n8n into a private Discord channel.

```
Browser ("Send to expert" button)
  -> POST /ask-expert (FastAPI)
  -> n8n webhook /webhook/ask-expert
  -> HTTP Request -> Discord #expert-inbox
```

The expert answers publicly in `#hỏi-đáp` and tags the asker (this step is manual).

### Run n8n

```bash
docker run -d --name n8n -p 5678:5678 \
  -e GENERIC_TIMEZONE=Europe/Berlin \
  -e TZ=Europe/Berlin \
  -v n8n_data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n
```

The volume keeps workflows when the container is stopped or removed. Open http://localhost:5678.

### Import the workflow

1. In n8n: menu `...` -> **Import from File** -> `n8n/ask-expert.workflow.json`.
2. Open the **HTTP Request** node and replace `https://discord.com/api/webhooks/REDACTED` with the webhook URL of your own Discord channel.
3. **Save**, then switch the workflow to **Active**.

### Configuration

In `.env` (not committed):

```
N8N_WEBHOOK_URL=http://localhost:5678/webhook/ask-expert
```

FastAPI always calls `/webhook/` (the workflow must be Active), never `/webhook-test/`.

### Design decisions

- Sending a message out is triggered by a **user click**, not by an LLM tool, so prompt injection cannot make the system send messages on its own.
- The server accepts only a numeric Discord ID (17-20 digits) and builds the profile link itself; n8n receives only `question`, `discord_id` and `discord_url`.
- `allowed_mentions: {parse: []}` blocks @everyone/@role pings.
- Question text is not logged.

### Known limitations

- The Discord ID is typed by the user and **not verified** (verification would need Discord OAuth2).
- Chat sessions live in RAM: lost on restart, no multi-worker setup.
- No authentication; the 3-questions-per-session limit can be bypassed by creating a new session.
- The local n8n webhook is not authenticated.
- The expert's reply path back to the user is manual.
