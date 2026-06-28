#!/usr/bin/env python3
"""
Phase 0 Unification Spike — First concrete action on the FRONTIER_PLAN.

This spike proves we can start bringing the *real* advanced pieces from your
codebase together for GPT-5.5 scale work:

- Deterministic transitive proof chains (directly from reasoner/ts_reasoner/proof_chain.py)
- Typed verifier support objects + hashing (from reasoner/ts_reasoner/typed_support.py)
- Living graph + wave/rules dynamics (core/graph/ + rules_engine.py)
- Full glass-box receipt

Because the monorepo has heavy package __init__ interdependencies, this spike
is deliberately self-contained for immediate execution while *faithfully*
reproducing the logic and spirit of the real modules (see source paths).

It shows the unification direction: ts_reasoner-level deterministic reasoning
becomes first-class inside the wave engine.

Run from the monorepo root:
  python3 experiments/frontier/phase0_unification_spike.py

Later phases will clean the package structure so we can `import` cleanly and
make the advanced verifier the default path (no more default LLM synthesis).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

# =============================================================================
# REAL LOGIC EXCERPTS (from your actual files — paths noted)
# =============================================================================


# From reasoner/ts_reasoner/proof_chain.py
# (small transitive proof-chain helpers for "all A are B" style)
class UniversalRelation:
    def __init__(
        self,
        quantifier: str,
        subject: str | None,
        predicate: str | None,
        text: str = "",
    ):
        self.quantifier = quantifier
        self.subject = subject
        self.predicate = predicate
        self.text = text


def universal_bridge_path(
    relations: Iterable[UniversalRelation], subject: str, predicate: str
) -> list[UniversalRelation]:
    """Return a shortest all/all transitive path from subject to predicate."""
    subject_key = subject.lower()
    predicate_key = predicate.lower()
    edges: dict[str, list[tuple[str, UniversalRelation]]] = {}
    for relation in relations:
        if (
            relation.quantifier != "all"
            or not relation.subject
            or not relation.predicate
        ):
            continue
        s = relation.subject.lower()
        p = relation.predicate.lower()
        edges.setdefault(s, []).append((p, relation))
    # BFS for shortest path
    from collections import deque

    q = deque([(subject_key, [])])
    seen = set()
    while q:
        current, path = q.popleft()
        if current in seen:
            continue
        seen.add(current)
        if current == predicate_key:
            return path
        for nxt, rel in edges.get(current, []):
            if nxt not in seen:
                q.append((nxt, path + [rel]))
    return []


# From reasoner/ts_reasoner/typed_support.py (simplified)
def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TypedSupportObject:
    support_type: str
    channel: str
    premises: tuple[str, ...]
    derived_claim: str
    verifier_passed: bool
    trace_hash: str = ""

    def to_dict(self):
        return asdict(self)


# Minimal graph + wave (distilled from core/graph/universal_living_graph.py + rules_engine.py + wave_propagation)
# This is the "physics" part. In full unification we call the real classes.


@dataclass
class Node:
    id: str
    content: str
    activation: float = 0.2
    base_strength: float = 0.15
    stability: float = 0.6
    topics: set = field(default_factory=set)


@dataclass
class Edge:
    source: str
    target: str
    relation: str
    weight: float = 0.9


class MiniGraph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []

    def add_node(self, content: str, topics=None):
        nid = "n:" + hashlib.md5(content.encode()).hexdigest()[:8]
        n = Node(nid, content, topics=set(topics or []))
        self.nodes[nid] = n
        return nid

    def add_is_a(self, subj_id: str, pred_id: str):
        self.edges.append(Edge(subj_id, pred_id, "is_a", 0.95))

    def propagate(self, spread=0.15, damping=0.88):
        updates = {}
        for e in self.edges:
            src = self.nodes.get(e.source)
            if src and not getattr(src, "collapsed", False):
                updates[e.target] = (
                    updates.get(e.target, 0.0)
                    + src.activation * e.weight * spread * damping
                )
        for nid, delta in updates.items():
            if nid in self.nodes:
                self.nodes[nid].activation = min(
                    1.0, self.nodes[nid].activation + delta
                )

    def relax(self, decay=0.82):
        for n in self.nodes.values():
            n.activation = n.base_strength + (n.activation - n.base_strength) * decay

    def compute_tension(self):
        return {
            nid: abs(n.activation - n.base_strength) for nid, n in self.nodes.items()
        }

    def run_waves(self, steps=3):
        logs = []
        for s in range(steps):
            self.propagate()
            self.relax()
            tens = self.compute_tension()
            logs.append(
                {
                    "step": s,
                    "max_tension": round(max(tens.values() or [0]), 4),
                    "strongest": max(
                        self.nodes.values(), key=lambda x: x.activation
                    ).content,
                }
            )
        return logs

    def summary(self):
        strongest = max(self.nodes.values(), key=lambda x: x.activation)
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "strongest": strongest.content,
        }


# =============================================================================
# THE SPIKE
# =============================================================================


def main():
    print("=== TS FRONTIER Phase 0 Unification Spike ===")
    print(
        "Synthesizing: proof_chain (ts_reasoner) + typed_support (ts_reasoner) + wave physics (core/graph)\n"
    )

    g = MiniGraph()

    # Seed facts (in real system this comes from TSLC / ts_chat compiler)
    facts = [
        ("whale", "mammal"),
        ("mammal", "animal"),
        ("animal", "mortal"),
    ]
    node_map = {}
    for subj, pred in facts:
        nid = g.add_node(f"{subj.capitalize()}", topics={subj})
        pid = g.add_node(f"{pred.capitalize()}", topics={pred})
        g.add_is_a(nid, pid)
        node_map[subj] = nid
        node_map[pred] = pid

    print("Seeded graph from facts:")
    for s, p in facts:
        print(f"  all {s} are {p}")

    # Run real-style waves
    print("\nRunning wave cycles (core/graph/rules_engine style)...")
    wave_logs = g.run_waves(4)
    for log in wave_logs:
        print(
            f"  step {log['step']}: max_tension={log['max_tension']}, strongest≈{log['strongest']}"
        )

    # Build relations for proof_chain (real logic)
    relations = []
    for e in g.edges:
        s_node = g.nodes[e.source]
        t_node = g.nodes[e.target]
        relations.append(
            UniversalRelation(
                "all",
                s_node.content.lower(),
                t_node.content.lower(),
                f"all {s_node.content} are {t_node.content}",
            )
        )

    # Use the *real* proof_chain algorithm
    print(
        "\nRunning universal_bridge_path from reasoner/ts_reasoner/proof_chain.py ..."
    )
    chain = universal_bridge_path(relations, "whale", "mortal")
    chain_texts = [r.text for r in chain]
    print(f"  Chain found: {chain_texts}")

    # Verifier using real typed support pattern
    support = TypedSupportObject(
        support_type="transitive_universal",
        channel="transitive_all",
        premises=tuple(chain_texts),
        derived_claim="whales are mortal",
        verifier_passed=bool(chain),
        trace_hash=canonical_hash({"chain": chain_texts}),
    )
    print(
        f"\nTyped verifier (reasoner/ts_reasoner/typed_support.py style): passed={support.verifier_passed}"
    )

    # Full receipt
    receipt = {
        "spike": "phase0_unification_001",
        "facts": facts,
        "wave_trace": wave_logs,
        "deterministic_chain": chain_texts,
        "verifier": support.to_dict(),
        "graph_final": g.summary(),
        "timestamp": time.time(),
    }

    print("\n=== GLASS-BOX RECEIPT (full trace) ===")
    print(json.dumps(receipt, indent=2))

    out = Path("artifacts/phase0_unification_receipt.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2))
    print(f"\nReceipt saved to {out}")

    print("\nPhase 0 spike complete. This is the shape of the real system:")
    print(
        "- Deterministic reasoning (proof_chain) + physics (waves) + verifier receipts"
    )
    print("- No black box. Everything inspectable.")
    print(
        "Next in plan: make ts_reasoner components native, scale emergence/dynamics, remove LLM default."
    )


if __name__ == "__main__":
    main()
