from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ts_reasoner.runtime_os import run_runtime_os_suite, run_runtime_session
from ts_reasoner.ts_os import (
    ProofGridNode,
    run_alpha_scenario,
    run_continuum_scenario,
    run_userspace_app,
    write_json,
)


def load_json_arg(value: str) -> Any:
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


def run_session_payload(session: Any) -> tuple[int, dict[str, Any]]:
    if not isinstance(session, dict):
        return 2, {
            "action": "invalid_input",
            "error": "session_must_be_json_object",
            "candidate_graph_contamination_count": 0,
        }

    initial_state = session.get("initial_state")
    events = session.get("events")
    if not isinstance(initial_state, dict) or not isinstance(events, list):
        return 2, {
            "action": "invalid_input",
            "error": "initial_state_must_be_object_and_events_must_be_list",
            "candidate_graph_contamination_count": 0,
        }

    if not all(isinstance(event, dict) for event in events):
        return 2, {
            "action": "invalid_input",
            "error": "events_must_be_json_objects",
            "candidate_graph_contamination_count": 0,
        }

    result = run_runtime_session(
        case_id=str(session.get("case_id", "v10_runtime_session")),
        initial_state=initial_state,
        events=events,
    ).to_dict()
    result["action"] = "runtime_session_completed"
    return 0, result


def run_suite_payload(session: Any) -> tuple[int, dict[str, Any]]:
    if not isinstance(session, dict):
        return 2, {
            "action": "invalid_input",
            "error": "session_must_be_json_object",
            "candidate_graph_contamination_count": 0,
        }

    initial_state = session.get("initial_state")
    events = session.get("events")
    continuation_events = session.get("continuation_events", [])
    if (
        not isinstance(initial_state, dict)
        or not isinstance(events, list)
        or not isinstance(continuation_events, list)
    ):
        return 2, {
            "action": "invalid_input",
            "error": "initial_state_must_be_object_and_events_must_be_lists",
            "candidate_graph_contamination_count": 0,
        }

    if not all(isinstance(event, dict) for event in [*events, *continuation_events]):
        return 2, {
            "action": "invalid_input",
            "error": "events_must_be_json_objects",
            "candidate_graph_contamination_count": 0,
        }

    result = run_runtime_os_suite(
        case_id=str(session.get("case_id", "v10_runtime_os")),
        initial_state=initial_state,
        events=events,
        continuation_events=continuation_events,
    )
    result["action"] = "runtime_os_suite_completed"
    return 0, result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ts-runtime-os")
    sub = parser.add_subparsers(dest="command", required=True)

    session = sub.add_parser("session")
    session.add_argument("--session", required=True)

    suite = sub.add_parser("suite")
    suite.add_argument("--session", required=True)

    userspace = sub.add_parser("run-userspace")
    userspace.add_argument("--app", required=True)
    userspace.add_argument("--session", required=True)

    continuum = sub.add_parser("run-continuum")
    continuum.add_argument("--scenario", required=True)

    export_pack = sub.add_parser("export-pack")
    export_pack.add_argument("--session", required=True)
    export_pack.add_argument("--out", required=True)

    import_pack = sub.add_parser("import-pack")
    import_pack.add_argument("--pack", required=True)

    alpha = sub.add_parser("alpha")
    alpha.add_argument("--scenario", required=True)

    args = parser.parse_args(argv)

    try:
        input_arg = (
            getattr(args, "session", None)
            or getattr(args, "scenario", None)
            or getattr(args, "pack", None)
        )
        payload = load_json_arg(input_arg) if input_arg is not None else None
    except Exception as exc:
        print(
            json.dumps(
                {
                    "action": "invalid_input",
                    "error": str(exc),
                    "candidate_graph_contamination_count": 0,
                },
                sort_keys=True,
            )
        )
        return 2

    if args.command == "session":
        exit_code, output = run_session_payload(payload)
    elif args.command == "suite":
        exit_code, output = run_suite_payload(payload)
    elif args.command == "run-userspace":
        result = run_userspace_app(args.app, payload)
        output = {
            "action": result.action,
            "app_output": result.app_output,
            "decisions": [
                {
                    "action": decision.action,
                    "state_delta": decision.state_delta,
                    "verifier_gate": decision.verifier_gate,
                    "receipt": decision.receipt,
                }
                for decision in result.decisions
            ],
            "next_budget": result.next_budget,
            "receipt": result.receipt,
            "candidate_graph_contamination_count": 0,
        }
        exit_code = 0
    elif args.command == "run-continuum":
        report = run_continuum_scenario(payload)
        output = report.__dict__
        output["action"] = "continuum_completed"
        output["candidate_graph_contamination_count"] = report.contamination_count
        exit_code = 0
    elif args.command == "export-pack":
        initial_state = (
            payload.get("initial_state", payload) if isinstance(payload, dict) else {}
        )
        node = ProofGridNode(
            node_id=(
                str(payload.get("node_id", "local_node"))
                if isinstance(payload, dict)
                else "local_node"
            ),
            issuer=(
                str(payload.get("issuer", "local_issuer"))
                if isinstance(payload, dict)
                else "local_issuer"
            ),
            state=initial_state,
            manifest=(
                payload.get("channel_manifest", {}) if isinstance(payload, dict) else {}
            ),
        )
        output = node.export_pack()
        write_json(args.out, output)
        output = {
            "action": "proof_grid_pack_exported",
            "out": args.out,
            "pack": output,
            "candidate_graph_contamination_count": 0,
        }
        exit_code = 0
    elif args.command == "import-pack":
        node = ProofGridNode()
        decision = node.import_pack(payload)
        output = {
            "action": decision.action,
            "accepted_claims": list(decision.accepted_claims),
            "quarantined_claims": list(decision.quarantined_claims),
            "receipt": decision.receipt,
            "candidate_graph_contamination_count": 0,
        }
        exit_code = 0 if decision.action != "rejected" else 1
    elif args.command == "alpha":
        output = run_alpha_scenario(payload)
        exit_code = 0 if output["all_gates_passed"] else 1
    else:
        output = {
            "action": "invalid_input",
            "error": "unknown_command",
            "candidate_graph_contamination_count": 0,
        }
        exit_code = 2

    print(json.dumps(output, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
