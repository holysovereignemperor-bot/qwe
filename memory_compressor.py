import json
from typing import List, Dict

class MemoryCompressor:
    """Summarizes long histories into high-level 'Cognitive Snapshots'."""
    def __init__(self, vision_client):
        self.vision = vision_client

    async def compress(self, history: List[Dict]) -> str:
        """Condenses raw action/result history into a single strategy lesson."""
        if not history: return ""

        # Heuristic: Take the first and last few actions
        summary_raw = json.dumps(history[:5]) + "..." + json.dumps(history[-3:])
        prompt = f"Summarize this execution history into a 1-sentence strategic lesson: {summary_raw}"

        # Using _call_vision with empty image for text summary
        summary = await self.vision._call_vision(prompt, None, "Strategy Synthesizer")
        return summary
