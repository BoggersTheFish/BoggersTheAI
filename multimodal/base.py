from __future__ import annotations

from typing import Protocol


class VoiceInProtocol(Protocol):
    def transcribe(self, audio: bytes) -> str: ...


class VoiceOutProtocol(Protocol):
    def synthesize(self, text: str) -> bytes: ...


class ImageInProtocol(Protocol):
    def caption(self, image: bytes) -> str: ...
