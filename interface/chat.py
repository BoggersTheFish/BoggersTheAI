from __future__ import annotations

from .runtime import BoggersRuntime


def run_chat(runtime: BoggersRuntime | None = None) -> None:
    rt = runtime or BoggersRuntime()
    print("BoggersTheAI chat interface. Type 'exit' to quit.")
    while True:
        query = input("> ").strip()
        if query.lower() in {"exit", "quit"}:
            rt.shutdown()
            break
        if query.lower() in {"status", "/status"}:
            status = rt.get_status()
            print("Wave status:")
            print(
                f"- cycle_count: {status.get('cycle_count')} | "
                f"thread_alive: {status.get('thread_alive')} | "
                f"nodes: {status.get('nodes')} | edges: {status.get('edges')} | "
                f"tension: {status.get('tension'):.2f} | last_cycle: {status.get('last_cycle')}"
            )
            continue
        response = rt.ask(query)
        print(response.answer)
