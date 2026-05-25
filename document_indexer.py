import os
import math
import re
import logging
from typing import List, Dict
from collections import Counter

logger = logging.getLogger(__name__)

STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "and", "but", "or", "nor", "not", "so", "yet",
    "it", "its", "this", "that", "these", "those", "i", "me", "my",
    "we", "our", "you", "your", "he", "him", "his", "she", "her",
})


def tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]


class DocumentIndexer:
    """TF-IDF based document search for local knowledge base."""

    def __init__(self, docs_dir="knowledge/docs"):
        self.docs_dir = docs_dir
        if not os.path.exists(self.docs_dir):
            os.makedirs(self.docs_dir)
        self._documents: Dict[str, str] = {}
        self._doc_tf: Dict[str, Counter] = {}
        self._idf: Dict[str, float] = {}
        self._rebuild_index()

    def _rebuild_index(self):
        self._documents.clear()
        self._doc_tf.clear()

        for filename in os.listdir(self.docs_dir):
            if filename.endswith((".txt", ".md")):
                path = os.path.join(self.docs_dir, filename)
                try:
                    with open(path, "r") as f:
                        content = f.read()
                    self._documents[filename] = content
                    tokens = tokenize(content)
                    tf = Counter(tokens)
                    total = len(tokens) if tokens else 1
                    self._doc_tf[filename] = Counter({t: c / total for t, c in tf.items()})
                except Exception:
                    logger.warning("Failed to index %s", filename)

        self._compute_idf()
        logger.info("Indexed %d documents", len(self._documents))

    def _compute_idf(self):
        self._idf.clear()
        n_docs = len(self._documents)
        if n_docs == 0:
            return

        all_terms: set = set()
        for tf in self._doc_tf.values():
            all_terms.update(tf.keys())

        for term in all_terms:
            doc_count = sum(1 for tf in self._doc_tf.values() if term in tf)
            self._idf[term] = math.log((n_docs + 1) / (doc_count + 1)) + 1

    def _tfidf_vector(self, tokens: List[str]) -> Dict[str, float]:
        tf = Counter(tokens)
        total = len(tokens) if tokens else 1
        return {t: (c / total) * self._idf.get(t, 1.0) for t, c in tf.items()}

    def _cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        common = set(vec_a.keys()) & set(vec_b.keys())
        if not common:
            return 0.0

        dot = sum(vec_a[k] * vec_b[k] for k in common)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query: str, limit=3) -> List[Dict[str, str]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        query_vec = self._tfidf_vector(query_tokens)
        scored_results = []

        for filename, content in self._documents.items():
            doc_tokens = tokenize(content)
            doc_vec = self._tfidf_vector(doc_tokens)
            score = self._cosine_similarity(query_vec, doc_vec)
            if score > 0:
                scored_results.append((score, filename, content[:500]))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [
            {"title": r[1], "snippet": r[2], "score": round(float(r[0]), 4)}
            for r in scored_results[:limit]
        ]

    def add_document(self, filename: str, content: str):
        path = os.path.join(self.docs_dir, filename)
        with open(path, "w") as f:
            f.write(content)
        self._rebuild_index()
