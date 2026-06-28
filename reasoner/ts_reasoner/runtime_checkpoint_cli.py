from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ts_reasoner.runtime_checkpoint_restore import build_checkpoint, restore_checkpoint


def load_json_arg(value: str) -> Any:
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


def checkpoint_session(session: Any) -> tuple[int, dict[str, Any]]:
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

    result = build_checkpoint(
        case_id=str(session.get("case_id", "checkpoint_cli")),
        initial_state=initial_state,
        events=events,
    )

    payload = result.to_dict()
    payload["action"] = "checkpoint_created"
    return 0, payload


def restore_checkpoint_payload(checkpoint: Any) -> tuple[int, dict[str, Any]]:
    if not isinstance(checkpoint, dict):
        return 2, {
            "action": "invalid_input",
            "error": "checkpoint_must_be_json_object",
            "candidate_graph_contamination_count": 0,
        }

    try:
        restored_state = restore_checkpoint(checkpoint)
    except Exception as exc:
        return 2, {
            "action": "invalid_input",
            "error": str(exc),
            "candidate_graph_contamination_count": 0,
        }

    return 0, {
        "action": "checkpoint_restored",
        "restored_state": restored_state,
        "candidate_graph_contamination_count": checkpoint.get(
            "candidate_graph_contamination_count", 0
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ts-runtime-checkpoint")
    sub = parser.add_subparsers(dest="command", required=True)

    checkpoint = sub.add_parser("checkpoint")
    checkpoint.add_argument("--session", required=True)

    restore = sub.add_parser("restore")
    restore.add_argument("--checkpoint", required=True)

    args = parser.parse_args(argv)

    if args.command == "checkpoint":
        try:
            session = load_json_arg(args.session)
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

        exit_code, payload = checkpoint_session(session)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return exit_code

    if args.command == "restore":
        try:
            checkpoint_payload = load_json_arg(args.checkpoint)
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

        exit_code, payload = restore_checkpoint_payload(checkpoint_payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return exit_code

    print(
        json.dumps(
            {
                "action": "invalid_input",
                "error": "unknown_command",
                "candidate_graph_contamination_count": 0,
            },
            sort_keys=True,
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
