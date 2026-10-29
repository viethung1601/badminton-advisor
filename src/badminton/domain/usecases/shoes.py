import json
import pandas as pd
from badminton.domain.shoe_scoring import WIDTH, W_WIDTH, W_LIGHT, GENDERS, explain


class RecommendShoes:
    def __init__(self, repo):
        self.repo = repo

    def __call__(self, gender, size_eu, prefer_light=False, width=None,
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

        df = self.repo.find_fitting(gender, size_eu, max_price)
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


class FindShoe:
    def __init__(self, repo):
        self.repo = repo

    def __call__(self, name: str, limit: int = 5) -> dict:
        df = self.repo.find_by_name(name, limit)
        if df.empty:
            return {"status": "not_found",
                    "note": f"No shoe whose name contains '{name}' in the data.", "results": []}
        return {"status": "found", "note": "", "results": json.loads(df.to_json(orient="records"))}
