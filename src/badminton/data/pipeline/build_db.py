"""Step 4: load rackets_clean.csv into SQLite (data/badminton.db).

Run: python src/build_db.py
The script can be re-run any number of times: it rebuilds the DB from the CSV each time.
"""
import sqlite3

import pandas as pd

from badminton.domain.contracts import RACKET_ALLOWED as ALLOWED   # shared "data contract"
from badminton.config import DB_PATH, PROCESSED


def in_list(values: set[str]) -> str:
    return ", ".join(f"'{v}'" for v in sorted(values))


# Each categorical column has a CHECK constraint generated from ALLOWED -> the DB rejects invalid values itself.
SCHEMA = f"""
CREATE TABLE rackets (
    racket_id        INTEGER PRIMARY KEY,
    name             TEXT    NOT NULL UNIQUE,
    brand            TEXT    NOT NULL,
    weight_class     TEXT    NOT NULL CHECK (weight_class IN ({in_list(ALLOWED['weight_class'])})),
    balance          TEXT    NOT NULL CHECK (balance      IN ({in_list(ALLOWED['balance'])})),
    stiffness        TEXT    NOT NULL CHECK (stiffness    IN ({in_list(ALLOWED['stiffness'])})),
    price_eur        REAL    NOT NULL CHECK (price_eur > 0),
    level            TEXT    NOT NULL CHECK (level        IN ({in_list(ALLOWED['level'])})),
    play_style       TEXT    NOT NULL CHECK (play_style   IN ({in_list(ALLOWED['play_style'])})),
    source_url       TEXT,   -- may be empty: use NULL when not available yet
    price_checked_at TEXT    -- date the price was checked, format YYYY-MM-DD
);
CREATE INDEX idx_rackets_level ON rackets(level);
"""


def main() -> None:
    df = pd.read_csv(PROCESSED)

    # Only load rows that passed validation, then drop the helper column needs_review
    n_bad = int(df["needs_review"].sum())
    if n_bad:
        print(
            f"Skipping {n_bad} needs_review rows (fix them in rackets.csv, then re-run clean_rackets.py)")
    df = df[~df["needs_review"]].drop(columns="needs_review")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # the DB is a product generated from the CSV -> rebuild it from scratch
    DB_PATH.unlink(missing_ok=True)

    # with = auto-commit; on error it rolls back automatically
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO rackets (racket_id, name, brand, weight_class, balance, stiffness,"
            " price_eur, level, play_style) VALUES (?,?,?,?,?,?,?,?,?)",
            df[["racket_id", "name", "brand", "weight_class", "balance", "stiffness",
                "price_eur", "level", "play_style"]].itertuples(index=False, name=None),
        )

        # Verify with SQL: this is also how you will "ask" the DB questions in later steps
        print(
            f"Loaded {conn.execute('SELECT COUNT(*) FROM rackets').fetchone()[0]} rackets into {DB_PATH}\n")
        print("Rackets by level and play_style:")
        for row in conn.execute(
            "SELECT level, play_style, COUNT(*) FROM rackets GROUP BY level, play_style ORDER BY 1, 2"
        ):
            print("  ", row)
        print("\nBeginner/intermediate rackets under 100 EUR:")
        for row in conn.execute(
            "SELECT name, brand, price_eur FROM rackets "
            "WHERE level IN ('beginner','intermediate') AND price_eur < 100 ORDER BY price_eur"
        ):
            print("  ", row)


if __name__ == "__main__":
    main()