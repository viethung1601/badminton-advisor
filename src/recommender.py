"""Recommender vợt cầu lông: lọc cứng theo ngân sách, xếp hạng mềm theo độ giống.

Chạy từ thư mục gốc:  python src/recommender.py
"""
import sqlite3
import json
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import manhattan_distances

from config import DB_PATH

# Thứ tự tự nhiên -> số trong [0, 1]
LEVEL = {"beginner": 0.0, "intermediate": 0.5, "advanced": 1.0}
STIFFNESS = {"flexible": 0.0, "medium": 0.5, "stiff": 1.0}
BALANCE = {"head_light": 0.0, "even": 0.5, "head_heavy": 1.0}
STYLES = ["attack", "speed", "control", "allround"]  # không có thứ tự -> one-hot

# Mức quan trọng của từng tiêu chí (chỉnh được, đây là "quyết định thiết kế" của bạn)
W_LEVEL, W_STYLE, W_BALANCE, W_STIFF = 2.0, 2.0, 1.0, 1.0

# Vợt có score thấp hơn ngưỡng này bị loại khỏi kết quả (cũng là quyết định thiết kế, chỉnh sau khi xem dữ liệu thật).
# Lưu ý: score tính tương đối theo các tiêu chí người dùng đã điền, nên hồ sơ điền ít tiêu chí
# sẽ có "sai 1 thứ" bị trừ nặng hơn hồ sơ điền đủ 4 tiêu chí.
MIN_SCORE = 0.5
EXACT = 0.999  # score >= EXACT coi là khớp hoàn toàn


def load_rackets(max_price: float) -> pd.DataFrame:
    """Lọc cứng ngân sách ngay trong SQL (tham số bằng ?, không ghép chuỗi)."""
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            "SELECT racket_id, name, brand, balance, stiffness, price_eur, level, play_style "
            "FROM rackets WHERE price_eur <= ?",
            conn,
            params=(max_price,),
        )


def encode(level, play_style, balance, stiffness) -> np.ndarray:
    """Một vợt (hoặc một hồ sơ) -> vector: [level, balance, stiffness, 4 cột one-hot style]."""
    onehot = [1.0 if play_style == s else 0.0 for s in STYLES]
    return np.array(
        [
            LEVEL[level],
            BALANCE[balance] if balance else 0.0,
            STIFFNESS[stiffness] if stiffness else 0.0,
            *onehot,
        ]
    )


def column_weights(balance, stiffness) -> np.ndarray:
    """Cột nào người dùng không quan tâm (None) thì trọng số = 0."""
    # one-hot sai style làm lệch 2 cột -> chia đôi để "sai style" tốn đúng W_STYLE
    return np.array(
        [
            W_LEVEL,
            W_BALANCE if balance else 0.0,
            W_STIFF if stiffness else 0.0,
            *[W_STYLE / 2] * len(STYLES),
        ]
    )

def score_rackets(df, level, play_style, balance, stiffness):
    """Thêm cột score vào df (cùng công thức cũ, tách ra để dùng lại)."""
    X = np.vstack(
        [encode(r.level, r.play_style, r.balance, r.stiffness) for r in df.itertuples()]
    )
    user = encode(level, play_style, balance, stiffness).reshape(1, -1)
    w = column_weights(balance, stiffness)
    dist = manhattan_distances(X * w, user * w).ravel()
    df = df.copy()
    df["score"] = 1 - dist / max_possible(w)
    return df

def find_racket(name: str, limit: int = 5) -> dict:
    """Tra vợt theo tên (khớp một phần, không phân biệt hoa thường)."""
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT name, brand, price_eur, level, play_style, balance, stiffness "
            "FROM rackets WHERE name LIKE ? OR (brand || ' ' || name) LIKE ? "
            "ORDER BY price_eur LIMIT ?",
            conn, params=(f"%{name.strip()}%", f"%{name.strip()}%", limit),
        )
    if df.empty:
        return {"status": "not_found",
                "note": f"Không có vợt nào tên chứa '{name}' trong dữ liệu.", "results": []}
    return {"status": "found", "note": "", "results": json.loads(df.to_json(orient="records"))}

