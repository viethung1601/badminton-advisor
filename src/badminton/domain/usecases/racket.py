import json
from badminton.domain.racket_scoring import MIN_SCORE, EXACT, score_rackets, explain


class RecommendRacket:
    def __init__(self, repo):
        self.repo = repo

    def _cheapest_match(self, level, play_style, balance, stiffness, min_score):
        df = self.repo.find_under_budget(1e9)       # trước: load_rackets(1e9)
        if df.empty:
            return None
        df = score_rackets(df, level, play_style, balance, stiffness)
        df = df[df["score"] >= min_score]
        if df.empty:
            return None
        r = df.sort_values(["price_eur", "score"],
                           ascending=[True, False]).iloc[0]
        return {
            "name": r["name"], "price_eur": float(r["price_eur"]),
            "level": r["level"], "play_style": r["play_style"],
            "score": round(float(r["score"]), 2), "is_exact": bool(r["score"] >= EXACT),
        }

    def __call__(self, level, play_style, max_price, balance=None, stiffness=None,
                 top_n=3, min_score=MIN_SCORE):
        # trước: load_rackets(max_price)
        df = self.repo.find_under_budget(max_price)
        if df.empty:
            return {
                "status": "no_rackets_in_budget",
                "note": f"No racket in the data with a maximum price of {max_price} EUR.",
                "results": [],
                "cheapest_match": self._cheapest_match(level, play_style, balance, stiffness, min_score),
            }

        df = score_rackets(df, level, play_style, balance, stiffness)

        df = df.sort_values(["score", "price_eur"], ascending=[False, True])
        df = df[df["score"] >= min_score].head(
            top_n)  # drop rackets below the threshold

        if df.empty:
            return {
                "status": "no_good_match",
                "note": (
                    f"There are rackets within the {max_price} EUR budget, but none is close enough "
                    "to your needs. Try raising the budget or relaxing some requirements."
                ),
                "results": [],
                "cheapest_match": self._cheapest_match(level, play_style, balance, stiffness, min_score),
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


class FindRacket:
    def __init__(self, repo):
        self.repo = repo

    def __call__(self, name: str, limit: int = 5) -> dict:
        df = self.repo.find_by_name(name, limit)
        if df.empty:
            return {"status": "not_found",
                    "note": f"No racket whose name contains '{name}' in the data.", "results": []}
        return {"status": "found", "note": "", "results": json.loads(df.to_json(orient="records"))}
