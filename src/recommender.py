"""Badminton racket recommender: hard filter by budget, soft ranking by similarity.

Run from the project root:  python src/recommender.py
"""
import sqlite3
import json
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import manhattan_distances
from badminton.domain.racket_scoring import MIN_SCORE, EXACT, score_rackets, explain
from config import DB_PATH


def load_rackets(max_price: float) -> pd.DataFrame:
    """Hard-filter the budget directly in SQL (parameters via ?, no string concatenation)."""
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            "SELECT racket_id, name, brand, balance, stiffness, price_eur, level, play_style "
            "FROM rackets WHERE price_eur <= ?",
            conn,
            params=(max_price,),
        )

def find_racket(name: str, limit: int = 5) -> dict:
    """Look up rackets by name (partial match, case-insensitive)."""
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT name, brand, price_eur, level, play_style, balance, stiffness "
            "FROM rackets WHERE name LIKE ? OR (brand || ' ' || name) LIKE ? "
            "ORDER BY price_eur LIMIT ?",
            conn, params=(f"%{name.strip()}%", f"%{name.strip()}%", limit),
        )
    if df.empty:
        return {"status": "not_found",
                "note": f"No racket whose name contains '{name}' in the data.", "results": []}
    return {"status": "found", "note": "", "results": json.loads(df.to_json(orient="records"))}

def cheapest_match(level, play_style, balance, stiffness, min_score=MIN_SCORE):
    """The cheapest racket among those close enough (score >= min_score), regardless of budget."""
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
    """Returns a dict:
      status  : "exact" (a racket matches fully) | "approximate" (only close matches)
                | "no_good_match" (rackets exist in the budget but all are below min_score)
                | "no_rackets_in_budget" (no racket at all within the budget)
      note    : an explanation for the user (empty if status = "exact")
      results : list of rackets (empty when nothing is good enough)
    """
    df = load_rackets(max_price)
    if df.empty:
        return {
            "status": "no_rackets_in_budget",
            "note": f"No racket in the data with a maximum price of {max_price} EUR.",
            "results": [],
            "cheapest_match": cheapest_match(level, play_style, balance, stiffness, min_score),
        }

    df = score_rackets(df, level, play_style, balance, stiffness)

    df = df.sort_values(["score", "price_eur"], ascending=[False, True])
    df = df[df["score"] >= min_score].head(top_n)  # drop rackets below the threshold

    if df.empty:
        return {
            "status": "no_good_match",
            "note": (
                f"There are rackets within the {max_price} EUR budget, but none is close enough "
                "to your needs. Try raising the budget or relaxing some requirements."
            ),
            "results": [],
            "cheapest_match": cheapest_match(level, play_style, balance, stiffness, min_score),
        }

    exact = df["score"].iloc[0] >= EXACT
    return {
        "status": "exact" if exact else "approximate",
        "note": "" if exact else (
            "No racket matches fully within the budget; these are the closest options."
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

if __name__ == "__main__":
    profiles = {
        "Beginner, 60 EUR": dict(level="beginner", play_style="attack", max_price=60),
        "Attack, 200 EUR, head_heavy + stiff": dict(
            level="advanced", play_style="attack", max_price=200,
            balance="head_heavy", stiffness="stiff",
        ),
        "Intermediate, speed-oriented, 120 EUR": dict(
            level="intermediate", play_style="speed", max_price=120, balance="head_light",
        ),
        "Edge case check: beginner, 20 EUR": dict(
            level="beginner", play_style="allround", max_price=20,
        ),
    }
    for title, p in profiles.items():
        print(f"\n=== {title} ===")
        res = recommend(**p)
        print(f"[status: {res['status']}]", res["note"])
        for i, x in enumerate(res["results"], 1):
            print(f"{i}. {x['name']} | {x['price_eur']} EUR | score {x['score']} | {x['reason']}")