import os
import subprocess
import shlex
from abc import ABC, abstractmethod
from typing import Dict, Any

class Skill(ABC):
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pass

class ClickSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from mac_utils import simulate_click, scale_coordinate
        x, y = params.get('x'), params.get('y')
        # vision_client uses 1024px width
        # We need the aspect ratio to determine the virtual height used by the LLM
        from mac_utils import get_screen_dimensions
        sw, sh = get_screen_dimensions()
        v_height = (1024 * sh) / sw

        sx, sy = scale_coordinate(x, y, 1024, v_height)
        simulate_click(sx, sy)
        return {"status": "success", "action": f"Clicked at {x}, {y}"}

class TypeSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from mac_utils import simulate_type
        text = params.get('text', '')
        simulate_type(text)
        return {"status": "success", "action": f"Typed text"}

class TerminalSkill(Skill):
    BLACKLIST = ["rm -rf /", "sudo", "mkfs", "dd"]

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cmd = params.get('cmd', '')
        if any(bad in cmd for bad in self.BLACKLIST):
            return {"status": "blocked", "reason": "Security guardrail: Unsafe command detected"}

        try:
            result = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=30)
            return {
                "status": "success",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

class FileSystemSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get('action')
        path = params.get('path')

        if ".." in path:
             return {"status": "blocked", "reason": "Security guardrail: Directory traversal detected"}

        try:
            if action == "read":
                with open(path, 'r') as f:
                    return {"status": "success", "content": f.read()}
            elif action == "write":
                content = params.get('content', '')
                with open(path, 'w') as f:
                    f.write(content)
                    return {"status": "success"}
            return {"status": "error", "error": f"Unknown action: {action}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

class SkillRegistry:
    def __init__(self):
        self._skills: Dict[str, Skill] = {
            "click": ClickSkill(),
            "type": TypeSkill(),
            "command": TerminalSkill(),
            "file": FileSystemSkill()
        }

    def register(self, name: str, skill: Skill):
        self._skills[name] = skill

    def get(self, name: str) -> Skill:
        return self._skills.get(name)
