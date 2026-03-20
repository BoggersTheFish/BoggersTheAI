from __future__ import annotations

import tempfile
from pathlib import Path

from BoggersTheAI.entities.insight import InsightEngine


def test_write_insight_creates_file():
    engine = InsightEngine()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = engine.write_insight(
            content="Test insight content",
            topics=["test", "insight"],
            source_nodes=["node1"],
            vault_path=tmpdir,
        )
        assert Path(path).exists()


def test_extract_hypotheses_returns_list():
    engine = InsightEngine()
    result = engine.extract_hypotheses(
        "Some content about AI and graphs", ["ai", "graphs"]
    )
    assert isinstance(result, list)
