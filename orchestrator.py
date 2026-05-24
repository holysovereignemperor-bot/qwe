import asyncio
import gc
import json
import os
from agents import ArchitectAgent, ExecutorAgent, AuditorAgent
from blackboard import Blackboard
from memory_vault import MemoryVault
from mac_utils import capture_screen, get_ui_tree, get_window_metadata
from vision_client import VisionClient
from skills import SkillRegistry
from report_generator import ReportGenerator

class Orchestrator:
    def __init__(self, vision: VisionClient, registry: SkillRegistry, memory: MemoryVault):
        self.architect = ArchitectAgent(vision)
        self.executor = ExecutorAgent(vision)
        self.auditor = AuditorAgent(vision)
        self.registry = registry
        self.memory = memory
        self.status_callback = None
        self.reporter = ReportGenerator()

        self.MAX_STEPS = 50
        self.MAX_COST = 2.0

    async def run(self, blackboard: Blackboard, project_context: str = ""):
        try:
            while blackboard.is_running and blackboard.current_step_index < self.MAX_STEPS:
                gc.collect()

                if blackboard.total_cost > self.MAX_COST:
                    blackboard.error = "Circuit breaker: Cost limit exceeded"
                    break

                # 1. Perceive
                blackboard.last_screenshot = capture_screen()
                blackboard.last_ui_tree = get_ui_tree()
                meta = get_window_metadata()
                full_context = f"{project_context}\nWindow Metadata: {json.dumps(meta)}"

                # 2. Plan
                if not blackboard.plan:
                    await self.architect.plan(blackboard, self.memory, full_context)
                    if self.status_callback:
                        self.status_callback("log", f"Architect generated plan: {len(blackboard.plan)} steps")
                    if not blackboard.plan:
                        blackboard.error = "Planning failed"
                        break

                # 3. Execute
                action = await self.executor.act(blackboard)
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
                    if skill:
                        result = await skill.execute(repair_action.get('params', {}))

                # 4. Verify
                blackboard.last_screenshot = capture_screen()
                blackboard.last_ui_tree = get_ui_tree()

                verification = await self.auditor.verify(action, blackboard)
                blackboard.add_history(action, verification)

                if verification.get("success"):
                    blackboard.current_step_index += 1
                else:
                    self.auditor.reflect_on_outcome(verification)
                    if self.status_callback:
                        self.status_callback("log", f"Verification failed: {verification.get('reflection')}")

                if blackboard.current_step_index >= len(blackboard.plan):
                    blackboard.status = "Completed"
                    self.memory.save_experience(blackboard.goal, blackboard.plan, True)
                    break

                blackboard.total_cost = self.architect.vision.total_cost
                await asyncio.sleep(0.5)

        except Exception as e:
            blackboard.error = f"Orchestration crash: {str(e)}"
            if self.status_callback:
                self.status_callback("log", f"CRASH: {str(e)}")
            blackboard.is_running = False
        finally:
            blackboard.is_running = False
            blackboard.status = "Finished"
            # Generate final report
            report_path = self.reporter.generate_report(blackboard)
            if self.status_callback:
                self.status_callback("log", f"Final report generated at: {report_path}")
