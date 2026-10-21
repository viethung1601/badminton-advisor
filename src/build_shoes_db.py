"""Bước 13b: nạp shoes_clean.csv vào bảng shoes của data/badminton.db

Chạy: python src/build_shoes_db.py   (cần chạy build_db.py trước để có file DB)
Chạy lại nhiều lần được: mỗi lần xây lại bảng shoes, không đụng bảng rackets.
"""
import sqlite3

import pandas as pd

from clean_shoes import ALLOWED, OUT_SHOES
from config import DB_PATH


def in_list(values: set[str]) -> str:
    return ", ".join(f"'{v}'" for v in sorted(values))


SCHEMA = f"""
DROP TABLE IF EXISTS shoes;
CREATE TABLE shoes (
    shoe_id            INTEGER PRIMARY KEY,
    name               TEXT    NOT NULL UNIQUE,
    brand              TEXT    NOT NULL,
    gender             TEXT    NOT NULL CHECK (gender IN ({in_list(ALLOWED['gender'])})),
    size_min_eu        REAL    NOT NULL CHECK (size_min_eu > 0),
    size_max_eu        REAL    NOT NULL CHECK (size_max_eu >= size_min_eu),
    weight_g           REAL    CHECK (weight_g > 0),
    weight_ref_size_eu REAL,
    width              TEXT    CHECK (width IS NULL OR width IN ({in_list(ALLOWED['width'])})),
    price_eur          REAL    NOT NULL CHECK (price_eur > 0),
    note               TEXT
);
CREATE INDEX idx_shoes_gender ON shoes(gender);
"""

COLS = ["shoe_id", "name", "brand", "gender", "size_min_eu", "size_max_eu",
        "weight_g", "weight_ref_size_eu", "width", "price_eur", "note"]


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit("Chưa có badminton.db. Chạy python src/build_db.py trước.")

    df = pd.read_csv(OUT_SHOES, encoding="utf-8")
    n_bad = int(df["needs_review"].sum())
    if n_bad:
        print(f"Bỏ qua {n_bad} dòng needs_review (sửa shoes.csv rồi chạy lại clean_shoes.py)")
    df = df[~df["needs_review"]]

    # Ô trống trong pandas là NaN; SQLite cần None để lưu thành NULL.
    rows = df[COLS].astype(object).where(df[COLS].notna(), None)

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            f"INSERT INTO shoes ({', '.join(COLS)}) VALUES ({', '.join('?' * len(COLS))})",
            rows.itertuples(index=False, name=None),
        )
        print(f"Đã nạp {conn.execute('SELECT COUNT(*) FROM shoes').fetchone()[0]} giày\n")

        print("Số giày theo gender và width:")
        for row in conn.execute(
            "SELECT gender, width, COUNT(*) FROM shoes GROUP BY gender, width ORDER BY 1, 2"
        ):
            print("  ", row)

        # Thử đúng truy vấn lọc cứng sẽ dùng sau này: nữ, size 38
        print("\nGiày cho nữ size 38 (women hoặc unisex, còn size 38):")
        for row in conn.execute(
            "SELECT name, gender, width, price_eur FROM shoes "
            "WHERE gender IN (?, 'unisex') AND size_min_eu <= ? AND size_max_eu >= ? "
            "ORDER BY price_eur",
            ("women", 38, 38),
        ):
            print("  ", row)


if __name__ == "__main__":
    main()