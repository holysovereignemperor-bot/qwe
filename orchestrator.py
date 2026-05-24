import asyncio
import gc
import json
import os
from agents import ArchitectAgent, ExecutorAgent, AuditorAgent
from blackboard import Blackboard
from memory_vault import MemoryVault
from mac_utils import get_marked_screenshot, get_ui_tree, get_window_metadata, compute_visual_diff
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
        self.voice = VoiceOS(); self.MAX_STEPS = 50; self.MAX_COST = 5.0
        self.history_dir = "logs/history"
        if not os.path.exists(self.history_dir): os.makedirs(self.history_dir)

    async def run(self, blackboard: Blackboard, project_context: str = ""):
        blackboard.gui_callback = self.status_callback
        try:
            while blackboard.is_running and blackboard.current_step_index < self.MAX_STEPS:
                while blackboard.is_paused: await asyncio.sleep(0.5)
                gc.collect()
                blackboard.total_cost = self.architect.vision.total_cost

                # 1. Perceive (Pre-action)
                pre_screenshot, marks = get_marked_screenshot()
                blackboard.last_screenshot = pre_screenshot
                blackboard.last_ui_tree = get_ui_tree(); meta = get_window_metadata()

                # 2. Plan
                if not blackboard.plan:
                    if self.status_callback: self.status_callback("agent_active", "PM")
                    await self.architect.plan(blackboard, self.memory, self.knowledge, project_context)

                # 3. Execute
                if self.status_callback: self.status_callback("agent_active", "Executor")
                action = await self.executor.act(blackboard)
                skill = self.registry.get(action.get('skill'))
                if skill:
                    if self.status_callback and action.get('skill') == "click":
                         self.status_callback("visual_feedback", action.get('params', {}))
                    await skill.execute(action.get('params', {}))

                # 4. Verify (Post-action with Visual Diff)
                if self.status_callback: self.status_callback("agent_active", "Auditor")
                post_screenshot, _ = get_marked_screenshot()

                diff_score = compute_visual_diff(pre_screenshot, post_screenshot)
                blackboard.last_screenshot = post_screenshot

                verification = await self.auditor.verify(action, blackboard)
                # Enhance verification with diff score
                verification["visual_change"] = diff_score > 0.1
                blackboard.add_history(action, verification)

                if verification.get("success"):
                    blackboard.current_step_index += 1
                else:
                    await self.auditor.generate_correction_plan(verification, blackboard)
                    blackboard.plan = []

                if blackboard.current_step_index >= len(blackboard.plan) and len(blackboard.plan) > 0:
                    blackboard.status = "Completed"; break
                await asyncio.sleep(0.5)

        except Exception as e: blackboard.error = str(e)
        finally:
            blackboard.is_running = False; blackboard.status = "Finished"
            self.reporter.generate_report(blackboard)
