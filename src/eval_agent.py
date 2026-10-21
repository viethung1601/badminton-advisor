"""Bước 7: bộ test đánh giá agent.

Chạy từ thư mục gốc:
    python src/eval_agent.py [số_lần_chạy_mỗi_câu] [nhóm ...]
Ví dụ:
    python src/eval_agent.py 1 B F     # thử nhanh nhóm B và F, mỗi câu 1 lần
    python src/eval_agent.py 5         # chạy đủ tất cả nhóm, mỗi câu 5 lần

Nguyên tắc: không so từng chữ. Chỉ kiểm tra thứ xác định được:
  1. tool có được gọi không, tham số đúng không
  2. tên vợt và giá trong câu trả lời có nằm trong kết quả tool (hoặc do chính người dùng nói) không
"""
import contextlib
import csv
import io
import json
import re
import sys

from config import ROOT
import agent

# ---------------------------------------------------------------- bộ câu hỏi
# expect.kind:
#   tool      : phải gọi tool; params phải khớp ở ít nhất 1 lời gọi; absent = tham số KHÔNG được điền
#   multi     : phải có lời gọi khớp với MỖI dict trong "each" (câu khoảng giá trị)
#   no_tool   : KHÔNG được gọi tool
#   any       : không ép gọi hay không gọi, chỉ chạy kiểm tra bịa dữ kiện
CASES = [
    # A. đủ thông tin
    {"id": "A1", "turns": ["Mình chơi trình beginner, thích tấn công, ngân sách 100 euro"],
     "expect": {"kind": "tool", "params": {"level": "beginner", "play_style": "attack", "max_price": 100},
                "absent": ["balance", "stiffness"]}},
    {"id": "A2", "turns": ["Mình mới chơi, hay phản tạt nhanh ở đôi, tối đa 80€ thôi"],
     "expect": {"kind": "tool", "params": {"level": "beginner", "play_style": "speed", "max_price": 80},
                "absent": ["balance", "stiffness"]}},
    {"id": "A3", "turns": ["Mình chơi trình trung bình, lối đa dụng, thân dẻo, ngân sách 150 euro, thích đầu nặng"],
     "expect": {"kind": "tool", "params": {"level": "intermediate", "play_style": "allround", "max_price": 150,
                                           "stiffness": "flexible", "balance": "head_heavy"}}},
    # B. thiếu thông tin -> phải hỏi lại
    {"id": "B1", "turns": ["Tư vấn cho mình cây vợt"],
        "expect": {"kind": "no_tool"}},
    {"id": "B2", "turns": ["Mình chơi tấn công, ngân sách 120 euro"], "expect": {
        "kind": "no_tool"}},
    {"id": "B3", "turns": [
        "Mình mới chơi, tầm 90 euro, nên mua vợt nào?"], "expect": {"kind": "no_tool"}},
    # C. vợt ngoài DB -> không được bịa
    {"id": "C1", "turns": ["Yonex Astrox 99 Pro giá bao nhiêu?"], "expect": {
        "kind": "tool_name", "tool": "find_racket", "status": "found"}},
    {"id": "C2", "turns": ["Vợt Li-Ning Axforce 80 có hợp với mình không?"],
        "expect": {"kind": "tool_name", "tool": "find_racket", "status": "found"}},
    {"id": "C3", "turns": ["So sánh giúp mình Victor Thruster K 9900 với Astrox 88S"], "expect": {
        "kind": "tool_name", "tool": "find_racket", "status": "not_found"}},
    # D. khoảng giá trị -> gọi tool nhiều lần
    {"id": "D1", "turns": ["Mình trình beginner, tấn công, 120 euro, thân dẻo đến trung bình"],
     "expect": {"kind": "multi", "each": [
         {"level": "beginner", "play_style": "attack",
             "max_price": 120, "stiffness": "flexible"},
         {"level": "beginner", "play_style": "attack", "max_price": 120, "stiffness": "medium"}]}},
    {"id": "D2", "turns": ["Trình trung bình, tấn công, 150 euro, thân trung bình hoặc cứng đều được"],
     "expect": {"kind": "multi", "each": [
         {"level": "intermediate", "play_style": "attack",
             "max_price": 150, "stiffness": "medium"},
         {"level": "intermediate", "play_style": "attack", "max_price": 150, "stiffness": "stiff"}]}},
    {"id": "D3", "turns": ["Mình trình trung bình, thiên về kiểm soát, 130 euro, thân dẻo hoặc trung bình"],
     "expect": {"kind": "multi", "each": [
         {"level": "intermediate", "play_style": "control",
             "max_price": 130, "stiffness": "flexible"},
         {"level": "intermediate", "play_style": "control", "max_price": 130, "stiffness": "medium"}]}},
    # E. ngân sách quá thấp -> no_rackets_in_budget, không bịa
    {"id": "E1", "turns": ["Mình trình beginner, tấn công, ngân sách 10 euro"],
     "expect": {"kind": "tool", "params": {"level": "beginner", "play_style": "attack", "max_price": 10}}},
    {"id": "E2", "turns": ["Trình trung bình, phản tạt nhanh, mình chỉ có 15€"],
     "expect": {"kind": "tool", "params": {"level": "intermediate", "play_style": "speed", "max_price": 15}}},
    {"id": "E3", "turns": ["beginner, đa dụng, budget 5 euro thôi"],
     "expect": {"kind": "tool", "params": {"level": "beginner", "play_style": "allround", "max_price": 5}}},
    {"id": "E4", "turns": ["Mình chơi trình nâng cao, thiên về kiểm soát, ngân sách 10 euro"],
     "expect": {"kind": "tool", "params": {"level": "advanced", "play_style": "control", "max_price": 10}}},
    # F. lạc đề -> không gọi tool
    {"id": "F1", "turns": ["Hôm nay thời tiết Frankfurt thế nào?"], "expect": {
        "kind": "no_tool"}},
    {"id": "F2", "turns": [
        "Viết giúp mình hàm Python đảo ngược chuỗi"], "expect": {"kind": "no_tool"}},
    {"id": "F3", "turns": ["Giày cầu lông Yonex giá bao nhiêu?"], "expect": {
        "kind": "no_tool"}},
    # G. kiến thức (search_knowledge)
    {"id": "G1", "turns": ["Head heavy khác head light thế nào?"],
     "expect": {"kind": "passages_include", "tool": "search_knowledge", "ids": ["k01", "k02"]}},
    {"id": "G2", "turns": ["Vợt cứng có hợp người mới không?"],
     "expect": {"kind": "passages_include", "tool": "search_knowledge", "ids": ["k06"]}},
    # G3: đã biết sẽ FAIL (k02 hạng 5), giữ làm mốc "trước"
    {"id": "G3", "turns": ["Vợt nhẹ đầu hợp với ai?"],
     "expect": {"kind": "passages_include", "tool": "search_knowledge", "ids": ["k02"]}},
    # G4, G5: kho không có số pound/gram; thước số sẽ bắt nếu bot bịa
    {"id": "G4", "turns": ["Căng cước bao nhiêu pound thì tốt cho người mới?"],
     "expect": {"kind": "tool_name", "tool": "search_knowledge"}},
    {"id": "G5", "turns": ["Vợt 3U nặng bao nhiêu gram?"],
     "expect": {"kind": "tool_name", "tool": "search_knowledge"}},
    # G6, G7: kho thiếu đáp án; phải ĐỌC TAY câu trả lời
    {"id": "G6", "turns": ["Các bước thực hiện một cú smash là gì?"],
     "expect": {"kind": "tool_name", "tool": "search_knowledge"}},
    {"id": "G7", "turns": ["Yonex hay Victor tốt hơn?"],
     "expect": {"kind": "tool_name", "tool": "search_knowledge"}},
    # G8: phải rẽ sang find_racket
    {"id": "G8", "turns": ["Axforce 80 bao nhiêu tiền?"],
     "expect": {"kind": "tool_name", "tool": "find_racket", "status": "found"}},
    # H. giày (recommend_shoes)
    {"id": "H1", "turns": ["Mình là nam, size EU 44, cần giày"],
     "expect": {"kind": "tool", "params": {"gender": "men", "size_eu": 44},
                "absent": ["prefer_light", "width", "max_price"]}},
    {"id": "H2", "turns": ["Giày nữ size 38, mình ưu tiên giày nhẹ"],
     "expect": {"kind": "tool", "params": {"gender": "women", "size_eu": 38, "prefer_light": True}}},
    {"id": "H3", "turns": ["Mình nữ, size 38, bàn chân hẹp, tìm giày"],
     "expect": {"kind": "tool", "params": {"gender": "women", "size_eu": 38, "width": "narrow"}}},
    {"id": "H4", "turns": ["Nam size 43, bàn chân to ngang, cần giày"],
     "expect": {"kind": "tool", "params": {"gender": "men", "size_eu": 43, "width": "wide"}}},
    # thiếu giới tính hoặc size, hoặc size hệ khác -> phải hỏi lại
    {"id": "H5", "turns": ["Tôi cần giày"], "expect": {"kind": "no_tool"}},
    {"id": "H6", "turns": ["Mình là nữ, cần giày cầu lông"],
        "expect": {"kind": "no_tool"}},
    {"id": "H7", "turns": ["Size 42, tư vấn giày giúp mình"],
        "expect": {"kind": "no_tool"}},
    {"id": "H8", "turns": ["Mình nam, size UK 8, cần giày"],
        "expect": {"kind": "no_tool"}},
    # không có size -> không bịa
    {"id": "H9", "turns": ["Giày nam size 50"],
     "expect": {"kind": "tool_name", "tool": "recommend_shoes", "status": "no_shoes_for_size"}},
    # không nhầm tool
    {"id": "H10", "turns": ["Mình trung cấp, thích tấn công, ngân sách 100 euro, cần vợt"],
     "expect": {"kind": "tool", "params": {"level": "intermediate", "play_style": "attack", "max_price": 100}}},
    {"id": "H11", "turns": ["Giày Yonex Aerus Z2 giá bao nhiêu?"],
     "expect": {"kind": "tool_name", "tool": "find_shoe", "status": "found"}},
    {"id": "H12", "turns": ["Giày Victor P9200 có size 44 không?"],
     "expect": {"kind": "tool_name", "tool": "find_shoe", "status": "not_found"}},
    {"id": "H13", "turns": ["SHB 65Z VA Slim nặng bao nhiêu?"],
     "expect": {"kind": "tool_name", "tool": "find_shoe", "status": "found"}},
]

