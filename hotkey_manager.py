import logging

logger = logging.getLogger(__name__)

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
        logger.info("Global hotkey activated")
        if self.callback:
            self.callback()

    def start(self):
        if not keyboard:
            logger.warning("pynput not available, hotkeys disabled")
            return
        h = keyboard.GlobalHotkeys({
            '<cmd>+<shift>+o': self._on_activate
        })
        self.listener = h
        self.listener.start()
        logger.info("Hotkey listener started (CMD+SHIFT+O)")

    def stop(self):
        if self.listener:
            self.listener.stop()
            logger.info("Hotkey listener stopped")
