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
        self.architect = ArchitectAgent(vision); self.executor = ExecutorAgent(vision)
        self.auditor = AuditorAgent(vision); self.registry = registry
        self.memory = memory; self.knowledge = knowledge
        self.status_callback = None; self.reporter = ReportGenerator()
        self.voice = VoiceOS(); self.MAX_STEPS = 50; self.MAX_COST = 5.0 # Increased for Swarm
        self.history_dir = "logs/history"
        if not os.path.exists(self.history_dir): os.makedirs(self.history_dir)

    async def run_sub_task(self, sub_goal, parent_blackboard):
        """Swarm Delegation: Runs a parallel specialized sub-agent."""
        sub_bb = Blackboard(sub_goal)
        # Inherit context but separate state
        await self.run(sub_bb, parent_blackboard.get_context_summary())
        return sub_bb.to_dict()

    async def run(self, blackboard: Blackboard, project_context: str = ""):
        blackboard.gui_callback = self.status_callback
        try:
            self.voice.speak(f"Swarm initiated for {blackboard.goal}")
            while blackboard.is_running and blackboard.current_step_index < self.MAX_STEPS:
                while blackboard.is_paused: await asyncio.sleep(0.5)
                gc.collect()
                blackboard.total_cost = self.architect.vision.total_cost
                if blackboard.total_cost > self.MAX_COST: break

                blackboard.last_screenshot, marks = get_marked_screenshot()
                blackboard.last_ui_tree = get_ui_tree()
                meta = get_window_metadata()

                # 1. Plan
                if not blackboard.plan:
                    if self.status_callback: self.status_callback("agent_active", "PM")
                    await self.architect.plan(blackboard, self.memory, self.knowledge, project_context)

                # 2. Swarm check: Did the Architect delegate?
                current_step = blackboard.plan[blackboard.current_step_index] if blackboard.plan else {}
                if current_step.get("action") == "delegate":
                    if self.status_callback: self.status_callback("log", f"Delegating sub-task: {current_step.get('description')}")
                    result = await self.run_sub_task(current_step.get("target_goal"), blackboard)
                    blackboard.add_chat("swarm", f"Sub-task completed: {result.get('status')}")
                    blackboard.current_step_index += 1
                    continue

                # 3. Execute
                if self.status_callback: self.status_callback("agent_active", "Executor")
                action = await self.executor.act(blackboard)

                if action.get("skill") == "ask_user":
                    blackboard.is_paused = True
                    if self.status_callback: self.status_callback("clarification_required", action.get("params", {}).get("question"))
                    continue

                skill = self.registry.get(action.get('skill'))
                if skill:
                    if self.status_callback and action.get('skill') == "click":
                         self.status_callback("visual_feedback", action.get('params', {}))
                    res = await skill.execute(action.get('params', {}))
                else: res = {"status": "error", "error": "Skill missing"}

                # 4. Verify
                if self.status_callback: self.status_callback("agent_active", "Auditor")
                blackboard.last_screenshot, _ = get_marked_screenshot()
                blackboard.last_ui_tree = get_ui_tree()
                verification = await self.auditor.verify(action, blackboard)
                blackboard.add_history(action, verification)

                if verification.get("success"):
                    blackboard.current_step_index += 1
                else:
                    correction = await self.auditor.generate_correction_plan(verification, blackboard)
                    blackboard.plan = []

                if blackboard.current_step_index >= len(blackboard.plan) and len(blackboard.plan) > 0:
                    blackboard.status = "Completed"
                    break
                await asyncio.sleep(0.5)

        except Exception as e: blackboard.error = str(e)
        finally:
            blackboard.is_running = False; blackboard.status = "Finished"
            self.reporter.generate_report(blackboard)
