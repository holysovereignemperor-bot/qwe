import psutil
import os

class SystemWatchdog:
    """Monitors M1 system health to prevent overheating or RAM exhaustion."""
    def __init__(self, ram_limit_pct=90.0, disk_limit_pct=95.0):
        self.ram_limit = ram_limit_pct
        self.disk_limit = disk_limit_pct

    def check_health(self):
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent

        status = {"ram": ram, "disk": disk, "critical": False, "reason": ""}

        if ram > self.ram_limit:
            status["critical"] = True
            status["reason"] = f"RAM usage critical ({ram}%)"
        elif disk > self.disk_limit:
            status["critical"] = True
            status["reason"] = f"Disk space critical ({disk}%)"

        return status
