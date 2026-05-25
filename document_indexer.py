import os
import json
import numpy as np
from typing import List, Dict

class DocumentIndexer:
    """Advanced Semantic Search (Simulated Embeddings for M1 optimization)."""
    def __init__(self, docs_dir="knowledge/docs"):
        self.docs_dir = docs_dir
        if not os.path.exists(self.docs_dir): os.makedirs(self.docs_dir)

    def _get_pseudo_embedding(self, text: str):
        """Simulates a lightweight embedding vector for search."""
        # In a full system, this would call a local model or tiny-embeddings API
        # Here we use a simple frequency-based vector representation
        vocab = ["code", "fix", "setup", "install", "research", "competitor", "mail", "send"]
        vector = [text.lower().count(w) for w in vocab]
        norm = np.linalg.norm(vector)
        return vector / norm if norm > 0 else vector

    def search(self, query: str, limit=3) -> List[Dict[str, str]]:
        """Cosine similarity search using pseudo-embeddings."""
        query_vec = self._get_pseudo_embedding(query)
        scored_results = []

        for filename in os.listdir(self.docs_dir):
            if filename.endswith(".txt") or filename.endswith(".md"):
                path = os.path.join(self.docs_dir, filename)
                try:
                    with open(path, 'r') as f:
                        content = f.read()
                        doc_vec = self._get_pseudo_embedding(content)
                        # Cosine similarity
                        score = np.dot(query_vec, doc_vec) if np.linalg.norm(doc_vec) > 0 else 0
                        scored_results.append((score, filename, content[:500]))
                except Exception: pass

        # Sort by score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [{"title": r[1], "snippet": r[2], "score": float(r[0])} for r in scored_results if r[0] > 0][:limit]
