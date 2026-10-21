"""Bước 4: nạp rackets_clean.csv vào SQLite (data/badminton.db).

Chạy: python src/build_db.py
Script có thể chạy lại nhiều lần: mỗi lần xây lại DB từ CSV.
"""
import sqlite3

import pandas as pd

from clean_rackets import ALLOWED          # dùng chung "hợp đồng dữ liệu"
from config import DB_PATH, PROCESSED


def in_list(values: set[str]) -> str:
    return ", ".join(f"'{v}'" for v in sorted(values))


# Mỗi cột categorical có một ràng buộc CHECK sinh từ ALLOWED -> DB tự từ chối giá trị sai.
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
    source_url       TEXT,   -- cho phép trống: chưa có thì để NULL
    price_checked_at TEXT    -- ngày kiểm tra giá, dạng YYYY-MM-DD
);
CREATE INDEX idx_rackets_level ON rackets(level);
"""


def main() -> None:
    df = pd.read_csv(PROCESSED)

    # Chỉ nạp dòng đã qua kiểm tra, rồi bỏ cột phụ needs_review
    n_bad = int(df["needs_review"].sum())
    if n_bad:
        print(
            f"Bỏ qua {n_bad} dòng needs_review (sửa trong rackets.csv rồi chạy lại clean_rackets.py)")
    df = df[~df["needs_review"]].drop(columns="needs_review")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # DB là sản phẩm sinh ra từ CSV -> xây lại từ đầu
    DB_PATH.unlink(missing_ok=True)

    # with = tự commit, lỗi thì tự rollback
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO rackets (racket_id, name, brand, weight_class, balance, stiffness,"
            " price_eur, level, play_style) VALUES (?,?,?,?,?,?,?,?,?)",
            df[["racket_id", "name", "brand", "weight_class", "balance", "stiffness",
                "price_eur", "level", "play_style"]].itertuples(index=False, name=None),
        )

        # Kiểm tra bằng SQL: đây cũng là cách bạn sẽ "hỏi" DB ở các bước sau
        print(
            f"Đã nạp {conn.execute('SELECT COUNT(*) FROM rackets').fetchone()[0]} vợt vào {DB_PATH}\n")
        print("Số vợt theo level và play_style:")
        for row in conn.execute(
            "SELECT level, play_style, COUNT(*) FROM rackets GROUP BY level, play_style ORDER BY 1, 2"
        ):
            print("  ", row)
        print("\nVợt beginner/intermediate dưới 100 EUR:")
        for row in conn.execute(
            "SELECT name, brand, price_eur FROM rackets "
            "WHERE level IN ('beginner','intermediate') AND price_eur < 100 ORDER BY price_eur"
        ):
            print("  ", row)


if __name__ == "__main__":
    main()
