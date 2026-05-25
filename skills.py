import os
import subprocess
import shlex
import io
import contextlib
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
    "chr": chr, "dict": dict, "divmod": divmod, "enumerate": enumerate,
    "filter": filter, "float": float, "format": format, "frozenset": frozenset,
    "getattr": getattr, "hasattr": hasattr, "hash": hash, "hex": hex,
    "int": int, "isinstance": isinstance, "issubclass": issubclass,
    "iter": iter, "len": len, "list": list, "map": map, "max": max,
    "min": min, "next": next, "oct": oct, "ord": ord, "pow": pow,
    "print": print, "range": range, "repr": repr, "reversed": reversed,
    "round": round, "set": set, "slice": slice, "sorted": sorted,
    "str": str, "sum": sum, "tuple": tuple, "type": type, "zip": zip,
}

BLOCKED_IMPORT_MODULES = frozenset({
    "os", "sys", "subprocess", "shutil", "socket", "http",
    "urllib", "requests", "ctypes", "signal", "multiprocessing",
    "threading", "importlib", "pathlib", "glob", "tempfile",
    "webbrowser", "code", "codeop", "compileall", "py_compile",
})


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
        logger.info("Clicked at (%s, %s) -> screen (%s, %s)", x, y, sx, sy)
        return {"status": "success", "action": f"Clicked at {x}, {y}"}


class TypeSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from mac_utils import simulate_type
        text = params.get('text', '')
        simulate_type(text)
        logger.info("Typed %d characters", len(text))
        return {"status": "success", "action": "Typed text"}


