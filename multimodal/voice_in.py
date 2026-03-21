from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger("boggers.multimodal.voice_in")


@dataclass(slots=True)
class VoiceInConfig:
    backend: str = "faster-whisper"
    model_size: str = "base"
    sample_rate_hz: int = 16000


class VoiceInAdapter:
    def __init__(self, config: VoiceInConfig | None = None) -> None:
        self.config = config or VoiceInConfig()
        self._model = None

    def transcribe(self, audio: bytes) -> str:
        if not audio:
            return ""
        if self.config.backend == "faster-whisper":
            return self._transcribe_faster_whisper(audio)
        return self._transcribe_placeholder(audio)

    def _transcribe_faster_whisper(self, audio: bytes) -> str:
        try:
            import tempfile

            from faster_whisper import WhisperModel

            if self._model is None:
                self._model = WhisperModel(self.config.model_size, compute_type="int8")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio)
                tmp_path = tmp.name
            try:
                segments, _ = self._model.transcribe(tmp_path)
                text = " ".join(seg.text for seg in segments).strip()
                logger.info("Transcribed %d bytes -> %d chars", len(audio), len(text))
                return text
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        except ImportError:
            logger.info("faster-whisper not installed; using placeholder")
            return self._transcribe_placeholder(audio)
        except Exception as exc:
            logger.warning("Transcription failed: %s", exc)
            return self._transcribe_placeholder(audio)

    def _transcribe_placeholder(self, audio: bytes) -> str:
        return (
            f"[voice-transcript backend={self.config.backend} "
            f"bytes={len(audio)} sample_rate={self.config.sample_rate_hz}]"
        )
