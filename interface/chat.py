from __future__ import annotations

from .runtime import BoggersRuntime


def run_chat(runtime: BoggersRuntime | None = None) -> None:
    rt = runtime or BoggersRuntime()
    print("BoggersTheAI chat interface. Type 'exit' to quit.")
    while True:
        query = input("> ").strip()
        if query.lower() in {"exit", "quit"}:
            break
        response = rt.ask(query)
        print(response.answer)
