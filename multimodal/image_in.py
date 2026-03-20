from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ImageInConfig:
    backend: str = "blip2"
    include_embedding_hint: bool = True


class ImageInAdapter:
    """
    Image input adapter.

    Primary output is text caption to satisfy synthesis pipeline constraints.
    """

    def __init__(self, config: ImageInConfig | None = None) -> None:
        self.config = config or ImageInConfig()

    def caption(self, image: bytes) -> str:
        if not image:
            return ""
        base = f"[image-caption backend={self.config.backend} bytes={len(image)}]"
        if self.config.include_embedding_hint:
            return base + " visual embedding available but text-caption is primary."
        return base
