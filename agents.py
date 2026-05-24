import json
from vision_client import VisionClient
from blackboard import Blackboard
from memory_vault import MemoryVault

class Agent:
    def __init__(self, vision: VisionClient):
        self.vision = vision

class ArchitectAgent(Agent):
    async def plan(self, blackboard: Blackboard, memory: MemoryVault, project_context: str = ""):
        similar = memory.retrieve_similar(blackboard.goal)
        context = project_context
        if similar:
            context += "\nSimilar successful plans from memory:\n" + json.dumps(similar)

        plan = await self.vision.get_plan(
            goal=blackboard.goal,
            screenshot=blackboard.last_screenshot,
            ui_tree_summary=json.dumps(blackboard.last_ui_tree),
            context=context
        )
        blackboard.plan = plan
        blackboard.status = "Executing"

class ExecutorAgent(Agent):
    async def act(self, blackboard: Blackboard):
        step = blackboard.plan[blackboard.current_step_index]
        action = await self.vision.get_action(
            step=step,
            screenshot=blackboard.last_screenshot,
            ui_tree_summary=json.dumps(blackboard.last_ui_tree)
        )
        return action

    async def self_repair(self, error: str, blackboard: Blackboard):
        # Improved self-repair could ask the LLM for a workaround
        print(f"Self-repairing error: {error}")
        return {"skill": "command", "params": {"cmd": f"echo 'Detected error: {error}. Attempting workaround...'"}}

class AuditorAgent(Agent):
    async def verify(self, last_action, blackboard: Blackboard):
        verification = await self.vision.verify_outcome(
            last_action=last_action,
            screenshot=blackboard.last_screenshot,
            ui_tree_summary=json.dumps(blackboard.last_ui_tree)
        )
        return verification

    def reflect_on_outcome(self, result: dict):
        """Causal analysis of the outcome with specific fix suggestions."""
        if not result.get("success"):
             observation = result.get('observation', 'None')
             reflection = result.get('reflection', 'Unknown cause')
             print(f"--- Auditor Reflection ---")
             print(f"Observation: {observation}")
             print(f"Causal Analysis: {reflection}")
             # We could return a structured repair hint to the Orchestrator
             return {"repair_hint": reflection, "retry_allowed": True}
        return None
