from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable


CENTRAL_BRAIN_SCHEMA = "ts_reasoner_central_brain_v1"
GENESIS_HASH = "0" * 64
MEMORY_STATUSES = frozenset({"accepted", "proposed", "rejected", "forgotten"})
POSITIVE_EDGE_TYPES = frozenset({
    "SUPPORTS",
    "MATERIALIZES",
    "VERIFIED_BY",
    "RECORDED_IN",
    "REPAIR_TARGETS",
    "HAS_BRANCH",
    "CONTAINS_ALTERNATIVE",
})
NEGATIVE_EDGE_TYPES = frozenset({"CONTRADICTS", "REJECTED_BY"})


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(payload: Any) -> str:
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_id(value: str) -> str:
    return "_".join(str(value).strip().lower().split())


@dataclass(frozen=True)
class BrainNode:
    node_id: str
    node_type: str
    status: str = "proposed"
    activation: float = 0.0
    tension: float = 0.0
    payload: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["payload"] = dict(self.payload or {})
        data["provenance"] = dict(self.provenance or {})
        return data


@dataclass(frozen=True)
class BrainEdge:
    edge_id: str
    source_id: str
    target_id: str
    edge_type: str
    status: str = "proposed"
    weight: float = 1.0
    payload: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["payload"] = dict(self.payload or {})
        data["provenance"] = dict(self.provenance or {})
        return data


@dataclass(frozen=True)
class BrainDecision:
    action: str
    candidate_node_id: str
    accepted: bool
    verifier_gate: dict[str, Any]
    state_delta: dict[str, Any]
    receipt: dict[str, Any]
    tension_telemetry: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayResult:
    mode: str
    boundary_receipt_hash: str
    boundary_sequence: int
    chain_valid: bool
    snapshot: dict[str, Any]
    delta_since_boundary: dict[str, Any]
    tension_telemetry: dict[str, Any]
    receipt: dict[str, Any] | None = None
    branch_world: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_brain_path(root: str | Path = ".") -> Path:
    return Path(root) / "artifacts" / "central_brain" / "brain.sqlite3"


