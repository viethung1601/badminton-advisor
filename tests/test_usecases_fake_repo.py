import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pandas as pd
from badminton.domain.usecases.racket import RecommendRacket


class FakeRacketRepo:
    def find_under_budget(self, max_price):
        df = pd.DataFrame([{"racket_id": 1, "name": "A", "brand": "X", "balance": "even",
                            "stiffness": "medium", "price_eur": 50.0,
                            "level": "beginner", "play_style": "attack"}])
        return df[df.price_eur <= max_price]


def test_exact_match():
    res = RecommendRacket(FakeRacketRepo())(level="beginner", play_style="attack", max_price=60)
    assert res["status"] == "exact" and res["results"][0]["name"] == "A"


def test_nothing_in_budget():
    res = RecommendRacket(FakeRacketRepo())(level="beginner", play_style="attack", max_price=10)
    assert res["status"] == "no_rackets_in_budget"