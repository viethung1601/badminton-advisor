"""Shoe recommender: hard filter by gender + size, soft ranking by width and lightness.

Run from the project root:  python src/shoe_recommender.py
"""
import sqlite3

import pandas as pd
import json
from badminton.domain.shoe_scoring import WIDTH, W_LIGHT, W_WIDTH, GENDERS, explain
from config import DB_PATH

def _esc_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def find_shoe(name: str, limit: int = 5) -> dict:
    """Look up shoes by name (partial match, case-insensitive)."""
    pat = f"%{_esc_like(name.strip())}%"
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT name, brand, gender, size_min_eu, size_max_eu, weight_g, weight_ref_size_eu, "
            "width, price_eur, note FROM shoes "
            "WHERE name LIKE ? ESCAPE '\\' OR (brand || ' ' || name) LIKE ? ESCAPE '\\' "
            "ORDER BY price_eur LIMIT ?",
            conn, params=(pat, pat, limit),
        )
    if df.empty:
        return {"status": "not_found",
                "note": f"No shoe whose name contains '{name}' in the data.", "results": []}
    return {"status": "found", "note": "", "results": json.loads(df.to_json(orient="records"))}

def load_shoes(gender: str, size_eu: float, max_price: float | None) -> pd.DataFrame:
    """Hard-filter in SQL (parameters via ?, no string concatenation)."""
    sql = ("SELECT shoe_id, name, brand, gender, width, weight_g, weight_ref_size_eu, price_eur "
           "FROM shoes WHERE gender IN (?, 'unisex') AND size_min_eu <= ? AND size_max_eu >= ?")
    params: list = [gender, size_eu, size_eu]
    if max_price is not None:
        sql += " AND price_eur <= ?"
        params.append(max_price)
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def recommend_shoes(gender, size_eu, prefer_light=False, width=None,
                    max_price=None, top_n=3) -> dict:
    """Returns a dict:
      status   : "ok" | "no_shoes_for_size" (no shoe matches gender + size [+ budget])
                 | "no_data_for_criteria" (shoes exist but all lack data for the chosen criteria)
      note     : an explanation for the user
      results  : list of ranked shoes
      excluded_no_data : shoes dropped because they lack data for the criteria the user chose
    """
    if gender not in GENDERS:
        raise ValueError(f"gender must be one of {sorted(GENDERS)}")
    if width is not None and width not in WIDTH:
        raise ValueError(f"width must be one of {sorted(WIDTH)}")

    df = load_shoes(gender, size_eu, max_price)
    if df.empty:
        return {"status": "no_shoes_for_size",
                "note": f"No shoes in the data for {gender}, EU size {size_eu}"
                        + (f", maximum price {max_price} EUR." if max_price is not None else "."),
                "results": [], "excluded_no_data": []}

    # Missing data for a criterion the user chose -> don't rank, but say why
    excluded = []
    if prefer_light:
        miss = df["weight_g"].isna()
        excluded += [{"name": n, "reason": "no weight data yet"}
                     for n in df.loc[miss, "name"]]
        df = df[~miss]
    if width:
        miss = df["width"].isna()
        excluded += [{"name": n, "reason": "no width data yet"}
                     for n in df.loc[miss, "name"]]
        df = df[~miss]

    if df.empty:
        return {"status": "no_data_for_criteria",
                "note": "There are shoes for this gender and size, but all lack data for the criteria you chose.",
                "results": [], "excluded_no_data": excluded}

    # Score = weighted average of the active criteria, each in [0, 1]
    df = df.copy()
    parts = []
    if width:
        parts.append(
            (W_WIDTH, 1 - (df["width"].map(WIDTH) - WIDTH[width]).abs()))
    if prefer_light:
        lo, hi = df["weight_g"].min(), df["weight_g"].max()
        light = pd.Series(1.0, index=df.index) if hi == lo else 1 - \
            (df["weight_g"] - lo) / (hi - lo)
        parts.append((W_LIGHT, light))
    df["score"] = (sum(w * s for w, s in parts) /
                   sum(w for w, _ in parts)) if parts else 1.0

    df = df.sort_values(["score", "price_eur"], ascending=[
                        False, True]).head(top_n)

    notes = []
    if prefer_light:
        notes.append(
            "Lightness is only compared among the shoes that remain after filtering, and the weights published by brands are measured "
            "at different reference sizes, so they are only approximate.")
    if excluded:
        notes.append(
            "Some pairs were not ranked because of missing data (see excluded_no_data).")
    if not parts:
        notes.append(
            "You haven't chosen any criteria (lightness, width), so the pairs tie on score and are sorted by ascending price.")

    return {"status": "ok", "note": " ".join(notes),
            "results": [{"name": r.name, "price_eur": float(r.price_eur), "score": round(float(r.score), 2),
                         "reason": explain(r, width, prefer_light)} for r in df.itertuples()],
            "excluded_no_data": excluded}

if __name__ == "__main__":
    cases = {
        "Women 38, prefers lightweight": dict(gender="women", size_eu=38, prefer_light=True),
        "Women 38, narrow fit": dict(gender="women", size_eu=38, width="narrow"),
        "Men 44, wide fit + lightweight": dict(gender="men", size_eu=44, width="wide", prefer_light=True),
        "Men 50 (no such size)": dict(gender="men", size_eu=50),
        "Women 38, no soft criteria": dict(gender="women", size_eu=38),
    }
    for title, p in cases.items():
        print(f"\n=== {title} ===")
        res = recommend_shoes(**p)
        print(f"[status: {res['status']}]", res["note"])
        for i, x in enumerate(res["results"], 1):
            print(
                f"{i}. {x['name']} | {x['price_eur']} EUR | score {x['score']} | {x['reason']}")
        for e in res["excluded_no_data"]:
            print(f"   (not ranked) {e['name']}: {e['reason']}")