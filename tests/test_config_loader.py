from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.config_loader import (  # noqa: E402
    _deep_merge,
    apply_yaml_to_config,
    load_and_apply,
    load_yaml,
)


@dataclass
class _FakeConfig:
    graph_path: str = "./graph.json"
    insight_vault_path: str = "./vault"
    inference: Dict[str, object] = field(
        default_factory=dict,
    )
    throttle_seconds: int = 60


def _write_yaml(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_yaml_from_file(tmp_path):
    cfg_path = _write_yaml(tmp_path, "wave:\n  damping: 0.8\n")
    data = load_yaml(cfg_path)
    assert isinstance(data, dict)
    assert data["wave"]["damping"] == 0.8


def test_load_yaml_missing_file_returns_empty():
    data = load_yaml(Path("/nonexistent/config.yaml"))
    assert data == {}


def test_apply_yaml_populates_fields(tmp_path):
    cfg_path = _write_yaml(
        tmp_path,
        "graph_path: /tmp/g.json\nthrottle_seconds: 30\n",
    )
    data = load_yaml(cfg_path)
    config = _FakeConfig()
    apply_yaml_to_config(config, data)
    assert config.graph_path == "/tmp/g.json"
    assert config.throttle_seconds == 30


def test_deep_merge_nested():
    base = {"a": {"x": 1, "y": 2}, "b": 10}
    overlay = {"a": {"y": 99, "z": 3}, "c": 5}
    result = _deep_merge(base, overlay)
    assert result["a"]["x"] == 1
    assert result["a"]["y"] == 99
    assert result["a"]["z"] == 3
    assert result["b"] == 10
    assert result["c"] == 5


def test_load_and_apply_with_tmp_yaml(tmp_path):
    cfg_path = _write_yaml(
        tmp_path,
        (
            "graph_path: /data/g.json\n"
            "wave:\n  damping: 0.9\n"
            "runtime:\n  graph_path: /data/g.json\n"
            "os_loop:\n  enabled: true\n"
            "autonomous:\n  enabled: false\n"
            "embeddings:\n  model: test\n"
        ),
    )
    config = _FakeConfig()
    raw = load_and_apply(config, cfg_path)
    assert isinstance(raw, dict)
    assert config.graph_path == "/data/g.json"
