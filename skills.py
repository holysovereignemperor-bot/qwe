import os
import subprocess
import shlex
import io
import contextlib
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class Skill(ABC):
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pass

class ClickSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from mac_utils import simulate_click, scale_coordinate, get_screen_dimensions
        x = params.get('x')
        y = params.get('y')
        if x is None or y is None:
            return {"status": "error", "error": "Missing x or y coordinates"}

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
        return {"status": "success", "action": "Typed text"}

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
        if not path:
             return {"status": "error", "error": "No path provided"}
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

class ExecuteCodeSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        code = params.get('code', '')
        if not code:
            return {"status": "error", "error": "No code provided"}
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(code, {"__builtins__": __builtins__})
            return {"status": "success", "stdout": stdout.getvalue(), "stderr": stderr.getvalue()}
        except Exception as e:
            return {"status": "error", "error": str(e), "stdout": stdout.getvalue(), "stderr": stderr.getvalue()}

class GithubSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from github_manager import GithubManager
        gh = GithubManager()
        action, args, cwd = params.get("action"), params.get("args", []), params.get("cwd", ".")
        if action == "git":
            return gh.run_git(args, cwd)
        elif action == "pr":
            return gh.create_pull_request(repo=params.get("repo"), title=params.get("title"), head=params.get("head"), body=params.get("body", ""))
        return {"status": "error", "error": f"Unknown github action: {action}"}

class PluginGeneratorSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name, code = params.get("name"), params.get("code")
        if not name or not code:
            return {"status": "error", "error": "Missing name or code"}
        path = os.path.join("plugins", f"{name}.py")
        try:
            with open(path, "w") as f:
                f.write(code)
            return {"status": "success", "message": f"Skill plugin '{name}' generated."}
        except Exception as e:
            return {"status": "error", "error": str(e)}

class AppleScriptSkill(Skill):
    """Allows the agent to control macOS apps via AppleScript."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from applescript_utils import AppleScriptUtils
        script = params.get("script")
        if not script:
            # Check for high-level templates
            action = params.get("action")
            if action == "safari_open":
                script = AppleScriptUtils.safari_open_url(params.get("url"))
            elif action == "mail_draft":
                script = AppleScriptUtils.mail_send_email(params.get("to"), params.get("subject"), params.get("body"))
            elif action == "notes_create":
                script = AppleScriptUtils.notes_create_note(params.get("title"), params.get("body"))

        if not script:
            return {"status": "error", "error": "No script or action provided"}

        return AppleScriptUtils.run_script(script)

class WebSearchSkill(Skill):
    """Allows the agent to search and scrape the web for live information."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query")
        if not query: return {"status": "error", "error": "No query"}

        # Strategy: Use Safari via AppleScript to search, then extract text
        # This keeps RAM low by not running a headless browser locally.
        from applescript_utils import AppleScriptUtils
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        AppleScriptUtils.run_script(AppleScriptUtils.safari_open_url(search_url))

        return {"status": "success", "message": f"Opened search for: {query}. Agent should now perceive Safari."}

class SkillRegistry:
    def __init__(self):
        self._skills: Dict[str, Skill] = {
            "click": ClickSkill(),
            "type": TypeSkill(),
            "command": TerminalSkill(),
            "file": FileSystemSkill(),
            "execute_code": ExecuteCodeSkill(),
            "github": GithubSkill(),
            "generate_skill": PluginGeneratorSkill(),
            "applescript": AppleScriptSkill(),
            "web_search": WebSearchSkill()
        }
    def register(self, name: str, skill: Skill):
        self._skills[name] = skill
    def get(self, name: str) -> Skill:
        return self._skills.get(name)
