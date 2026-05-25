import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DECOMPOSITION_PROMPT = """You are a task decomposition expert. Break down this complex goal into independent sub-goals.

Goal: {goal}
Context: {context}

Rules:
1. Each sub-goal must be self-contained and achievable independently.
2. Order sub-goals by dependency (independent ones first).
3. Mark sub-goals that can run in parallel with "parallel": true.
4. If the goal is simple (1-3 steps), return it as a single sub-goal.

Return JSON array:
[
  {{"id": 1, "sub_goal": "...", "parallel": false, "depends_on": [], "complexity": "low|medium|high"}},
  ...
]"""


class TaskDecomposer:
    """Breaks complex goals into manageable sub-goals with dependency tracking."""

    def __init__(self, llm_router):
        self.llm = llm_router

    async def decompose(self, goal: str, context: str = "") -> List[Dict[str, Any]]:
        prompt = DECOMPOSITION_PROMPT.format(goal=goal, context=context)
        messages = [
            {"role": "system", "content": "Task Decomposer"},
            {"role": "user", "content": [{"type": "text", "text": prompt}]},
        ]

        try:
            response = await self.llm.chat(messages, max_tokens=1000, use_cache=True, need_vision=False)
            sub_goals = self._parse_response(response)
            if sub_goals:
                logger.info("Decomposed '%s' into %d sub-goals", goal[:50], len(sub_goals))
                return sub_goals
        except Exception as e:
            logger.warning("Decomposition failed, treating as single goal: %s", e)

        return [{"id": 1, "sub_goal": goal, "parallel": False, "depends_on": [], "complexity": "medium"}]

    def _parse_response(self, response: str) -> List[Dict[str, Any]]:
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            data = json.loads(json_str)
            if isinstance(data, list) and len(data) > 0:
                return data
        except (json.JSONDecodeError, IndexError):
            pass
        return []

    def get_parallel_groups(self, sub_goals: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        groups: List[List[Dict[str, Any]]] = []
        current_group: List[Dict[str, Any]] = []
        completed_ids: set = set()

        for sg in sub_goals:
            deps = set(sg.get("depends_on", []))
            can_parallel = sg.get("parallel", False)

            if deps and not deps.issubset(completed_ids):
                if current_group:
                    groups.append(current_group)
                    completed_ids.update(g["id"] for g in current_group)
                    current_group = []
                current_group.append(sg)
            elif can_parallel:
                current_group.append(sg)
            else:
                if current_group:
                    groups.append(current_group)
                    completed_ids.update(g["id"] for g in current_group)
                    current_group = []
                current_group.append(sg)

        if current_group:
            groups.append(current_group)

        return groups
