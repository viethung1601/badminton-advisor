"""Bước 13a: làm sạch data/raw/shoes.csv -> data/processed/shoes_clean.csv

Chạy: python src/clean_shoes.py
"""
import csv

import pandas as pd

from clean_rackets import BRAND_MAP        # dùng chung cách gom tên hãng
from config import ROOT

RAW_SHOES = ROOT / "data" / "raw" / "shoes.csv"
OUT_SHOES = ROOT / "data" / "processed" / "shoes_clean.csv"

COLUMNS = ["name", "brand", "gender", "size_min_eu", "size_max_eu", "weight_g",
           "weight_ref_size_eu", "width", "price_eur", "note"]

# Hợp đồng dữ liệu cho cột phân loại. width được phép trống (hãng không công bố).
ALLOWED = {
    "gender": {"men", "women", "unisex"},
    "width": {"narrow", "standard", "wide"},
}
# Khoảng hợp lý cho cột số: ngoài khoảng này thì nhiều khả năng nhập sai.
RANGES = {
    "size_min_eu": (30, 55), "size_max_eu": (30, 55),
    "weight_g": (150, 500), "weight_ref_size_eu": (30, 55),
    "price_eur": (20, 500),
}


def check_columns() -> bool:
    """Mỗi dòng phải đủ số ô. pandas tự điền ô thiếu nên lỗi này không tự lộ ra."""
    ok = True
    with open(RAW_SHOES, encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.reader(f), start=1):
            if len(row) != len(COLUMNS):
                print(f"[SAI] dòng {i} có {len(row)} ô, cần {len(COLUMNS)}: {row[:3]}...")
                ok = False
    return ok


def main() -> None:
    if not check_columns():
        raise SystemExit("Sửa số ô trong shoes.csv (thêm/bớt dấu phẩy) rồi chạy lại.")

    df = pd.read_csv(RAW_SHOES, encoding="utf-8")
    print(f"Đọc {len(df)} dòng, {df.shape[1]} cột\n")

    # 1) Chuẩn hóa chuỗi
    for col in ["name", "brand", "gender", "width", "note"]:
        df[col] = df[col].astype("string").str.strip()
    df["gender"] = df["gender"].str.lower()
    df["width"] = df["width"].str.lower()
    mapped = df["brand"].str.lower().map(BRAND_MAP)
    brand_unknown = mapped.isna()
    df["brand"] = mapped.fillna(df["brand"])

    # 2) Kiểm tra: mỗi quy tắc cho ra một mask, gộp lại thành needs_review
    bad = pd.Series(False, index=df.index)

    def flag(mask: pd.Series, msg: str) -> None:
        nonlocal bad
        if mask.any():
            print(f"[SAI] {msg}:")
            print(df.loc[mask, ["name"]].to_string(index=False), "\n")
        bad |= mask

    flag(df["gender"].isna() | ~df["gender"].isin(ALLOWED["gender"]), "gender ngoài hợp đồng")
    flag(df["width"].notna() & ~df["width"].isin(ALLOWED["width"]), "width ngoài hợp đồng")
    flag(brand_unknown, "hãng chưa có trong BRAND_MAP")
    flag(df["name"].str.lower().duplicated(keep=False), "tên trùng")
    flag(df["size_min_eu"] > df["size_max_eu"], "size_min lớn hơn size_max")
    for col, (lo, hi) in RANGES.items():
        required = col in ("size_min_eu", "size_max_eu", "price_eur")
        missing = df[col].isna()
        out = df[col].notna() & ~df[col].between(lo, hi)
        flag(out | (missing if required else False), f"'{col}' thiếu hoặc ngoài [{lo}, {hi}]")
    # Cân nặng và size tham chiếu phải đi cùng nhau: có cái này thì phải có cái kia.
    flag(df["weight_g"].isna() != df["weight_ref_size_eu"].isna(),
         "weight_g và weight_ref_size_eu chỉ có một")

    df["needs_review"] = bad

    # 3) Báo cáo dữ liệu thiếu (không phải lỗi, nhưng ảnh hưởng độ tin cậy)
    print("Thiếu weight_g:", int(df["weight_g"].isna().sum()),
          "| thiếu width:", int(df["width"].isna().sum()), "\n")
    print(df.groupby(["gender", "width"], dropna=False).size().to_string(), "\n")

    # 4) Id ổn định: sắp theo hãng + tên rồi đánh số
    df = df.sort_values(["brand", "name"]).reset_index(drop=True)
    df.insert(0, "shoe_id", df.index + 1)

    OUT_SHOES.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_SHOES, index=False, encoding="utf-8")
    print(f"Đã lưu {OUT_SHOES} ({int(df['needs_review'].sum())} dòng cần xem lại)")


if __name__ == "__main__":
    main()