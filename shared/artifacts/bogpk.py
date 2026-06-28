"""Standard .bogpk binary container path for reproducible artifact trails.

Every TS-OS layer — BOGVM-0 state logs, TensionLM tension fields, reasoner
receipts — serializes through this module to maintain a perfect, compressed,
deterministic artifact chain.
"""

from __future__ import annotations

import json
import struct
import sys
from enum import Enum
from pathlib import Path
from typing import Any

_CORE_VM = Path(__file__).resolve().parents[2] / "core-vm"
if str(_CORE_VM) not in sys.path:
    sys.path.insert(0, str(_CORE_VM))

from bogvm.container import (  # noqa: E402
    build_bog_container,
    read_container,
    write_bogpk_container,
)
from bogvm.schema import SchemaError, validate_schema  # noqa: E402

ARTIFACT_EXTENSION = ".bogpk"
_SCHEMA_NAME = "bogpk-metadata.schema.json"


class ArtifactKind(str, Enum):
    """Typed artifact categories across TS-OS layers."""

    VM_STATE = "vm_state"
    TENSION_FIELD = "tension_field"
    REASONER_RECEIPT = "reasoner_receipt"
    WAVE_SNAPSHOT = "wave_snapshot"
    GENERIC = "generic"


class BogpkValidationError(Exception):
    """Raised when container metadata fails schema validation."""


def validate_container_metadata(container: dict[str, Any]) -> None:
    """Validate decoded or pre-write container against bogpk-metadata.schema.json."""
    try:
        validate_schema(container, _SCHEMA_NAME)
    except SchemaError as exc:
        raise BogpkValidationError(str(exc)) from exc


_ENVELOPE_STRUCT = struct.Struct(">I")


def _wrap_payload_envelope(
    data: bytes,
    *,
    kind: ArtifactKind,
    metadata: dict[str, Any] | None,
) -> bytes:
    """Prefix payload with a length-prefixed JSON envelope surviving BOGPK round-trip."""
    envelope = {
        "artifact_kind": kind.value,
        "artifact_metadata": metadata or {},
    }
    header = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _ENVELOPE_STRUCT.pack(len(header)) + header + data


def _unwrap_payload_envelope(raw: bytes) -> tuple[dict[str, Any], bytes]:
    if len(raw) < _ENVELOPE_STRUCT.size:
        return {}, raw
    header_len = _ENVELOPE_STRUCT.unpack(raw[: _ENVELOPE_STRUCT.size])[0]
    header_end = _ENVELOPE_STRUCT.size + header_len
    if header_end > len(raw):
        return {}, raw
    try:
        envelope = json.loads(raw[_ENVELOPE_STRUCT.size : header_end].decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}, raw
    if not isinstance(envelope, dict):
        return {}, raw
    return envelope, raw[header_end:]


def _ensure_bogpk_path(path: str | Path) -> Path:
    target = Path(path)
    if target.suffix != ARTIFACT_EXTENSION:
        target = target.with_suffix(ARTIFACT_EXTENSION)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def serialize_bytes(
    data: bytes,
    path: str | Path,
    *,
    kind: ArtifactKind = ArtifactKind.GENERIC,
    metadata: dict[str, Any] | None = None,
    chunk_size: int = 64,
    validate: bool = True,
) -> Path:
    """Pack raw bytes into a .bogpk container with envelope metadata in payload."""
    packed = _wrap_payload_envelope(data, kind=kind, metadata=metadata)
    container = build_bog_container(packed, chunk_size=chunk_size)
    if validate:
        validate_container_metadata(container)
    target = _ensure_bogpk_path(path)
    write_bogpk_container(container, str(target))
    return target


def serialize_json_payload(
    payload: dict[str, Any],
    path: str | Path,
    *,
    kind: ArtifactKind = ArtifactKind.GENERIC,
    validate: bool = True,
) -> Path:
    """Serialize a JSON-serializable dict through the .bogpk compression path."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return serialize_bytes(
        raw,
        path,
        kind=kind,
        metadata={"encoding": "json"},
        validate=validate,
    )


def serialize_artifact(
    payload: bytes | dict[str, Any],
    path: str | Path,
    *,
    kind: ArtifactKind = ArtifactKind.GENERIC,
    metadata: dict[str, Any] | None = None,
    validate: bool = True,
) -> Path:
    """Unified entry point: bytes or dict → .bogpk artifact."""
    if isinstance(payload, dict):
        return serialize_json_payload(payload, path, kind=kind, validate=validate)
    return serialize_bytes(
        payload, path, kind=kind, metadata=metadata, validate=validate
    )


def deserialize_artifact(
    path: str | Path, *, validate: bool = True
) -> tuple[bytes, dict[str, Any]]:
    """Read a .bogpk artifact and return (payload_bytes, container_metadata)."""
    container = read_container(str(path))
    if validate:
        validate_container_metadata(container)
    from bogvm.container import reconstruct_bog_container_bytes  # noqa: E402

    packed = reconstruct_bog_container_bytes(container)
    envelope, data = _unwrap_payload_envelope(packed)
    if envelope:
        container = {**container, **envelope}
    return data, container


def artifact_trail_dir(layer: str, base: str | Path = "artifacts") -> Path:
    """Return the canonical artifact directory for a TS-OS layer."""
    trail = Path(base) / layer
    trail.mkdir(parents=True, exist_ok=True)
    return trail
