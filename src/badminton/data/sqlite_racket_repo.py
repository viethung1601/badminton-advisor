import sqlite3
from contextlib import closing

import pandas as pd

from badminton.data.sql_utils import escape_like
from badminton.domain.contracts import RACKET_SORTS

FILTER_COLS = ("level", "play_style", "balance", "stiffness",
               "weight_class")  # fixed list, never from the user
SORTS = {
    "price_asc": "price_eur ASC, name ASC",
    "price_desc": "price_eur DESC, name ASC",
    "name": "name ASC",
}
COLUMNS = ("racket_id, name, brand, weight_class, balance, stiffness, "
           "price_eur, level, play_style, source_url, price_checked_at")

assert set(SORTS) == set(RACKET_SORTS)


class SqliteRacketRepository:
    def __init__(self, db_path):
        self.db_path = db_path

    def find_under_budget(self, max_price: float) -> pd.DataFrame:
        with closing(sqlite3.connect(self.db_path)) as conn:
            return pd.read_sql_query(
                "SELECT racket_id, name, brand, balance, stiffness, price_eur, level, play_style "
                "FROM rackets WHERE price_eur <= ?",
                conn, params=(max_price,),
            )

    def find_by_name(self, name: str, limit: int) -> pd.DataFrame:
        with closing(sqlite3.connect(self.db_path)) as conn:
            return pd.read_sql_query(
                "SELECT name, brand, price_eur, level, play_style, balance, stiffness "
                "FROM rackets WHERE name LIKE ? OR (brand || ' ' || name) LIKE ? "
                "ORDER BY price_eur LIMIT ?",
                conn, params=(f"%{name.strip()}%", f"%{name.strip()}%", limit),
            )

    def list_page(self, *, q=None, brands=None, filters=None, min_price=None,
                  max_price=None, sort="price_asc", limit=50, offset=0) -> dict:
        where, params = [], []
        if q and q.strip():
            pat = f"%{escape_like(q.strip())}%"
            where.append(
                "(name LIKE ? ESCAPE '\\' OR brand LIKE ? ESCAPE '\\')")
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

        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            total = conn.execute(
                f"SELECT COUNT(*) FROM rackets{w}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT {COLUMNS} FROM rackets{w} ORDER BY {SORTS[sort]} LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
            brand_list = [r[0] for r in conn.execute(
                "SELECT DISTINCT brand FROM rackets ORDER BY brand")]
        return {"total": total, "items": [dict(r) for r in rows], "brands": brand_list}
