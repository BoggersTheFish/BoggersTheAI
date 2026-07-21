from __future__ import annotations

try:
    from ..core.protocols import ImageInProtocol, VoiceInProtocol, VoiceOutProtocol
except ImportError:
    from core.protocols import ImageInProtocol, VoiceInProtocol, VoiceOutProtocol

__all__ = ["VoiceInProtocol", "VoiceOutProtocol", "ImageInProtocol"]
