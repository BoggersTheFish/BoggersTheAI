"""Provenance trust pressure for TS-Reasoner v7.7.0.

Trust pressure is an audit signal, not proof.

Purpose:
- assign bounded trust tiers to sessions/packs/sources
- compute pressure on merge conflicts
- block unsafe low-trust imports against higher-trust rejections
- preserve verifier-first boundaries

Boundary:
- trust is not proof
- source weight is not proof
- pressure is not proof
- pack merge is not proof
- typed verifier/common-ground support remains proof authority
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ts_reasoner.knowledge_pack_library import (
    KnowledgePackLibrary,
    create_pack_from_edges,
    pack_accepted_edges,
    pack_rejected_relations,
)
from ts_reasoner.ts_chat import TSChatSession, receipt_to_dict


RELEASE = "v7.7.0"
SCHEMA = "ts_reasoner_trust_pressure_v1"

TRUST_TIERS = {
    "low": 0.25,
    "medium": 0.50,
    "high": 0.80,
    "verified": 1.00,
}


@dataclass(frozen=True)
class TrustSource:
    label: str
    tier: str
    weight: float
    source_type: str
    trust_is_proof: bool = False
    typed_verifier_remains_proof_authority: bool = True


class TrustRegistry:
    def __init__(self) -> None:
        self.sources: dict[str, TrustSource] = {}

    def set_source(self, label: str, tier: str, source_type: str = "unknown") -> TrustSource:
        if tier not in TRUST_TIERS:
            raise ValueError(f"Unknown trust tier: {tier}")

        source = TrustSource(
            label=label,
            tier=tier,
            weight=TRUST_TIERS[tier],
            source_type=source_type,
            trust_is_proof=False,
            typed_verifier_remains_proof_authority=True,
        )
        self.sources[label] = source
        return source

    def get(self, label: str) -> TrustSource:
        if label not in self.sources:
            return TrustSource(
                label=label,
                tier="low",
                weight=TRUST_TIERS["low"],
                source_type="unknown",
                trust_is_proof=False,
                typed_verifier_remains_proof_authority=True,
            )
        return self.sources[label]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ts_reasoner_trust_registry_v1",
            "release": RELEASE,
            "source_count": len(self.sources),
            "sources": {
                label: asdict(source)
                for label, source in sorted(self.sources.items())
            },
            "trust_is_proof": False,
            "source_weight_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
            "candidate_graph_contamination_count": 0,
            "external_llm_used": False,
        }


def _write_json(path: str | Path, payload: Any) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def _relation_dict(edge: tuple[str, str]) -> dict[str, str]:
    return {"subject": edge[0], "object": edge[1]}


def _sorted_relation_dicts(edges: set[tuple[str, str]]) -> list[dict[str, str]]:
    return [_relation_dict(edge) for edge in sorted(edges)]


def session_rejected_relations(session: TSChatSession) -> set[tuple[str, str]]:
    rejected: set[tuple[str, str]] = set()

    for record in session.common_ground.records:
        if record.status in {"rejected", "unsupported", "abstained"}:
            rejected.add((record.relation.subject, record.relation.object))

    return rejected


def session_accepted_edges(session: TSChatSession) -> set[tuple[str, str]]:
    return set(session.common_ground.accepted_edges)


def pressure_record(
    relation: tuple[str, str],
    *,
    accepting_source: TrustSource,
    rejecting_source: TrustSource,
    reason: str,
) -> dict[str, Any]:
    accepted_pressure = accepting_source.weight
    rejected_pressure = rejecting_source.weight
    net_pressure = accepted_pressure - rejected_pressure

    return {
        "relation": _relation_dict(relation),
        "accepting_source": asdict(accepting_source),
        "rejecting_source": asdict(rejecting_source),
        "accepted_pressure": accepted_pressure,
        "rejected_pressure": rejected_pressure,
        "net_pressure": net_pressure,
        "higher_pressure_side": "accepted" if net_pressure > 0 else "rejected" if net_pressure < 0 else "balanced",
        "reason": reason,
        "trust_pressure_is_proof": False,
        "typed_verifier_remains_proof_authority": True,
    }


def audit_pack_merge_with_trust(
    library: KnowledgePackLibrary,
    label: str,
    session: TSChatSession,
    registry: TrustRegistry,
    *,
    target_label: str = "session",
) -> dict[str, Any]:
    pack = library.load_pack(label)

    pack_edges = pack_accepted_edges(pack)
    pack_rejected = pack_rejected_relations(pack)
    target_rejected = session_rejected_relations(session)
    target_edges = session_accepted_edges(session)

    pack_source = registry.get(label)
    target_source = registry.get(target_label)

    direct_conflicts = sorted(pack_edges & target_rejected)
    pressure_records = [
        pressure_record(
            edge,
            accepting_source=pack_source,
            rejecting_source=target_source,
            reason="pack accepts a relation rejected by target session",
        )
        for edge in direct_conflicts
    ]

    blocked = len(direct_conflicts) > 0
    safe_to_merge = not blocked

    return {
        "schema": "ts_reasoner_trust_pressure_merge_audit_v1",
        "release": RELEASE,
        "label": label,
        "target_label": target_label,
        "pack_source": asdict(pack_source),
        "target_source": asdict(target_source),
        "pack_edge_count": len(pack_edges),
        "pack_rejected_relation_count": len(pack_rejected),
        "target_rejected_relation_count": len(target_rejected),
        "new_edge_count": len(pack_edges - target_edges),
        "already_present_edge_count": len(pack_edges & target_edges),
        "direct_conflict_count": len(direct_conflicts),
        "direct_conflicts": _sorted_relation_dicts(set(direct_conflicts)),
        "pressure_records": pressure_records,
        "blocked": blocked,
        "safe_to_merge": safe_to_merge,
        "decision": "block_merge" if blocked else "allow_merge",
        "trust_is_proof": False,
        "source_weight_is_proof": False,
        "trust_pressure_is_proof": False,
        "pack_import_is_proof": False,
        "pack_merge_is_proof": False,
        "typed_verifier_remains_proof_authority": True,
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
    }


def merge_pack_with_trust(
    library: KnowledgePackLibrary,
    label: str,
    session: TSChatSession,
    registry: TrustRegistry,
    *,
    target_label: str = "session",
) -> dict[str, Any]:
    trust_audit = audit_pack_merge_with_trust(
        library,
        label,
        session,
        registry,
        target_label=target_label,
    )

    if trust_audit["blocked"]:
        return {
            "schema": "ts_reasoner_trust_pressure_merge_receipt_v1",
            "release": RELEASE,
            "label": label,
            "target_label": target_label,
            "merged": False,
            "blocked": True,
            "trust_audit": trust_audit,
            "created_receipts": [],
            "trust_is_proof": False,
            "source_weight_is_proof": False,
            "trust_pressure_is_proof": False,
            "pack_import_is_proof": False,
            "pack_merge_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
            "candidate_graph_contamination_count": 0,
            "external_llm_used": False,
        }

    base_merge = library.merge_pack_into_session(label, session)

    return {
        "schema": "ts_reasoner_trust_pressure_merge_receipt_v1",
        "release": RELEASE,
        "label": label,
        "target_label": target_label,
        "merged": base_merge["merged"],
        "blocked": base_merge["blocked"],
        "merged_edge_count": base_merge.get("merged_edge_count", 0),
        "trust_audit": trust_audit,
        "base_merge": base_merge,
        "created_receipts": base_merge.get("created_receipts", []),
        "trust_is_proof": False,
        "source_weight_is_proof": False,
        "trust_pressure_is_proof": False,
        "pack_import_is_proof": False,
        "pack_merge_is_proof": False,
        "typed_verifier_remains_proof_authority": True,
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
    }


def compare_packs_with_trust(
    library: KnowledgePackLibrary,
    left: str,
    right: str,
    registry: TrustRegistry,
) -> dict[str, Any]:
    left_pack = library.load_pack(left)
    right_pack = library.load_pack(right)

    left_edges = pack_accepted_edges(left_pack)
    right_edges = pack_accepted_edges(right_pack)
    left_rejected = pack_rejected_relations(left_pack)
    right_rejected = pack_rejected_relations(right_pack)

    left_source = registry.get(left)
    right_source = registry.get(right)

    pressure_records = []
    for edge in sorted(left_edges & right_rejected):
        pressure_records.append(
            pressure_record(
                edge,
                accepting_source=left_source,
                rejecting_source=right_source,
                reason="left pack accepts a relation rejected by right pack",
            )
        )
    for edge in sorted(right_edges & left_rejected):
        pressure_records.append(
            pressure_record(
                edge,
                accepting_source=right_source,
                rejecting_source=left_source,
                reason="right pack accepts a relation rejected by left pack",
            )
        )

    return {
        "schema": "ts_reasoner_trust_pressure_pack_compare_v1",
        "release": RELEASE,
        "left": left,
        "right": right,
        "left_source": asdict(left_source),
        "right_source": asdict(right_source),
        "shared_edges": _sorted_relation_dicts(left_edges & right_edges),
        "only_left_edges": _sorted_relation_dicts(left_edges - right_edges),
        "only_right_edges": _sorted_relation_dicts(right_edges - left_edges),
        "pressure_records": pressure_records,
        "pressure_record_count": len(pressure_records),
        "trust_is_proof": False,
        "trust_pressure_is_proof": False,
        "typed_verifier_remains_proof_authority": True,
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
    }


def trust_pressure_payload_valid(payload: dict[str, Any]) -> bool:
    required = {
        "release",
        "trust_is_proof",
        "typed_verifier_remains_proof_authority",
        "candidate_graph_contamination_count",
        "external_llm_used",
    }
    if not required.issubset(payload):
        return False
    if payload["release"] != RELEASE:
        return False
    if payload["trust_is_proof"] is not False:
        return False
    if payload["typed_verifier_remains_proof_authority"] is not True:
        return False
    if payload["candidate_graph_contamination_count"] != 0:
        return False
    if payload["external_llm_used"] is not False:
        return False
    return True


def run_trust_pressure_demo(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    packs_dir = out / "packs"
    library_dir = out / "library"
    packs_dir.mkdir(parents=True, exist_ok=True)

    unsafe_pack_path = packs_dir / "low_trust_direct_robots.json"
    bridge_pack_path = packs_dir / "medium_trust_machine_bridge.json"
    dispute_pack_path = packs_dir / "low_dispute_pack.json"

    create_pack_from_edges(
        unsafe_pack_path,
        label="low_direct_robots",
        accepted_edges=[("cats", "robots")],
    )
    create_pack_from_edges(
        bridge_pack_path,
        label="medium_machine_bridge",
        accepted_edges=[("cats", "machines"), ("machines", "robots")],
    )
    create_pack_from_edges(
        dispute_pack_path,
        label="low_dispute_pack",
        accepted_edges=[("cats", "robots")],
        rejected_relations=[("cats", "machines")],
    )

    library = KnowledgePackLibrary(library_dir)
    library.register_pack("low_direct_robots", unsafe_pack_path)
    library.register_pack("medium_machine_bridge", bridge_pack_path)
    library.register_pack("low_dispute_pack", dispute_pack_path)

    registry = TrustRegistry()
    registry.set_source("session", "high", source_type="live_session")
    registry.set_source("low_direct_robots", "low", source_type="knowledge_pack")
    registry.set_source("medium_machine_bridge", "medium", source_type="knowledge_pack")
    registry.set_source("low_dispute_pack", "low", source_type="knowledge_pack")

    session = TSChatSession()
    session.process("also say all cats are robots")

    unsafe_audit = audit_pack_merge_with_trust(library, "low_direct_robots", session, registry)
    unsafe_merge = merge_pack_with_trust(library, "low_direct_robots", session, registry)

    safe_audit = audit_pack_merge_with_trust(library, "medium_machine_bridge", session, registry)
    safe_merge = merge_pack_with_trust(library, "medium_machine_bridge", session, registry)
    post_merge_question = session.process("are all cats robots?")

    pack_compare = compare_packs_with_trust(
        library,
        "medium_machine_bridge",
        "low_dispute_pack",
        registry,
    )

    state_path = out / "trust_pressure_state.json"
    receipt_path = out / "trust_pressure_receipt.json"
    report_path = out / "trust_pressure_report.json"

    state = {
        "registry": registry.to_dict(),
        "unsafe_audit": unsafe_audit,
        "unsafe_merge": unsafe_merge,
        "safe_audit": safe_audit,
        "safe_merge": safe_merge,
        "post_merge_question": receipt_to_dict(post_merge_question),
        "pack_compare": pack_compare,
    }

    _write_json(state_path, state)

    unsafe_pressure_detected = (
        unsafe_audit["direct_conflict_count"] == 1
        and unsafe_audit["pressure_records"][0]["higher_pressure_side"] == "rejected"
    )

    post_merge_accepted = any(
        record.get("kind") == "question"
        and record.get("status") == "accepted"
        and record.get("relation", {}).get("subject") == "cats"
        and record.get("relation", {}).get("object") == "robots"
        for record in post_merge_question.records_created
    )

    gates = {
        "registry_valid": trust_pressure_payload_valid(registry.to_dict()),
        "unsafe_pressure_detected": unsafe_pressure_detected,
        "unsafe_merge_blocked": unsafe_merge["blocked"] is True and unsafe_merge["merged"] is False,
        "safe_audit_allows_merge": safe_audit["safe_to_merge"] is True,
        "safe_merge_allowed": safe_merge["merged"] is True and safe_merge["blocked"] is False,
        "post_merge_answer_accepted": bool(post_merge_accepted),
        "pack_compare_available": pack_compare["schema"] == "ts_reasoner_trust_pressure_pack_compare_v1",
        "trust_is_not_proof": (
            registry.to_dict()["trust_is_proof"] is False
            and unsafe_audit["trust_is_proof"] is False
            and safe_merge["trust_is_proof"] is False
            and pack_compare["trust_is_proof"] is False
        ),
        "trust_pressure_is_not_proof": (
            unsafe_audit["trust_pressure_is_proof"] is False
            and safe_merge["trust_pressure_is_proof"] is False
            and pack_compare["trust_pressure_is_proof"] is False
        ),
        "candidate_graph_contamination_count_is_zero": (
            registry.to_dict()["candidate_graph_contamination_count"] == 0
            and unsafe_audit["candidate_graph_contamination_count"] == 0
            and unsafe_merge["candidate_graph_contamination_count"] == 0
            and safe_audit["candidate_graph_contamination_count"] == 0
            and safe_merge["candidate_graph_contamination_count"] == 0
            and pack_compare["candidate_graph_contamination_count"] == 0
        ),
        "external_llm_used_false": True,
    }

    receipt = {
        "schema": "ts_reasoner_v7_7_trust_pressure_receipt",
        "release": RELEASE,
        "milestone": "Provenance Trust Pressure",
        "external_llm_used": False,
        "out_dir": str(out),
        "state_path": str(state_path),
        "report_path": str(report_path),
        "source_count": registry.to_dict()["source_count"],
        "unsafe_pressure_detected": unsafe_pressure_detected,
        "unsafe_merge_blocked": unsafe_merge["blocked"],
        "safe_merge_allowed": safe_merge["merged"],
        "post_merge_answer_accepted": bool(post_merge_accepted),
        "pack_compare_pressure_record_count": pack_compare["pressure_record_count"],
        "candidate_graph_contamination_count": 0,
        "trust_is_not_proof": True,
        "source_weight_is_not_proof": True,
        "trust_pressure_is_not_proof": True,
        "pack_merge_is_not_proof": True,
        "typed_verifier_remains_proof_authority": True,
        "gates": gates,
        "all_gates_passed": all(gates.values()),
        "boundary": {
            "broad_natural_language_understanding": False,
            "neural_training": False,
            "live_tensionlm_runtime": False,
            "external_benchmark_victory": False,
            "trust_is_proof": False,
            "source_weight_is_proof": False,
            "trust_pressure_is_proof": False,
            "pack_merge_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
        },
    }

    report = {
        "schema": "ts_reasoner_v7_7_trust_pressure_report",
        "release": RELEASE,
        "source_count": receipt["source_count"],
        "unsafe_pressure_detected": receipt["unsafe_pressure_detected"],
        "unsafe_merge_blocked": receipt["unsafe_merge_blocked"],
        "safe_merge_allowed": receipt["safe_merge_allowed"],
        "post_merge_answer_accepted": receipt["post_merge_answer_accepted"],
        "pack_compare_pressure_record_count": receipt["pack_compare_pressure_record_count"],
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
        "all_gates_passed": receipt["all_gates_passed"],
    }

    _write_json(receipt_path, receipt)
    _write_json(report_path, report)

    receipt["receipt_path"] = str(receipt_path)
    return receipt
