import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
GOLDEN = ROOT / "tests" / "golden"

from badminton.presentation.tools import TOOLS, run_tool  # noqa: E402

BY_NAME = {t.name: t for t in TOOLS}


def _sort_brackets(text):
    """Old descriptions embedded list(set), whose order changed every run: compare order-free."""
    return re.sub(r"\[([^\]]*)\]",
                  lambda m: "[" + ", ".join(sorted(x.strip() for x in m.group(1).split(","))) + "]", text)


def _sort_enums(schema):
    s = json.loads(json.dumps(schema))
    for spec in s.get("properties", {}).values():
        if "enum" in spec:
            spec["enum"] = sorted(spec["enum"])
    return s


def test_same_tools_as_agent_before():
    old = json.loads((GOLDEN / "agent_tools.json").read_text(encoding="utf-8"))
    assert [t["name"] for t in old] == [t.name for t in TOOLS]
    for o in old:
        t = BY_NAME[o["name"]]
        assert t.description == o["description"], o["name"]
        assert _sort_enums(t.input_schema) == _sort_enums(o["input_schema"]), o["name"]


def test_same_tools_as_mcp_before():
    old = json.loads((GOLDEN / "mcp_tools.json").read_text(encoding="utf-8"))
    assert sorted(t["name"] for t in old) == sorted(BY_NAME)
    for o in old:
        t = BY_NAME[o["name"]]
        assert _sort_brackets(t.mcp_description) == _sort_brackets(o["description"]), o["name"]
        assert sorted(t.input_schema["properties"]) == o["properties"], o["name"]
        assert sorted(t.input_schema["required"]) == o["required"], o["name"]


def test_bad_input_is_an_error_not_a_crash():
    assert run_tool("nope", {})[1] is True
    assert run_tool("find_racket", {"name": "  "})[1] is True
    assert run_tool("recommend_racket", {"level": "pro", "play_style": "attack", "max_price": 60})[1] is True
    assert run_tool("recommend_shoes", {"gender": "robot", "size_eu": 42})[1] is True
    assert run_tool("recommend_racket", {"level": "beginner"})[1] is True


def test_real_calls_work():
    content, err = run_tool("find_shoe", {"name": "Subaxia GT"})
    assert not err and content["status"] == "found"
    content, err = run_tool("recommend_racket", {"level": "beginner", "play_style": "attack", "max_price": 60})
    assert not err and content["status"] in ("exact", "approximate")