#!/usr/bin/env python3
"""
Phase 0 Perf Baseline (P0.6 in PHASE0_DETAIL_PLAN.md).
Self-contained minimal simulation of wave/rules dynamics.
"""

import json
import time
import tracemalloc
from pathlib import Path

print("[Phase 0] Perf baseline - self-contained simulation of core wave + rules dynamics")

EMERGENCE_MAX_SPAWN = 5

class MiniNode:
    def __init__(self, nid, content, topics=None):
        self.id = nid
        self.content = content
        self.activation = 0.2
        self.base_strength = 0.15
        self.stability = 0.6
        self.topics = set(topics or [])
        self.collapsed = False

class MiniGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_node(self, content="", topics=None):
        nid = f"n{len(self.nodes)}"
        self.nodes[nid] = MiniNode(nid, content, topics)
        return nid

    def add_edge(self, source_id, target_id, relation="is_a", weight=0.9):
        self.edges.append((source_id, target_id, weight))

def simulate_wave_step(nodes, edges):
    # propagate
    updates = {}
    for src, tgt, w in edges:
        if src in nodes:
            updates[tgt] = updates.get(tgt, 0.0) + nodes[src].activation * w * 0.12
    for nid, delta in updates.items():
        if nid in nodes:
            nodes[nid].activation = min(1.0, nodes[nid].activation + delta)
    # relax
    for n in nodes.values():
        n.activation = n.base_strength + (n.activation - n.base_strength) * 0.82
    # tensions
    tensions = {nid: abs(n.activation - n.base_strength) for nid, n in nodes.items()}
    # fake emergence
    high_t = [t for t in tensions.values() if t > 0.25]
    emergent = min(EMERGENCE_MAX_SPAWN, len(high_t))
    return {"tensions": tensions, "emergent": emergent, "max_tension": max(tensions.values() or [0])}

def make_synthetic_chain(n):
    g = MiniGraph()
    ids = []
    for i in range(n):
        nid = g.add_node(f"Node{i}", {f"t{i}"})
        ids.append(nid)
    for i in range(n-1):
        g.add_edge(ids[i], ids[i+1])
    return g

def run_baseline():
    results = {"phase": "0", "emergence_max_spawn": EMERGENCE_MAX_SPAWN, "timestamp": time.time(), "runs": []}
    sizes = [100, 1000, 5000, 10000]
    for sz in sizes:
        g = make_synthetic_chain(sz)
        nodes = {k: v for k, v in g.nodes.items()}
        edgs = list(g.edges)
        tracemalloc.start()
        t0 = time.perf_counter()
        last = None
        for _ in range(3):
            last = simulate_wave_step(nodes, edgs)
        dt = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        entry = {
            "nodes": sz,
            "3step_time_s": round(dt, 4),
            "peak_mem_mb": round(peak / 1024 / 1024, 2),
            "max_tension": round(last["max_tension"], 4),
            "emergent": last["emergent"]
        }
        results["runs"].append(entry)
        print(f"nodes={sz}: {entry['3step_time_s']}s, mem~{entry['peak_mem_mb']}MB, tension={entry['max_tension']}")

    out = Path("artifacts/phase0_perf_baseline.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nBaseline saved: {out}")
    return results

if __name__ == "__main__":
    run_baseline()
