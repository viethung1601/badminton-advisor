"""Step 3: read, validate and clean rackets.csv.

Run: python src/clean_rackets.py
"""
from pathlib import Path
from config import RAW, PROCESSED
import pandas as pd


# "Data contract": each column may only take these values.
ALLOWED = {
    "weight_class": {"2U", "3U", "4U", "5U"},
    "balance": {"head_light", "even", "head_heavy"},
    "stiffness": {"flexible", "medium", "stiff"},
    "level": {"beginner", "intermediate", "advanced"},
    "play_style": {"attack", "speed", "control", "allround"},
}
# The same brand is spelled differently by each shop -> map it to one canonical name.
BRAND_MAP = {"lining": "Li-Ning", "li-ning": "Li-Ning", "yonex": "Yonex",
             "victor": "Victor", "mizuno": "Mizuno", "proace": "Proace",
             "apacs": "Apacs", "flypower": "FlyPower"}


def main() -> None:
    df = pd.read_csv(RAW)
    print(f"Read {len(df)} rows, {df.shape[1]} columns\n")

    # 1) Normalize strings: strip extra whitespace, categoricals -> lowercase
    df["name"] = df["name"].str.strip()
    df["brand"] = df["brand"].str.strip().str.lower().map(
        BRAND_MAP).fillna(df["brand"])
    for col in ALLOWED:
        df[col] = df[col].str.strip().str.lower() if col != "weight_class" \
            else df[col].str.strip().str.upper()

    # 2) Validate: missing values, duplicates, unexpected values
    print("Missing values per column:\n", df.isna().sum().to_string(), "\n")
    print("Duplicate racket names:",
          df["name"].str.lower().duplicated().sum(), "\n")

    bad = pd.Series(False, index=df.index)
    for col, ok in ALLOWED.items():
        mask = ~df[col].isin(ok)
        if mask.any():
            print(f"[INVALID] column '{col}':")
            print(df.loc[mask, ["name", col]].to_string(index=False), "\n")
        bad |= mask
    df["needs_review"] = bad

    # 3) Which columns don't help tell rows apart?
    print("Distinct values per column:\n", df.nunique().to_string(), "\n")
    print("Price (EUR):", df["price_eur"].describe()
          [["min", "50%", "max"]].to_dict())

    # 4) Add a stable id to use as the primary key in SQLite later
    df.insert(0, "racket_id", range(1, len(df) + 1))
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED, index=False)
    print(f"\nSaved {PROCESSED} ({int(bad.sum())} rows need review)")


if __name__ == "__main__":
    main()
