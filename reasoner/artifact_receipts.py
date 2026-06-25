"""Reasoner receipt serialization through the unified .bogpk pipeline."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared.artifacts import ArtifactKind, artifact_trail_dir, serialize_json_payload


def write_reasoner_receipt(
    receipt: dict[str, Any],
    *,
    receipt_id: str | None = None,
    artifacts_root: str | Path = "artifacts",
) -> Path:
    """Persist a verifier-gated reasoner receipt as .bogpk."""
    trail = artifact_trail_dir("reasoner", artifacts_root)
    rid = receipt_id or receipt.get("receipt_id", f"receipt_{len(list(trail.glob('*.bogpk')))}")
    payload = {"layer": "reasoner", **receipt, "receipt_id": rid}
    return serialize_json_payload(payload, trail / rid, kind=ArtifactKind.REASONER_RECEIPT)