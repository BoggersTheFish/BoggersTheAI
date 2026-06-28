from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

SUPPORTED_SCHEMA = "1.0"
MIGRATABLE_SCHEMAS = {"0.9"}


@dataclass
class KnowledgePackImportResult:
    case_id: str
    imported: bool
    quarantined: bool
    migrated: bool
    accepted_claims: list[str] = field(default_factory=list)
    branch_worlds: list[dict[str, Any]] = field(default_factory=list)
    repair_targets: list[dict[str, Any]] = field(default_factory=list)
    provenance_records: list[dict[str, Any]] = field(default_factory=list)
    quarantined_claims: list[str] = field(default_factory=list)
    unsupported_claims_promoted_count: int = 0
    candidate_graph_contamination_count: int = 0
    explanation: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_claim(text: str) -> str:
    return " ".join(text.lower().strip().split())


def normalize_claims(claims: Iterable[str]) -> list[str]:
    return [normalize_claim(claim) for claim in claims]


def import_knowledge_pack(pack: dict[str, Any]) -> KnowledgePackImportResult:
    case_id = str(pack["case_id"])
    schema = str(pack["pack_schema_version"])

    if schema not in {SUPPORTED_SCHEMA, *MIGRATABLE_SCHEMAS}:
        return KnowledgePackImportResult(
            case_id=case_id,
            imported=False,
            quarantined=True,
            migrated=False,
            accepted_claims=[],
            branch_worlds=[],
            repair_targets=[],
            provenance_records=[],
            quarantined_claims=normalize_claims(pack.get("unsupported_claims", [])),
            unsupported_claims_promoted_count=0,
            candidate_graph_contamination_count=0,
            explanation="Knowledge pack schema is invalid, so the pack is quarantined and no state is imported.",
        )

    migrated = schema in MIGRATABLE_SCHEMAS
    accepted_claims = normalize_claims(pack.get("accepted_claims", []))
    unsupported_claims = normalize_claims(pack.get("unsupported_claims", []))

    branch_worlds = []
    for world in pack.get("branch_worlds", []):
        branch_worlds.append(
            {
                "world_id": str(world["world_id"]),
                "parent_world_id": str(world["parent_world_id"]),
                "claims": normalize_claims(world.get("claims", [])),
                "branch_reason": str(world["branch_reason"]),
                "auto_merge_allowed": False,
            }
        )

    repair_targets = []
    for target in pack.get("repair_targets", []):
        repair_targets.append(
            {
                "target_claim": normalize_claim(str(target["target_claim"])),
                "repair_type": str(target["repair_type"]),
                "candidate_bridges": normalize_claims(
                    target.get("candidate_bridges", [])
                ),
                "accepted_as_proof": False,
            }
        )

    provenance_records = []
    for record in pack.get("provenance_records", []):
        provenance_records.append(
            {
                "claim": normalize_claim(str(record["claim"])),
                "source": str(record["source"]),
                "trust": float(record["trust"]),
            }
        )

    return KnowledgePackImportResult(
        case_id=case_id,
        imported=True,
        quarantined=bool(unsupported_claims),
        migrated=migrated,
        accepted_claims=accepted_claims,
        branch_worlds=branch_worlds,
        repair_targets=repair_targets,
        provenance_records=provenance_records,
        quarantined_claims=unsupported_claims,
        unsupported_claims_promoted_count=0,
        candidate_graph_contamination_count=0,
        explanation="Knowledge pack imported under contract. Unsupported claims are quarantined and candidate/repair data is not promoted to proof.",
    )


def evaluate_knowledge_pack_cases(cases: Iterable[dict[str, Any]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0
    unsupported_promoted = 0

    for raw in cases:
        total += 1
        result = import_knowledge_pack(raw)

        expected_imported = bool(raw["expected_imported"])
        expected_quarantined = bool(raw["expected_quarantined"])
        expected_migrated = bool(raw["expected_migrated"])
        expected_accepted_count = int(raw["expected_accepted_claim_count"])
        expected_branch_count = int(raw["expected_branch_world_count"])
        expected_repair_count = int(raw["expected_repair_target_count"])

        case_passed = (
            result.imported == expected_imported
            and result.quarantined == expected_quarantined
            and result.migrated == expected_migrated
            and len(result.accepted_claims) == expected_accepted_count
            and len(result.branch_worlds) == expected_branch_count
            and len(result.repair_targets) == expected_repair_count
            and result.unsupported_claims_promoted_count == 0
            and result.candidate_graph_contamination_count == 0
        )

        if case_passed:
            passed += 1

        contamination += result.candidate_graph_contamination_count
        unsupported_promoted += result.unsupported_claims_promoted_count

        row = result.to_dict()
        row["expected_imported"] = expected_imported
        row["expected_quarantined"] = expected_quarantined
        row["expected_migrated"] = expected_migrated
        row["expected_accepted_claim_count"] = expected_accepted_count
        row["expected_branch_world_count"] = expected_branch_count
        row["expected_repair_target_count"] = expected_repair_count
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v8.5.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "knowledge_pack_contract_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "unsupported_claims_promoted_count": unsupported_promoted,
        "all_gates_passed": total > 0
        and passed == total
        and contamination == 0
        and unsupported_promoted == 0,
        "results": results,
    }
