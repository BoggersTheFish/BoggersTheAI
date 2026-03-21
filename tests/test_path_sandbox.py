from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.path_sandbox import (  # noqa: E402
    validate_path,
)


def test_valid_path_resolves(tmp_path):
    result = validate_path("sub/file.txt", str(tmp_path))
    assert str(result).startswith(str(tmp_path.resolve()))
    assert result.name == "file.txt"


def test_dot_dot_traversal_raises(tmp_path):
    with pytest.raises(ValueError, match="traversal"):
        validate_path("../../etc/passwd", str(tmp_path))


def test_absolute_outside_raises(tmp_path):
    outside = Path(tmp_path).parent / "outside"
    with pytest.raises(ValueError, match="traversal"):
        validate_path(str(outside.resolve()), str(tmp_path))
