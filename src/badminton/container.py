"""Composition root: the ONLY module that knows both the domain and the data layer."""
from dataclasses import dataclass
from functools import lru_cache

from badminton.config import DB_PATH, KNOWLEDGE_CSV, KNOWLEDGE_EMB
from badminton.data.embedding_knowledge_index import EmbeddingKnowledgeIndex
from badminton.data.sqlite_racket_repo import SqliteRacketRepository
from badminton.data.sqlite_shoe_repo import SqliteShoeRepository
from badminton.domain.usecases.catalog import ListRackets, ListShoes
from badminton.domain.usecases.knowledge import SearchKnowledge
from badminton.domain.usecases.racket import FindRacket, RecommendRacket
from badminton.domain.usecases.shoes import FindShoe, RecommendShoes


@dataclass(frozen=True)
class UseCases:
    recommend_racket: RecommendRacket
    find_racket: FindRacket
    recommend_shoes: RecommendShoes
    find_shoe: FindShoe
    search_knowledge: SearchKnowledge
    list_rackets: ListRackets
    list_shoes: ListShoes


def build_usecases(db_path=DB_PATH, knowledge_csv=KNOWLEDGE_CSV,
                   knowledge_emb=KNOWLEDGE_EMB) -> UseCases:
    rackets = SqliteRacketRepository(db_path)
    shoes = SqliteShoeRepository(db_path)
    index = EmbeddingKnowledgeIndex(knowledge_csv, knowledge_emb)   # model loads lazily
    return UseCases(
        recommend_racket=RecommendRacket(rackets), find_racket=FindRacket(rackets),
        recommend_shoes=RecommendShoes(shoes), find_shoe=FindShoe(shoes),
        search_knowledge=SearchKnowledge(index),
        list_rackets=ListRackets(rackets), list_shoes=ListShoes(shoes),
    )


@lru_cache(maxsize=1)
def get_usecases() -> UseCases:
    return build_usecases()