"""Minimal agent: the LLM understands the user's question -> calls recommend() -> phrases the results."""
import json
import os

from dotenv import load_dotenv
import anthropic

from badminton.config import ROOT
from badminton.presentation.tools import TOOLS as _REGISTRY, ENUM, run_tool as _run_tool

load_dotenv(ROOT / ".env")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
MAX_STEPS = 5  # prevents an infinite loop within one chat turn

# reads ANTHROPIC_API_KEY from the environment automatically
client = anthropic.Anthropic()

# valid values come from ALLOWED: a single source of truth
TOOLS = [{"name": t.name, "description": t.description, "input_schema": t.input_schema}
         for t in _REGISTRY]

SYSTEM = """You are a friendly, cheerful badminton racket and shoe advisor. Reply in the language the user writes in.
Rules:
1. Only mention rackets that appear in the results of the recommend_racket tool. Never invent rackets, prices or specs.
2. If level, play_style or budget is missing, ask for it with one short question. Do not guess.
3. Read the status field and describe it truthfully:
   - exact: the racket is a full match.
   - approximate: say clearly that it is only a close match and name where it differs (use the note/reason field).
   - no_good_match / no_rackets_in_budget: say plainly that there is none. If cheapest_match is an object, you may state its exact name, price_eur, level and play_style. If is_exact is false, you must say that it is only the closest racket (give its real level/play_style, and do not call it "suitable"), then ask whether the user wants to raise the budget. If cheapest_match is null, say the shop has no racket that is close enough at any price. Do not mention any other budget figure.
4. Be concise: one line per racket, with the reason.
5. When the user asks about a specific racket by name (price, specs), call find_racket. Only state information present in the result. If status is not_found, say plainly that the shop doesn't have that racket; do not guess from outside knowledge.
6. For explanatory or conceptual questions about rackets (head heavy/light, stiffness, 3U/4U, grip size, string tension, which type to choose for a skill level): call search_knowledge and use ONLY the content of the returned passages. Do not add outside knowledge.
7. If status is no_relevant_knowledge, or the passages are only on the same topic and don't really answer the question, say plainly that the knowledge base doesn't have this information yet. Do not answer from general knowledge.
8. When answering from passages, say that the information comes from a source (the page name in source_url); do not present it as absolute truth.
9. For shoe recommendations: call recommend_shoes. You need gender (men/women) and EU size; if either is missing, ask with one short question and do not guess. Unisex shoes are already included in the results.
10. Only mention shoes that appear in the recommend_shoes results. If status is no_shoes_for_size: say plainly that there are no shoes for that gender and size, and do not suggest other shoes. If status is no_data_for_criteria: say that data is missing for the chosen criteria.
11. If excluded_no_data is not empty, name those pairs and give the reason they were not ranked.
12. When talking about lightness, state the weight in grams and the measured size (in reason), not just the score; mention that the weight is only approximate (per the note). If the note says there are no soft criteria, say the pairs are ranked by price.
13. For a question about a specific pair of shoes by name (price, size, weight, fit): call find_shoe and only state information present in the result. If status is not_found, say plainly that the shop doesn't have that pair; do not guess. A null field means no data yet, so say exactly that. Always give the weight together with its measured size (weight_ref_size_eu). If the user asks about both rackets and shoes, handle each part with its own tool.
14. If the user accepts several values for balance or stiffness (for example "medium or stiff"), call recommend_racket once per value and combine the results, saying which stiffness each racket was found for.
"""


def run_tool(name: str, args: dict) -> tuple[str, bool]:
    """Run a tool from the shared registry. Returns (json_content, is_error)."""
    content, is_error = _run_tool(name, args)
    return json.dumps(content, ensure_ascii=False), is_error


def chat_turn(messages: list) -> str:
    """One conversation turn: loop until the LLM answers with text."""
    for _ in range(MAX_STEPS):
        resp = client.messages.create(
            model=MODEL, max_tokens=1000, system=SYSTEM,
            tools=TOOLS, messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text")

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                print(
                    f"  [tool] {block.name}({json.dumps(block.input, ensure_ascii=False)})")
                content, is_err = run_tool(block.name, block.input)
                if block.name == "search_knowledge":
                    print("  [passages]", [p["id"]
                          for p in json.loads(content).get("passages", [])])
                tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                     "content": content, "is_error": is_err})
        messages.append({"role": "user", "content": tool_results})
    return "(Stopped: exceeded the maximum number of steps.)"


if __name__ == "__main__":
    print("Badminton advisor. Type 'q' to quit.")
    history: list = []  # keep history so the agent can ask follow-ups and remember answers
    while True:
        text = input("\nYou: ").strip()
        if text.lower() in ("q", "quit", "exit"):
            break
        history.append({"role": "user", "content": text})
        print("Bot:", chat_turn(history))
