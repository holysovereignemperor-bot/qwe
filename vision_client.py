import os
import base64
import json
import asyncio
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import List, Optional

class VisionClient:
    def __init__(self, api_key=None, model="gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = model
        self.total_cost = 0.0

    def _track_usage(self, response):
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        cost = (prompt_tokens * 0.00000015) + (completion_tokens * 0.00000060)
        self.total_cost += cost

    async def _call_vision(self, prompt, image_bytes, system_prompt=None):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "low"
                    }
                }
            ]
        })

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=500
        )

        self._track_usage(response)
        return response.choices[0].message.content

    async def get_plan(self, goal, screenshot, ui_tree_summary, context=""):
        system_prompt = "You are the Architect Agent. Your job is to break down a high-level goal into a sequential plan of actions."
        prompt = f"""
Goal: {goal}
Current Context: {context}
UI Tree Summary: {ui_tree_summary}

Based on the screenshot and the UI tree, generate a JSON list of steps.
Each step should have 'action', 'description', and 'target_element' (if applicable).
Return ONLY the JSON.
"""
        response_text = await self._call_vision(prompt, screenshot, system_prompt)
        try:
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            return json.loads(json_str)
        except:
            return [{"action": "error", "description": f"Failed to parse plan: {response_text}"}]

    async def get_action(self, step, screenshot, ui_tree_summary):
        system_prompt = "You are the Executor Agent. You translate steps into precise VLA actions."
        prompt = f"""
Current Step: {json.dumps(step)}
UI Tree Summary: {ui_tree_summary}

Look at the screenshot. Note that the screenshot has a width of 1024px.
All coordinates (x, y) you return must be relative to this 1024px width.
Identify the precise coordinates (x, y) for the target element if required.
Return a JSON object with:
- 'skill': the skill to use (e.g., 'click', 'type', 'command')
- 'params': parameters for the skill (e.g., 'x', 'y', 'text', 'cmd')
- 'reasoning': brief explanation of why this action is chosen.
Return ONLY the JSON.
"""
        response_text = await self._call_vision(prompt, screenshot, system_prompt)
        try:
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            return json.loads(json_str)
        except:
            return {"skill": "error", "error": f"Failed to parse action: {response_text}"}

    async def verify_outcome(self, last_action, screenshot, ui_tree_summary):
        system_prompt = "You are the Auditor Agent. You verify if the last action successfully changed the UI state."
        prompt = f"""
Last Action: {json.dumps(last_action)}
UI Tree Summary: {ui_tree_summary}

Does the current UI state indicate success?
Return a JSON object with:
- 'success': boolean
- 'observation': what you see
- 'reflection': if failed, why do you think it happened?
Return ONLY the JSON.
"""
        response_text = await self._call_vision(prompt, screenshot, system_prompt)
        try:
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            return json.loads(json_str)
        except:
            return {"success": False, "observation": "Failed to parse verification."}
