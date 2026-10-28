"""MCP server for Badminton Advisor: wraps the existing functions as tools.
Runs over stdio. Do NOT print() to stdout (stdout is the protocol channel)."""
from shoe_recommender import recommend_shoes, find_shoe, GENDERS
from clean_shoes import ALLOWED as SHOE_ALLOWED
from recommender import recommend, find_racket
from clean_rackets import ALLOWED
from knowledge import search_knowledge
from mcp.server.fastmcp import FastMCP
import sys
import json

_real_stdout = sys.stdout
sys.stdout = sys.stderr  # any print during import goes to stderr


sys.stdout = _real_stdout

ENUM = {k: list(ALLOWED[k])
        for k in ("level", "play_style", "balance", "stiffness")}

mcp = FastMCP("badminton-advisor")


def _check_enum(col, value):
    if value is not None and value not in ENUM[col]:
        raise ValueError(
            f"{col}={value!r} is invalid, allowed: {ENUM[col]}")


def _need_name(name, what):
    name = str(name).strip()
    if not name:
        raise ValueError(f"missing {what} name")
    return name


@mcp.tool(
    name="recommend_racket",
    description=(
        "Recommend badminton rackets from the shop's database. This is the ONLY source for choosing rackets. "
        "Only call it when level, play_style and max_price (EUR) are known; if any is missing, ask the user instead of guessing. "
        f"level: {ENUM['level']}. play_style: {ENUM['play_style']} "
        "(attack, speed = fast/counter-attacking, control, allround). "
        f"balance: {ENUM['balance']}, stiffness: {ENUM['stiffness']}: only fill in when the user states them clearly. "
        "Only mention rackets that appear in the results. Read the status field: exact = full match; "
        "approximate = only a close match, you must name where it differs; "
        "no_good_match / no_rackets_in_budget = say plainly that there is no racket within the budget. "
        "If cheapest_match is an object: state its exact name, price_eur, level and play_style; "
        "if is_exact is false, say clearly that it is only the closest racket, do not call it 'suitable', then ask the user "
        "whether they want to raise the budget. If cheapest_match is null, say the shop has no racket close enough "
        "at any price. Do not mention any other budget figure."
    ),
)
def tool_recommend_racket(level: str, play_style: str, max_price: float,
                          balance: str | None = None, stiffness: str | None = None) -> dict:
    for col, v in (("level", level), ("play_style", play_style),
                   ("balance", balance), ("stiffness", stiffness)):
        _check_enum(col, v)
    result = recommend(level=level, play_style=play_style, max_price=float(max_price),
                     balance=balance, stiffness=stiffness)
    return json.loads(json.dumps(result,ensure_ascii=False))

@mcp.tool(
    name="find_racket",
    description=(
        "Look up information about a specific racket by name (price, level, play style...) in the shop's "
        "database, for example 'Astrox 99 Pro'. Only state information present in the result; status not_found means "
        "the shop doesn't have that racket, so do not guess from outside knowledge. Do not use it to recommend rackets based on needs."
    ),
)
def tool_find_racket(name: str) -> dict:
    return find_racket(_need_name(name, "racket"))


@mcp.tool(
    name="search_knowledge",
    description=(
        "Search badminton knowledge in the curated knowledge base: balance (head heavy/light), shaft "
        "stiffness, 3U/4U, grip size G, string tension, advice by skill level. Use for questions that ask for an "
        "explanation or a concept. ONLY use the content of the returned passages and say clearly that the information comes from a source "
        "(source_url). If status is no_relevant_knowledge, say plainly that the knowledge base doesn't have this information. "
        "Do not use it to look up the price/name of a specific racket (use find_racket) or to recommend rackets by budget (use recommend_racket)."
    ),
)
def tool_search_knowledge(query: str) -> dict:
    q = str(query).strip()
    if not q:
        raise ValueError("missing query")
    result = search_knowledge(q)
    if result.get("status") == "error":
        raise ValueError(str(result))
    return result


@mcp.tool(
    name="recommend_shoes",
    description=(
        "Recommend badminton shoes from the shop's database. This is the ONLY source for choosing shoes. "
        "Only call it when gender (men/women) and size_eu are known; if either is missing, ask instead of guessing. "
        "If the user gives a size in another system (UK, US, cm), ask for the EU size; do not convert it yourself. "
        "Only fill in prefer_light, width and max_price when the user states them clearly. "
        f"width: {sorted(SHOE_ALLOWED['width'])} (narrow, standard, wide). "
        "Only mention shoes that appear in the results. If excluded_no_data is not empty, name those pairs and the reason "
        "they were not ranked. When talking about lightness, state the weight in grams together with the measured size and mention that the weight is only approximate. "
        "status no_shoes_for_size = there are no shoes for that gender and size; "
        "no_data_for_criteria = data is missing for the chosen criteria. "
        "Unisex shoes are already included in the results, no need to ask more."
    ),
)
def tool_recommend_shoes(gender: str, size_eu: float, prefer_light: bool = False,
                         width: str | None = None, max_price: float | None = None) -> dict:
    if gender not in GENDERS:
        raise ValueError(f"gender must be one of {sorted(GENDERS)}")
    if width is not None and width not in SHOE_ALLOWED["width"]:
        raise ValueError(
            f"width={width!r} is invalid, allowed: {sorted(SHOE_ALLOWED['width'])}")
    return recommend_shoes(gender=gender, size_eu=float(size_eu), prefer_light=bool(prefer_light),
                           width=width, max_price=float(max_price) if max_price is not None else None)


@mcp.tool(
    name="find_shoe",
    description=(
        "Look up information about a specific pair of shoes by name (price, gender, EU size range, weight, fit) "
        "in the shop's database, for example 'Subaxia GT'. Only state information present in the result; "
        "status not_found = the shop doesn't have that pair; a null field = no data yet, say exactly that. "
        "Always give the weight together with weight_ref_size_eu. Do not use it to recommend shoes based on needs (use recommend_shoes)."
    ),
)
def tool_find_shoe(name: str) -> dict:
    return find_shoe(_need_name(name, "shoe"))


if __name__ == "__main__":
    mcp.run()  # default: stdio