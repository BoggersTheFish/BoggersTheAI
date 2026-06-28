"""TS-Reasoner v8.0.0 milestone pack.

Packages the v7.1-v7.9 verifier-first TS-Chat line into a single local
reasoning OS receipt.

Boundary:
- milestone packaging is not a new broad capability benchmark
- receipts are evidence, not proof of general intelligence
- generated text is not proof
- confidence/trust/audit/search outputs are not proof
- typed verifier support remains proof authority
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RELEASE = "v8.0.0"
SCHEMA = "ts_reasoner_v8_local_verifier_first_reasoning_os_v1"


COMPONENTS = [
    {
        "version": "v7.1.0",
        "name": "Unified Runtime + Session Compiler",
        "capability": "live runtime surface and session-to-artifact compiler",
        "receipt": "artifacts/ts_reasoner_v7_1_unified_runtime_receipt.json",
        "report": "artifacts/ts_reasoner_v7_1_unified_runtime_report.json",
    },
    {
        "version": "v7.2.0",
        "name": "Self-Curriculum Generator",
        "capability": "compiled sessions generate replay, repair, support-path, and boundary curriculum",
        "receipt": "artifacts/ts_reasoner_v7_2_self_curriculum_receipt.json",
        "report": "artifacts/ts_reasoner_v7_2_self_curriculum_report.json",
    },
    {
        "version": "v7.3.0",
        "name": "Branching Worlds",
        "capability": "branch-local common-ground worlds, comparisons, blocked unsafe merges, safe support merges",
        "receipt": "artifacts/ts_reasoner_v7_3_branching_worlds_receipt.json",
        "report": "artifacts/ts_reasoner_v7_3_branching_worlds_report.json",
    },
    {
        "version": "v7.4.0",
        "name": "Live Contradiction Firewall",
        "capability": "live no-X-are-Y contradiction rejection with support-path traces and repairs",
        "receipt": "artifacts/ts_reasoner_v7_4_live_contradiction_firewall_receipt.json",
        "report": "artifacts/ts_reasoner_v7_4_live_contradiction_firewall_report.json",
    },
    {
        "version": "v7.5.0",
        "name": "Repair Planner",
        "capability": "bounded repair plans for missing-support and contradiction repairs",
        "receipt": "artifacts/ts_reasoner_v7_5_repair_planner_receipt.json",
        "report": "artifacts/ts_reasoner_v7_5_repair_planner_report.json",
    },
    {
        "version": "v7.6.0",
        "name": "Knowledge Pack Library + Safe Merge",
        "capability": "registered local knowledge packs, pack comparison, safe merge and blocked unsafe import",
        "receipt": "artifacts/ts_reasoner_v7_6_knowledge_pack_library_receipt.json",
        "report": "artifacts/ts_reasoner_v7_6_knowledge_pack_library_report.json",
    },
    {
        "version": "v7.7.0",
        "name": "Provenance Trust Pressure",
        "capability": "source trust tiers create merge pressure without becoming proof",
        "receipt": "artifacts/ts_reasoner_v7_7_trust_pressure_receipt.json",
        "report": "artifacts/ts_reasoner_v7_7_trust_pressure_report.json",
    },
    {
        "version": "v7.8.0",
        "name": "Minimal Proof / Repair Search",
        "capability": "live /prove, /missing, and /cut search over bounded common ground",
        "receipt": "artifacts/ts_reasoner_v7_8_proof_repair_search_receipt.json",
        "report": "artifacts/ts_reasoner_v7_8_proof_repair_search_report.json",
    },
    {
        "version": "v7.9.0",
        "name": "Live Self-Audit Mode",
        "capability": "live /audit for session health, boundary preservation, repair pressure, and contamination checks",
        "receipt": "artifacts/ts_reasoner_v7_9_live_self_audit_receipt.json",
        "report": "artifacts/ts_reasoner_v7_9_live_self_audit_report.json",
    },
]


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, payload: Any) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return out


def _bool_from(payload: dict[str, Any], key: str, default: bool = False) -> bool:
    return bool(payload.get(key, default))


def _int_from(payload: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(payload.get(key, default))
    except (TypeError, ValueError):
        return default


def _boundary_ok(receipt: dict[str, Any]) -> bool:
    boundary = receipt.get("boundary", {})

    broad_ok = boundary.get("broad_natural_language_understanding") is False
    neural_ok = boundary.get("neural_training") is False
    tensionlm_ok = boundary.get("live_tensionlm_runtime") is False
    benchmark_ok = boundary.get("external_benchmark_victory") is False

    typed_ok = (
        receipt.get("typed_verifier_remains_proof_authority") is True
        or boundary.get("typed_verifier_remains_proof_authority") is True
    )

    return broad_ok and neural_ok and tensionlm_ok and benchmark_ok and typed_ok


def _proof_boundary_flags(receipt: dict[str, Any]) -> dict[str, bool]:
    boundary = receipt.get("boundary", {})

    return {
        "no_broad_natural_language_understanding_claim": boundary.get(
            "broad_natural_language_understanding"
        )
        is False,
        "no_neural_training_claim": boundary.get("neural_training") is False,
        "no_live_tensionlm_runtime_claim": boundary.get("live_tensionlm_runtime")
        is False,
        "no_external_benchmark_victory_claim": boundary.get(
            "external_benchmark_victory"
        )
        is False,
        "typed_verifier_remains_proof_authority": (
            receipt.get("typed_verifier_remains_proof_authority") is True
            or boundary.get("typed_verifier_remains_proof_authority") is True
        ),
    }


def _component_summary(component: dict[str, str]) -> dict[str, Any]:
    receipt_path = Path(component["receipt"])
    report_path = Path(component["report"])

    receipt_exists = receipt_path.exists()
    report_exists = report_path.exists()

    receipt: dict[str, Any] = _load_json(receipt_path) if receipt_exists else {}
    report: dict[str, Any] = _load_json(report_path) if report_exists else {}

    candidate_graph_contamination_count = _int_from(
        receipt, "candidate_graph_contamination_count", 0
    ) + _int_from(report, "candidate_graph_contamination_count", 0)

    external_llm_used = _bool_from(receipt, "external_llm_used", False) or _bool_from(
        report, "external_llm_used", False
    )

    gates_passed = (
        receipt_exists
        and report_exists
        and receipt.get("all_gates_passed") is True
        and report.get("all_gates_passed") is True
    )

    return {
        "version": component["version"],
        "name": component["name"],
        "capability": component["capability"],
        "receipt_path": component["receipt"],
        "report_path": component["report"],
        "receipt_exists": receipt_exists,
        "report_exists": report_exists,
        "receipt_all_gates_passed": receipt.get("all_gates_passed") is True,
        "report_all_gates_passed": report.get("all_gates_passed") is True,
        "component_gates_passed": gates_passed,
        "candidate_graph_contamination_count": candidate_graph_contamination_count,
        "external_llm_used": external_llm_used,
        "boundary_flags": _proof_boundary_flags(receipt),
        "boundary_ok": _boundary_ok(receipt),
        "receipt_schema": receipt.get("schema"),
        "report_schema": report.get("schema"),
    }


def build_v8_milestone_payload() -> dict[str, Any]:
    components = [_component_summary(component) for component in COMPONENTS]

    missing_assets = [
        {
            "version": component["version"],
            "name": component["name"],
            "receipt_exists": component["receipt_exists"],
            "report_exists": component["report_exists"],
            "receipt_path": component["receipt_path"],
            "report_path": component["report_path"],
        }
        for component in components
        if not component["receipt_exists"] or not component["report_exists"]
    ]

    failed_components = [
        {
            "version": component["version"],
            "name": component["name"],
            "receipt_all_gates_passed": component["receipt_all_gates_passed"],
            "report_all_gates_passed": component["report_all_gates_passed"],
            "boundary_ok": component["boundary_ok"],
        }
        for component in components
        if not component["component_gates_passed"] or not component["boundary_ok"]
    ]

    total_candidate_graph_contamination_count = sum(
        component["candidate_graph_contamination_count"] for component in components
    )
    external_llm_used_any = any(
        component["external_llm_used"] for component in components
    )

    component_count = len(components)
    component_gate_pass_count = sum(
        1 for component in components if component["component_gates_passed"]
    )
    boundary_ok_count = sum(1 for component in components if component["boundary_ok"])

    capabilities = [component["capability"] for component in COMPONENTS]

    gates = {
        "all_assets_present": len(missing_assets) == 0,
        "all_component_gates_passed": component_gate_pass_count == component_count,
        "all_boundaries_ok": boundary_ok_count == component_count,
        "candidate_graph_contamination_count_is_zero": total_candidate_graph_contamination_count
        == 0,
        "external_llm_used_false": external_llm_used_any is False,
        "component_count_is_nine": component_count == 9,
        "typed_verifier_remains_proof_authority": True,
        "milestone_pack_is_not_external_benchmark_claim": True,
    }

    return {
        "schema": SCHEMA,
        "release": RELEASE,
        "milestone": "Local Verifier-First Reasoning OS",
        "component_count": component_count,
        "component_gate_pass_count": component_gate_pass_count,
        "boundary_ok_count": boundary_ok_count,
        "components": components,
        "capabilities": capabilities,
        "missing_assets": missing_assets,
        "failed_components": failed_components,
        "total_candidate_graph_contamination_count": total_candidate_graph_contamination_count,
        "external_llm_used_any": external_llm_used_any,
        "local_runtime_included": True,
        "session_compiler_included": True,
        "self_curriculum_included": True,
        "branching_worlds_included": True,
        "live_contradiction_firewall_included": True,
        "repair_planner_included": True,
        "knowledge_pack_library_included": True,
        "trust_pressure_included": True,
        "proof_repair_search_included": True,
        "live_self_audit_included": True,
        "generated_text_is_not_proof": True,
        "trust_is_not_proof": True,
        "audit_output_is_not_proof": True,
        "search_results_are_not_proof": True,
        "milestone_pack_is_not_external_benchmark_claim": True,
        "typed_verifier_remains_proof_authority": True,
        "candidate_graph_contamination_count": total_candidate_graph_contamination_count,
        "external_llm_used": external_llm_used_any,
        "gates": gates,
        "all_gates_passed": all(gates.values()),
        "boundary": {
            "broad_natural_language_understanding": False,
            "neural_training": False,
            "live_tensionlm_runtime": False,
            "external_benchmark_victory": False,
            "milestone_pack_is_general_intelligence_claim": False,
            "generated_text_is_proof": False,
            "trust_is_proof": False,
            "audit_output_is_proof": False,
            "search_result_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
        },
    }


def run_v8_milestone(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    payload = build_v8_milestone_payload()

    receipt_path = out / "v8_0_local_verifier_first_reasoning_os_receipt.json"
    report_path = out / "v8_0_local_verifier_first_reasoning_os_report.json"

    report = {
        "schema": "ts_reasoner_v8_0_local_verifier_first_reasoning_os_report",
        "release": RELEASE,
        "component_count": payload["component_count"],
        "component_gate_pass_count": payload["component_gate_pass_count"],
        "boundary_ok_count": payload["boundary_ok_count"],
        "total_candidate_graph_contamination_count": payload[
            "total_candidate_graph_contamination_count"
        ],
        "external_llm_used": payload["external_llm_used"],
        "missing_asset_count": len(payload["missing_assets"]),
        "failed_component_count": len(payload["failed_components"]),
        "capabilities": payload["capabilities"],
        "all_gates_passed": payload["all_gates_passed"],
    }

    _write_json(receipt_path, payload)
    _write_json(report_path, report)

    payload["receipt_path"] = str(receipt_path)
    payload["report_path"] = str(report_path)
    return payload
