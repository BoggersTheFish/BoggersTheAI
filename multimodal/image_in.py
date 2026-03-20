from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("boggers.multimodal.image_in")


@dataclass(slots=True)
class ImageInConfig:
    backend: str = "blip2"
    model_name: str = "Salesforce/blip2-opt-2.7b"


class ImageInAdapter:
    def __init__(self, config: ImageInConfig | None = None) -> None:
        self.config = config or ImageInConfig()
        self._processor = None
        self._model = None

    def caption(self, image: bytes) -> str:
        if not image:
            return ""
        if self.config.backend == "blip2":
            return self._caption_blip2(image)
        return self._caption_placeholder(image)

    def _caption_blip2(self, image: bytes) -> str:
        try:
            import io

            from PIL import Image
            from transformers import Blip2ForConditionalGeneration, Blip2Processor

            if self._processor is None:
                self._processor = Blip2Processor.from_pretrained(self.config.model_name)
                self._model = Blip2ForConditionalGeneration.from_pretrained(
                    self.config.model_name
                )
            pil_image = Image.open(io.BytesIO(image)).convert("RGB")
            inputs = self._processor(images=pil_image, return_tensors="pt")
            output = self._model.generate(**inputs, max_new_tokens=50)
            caption = self._processor.decode(
                output[0], skip_special_tokens=True
            ).strip()
            logger.info("Captioned %d bytes -> '%s'", len(image), caption[:80])
            return caption
        except ImportError:
            logger.info("transformers/PIL not installed; using placeholder")
            return self._caption_placeholder(image)
        except Exception as exc:
            logger.warning("Image captioning failed: %s", exc)
            return self._caption_placeholder(image)

    def _caption_placeholder(self, image: bytes) -> str:
        return f"[image-caption backend={self.config.backend} bytes={len(image)}]"
