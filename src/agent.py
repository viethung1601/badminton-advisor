"""Minimal agent: the LLM understands the user's question -> calls recommend() -> phrases the results."""
import json
import os

from dotenv import load_dotenv
import anthropic

from knowledge import search_knowledge
from config import ROOT
from clean_rackets import ALLOWED
from recommender import recommend, find_racket
from clean_shoes import ALLOWED as SHOE_ALLOWED
from shoe_recommender import recommend_shoes, find_shoe, GENDERS

load_dotenv(ROOT / ".env")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
MAX_STEPS = 5  # prevents an infinite loop within one chat turn

# reads ANTHROPIC_API_KEY from the environment automatically
client = anthropic.Anthropic()

# valid values come from ALLOWED: a single source of truth
ENUM = {k: list(ALLOWED[k])
        for k in ("level", "play_style", "balance", "stiffness")}

TOOLS = [{
    "name": "recommend_racket",
    "description": (
        "Recommend badminton rackets from the shop's database. This is the only source "
        "for choosing rackets. Only call it when level, play_style and budget are all known. "
        "If any of the three is missing, ask the user instead of guessing. "
        "Only fill in balance and stiffness if the user explicitly specifies them."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "level": {"type": "string", "enum": ENUM["level"],
                      "description": "Player skill level."},
            "play_style": {"type": "string", "enum": ENUM["play_style"],
                           "description": "Play style: attack, speed (fast/counter-attacking), "
                                          "control, allround."},
            "max_price": {"type": "number", "description": "Maximum budget in EUR."},
            "balance": {"type": "string", "enum": ENUM["balance"],
                        "description": "Balance point. Leave empty if the user doesn't mention it."},
            "stiffness": {"type": "string", "enum": ENUM["stiffness"],
                          "description": "Shaft stiffness. Leave empty if the user doesn't mention it."},
        },
        "required": ["level", "play_style", "max_price"],
    },
},
    {
    "name": "search_knowledge",
    "description": (
        "Search badminton knowledge from the curated knowledge base: balance "
        "(head heavy/light), shaft stiffness, 3U/4U, grip size G, string tension, "
        "advice by skill level. Use for questions that ask for an explanation or a concept. "
        "Do NOT use it to look up the price or name of a specific racket (use find_racket), "
        "and do NOT use it to recommend rackets by budget (use recommend_racket)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The user's question, kept in their own wording (e.g. 'head heavy', 'nặng đầu').",
            }
        },
        "required": ["query"],
    },
},
    {
    "name": "find_racket",
    "description": (
        "Look up information about a specific racket by name (price, level, play style...) "
        "in the shop's database. Use when the user asks about a racket by name. "
        "Do not use it to recommend rackets based on the user's needs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Racket name, for example 'Astrox 99 Pro'."}},
        "required": ["name"],
    },
},
    {
    "name": "recommend_shoes",
    "description": (
        "Recommend badminton shoes from the shop's database. This is the ONLY source for choosing shoes. "
        "Only call it when gender (men/women) and EU size are both known. If either is missing, ask instead of guessing. "
        "If the user gives a size in another system (UK, US, cm), ask for the EU size; do not convert it yourself. "
        "Only fill in prefer_light and width when the user states them clearly."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "gender": {"type": "string", "enum": sorted(GENDERS), "description": "men or women."},
            "size_eu": {"type": "number", "description": "Shoe size in the EU system, e.g. 42 or 42.5."},
            "prefer_light": {"type": "boolean", "description": "true if the user prefers lightweight shoes."},
            "width": {"type": "string", "enum": sorted(SHOE_ALLOWED["width"]),
                      "description": "Fit: narrow, standard, or wide (for wider feet)."},
            "max_price": {"type": "number", "description": "Maximum budget in EUR. Leave empty if not mentioned."},
        },
        "required": ["gender", "size_eu"],
    },
},
    {
    "name": "find_shoe",
    "description": (
        "Look up information about a specific pair of shoes by name (price, gender, EU size range, weight, fit) "
        "in the shop's database. Use when the user asks about a named shoe or a brand. "
        "Do not use it to recommend shoes based on needs (use recommend_shoes)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Shoe name, for example 'Subaxia GT'."}},
        "required": ["name"],
    },
}
]


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
    """Run the real tool. Returns (json_content, is_error). Validates input before calling."""
    if name == "find_racket":
        n = str(args.get("name", "")).strip()
        if not n:
            return json.dumps({"error": "missing racket name"}), True
        try:
            return json.dumps(find_racket(n), ensure_ascii=False), False
        except Exception as e:
            return json.dumps({"error": str(e)}), True

    if name == "search_knowledge":
        q = str(args.get("query", "")).strip()
        if not q:
            return json.dumps({"error": "missing query"}), True
        result = search_knowledge(q)
        return json.dumps(result, ensure_ascii=False), result.get("status") == "error"

    if name == "find_shoe":
        n = str(args.get("name", "")).strip()
        if not n:
            return json.dumps({"error": "missing shoe name"}), True
        try:
            return json.dumps(find_shoe(n), ensure_ascii=False), False
        except Exception as e:
            return json.dumps({"error": str(e)}), True

    if name == "recommend_shoes":
        if args.get("gender") not in GENDERS:
            return json.dumps({"error": f"gender must be one of {sorted(GENDERS)}"}), True
        w = args.get("width")
        if w is not None and w not in SHOE_ALLOWED["width"]:
            return json.dumps({"error": f"width={w!r} is invalid, allowed: {sorted(SHOE_ALLOWED['width'])}"}), True
        try:
            mp = args.get("max_price")
            result = recommend_shoes(
                gender=args["gender"], size_eu=float(args["size_eu"]),
                prefer_light=bool(args.get("prefer_light", False)), width=w,
                max_price=float(mp) if mp is not None else None,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}), True
        return json.dumps(result, ensure_ascii=False), False
    if name != "recommend_racket":
        return json.dumps({"error": f"unknown tool: {name}"}), True

    for col in ("level", "play_style", "balance", "stiffness"):
        v = args.get(col)
        if v is not None and v not in ENUM[col]:
            return json.dumps({"error": f"{col}={v!r} is invalid, allowed: {ENUM[col]}"}), True
    try:
        result = recommend(
            level=args["level"], play_style=args["play_style"],
            max_price=float(args["max_price"]),
            balance=args.get("balance"), stiffness=args.get("stiffness"),
        )
    except Exception as e:  # return the error to the LLM instead of crashing the program
        return json.dumps({"error": str(e)}), True
    return json.dumps(result, ensure_ascii=False), False


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