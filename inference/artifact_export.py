"""TensionLM tension-field export through the unified .bogpk pipeline."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared.artifacts import ArtifactKind, artifact_trail_dir, serialize_bytes


def export_tension_field(
    tension_matrix: np.ndarray,
    *,
    layer: int,
    prompt: str,
    artifacts_root: str | Path = "artifacts",
) -> Path:
    """Serialize a TensionLM tension field to .bogpk for reproducible trails."""
    trail = artifact_trail_dir("inference", artifacts_root)
    safe = "".join(c if c.isalnum() else "_" for c in prompt[:32])
    name = f"tension_L{layer}_{safe}"
    raw = tension_matrix.astype(np.float32).tobytes()
    return serialize_bytes(
        raw,
        trail / name,
        kind=ArtifactKind.TENSION_FIELD,
        metadata={"layer": layer, "prompt_prefix": prompt[:64], "shape": list(tension_matrix.shape)},
    )