from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ts_reasoner.runtime_replay import replay_events


def load_json_arg(value: str) -> Any:
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


def replay_session(session: Any) -> tuple[int, dict[str, Any]]:
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

    result = replay_events(
        case_id=str(session.get("case_id", "cli_replay")),
        initial_state=initial_state,
        events=events,
    )

    payload = result.to_dict()
    payload["action"] = "replay_completed"
    return 0, payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ts-runtime-replay")
    sub = parser.add_subparsers(dest="command", required=True)

    replay = sub.add_parser("replay")
    replay.add_argument("--session", required=True)

    args = parser.parse_args(argv)

    if args.command == "replay":
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

        exit_code, payload = replay_session(session)
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
