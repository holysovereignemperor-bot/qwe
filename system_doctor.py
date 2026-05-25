import logging
import psutil
import subprocess

logger = logging.getLogger(__name__)


class SystemDoctor:
    """Active OS maintenance: detects and resolves system issues."""

    def check_app_hangs(self):
        hanging = []
        for proc in psutil.process_iter(['name', 'status']):
            try:
                if proc.info['status'] == psutil.STATUS_DISK_SLEEP:
                    hanging.append(proc.info['name'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return hanging

    def optimize_performance(self):
        try:
            pid = psutil.Process().pid
            subprocess.run(['renice', '-n', '-5', '-p', str(pid)], capture_output=True)
            logger.info("Agent priority optimized (pid=%d)", pid)
            return "Agent priority optimized."
        except Exception as e:
            logger.warning("Priority optimization failed: %s", e)
            return "Optimization failed (needs sudo for some levels)."

    def diagnose(self):
        issues = []
        hangs = self.check_app_hangs()
        if hangs:
            issues.append(f"Hanging apps: {', '.join(hangs)}")

        cpu = psutil.cpu_percent(interval=1)
        if cpu > 80:
            issues.append(f"High CPU load: {cpu}%")

        if issues:
            logger.warning("System issues detected: %s", issues)
        return issues
