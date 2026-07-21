from __future__ import annotations

import json
import sys
from pathlib import Path

from .runtime import BoggersRuntime


def run_chat(runtime: BoggersRuntime | None = None) -> None:
    if len(sys.argv) >= 3 and sys.argv[1:3] == ["kernel", "demo"]:
        from core.kernel.demo import main as kernel_demo_main

        raise SystemExit(kernel_demo_main(sys.argv[3:]))
    if len(sys.argv) >= 3 and sys.argv[1:3] == ["kernel", "run-seeds"]:
        from experiments.frontier.run_seed_tasks import main as run_seeds_main

        raise SystemExit(run_seeds_main(sys.argv[3:]))
    if len(sys.argv) >= 3 and sys.argv[1:3] == ["kernel", "replay"]:
        if len(sys.argv) < 4:
            raise SystemExit("usage: boggers kernel replay RECEIPT_JSON")
        receipt = _load_receipt(sys.argv[3])
        replay_verified, post_hash, error = _replay_receipt_from_empty_graph(receipt)
        if not replay_verified:
            print(f"ERROR: replay failed: {error}")
            raise SystemExit(1)
        print("REPLAY_VERIFIED: true")
        print(f"POST_HASH: {post_hash}")
        raise SystemExit(0)
    if len(sys.argv) >= 3 and sys.argv[1:3] == ["kernel", "audit"]:
        from core.kernel.receipts import validate_receipt_hash
        from core.trace_processor import TraceProcessor

        if len(sys.argv) < 4:
            raise SystemExit("usage: boggers kernel audit RECEIPT_JSON")
        receipt = _load_receipt(sys.argv[3])
        required = [
            item
            for item in receipt.get("verifier_obligations", [])
            if item.get("required", True)
        ]
        failures = _mandatory_obligation_failures(receipt)
        replay_verified, post_hash, replay_error = _replay_receipt_from_empty_graph(
            receipt
        )
        hash_valid = validate_receipt_hash(receipt)
        training_eligible = TraceProcessor()._is_training_eligible(
            {"receipt": receipt, "replay_verified": replay_verified}
        )
        decision = str(receipt.get("commit_decision", "unknown"))

        print(f"DECISION: {decision}")
        print(f"RECEIPT_HASH: {receipt.get('receipt_hash', '')}")
        print(f"HASH_VALID: {str(hash_valid).lower()}")
        print(f"REPLAY_VERIFIED: {str(replay_verified).lower()}")
        if replay_verified:
            print(f"POST_HASH: {post_hash}")
        else:
            print(f"REPLAY_ERROR: {replay_error}")
        replay_metadata = receipt.get("renderer_metadata", {}).get(
            "replay_verified", False
        )
        print(f"REPLAY_METADATA: {replay_metadata}")
        print(f"REQUIRED_OBLIGATIONS: {len(required)}")
        print(f"FAILED_MANDATORY_OBLIGATIONS: {', '.join(failures) or 'none'}")
        bogvm_artifacts = receipt.get("BOGVM_artifacts", [])
        print(f"BOGVM_ARTIFACTS: {len(bogvm_artifacts)}")
        for index, artifact in enumerate(bogvm_artifacts, start=1):
            print(
                f"BOGVM_ARTIFACT_{index}: "
                f"execution_completed={artifact.get('execution_completed')} "
                f"proof_obligation_satisfied={artifact.get('proof_obligation_satisfied')} "
                f"state_commit_authorized={artifact.get('state_commit_authorized')}"
            )
        print(f"TRAINING_ELIGIBLE: {str(training_eligible).lower()}")
        if not hash_valid or not replay_verified:
            raise SystemExit(1)
        if decision == "commit" and failures:
            raise SystemExit(1)
        raise SystemExit(0)

    rt = runtime or BoggersRuntime()
    print("BoggersTheAI chat interface. Type 'help' for commands, 'exit' to quit.")
    while True:
        query = input("> ").strip()
        if not query:
            continue
        cmd = query.lower()
        if cmd in {"exit", "quit"}:
            rt.shutdown()
            break
        if cmd in {"help", "/help"}:
            print("Commands:")
            print("  status      - Wave engine status")
            print("  graph stats - Graph metrics and topology summary")
            print("  trace show  - Show last reasoning trace")
            print("  wave pause  - Pause background wave")
            print("  wave resume - Resume background wave")
            print("  improve     - Trigger self-improvement cycle")
            print("  health      - Run system health checks")
            print("  history     - Show conversation history")
            print("  help        - Show this help")
            print("  exit        - Quit")
            continue
        if cmd in {"status", "/status"}:
            status = rt.get_status()
            print("Wave status:")
            print(
                f"  cycle_count: {status.get('cycle_count')} | "
                f"thread_alive: {status.get('thread_alive')} | "
                f"nodes: {status.get('nodes')} | edges: {status.get('edges')} | "
                f"tension: {float(status.get('tension', 0)):.2f} | "
                f"last_cycle: {status.get('last_cycle')}"
            )
            continue
        if cmd in {"graph stats", "graph", "/graph"}:
            metrics = rt.graph.get_metrics()
            print("Graph metrics:")
            print(
                f"  Nodes: {metrics['active_nodes']} active / "
                f"{metrics['total_nodes']} total"
            )
            print(
                f"  Edges: {metrics['edges']} | Density: {metrics['edge_density']:.4f}"
            )
            print(f"  Avg activation: {metrics['avg_activation']:.4f}")
            print(f"  Avg stability:  {metrics['avg_stability']:.4f}")
            top_topics = sorted(
                metrics.get("topics", {}).items(), key=lambda x: x[1], reverse=True
            )[:10]
            if top_topics:
                print(f"  Top topics: {', '.join(f'{t}({c})' for t, c in top_topics)}")
            continue
        if cmd in {"trace show", "trace", "/trace"}:
            traces_dir = Path("traces")
            if traces_dir.exists():
                files = sorted(traces_dir.glob("*.jsonl"), reverse=True)
                if files:
                    content = files[0].read_text(encoding="utf-8").strip()
                    print(f"Latest trace ({files[0].name}):")
                    print(content[:500])
                else:
                    print("No traces found.")
            else:
                print("Traces directory not found.")
            continue
        if cmd in {"wave pause", "/wave pause"}:
            rt.graph.stop_background_wave()
            print("Wave engine paused.")
            continue
        if cmd in {"wave resume", "/wave resume"}:
            rt.graph.start_background_wave()
            print("Wave engine resumed.")
            continue
        if cmd in {"improve", "/improve"}:
            print("Running self-improvement check...")
            result = rt.trigger_self_improvement()
            print(f"Result: {result}")
            continue
        if cmd in {"health", "/health"}:
            result = rt.run_health_checks()
            print(f"Health: {result.get('overall', 'unknown')}")
            for name, check in result.get("checks", {}).items():
                status = "OK" if check.get("healthy") else "FAIL"
                print(f"  {name}: {status} ({check.get('duration_ms', 0)}ms)")
            continue
        if cmd in {"history", "/history"}:
            history = rt.get_conversation_history()
            if not history:
                print("No conversation history.")
            else:
                for item in history:
                    print(
                        f"  [{item.get('timestamp', '?')}] "
                        f"{item.get('content', '')[:120]}"
                    )
            continue
        try:
            response = rt.ask(query)
            print(response.answer)
        except Exception as exc:
            print(f"Error: {exc}")