def cheapest_match(level, play_style, balance, stiffness, min_score=MIN_SCORE):
    """Vợt rẻ nhất trong số vợt đủ gần (score >= min_score), bất kể ngân sách."""
    df = load_rackets(1e9)
    if df.empty:
        return None
    df = score_rackets(df, level, play_style, balance, stiffness)
    df = df[df["score"] >= min_score]
    if df.empty:
        return None
    r = df.sort_values(["price_eur", "score"], ascending=[True, False]).iloc[0]
    return {
        "name": r["name"], "price_eur": float(r["price_eur"]),
        "level": r["level"], "play_style": r["play_style"],
        "score": round(float(r["score"]), 2), "is_exact": bool(r["score"] >= EXACT),
    }

def recommend(level, play_style, max_price, balance=None, stiffness=None,
              top_n=3, min_score=MIN_SCORE):
    """Trả về dict:
      status  : "exact" (có vợt khớp hoàn toàn) | "approximate" (chỉ có vợt gần đúng)
                | "no_good_match" (có vợt trong ngân sách nhưng đều dưới min_score)
                | "no_rackets_in_budget" (không có vợt nào trong ngân sách)
      note    : câu giải thích cho người dùng (rỗng nếu status = "exact")
      results : danh sách vợt (rỗng khi không có gì đủ tốt)
    """
    df = load_rackets(max_price)
    if df.empty:
        return {
            "status": "no_rackets_in_budget",
            "note": f"Không có vợt nào trong dữ liệu với giá tối đa {max_price} EUR.",
            "results": [],
            "cheapest_match": cheapest_match(level, play_style, balance, stiffness, min_score),
        }

    df = score_rackets(df, level, play_style, balance, stiffness)

    df = df.sort_values(["score", "price_eur"], ascending=[False, True])
    df = df[df["score"] >= min_score].head(top_n)  # bỏ các vợt dưới ngưỡng

    if df.empty:
        return {
            "status": "no_good_match",
            "note": (
                f"Có vợt trong ngân sách {max_price} EUR nhưng không vợt nào đủ gần "
                "với nhu cầu. Thử tăng ngân sách hoặc nới bớt yêu cầu."
            ),
            "results": [],
            "cheapest_match": cheapest_match(level, play_style, balance, stiffness, min_score),
        }

    exact = df["score"].iloc[0] >= EXACT
    return {
        "status": "exact" if exact else "approximate",
        "note": "" if exact else (
            "Không có vợt khớp hoàn toàn trong ngân sách; đây là các lựa chọn gần nhất."
        ),
        "results": [
            {
                "name": r.name,
                "price_eur": r.price_eur,
                "score": round(r.score, 2),
                "reason": explain(r, level, play_style, balance, stiffness),
            }
            for r in df.itertuples()
        ],
    }


def max_possible(w: np.ndarray) -> float:
    """Khoảng cách lớn nhất có thể -> để chuẩn hoá score về [0, 1].
    level/balance/stiffness lệch tối đa = 1 * w; style sai = 2 cột lệch * (W_STYLE/2) = W_STYLE."""
    return w[0] + w[1] + w[2] + 2 * w[3]  # w[3] = W_STYLE/2; style sai lệch 2 cột


def explain(r, level, play_style, balance, stiffness) -> str:
    parts = []
    parts.append(f"level {r.level}" + (" (đúng)" if r.level == level else f" (bạn: {level})"))
    parts.append(f"style {r.play_style}" + (" (đúng)" if r.play_style == play_style else f" (bạn: {play_style})"))
    if balance:
        parts.append(f"balance {r.balance}" + (" (đúng)" if r.balance == balance else f" (bạn: {balance})"))
    if stiffness:
        parts.append(f"độ cứng {r.stiffness}" + (" (đúng)" if r.stiffness == stiffness else f" (bạn: {stiffness})"))
    return "; ".join(parts)


if __name__ == "__main__":
    profiles = {
        "Người mới, 60 EUR": dict(level="beginner", play_style="attack", max_price=60),
        "Tấn công, 200 EUR, head_heavy + stiff": dict(
            level="advanced", play_style="attack", max_price=200,
            balance="head_heavy", stiffness="stiff",
        ),
        "Trung cấp, thiên tốc độ, 120 EUR": dict(
            level="intermediate", play_style="speed", max_price=120, balance="head_light",
        ),
        "Kiểm tra trường hợp biên: người mới, 20 EUR": dict(
            level="beginner", play_style="allround", max_price=20,
        ),
    }
    for title, p in profiles.items():
        print(f"\n=== {title} ===")
        res = recommend(**p)
        print(f"[status: {res['status']}]", res["note"])
        for i, x in enumerate(res["results"], 1):
            print(f"{i}. {x['name']} | {x['price_eur']} EUR | score {x['score']} | {x['reason']}")
