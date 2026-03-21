from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.protocols import (  # noqa: E402
    GraphProtocol,
    ImageInProtocol,
    VoiceInProtocol,
    VoiceOutProtocol,
)
from BoggersTheAI.multimodal.base import ImageInProtocol as MMImageIn  # noqa: E402
from BoggersTheAI.multimodal.base import VoiceInProtocol as MMVoiceIn  # noqa: E402
from BoggersTheAI.multimodal.base import VoiceOutProtocol as MMVoiceOut  # noqa: E402


class TestProtocolImports:
    def test_core_protocols_importable(self):
        assert VoiceInProtocol is not None
        assert VoiceOutProtocol is not None
        assert ImageInProtocol is not None
        assert GraphProtocol is not None

    def test_multimodal_reexports_match(self):
        assert MMVoiceIn is VoiceInProtocol
        assert MMVoiceOut is VoiceOutProtocol
        assert MMImageIn is ImageInProtocol

    def test_voice_in_protocol_has_transcribe(self):
        assert hasattr(VoiceInProtocol, "transcribe")

    def test_voice_out_protocol_has_synthesize(self):
        assert hasattr(VoiceOutProtocol, "synthesize")

    def test_image_in_protocol_has_caption(self):
        assert hasattr(ImageInProtocol, "caption")
