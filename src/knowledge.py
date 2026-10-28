import sys
import numpy as np
import pandas as pd
import hashlib
from sentence_transformers import SentenceTransformer
from config import ROOT

CSV_PATH = str(ROOT/"data"/"raw"/"knowledge.csv")
EMB_PATH = str(ROOT/"data"/"knowledge_emb.npy")
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
MIN_KNOWLEDGE_SCORE = 0.2  # only filters out off-topic questions; see the limitations below
_model = None

def _embed_text(df):
    """What the model sees: a short title (context) followed by the passage text."""
    return (df["title"] + ". " + df["text"]).tolist()

def _fingerprint(df):
    return hashlib.sha256("\n".join(_embed_text(df)).encode("utf-8")).hexdigest()

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
        # default is 128 tokens; long passages (k04, k10) would have their tails cut off
        _model.max_seq_length = 256
    return _model


def load_chunks():
    return pd.read_csv(CSV_PATH)


def build_index():
    df = load_chunks()
    emb = _get_model().encode(_embed_text(df), normalize_embeddings=True)
    np.save(EMB_PATH, emb)
    open(EMB_PATH + ".hash", "w").write(_fingerprint(df))
    print(f"Computed {emb.shape[0]} vectors, {emb.shape[1]} dimensions each")


def search(query, k=3):
    df = load_chunks()
    emb = np.load(EMB_PATH)
    if open(EMB_PATH + ".hash").read() != _fingerprint(df):
      raise RuntimeError("The CSV has changed, re-run: python src/knowledge.py build")
    q = _get_model().encode([query], normalize_embeddings=True)[0]
    scores = emb @ q  # vectors are normalized, so the dot product = cosine similarity
    top = np.argsort(-scores)[:k]
    return [
        {
            "id": df.loc[i, "id"],
            "topic": df.loc[i, "topic"],
            "score": float(scores[i]),
            "text": df.loc[i, "text"],
            "source_url": df.loc[i, "source_url"],
        }
        for i in top
    ]


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

def search_knowledge(query, k=3):
    """Tool for the agent: returns knowledge passages, or says the knowledge base has nothing."""
    try:
        hits = [r for r in search(query, k=k) if r["score"] >= MIN_KNOWLEDGE_SCORE]
    except Exception as e:  # e.g. forgot to run build
        return {"status": "error", "message": str(e)}
    if not hits:
        return {"status": "no_relevant_knowledge"}
    return {
        "status": "ok",
        "passages": [
            {"id": r["id"], "text": r["text"], "source_url": r["source_url"]}
            for r in hits
        ],
    }

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        build_index()
    else:
        for q in TEST_QUERIES:
            print(f"\n=== {q}")
            for r in search(q):
                print(f"  {r['score']:.3f}  {r['id']} ({r['topic']})  {r['text'][:70]}...")