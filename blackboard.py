import time
import json
import os
from typing import List, Dict, Any, Optional

class Blackboard:
    """State for agents with Workspace Persistence."""
    def __init__(self, goal: str):
        self.goal = goal
        self.plan: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []
        self.chat_history: List[Dict[str, str]] = []
        self.data_bus: Dict[str, Any] = {}
        self.current_step_index: int = 0
        self.total_cost: float = 0.0
        self.start_time: float = time.time()
        self.status: str = "Planning"
        self.is_running: bool = True
        self.is_paused: bool = False
        self.user_response: Optional[str] = None
        self.correction_plan: Optional[str] = None
        self.error: Optional[str] = None
        self.last_screenshot: Optional[bytes] = None
        self.last_ui_tree: Optional[Dict[str, Any]] = None

    def add_history(self, action: Dict[str, Any], result: Dict[str, Any]):
        self.history.append({"timestamp": time.time(), "step_index": self.current_step_index, "action": action, "result": result})

    def add_chat(self, role: str, content: str):
        self.chat_history.append({"role": role, "content": content})

    def save_state(self, path="logs/session_resume.json"):
        """Persistence: Serializes current state for restoration."""
        state = {
            "goal": self.goal, "plan": self.plan, "history": self.history,
            "step": self.current_step_index, "bus": self.data_bus, "cost": self.total_cost
        }
        with open(path, 'w') as f: json.dump(state, f, indent=2)

    @classmethod
    def load_state(cls, path="logs/session_resume.json"):
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                obj = cls(data["goal"])
                obj.plan = data["plan"]; obj.history = data["history"]
                obj.current_step_index = data["step"]; obj.data_bus = data["bus"]
                obj.total_cost = data["cost"]; return obj
        return None

    def get_context_summary(self) -> str:
        summary = f"Goal: {self.goal}\n"
        if self.plan: summary += f"Step: {self.current_step_index + 1}/{len(self.plan)}\n"
        return summary

    def to_dict(self) -> Dict[str, Any]:
        return {"goal": self.goal, "status": self.status, "total_cost": self.total_cost, "is_paused": self.is_paused}
