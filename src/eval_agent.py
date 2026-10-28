"""Step 7: evaluation suite for the agent.

Run from the project root:
    python src/eval_agent.py [runs_per_case] [group ...]
Examples:
    python src/eval_agent.py 1 B F     # quick try of groups B and F, 1 run per case
    python src/eval_agent.py 5         # run all groups, 5 runs per case

Principle: no word-for-word comparison. Only check what can be determined:
  1. whether the tool was called, and whether its parameters are right
  2. whether racket names and prices in the answer appear in the tool results (or were stated by the user)
"""
import contextlib
import csv
import io
import json
import re
import sys

from config import ROOT
import agent

# ---------------------------------------------------------------- test cases
# expect.kind:
#   tool      : a tool must be called; params must match in at least 1 call; absent = parameter must NOT be filled
#   multi     : there must be a matching call for EACH dict in "each" (questions with a range of values)
#   no_tool   : NO tool may be called
#   any       : neither forces nor forbids a call, only runs the fabrication check
CASES = [
    # A. complete information
    {"id": "A1", "turns": ["I'm a beginner, I like attacking play, my budget is 100 euro"],
     "expect": {"kind": "tool", "params": {"level": "beginner", "play_style": "attack", "max_price": 100},
                "absent": ["balance", "stiffness"]}},
    {"id": "A2", "turns": ["I'm new to the game, I often play fast counter-attacks in doubles, 80€ max"],
     "expect": {"kind": "tool", "params": {"level": "beginner", "play_style": "speed", "max_price": 80},
                "absent": ["balance", "stiffness"]}},
    {"id": "A3", "turns": ["I'm an intermediate player, all-round style, flexible shaft, budget 150 euro, I like head heavy"],
     "expect": {"kind": "tool", "params": {"level": "intermediate", "play_style": "allround", "max_price": 150,
                                           "stiffness": "flexible", "balance": "head_heavy"}}},
    # B. missing information -> must ask back
    {"id": "B1", "turns": ["Recommend me a racket"],
        "expect": {"kind": "no_tool"}},
    {"id": "B2", "turns": ["I play attacking style, budget 120 euro"], "expect": {
        "kind": "no_tool"}},
    {"id": "B3", "turns": [
        "I'm new to the game, around 90 euro, which racket should I buy?"], "expect": {"kind": "no_tool"}},
    # C. rackets outside the DB -> must not be made up
    {"id": "C1", "turns": ["How much is the Yonex Astrox 99 Pro?"], "expect": {
        "kind": "tool_name", "tool": "find_racket", "status": "found"}},
    {"id": "C2", "turns": ["Is the Li-Ning Axforce 80 suitable for me?"],
        "expect": {"kind": "tool_name", "tool": "find_racket", "status": "found"}},
    {"id": "C3", "turns": ["Please compare the Victor Thruster K 9900 with the Astrox 88S"], "expect": {
        "kind": "tool_name", "tool": "find_racket", "status": "not_found"}},
    # D. range of values -> call the tool several times
    {"id": "D1", "turns": ["I'm a beginner, attacking style, 120 euro, flexible to medium shaft"],
     "expect": {"kind": "multi", "each": [
         {"level": "beginner", "play_style": "attack",
             "max_price": 120, "stiffness": "flexible"},
         {"level": "beginner", "play_style": "attack", "max_price": 120, "stiffness": "medium"}]}},
    {"id": "D2", "turns": ["Intermediate level, attacking style, 150 euro, medium or stiff shaft are both fine"],
     "expect": {"kind": "multi", "each": [
         {"level": "intermediate", "play_style": "attack",
             "max_price": 150, "stiffness": "medium"},
         {"level": "intermediate", "play_style": "attack", "max_price": 150, "stiffness": "stiff"}]}},
    {"id": "D3", "turns": ["I'm an intermediate player, leaning towards control, 130 euro, flexible or medium shaft"],
     "expect": {"kind": "multi", "each": [
         {"level": "intermediate", "play_style": "control",
             "max_price": 130, "stiffness": "flexible"},
         {"level": "intermediate", "play_style": "control", "max_price": 130, "stiffness": "medium"}]}},
    # E. budget too low -> no_rackets_in_budget, nothing made up
    {"id": "E1", "turns": ["I'm a beginner, attacking style, budget 10 euro"],
     "expect": {"kind": "tool", "params": {"level": "beginner", "play_style": "attack", "max_price": 10}}},
    {"id": "E2", "turns": ["Intermediate level, fast counter-attacks, I only have 15€"],
     "expect": {"kind": "tool", "params": {"level": "intermediate", "play_style": "speed", "max_price": 15}}},
    {"id": "E3", "turns": ["beginner, all-round, budget 5 euro only"],
     "expect": {"kind": "tool", "params": {"level": "beginner", "play_style": "allround", "max_price": 5}}},
    {"id": "E4", "turns": ["I'm an advanced player, leaning towards control, budget 10 euro"],
     "expect": {"kind": "tool", "params": {"level": "advanced", "play_style": "control", "max_price": 10}}},
    # F. off-topic -> no tool
    {"id": "F1", "turns": ["What's the weather like in Frankfurt today?"], "expect": {
        "kind": "no_tool"}},
    {"id": "F2", "turns": [
        "Write me a Python function that reverses a string"], "expect": {"kind": "no_tool"}},
    {"id": "F3", "turns": ["How much do Yonex badminton shoes cost?"], "expect": {
        "kind": "tool_name","tool":"find_shoe" ,"status":"found"}},
    # G. knowledge (search_knowledge)
    {"id": "G1", "turns": ["What's the difference between head heavy and head light?"],
     "expect": {"kind": "passages_include", "tool": "search_knowledge", "ids": ["k01", "k02"]}},
    {"id": "G2", "turns": ["Is a stiff racket suitable for beginners?"],
     "expect": {"kind": "passages_include", "tool": "search_knowledge", "ids": ["k06"]}},
    # G3: known to FAIL (k02 ranks 5th), kept as a "before" baseline
    {"id": "G3", "turns": ["Who is a head light racket suitable for?"],
     "expect": {"kind": "passages_include", "tool": "search_knowledge", "ids": ["k02"]}},
    # G4, G5: the knowledge base has no pound/gram figures; the numeric check will catch it if the bot makes them up
    {"id": "G4", "turns": ["What string tension in pounds is good for beginners?"],
     "expect": {"kind": "tool_name", "tool": "search_knowledge"}},
    {"id": "G5", "turns": ["How many grams does a 3U racket weigh?"],
     "expect": {"kind": "tool_name", "tool": "search_knowledge"}},
    # G6, G7: the knowledge base lacks the answer; the answer must be READ BY HAND
    {"id": "G6", "turns": ["What are the steps of a smash?"],
     "expect": {"kind": "tool_name", "tool": "search_knowledge"}},
    {"id": "G7", "turns": ["Which is better, Yonex or Victor?"],
     "expect": {"kind": "tool_name", "tool": "search_knowledge"}},
    # G8: must be routed to find_racket
    {"id": "G8", "turns": ["How much is the Axforce 80?"],
     "expect": {"kind": "tool_name", "tool": "find_racket", "status": "found"}},
    # H. shoes (recommend_shoes)
    {"id": "H1", "turns": ["I'm a man, EU size 44, I need shoes"],
     "expect": {"kind": "tool", "params": {"gender": "men", "size_eu": 44},
                "absent": ["prefer_light", "width", "max_price"]}},
    {"id": "H2", "turns": ["Women's shoes size 38, I prefer lightweight shoes"],
     "expect": {"kind": "tool", "params": {"gender": "women", "size_eu": 38, "prefer_light": True}}},
    {"id": "H3", "turns": ["I'm a woman, size 38, narrow feet, looking for shoes"],
     "expect": {"kind": "tool", "params": {"gender": "women", "size_eu": 38, "width": "narrow"}}},
    {"id": "H4", "turns": ["Men's size 43, wide feet, I need shoes"],
     "expect": {"kind": "tool", "params": {"gender": "men", "size_eu": 43, "width": "wide"}}},
    # missing gender or size, or size in another system -> must ask back
    {"id": "H5", "turns": ["I need shoes"], "expect": {"kind": "no_tool"}},
    {"id": "H6", "turns": ["I'm a woman, I need badminton shoes"],
        "expect": {"kind": "no_tool"}},
    {"id": "H7", "turns": ["Size 42, please recommend shoes"],
        "expect": {"kind": "no_tool"}},
    {"id": "H8", "turns": ["I'm a man, UK size 8, I need shoes"],
        "expect": {"kind": "no_tool"}},
    # no such size -> nothing made up
    {"id": "H9", "turns": ["Men's shoes size 50"],
     "expect": {"kind": "tool_name", "tool": "recommend_shoes", "status": "no_shoes_for_size"}},
    # no confusing the tools
    {"id": "H10", "turns": ["I'm intermediate, I like attacking play, budget 100 euro, I need a racket"],
     "expect": {"kind": "tool", "params": {"level": "intermediate", "play_style": "attack", "max_price": 100}}},
    {"id": "H11", "turns": ["How much are the Yonex Aerus Z2 shoes?"],
     "expect": {"kind": "tool_name", "tool": "find_shoe", "status": "found"}},
    {"id": "H12", "turns": ["Do the Victor P9200 shoes come in size 44?"],
     "expect": {"kind": "tool_name", "tool": "find_shoe", "status": "not_found"}},
    {"id": "H13", "turns": ["How much does the SHB 65Z VA Slim weigh?"],
     "expect": {"kind": "tool_name", "tool": "find_shoe", "status": "found"}},
]

