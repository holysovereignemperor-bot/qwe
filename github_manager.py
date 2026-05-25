import subprocess
import os
import json
import logging
from typing import Dict, Any, List

import requests

logger = logging.getLogger(__name__)


class GithubManager:
    """Handles Git and GitHub API operations with security guardrails."""

    GITHUB_API_URL = "https://api.github.com"

    def __init__(self, token: str = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.PROTECTED_BRANCHES = ["main", "master", "production"]

    def run_git(self, args: List[str], cwd: str = ".") -> Dict[str, Any]:
        if "push" in args:
            for branch in self.PROTECTED_BRANCHES:
                if branch in args:
                    logger.warning("Blocked push to protected branch: %s", branch)
                    return {
                        "status": "blocked",
                        "reason": f"Security guardrail: Direct push to protected branch '{branch}' is forbidden.",
                    }

        if "add" in args:
            sensitive_files = {".env", "id_rsa", ".env.local", "credentials.json", "vault.key"}
            for arg in args:
                if arg in sensitive_files:
                    logger.warning("Blocked adding sensitive file: %s", arg)
                    return {
                        "status": "blocked",
                        "reason": "Security guardrail: Attempt to add sensitive credentials detected.",
                    }

        try:
            result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=30)
            return {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Git command timed out"}
        except Exception as e:
            logger.error("Git command failed: %s", e)
            return {"status": "error", "error": str(e)}

    async def create_pull_request(
        self,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
    ) -> Dict[str, Any]:
        if not self.token:
            return {"status": "error", "error": "GitHub token not configured. Set GITHUB_TOKEN env var."}

        if not repo or not title or not head:
            return {"status": "error", "error": "Missing required fields: repo, title, head"}

        url = f"{self.GITHUB_API_URL}/repos/{repo}/pulls"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        payload = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code == 201:
                pr_data = response.json()
                logger.info("PR created: %s", pr_data.get("html_url"))
                return {
                    "status": "success",
                    "pr_url": pr_data.get("html_url"),
                    "pr_number": pr_data.get("number"),
                }
            else:
                error_msg = response.json().get("message", response.text)
                logger.error("PR creation failed (%d): %s", response.status_code, error_msg)
                return {"status": "error", "error": f"GitHub API error ({response.status_code}): {error_msg}"}
        except requests.Timeout:
            return {"status": "error", "error": "GitHub API request timed out"}
        except Exception as e:
            logger.error("PR creation exception: %s", e)
            return {"status": "error", "error": str(e)}
