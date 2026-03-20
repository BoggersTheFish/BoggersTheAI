from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("boggers.multimodal.voice_out")


@dataclass(slots=True)
class VoiceOutConfig:
    backend: str = "piper"
    model: str = "en_US-lessac-medium"


class VoiceOutAdapter:
    def __init__(self, config: VoiceOutConfig | None = None) -> None:
        self.config = config or VoiceOutConfig()

    def synthesize(self, text: str) -> bytes:
        if not text:
            return b""
        if self.config.backend == "piper":
            return self._synthesize_piper(text)
        return self._synthesize_placeholder(text)

    def _synthesize_piper(self, text: str) -> bytes:
        try:
            import subprocess

            result = subprocess.run(
                ["piper", "--model", self.config.model, "--output_raw"],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout:
                logger.info(
                    "Synthesized %d chars -> %d bytes audio",
                    len(text),
                    len(result.stdout),
                )
                return result.stdout
            return self._synthesize_placeholder(text)
        except FileNotFoundError:
            logger.info("piper not installed; using placeholder")
            return self._synthesize_placeholder(text)
        except Exception as exc:
            logger.warning("TTS failed: %s", exc)
            return self._synthesize_placeholder(text)

    def _synthesize_placeholder(self, text: str) -> bytes:
        return text.encode("utf-8")
