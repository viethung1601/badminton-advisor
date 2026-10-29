from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "rackets.csv"
PROCESSED = ROOT / "data" / "processed" / "rackets_clean.csv"
DB_PATH = ROOT / "data" / "badminton.db"

