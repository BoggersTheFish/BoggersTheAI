"""TensionLM tension-field export through the unified .bogpk pipeline."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared.artifacts import (  # noqa: E402
    ArtifactKind,
    BogpkValidationError,
    artifact_trail_dir,
    deserialize_artifact,
    serialize_bytes,
    validate_container_metadata,
)

_TENSION_FIELD_METADATA_KEYS = frozenset(
    {
        "layer",
        "prompt_prefix",
        "shape",
        "dtype",
        "backend",
        "encoding",
    }
)


def _validate_tension_metadata(metadata: dict[str, Any]) -> None:
    unknown = set(metadata) - _TENSION_FIELD_METADATA_KEYS
    if unknown:
        raise BogpkValidationError(
            f"tension_field metadata contains unknown keys: {sorted(unknown)}"
        )
    if "shape" in metadata:
        shape = metadata["shape"]
        if not isinstance(shape, list) or not all(
            isinstance(v, int) and v > 0 for v in shape
        ):
            raise BogpkValidationError(
                "tension_field metadata.shape must be a list of positive ints"
            )
    if "layer" in metadata and not isinstance(metadata["layer"], int):
        raise BogpkValidationError("tension_field metadata.layer must be an int")


def export_tension_field(
    tension_matrix: np.ndarray,
    *,
    layer: int,
    prompt: str,
    artifacts_root: str | Path = "artifacts",
    dtype: str = "float32",
    backend: str = "cpu",
) -> Path:
    """Serialize a TensionLM tension field to .bogpk for reproducible trails."""
    if tension_matrix.ndim < 1:
        raise ValueError("tension_matrix must have at least one dimension")

    trail = artifact_trail_dir("inference", artifacts_root)
    safe = "".join(c if c.isalnum() else "_" for c in prompt[:32])
    name = f"tension_L{layer}_{safe}"
    metadata: dict[str, Any] = {
        "layer": layer,
        "prompt_prefix": prompt[:64],
        "shape": list(tension_matrix.shape),
        "dtype": dtype,
        "backend": backend,
    }
    _validate_tension_metadata(metadata)

    raw = tension_matrix.astype(np.float32).tobytes()
    path = serialize_bytes(
        raw,
        trail / name,
        kind=ArtifactKind.TENSION_FIELD,
        metadata=metadata,
        validate=True,
    )
    verify_exported_artifact(path, expected_shape=list(tension_matrix.shape))
    return path


def verify_exported_artifact(
    path: str | Path,
    *,
    expected_shape: list[int] | None = None,
) -> dict[str, Any]:
    """Round-trip verify a .bogpk export against schema and optional shape."""
    raw, container = deserialize_artifact(path, validate=True)
    validate_container_metadata(container)
    if container.get("artifact_kind") != ArtifactKind.TENSION_FIELD.value:
        raise BogpkValidationError(
            f"expected artifact_kind tension_field, got {container.get('artifact_kind')!r}"
        )
    meta = container.get("artifact_metadata", {})
    _validate_tension_metadata(meta)
    if expected_shape is not None and meta.get("shape") != expected_shape:
        raise BogpkValidationError(
            f"shape mismatch: metadata {meta.get('shape')} != expected {expected_shape}"
        )
    expected_bytes = int(np.prod(meta["shape"])) * 4
    if len(raw) != expected_bytes:
        raise BogpkValidationError(
            f"payload byte length {len(raw)} != expected {expected_bytes} for shape {meta['shape']}"
        )
    return container
