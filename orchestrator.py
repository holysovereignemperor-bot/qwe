import asyncio
import gc
import json
import os
from agents import ArchitectAgent, ExecutorAgent, AuditorAgent
from blackboard import Blackboard
from memory_vault import MemoryVault
from mac_utils import get_marked_screenshot, get_ui_tree, get_window_metadata
from vision_client import VisionClient
from skills import SkillRegistry
from report_generator import ReportGenerator
from voice_os import VoiceOS
from knowledge_manager import KnowledgeManager

class Orchestrator:
    def __init__(self, vision: VisionClient, registry: SkillRegistry, memory: MemoryVault, knowledge: KnowledgeManager):
        self.architect = ArchitectAgent(vision)
        self.executor = ExecutorAgent(vision)
        self.auditor = AuditorAgent(vision)
        self.registry = registry
        self.memory = memory
        self.knowledge = knowledge
        self.status_callback = None
        self.reporter = ReportGenerator()
        self.voice = VoiceOS()

        self.MAX_STEPS = 50
        self.MAX_COST = 2.0
        self.history_dir = "logs/history"
        if not os.path.exists(self.history_dir): os.makedirs(self.history_dir)

    async def run(self, blackboard: Blackboard, project_context: str = ""):
        # Link callback for Agent-to-GUI direct signaling
        blackboard.gui_callback = self.status_callback

        try:
            self.voice.speak(f"Transcending task: {blackboard.goal}")
            while blackboard.is_running and blackboard.current_step_index < self.MAX_STEPS:
                while blackboard.is_paused:
                    await asyncio.sleep(0.5);
                    if not blackboard.is_running: return

                gc.collect()
                blackboard.total_cost = self.architect.vision.total_cost
                if blackboard.total_cost > self.MAX_COST:
                    blackboard.error = "Circuit breaker: Cost limit exceeded"; break

                # 1. Perceive
                blackboard.last_screenshot, marks = get_marked_screenshot()
                blackboard.last_ui_tree = get_ui_tree()
                meta = get_window_metadata()

                path = os.path.join(self.history_dir, f"step_{blackboard.current_step_index}.jpg")
                with open(path, "wb") as f: f.write(blackboard.last_screenshot)
                if self.status_callback: self.status_callback("visual_history", path)

                full_context = f"{project_context}\nVisual Marks: {json.dumps(marks[:10])}\n{blackboard.get_context_summary()}\nMetadata: {json.dumps(meta)}"

                # 2. Plan
                if not blackboard.plan:
                    if self.status_callback: self.status_callback("agent_active", "PM")
                    await self.architect.plan(blackboard, self.memory, self.knowledge, full_context)
                    if self.status_callback: self.status_callback("log", "Omega Architect plan ready.")
                    if not blackboard.plan: blackboard.error = "Planning failed"; break

                # 3. Execute
                if self.status_callback: self.status_callback("agent_active", "Executor")
                action = await self.executor.act(blackboard)

                if action.get("skill") == "ask_user":
                    blackboard.is_paused = True
                    message = action.get("params", {}).get("question", "Input required.")
                    blackboard.add_chat("agent", message)
                    if self.status_callback: self.status_callback("clarification_required", message)
                    continue

                skill_name = action.get('skill')
                skill = self.registry.get(skill_name)
                if skill:
                    if self.status_callback and skill_name == "click" and "params" in action:
                        self.status_callback("visual_feedback", action['params'])
                    result = await skill.execute(action.get('params', {}))
                else:
                    result = {"status": "error", "error": f"Unknown skill: {skill_name}"}

                if result.get("status") == "error":
                    repair_action = await self.executor.self_repair(result['error'], blackboard)
                    skill = self.registry.get(repair_action.get('skill'))
                    if skill: result = await skill.execute(repair_action.get('params', {}))

                # 4. Verify
                if self.status_callback: self.status_callback("agent_active", "Auditor")
                blackboard.last_screenshot, _ = get_marked_screenshot()
                blackboard.last_ui_tree = get_ui_tree()
                verification = await self.auditor.verify(action, blackboard)
                blackboard.add_history(action, verification)

                if verification.get("success"): blackboard.current_step_index += 1
                else: self.auditor.reflect_on_outcome(verification)

                if blackboard.current_step_index >= len(blackboard.plan):
                    blackboard.status = "Completed"
                    self.memory.save_experience(blackboard.goal, blackboard.plan, True)
                    self.voice.speak("Omega task finalized."); break

                await asyncio.sleep(0.5)

        except Exception as e:
            blackboard.error = f"Omega crash: {str(e)}"; blackboard.is_running = False
        finally:
            blackboard.is_running = False; blackboard.status = "Finished"
            blackboard.total_cost = self.architect.vision.total_cost
            self.reporter.generate_report(blackboard)
            if self.status_callback: self.status_callback("agent_active", "None")
