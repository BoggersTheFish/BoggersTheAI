from __future__ import annotations

import argparse
import json
from typing import Any

from ts_reasoner.central_brain import CentralBrainRuntime, default_brain_path, stable_hash


def _json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _boundary_kwargs(value: str) -> dict[str, Any]:
    try:
        return {"boundary_sequence": int(value)}
    except ValueError:
        return {"boundary_hash": value}


def _support(value: str | None, command: str) -> list[str]:
    if value:
        return [value]
    return [f"typed_support:central_brain_cli:{command}"]


def _dashboard_summary(brain: CentralBrainRuntime) -> dict[str, Any]:
    dashboard = brain.dashboard()
    return {
        "action": "dashboard",
        "ledger_head": dashboard["ledger_head"],
        "node_count": dashboard["node_count"],
        "edge_count": dashboard["edge_count"],
        "status_counts": dashboard["status_counts"],
        "node_type_counts": dashboard["tension_telemetry"]["node_type_counts"],
        "tension_hotspots": dashboard["tension_telemetry"]["hotspots"],
        "strongest_nodes": dashboard["tension_telemetry"]["strongest_nodes"],
        "repair_targets": dashboard["repair_targets"],
        "branch_worlds": dashboard["branch_worlds"],
        "replay_sessions": dashboard["replay_sessions"],
        "cli_sessions": dashboard["cli_sessions"],
        "recent_receipts": dashboard["recent_receipts"],
        "candidate_graph_contamination_count": dashboard["candidate_graph_contamination_count"],
        "graph_mutated": False,
    }


def _verify_chain(brain: CentralBrainRuntime) -> dict[str, Any]:
    receipts = brain._ledger_receipts()
    chain_valid = brain._verify_receipt_chain(receipts)
    issues = []
    previous = "0" * 64
    for index, receipt in enumerate(receipts):
        if int(receipt.get("sequence", -1)) != index:
            issues.append({"sequence": index, "issue": "sequence_gap_or_reorder"})
        if receipt.get("previous_hash") != previous:
            issues.append({"sequence": index, "issue": "previous_hash_mismatch"})
        previous = str(receipt.get("receipt_hash", ""))
    return {
        "action": "verify_chain",
        "chain_valid": chain_valid,
        "receipt_count": len(receipts),
        "ledger_head": brain.graph_snapshot()["ledger_head"],
        "issues": issues,
        "candidate_graph_contamination_count": 0,
        "graph_mutated": False,
    }


def run_cli_payload(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    brain = CentralBrainRuntime(args.db)

    if args.command in {"dashboard", "status"}:
        return 0, _dashboard_summary(brain)

    if args.command == "verify-chain":
        payload = _verify_chain(brain)
        return (0 if payload["chain_valid"] else 1), payload

    if args.command == "inspect-receipt":
        replay = brain.inspect_receipt_boundary(
            **_boundary_kwargs(args.boundary),
            support=_support(args.support, "inspect_receipt"),
        )
        snapshot = replay.snapshot
        payload = {
            "action": "inspect_receipt",
            "mode": replay.mode,
            "boundary_receipt_hash": replay.boundary_receipt_hash,
            "boundary_sequence": replay.boundary_sequence,
            "chain_valid": replay.chain_valid,
            "receipt_hash": replay.receipt["receipt_hash"] if replay.receipt else "",
            "snapshot": {
                "ledger_head": snapshot["ledger_head"],
                "node_count": len(snapshot["nodes"]),
                "edge_count": len(snapshot["edges"]),
            },
            "delta_since_boundary": replay.delta_since_boundary,
            "tension_telemetry": replay.tension_telemetry,
            "graph_mutated": False,
            "candidate_graph_contamination_count": 0,
        }
        return 0, payload

    if args.command == "revert-branch":
        replay = brain.create_revert_branch_from_receipt(
            **_boundary_kwargs(args.boundary),
            support=_support(args.support, "revert_branch"),
        )
        cli_session = brain.submit_candidate(
            {
                "action": "add_node",
                "node_id": f"cli:session:{stable_hash({'command': 'revert-branch', 'receipt': replay.receipt['receipt_hash']})[:16]}",
                "node_type": "cli_session",
                "payload": {
                    "command": "revert-branch",
                    "boundary_receipt_hash": replay.boundary_receipt_hash,
                    "boundary_sequence": replay.boundary_sequence,
                    "result_receipt_hash": replay.receipt["receipt_hash"] if replay.receipt else "",
                    "graph_mutation": "branch_world_restore_context_created",
                },
                "support": _support(args.support, "revert_branch_cli_session"),
            },
            proposer_id="central_brain_cli",
        )
        payload = {
            "action": "revert_branch",
            "mode": replay.mode,
            "boundary_receipt_hash": replay.boundary_receipt_hash,
            "boundary_sequence": replay.boundary_sequence,
            "chain_valid": replay.chain_valid,
            "receipt_hash": replay.receipt["receipt_hash"] if replay.receipt else "",
            "cli_session_node_id": cli_session.state_delta["nodes_added"][0]["node_id"],
            "cli_session_receipt_hash": cli_session.receipt["receipt_hash"],
            "branch_world": replay.branch_world,
            "delta_since_boundary": replay.delta_since_boundary,
            "tension_telemetry": replay.tension_telemetry,
            "accepted_state_overwritten": False,
            "candidate_graph_contamination_count": 0,
        }
        return 0, payload

    return 2, {
        "action": "invalid_input",
        "error": "unknown_command",
        "candidate_graph_contamination_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ts-central-brain")
    parser.add_argument("--db", default=str(default_brain_path()), help="Path to central brain SQLite DB.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("dashboard")
    sub.add_parser("status")
    sub.add_parser("verify-chain")

    inspect = sub.add_parser("inspect-receipt")
    inspect.add_argument("boundary", help="Receipt sequence integer or receipt hash.")
    inspect.add_argument("--support", help="Typed support string for the replay verifier gate.")

    revert = sub.add_parser("revert-branch")
    revert.add_argument("boundary", help="Receipt sequence integer or receipt hash.")
    revert.add_argument("--support", help="Typed support string for the replay verifier gate.")

    args = parser.parse_args(argv)

    try:
        exit_code, output = run_cli_payload(args)
    except Exception as exc:
        exit_code = 1
        output = {
            "action": getattr(args, "command", "unknown"),
            "error": str(exc),
            "candidate_graph_contamination_count": 0,
        }

    print(_json(output))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