class CentralBrainRuntime:
    """SQLite-backed verifier-first brain substrate.

    Candidates are always recorded as proposal nodes first. Accepted graph
    state can only change through verifier gates that produce hash-chained
    receipts.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()
        self._ensure_foundation_nodes()

    def close(self) -> None:
        self.conn.close()

    def _init_db(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                status TEXT NOT NULL,
                activation REAL NOT NULL,
                tension REAL NOT NULL,
                payload_json TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS edges (
                edge_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                status TEXT NOT NULL,
                weight REAL NOT NULL,
                payload_json TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_hash TEXT PRIMARY KEY,
                previous_hash TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                receipt_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_hash TEXT PRIMARY KEY,
                receipt_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def _ensure_foundation_nodes(self) -> None:
        foundation_nodes = self._foundation_nodes()
        for node in foundation_nodes:
            self._upsert_node(node)
        if self._head_hash() == GENESIS_HASH:
            receipt = self._write_receipt(
                "central_brain_bootstrap",
                {
                    "action": "bootstrap_foundation_nodes",
                    "foundation_node_ids": [node.node_id for node in foundation_nodes],
                    "foundation_nodes": [node.to_dict() for node in foundation_nodes],
                    "foundation_edge_types": [
                        "PROPOSES",
                        "VERIFIED_BY",
                        "MATERIALIZES",
                        "SUPPORTS",
                        "CONTRADICTS",
                        "RECORDED_IN",
                        "REPAIR_TARGETS",
                        "HAS_BRANCH",
                        "CONTAINS_ALTERNATIVE",
                    ],
                    "memory_statuses": sorted(MEMORY_STATUSES),
                    "candidate_graph_contamination_count": 0,
                    "proof_boundary": "typed_verifier_gate",
                },
            )
            self._upsert_node(
                BrainNode(
                    f"receipt:{receipt['receipt_hash'][:16]}",
                    "receipt",
                    "accepted",
                    0.6,
                    0.0,
                    {"receipt_hash": receipt["receipt_hash"], "receipt_type": receipt["receipt_type"]},
                )
            )

    def _foundation_nodes(self) -> tuple[BrainNode, ...]:
        return (
            BrainNode("brain:ts_reasoner_core", "reasoner_core", "accepted", 1.0, 0.0, {"loop": "propose_verify_receipt_accept_reject_repair_record"}),
            BrainNode("ledger:receipt_ledger", "receipt_ledger", "accepted", 0.9, 0.0, {"hash_chained": True}),
            BrainNode("scheduler:wave_scheduler", "wave_scheduler", "accepted", 0.7, 0.0, {"cycle": "activation_then_tension_relaxation"}),
            BrainNode("boundary:typed_verifier", "proof_boundary", "accepted", 1.0, 0.0, {"generated_text_is_not_proof": True}),
            BrainNode("repair:target_registry", "repair_registry", "accepted", 0.65, 0.0, {"purpose": "index_explicit_repair_targets"}),
            BrainNode("branch:world_registry", "branch_registry", "accepted", 0.6, 0.0, {"purpose": "index_temporary_branch_worlds"}),
        )

    def _head_hash(self) -> str:
        row = self.conn.execute("SELECT receipt_hash FROM receipts ORDER BY sequence DESC LIMIT 1").fetchone()
        return str(row["receipt_hash"]) if row else GENESIS_HASH

    def _next_sequence(self) -> int:
        row = self.conn.execute("SELECT COALESCE(MAX(sequence), -1) + 1 AS next_sequence FROM receipts").fetchone()
        return int(row["next_sequence"])

    def _write_receipt(self, receipt_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        previous_hash = self._head_hash()
        created_at = utc_now_iso()
        sequence = self._next_sequence()
        receipt = {
            "schema": CENTRAL_BRAIN_SCHEMA,
            "receipt_type": receipt_type,
            "sequence": sequence,
            "previous_hash": previous_hash,
            "created_at": created_at,
            **deepcopy(payload),
        }
        receipt_hash = stable_hash(receipt)
        receipt["receipt_hash"] = receipt_hash
        self.conn.execute(
            "INSERT INTO receipts(receipt_hash, previous_hash, sequence, receipt_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (receipt_hash, previous_hash, sequence, receipt_type, canonical_json(receipt), created_at),
        )
        self.conn.commit()
        return receipt

    def _upsert_node(self, node: BrainNode) -> None:
        if node.status not in MEMORY_STATUSES:
            raise ValueError(f"invalid node status: {node.status}")
        self.conn.execute(
            """
            INSERT INTO nodes(node_id, node_type, status, activation, tension, payload_json, provenance_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET
                node_type=excluded.node_type,
                status=excluded.status,
                activation=excluded.activation,
                tension=excluded.tension,
                payload_json=excluded.payload_json,
                provenance_json=excluded.provenance_json,
                updated_at=excluded.updated_at
            """,
            (
                node.node_id,
                node.node_type,
                node.status,
                float(node.activation),
                float(node.tension),
                canonical_json(node.payload or {}),
                canonical_json(node.provenance or {}),
                utc_now_iso(),
            ),
        )
        self.conn.commit()

    def _upsert_edge(self, edge: BrainEdge) -> None:
        if edge.status not in MEMORY_STATUSES:
            raise ValueError(f"invalid edge status: {edge.status}")
        self.conn.execute(
            """
            INSERT INTO edges(edge_id, source_id, target_id, edge_type, status, weight, payload_json, provenance_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(edge_id) DO UPDATE SET
                source_id=excluded.source_id,
                target_id=excluded.target_id,
                edge_type=excluded.edge_type,
                status=excluded.status,
                weight=excluded.weight,
                payload_json=excluded.payload_json,
                provenance_json=excluded.provenance_json,
                updated_at=excluded.updated_at
            """,
            (
                edge.edge_id,
                edge.source_id,
                edge.target_id,
                edge.edge_type,
                edge.status,
                float(edge.weight),
                canonical_json(edge.payload or {}),
                canonical_json(edge.provenance or {}),
                utc_now_iso(),
            ),
        )
        self.conn.commit()

    def _node_exists(self, node_id: str, *, accepted_only: bool = False) -> bool:
        if accepted_only:
            row = self.conn.execute("SELECT 1 FROM nodes WHERE node_id=? AND status='accepted'", (node_id,)).fetchone()
        else:
            row = self.conn.execute("SELECT 1 FROM nodes WHERE node_id=?", (node_id,)).fetchone()
        return row is not None

    def _get_node(self, node_id: str) -> BrainNode | None:
        row = self.conn.execute("SELECT * FROM nodes WHERE node_id=?", (node_id,)).fetchone()
        if row is None:
            return None
        return BrainNode(
            node_id=str(row["node_id"]),
            node_type=str(row["node_type"]),
            status=str(row["status"]),
            activation=float(row["activation"]),
            tension=float(row["tension"]),
            payload=json.loads(str(row["payload_json"])),
            provenance=json.loads(str(row["provenance_json"])),
        )

    def submit_candidate(self, candidate: dict[str, Any], *, proposer_id: str = "local") -> BrainDecision:
        candidate_payload = deepcopy(candidate)
        candidate_node_id = f"candidate:{stable_hash({'candidate': candidate_payload, 'proposer': proposer_id})[:16]}"
        proposer_node_id = f"proposer:{normalize_id(proposer_id)}"
        before_summary = self._state_summary()
        self._upsert_node(BrainNode(proposer_node_id, "proposer", "accepted", 0.55, 0.0, {"local_first": True}))
        self._upsert_node(
            BrainNode(
                candidate_node_id,
                "candidate",
                "proposed",
                0.5,
                0.2,
                candidate_payload,
                {"proposer_id": proposer_id},
            )
        )
        self._upsert_edge(
            BrainEdge(
                f"edge:{stable_hash({'s': proposer_node_id, 't': candidate_node_id, 'type': 'PROPOSES'})[:16]}",
                proposer_node_id,
                candidate_node_id,
                "PROPOSES",
                "accepted",
                1.0,
            )
        )

        gate = self._verify_candidate(candidate_payload)
        accepted = bool(gate["passed"])
        state_delta: dict[str, Any] = {}
        tension = 0.0 if accepted else 0.75
        repair_branch_delta: dict[str, Any] = {}

        if accepted:
            action = self._apply_candidate(candidate_payload, candidate_node_id)
            state_delta = action["state_delta"]
            repair_branch_delta = action.get("repair_branch_delta", {})
            self._set_node_status(candidate_node_id, "accepted", activation=0.9, tension=0.0)
            self._upsert_edge(
                BrainEdge(
                    f"edge:{stable_hash({'s': candidate_node_id, 't': 'boundary:typed_verifier', 'type': 'VERIFIED_BY'})[:16]}",
                    candidate_node_id,
                    "boundary:typed_verifier",
                    "VERIFIED_BY",
                    "accepted",
                    1.0,
                    {"gate": gate},
                )
            )
            action_name = action["action"]
        else:
            self._set_node_status(candidate_node_id, "rejected", activation=0.25, tension=tension)
            self._upsert_edge(
                BrainEdge(
                    f"edge:{stable_hash({'s': candidate_node_id, 't': 'boundary:typed_verifier', 'type': 'REJECTED_BY', 'reason': gate['reason']})[:16]}",
                    candidate_node_id,
                    "boundary:typed_verifier",
                    "REJECTED_BY",
                    "accepted",
                    1.0,
                    {"gate": gate},
                )
            )
            repair_branch_delta = self._create_repair_and_branch_for_rejection(
                candidate_node_id=candidate_node_id,
                candidate=candidate_payload,
                gate=gate,
                tension=tension,
            )
            action_name = "candidate_rejected"

        telemetry = self.tension_telemetry()
        merged_delta = self._merge_state_delta(state_delta, repair_branch_delta)
        after_summary = self._state_summary()
        receipt = self._write_receipt(
            "central_brain_decision",
            {
                "action": action_name,
                "candidate_node_id": candidate_node_id,
                "proposer_id": proposer_id,
                "candidate": candidate_payload,
                "verifier_gate": gate,
                "state_delta": merged_delta,
                "before_state": before_summary,
                "after_state": after_summary,
                "accepted": accepted,
                "candidate_graph_contamination_count": 0,
                "proof_boundary": "typed_verifier_gate",
                "generated_text_is_not_proof": True,
                "model_confidence_is_not_proof": True,
                "memory_statuses": sorted(MEMORY_STATUSES),
                "tension_telemetry": telemetry,
            },
        )
        self._upsert_node(
            BrainNode(
                f"receipt:{receipt['receipt_hash'][:16]}",
                "receipt",
                "accepted",
                0.6,
                0.0,
                {"receipt_hash": receipt["receipt_hash"], "receipt_type": receipt["receipt_type"]},
            )
        )
        self._upsert_edge(
            BrainEdge(
                f"edge:{stable_hash({'s': candidate_node_id, 't': receipt['receipt_hash'], 'type': 'RECORDED_IN'})[:16]}",
                candidate_node_id,
                f"receipt:{receipt['receipt_hash'][:16]}",
                "RECORDED_IN",
                "accepted",
                1.0,
            )
        )

        return BrainDecision(
            action=action_name,
            candidate_node_id=candidate_node_id,
            accepted=accepted,
            verifier_gate=gate,
            state_delta=merged_delta,
            receipt=receipt,
            tension_telemetry=telemetry,
        )

    def _set_node_status(self, node_id: str, status: str, *, activation: float | None = None, tension: float | None = None) -> None:
        node = self._get_node(node_id)
        if node is None:
            raise ValueError(f"unknown node: {node_id}")
        self._upsert_node(
            BrainNode(
                node.node_id,
                node.node_type,
                status,
                node.activation if activation is None else activation,
                node.tension if tension is None else tension,
                node.payload,
                node.provenance,
            )
        )

    def _state_summary(self) -> dict[str, Any]:
        rows = self.conn.execute("SELECT node_type, status, tension FROM nodes").fetchall()
        edge_count = int(self.conn.execute("SELECT COUNT(*) AS count FROM edges").fetchone()["count"])
        counts_by_type: dict[str, int] = {}
        counts_by_status: dict[str, int] = {}
        for row in rows:
            node_type = str(row["node_type"])
            status = str(row["status"])
            counts_by_type[node_type] = counts_by_type.get(node_type, 0) + 1
            counts_by_status[status] = counts_by_status.get(status, 0) + 1
        return {
            "ledger_head": self._head_hash(),
            "node_count": len(rows),
            "edge_count": edge_count,
            "node_type_counts": counts_by_type,
            "status_counts": counts_by_status,
            "total_tension": round(sum(float(row["tension"]) for row in rows), 6),
        }

    def _merge_state_delta(self, *deltas: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for delta in deltas:
            for key, value in delta.items():
                if isinstance(value, list):
                    merged.setdefault(key, []).extend(value)
                elif isinstance(value, dict):
                    merged.setdefault(key, {}).update(value)
                else:
                    merged[key] = value
        return merged

    def _edge_id(self, source_id: str, target_id: str, edge_type: str, payload: dict[str, Any] | None = None) -> str:
        return f"edge:{stable_hash({'s': source_id, 't': target_id, 'type': edge_type, 'payload': payload or {}})[:16]}"

    def _create_repair_target(
        self,
        *,
        source_node_id: str,
        reason: str,
        repair_type: str,
        tension: float,
        evidence: list[str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> BrainNode:
        repair_payload = {
            "reason": reason,
            "repair_type": repair_type,
            "source_node_id": source_node_id,
            "evidence": list(evidence or []),
            "suggested_next_gate": "collect_typed_support_or_branch_world_evidence",
            **dict(payload or {}),
        }
        repair_node = BrainNode(
            f"repair:{stable_hash(repair_payload)[:16]}",
            "repair_target",
            "accepted",
            0.68,
            round(min(1.0, max(0.35, tension)), 6),
            repair_payload,
            {"source_node_id": source_node_id},
        )
        self._upsert_node(repair_node)
        for source, target, edge_type in (
            (source_node_id, repair_node.node_id, "REPAIR_TARGETS"),
            ("repair:target_registry", repair_node.node_id, "SUPPORTS"),
        ):
            self._upsert_edge(
                BrainEdge(
                    self._edge_id(source, target, edge_type, {"reason": reason}),
                    source,
                    target,
                    edge_type,
                    "accepted",
                    1.0,
                    {"reason": reason},
                )
            )
        return repair_node

    def _create_branch_world(
        self,
        *,
        source_node_id: str,
        reason: str,
        alternatives: list[dict[str, Any]],
        tension: float,
    ) -> BrainNode:
        branch_payload = {
            "reason": reason,
            "source_node_id": source_node_id,
            "alternatives": deepcopy(alternatives),
            "auto_merge_allowed": False,
            "merge_requires_verifier_receipt": True,
        }
        branch_node = BrainNode(
            f"branch:{stable_hash(branch_payload)[:16]}",
            "branch_world",
            "accepted",
            0.62,
            round(min(1.0, max(0.25, tension * 0.7)), 6),
            branch_payload,
            {"source_node_id": source_node_id},
        )
        self._upsert_node(branch_node)
        for source, target, edge_type in (
            (source_node_id, branch_node.node_id, "HAS_BRANCH"),
            ("branch:world_registry", branch_node.node_id, "SUPPORTS"),
        ):
            self._upsert_edge(
                BrainEdge(
                    self._edge_id(source, target, edge_type, {"reason": reason}),
                    source,
                    target,
                    edge_type,
                    "accepted",
                    1.0,
                    {"reason": reason},
                )
            )
        for alternative in alternatives:
            alt_id = str(alternative.get("node_id", ""))
            if alt_id and self._node_exists(alt_id):
                self._upsert_edge(
                    BrainEdge(
                        self._edge_id(branch_node.node_id, alt_id, "CONTAINS_ALTERNATIVE", alternative),
                        branch_node.node_id,
                        alt_id,
                        "CONTAINS_ALTERNATIVE",
                        "accepted",
                        1.0,
                        alternative,
                    )
                )
        return branch_node

    def _create_repair_and_branch_for_rejection(
        self,
        *,
        candidate_node_id: str,
        candidate: dict[str, Any],
        gate: dict[str, Any],
        tension: float,
    ) -> dict[str, Any]:
        evidence = [str(item) for item in candidate.get("support", []) if str(item).strip()]
        repair = self._create_repair_target(
            source_node_id=candidate_node_id,
            reason=str(gate["reason"]),
            repair_type="missing_support_or_failed_gate",
            tension=tension * 0.8,
            evidence=evidence,
            payload={
                "candidate_action": candidate.get("action", ""),
                "candidate_payload_hash": stable_hash(candidate),
                "required_evidence": [
                    "typed_support_path",
                    "contradiction_evidence_if_applicable",
                    "verifier_rule_receipt",
                ],
            },
        )
        branch = self._create_branch_world(
            source_node_id=candidate_node_id,
            reason=f"high_tension_rejected_candidate:{gate['reason']}",
            tension=tension,
            alternatives=[
                {
                    "label": "main_world_keeps_candidate_rejected",
                    "node_id": candidate_node_id,
                    "status": "rejected",
                    "requires": "no_extra_action",
                },
                {
                    "label": "repair_world_collects_support",
                    "node_id": repair.node_id,
                    "status": "accepted_repair_target",
                    "requires": "typed_support_before_acceptance",
                },
            ],
        )
        return {
            "repair_targets_added": [repair.to_dict()],
            "branch_worlds_added": [branch.to_dict()],
        }

    def _create_repair_and_branch_for_contradiction(
        self,
        *,
        candidate_node_id: str,
        edge: BrainEdge,
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        evidence = [str(item) for item in candidate.get("support", []) if str(item).strip()]
        repair = self._create_repair_target(
            source_node_id=candidate_node_id,
            reason="accepted_contradicts_edge_requires_resolution",
            repair_type="contradiction_resolution",
            tension=max(0.65, float(edge.weight)),
            evidence=evidence,
            payload={
                "contradiction_edge_id": edge.edge_id,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "required_evidence": [
                    "which_side_has_typed_support",
                    "whether_branch_should_remain_isolated",
                    "merge_or_forget_receipt",
                ],
            },
        )
        branch = self._create_branch_world(
            source_node_id=candidate_node_id,
            reason="contradiction_requires_temporary_alternative_worlds",
            tension=max(0.65, float(edge.weight)),
            alternatives=[
                {
                    "label": "world_accepts_source_side",
                    "node_id": edge.source_id,
                    "status": "accepted",
                    "blocked_edge_id": edge.edge_id,
                },
                {
                    "label": "world_accepts_target_side",
                    "node_id": edge.target_id,
                    "status": "accepted",
                    "blocked_edge_id": edge.edge_id,
                },
                {
                    "label": "repair_world_resolves_contradiction",
                    "node_id": repair.node_id,
                    "status": "accepted_repair_target",
                    "blocked_edge_id": edge.edge_id,
                },
            ],
        )
        return {
            "repair_targets_added": [repair.to_dict()],
            "branch_worlds_added": [branch.to_dict()],
        }

    def _verify_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        action = str(candidate.get("action", ""))
        support = candidate.get("support", [])
        support_ok = isinstance(support, list) and bool(support) and all(isinstance(item, str) and item.strip() for item in support)
        gate = {
            "passed": False,
            "action": action,
            "reason": "unsupported_candidate",
            "typed_support_present": support_ok,
            "proof_boundary": "typed_verifier_support",
        }

        if action == "add_node":
            node_id = str(candidate.get("node_id", "")).strip()
            node_type = str(candidate.get("node_type", "")).strip()
            if not node_id or not node_type:
                gate["reason"] = "missing_node_identity"
            elif support_ok:
                gate.update({"passed": True, "reason": "typed_support_present"})
        elif action == "add_edge":
            source = str(candidate.get("source_id", "")).strip()
            target = str(candidate.get("target_id", "")).strip()
            edge_type = str(candidate.get("edge_type", "")).strip().upper()
            if not source or not target or not edge_type:
                gate["reason"] = "missing_edge_identity"
            elif not self._node_exists(source, accepted_only=True) or not self._node_exists(target, accepted_only=True):
                gate["reason"] = "edge_endpoint_not_accepted"
            elif edge_type in NEGATIVE_EDGE_TYPES and support_ok:
                gate.update({"passed": True, "reason": "typed_contradiction_support_present"})
            elif support_ok:
                gate.update({"passed": True, "reason": "typed_support_present"})
        elif action == "forget_node":
            node_id = str(candidate.get("node_id", "")).strip()
            if not self._node_exists(node_id, accepted_only=True):
                gate["reason"] = "forget_target_not_accepted"
            elif support_ok:
                gate.update({"passed": True, "reason": "typed_forgetting_support_present"})
        elif action == "self_evolution_proposal":
            if support_ok:
                gate.update({"passed": True, "reason": "self_evolution_proposal_supported"})
            else:
                gate["reason"] = "self_evolution_requires_tension_receipt_support"
        else:
            gate["reason"] = "unknown_candidate_action"

        return gate

    def _apply_candidate(self, candidate: dict[str, Any], candidate_node_id: str) -> dict[str, Any]:
        action = str(candidate["action"])
        if action == "add_node":
            node = BrainNode(
                str(candidate["node_id"]),
                str(candidate["node_type"]),
                "accepted",
                float(candidate.get("activation", 0.5)),
                float(candidate.get("tension", 0.0)),
                dict(candidate.get("payload", {})),
                {"candidate_node_id": candidate_node_id, "support": list(candidate.get("support", []))},
            )
            self._upsert_node(node)
            self._upsert_edge(
                BrainEdge(
                    f"edge:{stable_hash({'s': candidate_node_id, 't': node.node_id, 'type': 'MATERIALIZES'})[:16]}",
                    candidate_node_id,
                    node.node_id,
                    "MATERIALIZES",
                    "accepted",
                    1.0,
                )
            )
            return {"action": "node_accepted", "state_delta": {"nodes_added": [node.to_dict()]}}

        if action == "add_edge":
            edge = BrainEdge(
                str(candidate.get("edge_id") or f"edge:{stable_hash(candidate)[:16]}"),
                str(candidate["source_id"]),
                str(candidate["target_id"]),
                str(candidate["edge_type"]).upper(),
                "accepted",
                float(candidate.get("weight", 1.0)),
                dict(candidate.get("payload", {})),
                {"candidate_node_id": candidate_node_id, "support": list(candidate.get("support", []))},
            )
            self._upsert_edge(edge)
            repair_branch_delta: dict[str, Any] = {}
            action_name = "edge_accepted"
            if edge.edge_type == "CONTRADICTS":
                repair_branch_delta = self._create_repair_and_branch_for_contradiction(
                    candidate_node_id=candidate_node_id,
                    edge=edge,
                    candidate=candidate,
                )
                action_name = "contradiction_recorded"
            return {
                "action": action_name,
                "state_delta": {"edges_added": [edge.to_dict()]},
                "repair_branch_delta": repair_branch_delta,
            }

        if action == "forget_node":
            node_id = str(candidate["node_id"])
            self._set_node_status(node_id, "forgotten", activation=0.0, tension=0.0)
            return {"action": "node_forgotten", "state_delta": {"nodes_forgotten": [node_id]}}

        if action == "self_evolution_proposal":
            node_id = str(candidate.get("node_id") or f"evolution:{stable_hash(candidate)[:16]}")
            node = BrainNode(
                node_id,
                "self_evolution_proposal",
                "proposed",
                0.45,
                0.5,
                dict(candidate.get("payload", {})),
                {"candidate_node_id": candidate_node_id, "support": list(candidate.get("support", []))},
            )
            self._upsert_node(node)
            self._upsert_edge(
                BrainEdge(
                    f"edge:{stable_hash({'s': candidate_node_id, 't': node.node_id, 'type': 'MATERIALIZES'})[:16]}",
                    candidate_node_id,
                    node.node_id,
                    "MATERIALIZES",
                    "proposed",
                    1.0,
                )
            )
            return {"action": "self_evolution_proposed", "state_delta": {"self_evolution_proposals_added": [node.to_dict()]}}

        raise ValueError(f"unsupported action: {action}")

    def run_wave_cycle(self, *, cycle_id: str = "manual", relaxation: float = 0.85) -> dict[str, Any]:
        nodes = {node["node_id"]: node for node in self.graph_snapshot()["nodes"]}
        accepted_edges = [edge for edge in self.graph_snapshot()["edges"] if edge["status"] == "accepted"]
        next_activation = {node_id: float(node["activation"]) * 0.75 for node_id, node in nodes.items()}
        next_tension = {node_id: float(node["tension"]) * relaxation for node_id, node in nodes.items()}

        for edge in accepted_edges:
            source = edge["source_id"]
            target = edge["target_id"]
            if source not in nodes or target not in nodes:
                continue
            weight = float(edge["weight"])
            source_activation = float(nodes[source]["activation"])
            if edge["edge_type"] in NEGATIVE_EDGE_TYPES:
                next_tension[source] = min(1.0, next_tension[source] + 0.18 * weight)
                next_tension[target] = min(1.0, next_tension[target] + 0.18 * weight)
                next_activation[target] = max(0.0, next_activation[target] - 0.1 * source_activation * weight)
            else:
                next_activation[target] = min(1.0, next_activation[target] + 0.22 * source_activation * weight)
                next_tension[target] = max(0.0, next_tension[target] - 0.08 * weight)

        changed = []
        for node_id, node in nodes.items():
            updated = BrainNode(
                node_id,
                str(node["node_type"]),
                str(node["status"]),
                round(next_activation[node_id], 6),
                round(next_tension[node_id], 6),
                dict(node["payload"]),
                dict(node["provenance"]),
            )
            self._upsert_node(updated)
            changed.append({"node_id": node_id, "activation": updated.activation, "tension": updated.tension})

        telemetry = self.tension_telemetry()
        evolution = self._maybe_propose_self_evolution(telemetry, cycle_id)
        receipt = self._write_receipt(
            "wave_cycle",
            {
                "cycle_id": cycle_id,
                "relaxation": relaxation,
                "updated_nodes": changed,
                "tension_telemetry": telemetry,
                "self_evolution_triggered": evolution is not None,
                "self_evolution_candidate_node_id": evolution.candidate_node_id if evolution else "",
                "candidate_graph_contamination_count": 0,
                "accepted_without_verifier_support_count": 0,
            },
        )
        return {
            "cycle_id": cycle_id,
            "receipt": receipt,
            "tension_telemetry": telemetry,
            "self_evolution": evolution.to_dict() if evolution else None,
        }

    def _maybe_propose_self_evolution(self, telemetry: dict[str, Any], cycle_id: str) -> BrainDecision | None:
        hotspots = telemetry["hotspots"]
        if not hotspots:
            return None
        top = hotspots[0]
        if float(top["tension"]) < 0.6:
            return None
        related_repairs = self._linked_nodes(top["node_id"], "REPAIR_TARGETS")
        related_branches = self._linked_nodes(top["node_id"], "HAS_BRANCH")
        proposal = "add_or_adjust_repair_rule_for_persistent_tension_hotspot"
        evidence_requirement = "typed_support_path"
        if top["node_type"] == "candidate" and top["status"] == "rejected":
            proposal = "require_repair_target_and_branch_for_high_tension_rejected_candidate"
            evidence_requirement = "support_or_explicit_rejection_receipt"
        elif top["node_type"] == "repair_target":
            proposal = "prioritize_repair_target_until_tension_relaxes_or_branch_merges"
            evidence_requirement = "repair_resolution_receipt"
        return self.submit_candidate(
            {
                "action": "self_evolution_proposal",
                "node_id": f"evolution:repair_rule_for_{normalize_id(top['node_id'])}",
                "payload": {
                    "proposal": proposal,
                    "hotspot_node_id": top["node_id"],
                    "hotspot_node_type": top["node_type"],
                    "hotspot_status": top["status"],
                    "observed_tension": top["tension"],
                    "cycle_id": cycle_id,
                    "related_repair_targets": related_repairs,
                    "related_branch_worlds": related_branches,
                    "suggested_verifier_requirement": evidence_requirement,
                },
                "support": [f"tension_hotspot:{top['node_id']}:{top['tension']}"],
            },
            proposer_id="wave_scheduler",
        )

    def _linked_nodes(self, source_id: str, edge_type: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT target_id FROM edges WHERE source_id=? AND edge_type=? AND status='accepted' ORDER BY target_id",
            (source_id, edge_type),
        ).fetchall()
        return [str(row["target_id"]) for row in rows]

    def tension_telemetry(self) -> dict[str, Any]:
        rows = self.conn.execute(
            "SELECT node_id, node_type, status, activation, tension FROM nodes ORDER BY tension DESC, activation DESC, node_id"
        ).fetchall()
        hotspots = [
            {
                "node_id": str(row["node_id"]),
                "node_type": str(row["node_type"]),
                "status": str(row["status"]),
                "activation": round(float(row["activation"]), 6),
                "tension": round(float(row["tension"]), 6),
            }
            for row in rows
            if float(row["tension"]) > 0.0
        ]
        rejected = sum(1 for row in rows if str(row["status"]) == "rejected")
        proposed = sum(1 for row in rows if str(row["status"]) == "proposed")
        accepted = sum(1 for row in rows if str(row["status"]) == "accepted")
        forgotten = sum(1 for row in rows if str(row["status"]) == "forgotten")
        type_counts: dict[str, int] = {}
        for row in rows:
            node_type = str(row["node_type"])
            type_counts[node_type] = type_counts.get(node_type, 0) + 1
        total_tension = round(sum(float(row["tension"]) for row in rows), 6)
        strongest = [
            {
                "node_id": str(row["node_id"]),
                "node_type": str(row["node_type"]),
                "status": str(row["status"]),
                "activation": round(float(row["activation"]), 6),
            }
            for row in sorted(rows, key=lambda item: (-float(item["activation"]), str(item["node_id"])))[:5]
        ]
        return {
            "total_tension": total_tension,
            "hotspots": hotspots[:8],
            "status_counts": {
                "accepted": accepted,
                "proposed": proposed,
                "rejected": rejected,
                "forgotten": forgotten,
            },
            "node_type_counts": type_counts,
            "strongest_nodes": strongest,
        }

    def graph_snapshot(self) -> dict[str, Any]:
        nodes = [
            {
                "node_id": str(row["node_id"]),
                "node_type": str(row["node_type"]),
                "status": str(row["status"]),
                "activation": float(row["activation"]),
                "tension": float(row["tension"]),
                "payload": json.loads(str(row["payload_json"])),
                "provenance": json.loads(str(row["provenance_json"])),
            }
            for row in self.conn.execute("SELECT * FROM nodes ORDER BY node_id").fetchall()
        ]
        edges = [
            {
                "edge_id": str(row["edge_id"]),
                "source_id": str(row["source_id"]),
                "target_id": str(row["target_id"]),
                "edge_type": str(row["edge_type"]),
                "status": str(row["status"]),
                "weight": float(row["weight"]),
                "payload": json.loads(str(row["payload_json"])),
                "provenance": json.loads(str(row["provenance_json"])),
            }
            for row in self.conn.execute("SELECT * FROM edges ORDER BY edge_id").fetchall()
        ]
        return {
            "schema": CENTRAL_BRAIN_SCHEMA,
            "ledger_head": self._head_hash(),
            "nodes": nodes,
            "edges": edges,
        }

    def build_checkpoint(self) -> dict[str, Any]:
        snapshot = self.graph_snapshot()
        receipts = [
            json.loads(str(row["payload_json"]))
            for row in self.conn.execute("SELECT payload_json FROM receipts ORDER BY sequence").fetchall()
        ]
        checkpoint = {
            "schema": f"{CENTRAL_BRAIN_SCHEMA}_checkpoint",
            "snapshot": snapshot,
            "receipts": receipts,
            "ledger_head": self._head_hash(),
            "receipt_count": len(receipts),
        }
        checkpoint_hash = stable_hash(checkpoint)
        checkpoint["checkpoint_hash"] = checkpoint_hash
        self.conn.execute(
            "INSERT OR REPLACE INTO checkpoints(checkpoint_hash, receipt_hash, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (checkpoint_hash, self._head_hash(), canonical_json(checkpoint), utc_now_iso()),
        )
        self.conn.commit()
        return checkpoint

    @classmethod
    def restore_from_checkpoint(cls, checkpoint: dict[str, Any], path: str | Path = ":memory:") -> "CentralBrainRuntime":
        if checkpoint.get("schema") != f"{CENTRAL_BRAIN_SCHEMA}_checkpoint":
            raise ValueError("invalid central brain checkpoint schema")
        expected_hash = checkpoint.get("checkpoint_hash")
        unhashed = dict(checkpoint)
        unhashed.pop("checkpoint_hash", None)
        if expected_hash != stable_hash(unhashed):
            raise ValueError("invalid central brain checkpoint hash")
        runtime = cls(path)
        runtime.conn.execute("DELETE FROM edges")
        runtime.conn.execute("DELETE FROM nodes")
        runtime.conn.execute("DELETE FROM receipts")
        runtime.conn.execute("DELETE FROM checkpoints")
        runtime.conn.commit()

        for node in checkpoint["snapshot"]["nodes"]:
            runtime._upsert_node(
                BrainNode(
                    str(node["node_id"]),
                    str(node["node_type"]),
                    str(node["status"]),
                    float(node["activation"]),
                    float(node["tension"]),
                    dict(node["payload"]),
                    dict(node["provenance"]),
                )
            )
        for edge in checkpoint["snapshot"]["edges"]:
            runtime._upsert_edge(
                BrainEdge(
                    str(edge["edge_id"]),
                    str(edge["source_id"]),
                    str(edge["target_id"]),
                    str(edge["edge_type"]),
                    str(edge["status"]),
                    float(edge["weight"]),
                    dict(edge["payload"]),
                    dict(edge["provenance"]),
                )
            )
        previous = GENESIS_HASH
        for receipt in checkpoint["receipts"]:
            if receipt["previous_hash"] != previous:
                raise ValueError("invalid restored receipt chain")
            if receipt["receipt_hash"] != stable_hash({key: value for key, value in receipt.items() if key != "receipt_hash"}):
                raise ValueError("invalid restored receipt hash")
            runtime.conn.execute(
                "INSERT INTO receipts(receipt_hash, previous_hash, sequence, receipt_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    receipt["receipt_hash"],
                    receipt["previous_hash"],
                    int(receipt["sequence"]),
                    receipt["receipt_type"],
                    canonical_json(receipt),
                    receipt["created_at"],
                ),
            )
            previous = receipt["receipt_hash"]
        runtime.conn.commit()
        if runtime._head_hash() != checkpoint["ledger_head"]:
            raise ValueError("restored ledger head mismatch")
        return runtime

    def _ledger_receipts(self) -> list[dict[str, Any]]:
        return [
            json.loads(str(row["payload_json"]))
            for row in self.conn.execute("SELECT payload_json FROM receipts ORDER BY sequence").fetchall()
        ]

    def _verify_receipt_chain(self, receipts: list[dict[str, Any]]) -> bool:
        previous = GENESIS_HASH
        for index, receipt in enumerate(receipts):
            if int(receipt.get("sequence", -1)) != index:
                return False
            if receipt.get("previous_hash") != previous:
                return False
            receipt_hash = str(receipt.get("receipt_hash", ""))
            unhashed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
            if receipt_hash != stable_hash(unhashed):
                return False
            previous = receipt_hash
        return True

    def _select_boundary_receipts(
        self,
        receipts: list[dict[str, Any]],
        *,
        boundary_hash: str | None = None,
        boundary_sequence: int | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if not receipts:
            raise ValueError("receipt ledger is empty")
        if boundary_hash is None and boundary_sequence is None:
            return receipts, receipts[-1]
        for index, receipt in enumerate(receipts):
            if boundary_hash is not None and receipt["receipt_hash"] == boundary_hash:
                return receipts[: index + 1], receipt
            if boundary_sequence is not None and int(receipt["sequence"]) == int(boundary_sequence):
                return receipts[: index + 1], receipt
        raise ValueError("receipt boundary not found")

    def _replay_snapshot_from_receipts(self, receipts: list[dict[str, Any]]) -> dict[str, Any]:
        nodes: dict[str, dict[str, Any]] = {}
        edges: dict[str, dict[str, Any]] = {}
        ledger_head = GENESIS_HASH

        def put_node(node: BrainNode | dict[str, Any]) -> None:
            payload = node.to_dict() if isinstance(node, BrainNode) else deepcopy(node)
            nodes[str(payload["node_id"])] = payload

        def put_edge(edge: BrainEdge | dict[str, Any]) -> None:
            payload = edge.to_dict() if isinstance(edge, BrainEdge) else deepcopy(edge)
            edges[str(payload["edge_id"])] = payload

        def materialize_repair_links(repair_node: dict[str, Any]) -> None:
            source = str(repair_node.get("payload", {}).get("source_node_id") or repair_node.get("provenance", {}).get("source_node_id", ""))
            if source:
                put_edge(BrainEdge(
                    self._edge_id(source, repair_node["node_id"], "REPAIR_TARGETS", {"replay": True}),
                    source,
                    repair_node["node_id"],
                    "REPAIR_TARGETS",
                    "accepted",
                    1.0,
                    {"replayed": True},
                ))
            put_edge(BrainEdge(
                self._edge_id("repair:target_registry", repair_node["node_id"], "SUPPORTS", {"replay": True}),
                "repair:target_registry",
                repair_node["node_id"],
                "SUPPORTS",
                "accepted",
                1.0,
                {"replayed": True},
            ))

        def materialize_branch_links(branch_node: dict[str, Any]) -> None:
            source = str(branch_node.get("payload", {}).get("source_node_id") or branch_node.get("provenance", {}).get("source_node_id", ""))
            if source:
                put_edge(BrainEdge(
                    self._edge_id(source, branch_node["node_id"], "HAS_BRANCH", {"replay": True}),
                    source,
                    branch_node["node_id"],
                    "HAS_BRANCH",
                    "accepted",
                    1.0,
                    {"replayed": True},
                ))
            put_edge(BrainEdge(
                self._edge_id("branch:world_registry", branch_node["node_id"], "SUPPORTS", {"replay": True}),
                "branch:world_registry",
                branch_node["node_id"],
                "SUPPORTS",
                "accepted",
                1.0,
                {"replayed": True},
            ))
            for alternative in branch_node.get("payload", {}).get("alternatives", []):
                alt_id = str(alternative.get("node_id", ""))
                if alt_id and alt_id in nodes:
                    put_edge(BrainEdge(
                        self._edge_id(branch_node["node_id"], alt_id, "CONTAINS_ALTERNATIVE", alternative),
                        branch_node["node_id"],
                        alt_id,
                        "CONTAINS_ALTERNATIVE",
                        "accepted",
                        1.0,
                        alternative,
                    ))

        for receipt in receipts:
            receipt_type = str(receipt.get("receipt_type", ""))
            if receipt_type == "central_brain_bootstrap":
                for node_payload in receipt.get("foundation_nodes", []):
                    put_node(node_payload)
                if not receipt.get("foundation_nodes"):
                    for node in self._foundation_nodes():
                        put_node(node)

            if receipt_type == "central_brain_decision":
                candidate_node_id = str(receipt.get("candidate_node_id", ""))
                candidate = dict(receipt.get("candidate", {}))
                proposer_id = str(receipt.get("proposer_id", "replay_unknown"))
                proposer_node_id = f"proposer:{normalize_id(proposer_id)}"
                accepted = bool(receipt.get("accepted", False))
                gate = dict(receipt.get("verifier_gate", {}))
                put_node(BrainNode(proposer_node_id, "proposer", "accepted", 0.55, 0.0, {"replayed": True}))
                if candidate_node_id:
                    put_node(
                        BrainNode(
                            candidate_node_id,
                            "candidate",
                            "accepted" if accepted else "rejected",
                            0.9 if accepted else 0.25,
                            0.0 if accepted else 0.75,
                            candidate,
                            {"proposer_id": proposer_id, "replayed_from_receipt": receipt["receipt_hash"]},
                        )
                    )
                    put_edge(BrainEdge(
                        self._edge_id(proposer_node_id, candidate_node_id, "PROPOSES", {"receipt": receipt["receipt_hash"]}),
                        proposer_node_id,
                        candidate_node_id,
                        "PROPOSES",
                        "accepted",
                        1.0,
                        {"replayed_from_receipt": receipt["receipt_hash"]},
                    ))
                    proof_edge_type = "VERIFIED_BY" if accepted else "REJECTED_BY"
                    put_edge(BrainEdge(
                        self._edge_id(candidate_node_id, "boundary:typed_verifier", proof_edge_type, gate),
                        candidate_node_id,
                        "boundary:typed_verifier",
                        proof_edge_type,
                        "accepted",
                        1.0,
                        {"gate": gate, "replayed_from_receipt": receipt["receipt_hash"]},
                    ))

                delta = dict(receipt.get("state_delta", {}))
                for key in ("nodes_added", "repair_targets_added", "branch_worlds_added", "self_evolution_proposals_added"):
                    for node_payload in delta.get(key, []):
                        put_node(node_payload)
                        if key == "repair_targets_added":
                            materialize_repair_links(node_payload)
                        elif key == "branch_worlds_added":
                            materialize_branch_links(node_payload)
                for edge_payload in delta.get("edges_added", []):
                    put_edge(edge_payload)
                for node_id in delta.get("nodes_forgotten", []):
                    if node_id in nodes:
                        nodes[node_id]["status"] = "forgotten"
                        nodes[node_id]["activation"] = 0.0
                        nodes[node_id]["tension"] = 0.0

            if receipt_type == "wave_cycle":
                for update in receipt.get("updated_nodes", []):
                    node_id = str(update.get("node_id", ""))
                    if node_id in nodes:
                        nodes[node_id]["activation"] = float(update.get("activation", nodes[node_id]["activation"]))
                        nodes[node_id]["tension"] = float(update.get("tension", nodes[node_id]["tension"]))

            receipt_hash = str(receipt["receipt_hash"])
            put_node(
                BrainNode(
                    f"receipt:{receipt_hash[:16]}",
                    "receipt",
                    "accepted",
                    0.6,
                    0.0,
                    {"receipt_hash": receipt_hash, "receipt_type": receipt_type},
                )
            )
            candidate_node_id = str(receipt.get("candidate_node_id", ""))
            if candidate_node_id and candidate_node_id in nodes:
                put_edge(BrainEdge(
                    self._edge_id(candidate_node_id, f"receipt:{receipt_hash[:16]}", "RECORDED_IN", {"receipt": receipt_hash}),
                    candidate_node_id,
                    f"receipt:{receipt_hash[:16]}",
                    "RECORDED_IN",
                    "accepted",
                    1.0,
                    {"replayed_from_receipt": receipt_hash},
                ))
            ledger_head = receipt_hash

        return {
            "schema": CENTRAL_BRAIN_SCHEMA,
            "ledger_head": ledger_head,
            "nodes": [nodes[node_id] for node_id in sorted(nodes)],
            "edges": [edges[edge_id] for edge_id in sorted(edges)],
        }

    def _telemetry_for_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        nodes = list(snapshot.get("nodes", []))
        hotspots = [
            {
                "node_id": str(node["node_id"]),
                "node_type": str(node["node_type"]),
                "status": str(node["status"]),
                "activation": round(float(node["activation"]), 6),
                "tension": round(float(node["tension"]), 6),
            }
            for node in sorted(nodes, key=lambda item: (-float(item["tension"]), -float(item["activation"]), str(item["node_id"])))
            if float(node.get("tension", 0.0)) > 0.0
        ]
        status_counts: dict[str, int] = {"accepted": 0, "proposed": 0, "rejected": 0, "forgotten": 0}
        type_counts: dict[str, int] = {}
        for node in nodes:
            status = str(node["status"])
            status_counts[status] = status_counts.get(status, 0) + 1
            node_type = str(node["node_type"])
            type_counts[node_type] = type_counts.get(node_type, 0) + 1
        strongest = [
            {
                "node_id": str(node["node_id"]),
                "node_type": str(node["node_type"]),
                "status": str(node["status"]),
                "activation": round(float(node["activation"]), 6),
            }
            for node in sorted(nodes, key=lambda item: (-float(item["activation"]), str(item["node_id"])))[:5]
        ]
        return {
            "total_tension": round(sum(float(node.get("tension", 0.0)) for node in nodes), 6),
            "hotspots": hotspots[:8],
            "status_counts": status_counts,
            "node_type_counts": type_counts,
            "strongest_nodes": strongest,
        }

    def _delta_between_snapshots(self, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        before_nodes = {node["node_id"]: node for node in before.get("nodes", [])}
        after_nodes = {node["node_id"]: node for node in after.get("nodes", [])}
        before_edges = {edge["edge_id"]: edge for edge in before.get("edges", [])}
        after_edges = {edge["edge_id"]: edge for edge in after.get("edges", [])}
        changed_nodes = []
        for node_id in sorted(set(before_nodes) & set(after_nodes)):
            before_node = before_nodes[node_id]
            after_node = after_nodes[node_id]
            changes = {}
            for key in ("status", "activation", "tension", "payload", "provenance"):
                if before_node.get(key) != after_node.get(key):
                    changes[key] = {"before": before_node.get(key), "after": after_node.get(key)}
            if changes:
                changed_nodes.append({"node_id": node_id, "changes": changes})
        return {
            "nodes_added": sorted(set(after_nodes) - set(before_nodes)),
            "nodes_removed": sorted(set(before_nodes) - set(after_nodes)),
            "nodes_changed": changed_nodes,
            "edges_added": sorted(set(after_edges) - set(before_edges)),
            "edges_removed": sorted(set(before_edges) - set(after_edges)),
        }

    def inspect_receipt_boundary(
        self,
        *,
        boundary_hash: str | None = None,
        boundary_sequence: int | None = None,
        support: list[str] | None = None,
    ) -> ReplayResult:
        gate = self._verify_replay_request("inspect", support or [])
        if not gate["passed"]:
            raise ValueError(gate["reason"])
        receipts = self._ledger_receipts()
        chain_valid = self._verify_receipt_chain(receipts)
        if not chain_valid:
            raise ValueError("invalid receipt chain")
        boundary_receipts, boundary = self._select_boundary_receipts(
            receipts,
            boundary_hash=boundary_hash,
            boundary_sequence=boundary_sequence,
        )
        boundary_snapshot = self._replay_snapshot_from_receipts(boundary_receipts)
        head_snapshot = self._replay_snapshot_from_receipts(receipts)
        delta_since_boundary = self._delta_between_snapshots(boundary_snapshot, head_snapshot)
        telemetry = self._telemetry_for_snapshot(boundary_snapshot)
        receipt = self._write_receipt(
            "receipt_replay_inspect",
            {
                "action": "inspect_receipt_boundary",
                "verifier_gate": gate,
                "boundary_receipt_hash": boundary["receipt_hash"],
                "boundary_sequence": int(boundary["sequence"]),
                "chain_valid": chain_valid,
                "replayed_snapshot_hash": stable_hash(boundary_snapshot),
                "delta_since_boundary": delta_since_boundary,
                "tension_telemetry": telemetry,
                "graph_mutated": False,
                "accepted_state_overwritten": False,
                "candidate_graph_contamination_count": 0,
            },
        )
        return ReplayResult(
            mode="inspect",
            boundary_receipt_hash=boundary["receipt_hash"],
            boundary_sequence=int(boundary["sequence"]),
            chain_valid=chain_valid,
            snapshot=boundary_snapshot,
            delta_since_boundary=delta_since_boundary,
            tension_telemetry=telemetry,
            receipt=receipt,
        )

    def create_revert_branch_from_receipt(
        self,
        *,
        boundary_hash: str | None = None,
        boundary_sequence: int | None = None,
        support: list[str] | None = None,
    ) -> ReplayResult:
        gate = self._verify_replay_request("revert_branch", support or [])
        if not gate["passed"]:
            raise ValueError(gate["reason"])
        inspection = self.inspect_receipt_boundary(
            boundary_hash=boundary_hash,
            boundary_sequence=boundary_sequence,
            support=support,
        )
        before_summary = self._state_summary()
        session_node = BrainNode(
            f"replay:session:{stable_hash({'boundary': inspection.boundary_receipt_hash, 'head': self._head_hash()})[:16]}",
            "replay_session",
            "accepted",
            0.72,
            0.0,
            {
                "mode": "revert_branch",
                "boundary_receipt_hash": inspection.boundary_receipt_hash,
                "boundary_sequence": inspection.boundary_sequence,
                "snapshot_hash": stable_hash(inspection.snapshot),
                "chain_valid": inspection.chain_valid,
            },
            {"support": list(support or [])},
        )
        boundary_node = BrainNode(
            f"receipt_boundary:{inspection.boundary_receipt_hash[:16]}",
            "receipt_boundary",
            "accepted",
            0.7,
            0.0,
            {
                "receipt_hash": inspection.boundary_receipt_hash,
                "sequence": inspection.boundary_sequence,
                "ledger_head_at_replay": self._head_hash(),
            },
            {"replay_session_node_id": session_node.node_id},
        )
        revert_target = BrainNode(
            f"revert:target:{inspection.boundary_receipt_hash[:16]}",
            "revert_target",
            "accepted",
            0.68,
            min(1.0, inspection.tension_telemetry["total_tension"]),
            {
                "boundary_receipt_hash": inspection.boundary_receipt_hash,
                "snapshot_hash": stable_hash(inspection.snapshot),
                "delta_since_boundary": inspection.delta_since_boundary,
                "accepted_state_overwrite_allowed": False,
            },
            {"replay_session_node_id": session_node.node_id},
        )
        for node in (session_node, boundary_node, revert_target):
            self._upsert_node(node)
        self._upsert_edge(BrainEdge(self._edge_id(session_node.node_id, boundary_node.node_id, "SUPPORTS"), session_node.node_id, boundary_node.node_id, "SUPPORTS", "accepted", 1.0))
        self._upsert_edge(BrainEdge(self._edge_id(session_node.node_id, revert_target.node_id, "REPAIR_TARGETS"), session_node.node_id, revert_target.node_id, "REPAIR_TARGETS", "accepted", 1.0))
        branch = self._create_branch_world(
            source_node_id=session_node.node_id,
            reason="receipt_boundary_revert_branch",
            tension=max(0.25, min(1.0, inspection.tension_telemetry["total_tension"])),
            alternatives=[
                {
                    "label": "live_world_remains_current",
                    "node_id": "brain:ts_reasoner_core",
                    "status": "accepted",
                    "requires": "no_overwrite",
                },
                {
                    "label": "historical_receipt_boundary_world",
                    "node_id": revert_target.node_id,
                    "status": "accepted_revert_target",
                    "requires": "explicit_future_merge_receipt",
                },
            ],
        )
        after_summary = self._state_summary()
        telemetry = self.tension_telemetry()
        receipt = self._write_receipt(
            "receipt_replay_revert_branch",
            {
                "action": "create_revert_branch_from_receipt",
                "verifier_gate": gate,
                "boundary_receipt_hash": inspection.boundary_receipt_hash,
                "boundary_sequence": inspection.boundary_sequence,
                "replay_session_node": session_node.to_dict(),
                "receipt_boundary_node": boundary_node.to_dict(),
                "revert_target_node": revert_target.to_dict(),
                "branch_world": branch.to_dict(),
                "before_state": before_summary,
                "after_state": after_summary,
                "delta_since_boundary": inspection.delta_since_boundary,
                "accepted_state_overwritten": False,
                "candidate_graph_contamination_count": 0,
                "tension_telemetry": telemetry,
            },
        )
        return ReplayResult(
            mode="revert_branch",
            boundary_receipt_hash=inspection.boundary_receipt_hash,
            boundary_sequence=inspection.boundary_sequence,
            chain_valid=True,
            snapshot=inspection.snapshot,
            delta_since_boundary=inspection.delta_since_boundary,
            tension_telemetry=telemetry,
            receipt=receipt,
            branch_world=branch.to_dict(),
        )

    def _verify_replay_request(self, mode: str, support: list[str]) -> dict[str, Any]:
        support_ok = bool(support) and all(isinstance(item, str) and item.strip() for item in support)
        return {
            "passed": support_ok and mode in {"inspect", "revert_branch"},
            "reason": "typed_replay_support_present" if support_ok else "replay_requires_typed_support",
            "mode": mode,
            "typed_support_present": support_ok,
            "accepted_state_overwrite_allowed": False,
            "proof_boundary": "typed_verifier_support",
        }

    def dashboard(self) -> dict[str, Any]:
        snapshot = self.graph_snapshot()
        recent_receipts = [
            json.loads(str(row["payload_json"]))
            for row in self.conn.execute("SELECT payload_json FROM receipts ORDER BY sequence DESC LIMIT 8").fetchall()
        ]
        proof_boundaries = [
            node
            for node in snapshot["nodes"]
            if node["node_type"] == "proof_boundary" and node["status"] == "accepted"
        ]
        repair_targets = [
            node
            for node in snapshot["nodes"]
            if node["node_type"] == "repair_target" and node["status"] == "accepted"
        ]
        replay_sessions = [
            node
            for node in snapshot["nodes"]
            if node["node_type"] == "replay_session" and node["status"] == "accepted"
        ]
        cli_sessions = [
            node
            for node in snapshot["nodes"]
            if node["node_type"] == "cli_session" and node["status"] == "accepted"
        ]
        receipt_boundaries = [
            node
            for node in snapshot["nodes"]
            if node["node_type"] == "receipt_boundary" and node["status"] == "accepted"
        ]
        revert_targets = [
            node
            for node in snapshot["nodes"]
            if node["node_type"] == "revert_target" and node["status"] == "accepted"
        ]
        branch_worlds = self.branch_worlds()
        return {
            "schema": f"{CENTRAL_BRAIN_SCHEMA}_dashboard",
            "ledger_head": snapshot["ledger_head"],
            "node_count": len(snapshot["nodes"]),
            "edge_count": len(snapshot["edges"]),
            "status_counts": self.tension_telemetry()["status_counts"],
            "tension_telemetry": self.tension_telemetry(),
            "recent_receipts": recent_receipts,
            "proof_boundaries": proof_boundaries,
            "repair_targets": repair_targets,
            "branch_worlds": branch_worlds,
            "replay_sessions": replay_sessions,
            "cli_sessions": cli_sessions,
            "receipt_boundaries": receipt_boundaries,
            "revert_targets": revert_targets,
            "rendered_from_substrate": True,
            "candidate_graph_contamination_count": 0,
        }

    def branch_worlds(self) -> list[dict[str, Any]]:
        snapshot = self.graph_snapshot()
        nodes = {node["node_id"]: node for node in snapshot["nodes"]}
        branch_nodes = [
            node
            for node in snapshot["nodes"]
            if node["node_type"] == "branch_world" and node["status"] == "accepted"
        ]
        worlds = []
        for branch in branch_nodes:
            alternatives = []
            for edge in snapshot["edges"]:
                if edge["source_id"] == branch["node_id"] and edge["edge_type"] == "CONTAINS_ALTERNATIVE":
                    target = nodes.get(edge["target_id"])
                    alternatives.append({
                        "edge": edge,
                        "target": target,
                    })
            worlds.append({
                **branch,
                "alternatives": alternatives,
            })
        return worlds


def run_central_brain_wave(candidates: Iterable[dict[str, Any]], *, path: str | Path = ":memory:") -> dict[str, Any]:
    brain = CentralBrainRuntime(path)
    decisions = [brain.submit_candidate(candidate).to_dict() for candidate in candidates]
    wave = brain.run_wave_cycle(cycle_id="central_brain_wave")
    checkpoint = brain.build_checkpoint()
    dashboard = brain.dashboard()
    return {
        "schema": CENTRAL_BRAIN_SCHEMA,
        "decisions": decisions,
        "wave": wave,
        "checkpoint": checkpoint,
        "dashboard": dashboard,
        "all_gates_passed": all(decision["receipt"]["candidate_graph_contamination_count"] == 0 for decision in decisions)
        and dashboard["candidate_graph_contamination_count"] == 0,
    }
