import os
import json
import numpy as np
from typing import List, Dict, Any

class DocumentIndexer:
    """Light-Vector RAG: Scalable semantic search using Numpy."""
    def __init__(self, docs_dir="knowledge/docs"):
        self.docs_dir = docs_dir
        if not os.path.exists(self.docs_dir): os.makedirs(self.docs_dir)

    def _embed(self, text: str):
        vector = np.zeros(128)
        words = text.lower().split()
        for w in words:
            idx = hash(w) % 128
            vector[idx] += 1
        norm = np.linalg.norm(vector)
        return vector / norm if norm > 0 else vector

    def search(self, query: str, limit=5) -> List[Dict[str, Any]]:
        query_vec = self._embed(query)
        scored_results = []

        for filename in os.listdir(self.docs_dir):
            if filename.endswith(".txt") or filename.endswith(".md"):
                path = os.path.join(self.docs_dir, filename)
                try:
                    with open(path, 'r') as f:
                        content = f.read()
                        doc_vec = self._embed(content)
                        score = np.dot(query_vec, doc_vec)
                        scored_results.append((score, filename, content[:800]))
                except Exception: pass

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [{"title": r[1], "snippet": r[2], "score": float(r[0])} for r in scored_results if r[0] > 0.01][:limit]
