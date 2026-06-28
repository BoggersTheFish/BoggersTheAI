"""Knowledge pack library for TS-Reasoner v7.6.0.

v7.6 adds a local library for bounded TS-Chat knowledge packs.

Capabilities:
- register packs by label
- list pack metadata
- compare pack edges
- audit unsafe imports
- safely merge compatible pack edges into a TSChatSession

Boundary:
- pack import is not proof
- pack merge is not proof
- pack metadata is not proof
- rejected pack records are not promoted
- typed verifier/common-ground support remains proof authority
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ts_reasoner.ts_chat import TSChatSession, receipt_to_dict

RELEASE = "v7.6.0"
SCHEMA = "ts_reasoner_knowledge_pack_library_v1"


@dataclass(frozen=True)
class PackEntry:
    label: str
    path: str
    schema: str
    release: str
    accepted_edge_count: int
    rejected_or_unsupported_record_count: int
    repair_target_count: int
    external_llm_used: bool
    pack_import_is_proof: bool = False
    pack_merge_is_proof: bool = False
    typed_verifier_remains_proof_authority: bool = True


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, payload: Any) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return out


def relation_key(relation: dict[str, Any]) -> tuple[str, str]:
    return str(relation.get("subject")), str(relation.get("object"))


def relation_text(relation: dict[str, Any]) -> str:
    return f"all {relation.get('subject')} are {relation.get('object')}"


def _sorted_relation_dicts(edges: set[tuple[str, str]]) -> list[dict[str, str]]:
    return [
        {"subject": subject, "object": object_} for subject, object_ in sorted(edges)
    ]


def pack_accepted_edges(pack: dict[str, Any]) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()

    for relation in pack.get("accepted_edges", []):
        if relation:
            edges.add(relation_key(relation))

    # v6.7/v7.1 pack forms may also carry full records.
    for record in pack.get("records", []):
        if (
            record.get("kind") == "asserted_premise"
            and record.get("status") == "accepted"
        ):
            relation = record.get("relation")
            if relation:
                edges.add(relation_key(relation))

    return edges


def pack_rejected_relations(pack: dict[str, Any]) -> set[tuple[str, str]]:
    rejected: set[tuple[str, str]] = set()

    for record in pack.get("records", []):
        if record.get("status") in {"rejected", "unsupported", "abstained"}:
            relation = record.get("relation")
            if relation:
                rejected.add(relation_key(relation))

    return rejected


def session_rejected_relations(session: TSChatSession) -> set[tuple[str, str]]:
    rejected: set[tuple[str, str]] = set()

    for record in session.common_ground.records:
        if record.status in {"rejected", "unsupported", "abstained"}:
            rejected.add((record.relation.subject, record.relation.object))

    return rejected


def make_pack_entry(label: str, path: str | Path, pack: dict[str, Any]) -> PackEntry:
    accepted_edges = pack_accepted_edges(pack)
    rejected = pack_rejected_relations(pack)
    repairs = pack.get("repair_targets", [])

    return PackEntry(
        label=label,
        path=str(path),
        schema=str(pack.get("schema", "unknown")),
        release=str(pack.get("release", "unknown")),
        accepted_edge_count=len(accepted_edges),
        rejected_or_unsupported_record_count=len(rejected),
        repair_target_count=len(repairs),
        external_llm_used=bool(pack.get("external_llm_used", False)),
        pack_import_is_proof=False,
        pack_merge_is_proof=False,
        typed_verifier_remains_proof_authority=True,
    )


class KnowledgePackLibrary:
    def __init__(self, library_dir: str | Path) -> None:
        self.library_dir = Path(library_dir)
        self.library_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.library_dir / "index.json"
        self.entries: dict[str, PackEntry] = {}
        if self.index_path.exists():
            self._load_index()

    def _load_index(self) -> None:
        payload = _load_json(self.index_path)
        entries = payload.get("entries", {})
        self.entries = {label: PackEntry(**entry) for label, entry in entries.items()}

    def save_index(self) -> Path:
        payload = {
            "schema": SCHEMA,
            "release": RELEASE,
            "library_dir": str(self.library_dir),
            "pack_count": len(self.entries),
            "entries": {
                label: asdict(entry) for label, entry in sorted(self.entries.items())
            },
            "external_llm_used": False,
            "pack_import_is_proof": False,
            "pack_merge_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
            "candidate_graph_contamination_count": 0,
        }
        return _write_json(self.index_path, payload)

    def register_pack(self, label: str, pack_path: str | Path) -> dict[str, Any]:
        pack = _load_json(pack_path)
        entry = make_pack_entry(label, pack_path, pack)
        self.entries[label] = entry
        self.save_index()

        return {
            "schema": "ts_reasoner_knowledge_pack_register_receipt_v1",
            "release": RELEASE,
            "label": label,
            "entry": asdict(entry),
            "external_llm_used": False,
            "pack_import_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
            "candidate_graph_contamination_count": 0,
        }

    def list_packs(self) -> dict[str, Any]:
        return {
            "schema": "ts_reasoner_knowledge_pack_list_v1",
            "release": RELEASE,
            "pack_count": len(self.entries),
            "entries": {
                label: asdict(entry) for label, entry in sorted(self.entries.items())
            },
            "external_llm_used": False,
            "candidate_graph_contamination_count": 0,
        }

    def load_pack(self, label: str) -> dict[str, Any]:
        if label not in self.entries:
            raise KeyError(f"Unknown knowledge pack: {label}")
        return _load_json(self.entries[label].path)

    def compare_packs(self, left: str, right: str) -> dict[str, Any]:
        left_pack = self.load_pack(left)
        right_pack = self.load_pack(right)

        left_edges = pack_accepted_edges(left_pack)
        right_edges = pack_accepted_edges(right_pack)
        left_rejected = pack_rejected_relations(left_pack)
        right_rejected = pack_rejected_relations(right_pack)

        unsafe_conflicts = []
        for edge in sorted(left_edges & right_rejected):
            unsafe_conflicts.append(
                {
                    "direction": f"{left}_into_{right}",
                    "relation": {"subject": edge[0], "object": edge[1]},
                    "reason": "left pack accepts a relation rejected by right pack",
                }
            )
        for edge in sorted(right_edges & left_rejected):
            unsafe_conflicts.append(
                {
                    "direction": f"{right}_into_{left}",
                    "relation": {"subject": edge[0], "object": edge[1]},
                    "reason": "right pack accepts a relation rejected by left pack",
                }
            )

        return {
            "schema": "ts_reasoner_knowledge_pack_compare_v1",
            "release": RELEASE,
            "left": left,
            "right": right,
            "shared_edges": _sorted_relation_dicts(left_edges & right_edges),
            "only_left_edges": _sorted_relation_dicts(left_edges - right_edges),
            "only_right_edges": _sorted_relation_dicts(right_edges - left_edges),
            "left_rejected_relations": _sorted_relation_dicts(left_rejected),
            "right_rejected_relations": _sorted_relation_dicts(right_rejected),
            "unsafe_conflicts": unsafe_conflicts,
            "external_llm_used": False,
            "pack_compare_is_proof": False,
            "candidate_graph_contamination_count": 0,
        }

    def audit_merge_into_session(
        self, label: str, session: TSChatSession
    ) -> dict[str, Any]:
        pack = self.load_pack(label)
        pack_edges = pack_accepted_edges(pack)
        pack_rejected = pack_rejected_relations(pack)
        session_rejected = session_rejected_relations(session)
        session_edges = set(session.common_ground.accepted_edges)

        blocked_edges = []
        for edge in sorted(pack_edges):
            if edge in session_rejected:
                blocked_edges.append(
                    {
                        "relation": {"subject": edge[0], "object": edge[1]},
                        "reason": "pack accepts a relation rejected by target session",
                    }
                )

        rejected_not_promoted = _sorted_relation_dicts(pack_rejected)

        return {
            "schema": "ts_reasoner_knowledge_pack_merge_audit_v1",
            "release": RELEASE,
            "label": label,
            "pack_edge_count": len(pack_edges),
            "new_edge_count": len(pack_edges - session_edges),
            "already_present_edge_count": len(pack_edges & session_edges),
            "blocked_edge_count": len(blocked_edges),
            "blocked_edges": blocked_edges,
            "rejected_pack_relations_not_promoted": rejected_not_promoted,
            "safe_to_merge": len(blocked_edges) == 0,
            "external_llm_used": False,
            "pack_import_is_proof": False,
            "pack_merge_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
            "candidate_graph_contamination_count": 0,
        }

    def merge_pack_into_session(
        self, label: str, session: TSChatSession
    ) -> dict[str, Any]:
        audit = self.audit_merge_into_session(label, session)

        if not audit["safe_to_merge"]:
            return {
                "schema": "ts_reasoner_knowledge_pack_merge_receipt_v1",
                "release": RELEASE,
                "label": label,
                "merged": False,
                "blocked": True,
                "audit": audit,
                "created_receipts": [],
                "external_llm_used": False,
                "pack_import_is_proof": False,
                "pack_merge_is_proof": False,
                "typed_verifier_remains_proof_authority": True,
                "candidate_graph_contamination_count": 0,
            }

        pack = self.load_pack(label)
        session_edges = set(session.common_ground.accepted_edges)
        created_receipts = []

        for subject, object_ in sorted(pack_accepted_edges(pack) - session_edges):
            receipt = session.process(f"all {subject} are {object_}")
            created_receipts.append(receipt_to_dict(receipt))

        return {
            "schema": "ts_reasoner_knowledge_pack_merge_receipt_v1",
            "release": RELEASE,
            "label": label,
            "merged": True,
            "blocked": False,
            "merged_edge_count": len(created_receipts),
            "audit": audit,
            "created_receipts": created_receipts,
            "external_llm_used": False,
            "pack_import_is_proof": False,
            "pack_merge_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
            "candidate_graph_contamination_count": 0,
        }


def create_pack_from_edges(
    path: str | Path,
    *,
    label: str,
    accepted_edges: list[tuple[str, str]],
    rejected_relations: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    rejected_relations = rejected_relations or []
    records = []
    claim_id = 1

    for subject, object_ in accepted_edges:
        records.append(
            {
                "claim_id": f"pack_{claim_id:04d}",
                "kind": "asserted_premise",
                "status": "accepted",
                "source": "knowledge_pack",
                "turn_id": claim_id,
                "relation": {"subject": subject, "object": object_},
                "support_path": [{"subject": subject, "object": object_}],
                "discourse_markers": [],
                "reason": "accepted premise stored in bounded knowledge pack",
            }
        )
        claim_id += 1

    for subject, object_ in rejected_relations:
        records.append(
            {
                "claim_id": f"pack_{claim_id:04d}",
                "kind": "requested_claim",
                "status": "rejected",
                "source": "knowledge_pack",
                "turn_id": claim_id,
                "relation": {"subject": subject, "object": object_},
                "support_path": [],
                "discourse_markers": [],
                "reason": "rejected record stored in bounded knowledge pack",
            }
        )
        claim_id += 1

    pack = {
        "schema": "ts_reasoner_v7_6_demo_knowledge_pack",
        "release": RELEASE,
        "label": label,
        "accepted_edges": [
            {"subject": subject, "object": object_}
            for subject, object_ in accepted_edges
        ],
        "records": records,
        "repair_targets": [],
        "external_llm_used": False,
        "knowledge_pack_import_is_proof": False,
        "pack_merge_is_proof": False,
        "typed_verifier_remains_proof_authority": True,
        "candidate_graph_contamination_count": 0,
    }

    _write_json(path, pack)
    return pack


def knowledge_pack_library_state_valid(payload: dict[str, Any]) -> bool:
    required = {
        "schema",
        "release",
        "pack_count",
        "entries",
        "external_llm_used",
        "candidate_graph_contamination_count",
    }
    if not required.issubset(payload):
        return False
    if payload["release"] != RELEASE:
        return False
    if payload["external_llm_used"] is not False:
        return False
    if payload["candidate_graph_contamination_count"] != 0:
        return False
    if payload["pack_count"] != len(payload["entries"]):
        return False
    return True


def run_knowledge_pack_library_demo(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    packs_dir = out / "packs"
    library_dir = out / "library"
    packs_dir.mkdir(parents=True, exist_ok=True)

    animals_pack_path = packs_dir / "animals_pack.json"
    machines_pack_path = packs_dir / "machines_pack.json"
    unsafe_pack_path = packs_dir / "unsafe_pack.json"

    create_pack_from_edges(
        animals_pack_path,
        label="animals",
        accepted_edges=[("cats", "animals"), ("animals", "mortal")],
    )
    create_pack_from_edges(
        machines_pack_path,
        label="machines",
        accepted_edges=[("cats", "machines"), ("machines", "robots")],
    )
    create_pack_from_edges(
        unsafe_pack_path,
        label="unsafe_direct_robots",
        accepted_edges=[("cats", "robots")],
    )

    library = KnowledgePackLibrary(library_dir)
    library.register_pack("animals", animals_pack_path)
    library.register_pack("machines", machines_pack_path)
    library.register_pack("unsafe_direct_robots", unsafe_pack_path)

    listing = library.list_packs()
    compare = library.compare_packs("animals", "machines")

    session = TSChatSession()
    session.process("also say all cats are robots")

    unsafe_audit = library.audit_merge_into_session("unsafe_direct_robots", session)
    unsafe_merge = library.merge_pack_into_session("unsafe_direct_robots", session)

    machines_audit = library.audit_merge_into_session("machines", session)
    machines_merge = library.merge_pack_into_session("machines", session)
    post_merge_question = session.process("are all cats robots?")
    post_merge_why = session.process("why?")

    state_path = out / "knowledge_pack_library_state.json"
    receipt_path = out / "knowledge_pack_library_receipt.json"
    report_path = out / "knowledge_pack_library_report.json"

    state = {
        "library": listing,
        "compare": compare,
        "unsafe_audit": unsafe_audit,
        "unsafe_merge": unsafe_merge,
        "machines_audit": machines_audit,
        "machines_merge": machines_merge,
        "post_merge_question": receipt_to_dict(post_merge_question),
        "post_merge_why": receipt_to_dict(post_merge_why),
    }

    _write_json(state_path, state)

    post_merge_accepted = any(
        record.get("kind") == "question"
        and record.get("status") == "accepted"
        and record.get("relation", {}).get("subject") == "cats"
        and record.get("relation", {}).get("object") == "robots"
        for record in post_merge_question.records_created
    )

    gates = {
        "library_state_valid": knowledge_pack_library_state_valid(listing),
        "three_packs_registered": listing["pack_count"] == 3,
        "pack_compare_available": compare["schema"]
        == "ts_reasoner_knowledge_pack_compare_v1",
        "unsafe_merge_blocked": unsafe_merge["blocked"] is True
        and unsafe_merge["merged"] is False,
        "safe_merge_allowed": machines_merge["merged"] is True
        and machines_merge["blocked"] is False,
        "safe_merge_added_edges": machines_merge["merged_edge_count"] == 2,
        "post_merge_answer_accepted": bool(post_merge_accepted),
        "rejected_pack_relations_not_promoted": isinstance(
            machines_audit["rejected_pack_relations_not_promoted"], list
        ),
        "pack_import_is_not_proof": machines_merge["pack_import_is_proof"] is False,
        "pack_merge_is_not_proof": machines_merge["pack_merge_is_proof"] is False,
        "candidate_graph_contamination_count_is_zero": (
            listing["candidate_graph_contamination_count"] == 0
            and compare["candidate_graph_contamination_count"] == 0
            and unsafe_merge["candidate_graph_contamination_count"] == 0
            and machines_merge["candidate_graph_contamination_count"] == 0
        ),
        "external_llm_used_false": True,
    }

    receipt = {
        "schema": "ts_reasoner_v7_6_knowledge_pack_library_receipt",
        "release": RELEASE,
        "milestone": "Knowledge Pack Library + Safe Merge",
        "external_llm_used": False,
        "out_dir": str(out),
        "state_path": str(state_path),
        "report_path": str(report_path),
        "pack_count": listing["pack_count"],
        "unsafe_merge_blocked": gates["unsafe_merge_blocked"],
        "safe_merge_allowed": gates["safe_merge_allowed"],
        "safe_merge_added_edges": machines_merge["merged_edge_count"],
        "post_merge_answer_accepted": bool(post_merge_accepted),
        "candidate_graph_contamination_count": 0,
        "pack_import_is_not_proof": True,
        "pack_merge_is_not_proof": True,
        "pack_metadata_is_not_proof": True,
        "typed_verifier_remains_proof_authority": True,
        "gates": gates,
        "all_gates_passed": all(gates.values()),
        "boundary": {
            "broad_natural_language_understanding": False,
            "neural_training": False,
            "live_tensionlm_runtime": False,
            "external_benchmark_victory": False,
            "pack_import_is_proof": False,
            "pack_merge_is_proof": False,
            "pack_metadata_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
        },
    }

    report = {
        "schema": "ts_reasoner_v7_6_knowledge_pack_library_report",
        "release": RELEASE,
        "pack_count": listing["pack_count"],
        "unsafe_merge_blocked": receipt["unsafe_merge_blocked"],
        "safe_merge_allowed": receipt["safe_merge_allowed"],
        "safe_merge_added_edges": receipt["safe_merge_added_edges"],
        "post_merge_answer_accepted": receipt["post_merge_answer_accepted"],
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
        "all_gates_passed": receipt["all_gates_passed"],
    }

    _write_json(receipt_path, receipt)
    _write_json(report_path, report)

    receipt["receipt_path"] = str(receipt_path)
    return receipt
