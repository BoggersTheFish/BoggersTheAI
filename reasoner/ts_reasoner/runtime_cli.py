from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ts_reasoner.runtime_kernel import VerifierFirstRuntimeKernel


def load_json_arg(value: str) -> Any:
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


def process_event(event: Any, state: Any, case_id: str = "cli") -> tuple[int, dict[str, Any]]:
    if not isinstance(event, dict) or not isinstance(state, dict):
        return 2, {
            "action": "invalid_input",
            "error": "event_and_state_must_be_json_objects",
            "candidate_graph_contamination_count": 0,
        }

    kernel = VerifierFirstRuntimeKernel()
    result = kernel.process_event(event=event, state=state, case_id=case_id)
    return 0, result.to_dict()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ts-runtime")
    sub = parser.add_subparsers(dest="command", required=True)

    process = sub.add_parser("process-event")
    process.add_argument("--event", required=True)
    process.add_argument("--state", required=True)
    process.add_argument("--case-id", default="cli")

    args = parser.parse_args(argv)

    if args.command == "process-event":
        try:
            event = load_json_arg(args.event)
            state = load_json_arg(args.state)
        except Exception as exc:
            print(json.dumps({
                "action": "invalid_input",
                "error": str(exc),
                "candidate_graph_contamination_count": 0,
            }, sort_keys=True))
            return 2

        exit_code, payload = process_event(event=event, state=state, case_id=args.case_id)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return exit_code

    print(json.dumps({
        "action": "invalid_input",
        "error": "unknown_command",
        "candidate_graph_contamination_count": 0,
    }, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
