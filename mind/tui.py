from __future__ import annotations

import json
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


def run_tui(
    runtime: "BoggersRuntime", stop_event: Event | None = None, theme: str = "matrix"
) -> None:
    console = Console()
    state = TUIState(recent_events=deque(maxlen=20), theme=theme)
    stop_event = stop_event or Event()

    with Live(
        _render(runtime, state), console=console, refresh_per_second=8
    ) as live:
        while not stop_event.is_set():
            status = runtime.get_status()
            folded_n = len(runtime.graph.folded_wave_nodes())
            state.recent_events.appendleft(
                f"cycle={status.get('cycle_count')} "
                f"tension={float(status.get('tension', 0.0)):.2f} "
                f"folded={folded_n}"
            )
            live.update(_render(runtime, state))
            stop_event.wait(0.25)


def _render(runtime: "BoggersRuntime", state: TUIState) -> Panel:
    status = runtime.get_status()
    metrics = runtime.graph.get_metrics()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    table.add_row("Cycle", str(status.get("cycle_count", 0)))
    table.add_row("Tension", f"{float(status.get('tension', 0.0)):.3f}")
    table.add_row(
        "Nodes (active/total)",
        f"{metrics.get('active_nodes', 0)}/{metrics.get('total_nodes', 0)}",
    )
    table.add_row("Edges", str(metrics.get("edges", 0)))
    table.add_row("Avg Activation", f"{metrics.get('avg_activation', 0):.4f}")
    table.add_row("Avg Stability", f"{metrics.get('avg_stability', 0):.4f}")
    table.add_row("Edge Density", f"{metrics.get('edge_density', 0):.4f}")
    table.add_row("CPU DistilLoRA", _cpu_distillora_summary(runtime))
    table.add_row(
        "Folded wave nodes",
        str(len(runtime.graph.folded_wave_nodes())),
    )

    top_nodes = sorted(
        [n for n in runtime.graph.nodes.values() if not n.collapsed],
        key=lambda n: n.activation,
        reverse=True,
    )[:5]

    nodes_table = Table(
        show_header=True, header_style="bold green", title="Top Activated"
    )
    nodes_table.add_column("Node", max_width=30)
    nodes_table.add_column("Act", justify="right")
    nodes_table.add_column("Stab", justify="right")
    for n in top_nodes:
        label = n.topics[0] if n.topics else n.id[:20]
        bar = "█" * int(n.activation * 10) + "░" * (10 - int(n.activation * 10))
        nodes_table.add_row(label, f"{n.activation:.2f} {bar}", f"{n.stability:.2f}")

    events_text = (
        "\n".join(list(state.recent_events)[:8])
        if state.recent_events
        else "No events yet"
    )

    layout = Table.grid(padding=1)
    layout.add_row(table, nodes_table)
    layout.add_row(Panel(events_text, title="Recent Events", border_style="dim"), "")

    return Panel(
        layout,
        title=f"[bold]BoggersTheAI TUI[/bold] [{state.theme}]",
        border_style="blue",
    )


def _cpu_distillora_summary(runtime: "BoggersRuntime") -> str:
    try:
        base = Path(runtime.fine_tuner.config.adapter_save_path)
        p = base / "cpu_distillora_stats.json"
        if not p.exists():
            return "n/a (no stats file)"
        data = json.loads(p.read_text(encoding="utf-8"))
        sr = data.get("sample_run") or {}
        return (
            f"samples={data.get('train_samples_seen', '?')} "
            f"loss={sr.get('simulated_training_loss', '?')}"
        )
    except Exception:
        return "n/a"
