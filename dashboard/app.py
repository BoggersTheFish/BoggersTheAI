from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse

from BoggersTheAI import BoggersRuntime
from BoggersTheAI.core.metrics import metrics as metrics_collector

app = FastAPI(title="BoggersTheAI Dashboard", version="0.5.0")

_runtime: BoggersRuntime | None = None
_runtime_lock = threading.Lock()


def get_runtime() -> BoggersRuntime:
    global _runtime
    if _runtime is None:
        with _runtime_lock:
            if _runtime is None:
                _runtime = BoggersRuntime()
    return _runtime


_tension_history: list[dict[str, Any]] = []
_history_lock = threading.Lock()

_AUTH_TOKEN = os.environ.get("BOGGERS_DASHBOARD_TOKEN", "")
_logger = logging.getLogger("boggers.dashboard")


def _check_auth(authorization: str = Header(default="")) -> None:
    if _AUTH_TOKEN and authorization != f"Bearer {_AUTH_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _read_cpu_distillora_stats() -> dict[str, Any] | None:
    try:
        ft = get_runtime().fine_tuner
        p = Path(ft.config.adapter_save_path) / "cpu_distillora_stats.json"
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _collect_status() -> dict[str, Any]:
    status = get_runtime().get_status()
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


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready(
    _: None = Depends(_check_auth),
) -> dict[str, Any]:
    checks = get_runtime().run_health_checks()
    return {"status": "ready", "checks": checks}


@app.get("/status")
def status(
    _: None = Depends(_check_auth),
) -> dict[str, Any]:
    return {
        "status": _collect_status(),
        "graph": {
            "nodes": len(get_runtime().graph.nodes),
            "edges": len(get_runtime().graph.edges),
            "path": str(get_runtime().graph.graph_path),
        },
    }


