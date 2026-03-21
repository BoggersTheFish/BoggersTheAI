from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.multimodal.image_in import ImageInAdapter, ImageInConfig  # noqa: E402
from BoggersTheAI.multimodal.voice_in import VoiceInAdapter, VoiceInConfig  # noqa: E402
from BoggersTheAI.multimodal.voice_out import VoiceOutAdapter  # noqa: E402


class TestVoiceInAdapter:
    def test_empty_audio(self):
        adapter = VoiceInAdapter()
        assert adapter.transcribe(b"") == ""

    def test_placeholder_fallback(self):
        config = VoiceInConfig(backend="placeholder")
        adapter = VoiceInAdapter(config=config)
        result = adapter.transcribe(b"\x00" * 100)
        assert "voice-transcript" in result
        assert "100" in result

    def test_faster_whisper_fallback(self):
        adapter = VoiceInAdapter()
        result = adapter.transcribe(b"\x00" * 50)
        assert isinstance(result, str)
        assert len(result) > 0


class TestVoiceOutAdapter:
    def test_synthesize_returns_bytes(self):
        adapter = VoiceOutAdapter()
        result = adapter.synthesize("hello")
        assert isinstance(result, bytes)


class TestImageInAdapter:
    def test_caption_returns_string(self):
        adapter = ImageInAdapter(ImageInConfig(backend="placeholder"))
        result = adapter.caption(b"\x00" * 100)
        assert isinstance(result, str)
