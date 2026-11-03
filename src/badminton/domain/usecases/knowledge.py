MIN_KNOWLEDGE_SCORE = 0.2


class SearchKnowledge:
    def __init__(self, index):
        self.index = index

    def __call__(self, query, k=3):
        """Tool for the agent: returns knowledge passages, or says the knowledge base has nothing."""
        try:
            hits = [r for r in self.index.search(query, k=k)
                    if r["score"] >= MIN_KNOWLEDGE_SCORE]
        except Exception as e:  # e.g. forgot to run build
            return {"status": "error", "message": str(e)}
        if not hits:
            return {"status": "no_relevant_knowledge"}
        return {
            "status": "ok",
            "passages": [
                {"id": r["id"], "text": r["text"],
                 "source_url": r["source_url"]}
                for r in hits
            ],
        }
