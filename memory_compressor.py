import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class MemoryCompressor:
    """Summarizes long histories into high-level cognitive snapshots."""

    def __init__(self, vision_client):
        self.vision = vision_client

    async def compress(self, history: List[Dict]) -> str:
        if not history:
            return ""

        summary_raw = json.dumps(history[:5]) + "..." + json.dumps(history[-3:])
        prompt = f"Summarize this execution history into a 1-sentence strategic lesson: {summary_raw}"

        summary = await self.vision._call_text(prompt, "Strategy Synthesizer")
        logger.info("History compressed into lesson (%d chars)", len(summary))
        return summary
