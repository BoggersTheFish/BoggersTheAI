from __future__ import annotations

from .image_in import ImageInAdapter, ImageInConfig


class ClipCaptionAdapter(ImageInAdapter):
    """Thin wrapper that pins the backend to ``clip``."""

    def __init__(self, config: ImageInConfig | None = None) -> None:
        cfg = config or ImageInConfig()
        cfg.backend = "clip"
        super().__init__(config=cfg)
