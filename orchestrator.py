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
from behavior_manager import BehaviorManager
from system_watchdog import SystemWatchdog
from system_doctor import SystemDoctor
from lesson_vault import LessonVault

class Orchestrator:
    def __init__(self, vision: VisionClient, registry: SkillRegistry, memory: MemoryVault, knowledge: KnowledgeManager):
        self.architect = ArchitectAgent(vision); self.executor = ExecutorAgent(vision)
        self.auditor = AuditorAgent(vision); self.registry = registry
        self.memory = memory; self.knowledge = knowledge
        self.status_callback = None; self.reporter = ReportGenerator()
        self.voice = VoiceOS(); self.behavior = BehaviorManager()
        self.watchdog = SystemWatchdog(); self.doctor = SystemDoctor()
        self.MAX_STEPS = 50; self.MAX_COST = 5.0
        self.history_dir = "logs/history"
        if not os.path.exists(self.history_dir): os.makedirs(self.history_dir)
        self.vision_quality = 50; self.vision_width = 1024

    async def run(self, blackboard: Blackboard, project_context: str = ""):
        blackboard.gui_callback = self.status_callback
        try:
            self.doctor.optimize_performance()
            # Initial Macro check
            macro = self.behavior.get_macro(blackboard.goal)
            if macro:
                for step in macro:
                    skill = self.registry.get(step.get('skill'))
                    if skill: await skill.execute(step.get('params', {}))
                blackboard.status = "Completed"; return

            while blackboard.is_running and blackboard.current_step_index < self.MAX_STEPS:
                while blackboard.is_paused: await asyncio.sleep(0.5)

                # Health Check
                health = self.watchdog.check_health()
                if health["critical"]: blackboard.is_paused = True

                blackboard.total_cost = self.architect.vision.total_cost
                pre_screenshot, marks = get_marked_screenshot(quality=self.vision_quality, max_width=self.vision_width)
                blackboard.last_screenshot = pre_screenshot
                blackboard.last_ui_tree = get_ui_tree()

                if not blackboard.plan:
                    full_context = f"{project_context}\n{self.behavior.get_behavior_context()}"
                    await self.architect.plan(blackboard, self.memory, self.knowledge, full_context)

                # Execute
                action = await self.executor.act(blackboard)
                skill = self.registry.get(action.get('skill'))
                if skill: await skill.execute(action.get('params', {}))

                # Verify
                post_screenshot, _ = get_marked_screenshot(quality=self.vision_quality, max_width=self.vision_width)
                diff_score = compute_visual_diff(pre_screenshot, post_screenshot)
                blackboard.last_screenshot = post_screenshot
                verification = await self.auditor.verify(action, blackboard)

                if verification.get("success"):
                    blackboard.add_history(action, verification)
                    blackboard.current_step_index += 1
                else:
                    await self.auditor.generate_correction_plan(verification, blackboard)
                    blackboard.plan = []

                if blackboard.current_step_index >= len(blackboard.plan) and len(blackboard.plan) > 0:
                    blackboard.status = "Completed"
                    LessonVault().add_lesson(blackboard.goal, "Transcendence path")
                    seq = [h['action'] for h in blackboard.history if h['result'].get('success')]
                    self.behavior.add_macro(blackboard.goal, seq)
                    break
                await asyncio.sleep(0.1) # Fast loop for tests

        except Exception as e: blackboard.error = str(e)
        finally:
            blackboard.is_running = False; blackboard.status = "Finished"
            self.reporter.generate_report(blackboard)
