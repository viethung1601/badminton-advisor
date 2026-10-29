import sqlite3
from contextlib import closing

import pandas as pd

from badminton.data.sql_utils import escape_like
from badminton.domain.contracts import SHOE_SORTS as SHOE_SORT_KEYS

SHOE_FILTER_COLS = ("gender", "width")  # fixed list, never from the user
SHOE_SORTS = {
    "price_asc": "price_eur ASC, name ASC",
    "price_desc": "price_eur DESC, name ASC",
    "name": "name ASC",
    # NULLs go last (SQLite treats NULL as smallest, so it needs a separate key)
    "weight_asc": "weight_g IS NULL, weight_g ASC, name ASC",
}
SHOE_COLUMNS = ("shoe_id, name, brand, gender, size_min_eu, size_max_eu, weight_g, "
                "weight_ref_size_eu, width, price_eur, note")

assert set(SHOE_SORTS) == set(SHOE_SORT_KEYS)


class SqliteShoeRepository:
    def __init__(self, db_path):
        self.db_path = db_path

    def find_fitting(self, gender: str, size_eu: float, max_price: float | None) -> pd.DataFrame:
        """Hard-filter in SQL (parameters via ?, no string concatenation)."""
        sql = ("SELECT shoe_id, name, brand, gender, width, weight_g, weight_ref_size_eu, price_eur "
               "FROM shoes WHERE gender IN (?, 'unisex') AND size_min_eu <= ? AND size_max_eu >= ?")
        params: list = [gender, size_eu, size_eu]
        if max_price is not None:
            sql += " AND price_eur <= ?"
            params.append(max_price)
        with sqlite3.connect(self.DB_PATH) as conn:
            return pd.read_sql_query(sql, conn, params=params)

    def find_by_name(self, name: str, limit: int) -> pd.DataFrame:
        pat = f"%{escape_like(name.strip())}%"
        with sqlite3.connect(self.DB_PATH) as conn:
            df = pd.read_sql_query(
                "SELECT name, brand, gender, size_min_eu, size_max_eu, weight_g, weight_ref_size_eu, "
                "width, price_eur, note FROM shoes "
                "WHERE name LIKE ? ESCAPE '\\' OR (brand || ' ' || name) LIKE ? ESCAPE '\\' "
                "ORDER BY price_eur LIMIT ?",
                conn, params=(pat, pat, limit),
            )
        return {"status": "found", "note": "", "results": json.loads(df.to_json(orient="records"))}

    def list_page(self, *, q=None, brands=None, filters=None, size_eu=None, min_price=None,
                  max_price=None, max_weight_g=None, sort="price_asc", limit=50, offset=0) -> dict:
        where, params = [], []
        if q and q.strip():
            pat = f"%{escape_like(q.strip())}%"
            where.append(
                "(name LIKE ? ESCAPE '\\' OR brand LIKE ? ESCAPE '\\')")
            params += [pat, pat]
        if brands:
            where.append(f"brand IN ({','.join('?' * len(brands))})")
            params += list(brands)
        for col in SHOE_FILTER_COLS:
            vals = (filters or {}).get(col)
            if vals:
                where.append(f"{col} IN ({','.join('?' * len(vals))})")
                params += list(vals)
        if size_eu is not None:
            where.append("size_min_eu <= ? AND size_max_eu >= ?")
            params += [size_eu, size_eu]
        if min_price is not None:
            where.append("price_eur >= ?")
            params.append(min_price)
        if max_price is not None:
            where.append("price_eur <= ?")
            params.append(max_price)
        if max_weight_g is not None:
            # shoes with no weight are excluded automatically
            where.append("weight_g <= ?")
            params.append(max_weight_g)
        w = (" WHERE " + " AND ".join(where)) if where else ""

        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            total = conn.execute(
                f"SELECT COUNT(*) FROM shoes{w}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT {SHOE_COLUMNS} FROM shoes{w} ORDER BY {SHOE_SORTS[sort]} LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
            brand_list = [r[0] for r in conn.execute(
                "SELECT DISTINCT brand FROM shoes ORDER BY brand")]
        return {"total": total, "items": [dict(r) for r in rows], "brands": brand_list}
