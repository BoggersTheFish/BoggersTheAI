from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from ..interface.runtime import BoggersRuntime


@dataclass(slots=True)
class TUIState:
    recent_events: deque[str]
    theme: str = "matrix"


def run_tui(runtime: "BoggersRuntime", stop_event: Event | None = None, theme: str = "matrix") -> None:
    console = Console()
    state = TUIState(recent_events=deque(maxlen=20), theme=theme)
    stop_event = stop_event or Event()

    with Live(_render(runtime, state), console=console, refresh_per_second=2) as live:
        while not stop_event.is_set():
            status = runtime.get_status()
            state.recent_events.appendleft(
                f"cycle={status.get('cycle_count')} tension={float(status.get('tension', 0.0)):.2f}"
            )
            live.update(_render(runtime, state))
            stop_event.wait(1.0)


def _render(runtime: "BoggersRuntime", state: TUIState):
    status = runtime.get_status()
    table = Table(title="BoggersTheAI TS-OS TUI", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Theme", state.theme)
    table.add_row("Wave thread", str(status.get("thread_alive")))
    table.add_row("Cycle count", str(status.get("cycle_count")))
    table.add_row("Nodes", str(status.get("nodes")))
    table.add_row("Edges", str(status.get("edges")))
    table.add_row("Tension", f"{float(status.get('tension', 0.0)):.2f}")
    table.add_row("Last cycle", str(status.get("last_cycle")))

    recent = "\n".join(list(state.recent_events)[:8]) or "No events yet."
    traces_count = len(list(Path("traces").glob("*.jsonl"))) if Path("traces").exists() else 0
    body = f"{table}\n\nRecent:\n{recent}\n\nTraces: {traces_count}"
    return Panel(body, border_style="green" if state.theme == "matrix" else "white")
