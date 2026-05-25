import os
import time
import threading
from typing import Callable

class WatcherService:
    """Proactive Monitoring: Automatically triggers tasks based on system events."""
    def __init__(self, watch_dir: str, callback: Callable):
        self.watch_dir = watch_dir
        self.callback = callback
        self.is_running = False
        self.known_files = set(os.listdir(watch_dir)) if os.path.exists(watch_dir) else set()

    def start(self):
        self.is_running = True
        threading.Thread(target=self._watch_loop, daemon=True).start()

    def stop(self):
        self.is_running = False

    def _watch_loop(self):
        while self.is_running:
            if os.path.exists(self.watch_dir):
                current_files = set(os.listdir(self.watch_dir))
                new_files = current_files - self.known_files

                for f in new_files:
                    print(f"Watcher: New file detected: {f}")
                    # Trigger autonomous task
                    if self.callback:
                        self.callback(f"New file in {self.watch_dir}: {f}. Analyze and sort it.")

                self.known_files = current_files
            time.sleep(5) # Low polling to save M1 RAM