NAME_COLUMNS = ("name", "racket", "racket_name", "model")


# ---------------------------------------------------------------- dữ liệu tham chiếu
def load_names() -> list[str]:
    """Đọc tên vợt từ rackets.csv để biết 'tên vợt thật' là gì."""
    path = next((p for p in ROOT.rglob("rackets.csv")
                 if not {".venv", "venv", "node_modules"} & set(p.parts)), None)
    if path is None:
        sys.exit("Không tìm thấy rackets.csv dưới thư mục gốc.")
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        col = next((c for c in NAME_COLUMNS if c in (
            reader.fieldnames or [])), None)
        if col is None:
            sys.exit(f"Không biết cột tên vợt. Các cột trong {path.name}: {reader.fieldnames}\n"
                     f"Sửa NAME_COLUMNS ở đầu file cho khớp.")
        return [row[col].strip() for row in reader if row[col].strip()]


def load_shoe_names() -> list[str]:
    with open(ROOT / "data" / "raw" / "shoes.csv", encoding="utf-8-sig", newline="") as f:
        return [r["name"].strip() for r in csv.DictReader(f) if r["name"].strip()]


def validate_cases() -> None:
    """Giá trị mong đợi phải nằm trong ENUM, nếu không test sai chứ không phải agent sai."""
    errors = []
    for c in CASES:
        e = c["expect"]
        dicts = ([e["params"]] if "params" in e else []) + e.get("each", [])
        for d in dicts:
            for k, v in d.items():
                if k in agent.ENUM and v not in agent.ENUM[k]:
                    errors.append(
                        f"{c['id']}: {k}={v!r} không có trong ENUM {agent.ENUM[k]}")
    if errors:
        sys.exit("Sửa CASES cho khớp ENUM:\n  " + "\n  ".join(errors))