NAME_COLUMNS = ("name", "racket", "racket_name", "model")


# ---------------------------------------------------------------- reference data
def load_names() -> list[str]:
    """Read racket names from rackets.csv to know what a 'real racket name' is."""
    path = next((p for p in ROOT.rglob("rackets.csv")
                 if not {".venv", "venv", "node_modules"} & set(p.parts)), None)
    if path is None:
        sys.exit("rackets.csv not found under the project root.")
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        col = next((c for c in NAME_COLUMNS if c in (
            reader.fieldnames or [])), None)
        if col is None:
            sys.exit(f"Can't tell which column holds the racket name. Columns in {path.name}: {reader.fieldnames}\n"
                     f"Edit NAME_COLUMNS at the top of the file to match.")
        return [row[col].strip() for row in reader if row[col].strip()]


def load_shoe_names() -> list[str]:
    with open(ROOT / "data" / "raw" / "shoes.csv", encoding="utf-8-sig", newline="") as f:
        return [r["name"].strip() for r in csv.DictReader(f) if r["name"].strip()]


def validate_cases() -> None:
    """Expected values must be inside ENUM; otherwise the test is wrong, not the agent."""
    errors = []
    for c in CASES:
        e = c["expect"]
        dicts = ([e["params"]] if "params" in e else []) + e.get("each", [])
        for d in dicts:
            for k, v in d.items():
                if k in agent.ENUM and v not in agent.ENUM[k]:
                    errors.append(
                        f"{c['id']}: {k}={v!r} is not in ENUM {agent.ENUM[k]}")
    if errors:
        sys.exit("Fix CASES to match ENUM:\n  " + "\n  ".join(errors))