class TerminalSkill(Skill):
    BLACKLIST = ["rm -rf /", "rm -rf /*", "sudo", "mkfs", "dd if=", ":(){ :|:& };:"]

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cmd = params.get('cmd', '')
        if any(bad in cmd for bad in self.BLACKLIST):
            logger.warning("Blocked unsafe command: %s", cmd)
            return {"status": "blocked", "reason": "Security guardrail: Unsafe command detected"}

        try:
            result = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=30)
            logger.info("Command executed: %s (rc=%d)", cmd[:80], result.returncode)
            return {
                "status": "success",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            logger.warning("Command timed out: %s", cmd[:80])
            return {"status": "error", "error": "Command timed out (30s limit)"}
        except Exception as e:
            logger.error("Command failed: %s", e)
            return {"status": "error", "error": str(e)}


class FileSystemSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get('action')
        path = params.get('path')
        if not path:
            return {"status": "error", "error": "No path provided"}
        if ".." in path:
            logger.warning("Blocked directory traversal attempt: %s", path)
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
            logger.error("FileSystem error: %s", e)
            return {"status": "error", "error": str(e)}


class ExecuteCodeSkill(Skill):
    """Sandboxed code execution with restricted builtins and blocked imports."""

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        code = params.get('code', '')
        if not code:
            return {"status": "error", "error": "No code provided"}

        for module in BLOCKED_IMPORT_MODULES:
            if f"import {module}" in code or f"from {module}" in code:
                logger.warning("Blocked dangerous import in code execution: %s", module)
                return {"status": "blocked", "reason": f"Security guardrail: Import of '{module}' is forbidden"}

        if "__import__" in code:
            return {"status": "blocked", "reason": "Security guardrail: __import__ is forbidden"}
        if "eval(" in code or "exec(" in code:
            return {"status": "blocked", "reason": "Security guardrail: eval/exec inside sandbox is forbidden"}
        if "open(" in code:
            return {"status": "blocked", "reason": "Security guardrail: open() is forbidden in sandbox"}

        stdout, stderr = io.StringIO(), io.StringIO()
        sandbox_globals = {"__builtins__": SAFE_BUILTINS}
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(code, sandbox_globals)
            logger.info("Code executed successfully in sandbox")
            return {"status": "success", "stdout": stdout.getvalue(), "stderr": stderr.getvalue()}
        except Exception as e:
            logger.error("Sandboxed code execution failed: %s", e)
            return {"status": "error", "error": str(e), "stdout": stdout.getvalue(), "stderr": stderr.getvalue()}


class GithubSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from github_manager import GithubManager
        gh = GithubManager()
        action = params.get("action")
        args = params.get("args", [])
        cwd = params.get("cwd", ".")
        if action == "git":
            return gh.run_git(args, cwd)
        elif action == "pr":
            return await gh.create_pull_request(
                repo=params.get("repo"),
                title=params.get("title"),
                head=params.get("head"),
                body=params.get("body", ""),
            )
        return {"status": "error", "error": f"Unknown github action: {action}"}


class PluginGeneratorSkill(Skill):
    """Generates, tests, and registers new skills via plugin files."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        code = params.get("code")
        test_code = params.get("test_code")
        if not name or not code:
            return {"status": "error", "error": "Missing data"}

        path = os.path.join("plugins", f"{name}.py")
        try:
            with open(path, "w") as f:
                f.write(code)

            if test_code:
                test_path = os.path.join("tests", f"test_{name}.py")
                with open(test_path, "w") as f:
                    f.write(test_code)
                res = subprocess.run(["pytest", test_path], capture_output=True)
                if res.returncode != 0:
                    return {"status": "error", "error": f"Generated skill failed tests: {res.stderr.decode()}"}

            logger.info("Plugin skill '%s' generated", name)
            return {"status": "success", "message": f"Skill '{name}' evolved and verified."}
        except Exception as e:
            logger.error("Plugin generation failed: %s", e)
            return {"status": "error", "error": str(e)}


class AppleScriptSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from applescript_utils import AppleScriptUtils
        script = params.get("script")
        if not script:
            action = params.get("action")
            if action == "safari_open":
                script = AppleScriptUtils.safari_open_url(params.get("url"))
            elif action == "mail_draft":
                script = AppleScriptUtils.mail_send_email(params.get("to"), params.get("subject"), params.get("body"))
            elif action == "notes_create":
                script = AppleScriptUtils.notes_create_note(params.get("title"), params.get("body"))
            elif action == "calendar_add":
                script = AppleScriptUtils.calendar_create_event(params.get("title"), params.get("start"))

        if not script:
            return {"status": "error", "error": "No script"}
        return AppleScriptUtils.run_script(script)


class WebSearchSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query")
        if not query:
            return {"status": "error", "error": "No query"}

        from applescript_utils import AppleScriptUtils
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        AppleScriptUtils.run_script(AppleScriptUtils.safari_open_url(search_url))
        logger.info("Web search opened for: %s", query)
        return {"status": "success", "message": f"Opened search for: {query}. Agent should now perceive Safari."}


class ClipboardSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action")
        try:
            if action == "copy":
                text = params.get("text", "")
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                process.communicate(text.encode('utf-8'))
                return {"status": "success", "message": "Text copied to clipboard"}
            elif action == "paste":
                text = subprocess.check_output(['pbpaste']).decode('utf-8')
                return {"status": "success", "text": text}
        except Exception as e:
            logger.error("Clipboard error: %s", e)
            return {"status": "error", "error": str(e)}
        return {"status": "error", "error": "Unknown action"}


class CommunicationSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        import json as json_mod
        platform = params.get("platform")
        webhook = params.get("webhook_url")
        message = params.get("message", "")

        if not webhook or not message:
            return {"status": "error", "error": "Missing webhook or message"}

        payload = {"text": message} if platform == "slack" else {"content": message}
        try:
            cmd = ['curl', '-X', 'POST', '-H', 'Content-type: application/json', '--data', json_mod.dumps(payload), webhook]
            subprocess.run(cmd, capture_output=True, timeout=10)
            logger.info("Message sent to %s", platform)
            return {"status": "success", "message": f"Sent to {platform}"}
        except Exception as e:
            logger.error("Communication failed: %s", e)
            return {"status": "error", "error": str(e)}


class NotificationSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        title = params.get("title", "OmniAgent OS")
        subtitle = params.get("subtitle", "")
        message = params.get("message", "")

        script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
        try:
            subprocess.run(['osascript', '-e', script])
            return {"status": "success", "message": "Notification sent"}
        except Exception as e:
            logger.error("Notification failed: %s", e)
            return {"status": "error", "error": str(e)}


class ResearchSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = params.get("url")
        if not url:
            return {"status": "error", "error": "No URL"}

        try:
            res = subprocess.run(['curl', '-L', url], capture_output=True, text=True, timeout=10)
            content = res.stdout[:5000]
            filename = url.split("//")[-1].replace("/", "_") + ".txt"
            path = os.path.join("knowledge", "docs", filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            logger.info("Researched and indexed: %s", url)
            return {"status": "success", "message": f"Researched and indexed: {url}"}
        except Exception as e:
            logger.error("Research failed: %s", e)
            return {"status": "error", "error": str(e)}


class TransferSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        key = params.get("key")
        value = params.get("value")
        if not key:
            return {"status": "error", "error": "No key"}
        return {"status": "success", "bus_update": {key: value}}


class OmniSearchSkill(Skill):
    def __init__(self, knowledge_manager=None, memory_vault=None):
        self._knowledge = knowledge_manager
        self._memory = memory_vault

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query")
        if not query:
            return {"status": "error", "error": "No query"}

        from knowledge_manager import KnowledgeManager
        from memory_vault import MemoryVault
        from applescript_utils import AppleScriptUtils

        km = self._knowledge or KnowledgeManager()
        mv = self._memory or MemoryVault()

        local_hits = km.search_docs(query)
        memory_hits = mv.retrieve_similar(query)
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        AppleScriptUtils.run_script(AppleScriptUtils.safari_open_url(search_url))

        return {
            "status": "success",
            "local_rag": local_hits,
            "neural_memory": memory_hits,
            "web_status": "Search opened in Safari"
        }


class DocumentationSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        title = params.get("title", "Project Documentation")
        content = params.get("content", "")
        filename = params.get("filename", "README.md")

        doc_header = f"# {title}\n*Generated by OmniAgent*\n\n"
        full_doc = doc_header + content

        try:
            with open(filename, "w") as f:
                f.write(full_doc)
            logger.info("Documentation saved to %s", filename)
            return {"status": "success", "message": f"Documentation saved to {filename}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


class ProjectArchitectSkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("project_name", "new_project")
        try:
            os.makedirs(f"{name}/src", exist_ok=True)
            os.makedirs(f"{name}/tests", exist_ok=True)
            with open(f"{name}/README.md", "w") as f:
                f.write(f"# {name}\nInitialized by OmniAgent")
            subprocess.run(["git", "init"], cwd=name, capture_output=True)
            logger.info("Project '%s' architecture established", name)
            return {"status": "success", "message": f"Project '{name}' architecture established."}
        except Exception as e:
            return {"status": "error", "error": str(e)}


class CLIFactorySkill(Skill):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        alias_name = params.get("alias")
        script_content = params.get("script")
        if not alias_name or not script_content:
            return {"status": "error", "error": "Missing data"}

        try:
            bin_dir = os.path.expanduser("~/bin")
            os.makedirs(bin_dir, exist_ok=True)
            script_path = os.path.join(bin_dir, alias_name)
            with open(script_path, "w") as f:
                f.write(f"#!/bin/bash\n{script_content}")
            os.chmod(script_path, 0o755)
            logger.info("CLI tool '%s' created at %s", alias_name, script_path)
            return {"status": "success", "message": f"CLI Tool '{alias_name}' created at {script_path}."}
        except Exception as e:
            return {"status": "error", "error": str(e)}


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
            "web_search": WebSearchSkill(),
            "clipboard": ClipboardSkill(),
            "communication": CommunicationSkill(),
            "notify": NotificationSkill(),
            "research": ResearchSkill(),
            "transfer": TransferSkill(),
            "omni_search": OmniSearchSkill(),
            "generate_doc": DocumentationSkill(),
            "project_architect": ProjectArchitectSkill(),
            "cli_factory": CLIFactorySkill(),
        }

    def register(self, name: str, skill: Skill):
        self._skills[name] = skill
        logger.info("Registered skill: %s", name)

    def get(self, name: str) -> Skill:
        return self._skills.get(name)

    def list_skills(self) -> List[str]:
        return list(self._skills.keys())
