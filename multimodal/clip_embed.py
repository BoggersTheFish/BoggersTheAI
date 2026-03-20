from __future__ import annotations

from .image_in import ImageInAdapter, ImageInConfig


class ClipCaptionAdapter(ImageInAdapter):
    def __init__(self, config: ImageInConfig | None = None) -> None:
        super().__init__(config=config or ImageInConfig(backend="clip"))
