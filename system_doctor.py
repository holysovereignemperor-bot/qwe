import psutil
import subprocess

class SystemDoctor:
    """Active OS Maintenance: Detects and resolves macOS system issues."""
    def __init__(self):
        pass

    def check_app_hangs(self):
        """Identifies unresponsive applications (Simplified concept)."""
        hanging = []
        for proc in psutil.process_iter(['name', 'status']):
            if proc.info['status'] == psutil.STATUS_DISK_SLEEP: # Often indicates IO hang
                 hanging.append(proc.info['name'])
        return hanging

    def optimize_performance(self):
        """Renice's the agent process to ensure priority on 8GB M1."""
        try:
            pid = psutil.Process().pid
            subprocess.run(['renice', '-n', '-5', '-p', str(pid)], capture_output=True)
            return "Agent priority optimized."
        except Exception: return "Optimization failed (needs sudo for some levels)."

    def diagnose(self):
        issues = []
        hangs = self.check_app_hangs()
        if hangs: issues.append(f"Hanging apps: {', '.join(hangs)}")

        cpu = psutil.cpu_percent(interval=1)
        if cpu > 80: issues.append(f"High CPU load: {cpu}%")

        return issues
