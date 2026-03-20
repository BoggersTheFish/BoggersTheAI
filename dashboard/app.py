from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse

from BoggersTheAI import BoggersRuntime

app = FastAPI(title="BoggersTheAI Dashboard", version="0.1.0")
runtime = BoggersRuntime()
_tension_history: list[dict[str, Any]] = []
_history_lock = threading.Lock()

_AUTH_TOKEN = os.environ.get("BOGGERS_DASHBOARD_TOKEN", "")


def _check_auth(authorization: str = Header(default="")) -> None:
    if _AUTH_TOKEN and authorization != f"Bearer {_AUTH_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _collect_status() -> dict[str, Any]:
    status = runtime.get_status()
    with _history_lock:
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
def status(_: None = Depends(_check_auth)) -> dict[str, Any]:
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


@app.get("/graph")
def graph(_: None = Depends(_check_auth)) -> dict[str, Any]:
    nodes = [
        {
            "id": n.id,
            "topics": n.topics,
            "activation": n.activation,
            "stability": n.stability,
            "collapsed": n.collapsed,
        }
        for n in runtime.graph.nodes.values()
    ]
    edges = [
        {"src": e.src, "dst": e.dst, "weight": e.weight} for e in runtime.graph.edges
    ]
    return {"nodes": nodes, "edges": edges}


@app.get("/graph/viz", response_class=HTMLResponse)
def graph_viz() -> str:
    return """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>BoggersTheAI Graph</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/sigma.js/2.4.0/sigma.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/graphology/0.25.4/graphology.umd.min.js"></script>
  <style>
    body { margin: 0; font-family: sans-serif; background: #1a1a2e; color: #eee; }
    #container { width: 100vw; height: 85vh; }
    #info { padding: 10px 20px; background: #16213e; }
    #details { position: fixed; top: 10px; right: 10px; background: #16213e; padding: 15px; border-radius: 8px; max-width: 350px; display: none; }
  </style>
</head>
<body>
  <div id="info"><b>BoggersTheAI Living Graph</b> | Click a node for details | Scroll to zoom</div>
  <div id="container"></div>
  <div id="details"></div>
  <script>
    const graph = new graphology.Graph();
    async function load() {
      const resp = await fetch("/graph");
      const data = await resp.json();
      data.nodes.forEach((n, i) => {
        const size = 3 + (n.activation || 0) * 12;
        const color = n.collapsed ? "#555" : (n.stability > 0.7 ? "#00d2ff" : "#ff6b6b");
        graph.addNode(n.id, {
          label: n.topics && n.topics[0] ? n.topics[0] : n.id.substring(0, 20),
          x: Math.cos(2 * Math.PI * i / data.nodes.length) * 100 + Math.random() * 50,
          y: Math.sin(2 * Math.PI * i / data.nodes.length) * 100 + Math.random() * 50,
          size: size,
          color: color,
          _data: n,
        });
      });
      data.edges.forEach((e, i) => {
        if (graph.hasNode(e.src) && graph.hasNode(e.dst)) {
          graph.addEdge(e.src, e.dst, { size: Math.max(0.5, e.weight * 2), color: "#334" });
        }
      });
      const renderer = new Sigma(graph, document.getElementById("container"), {
        renderLabels: true,
        labelColor: { color: "#ddd" },
        labelSize: 12,
      });
      renderer.on("clickNode", ({node}) => {
        const d = graph.getNodeAttributes(node)._data;
        const det = document.getElementById("details");
        det.style.display = "block";
        det.innerHTML = "<b>" + node + "</b><br>"
          + "Topics: " + (d.topics || []).join(", ") + "<br>"
          + "Activation: " + (d.activation || 0).toFixed(3) + "<br>"
          + "Stability: " + (d.stability || 0).toFixed(3) + "<br>"
          + "Collapsed: " + (d.collapsed || false) + "<br>"
          + "<hr><small>" + (d.id || "") + "</small>";
      });
    }
    load();
  </script>
</body>
</html>"""


@app.get("/metrics")
def metrics_endpoint(_: None = Depends(_check_auth)) -> dict[str, Any]:
    metrics = runtime.graph.get_metrics()
    wave_status = runtime.get_status()

    stability_trend: list[float] = []
    with _history_lock:
        for entry in _tension_history[-50:]:
            stability_trend.append(1.0 - entry.get("tension", 0.0))

    return {
        "graph": metrics,
        "wave": wave_status,
        "stability_trend": stability_trend,
        "tension_history_length": len(_tension_history),
    }


@app.get("/traces")
def traces(_: None = Depends(_check_auth), limit: int = 20) -> dict[str, Any]:
    traces_dir = Path("traces")
    if not traces_dir.exists():
        return {"traces": [], "count": 0}
    files = sorted(traces_dir.glob("*.jsonl"), reverse=True)[:limit]
    items = []
    for f in files:
        try:
            items.append(
                {"file": f.name, "content": f.read_text(encoding="utf-8").strip()}
            )
        except Exception:
            continue
    return {"traces": items, "count": len(items)}


def main() -> None:
    import uvicorn

    host = os.environ.get("BOGGERS_DASHBOARD_HOST", "0.0.0.0")
    port = int(os.environ.get("BOGGERS_DASHBOARD_PORT", "8000"))
    uvicorn.run("BoggersTheAI.dashboard.app:app", host=host, port=port, reload=False)
