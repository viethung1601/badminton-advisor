import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from badminton.domain.usecases.knowledge import SearchKnowledge


class FakeIndex:
    def __init__(self, hits=None, error=None):
        self.hits, self.error = hits or [], error

    def search(self, query, k=3):
        if self.error:
            raise self.error
        return self.hits


HIT = {"id": "k01", "topic": "balance", "score": 0.8, "text": "t", "source_url": "u"}


def test_ok():
    res = SearchKnowledge(FakeIndex([HIT]))("anything")
    assert res["status"] == "ok" and res["passages"][0]["id"] == "k01"


def test_low_score_is_filtered():
    res = SearchKnowledge(FakeIndex([{**HIT, "score": 0.1}]))("anything")
    assert res["status"] == "no_relevant_knowledge"


def test_error_is_reported():
    res = SearchKnowledge(FakeIndex(error=RuntimeError("boom")))("anything")
    assert res == {"status": "error", "message": "boom"}