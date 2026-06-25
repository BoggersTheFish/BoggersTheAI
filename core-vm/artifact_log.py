"""BOGVM-0 state change logging through the unified .bogpk pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared.artifacts import ArtifactKind, artifact_trail_dir, serialize_json_payload


def log_vm_state_change(
    opcode: str,
    state_before: dict[str, Any],
    state_after: dict[str, Any],
    *,
    receipt_id: str | None = None,
    artifacts_root: str | Path = "artifacts",
) -> Path:
    """Record a deterministic VM state transition as a .bogpk artifact."""
    trail = artifact_trail_dir("core-vm", artifacts_root)
    rid = receipt_id or f"vm_{opcode}_{len(list(trail.glob('*.bogpk')))}"
    payload = {
        "layer": "core-vm",
        "opcode": opcode,
        "state_before": state_before,
        "state_after": state_after,
        "receipt_id": rid,
    }
    return serialize_json_payload(payload, trail / rid, kind=ArtifactKind.VM_STATE)