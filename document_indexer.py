import os
import json
from typing import List, Dict

class DocumentIndexer:
    """Simple local document search (Mini-RAG)."""
    def __init__(self, docs_dir="knowledge/docs"):
        self.docs_dir = docs_dir
        if not os.path.exists(self.docs_dir):
            os.makedirs(self.docs_dir)

    def search(self, query: str, limit=3) -> List[Dict[str, str]]:
        """Keyword-based search across local documents."""
        results = []
        words = query.lower().split()
        if not words: return []

        for filename in os.listdir(self.docs_dir):
            if filename.endswith(".txt") or filename.endswith(".md"):
                path = os.path.join(self.docs_dir, filename)
                try:
                    with open(path, 'r') as f:
                        content = f.read()
                        if any(w in content.lower() for w in words):
                            results.append({"title": filename, "snippet": content[:500]})
                except Exception:
                    pass
        return results[:limit]
