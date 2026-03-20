from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from BoggersTheAI import BoggersRuntime

app = FastAPI(title="BoggersTheAI Dashboard", version="0.1.0")
runtime = BoggersRuntime()
_tension_history: list[dict[str, Any]] = []


def _collect_status() -> dict[str, Any]:
    status = runtime.get_status()
    _tension_history.append(
        {
            "cycle": int(status.get("cycle_count", 0)),
            "tension": float(status.get("tension", 0.0)),
        }
    )
    if len(_tension_history) > 300:
        del _tension_history[:-300]
    return status


@app.get("/status")
def status() -> dict[str, Any]:
    return {
        "status": _collect_status(),
        "graph": {
            "nodes": len(runtime.graph.nodes),
            "edges": len(runtime.graph.edges),
            "path": str(runtime.graph.graph_path),
        },
    }


@app.get("/wave", response_class=HTMLResponse)
def wave() -> str:
    _collect_status()
    return """<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>BoggersTheAI Wave Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  </head>
  <body>
    <h2>BoggersTheAI Wave Tension</h2>
    <canvas id="waveChart" width="900" height="360"></canvas>
    <script>
      const ctx = document.getElementById("waveChart").getContext("2d");
      const chart = new Chart(ctx, {
        type: "line",
        data: {
          labels: [],
          datasets: [{
            label: "Tension",
            data: [],
            borderWidth: 2,
            fill: false,
          }],
        },
        options: {
          responsive: true,
          animation: false,
          scales: {
            y: { beginAtZero: true, max: 1.5 },
          },
        },
      });

      async function tick() {
        const response = await fetch("/status");
        const payload = await response.json();
        const s = payload.status || {};
        chart.data.labels.push(s.cycle_count ?? 0);
        chart.data.datasets[0].data.push(s.tension ?? 0);
        if (chart.data.labels.length > 120) {
          chart.data.labels.shift();
          chart.data.datasets[0].data.shift();
        }
        chart.update();
      }

      tick();
      setInterval(tick, 2000);
    </script>
  </body>
</html>
"""


def main() -> None:
    import uvicorn

    uvicorn.run("dashboard.app:app", host="0.0.0.0", port=8000, reload=False)
