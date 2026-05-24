import json
from vision_client import VisionClient
from blackboard import Blackboard
from memory_vault import MemoryVault
from knowledge_manager import KnowledgeManager
from lesson_vault import LessonVault

class Agent:
    def __init__(self, vision: VisionClient):
        self.vision = vision

class ArchitectAgent(Agent):
    async def plan(self, blackboard: Blackboard, memory: MemoryVault, knowledge: KnowledgeManager, project_context: str = ""):
        # Transcendence: Use Lessons + Memory + Docs
        lessons = LessonVault().get_lessons(blackboard.goal)
        doc_context = knowledge.search_docs(blackboard.goal)
        similar = memory.retrieve_similar(blackboard.goal)

        full_context = f"{project_context}\nNeural Lessons: {json.dumps(lessons)}\nDocs: {json.dumps(doc_context)}\nMemory: {json.dumps(similar)}"

        if hasattr(blackboard, "correction_plan") and blackboard.correction_plan:
            full_context += f"\nCORRECTION: {blackboard.correction_plan}"

        candidates = []
        for i in range(2):
            p = await self.vision.get_plan(goal=blackboard.goal, screenshot=blackboard.last_screenshot, ui_tree_summary=json.dumps(blackboard.last_ui_tree), context=full_context)
            candidates.append(p)

        best_plan = min(candidates, key=len)
        blackboard.plan = best_plan
        blackboard.status = "Executing"

class ExecutorAgent(Agent):
    async def act(self, blackboard: Blackboard):
        if not blackboard.plan or blackboard.current_step_index >= len(blackboard.plan):
            return {"skill": "error", "error": "End of plan"}
        step = blackboard.plan[blackboard.current_step_index]
        return await self.vision.get_action(step=step, screenshot=blackboard.last_screenshot, ui_tree_summary=json.dumps(blackboard.last_ui_tree))

    async def self_repair(self, error: str, blackboard: Blackboard):
        if "ModuleNotFoundError" in error:
            pkg = error.split("'")[-2] if "'" in error else "package"
            return {"skill": "command", "params": {"cmd": f"pip install {pkg}"}}
        return {"skill": "command", "params": {"cmd": "echo 'Repairing...'"}}

class AuditorAgent(Agent):
    async def verify(self, last_action, blackboard: Blackboard):
        return await self.vision.verify_outcome(last_action=last_action, screenshot=blackboard.last_screenshot, ui_tree_summary=json.dumps(blackboard.last_ui_tree))

    async def generate_correction_plan(self, failed_result: dict, blackboard: Blackboard):
        prompt = f"Fail: {failed_result.get('observation')}. Suggest 1 fix."
        correction = await self.vision._call_vision(prompt, blackboard.last_screenshot, "Senior Debugger")
        blackboard.correction_plan = correction
        return correction

    def reflect_on_outcome(self, result: dict):
        return result.get('reflection')
