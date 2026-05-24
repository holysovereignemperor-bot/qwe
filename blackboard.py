import time
from typing import List, Dict, Any, Optional

class Blackboard:
    """Shared state container for agents (Blackboard Pattern)."""
    def __init__(self, goal: str):
        self.goal = goal
        self.plan: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []
        self.current_step_index: int = 0
        self.total_cost: float = 0.0
        self.start_time: float = time.time()
        self.status: str = "Planning"
        self.is_running: bool = True
        self.error: Optional[str] = None
        self.last_screenshot: Optional[bytes] = None
        self.last_ui_tree: Optional[Dict[str, Any]] = None

    def add_history(self, action: Dict[str, Any], result: Dict[str, Any]):
        self.history.append({
            "timestamp": time.time(),
            "step_index": self.current_step_index,
            "action": action,
            "result": result
        })

    def get_context_summary(self) -> str:
        summary = f"Goal: {self.goal}\n"
        if self.plan:
            summary += f"Current Step: {self.current_step_index + 1}/{len(self.plan)}\n"
        if self.history:
            last_3 = self.history[-3:]
            summary += "Recent Actions:\n"
            for h in last_3:
                summary += f"- {h['action'].get('skill', 'unknown')}: {h['result'].get('observation', 'no observation')}\n"
        return summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "plan_length": len(self.plan),
            "current_step": self.current_step_index,
            "history_length": len(self.history),
            "total_cost": self.total_cost,
            "runtime": time.time() - self.start_time,
            "status": self.status,
            "error": self.error
        }