# ---------------------------------------------------------------- đọc vết hội thoại
def get_trace(messages: list) -> tuple[list[dict], list[str]]:
    """Từ list messages (agent.py đã append tại chỗ) lấy ra: các lời gọi tool và kết quả tool."""
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
    """Tên vợt (đầy đủ hoặc bỏ hãng) xuất hiện trong text. Tên dài khớp trước để tránh khớp nhầm tên ngắn."""
    t, found = text.lower(), set()
    for n in sorted(names, key=len, reverse=True):
        for alias in (n.lower(), strip_brand(n).lower()):
            if len(alias) >= 4 and alias in t:
                found.add(n)
                t = t.replace(alias, " " * len(alias))
                break
    return found


def blank_names(text: str, names: list[str]) -> str:
    """Xóa tên vợt khỏi text để số trong tên (700, 99...) không bị tính là giá."""
    t = text.lower()
    for n in sorted(names, key=len, reverse=True):
        for alias in (n.lower(), strip_brand(n).lower()):
            if len(alias) >= 4 and alias in t:
                t = t.replace(alias, " " * len(alias))
    return t


def prices_in(text: str, names: list[str]) -> set[float]:
    """Mọi số >= 10 trong câu trả lời (sau khi bỏ tên vợt), có đơn vị hay không."""
    t = blank_names(text, names)
    nums = {float(m.replace(",", "."))
            for m in re.findall(r"\d+(?:[.,]\d+)?", t)}
    return {x for x in nums if x >= 10}


