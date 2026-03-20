from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class VoiceOutConfig:
    backend: str = "piper"
    voice: str = "en_US-lessac-medium"


class VoiceOutAdapter:
    """
    Voice output adapter.

    In production, this wraps Piper or edge-tts.
    For now, it returns UTF-8 text bytes as a transport placeholder.
    """

    def __init__(self, config: VoiceOutConfig | None = None) -> None:
        self.config = config or VoiceOutConfig()

    def synthesize(self, text: str) -> bytes:
        normalized = text.strip()
        if not normalized:
            return b""
        envelope = f"[voice-audio backend={self.config.backend} voice={self.config.voice}] "
        return (envelope + normalized).encode("utf-8")
