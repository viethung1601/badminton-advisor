import sys
import numpy as np
import pandas as pd
import hashlib
from sentence_transformers import SentenceTransformer
from config import ROOT

CSV_PATH = str(ROOT/"data"/"raw"/"knowledge.csv")
EMB_PATH = str(ROOT/"data"/"knowledge_emb.npy")
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
MIN_KNOWLEDGE_SCORE = 0.2  # chỉ lọc câu lạc đề; xem phần giới hạn bên dưới
_model = None

def _fingerprint(df):
    return hashlib.sha256("\n".join(df["text"]).encode("utf-8")).hexdigest()

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
        # mặc định 128 token; đoạn dài (k04, k10) sẽ bị cắt đuôi
        _model.max_seq_length = 256
    return _model


def load_chunks():
    return pd.read_csv(CSV_PATH)


def build_index():
    df = load_chunks()
    emb = _get_model().encode(df["text"].tolist(), normalize_embeddings=True)
    np.save(EMB_PATH, emb)
    open(EMB_PATH + ".hash", "w").write(_fingerprint(df))
    print(f"Đã tính {emb.shape[0]} vector, mỗi vector {emb.shape[1]} chiều")


def search(query, k=3):
    df = load_chunks()
    emb = np.load(EMB_PATH)
    if open(EMB_PATH + ".hash").read() != _fingerprint(df):
      raise RuntimeError("CSV đã đổi, chạy lại: python src/knowledge.py build")
    q = _get_model().encode([query], normalize_embeddings=True)[0]
    scores = emb @ q  # vector đã chuẩn hóa nên tích vô hướng = cosine
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
    "head heavy khác head light thế nào",
    "vợt cứng có hợp người mới không",
    "3U với 4U cái nào nặng hơn",
    "căng dây bao nhiêu thì tốt cho người mới",
    "Yonex Astrox 99 Pro giá bao nhiêu",
    "hôm nay thời tiết Frankfurt thế nào",
    "cách đánh smash cho đúng kỹ thuật",
    "nên chọn giày cầu lông nào",
    "Yonex hay Victor tốt hơn",
    "vợt nặng đầu có dễ mỏi tay không",
]

def search_knowledge(query, k=3):
    """Tool cho agent: trả các đoạn kiến thức, hoặc báo kho không có."""
    try:
        hits = [r for r in search(query, k=k) if r["score"] >= MIN_KNOWLEDGE_SCORE]
    except Exception as e:  # ví dụ quên chạy build
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