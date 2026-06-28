"""
Scale Probe for Wave 0: 10k-20k node graphs

Uses minimal graph sim for speed (real graph import issues).
Measures time, tension convergence, memory for large synthetic graphs.
Reports bottlenecks.
"""

import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class ScaleGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = []

    def add_node(self, content):
        nid = len(self.nodes)
        self.nodes[nid] = {"id": nid, "content": content, "activation": 0.2}
        return nid

    def add_edge(self, s, t):
        self.edges.append((s, t))

    def run_waves(self, steps=5):
        for _ in range(steps):
            updates = {}
            for s, t in self.edges:
                if s in self.nodes:
                    delta = self.nodes[s]["activation"] * 0.1
                    updates[t] = updates.get(t, 0) + delta
            for nid, d in updates.items():
                self.nodes[nid]["activation"] = min(
                    1.0, self.nodes[nid]["activation"] + d
                )

    def detect_tensions(self):
        return {nid: abs(n["activation"] - 0.2) for nid, n in self.nodes.items()}


def probe(max_nodes=10000):
    g = ScaleGraph()
    for i in range(max_nodes):
        g.add_node(f"node_{i}")
        if i > 0:
            g.add_edge(i - 1, i)
    start = time.time()
    tracemalloc.start()
    g.run_waves(5)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed = time.time() - start
    max_t = max(g.detect_tensions().values())
    print(f"Nodes: {max_nodes}")
    print(f"Time for 5 waves: {elapsed:.2f}s")
    print(f"Peak mem: {peak / 1024 / 1024:.2f} MB")
    print(f"Final max tension: {max_t:.4f}")
    return {
        "nodes": max_nodes,
        "time": elapsed,
        "peak_mb": peak / 1e6,
        "max_tension": max_t,
    }


if __name__ == "__main__":
    for n in [1000, 5000, 10000, 20000]:
        probe(n)
