"""Truy vấn danh mục vợt cho GET /rackets. Chỉ SELECT, mọi giá trị đi qua ?."""
import sqlite3
from contextlib import closing

from recommender import DB_PATH

FILTER_COLS = ("level", "play_style", "balance", "stiffness", "weight_class")  # cố định, không từ người dùng
SORTS = {
    "price_asc": "price_eur ASC, name ASC",
    "price_desc": "price_eur DESC, name ASC",
    "name": "name ASC",
}
COLUMNS = ("racket_id, name, brand, weight_class, balance, stiffness, "
           "price_eur, level, play_style, source_url, price_checked_at")


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_rackets(*, q=None, brands=None, filters=None, min_price=None, max_price=None,
                 sort="price_asc", limit=50, offset=0) -> dict:
    """Trả {total, items, brands}. Người gọi phải kiểm tra enum và sort trước."""
    where, params = [], []
    if q and q.strip():
        pat = f"%{_escape_like(q.strip())}%"
        where.append("(name LIKE ? ESCAPE '\\' OR brand LIKE ? ESCAPE '\\')")
        params += [pat, pat]
    if brands:
        where.append(f"brand IN ({','.join('?' * len(brands))})")
        params += list(brands)
    for col in FILTER_COLS:
        vals = (filters or {}).get(col)
        if vals:
            where.append(f"{col} IN ({','.join('?' * len(vals))})")
            params += list(vals)
    if min_price is not None:
        where.append("price_eur >= ?")
        params.append(min_price)
    if max_price is not None:
        where.append("price_eur <= ?")
        params.append(max_price)
    w = (" WHERE " + " AND ".join(where)) if where else ""

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute(f"SELECT COUNT(*) FROM rackets{w}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT {COLUMNS} FROM rackets{w} ORDER BY {SORTS[sort]} LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        brand_list = [r[0] for r in conn.execute("SELECT DISTINCT brand FROM rackets ORDER BY brand")]
    return {"total": total, "items": [dict(r) for r in rows], "brands": brand_list}