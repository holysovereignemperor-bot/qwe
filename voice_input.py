try:
    from Cocoa import NSSpeechRecognizer, NSObject
except ImportError:
    NSSpeechRecognizer = NSObject = None

class VoiceInput(NSObject):
    """Native macOS Voice Recognition for goal initiation."""
    def initWithCallback_(self, callback):
        self = super().init()
        if self:
            self.callback = callback
            self.recognizer = NSSpeechRecognizer.alloc().init()
            self.recognizer.setDelegate_(self)
            # Example triggers
            self.recognizer.setCommands_(["start research", "check mail", "stop agent"])
        return self

    def speechRecognizer_didRecognizeCommand_(self, recognizer, command):
        print(f"Recognized Voice Command: {command}")
        if self.callback:
            self.callback(str(command))

    def start_listening(self):
        if self.recognizer:
            self.recognizer.startListening()

    def stop_listening(self):
        if self.recognizer:
            self.recognizer.stopListening()
