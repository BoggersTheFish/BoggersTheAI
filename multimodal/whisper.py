from __future__ import annotations

from .voice_in import VoiceInAdapter, VoiceInConfig


class WhisperAdapter(VoiceInAdapter):
    """Thin wrapper that pins the backend to ``faster-whisper``."""

    def __init__(self, config: VoiceInConfig | None = None) -> None:
        cfg = config or VoiceInConfig()
        cfg.backend = "faster-whisper"
        super().__init__(config=cfg)
