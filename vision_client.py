import os
import base64
import json
import asyncio
from openai import AsyncOpenAI

class VisionClient:
    def __init__(self, api_key=None, model="gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = model; self.total_cost = 0.0

    def _track_usage(self, r):
        self.total_cost += (r.usage.prompt_tokens * 0.00000015) + (r.usage.completion_tokens * 0.00000060)

    async def _call_vision(self, prompt, img_bytes, sys_prompt=None, temp=0.0):
        if not img_bytes: return "{}"
        m = [{"role": "system", "content": sys_prompt}] if sys_prompt else []
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        m.append({"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "low"}}]})
        res = await self.client.chat.completions.create(model=self.model, messages=m, max_tokens=500, temperature=temp)
        self._track_usage(res)
        return res.choices[0].message.content

    async def get_plan(self, goal, screenshot, ui_tree_summary, context=""):
        p = f"Goal: {goal}\nContext: {context}\nTree: {ui_tree_summary}\nGenerate JSON steps."
        res = await self._call_vision(p, screenshot, "Architect")
        try:
            if "```json" in res: json_str = res.split("```json")[1].split("```")[0].strip()
            else: json_str = res.strip()
            return json.loads(json_str)
        except: return [{"action": "error", "description": res}]

    async def get_action(self, step, screenshot, ui_tree_summary):
        p = f"Step: {json.dumps(step)}\nTree: {ui_tree_summary}\nReturn JSON skill/params/reasoning."
        res = await self._call_vision(p, screenshot, "Executor")
        try:
            if "```json" in res: json_str = res.split("```json")[1].split("```")[0].strip()
            else: json_str = res.strip()
            return json.loads(json_str)
        except: return {"skill": "error", "error": res}

    async def verify_outcome(self, last_action, screenshot, ui_tree_summary, high_stakes=False):
        """Consensus Verification: High-stakes actions trigger dual verification paths."""
        async def _single_verify(t):
             res = await self._call_vision(f"Verify: {json.dumps(last_action)}", screenshot, "Auditor", temp=t)
             try:
                 if "```json" in res: return json.loads(res.split("```json")[1].split("```")[0].strip())
                 return json.loads(res)
             except: return {"success": False}

        v1 = await _single_verify(0.0)
        if not high_stakes: return v1

        # Dual Path Consensus
        v2 = await _single_verify(0.7)
        return v1 if v1.get("success") == v2.get("success") else {"success": False, "observation": "Consensus failed."}
