import logging

logger = logging.getLogger(__name__)

try:
    from Cocoa import NSSpeechRecognizer, NSObject
except ImportError:
    NSSpeechRecognizer = NSObject = None


if NSObject:
    class VoiceInput(NSObject):
        """Native macOS Voice Recognition for goal initiation."""

        def initWithCallback_(self, callback):
            self = super().init()
            if self:
                self.callback = callback
                self.recognizer = NSSpeechRecognizer.alloc().init()
                self.recognizer.setDelegate_(self)
                self.recognizer.setCommands_(["start research", "check mail", "stop agent"])
            return self

        def speechRecognizer_didRecognizeCommand_(self, recognizer, command):
            logger.info("Voice command recognized: %s", command)
            if self.callback:
                self.callback(str(command))

        def start_listening(self):
            if self.recognizer:
                self.recognizer.startListening()
                logger.info("Voice input listening started")

        def stop_listening(self):
            if self.recognizer:
                self.recognizer.stopListening()
                logger.info("Voice input listening stopped")
else:
    class VoiceInput:
        """Stub for non-macOS platforms."""

        def __init__(self, callback=None):
            self.callback = callback
            logger.info("VoiceInput unavailable (not macOS)")

        def start_listening(self):
            pass

        def stop_listening(self):
            pass
