import time
from typing import List, Dict, Any, Optional

class Blackboard:
    """State for agents with recursive verification support."""
    def __init__(self, goal: str):
        self.goal = goal
        self.plan: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []
        self.chat_history: List[Dict[str, str]] = []
        self.current_step_index: int = 0
        self.total_cost: float = 0.0
        self.start_time: float = time.time()
        self.status: str = "Planning"
        self.is_running: bool = True
        self.is_paused: bool = False
        self.user_response: Optional[str] = None
        self.correction_plan: Optional[str] = None # For Recursive Reasoning
        self.error: Optional[str] = None
        self.last_screenshot: Optional[bytes] = None
        self.last_ui_tree: Optional[Dict[str, Any]] = None

    def add_history(self, action: Dict[str, Any], result: Dict[str, Any]):
        self.history.append({"timestamp": time.time(), "step_index": self.current_step_index, "action": action, "result": result})

    def add_chat(self, role: str, content: str):
        self.chat_history.append({"role": role, "content": content})

    def get_context_summary(self) -> str:
        summary = f"Goal: {self.goal}\n"
        if self.plan: summary += f"Step: {self.current_step_index + 1}/{len(self.plan)}\n"
        return summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "status": self.status,
            "total_cost": self.total_cost,
            "runtime": time.time() - self.start_time,
            "is_paused": self.is_paused
        }
