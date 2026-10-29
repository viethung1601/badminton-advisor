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
    from badminton.config import DB_PATH
    from badminton.data.sqlite_racket_repo import SqliteRacketRepository
    from badminton.data.sqlite_shoe_repo import SqliteShoeRepository
    from badminton.domain.usecases.racket import RecommendRacket, FindRacket
    from badminton.domain.usecases.shoes import RecommendShoes, FindShoe
    from badminton.domain.usecases.catalog import ListRackets, ListShoes
    rr, sr = SqliteRacketRepository(DB_PATH), SqliteShoeRepository(DB_PATH)
    return {
        "recommend_racket": RecommendRacket(rr),
        "find_racket": FindRacket(rr),
        "recommend_shoes": RecommendShoes(sr),
        "find_shoe": FindShoe(sr),
        "list_rackets": ListRackets(rr),
        "list_shoes": ListShoes(sr),
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
