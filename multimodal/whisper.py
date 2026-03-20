from __future__ import annotations

from .voice_in import VoiceInAdapter, VoiceInConfig


class WhisperAdapter(VoiceInAdapter):
    def __init__(self, config: VoiceInConfig | None = None) -> None:
        super().__init__(config=config or VoiceInConfig(backend="faster-whisper"))
