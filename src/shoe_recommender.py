"""Recommender giày: lọc cứng theo giới tính + size, xếp hạng mềm theo độ rộng và độ nhẹ.

Chạy từ thư mục gốc:  python src/shoe_recommender.py
"""
import sqlite3

import pandas as pd

from config import DB_PATH

WIDTH = {"narrow": 0.0, "standard": 0.5, "wide": 1.0}
# Mức quan trọng (quyết định thiết kế, chưa kiểm chứng với người dùng)
W_WIDTH, W_LIGHT = 2.0, 1.0
# người dùng chọn men/women; giày unisex tự được đưa vào
GENDERS = {"men", "women"}


def load_shoes(gender: str, size_eu: float, max_price: float | None) -> pd.DataFrame:
    """Lọc cứng trong SQL (tham số bằng ?, không ghép chuỗi)."""
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
    """Trả về dict:
      status   : "ok" | "no_shoes_for_size" (không giày nào đúng giới tính + size [+ ngân sách])
                 | "no_data_for_criteria" (có giày nhưng đều thiếu dữ liệu cho tiêu chí đã chọn)
      note     : câu giải thích cho người dùng
      results  : danh sách giày đã xếp hạng
      excluded_no_data : giày bị loại vì thiếu dữ liệu cho tiêu chí người dùng chọn
    """
    if gender not in GENDERS:
        raise ValueError(f"gender phải là một trong {sorted(GENDERS)}")
    if width is not None and width not in WIDTH:
        raise ValueError(f"width phải là một trong {sorted(WIDTH)}")

    df = load_shoes(gender, size_eu, max_price)
    if df.empty:
        return {"status": "no_shoes_for_size",
                "note": f"Không có giày nào trong dữ liệu cho {gender}, size EU {size_eu}"
                        + (f", giá tối đa {max_price} EUR." if max_price is not None else "."),
                "results": [], "excluded_no_data": []}

    # Thiếu dữ liệu cho tiêu chí người dùng chọn -> không xếp, nhưng nói rõ lý do
    excluded = []
    if prefer_light:
        miss = df["weight_g"].isna()
        excluded += [{"name": n, "reason": "chưa có dữ liệu cân nặng"}
                     for n in df.loc[miss, "name"]]
        df = df[~miss]
    if width:
        miss = df["width"].isna()
        excluded += [{"name": n, "reason": "chưa có dữ liệu độ rộng"}
                     for n in df.loc[miss, "name"]]
        df = df[~miss]

    if df.empty:
        return {"status": "no_data_for_criteria",
                "note": "Có giày đúng giới tính và size nhưng đều thiếu dữ liệu cho tiêu chí bạn chọn.",
                "results": [], "excluded_no_data": excluded}

    # Điểm = trung bình có trọng số của các tiêu chí đang bật, mỗi tiêu chí trong [0, 1]
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
            "Độ nhẹ chỉ so sánh trong các đôi còn lại sau khi lọc, và cân nặng hãng công bố ""ở các size tham chiếu khác nhau nên chỉ gần đúng.")
    if excluded:
        notes.append(
            "Một số đôi không được xếp vì thiếu dữ liệu (xem excluded_no_data).")
    if not parts:
        notes.append(
            "Bạn chưa chọn tiêu chí nào (độ nhẹ, độ rộng) nên các đôi hòa điểm và xếp theo giá tăng dần.")

    return {"status": "ok", "note": " ".join(notes),
            "results": [{"name": r.name, "price_eur": float(r.price_eur), "score": round(float(r.score), 2),
                         "reason": explain(r, width, prefer_light)} for r in df.itertuples()],
            "excluded_no_data": excluded}


def explain(r, width, prefer_light) -> str:
    parts = [f"form {r.width}" + (" (đúng)" if width and r.width == width
                                  else f" (bạn: {width})" if width else "")
             if isinstance(r.width, str) else "form: không có dữ liệu"]
    if prefer_light:
        parts.append(
            f"nặng {r.weight_g:.0f} g (đo ở size EU {r.weight_ref_size_eu:g})")
    return "; ".join(parts)


if __name__ == "__main__":
    cases = {
        "Nữ 38, ưu tiên nhẹ": dict(gender="women", size_eu=38, prefer_light=True),
        "Nữ 38, form hẹp": dict(gender="women", size_eu=38, width="narrow"),
        "Nam 44, form rộng + nhẹ": dict(gender="men", size_eu=44, width="wide", prefer_light=True),
        "Nam 50 (không có size)": dict(gender="men", size_eu=50),
        "Nữ 38, không tiêu chí mềm": dict(gender="women", size_eu=38),
    }
    for title, p in cases.items():
        print(f"\n=== {title} ===")
        res = recommend_shoes(**p)
        print(f"[status: {res['status']}]", res["note"])
        for i, x in enumerate(res["results"], 1):
            print(
                f"{i}. {x['name']} | {x['price_eur']} EUR | score {x['score']} | {x['reason']}")
        for e in res["excluded_no_data"]:
            print(f"   (không xếp) {e['name']}: {e['reason']}")
