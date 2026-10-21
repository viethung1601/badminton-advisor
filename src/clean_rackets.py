"""Bước 3: đọc, kiểm tra, làm sạch rackets.csv.

Chạy: python clean_rackets.py
"""
from pathlib import Path
from config import RAW, PROCESSED
import pandas as pd


# "Hợp đồng dữ liệu": mỗi cột chỉ được phép nhận những giá trị này.
ALLOWED = {
    "weight_class": {"2U", "3U", "4U", "5U"},
    "balance": {"head_light", "even", "head_heavy"},
    "stiffness": {"flexible", "medium", "stiff"},
    "level": {"beginner", "intermediate", "advanced"},
    "play_style": {"attack", "speed", "control", "allround"},
}
# Cùng một hãng nhưng mỗi shop viết một kiểu -> gom về 1 tên chuẩn.
BRAND_MAP = {"lining": "Li-Ning", "li-ning": "Li-Ning", "yonex": "Yonex",
             "victor": "Victor", "mizuno": "Mizuno", "proace": "Proace",
             "apacs": "Apacs", "flypower": "FlyPower"}


def main() -> None:
    df = pd.read_csv(RAW)
    print(f"Đọc {len(df)} dòng, {df.shape[1]} cột\n")

    # 1) Chuẩn hóa chuỗi: bỏ khoảng trắng thừa, categorical -> chữ thường
    df["name"] = df["name"].str.strip()
    df["brand"] = df["brand"].str.strip().str.lower().map(
        BRAND_MAP).fillna(df["brand"])
    for col in ALLOWED:
        df[col] = df[col].str.strip().str.lower() if col != "weight_class" \
            else df[col].str.strip().str.upper()

    # 2) Kiểm tra: thiếu, trùng, giá trị lạ
    print("Giá trị thiếu mỗi cột:\n", df.isna().sum().to_string(), "\n")
    print("Tên vợt trùng:", df["name"].str.lower().duplicated().sum(), "\n")

    bad = pd.Series(False, index=df.index)
    for col, ok in ALLOWED.items():
        mask = ~df[col].isin(ok)
        if mask.any():
            print(f"[SAI] cột '{col}':")
            print(df.loc[mask, ["name", col]].to_string(index=False), "\n")
        bad |= mask
    df["needs_review"] = bad

    # 3) Cột nào không có tác dụng phân biệt?
    print("Số giá trị khác nhau mỗi cột:\n", df.nunique().to_string(), "\n")
    print("Giá (EUR):", df["price_eur"].describe()
          [["min", "50%", "max"]].to_dict())

    # 4) Thêm id ổn định để sau này làm khóa chính trong SQLite
    df.insert(0, "racket_id", range(1, len(df) + 1))
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED, index=False)
    print(f"\nĐã lưu {PROCESSED} ({int(bad.sum())} dòng cần xem lại)")


if __name__ == "__main__":
    main()
