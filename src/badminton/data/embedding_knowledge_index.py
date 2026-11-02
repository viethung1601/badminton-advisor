import hashlib

import numpy as np
import pandas as pd

class EmbeddingKnowledgeIndex:
    def __init__(self, csv_path, emb_path,
                 model_name="paraphrase-multilingual-MiniLM-L12-v2"):
        self.csv_path = str(csv_path)
        self.emb_path = str(emb_path)
        self.model_name = model_name
        self._model = None

    def _embed_text(self, df):
        """What the model sees: a short title (context) followed by the passage text."""
        return (df["title"] + ". " + df["text"]).tolist()

    def _fingerprint(self, df):
        return hashlib.sha256("\n".join(self._embed_text(df)).encode("utf-8")).hexdigest()

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            # default is 128 tokens; long passages (k04, k10) would have their tails cut off
            self._model.max_seq_length = 256
        return self._model

    def load_chunks(self):
        return pd.read_csv(self.csv_path)

    def build(self):
        df = self.load_chunks()
        emb = self._get_model().encode(self._embed_text(df), normalize_embeddings=True)
        np.save(self.emb_path, emb)
        open(self.emb_path + ".hash", "w").write(self._fingerprint(df))
        print(
            f"Computed {emb.shape[0]} vectors, {emb.shape[1]} dimensions each")

    def search(self, query, k=3):
        df = self.load_chunks()
        emb = np.load(self.emb_path)
        if open(self.emb_path + ".hash").read() != self._fingerprint(df):
            raise RuntimeError(
                "The CSV has changed, re-run: python src/knowledge.py build")
        q = self._get_model().encode([query], normalize_embeddings=True)[0]
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
