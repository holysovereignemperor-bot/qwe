import os
import base64
import json
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class VisionClient:
    def __init__(self, api_key=None, model="gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = model
        self.total_cost = 0.0

    def _track_usage(self, r):
        cost = (r.usage.prompt_tokens * 0.00000015) + (r.usage.completion_tokens * 0.00000060)
        self.total_cost += cost
        logger.debug("API call cost: $%.6f (total: $%.4f)", cost, self.total_cost)

    async def _call_vision(self, prompt, img_bytes, sys_prompt=None):
        if not img_bytes:
            return "{}"
        m = [{"role": "system", "content": sys_prompt}] if sys_prompt else []
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        m.append({"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "low"}},
        ]})
        res = await self.client.chat.completions.create(model=self.model, messages=m, max_tokens=500)
        self._track_usage(res)
        return res.choices[0].message.content

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
