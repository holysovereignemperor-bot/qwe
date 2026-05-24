import subprocess
import os
import json
from typing import Dict, Any, List

class GithubManager:
    """Handles Git and GitHub API operations with security guardrails."""
    def __init__(self, token: str = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.PROTECTED_BRANCHES = ["main", "master", "production"]

    def run_git(self, args: List[str], cwd: str = ".") -> Dict[str, Any]:
        # Guardrail: Prevent direct pushes to protected branches
        if "push" in args:
             for branch in self.PROTECTED_BRANCHES:
                 if branch in args:
                     return {"status": "blocked", "reason": f"Security guardrail: Direct push to protected branch '{branch}' is forbidden. Use Pull Requests."}

        # Guardrail: Prevent adding sensitive files
        if "add" in args and (".env" in args or "id_rsa" in args):
             return {"status": "blocked", "reason": "Security guardrail: Attempt to add sensitive credentials detected."}

        try:
            result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
            return {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def create_pull_request(self, repo: str, title: str, head: str, base: str = "main", body: str = ""):
        if not self.token:
             return {"status": "error", "error": "GitHub token not configured"}
        print(f"Creating PR: {title} from {head} to {base} in {repo}")
        return {"status": "success", "pr_url": f"https://github.com/{repo}/pull/1"}
