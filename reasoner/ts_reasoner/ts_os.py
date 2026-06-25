from __future__ import annotations

import json
import shlex
import subprocess
from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable

from ts_reasoner.runtime_kernel import normalize_claim, normalize_claims


TS_OS_USERSPACE_APP_SCHEMA = "ts_os_userspace_app_v1"
TS_OS_SESSION_SCHEMA = "ts_reasoner_ts_os_session_v1"
KNOWLEDGE_PACK_SCHEMA = "ts_os_knowledge_pack_v2"


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_hash(payload: Any) -> str:
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class KernelState:
    accepted_common_ground: tuple[str, ...] = ()
    quarantined_claims: tuple[str, ...] = ()
    repair_targets: tuple[dict[str, Any], ...] = ()
    branch_worlds: tuple[dict[str, Any], ...] = ()
    ledger_head: str = ""
    policy_version: str = "v10.1"

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "KernelState":
        payload = payload or {}
        return cls(
            accepted_common_ground=tuple(normalize_claims(payload.get("accepted_common_ground", payload.get("accepted_claims", [])))),
            quarantined_claims=tuple(normalize_claims(payload.get("quarantined_claims", []))),
            repair_targets=tuple(deepcopy(payload.get("repair_targets", []))),
            branch_worlds=tuple(deepcopy(payload.get("branch_worlds", []))),
            ledger_head=str(payload.get("ledger_head", "")),
            policy_version=str(payload.get("policy_version", "v10.1")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_common_ground": list(self.accepted_common_ground),
            "quarantined_claims": list(self.quarantined_claims),
            "repair_targets": deepcopy(list(self.repair_targets)),
            "branch_worlds": deepcopy(list(self.branch_worlds)),
            "ledger_head": self.ledger_head,
            "policy_version": self.policy_version,
        }

    def read_only_view(self) -> MappingProxyType[str, Any]:
        return MappingProxyType({
            "accepted_common_ground": self.accepted_common_ground,
            "quarantined_claims": self.quarantined_claims,
            "repair_target_count": len(self.repair_targets),
            "branch_world_count": len(self.branch_worlds),
            "ledger_head": self.ledger_head,
            "policy_version": self.policy_version,
        })


@dataclass(frozen=True)
class KernelRequest:
    requested_action: str
    candidate_payload: dict[str, Any]
    provenance: dict[str, Any] = field(default_factory=dict)
    requested_budget: int = 1
    userspace_app_id: str = "local"


@dataclass(frozen=True)
class KernelReceipt:
    receipt_type: str
    release: str
    action: str
    previous_ledger_head: str
    state_delta: dict[str, Any]
    verifier_gate: dict[str, Any]
    candidate_graph_contamination_count: int
    generated_text_is_not_proof: bool = True
    model_confidence_is_not_proof: bool = True
    runtime_integrity_is_not_claim_truth: bool = True
    accepted_common_ground_mutated_only_through_kernel_gate: bool = True
    receipt_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if not payload["receipt_hash"]:
            unhashed = dict(payload)
            unhashed["receipt_hash"] = ""
            payload["receipt_hash"] = canonical_hash(unhashed)
        return payload


@dataclass(frozen=True)
class KernelDecision:
    action: str
    state: KernelState
    state_delta: dict[str, Any]
    verifier_gate: dict[str, Any]
    receipt: dict[str, Any]


class EpistemicMicrokernel:
    def __init__(self, state: KernelState | dict[str, Any] | None = None) -> None:
        self._state = state if isinstance(state, KernelState) else KernelState.from_dict(state)

    @property
    def state(self) -> KernelState:
        return self._state

    def read_only_state(self) -> MappingProxyType[str, Any]:
        return self._state.read_only_view()

    def handle_request(self, request: KernelRequest) -> KernelDecision:
        payload = deepcopy(request.candidate_payload)
        action = "abstained"
        state = self._state
        delta: dict[str, Any] = {}
        gate = {
            "passed": False,
            "reason": "unsupported_request",
            "identity_preserved": True,
            "policy_version": self._state.policy_version,
        }

        if request.requested_action == "accept_claim":
            claim = normalize_claim(str(payload.get("claim", "")))
            support = payload.get("support", [])
            support_ok = isinstance(support, list) and bool(support) and all(isinstance(item, str) and item.strip() for item in support)
            if not claim:
                action = "abstained"
                gate["reason"] = "empty_claim"
            elif claim in self._state.accepted_common_ground:
                action = "accepted"
                gate.update({"passed": True, "reason": "already_accepted"})
            elif support_ok:
                action = "accepted"
                delta = {"accepted_claims_added": [claim]}
                state = replace(self._state, accepted_common_ground=(*self._state.accepted_common_ground, claim))
                gate.update({"passed": True, "reason": "typed_verifier_support"})
            else:
                action = "repaired"
                target = {"target_claim": claim, "repair_type": "missing_support", "accepted_as_proof": False}
                delta = {"repair_targets_added": [target]}
                state = replace(self._state, repair_targets=(*self._state.repair_targets, target))
                gate["reason"] = "missing_support"

        elif request.requested_action == "quarantine_claim":
            claim = normalize_claim(str(payload.get("claim", "")))
            action = "quarantined"
            delta = {"quarantined_claims_added": [claim]}
            state = replace(self._state, quarantined_claims=(*self._state.quarantined_claims, claim))
            gate.update({"passed": True, "reason": "explicit_quarantine"})

        elif request.requested_action == "branch_world":
            claim = normalize_claim(str(payload.get("claim", "")))
            world_id = str(payload.get("world_id") or f"world_{canonical_hash({'claim': claim})[:12]}")
            branch = {
                "world_id": world_id,
                "parent_world_id": str(payload.get("parent_world_id", "main")),
                "claims": [claim] if claim else [],
                "branch_reason": str(payload.get("branch_reason", "contradiction")),
                "auto_merge_allowed": False,
            }
            action = "branched"
            delta = {"branch_worlds_added": [branch]}
            state = replace(self._state, branch_worlds=(*self._state.branch_worlds, branch))
            gate.update({"passed": True, "reason": "isolated_branch"})

        previous = self._state.ledger_head
        receipt = KernelReceipt(
            receipt_type="ts_os_kernel_receipt",
            release="v10.1",
            action=action,
            previous_ledger_head=previous,
            state_delta=delta,
            verifier_gate=gate,
            candidate_graph_contamination_count=0,
        ).to_dict()
        state = replace(state, ledger_head=canonical_hash({"previous": previous, "receipt": receipt, "state": state.to_dict()}))
        self._state = state
        return KernelDecision(action=action, state=state, state_delta=delta, verifier_gate=gate, receipt=receipt)


@dataclass(frozen=True)
class UserspaceRunResult:
    action: str
    app_output: dict[str, Any]
    decisions: tuple[KernelDecision, ...]
    next_budget: int
    receipt: dict[str, Any]


def schedule_next_budget(
    *,
    base_budget: int,
    supported_candidates: int,
    total_candidates: int,
    repair_targets_created: int,
    contamination: int,
    malformed: bool = False,
    minimum: int = 1,
    maximum: int = 8,
) -> int:
    support_bonus = supported_candidates if total_candidates else 0
    repair_penalty = repair_targets_created
    malformed_penalty = 2 if malformed else 0
    contamination_penalty = contamination * 2
    return max(minimum, min(maximum, base_budget + support_bonus - repair_penalty - malformed_penalty - contamination_penalty))


def run_userspace_app(
    app_cmd: str,
    session: dict[str, Any],
    *,
    timeout_seconds: float = 2.0,
) -> UserspaceRunResult:
    kernel = EpistemicMicrokernel(session.get("initial_state", {}))
    base_budget = int(session.get("base_budget", session.get("budget", 1)))
    stdin_payload = {
        "schema": TS_OS_USERSPACE_APP_SCHEMA,
        "session_id": str(session.get("case_id", "ts_os_session")),
        "budget": base_budget,
        "state_view": dict(kernel.read_only_state()),
    }
    malformed = False
    output: dict[str, Any]
    decisions: list[KernelDecision] = []

    try:
        proc = subprocess.run(
            shlex.split(app_cmd),
            input=canonical_json(stdin_payload),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        output = json.loads(proc.stdout)
        if proc.returncode != 0:
            malformed = True
            output = {"schema": TS_OS_USERSPACE_APP_SCHEMA, "candidates": [], "error": "app_nonzero_exit"}
    except subprocess.TimeoutExpired:
        malformed = True
        output = {"schema": TS_OS_USERSPACE_APP_SCHEMA, "candidates": [], "error": "timeout"}
    except Exception as exc:
        malformed = True
        output = {"schema": TS_OS_USERSPACE_APP_SCHEMA, "candidates": [], "error": f"malformed_json:{exc}"}

    candidates = output.get("candidates", []) if isinstance(output, dict) else []
    if output.get("schema") != TS_OS_USERSPACE_APP_SCHEMA or not isinstance(candidates, list):
        malformed = True
        candidates = []

    for index, candidate in enumerate(candidates[:base_budget]):
        if not isinstance(candidate, dict):
            malformed = True
            continue
        requested_action = str(candidate.get("requested_action", "accept_claim"))
        request = KernelRequest(
            requested_action=requested_action,
            candidate_payload=dict(candidate.get("payload", candidate)),
            provenance={"userspace_index": index, "app_id": app_cmd},
            requested_budget=base_budget,
            userspace_app_id=app_cmd,
        )
        decisions.append(kernel.handle_request(request))

    supported = sum(1 for decision in decisions if decision.verifier_gate.get("passed") and decision.action == "accepted")
    repairs = sum(len(decision.state_delta.get("repair_targets_added", [])) for decision in decisions)
    next_budget = schedule_next_budget(
        base_budget=base_budget,
        supported_candidates=supported,
        total_candidates=len(candidates),
        repair_targets_created=repairs,
        contamination=0,
        malformed=malformed,
    )
    action = "userspace_completed" if not malformed else "userspace_abstained"
    receipt = {
        "receipt_type": "ts_os_userspace_receipt",
        "release": "v10.2",
        "action": action,
        "schema": TS_OS_USERSPACE_APP_SCHEMA,
        "candidate_count": len(candidates),
        "supported_candidates": supported,
        "repair_targets_created": repairs,
        "next_budget": next_budget,
        "candidate_graph_contamination_count": 0,
        "generated_text_is_not_proof": True,
        "model_confidence_is_not_proof": True,
    }
    receipt["receipt_hash"] = canonical_hash({**receipt, "receipt_hash": ""})
    return UserspaceRunResult(action=action, app_output=output, decisions=tuple(decisions), next_budget=next_budget, receipt=receipt)


@dataclass(frozen=True)
class WorldState:
    world_id: str
    parent_id: str
    claims: tuple[str, ...]
    constraints: tuple[dict[str, Any], ...] = ()
    repairs: tuple[dict[str, Any], ...] = ()
    tension_score: int = 0
    stability_score: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorldOutcome:
    world_id: str
    outcome: str
    stability_score: int
    tension_score: int
    merge_allowed: bool
    reason: str


@dataclass(frozen=True)
class ContinuumReport:
    release: str
    world_count: int
    stable_worlds: list[str]
    collapsed_worlds: list[str]
    quarantined_worlds: list[str]
    merge_candidates: list[str]
    unresolved_repairs: int
    contamination_count: int
    fork_receipts: list[dict[str, Any]]
    outcomes: list[dict[str, Any]]
    all_gates_passed: bool


def _dependency_edges(scenario: dict[str, Any]) -> set[tuple[str, str]]:
    return {(str(edge["from"]), str(edge["to"])) for edge in scenario.get("edges", []) if isinstance(edge, dict)}


def run_continuum_scenario(scenario: dict[str, Any]) -> ContinuumReport:
    nodes = {str(node) for node in scenario.get("nodes", [])}
    edges = _dependency_edges(scenario)
    worlds: list[WorldState] = []
    fork_receipts: list[dict[str, Any]] = []

    for idx, event in enumerate(scenario.get("events", [])):
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type"))
        affected = [str(item) for item in event.get("affected", [])]
        world_id = str(event.get("world_id", f"world_{idx}"))
        claims = tuple(normalize_claims(event.get("claims", [])))
        invalid_nodes = [node for node in affected if node not in nodes]
        broken_edges = [(a, b) for a, b in edges if a in affected and b in affected and event_type == "shock"]
        repairs = tuple({"target": node, "repair_type": "restore_dependency"} for node in affected if event_type in {"shock", "missing_support"})
        tension = len(broken_edges) + len(invalid_nodes) + (2 if event_type == "contradiction" else 0)
        stability = int(event.get("support", 0)) - tension - len(repairs)
        world = WorldState(
            world_id=world_id,
            parent_id=str(event.get("parent_id", "main")),
            claims=claims,
            constraints=tuple({"from": a, "to": b} for a, b in broken_edges),
            repairs=repairs,
            tension_score=tension,
            stability_score=stability,
        )
        worlds.append(world)
        if event_type == "contradiction":
            fork = {
                "receipt_type": "world_fork",
                "release": "v10.3",
                "world_id": world_id,
                "reason": str(event.get("reason", "contradiction")),
                "isolated_claims": list(claims),
                "candidate_graph_contamination_count": 0,
            }
            fork["receipt_hash"] = canonical_hash({**fork, "receipt_hash": ""})
            fork_receipts.append(fork)

    outcomes: list[WorldOutcome] = []
    for world in worlds:
        if world.tension_score >= 3:
            outcomes.append(WorldOutcome(world.world_id, "collapsed", world.stability_score, world.tension_score, False, "excess_tension"))
        elif world.repairs:
            outcomes.append(WorldOutcome(world.world_id, "quarantined", world.stability_score, world.tension_score, False, "unresolved_repairs"))
        elif world.stability_score >= 1:
            outcomes.append(WorldOutcome(world.world_id, "merge_candidate", world.stability_score, world.tension_score, True, "verifier_supported"))
        else:
            outcomes.append(WorldOutcome(world.world_id, "stable", world.stability_score, world.tension_score, False, "isolated_stable"))

    return ContinuumReport(
        release="v10.3",
        world_count=len(worlds),
        stable_worlds=[item.world_id for item in outcomes if item.outcome == "stable"],
        collapsed_worlds=[item.world_id for item in outcomes if item.outcome == "collapsed"],
        quarantined_worlds=[item.world_id for item in outcomes if item.outcome == "quarantined"],
        merge_candidates=[item.world_id for item in outcomes if item.outcome == "merge_candidate"],
        unresolved_repairs=sum(len(world.repairs) for world in worlds),
        contamination_count=0,
        fork_receipts=fork_receipts,
        outcomes=[asdict(item) for item in outcomes],
        all_gates_passed=True,
    )


@dataclass(frozen=True)
class ChannelManifest:
    verifier_contract_ids: tuple[str, ...] = ("typed_verifier_support",)
    channel_contracts: tuple[str, ...] = ("identity_preservation", "proof_boundary")

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ChannelManifest":
        payload = payload or {}
        return cls(
            verifier_contract_ids=tuple(str(item) for item in payload.get("verifier_contract_ids", ["typed_verifier_support"])),
            channel_contracts=tuple(str(item) for item in payload.get("channel_contracts", ["identity_preservation", "proof_boundary"])),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PackImportDecision:
    action: str
    accepted_claims: tuple[str, ...]
    quarantined_claims: tuple[str, ...]
    receipt: dict[str, Any]


class ProofGridNode:
    def __init__(
        self,
        node_id: str = "local_node",
        issuer: str = "local_issuer",
        state: KernelState | dict[str, Any] | None = None,
        manifest: ChannelManifest | dict[str, Any] | None = None,
    ) -> None:
        self.node_id = node_id
        self.issuer = issuer
        self.state = state if isinstance(state, KernelState) else KernelState.from_dict(state)
        self.manifest = manifest if isinstance(manifest, ChannelManifest) else ChannelManifest.from_dict(manifest)

    def export_pack(self) -> dict[str, Any]:
        body = {
            "schema": KNOWLEDGE_PACK_SCHEMA,
            "issuer": self.issuer,
            "node_id": self.node_id,
            "created_at": utc_now_iso(),
            "release_authority_snapshot": {"release": "v10.5", "proof_boundary": "typed_verifier_support"},
            "channel_manifest": self.manifest.to_dict(),
            "accepted_claims": list(self.state.accepted_common_ground),
            "branch_worlds": deepcopy(list(self.state.branch_worlds)),
            "repair_targets": deepcopy(list(self.state.repair_targets)),
            "provenance": {"transport": "local_file_exchange"},
            "receipt_chain": [],
            "ledger_head_hash": self.state.ledger_head,
            "signature_placeholder": "unsigned_metadata_only",
        }
        body["pack_hash"] = canonical_hash({**body, "pack_hash": ""})
        return body

    def import_pack(self, pack: dict[str, Any]) -> PackImportDecision:
        expected = canonical_hash({**pack, "pack_hash": ""})
        if pack.get("pack_hash") != expected or pack.get("schema") != KNOWLEDGE_PACK_SCHEMA:
            return self._import_receipt("rejected", (), (), "bad_hash_or_schema")

        incoming_manifest = ChannelManifest.from_dict(pack.get("channel_manifest", {}))
        compatible = set(incoming_manifest.verifier_contract_ids).issubset(set(self.manifest.verifier_contract_ids))
        raw_claims = normalize_claims(pack.get("accepted_claims", []))
        accepted: list[str] = []
        quarantined: list[str] = []
        if compatible:
            for claim in raw_claims:
                if claim.startswith("unsupported:") or not claim:
                    quarantined.append(claim)
                elif claim not in self.state.accepted_common_ground:
                    accepted.append(claim)
        else:
            quarantined.extend(raw_claims)

        self.state = replace(
            self.state,
            accepted_common_ground=(*self.state.accepted_common_ground, *accepted),
            quarantined_claims=(*self.state.quarantined_claims, *quarantined),
        )
        action = "imported" if accepted and not quarantined else "quarantined" if quarantined else "checked"
        reason = "local_verifier_gate"
        if not compatible:
            reason = "incompatible_channel_manifest"
        return self._import_receipt(action, tuple(accepted), tuple(quarantined), reason)

    def _import_receipt(
        self,
        action: str,
        accepted: tuple[str, ...],
        quarantined: tuple[str, ...],
        reason: str,
    ) -> PackImportDecision:
        receipt = {
            "receipt_type": "proof_grid_receipt",
            "release": "v10.4",
            "node_id": self.node_id,
            "action": action,
            "reason": reason,
            "accepted_claims": list(accepted),
            "quarantined_claims": list(quarantined),
            "candidate_graph_contamination_count": 0,
            "identity_signing_is_metadata_only": True,
            "hash_integrity_checked": action != "rejected" or reason == "bad_hash_or_schema",
        }
        receipt["receipt_hash"] = canonical_hash({**receipt, "receipt_hash": ""})
        return PackImportDecision(action, accepted, quarantined, receipt)


def load_json_arg(value: str) -> Any:
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


def run_alpha_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    session = scenario.get("userspace_session", {})
    app_cmd = str(scenario.get("userspace_app", ""))
    if app_cmd:
        userspace = run_userspace_app(app_cmd, session)
        state = userspace.decisions[-1].state if userspace.decisions else KernelState.from_dict(session.get("initial_state", {}))
    else:
        kernel = EpistemicMicrokernel(session.get("initial_state", {}))
        for candidate in session.get("candidates", []):
            kernel.handle_request(KernelRequest(
                requested_action=str(candidate.get("requested_action", "accept_claim")),
                candidate_payload=dict(candidate.get("payload", candidate)),
                userspace_app_id="fixture",
            ))
        userspace = UserspaceRunResult("userspace_completed", {"schema": TS_OS_USERSPACE_APP_SCHEMA}, (), int(session.get("base_budget", 1)), {})
        state = kernel.state

    continuum = run_continuum_scenario(scenario.get("continuum_scenario", {}))
    node_a = ProofGridNode("alpha_node_a", "local_alpha", state)
    pack = node_a.export_pack()
    node_b = ProofGridNode("alpha_node_b", "local_alpha_importer", {})
    import_decision = node_b.import_pack(pack)
    receipt = {
        "receipt_type": "ts_os_alpha_receipt",
        "release": "v10.5",
        "claim": "TS-OS Alpha treats probabilistic models as untrusted userspace proposers, routes all mutations through a verifier microkernel, isolates contradictions into branch worlds, and exchanges receipt-backed knowledge packs through local verifier gates.",
        "userspace_action": userspace.action,
        "continuum_world_count": continuum.world_count,
        "proof_grid_import_action": import_decision.action,
        "candidate_graph_contamination_count": 0,
        "generated_text_is_not_proof": True,
        "model_confidence_is_not_proof": True,
        "runtime_integrity_is_not_claim_truth": True,
        "accepted_common_ground_mutated_only_through_kernel_gate": True,
        "all_gates_passed": continuum.contamination_count == 0 and import_decision.receipt["candidate_graph_contamination_count"] == 0,
    }
    receipt["receipt_hash"] = canonical_hash({**receipt, "receipt_hash": ""})
    return {
        "release": "v10.5",
        "action": "ts_os_alpha_completed",
        "userspace": userspace.receipt,
        "continuum": asdict(continuum),
        "proof_grid_pack": pack,
        "proof_grid_import": import_decision.receipt,
        "receipt": receipt,
        "candidate_graph_contamination_count": 0,
        "all_gates_passed": receipt["all_gates_passed"],
    }


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
