from dataclasses import dataclass
from typing import Callable

from badminton.container import UseCases, get_usecases
from badminton.domain.contracts import RACKET_ALLOWED, SHOE_ALLOWED
from badminton.domain.shoe_scoring import GENDERS

ENUM = {k: sorted(RACKET_ALLOWED[k]) for k in (
    "level", "play_style", "balance", "stiffness")}
WIDTHS = sorted(SHOE_ALLOWED["width"])


class ToolError(Exception):
    """A problem the model should be told about."""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str        # sent to the agent
    mcp_description: str    # sent to MCP clients (carries the behaviour rules)
    input_schema: dict
    handler: Callable[[UseCases, dict], dict]


def _need_name(value, what):
    value = str(value or "").strip()
    if not value:
        raise ToolError(f"missing {what} name")
    return value


def _recommend_racket(uc, a):
    return uc.recommend_racket(level=a["level"], play_style=a["play_style"],
                               max_price=float(a["max_price"]),
                               balance=a.get("balance"), stiffness=a.get("stiffness"))


def _find_racket(uc, a):
    return uc.find_racket(_need_name(a.get("name"), "racket"))


def _search_knowledge(uc, a):
    q = str(a.get("query") or "").strip()
    if not q:
        raise ToolError("missing query")
    result = uc.search_knowledge(q)
    if result.get("status") == "error":
        raise ToolError(result.get("message", "knowledge search failed"))
    return result


def _recommend_shoes(uc, a):
    mp = a.get("max_price")
    return uc.recommend_shoes(gender=a["gender"], size_eu=float(a["size_eu"]),
                              prefer_light=bool(a.get("prefer_light", False)), width=a.get("width"),
                              max_price=float(mp) if mp is not None else None)


def _find_shoe(uc, a):
    return uc.find_shoe(_need_name(a.get("name"), "shoe"))


TOOLS: list[Tool] = [
    Tool(
        name="recommend_racket",
        description=("Recommend badminton rackets from the shop's database. This is the only source "
                     "for choosing rackets. Only call it when level, play_style and budget are all known. "
                     "If any of the three is missing, ask the user instead of guessing. "
                     "Only fill in balance and stiffness if the user explicitly specifies them."),
        mcp_description=("Recommend badminton rackets from the shop's database. This is the ONLY source for choosing rackets. "
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
                         "at any price. Do not mention any other budget figure."),        # dán từ mcp_server.py (description của recommend_racket)
        input_schema={"type": "object",
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
                      "required": ["level", "play_style", "max_price"], },
        handler=_recommend_racket,
    ),
    Tool(
        name="search_knowledge",
        description=(
            "Search badminton knowledge from the curated knowledge base: balance "
            "(head heavy/light), shaft stiffness, 3U/4U, grip size G, string tension, "
            "advice by skill level. Use for questions that ask for an explanation or a concept. "
            "Do NOT use it to look up the price or name of a specific racket (use find_racket), "
            "and do NOT use it to recommend rackets by budget (use recommend_racket)."
        ),
        mcp_description=(
            "Search badminton knowledge in the curated knowledge base: balance (head heavy/light), shaft "
            "stiffness, 3U/4U, grip size G, string tension, advice by skill level. Use for questions that ask for an "
            "explanation or a concept. ONLY use the content of the returned passages and say clearly that the information comes from a source "
            "(source_url). If status is no_relevant_knowledge, say plainly that the knowledge base doesn't have this information. "
            "Do not use it to look up the price/name of a specific racket (use find_racket) or to recommend rackets by budget (use recommend_racket)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user's question, kept in their own wording (e.g. 'head heavy', 'nặng đầu').",
                    }
            },
            "required": ["query"],
        },
        handler=_search_knowledge,
    ),
    Tool(
        name="find_racket",
        description=(
            "Look up information about a specific racket by name (price, level, play style...) "
            "in the shop's database. Use when the user asks about a racket by name. "
            "Do not use it to recommend rackets based on the user's needs."),
        mcp_description=(
            "Look up information about a specific racket by name (price, level, play style...) in the shop's "
            "database, for example 'Astrox 99 Pro'. Only state information present in the result; status not_found means "
            "the shop doesn't have that racket, so do not guess from outside knowledge. Do not use it to recommend rackets based on needs."
        ),
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Racket name, for example 'Astrox 99 Pro'."}},
            "required": ["name"],
        },
        handler=_find_racket,
    ),
    Tool(
        name="recommend_shoes",
        description=(
            "Recommend badminton shoes from the shop's database. This is the ONLY source for choosing shoes. "
            "Only call it when gender (men/women) and EU size are both known. If either is missing, ask instead of guessing. "
            "If the user gives a size in another system (UK, US, cm), ask for the EU size; do not convert it yourself. "
            "Only fill in prefer_light and width when the user states them clearly."
        ),
        mcp_description=(
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
        input_schema={
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
        handler=_recommend_shoes,
    ),

    Tool(
        name="find_shoe",
        description=(
            "Look up information about a specific pair of shoes by name (price, gender, EU size range, weight, fit) "
            "in the shop's database. Use when the user asks about a named shoe or a brand. "
            "Do not use it to recommend shoes based on needs (use recommend_shoes)."
        ),
        mcp_description=(
            "Look up information about a specific pair of shoes by name (price, gender, EU size range, weight, fit) "
            "in the shop's database, for example 'Subaxia GT'. Only state information present in the result; "
            "status not_found = the shop doesn't have that pair; a null field = no data yet, say exactly that. "
            "Always give the weight together with weight_ref_size_eu. Do not use it to recommend shoes based on needs (use recommend_shoes)."
        ),
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Shoe name, for example 'Subaxia GT'."}},
            "required": ["name"],
        },
        handler=_find_shoe,
    ),
]


_BY_NAME = {t.name: t for t in TOOLS}


def _validate(tool, args):
    schema = tool.input_schema
    for key in schema.get("required", []):
        if args.get(key) is None:
            raise ToolError(f"missing required argument: {key}")
    for key, spec in schema["properties"].items():
        value = args.get(key)
        if value is not None and "enum" in spec and value not in spec["enum"]:
            raise ToolError(
                f"{key}={value!r} is invalid, allowed: {spec['enum']}")


def run_tool(name, args, usecases=None):
    """Returns (content: dict, is_error: bool). Never raises: errors go back to the model."""
    tool = _BY_NAME.get(name)
    if tool is None:
        return {"error": f"unknown tool: {name}"}, True
    try:
        _validate(tool, args or {})
        return tool.handler(usecases or get_usecases(), args or {}), False
    except Exception as e:
        return {"error": str(e)}, True
