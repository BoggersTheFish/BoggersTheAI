"""Autonomous demo: run BoggersTheAI for a short period and observe evolution."""

from __future__ import annotations

import time

from BoggersTheAI import BoggersRuntime
from BoggersTheAI.interface.runtime import RuntimeConfig


def main() -> None:
    cfg = RuntimeConfig()
    cfg.wave = {
        "enabled": True,
        "interval_seconds": 5,
        "log_each_cycle": True,
        "auto_save": True,
    }
    cfg.os_loop = {
        "enabled": True,
        "interval_seconds": 10,
        "idle_threshold_seconds": 5,
        "autonomous_modes": ["exploration", "consolidation", "insight"],
    }
    cfg.tui = {"enabled": False}

    rt = BoggersRuntime(config=cfg)
    print("=== BoggersTheAI Autonomous Demo ===")
    print("Seeding initial knowledge...")

    rt.ask("What is wave propagation in graph networks?")
    rt.ask("Explain constraint satisfaction problems")
    rt.ask("How do emergent behaviors arise from local interactions?")

    print(f"\nGraph after seeding: {rt.graph.get_metrics()}")
    print("\nRunning autonomously for 60 seconds...")
    print("Watch the wave cycles and autonomous actions below:\n")

    time.sleep(60)

    print("\n=== Final State ===")
    print(f"Status: {rt.get_status()}")
    print(f"Metrics: {rt.graph.get_metrics()}")
    history = rt.get_conversation_history()
    print(f"Conversation turns: {len(history)}")

    rt.shutdown()
    print("Demo complete.")


if __name__ == "__main__":
    main()
