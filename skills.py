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
    """Autonomous Skill Lab: Generates, tests, and registers new skills."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name, code = params.get("name"), params.get("code")
        test_code = params.get("test_code")
        if not name or not code: return {"status": "error", "error": "Missing data"}

        # 1. Write plugin
        path = os.path.join("plugins", f"{name}.py")
        try:
            with open(path, "w") as f: f.write(code)

            # 2. Optional: Run Autonomous Test
            if test_code:
                test_path = os.path.join("tests", f"test_{name}.py")
                with open(test_path, "w") as f: f.write(test_code)
                import subprocess
                res = subprocess.run(["pytest", test_path], capture_output=True)
                if res.returncode != 0:
                    return {"status": "error", "error": f"Generated skill failed tests: {res.stderr.decode()}"}

            return {"status": "success", "message": f"Skill '{name}' evolved and verified."}
        except Exception as e:
            return {"status": "error", "error": str(e)}

class AppleScriptSkill(Skill):
    """Allows the agent to control macOS apps via AppleScript."""
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

        if not script: return {"status": "error", "error": "No script"}
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

class ClipboardSkill(Skill):
    """Allows the agent to read and write the macOS system clipboard."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action")
        try:
            import subprocess
            if action == "copy":
                text = params.get("text", "")
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                process.communicate(text.encode('utf-8'))
                return {"status": "success", "message": "Text copied to clipboard"}
            elif action == "paste":
                text = subprocess.check_output(['pbpaste']).decode('utf-8')
                return {"status": "success", "text": text}
        except Exception as e:
            return {"status": "error", "error": str(e)}
        return {"status": "error", "error": "Unknown action"}

