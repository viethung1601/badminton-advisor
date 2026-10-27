"""Lưới an toàn khi refactor: so kết quả hiện tại với baseline.json (sinh từ code cũ).

Chạy từ thư mục gốc:  python tests/test_golden.py        (hoặc: python -m pytest tests -q)
Khi refactor, CHỈ sửa phần ADAPTER bên dưới để trỏ sang use case mới.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
BASELINE = json.loads((ROOT / "tests" / "golden" / "baseline.json").read_text(encoding="utf-8"))


# ======================= ADAPTER: sửa phần này theo từng bước refactor =======================
def impl() -> dict:
    import recommender as R
    import shoe_recommender as S
    import catalog as C
    return {
        "recommend_racket": lambda **a: R.recommend(**a),
        "find_racket": lambda name: R.find_racket(name),
        "recommend_shoes": lambda **a: S.recommend_shoes(**a),
        "find_shoe": lambda name: S.find_shoe(name),
        "list_rackets": lambda **a: C.list_rackets(**a),
        "list_shoes": lambda **a: C.list_shoes(**a),
    }
# =============================================================================================


def _clean(x):
    return json.loads(json.dumps(x, default=float, ensure_ascii=False))


def run_all() -> list[str]:
    fns = impl()
    failures = []
    for group, cases in BASELINE.items():
        for i, c in enumerate(cases):
            got = _clean(fns[group](**c["args"]))
            if got != c["result"]:
                failures.append(f"{group}[{i}] args={c['args']}")
    return failures


def test_golden():
    failures = run_all()
    assert not failures, f"{len(failures)} khác baseline, ví dụ: {failures[:3]}"


if __name__ == "__main__":
    bad = run_all()
    total = sum(len(v) for v in BASELINE.values())
    print(f"{total - len(bad)}/{total} khớp baseline")
    for b in bad[:10]:
        print("  KHÁC:", b)
    sys.exit(1 if bad else 0)
