import os
import base64
import json
import logging
from typing import Optional
from llm_provider import LLMRouter

logger = logging.getLogger(__name__)


class VisionClient:
    """Vision-Language client that routes through LLMRouter for offline/online resilience."""

    def __init__(self, llm_router: LLMRouter = None, model: str = "gpt-4o-mini"):
        self.llm = llm_router or LLMRouter()
        self.model = model

    @property
    def total_cost(self) -> float:
        return self.llm.total_cost

    @total_cost.setter
    def total_cost(self, value: float):
        self.llm.total_cost = value

    async def _call_vision(self, prompt: str, img_bytes: Optional[bytes], sys_prompt: str = None) -> str:
        messages = []
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})

        if img_bytes:
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            messages.append({"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "low"}},
            ]})
            return await self.llm.chat(messages, model=self.model, max_tokens=500, need_vision=True)
        else:
            messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
            return await self.llm.chat(messages, model=self.model, max_tokens=500, need_vision=False)

    async def _call_text(self, prompt: str, sys_prompt: str = None, max_tokens: int = 500) -> str:
        messages = []
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
        return await self.llm.chat(messages, model=self.model, max_tokens=max_tokens, need_vision=False)

    async def get_plan(self, goal, screenshot, ui_tree_summary, context=""):
        p = f"Goal: {goal}\nContext: {context}\nTree: {ui_tree_summary}\nGenerate JSON steps."
        res = await self._call_vision(p, screenshot, "Architect")
        try:
            if "```json" in res:
                json_str = res.split("```json")[1].split("```")[0].strip()
            else:
                json_str = res.strip()
            plan = json.loads(json_str)
            logger.info("Plan parsed: %d steps", len(plan) if isinstance(plan, list) else 1)
            return plan
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning("Plan parsing failed: %s", e)
            return [{"action": "error", "description": res}]

    async def get_action(self, step, screenshot, ui_tree_summary):
        p = f"""
Step: {json.dumps(step)}
Tree Summary: {ui_tree_summary}

Instructions:
1. Prefer using the 'Visual Marks' IDs (0, 1, 2...) for coordinates.
2. If ID is missing, identify the element by its 'Semantic Anchor' (e.g., 'blue button', 'search field').
Return JSON with 'skill', 'params' (x, y relative to 1024 width), and 'reasoning'.
"""
        res = await self._call_vision(p, screenshot, "Executor")
        try:
            if "```json" in res:
                json_str = res.split("```json")[1].split("```")[0].strip()
            else:
                json_str = res.strip()
            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning("Action parsing failed: %s", e)
            return {"skill": "error", "error": res}

    async def verify_outcome(self, last_action, screenshot, ui_tree_summary):
        p = f"Action: {json.dumps(last_action)}\nTree: {ui_tree_summary}\nVerify success. Return JSON 'success', 'observation'."
        res = await self._call_vision(p, screenshot, "Auditor")
        try:
            if "```json" in res:
                json_str = res.split("```json")[1].split("```")[0].strip()
            else:
                json_str = res.strip()
            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning("Verification parsing failed: %s", e)
            return {"success": False, "observation": res}