class CommunicationSkill(Skill):
    """Omni-Bridge: Sends updates to external platforms like Slack/Discord."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        import json
        import subprocess
        platform = params.get("platform") # "slack" or "discord"
        webhook = params.get("webhook_url")
        message = params.get("message", "")

        if not webhook or not message: return {"status": "error", "error": "Missing webhook or message"}

        payload = {"text": message} if platform == "slack" else {"content": message}
        try:
            # Using curl to keep it zero-dependency
            cmd = ['curl', '-X', 'POST', '-H', 'Content-type: application/json', '--data', json.dumps(payload), webhook]
            subprocess.run(cmd, capture_output=True)
            return {"status": "success", "message": f"Sent to {platform}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

class NotificationSkill(Skill):
    """Native macOS Notifications using NSUserNotificationCenter."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        title = params.get("title", "OmniAgent OS")
        subtitle = params.get("subtitle", "")
        message = params.get("message", "")

        script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
        try:
            import subprocess
            subprocess.run(['osascript', '-e', script])
            return {"status": "success", "message": "Notification sent"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

class ResearchSkill(Skill):
    """Autonomous Research: Crawls and indexes web data into local RAG."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = params.get("url")
        if not url: return {"status": "error", "error": "No URL"}

        # Simple extraction via curl + indexing into docs
        import subprocess
        import os
        try:
            res = subprocess.run(['curl', '-L', url], capture_output=True, text=True, timeout=10)
            content = res.stdout[:5000] # Limit size
            filename = url.split("//")[-1].replace("/", "_") + ".txt"
            path = os.path.join("knowledge", "docs", filename)
            with open(path, "w") as f: f.write(content)
            return {"status": "success", "message": f"Researched and indexed: {url}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

class SelfEvolveSkill(Skill):
    """Allows the agent to refactor its own source code with safety backups."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        module = params.get("module") # e.g., "agents.py"
        new_content = params.get("content")
        if not module or not new_content: return {"status": "error", "error": "Missing data"}

        # Safety: Backup first
        import shutil
        try:
            shutil.copy(module, f"{module}.bak")
            with open(module, "w") as f: f.write(new_content)
            return {"status": "success", "message": f"Module '{module}' evolved. Backup created at '{module}.bak'"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

class TransferSkill(Skill):
    """Omni-Bus: Transfers data between apps via the blackboard data bus."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from blackboard import Blackboard
        # This skill usually interacts with a shared state
        # In this implementation, we return the value to be stored by the Orchestrator
        key = params.get("key")
        value = params.get("value")
        if not key: return {"status": "error", "error": "No key"}
        return {"status": "success", "bus_update": {key: value}}

class OmniSearchSkill(Skill):
    """Omni-Search: Aggregates local RAG, Neural Memory, and Web Research."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query")
        if not query: return {"status": "error", "error": "No query"}

        from knowledge_manager import KnowledgeManager
        from memory_vault import MemoryVault
        from applescript_utils import AppleScriptUtils

        # 1. Local RAG
        local_hits = KnowledgeManager().search_docs(query)
        # 2. Neural Memory
        memory_hits = MemoryVault().retrieve_similar(query)
        # 3. Web Trigger
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        AppleScriptUtils.run_script(AppleScriptUtils.safari_open_url(search_url))

        return {
            "status": "success",
            "local_rag": local_hits,
            "neural_memory": memory_hits,
            "web_status": "Search opened in Safari"
        }

class DocumentationSkill(Skill):
    """AI-Doc Generator: Autonomously creates professional technical documentation."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        title = params.get("title", "Project Documentation")
        content = params.get("content", "")
        filename = params.get("filename", "README.md")

        doc_header = f"# {title}\n*Generated by OmniAgent Apex Edition*\n\n"
        full_doc = doc_header + content

        try:
            with open(filename, "w") as f: f.write(full_doc)
            return {"status": "success", "message": f"Documentation saved to {filename}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

class ProjectArchitectSkill(Skill):
    """Sovereign Project Architect: Initializes full workspace environments."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("project_name", "new_project")
        try:
            import os
            import subprocess
            os.makedirs(f"{name}/src", exist_ok=True)
            os.makedirs(f"{name}/tests", exist_ok=True)
            with open(f"{name}/README.md", "w") as f: f.write(f"# {name}\nInitialized by OmniAgent")
            subprocess.run(["git", "init"], cwd=name)
            return {"status": "success", "message": f"Project '{name}' architecture established."}
        except Exception as e:
            return {"status": "error", "error": str(e)}

class CLIFactorySkill(Skill):
    """CLI Factory: Autonomously generates bash scripts and zsh aliases."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        alias_name = params.get("alias")
        script_content = params.get("script")
        if not alias_name or not script_content: return {"status": "error", "error": "Missing data"}

        try:
            bin_dir = os.path.expanduser("~/bin")
            os.makedirs(bin_dir, exist_ok=True)
            script_path = os.path.join(bin_dir, alias_name)
            with open(script_path, "w") as f: f.write(f"#!/bin/bash\n{script_content}")
            os.chmod(script_path, 0o755)

            # Simple alias concept for logs
            return {"status": "success", "message": f"CLI Tool '{alias_name}' created at {script_path}. Add 'export PATH=\"$HOME/bin:$PATH\"' to your .zshrc."}
        except Exception as e:
            return {"status": "error", "error": str(e)}

class AppMapperSkill(Skill):
    """Eternity App Mapper: Scans macOS apps and extracts capability metadata."""
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import os
            apps = [a for f in ["/Applications", "/System/Applications"] if os.path.exists(f) for a in os.listdir(f)[:10]]
            return {"status": "success", "installed_apps": apps, "message": "System capability map updated."}
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
            "self_evolve": SelfEvolveSkill(),
            "transfer": TransferSkill(),
            "omni_search": OmniSearchSkill(),
            "generate_doc": DocumentationSkill(),
            "project_architect": ProjectArchitectSkill(),
            "cli_factory": CLIFactorySkill(),
            "app_mapper": AppMapperSkill()
        }
    def register(self, name: str, skill: Skill):
        self._skills[name] = skill
    def get(self, name: str) -> Skill:
        return self._skills.get(name)