@app.get("/wave", response_class=HTMLResponse)
def wave() -> str:
    _collect_status()
    return r"""<!doctype html>
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

      const _token = document.cookie.replace(
        /(?:(?:^|.*;\s*)boggers_token\s*=\s*([^;]*).*$)|^.*$/,
        "$1",
      );
      const _hdrs = _token ? { "Authorization": "Bearer " + _token } : {};
      async function tick() {
        const response = await fetch("/status", { headers: _hdrs });
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
            "folded_wave": (
                1
                if (n.id.startswith("meta:") or "waves_jsonl" in n.topics)
                else 0
            ),
        }
        for n in get_runtime().graph.nodes.values()
    ]
    edges = [
        {"src": e.src, "dst": e.dst, "weight": e.weight}
        for e in get_runtime().graph.edges
    ]
    return {"nodes": nodes, "edges": edges}


@app.get("/graph/viz", response_class=HTMLResponse)
def graph_viz(_: None = Depends(_check_auth)) -> str:
    return r"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>BoggersTheAI Living Graph</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
  <style>
    body { margin: 0; font-family: sans-serif; background: #1a1a2e; color: #eee; }
    #cy { width: 100vw; height: 90vh; }
    #info { padding: 8px 20px; background: #16213e; font-size: 14px; }
    #details {
      position: fixed;
      top: 10px;
      right: 10px;
      background: #16213e;
      padding: 15px;
      border-radius: 8px;
      max-width: 350px;
      display: none;
      z-index: 10;
      font-size: 13px;
    }
  </style>
</head>
<body>
  <div id="info">
    <b>BoggersTheAI Living Graph</b> | Click a node for details | Scroll to zoom |
    Drag to pan
  </div>
  <div id="cy"></div>
  <div id="details"></div>
  <script>
    let cy = null;
    const POLL_MS = 2500;
    function graphAuthHeaders() {
      const _token = document.cookie.replace(
        /(?:(?:^|.*;\s*)boggers_token\s*=\s*([^;]*).*$)|^.*$/,
        "$1",
      );
      return _token ? { "Authorization": "Bearer " + _token } : {};
    }
    function buildElements(data) {
      const elements = [];
      data.nodes.forEach(n => {
        elements.push({
          data: {
            id: n.id,
            label: n.topics && n.topics[0] ? n.topics[0] : n.id.substring(0, 20),
            activation: n.activation || 0,
            stability: n.stability || 0,
            collapsed: n.collapsed || false,
            topics: (n.topics || []).join(", "),
            folded_wave: n.folded_wave || 0,
          }
        });
      });
      data.edges.forEach((e, i) => {
        elements.push({
          data: {
            id: "e" + i + "_" + e.src + "_" + e.dst,
            source: e.src,
            target: e.dst,
            weight: e.weight || 0.5,
          }
        });
      });
      return elements;
    }
    function wireCyHandlers(instance) {
      instance.on("tap", "node", function(evt) {
        const d = evt.target.data();
        const det = document.getElementById("details");
        det.style.display = "block";
        det.innerHTML = "<b>" + d.id + "</b><br>"
          + "Topics: " + d.topics + "<br>"
          + "Activation: " + (d.activation).toFixed(3) + "<br>"
          + "Stability: " + (d.stability).toFixed(3) + "<br>"
          + "Collapsed: " + d.collapsed + "<br>"
          + (d.folded_wave
            ? "<i>Folded waves.jsonl node — inspect graph DB</i>"
            : "");
      });
      instance.on("tap", function(evt) {
        if (evt.target === instance) {
          document.getElementById("details").style.display = "none";
        }
      });
    }
    async function refreshGraph() {
      const resp = await fetch("/graph", { headers: graphAuthHeaders() });
      const data = await resp.json();
      const elements = buildElements(data);
      const info = document.getElementById("info");
      info.textContent =
        "BoggersTheAI Living Graph | nodes " + data.nodes.length
        + " | edges " + data.edges.length + " | polling " + POLL_MS + "ms";
      if (cy) {
        cy.destroy();
        cy = null;
      }
      cy = cytoscape({
        container: document.getElementById("cy"),
        elements: elements,
        style: [
          { selector: "node", style: {
            "label": "data(label)",
            "width": "mapData(activation, 0, 1, 20, 60)",
            "height": "mapData(activation, 0, 1, 20, 60)",
            "background-color": "mapData(stability, 0, 1, #ff6b6b, #00d2ff)",
            "color": "#ddd", "font-size": "10px",
            "text-valign": "bottom", "text-halign": "center",
            "border-width": 1, "border-color": "#334",
          }},
          {
            selector: "node[?collapsed]",
            style: { "background-color": "#555", "opacity": 0.4 },
          },
          {
            selector: "node[folded_wave = 1]",
            style: {
              "background-color": "#a855f7",
              "border-width": 3,
              "border-color": "#e9d5ff",
            },
          },
          { selector: "edge", style: {
            "width": "mapData(weight, 0, 1, 0.5, 4)",
            "line-color": "#334", "curve-style": "bezier",
            "target-arrow-shape": "triangle", "target-arrow-color": "#445",
            "arrow-scale": 0.6,
          }},
        ],
        layout: {
          name: "cose",
          animate: false,
          nodeRepulsion: 8000,
          idealEdgeLength: 80,
        },
      });
      wireCyHandlers(cy);
    }
    refreshGraph();
    setInterval(refreshGraph, POLL_MS);
  </script>
</body>
</html>"""


@app.get("/metrics")
def metrics_endpoint(_: None = Depends(_check_auth)) -> dict[str, Any]:
    graph_metrics = get_runtime().graph.get_metrics()
    wave_status = get_runtime().get_status()

    stability_trend: list[float] = []
    with _history_lock:
        for entry in _tension_history[-50:]:
            stability_trend.append(1.0 - entry.get("tension", 0.0))

    rt = get_runtime()
    folded = rt.graph.folded_wave_nodes()
    return {
        "graph": graph_metrics,
        "wave": wave_status,
        "stability_trend": stability_trend,
        "tension_history_length": len(_tension_history),
        "system": metrics_collector.snapshot(),
        "cpu_distillora": _read_cpu_distillora_stats(),
        "folded_wave_nodes": folded[:80],
        "folded_wave_count": len(folded),
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

    # Default localhost-only; use BOGGERS_DASHBOARD_HOST=0.0.0.0 in production
    # behind a reverse proxy so the app listens on all interfaces explicitly.
    host = os.environ.get("BOGGERS_DASHBOARD_HOST", "127.0.0.1")
    port = int(os.environ.get("BOGGERS_DASHBOARD_PORT", "8000"))
    if not os.environ.get("BOGGERS_DASHBOARD_TOKEN"):
        _logger.warning("Dashboard running without authentication token")
    uvicorn.run("BoggersTheAI.dashboard.app:app", host=host, port=port, reload=False)