# ---------------------------------------------------------------- reading the conversation trace
def get_trace(messages: list) -> tuple[list[dict], list[str]]:
    """From the messages list (agent.py appends to it in place) extract: the tool calls and the tool results."""
    calls, results = [], []
    for m in messages:
        if not isinstance(m["content"], list):
            continue
        for b in m["content"]:
            if m["role"] == "assistant" and getattr(b, "type", None) == "tool_use":
                calls.append({"name": b.name, "input": dict(b.input)})
            elif m["role"] == "user" and isinstance(b, dict) and b.get("type") == "tool_result":
                results.append(b["content"])
    return calls, results


def numbers_in(obj) -> set[float]:
    out = set()
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            out |= numbers_in(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= numbers_in(v)
    return out


def strip_brand(name: str) -> str:
    parts = name.split(maxsplit=1)
    return parts[1] if len(parts) == 2 else name


def mentioned_names(text: str, names: list[str]) -> set[str]:
    """Racket names (full, or without the brand) that appear in the text. Longer names match first to avoid false matches on short names."""
    t, found = text.lower(), set()
    for n in sorted(names, key=len, reverse=True):
        for alias in (n.lower(), strip_brand(n).lower()):
            if len(alias) >= 4 and alias in t:
                found.add(n)
                t = t.replace(alias, " " * len(alias))
                break
    return found


def blank_names(text: str, names: list[str]) -> str:
    """Remove racket names from the text so numbers inside names (700, 99...) aren't counted as prices."""
    t = text.lower()
    for n in sorted(names, key=len, reverse=True):
        for alias in (n.lower(), strip_brand(n).lower()):
            if len(alias) >= 4 and alias in t:
                t = t.replace(alias, " " * len(alias))
    return t


def prices_in(text: str, names: list[str]) -> set[float]:
    """Every number >= 10 in the answer (after removing racket names), with or without a unit."""
    t = blank_names(text, names)
    nums = {float(m.replace(",", "."))
            for m in re.findall(r"\d+(?:[.,]\d+)?", t)}
    return {x for x in nums if x >= 10}


# ---------------------------------------------------------------- checking one run
def match(inp: dict, need: dict) -> bool:
    for k, v in need.items():
        if k not in inp:
            return False
        if isinstance(v, (int, float)):
            if abs(float(inp[k]) - v) > 1e-9:
                return False
        elif inp[k] != v:
            return False
    return True


def check(case, calls, results, answers, names) -> list[str]:
    fails, exp = [], case["expect"]
    kind = exp["kind"]

    if kind == "no_tool" and calls:
        fails.append(f"called a tool when it shouldn't: {[c['input'] for c in calls]}")
    elif kind == "tool":
        ok = [c for c in calls if match(c["input"], exp["params"])]
        if not ok:
            fails.append(
                f"no call matches {exp['params']}; actual: {[c['input'] for c in calls]}")
        else:
            bad = [k for k in exp.get("absent", []) if all(
                k in c["input"] for c in ok)]
            if bad:
                fails.append(f"filled parameters the user didn't mention: {bad}")
    elif kind == "multi":
        for need in exp["each"]:
            if not any(match(c["input"], need) for c in calls):
                fails.append(f"missing call {need}")
    elif kind == "tool_name":
        if not any(c["name"] == exp["tool"] for c in calls):
            fails.append(
                f"did not call tool {exp['tool']}; actual: {[c['name'] for c in calls]}")
        if "status" in exp and not any(f'"status": "{exp["status"]}"' in r for r in results):
            fails.append(f"tool did not return status {exp['status']}")
    elif kind == "passages_include":
        if not any(c["name"] == exp["tool"] for c in calls):
            fails.append(
                f"did not call tool {exp['tool']}; actual: {[c['name'] for c in calls]}")
        for pid in exp["ids"]:
            if not any(f'"id": "{pid}"' in r for r in results):
                fails.append(f"passages are missing {pid}")

    # Fabrication check (applies to every case)
    answer = "\n".join(answers)
    user_text = " ".join(case["turns"]).lower()
    results_text = " ".join(results).lower()
    allowed_text = results_text + " " + user_text

    for n in mentioned_names(answer, names):
        if n.lower() not in allowed_text and strip_brand(n).lower() not in allowed_text:
            fails.append(f"mentioned a racket that is not in the tool results: {n}")

    allowed_nums = set()
    for r in results:
        try:
            allowed_nums |= numbers_in(json.loads(r))
        except json.JSONDecodeError:
            pass
    allowed_nums |= {float(x.replace(",", "."))
                     for x in re.findall(r"\d+(?:[.,]\d+)?", user_text)}
    allowed_nums |= {float(x.replace(",", "."))
                     for x in re.findall(r"\d+(?:[.,]\d+)?", results_text)}
    for p in prices_in(answer, names):
        if not any(abs(p - a) < 0.01 for a in allowed_nums):
            fails.append(f"price is in neither the tool results nor the question: {p}")
    return fails


def run_once(case, names) -> dict:
    messages, answers = [], []
    try:
        for text in case["turns"]:
            messages.append({"role": "user", "content": text})
            # silence the [tool] lines to keep the output tidy
            with contextlib.redirect_stdout(io.StringIO()):
                answers.append(agent.chat_turn(messages))
        calls, results = get_trace(messages)
        fails = check(case, calls, results, answers, names)
    except Exception as e:
        calls, fails = [], [f"error while running: {type(e).__name__}: {e}"]
    return {"id": case["id"], "passed": not fails, "fails": fails,
            "calls": [c["input"] for c in calls], "answer": "\n".join(answers)}


# ---------------------------------------------------------------- main
def main() -> None:
    args = sys.argv[1:]
    runs = int(args[0]) if args and args[0].isdigit() else 3
    groups = [a.upper() for a in args[1:] if not a.isdigit()]
    cases = [c for c in CASES if not groups or c["id"][0] in groups]

    validate_cases()
    names = load_names() + load_shoe_names()

    print(f"{len(cases)} cases x {runs} runs, {len(names)} items (rackets + shoes from rackets.csv + shoes.csv), model={agent.MODEL}\n")

    records = []
    for c in cases:
        for i in range(runs):
            rec = run_once(c, names)
            rec["run"] = i + 1
            records.append(rec)
            print(
                f"{c['id']} run {i + 1}: {'pass' if rec['passed'] else 'FAIL'}", flush=True)

    # Table by case
    print("\n=== By case ===")
    for c in cases:
        rs = [r for r in records if r["id"] == c["id"]]
        n_ok = sum(r["passed"] for r in rs)
        print(f"{c['id']}: {n_ok}/{len(rs)}  {c['turns'][0][:60]}")

    # Table by group
    print("\n=== By group ===")
    for g in sorted({c["id"][0] for c in cases}):
        rs = [r for r in records if r["id"][0] == g]
        n_ok = sum(r["passed"] for r in rs)
        print(f"Group {g}: {n_ok}/{len(rs)} = {100 * n_ok / len(rs):.0f}%")

    # Failure details
    fails = [r for r in records if not r["passed"]]
    if fails:
        print("\n=== Failure details ===")
        for r in fails:
            print(f"\n[{r['id']} run {r['run']}]")
            for f in r["fails"]:
                print("  -", f)
            print("  tool calls:", r["calls"])
            print("  answer:", r["answer"][:400].replace("\n", " | "))

    out = ROOT / "eval_results.json"
    out.write_text(json.dumps(records, ensure_ascii=False,
                   indent=2), encoding="utf-8")
    print(f"\nSaved details to {out.name}")


if __name__ == "__main__":
    main()