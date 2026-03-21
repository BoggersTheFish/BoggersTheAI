from __future__ import annotations

from .runtime import BoggersRuntime


def run_chat(runtime: BoggersRuntime | None = None) -> None:
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
            from pathlib import Path

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
