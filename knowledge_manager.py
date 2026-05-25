import os
import json
import logging
from typing import Dict, Any, Optional
from document_indexer import DocumentIndexer

logger = logging.getLogger(__name__)


class KnowledgeManager:
    """Manages profile-based context injection and local document search."""

    def __init__(self, knowledge_dir="knowledge", indexer: DocumentIndexer = None):
        self.knowledge_dir = knowledge_dir
        if not os.path.exists(self.knowledge_dir):
            os.makedirs(self.knowledge_dir)
        self.indexer = indexer or DocumentIndexer(os.path.join(knowledge_dir, "docs"))

    def get_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        if not profile_name:
            return None
        path = os.path.join(self.knowledge_dir, f"{profile_name}.json")
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load profile '%s': %s", profile_name, e)
                return None
        return None

    def search_docs(self, query: str):
        return self.indexer.search(query)

    def list_profiles(self):
        return [f.replace(".json", "") for f in os.listdir(self.knowledge_dir) if f.endswith(".json")]

    def save_profile(self, profile_name: str, data: Dict[str, Any]):
        path = os.path.join(self.knowledge_dir, f"{profile_name}.json")
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Profile '%s' saved", profile_name)
        except Exception as e:
            logger.error("Failed to save profile '%s': %s", profile_name, e)
