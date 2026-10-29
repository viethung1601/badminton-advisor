import sys

from badminton.config import KNOWLEDGE_CSV, KNOWLEDGE_EMB
from badminton.data.embedding_knowledge_index import EmbeddingKnowledgeIndex
from badminton.domain.usecases.knowledge import SearchKnowledge

_index = EmbeddingKnowledgeIndex(KNOWLEDGE_CSV, KNOWLEDGE_EMB)
search = _index.search               # probe_eval.py đang dùng
build_index = _index.build
search_knowledge = SearchKnowledge(_index)   # agent.py và mcp_server.py đang dùng

TEST_QUERIES = [
    "what is the difference between head heavy and head light",
    "is a stiff racket suitable for beginners",
    "which is heavier, 3U or 4U",
    "what string tension is good for beginners",
    "how much is the Yonex Astrox 99 Pro",
    "what's the weather like in Frankfurt today",
    "how to do a smash with proper technique",
    "which badminton shoes should I choose",
    "which is better, Yonex or Victor",
    "does a head heavy racket tire your arm easily",
]

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        build_index()
    else:
        for q in TEST_QUERIES:
            print(f"\n=== {q}")
            for r in search(q):
                print(f"  {r['score']:.3f}  {r['id']} ({r['topic']})  {r['text'][:70]}...")