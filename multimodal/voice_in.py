from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class VoiceInConfig:
    backend: str = "faster-whisper"
    sample_rate_hz: int = 16000


class VoiceInAdapter:
    """
    Voice input adapter.

    In production, this wraps `faster-whisper`, `whisper.cpp`, or `vosk`.
    Current implementation is a CPU-friendly placeholder that returns
    a deterministic marker for pipeline wiring.
    """

    def __init__(self, config: VoiceInConfig | None = None) -> None:
        self.config = config or VoiceInConfig()

    def transcribe(self, audio: bytes) -> str:
        if not audio:
            return ""
        # Placeholder result until a local STT backend is configured.
        return (
            f"[voice-transcript backend={self.config.backend} "
            f"bytes={len(audio)} sample_rate={self.config.sample_rate_hz}]"
        )
