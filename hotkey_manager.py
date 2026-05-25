try:
    from pynput import keyboard
except ImportError:
    keyboard = None

class HotkeyManager:
    """Supports global shortcuts to invoke the agent."""
    def __init__(self, callback):
        self.callback = callback
        self.listener = None

    def _on_activate(self):
        print("Global Hotkey Activated!")
        if self.callback: self.callback()

    def start(self):
        if not keyboard: return
        # Shortcut: CMD + SHIFT + O
        h = keyboard.GlobalHotkeys({
            '<cmd>+<shift>+o': self._on_activate
        })
        self.listener = h
        self.listener.start()

    def stop(self):
        if self.listener: self.listener.stop()
