import logging

logger = logging.getLogger(__name__)

try:
    from Cocoa import NSSpeechSynthesizer
except ImportError:
    NSSpeechSynthesizer = None


class VoiceOS:
    """Allows the agent to speak using native macOS speech synthesis."""

    def __init__(self, voice="com.apple.speech.synthesis.voice.Alex"):
        self.enabled = False
        if NSSpeechSynthesizer:
            self.synth = NSSpeechSynthesizer.alloc().initWithVoice_(voice)
        else:
            self.synth = None

    def speak(self, text: str):
        if self.enabled and self.synth:
            self.synth.speakString_(text)
            logger.debug("Speaking: %s", text[:50])

    def set_enabled(self, state: bool):
        self.enabled = state
        logger.info("Voice output %s", "enabled" if state else "disabled")
