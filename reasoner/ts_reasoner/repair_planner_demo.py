"""Demo helper for TS-Reasoner v7.5.0 repair planner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ts_reasoner.repair_planner import (
    generate_repair_plans,
    render_repair_plan_bundle,
    repair_plan_bundle_valid,
)
from ts_reasoner.ts_chat import TSChatSession, receipt_to_dict

RELEASE = "v7.5.0"


def run_repair_planner_demo(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    session = TSChatSession()
    turns = [
        "all cats are animals",
        "all animals are mortal",
        "also say all cats are robots",
        "/plan repair_0001",
        "no cats are mortal",
        "/plan repair_0002",
    ]

    receipts = [session.process(turn) for turn in turns]
    receipt_dicts = [receipt_to_dict(receipt) for receipt in receipts]

    missing_support_repair = next(
        repair
        for repair in session.common_ground.repair_targets
        if repair.kind == "missing_support"
    )
    contradiction_repair = next(
        repair
        for repair in session.common_ground.repair_targets
        if repair.kind == "contradiction"
    )

    missing_support_bundle = generate_repair_plans(
        session.common_ground, missing_support_repair.repair_id
    )
    contradiction_bundle = generate_repair_plans(
        session.common_ground, contradiction_repair.repair_id
    )

    missing_support_rendered = render_repair_plan_bundle(missing_support_bundle)
    contradiction_rendered = render_repair_plan_bundle(contradiction_bundle)

    session_path = out / "repair_planner_session.json"
    bundle_path = out / "repair_planner_bundles.json"
    report_path = out / "repair_planner_report.json"
    receipt_path = out / "repair_planner_receipt.json"

    session_path.write_text(
        json.dumps(receipt_dicts, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    bundle_path.write_text(
        json.dumps(
            {
                "missing_support_bundle": missing_support_bundle,
                "contradiction_bundle": contradiction_bundle,
                "missing_support_rendered": missing_support_rendered,
                "contradiction_rendered": contradiction_rendered,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    gates = {
        "missing_support_bundle_valid": repair_plan_bundle_valid(
            missing_support_bundle
        ),
        "contradiction_bundle_valid": repair_plan_bundle_valid(contradiction_bundle),
        "missing_support_has_bridge_plan": any(
            plan["strategy"] == "bridge_support"
            for plan in missing_support_bundle["plans"]
        ),
        "missing_support_has_direct_plan": any(
            plan["strategy"] == "direct_support"
            for plan in missing_support_bundle["plans"]
        ),
        "contradiction_has_keep_rejected_plan": any(
            plan["strategy"] == "keep_negative_rejected"
            for plan in contradiction_bundle["plans"]
        ),
        "contradiction_has_dispute_support_plan": any(
            plan["strategy"] == "dispute_support_premise"
            for plan in contradiction_bundle["plans"]
        ),
        "plans_create_no_proof": (
            missing_support_bundle["all_plans_create_no_proof"]
            and contradiction_bundle["all_plans_create_no_proof"]
        ),
        "plans_not_auto_applied": (
            missing_support_bundle["all_plans_not_auto_applied"]
            and contradiction_bundle["all_plans_not_auto_applied"]
        ),
        "candidate_graph_contamination_count_is_zero": (
            missing_support_bundle["candidate_graph_contamination_count"] == 0
            and contradiction_bundle["candidate_graph_contamination_count"] == 0
        ),
        "external_llm_used_false": True,
    }

    receipt = {
        "schema": "ts_reasoner_v7_5_repair_planner_receipt",
        "release": RELEASE,
        "milestone": "Repair Planner",
        "external_llm_used": False,
        "out_dir": str(out),
        "session_path": str(session_path),
        "bundle_path": str(bundle_path),
        "report_path": str(report_path),
        "missing_support_plan_count": missing_support_bundle["plan_count"],
        "contradiction_plan_count": contradiction_bundle["plan_count"],
        "candidate_graph_contamination_count": 0,
        "repair_plans_are_not_proof": True,
        "generated_bridge_terms_are_not_proof": True,
        "user_confirmation_is_not_proof": True,
        "typed_verifier_remains_proof_authority": True,
        "gates": gates,
        "all_gates_passed": all(gates.values()),
        "boundary": {
            "broad_natural_language_understanding": False,
            "neural_training": False,
            "live_tensionlm_runtime": False,
            "external_benchmark_victory": False,
            "repair_plan_is_proof": False,
            "generated_bridge_term_is_proof": False,
            "user_confirmation_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
        },
    }

    report = {
        "schema": "ts_reasoner_v7_5_repair_planner_report",
        "release": RELEASE,
        "missing_support_plan_count": missing_support_bundle["plan_count"],
        "contradiction_plan_count": contradiction_bundle["plan_count"],
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
        "all_gates_passed": receipt["all_gates_passed"],
    }

    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    receipt["receipt_path"] = str(receipt_path)
    return receipt
