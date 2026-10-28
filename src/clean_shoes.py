"""Step 13a: clean data/raw/shoes.csv -> data/processed/shoes_clean.csv

Run: python src/clean_shoes.py
"""
import csv
from badminton.domain.contracts import SHOE_ALLOWED as ALLOWED
import pandas as pd

from clean_rackets import BRAND_MAP        # shared brand-name normalization
from config import ROOT

RAW_SHOES = ROOT / "data" / "raw" / "shoes.csv"
OUT_SHOES = ROOT / "data" / "processed" / "shoes_clean.csv"

COLUMNS = ["name", "brand", "gender", "size_min_eu", "size_max_eu", "weight_g",
           "weight_ref_size_eu", "width", "price_eur", "note"]

# Data contract for categorical columns. width may be empty (the brand doesn't publish it).

# Plausible ranges for numeric columns: values outside are most likely typos.
RANGES = {
    "size_min_eu": (30, 55), "size_max_eu": (30, 55),
    "weight_g": (150, 500), "weight_ref_size_eu": (30, 55),
    "price_eur": (20, 500),
}


def check_columns() -> bool:
    """Every row must have the right number of cells. pandas silently fills missing cells, so this error wouldn't show up on its own."""
    ok = True
    with open(RAW_SHOES, encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.reader(f), start=1):
            if len(row) != len(COLUMNS):
                print(
                    f"[INVALID] row {i} has {len(row)} cells, expected {len(COLUMNS)}: {row[:3]}...")
                ok = False
    return ok


def main() -> None:
    if not check_columns():
        raise SystemExit(
            "Fix the number of cells in shoes.csv (add/remove commas), then re-run.")

    df = pd.read_csv(RAW_SHOES, encoding="utf-8")
    print(f"Read {len(df)} rows, {df.shape[1]} columns\n")

    # 1) Normalize strings
    for col in ["name", "brand", "gender", "width", "note"]:
        df[col] = df[col].astype("string").str.strip()
    df["gender"] = df["gender"].str.lower()
    df["width"] = df["width"].str.lower()
    mapped = df["brand"].str.lower().map(BRAND_MAP)
    brand_unknown = mapped.isna()
    df["brand"] = mapped.fillna(df["brand"])

    # 2) Validate: each rule produces a mask; the masks are combined into needs_review
    bad = pd.Series(False, index=df.index)

    def flag(mask: pd.Series, msg: str) -> None:
        nonlocal bad
        if mask.any():
            print(f"[INVALID] {msg}:")
            print(df.loc[mask, ["name"]].to_string(index=False), "\n")
        bad |= mask

    flag(df["gender"].isna() | ~df["gender"].isin(
        ALLOWED["gender"]), "gender outside the contract")
    flag(df["width"].notna() & ~df["width"].isin(
        ALLOWED["width"]), "width outside the contract")
    flag(brand_unknown, "brand not in BRAND_MAP")
    flag(df["name"].str.lower().duplicated(keep=False), "duplicate name")
    flag(df["size_min_eu"] > df["size_max_eu"], "size_min greater than size_max")
    for col, (lo, hi) in RANGES.items():
        required = col in ("size_min_eu", "size_max_eu", "price_eur")
        missing = df[col].isna()
        out = df[col].notna() & ~df[col].between(lo, hi)
        flag(out | (missing if required else False),
             f"'{col}' missing or outside [{lo}, {hi}]")
    # Weight and its reference size must come together: if one is present, so must the other.
    flag(df["weight_g"].isna() != df["weight_ref_size_eu"].isna(),
         "only one of weight_g and weight_ref_size_eu is set")

    df["needs_review"] = bad

    # 3) Report missing data (not an error, but it affects reliability)
    print("Missing weight_g:", int(df["weight_g"].isna().sum()),
          "| missing width:", int(df["width"].isna().sum()), "\n")
    print(df.groupby(["gender", "width"],
          dropna=False).size().to_string(), "\n")

    # 4) Stable id: sort by brand + name, then number the rows
    df = df.sort_values(["brand", "name"]).reset_index(drop=True)
    df.insert(0, "shoe_id", df.index + 1)

    OUT_SHOES.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_SHOES, index=False, encoding="utf-8")
    print(
        f"Saved {OUT_SHOES} ({int(df['needs_review'].sum())} rows need review)")


if __name__ == "__main__":
    main()