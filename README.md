# Badminton Advisor

A gear advisor for badminton players. Currently it recommends rackets and shoes; shuttles are planned.

## Who is it for?

Beginner, intermediate and advanced players who want to upgrade their gear but are unsure which racket, shoes or shuttles suit them.

## How do users filter?

Self-estimated level (a future version may estimate it from uploaded videos), play style (aggressive attack, attack, control, defense, balance...), budget, grip strength, colors, etc.
For shoes: gender and EU size (hard filters), foot width (narrow / standard / wide) and a preference for light shoes (soft ranking), optionally a maximum price.

## What does the user get?

The 3 best options for the item they ask about.

## Setup

Requires Python 3.11+ and an Anthropic API key.

```powershell
git clone <repo-url>
cd badminton-advisor
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then put your ANTHROPIC_API_KEY into .env
```

`sentence-transformers` pulls in PyTorch, so the install is large (several GB).

### Build the local data (not committed)

`data/badminton.db` and `data/knowledge_emb.npy` are git-ignored and must be generated once:

```powershell
python src/build_db.py
python src/build_shoes_db.py
python src/knowledge.py build
```

The first embedding run downloads the embedding model from Hugging Face, so it needs internet and takes a while.

### Run

```powershell
uvicorn api:app --app-dir src
```

Open http://127.0.0.1:8000. The "Ask an expert" button also needs n8n running (see below); everything else works without it.

## Limits of the racket recommender

- Content-based ranking (weighted Manhattan distance); no model is trained on data.
- The weights and the `min_score` threshold are set by the author from badminton knowledge and have not been validated with user feedback.
- Small dataset (26 rackets): some level × style × balance combinations are empty. In that case `status = "approximate"`.
- Many rackets can tie at 1.0; the order currently depends only on ascending price.

## Shoe recommender

Same two-step idea as the racket recommender, with different criteria:

- **Hard filter (SQL):** gender (`unisex` shoes are always included) and EU size (`size_min_eu <= size <= size_max_eu`), optionally price.
- **Soft ranking:** width match and lightness, each scored in [0, 1] and combined with weights (`W_WIDTH = 2`, `W_LIGHT = 1`).
- **Missing data:** if the user asks for a criterion that a shoe has no data for (for example weight), that shoe is not ranked. It is reported separately in `excluded_no_data` with the reason, so the bot can say so.
- Data pipeline: `data/raw/shoes.csv` -> `src/clean_shoes.py` (checks column count per row, allowed values, numeric ranges, weight and reference size must come together) -> `data/processed/shoes_clean.csv` -> `src/build_shoes_db.py`.

### Limits of the shoe recommender

- Only 5 shoes so far: enough to prove the pipeline, not a catalog. Many gender × size combinations return few or no results.
- Manufacturers publish weight at different reference sizes, so weight comparison across brands is approximate.
- Lightness is min-max normalised among the shoes left after filtering, so it is relative: a single remaining shoe scores 1.0 even if it is not light.
- Shoes with several widths are stored as separate rows, so one model can fill several of the top 3 slots.
- No lookup of a shoe by name yet (only `recommend_shoes`).
- Weights are author-chosen and not validated with user feedback.

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

## Shoe evaluation

Group H in `src/eval_agent.py`: 10 questions (complete information, missing gender or size, size given in UK instead of EU, size not in the data, racket request that must not be routed to the shoe tool), each run 4 times.

- **Result:** 39/40. The single failure is a false alarm: when asking for the EU size, the bot gave example sizes ("42, 42.5"), and the script counted them as invented numbers. Read by hand, the answer was correct.
- No "before" baseline exists for shoes.
- **Regression check after adding the shoe tool:** groups A, B, E and F3 were re-run once per question and passed. Groups C, D, F1, F2 and G were not re-run, so their earlier results (95/95, 40/40) belong to the previous version of the prompt.
- The script cannot judge wording, for example whether the bot names the shoes that were left out for missing data; that was checked by reading answers.

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

### MCP Server
- The same tools in agent uses are also exposed as an [MCP](https://modelcontextprotocol.io) server, so any MCP client(for example Claude desktop) can call the catalog and knowledge base without the custom agent.


- to run MCP Server:
```
python src/mcp_server,py
```
- to test:
```
python src/test_mcp_client.py
```
