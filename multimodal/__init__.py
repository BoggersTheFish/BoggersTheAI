from __future__ import annotations

from .base import ImageInProtocol, VoiceInProtocol, VoiceOutProtocol
from .image_in import ImageInAdapter, ImageInConfig
from .voice_in import VoiceInAdapter, VoiceInConfig
from .voice_out import VoiceOutAdapter, VoiceOutConfig


class WhisperAdapter(VoiceInAdapter):
    """Thin wrapper that pins the backend to ``faster-whisper``."""

    def __init__(self, config: VoiceInConfig | None = None) -> None:
        cfg = config or VoiceInConfig()
        cfg.backend = "faster-whisper"
        super().__init__(config=cfg)


class ClipCaptionAdapter(ImageInAdapter):
    """Thin wrapper that pins the backend to ``clip``."""

    def __init__(self, config: ImageInConfig | None = None) -> None:
        cfg = config or ImageInConfig()
        cfg.backend = "clip"
        super().__init__(config=cfg)


__all__ = [
    "ClipCaptionAdapter",
    "ImageInAdapter",
    "ImageInConfig",
    "ImageInProtocol",
    "VoiceInAdapter",
    "VoiceInConfig",
    "VoiceInProtocol",
    "VoiceOutAdapter",
    "VoiceOutConfig",
    "VoiceOutProtocol",
    "WhisperAdapter",
]