def _load_receipt(path_arg: str) -> dict:
    path = Path(path_arg)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"ERROR: cannot read receipt {path}: {exc}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON receipt {path}: {exc}") from None
    if not isinstance(payload, dict):
        raise SystemExit(f"ERROR: receipt {path} must contain a JSON object")
    return payload


def _replay_receipt_from_empty_graph(receipt: dict) -> tuple[bool, str, str]:
    from core.graph.universal_living_graph import UniversalLivingGraph
    from core.kernel.replay import replay_receipt

    try:
        post_hash = replay_receipt(UniversalLivingGraph(auto_load=False), receipt)
    except Exception as exc:
        return False, "", f"{exc.__class__.__name__}: {exc}"
    return True, post_hash, ""


def _mandatory_obligation_failures(receipt: dict) -> list[str]:
    obligations = [
        item
        for item in receipt.get("verifier_obligations", [])
        if item.get("required", True)
    ]
    results_by_obligation: dict[str, list[dict]] = {}
    for result in receipt.get("verification_results", []):
        results_by_obligation.setdefault(
            str(result.get("obligation_id", "")), []
        ).append(result)

    failures: list[str] = []
    for obligation in obligations:
        obligation_id = str(obligation.get("id", ""))
        results = results_by_obligation.get(obligation_id, [])
        if not results:
            failures.append(f"{obligation_id}:missing")
        elif len(results) > 1:
            failures.append(f"{obligation_id}:duplicate")
        elif results[0].get("outcome") != "pass":
            failures.append(f"{obligation_id}:{results[0].get('outcome', 'unknown')}")
    return failures