# ---------------------------------------------------------------- kiểm tra một lần chạy
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
        fails.append(f"gọi tool dù không nên: {[c['input'] for c in calls]}")
    elif kind == "tool":
        ok = [c for c in calls if match(c["input"], exp["params"])]
        if not ok:
            fails.append(
                f"không có lời gọi khớp {exp['params']}; thực tế: {[c['input'] for c in calls]}")
        else:
            bad = [k for k in exp.get("absent", []) if all(
                k in c["input"] for c in ok)]
            if bad:
                fails.append(f"điền tham số người dùng không nói: {bad}")
    elif kind == "multi":
        for need in exp["each"]:
            if not any(match(c["input"], need) for c in calls):
                fails.append(f"thiếu lời gọi {need}")
    elif kind == "tool_name":
        if not any(c["name"] == exp["tool"] for c in calls):
            fails.append(
                f"không gọi tool {exp['tool']}; thực tế: {[c['name'] for c in calls]}")
        if "status" in exp and not any(f'"status": "{exp["status"]}"' in r for r in results):
            fails.append(f"tool không trả status {exp['status']}")
    elif kind == "passages_include":
        if not any(c["name"] == exp["tool"] for c in calls):
            fails.append(
                f"không gọi tool {exp['tool']}; thực tế: {[c['name'] for c in calls]}")
        for pid in exp["ids"]:
            if not any(f'"id": "{pid}"' in r for r in results):
                fails.append(f"passages thiếu {pid}")

    # Kiểm tra bịa dữ kiện (áp dụng mọi câu)
    answer = "\n".join(answers)
    user_text = " ".join(case["turns"]).lower()
    results_text = " ".join(results).lower()
    allowed_text = results_text + " " + user_text

    for n in mentioned_names(answer, names):
        if n.lower() not in allowed_text and strip_brand(n).lower() not in allowed_text:
            fails.append(f"nhắc vợt không có trong kết quả tool: {n}")

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
            fails.append(f"giá không có trong kết quả tool hoặc câu hỏi: {p}")
    return fails


def run_once(case, names) -> dict:
    messages, answers = [], []
    try:
        for text in case["turns"]:
            messages.append({"role": "user", "content": text})
            # tắt dòng [tool] cho bảng gọn
            with contextlib.redirect_stdout(io.StringIO()):
                answers.append(agent.chat_turn(messages))
        calls, results = get_trace(messages)
        fails = check(case, calls, results, answers, names)
    except Exception as e:
        calls, fails = [], [f"lỗi khi chạy: {type(e).__name__}: {e}"]
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

    print(f"{len(cases)} câu x {runs} lần, {len(names)} items(including rackets + shoes trong rackets.csv + shoes.csv, model={agent.MODEL}\n")

    records = []
    for c in cases:
        for i in range(runs):
            rec = run_once(c, names)
            rec["run"] = i + 1
            records.append(rec)
            print(
                f"{c['id']} lần {i + 1}: {'pass' if rec['passed'] else 'FAIL'}", flush=True)

    # Bảng theo câu
    print("\n=== Theo câu ===")
    for c in cases:
        rs = [r for r in records if r["id"] == c["id"]]
        n_ok = sum(r["passed"] for r in rs)
        print(f"{c['id']}: {n_ok}/{len(rs)}  {c['turns'][0][:60]}")

    # Bảng theo nhóm
    print("\n=== Theo nhóm ===")
    for g in sorted({c["id"][0] for c in cases}):
        rs = [r for r in records if r["id"][0] == g]
        n_ok = sum(r["passed"] for r in rs)
        print(f"Nhóm {g}: {n_ok}/{len(rs)} = {100 * n_ok / len(rs):.0f}%")

    # Chi tiết lỗi
    fails = [r for r in records if not r["passed"]]
    if fails:
        print("\n=== Chi tiết lỗi ===")
        for r in fails:
            print(f"\n[{r['id']} lần {r['run']}]")
            for f in r["fails"]:
                print("  -", f)
            print("  tool calls:", r["calls"])
            print("  trả lời:", r["answer"][:400].replace("\n", " | "))

    out = ROOT / "eval_results.json"
    out.write_text(json.dumps(records, ensure_ascii=False,
                   indent=2), encoding="utf-8")
    print(f"\nĐã lưu chi tiết vào {out.name}")


if __name__ == "__main__":
    main()
