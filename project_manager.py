import os
import subprocess
from typing import List, Dict, Any

class ProjectManager:
    """Detects active applications and manages workspace context."""
    def __init__(self):
        pass

    def get_active_apps(self) -> List[str]:
        """Returns a list of names of running applications using AppleScript."""
        script = 'tell application "System Events" to get name of every process whose background only is false'
        try:
            output = subprocess.check_output(['osascript', '-e', script]).decode('utf-8')
            return [name.strip() for name in output.split(',')]
        except Exception:
            return []

    def get_workspace_summary(self) -> str:
        apps = self.get_active_apps()
        summary = f"Active Applications: {', '.join(apps)}\n"
        # Could add file listing of current directory etc.
        summary += f"Working Directory: {os.getcwd()}\n"
        return summary
