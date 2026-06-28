"""
Phase 0 basic receipt support for waves and graph updates.
Provides simple hash-chained receipts (glass-box foundation).
See PHASE0_DETAIL_PLAN.md and FRONTIER_PLAN.md.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class WaveStepReceipt:
    step: int
    max_tension: float
    pruned: int
    emergent: int
    strongest_id: Optional[str]
    trace_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not d.get("trace_hash"):
            d["trace_hash"] = stable_hash(
                {k: v for k, v in d.items() if k != "trace_hash"}
            )
        return d


@dataclass
class GraphUpdateReceipt:
    before_summary: Dict[str, Any]
    after_summary: Dict[str, Any]
    deltas: List[Dict[str, Any]]
    receipt_hash: str = ""

    def finalize(self) -> Dict[str, Any]:
        d = asdict(self)
        d["receipt_hash"] = stable_hash(d)
        return d


def make_wave_receipt(
    step: int, result: Any, tensions: Dict[str, float] | None = None
) -> WaveStepReceipt:
    """Create a receipt from a RulesEngineCycleResult or similar."""
    max_t = max(tensions.values()) if tensions else 0.0
    return WaveStepReceipt(
        step=step,
        max_tension=round(max_t, 4),
        pruned=getattr(result, "pruned_edges", 0),
        emergent=len(getattr(result, "emergent_nodes", [])),
        strongest_id=getattr(result, "strongest_node_id", None),
    )
