"""Adversarial topology generators for v0.5 selector stress tests."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable

from thinking_system.benchmarks.graph_scaling.tasks.scaling import (
    CONTRADICTS,
    SUPPORT,
    Edge,
    GraphSpec,
    SyntheticGraph,
    build_adjacency,
    node_degrees,
)

PLACEMENTS = ["hub_hub", "hub_leaf", "leaf_leaf", "random"]
FAMILIES = ["mixed_core_periphery", "hub_threshold_sweep", "topology_noise_sweep"]


@dataclass(frozen=True)
class AdversarialSpec:
    family: str
    placement: str
    nodes: int
    seed: int
    hub_strength: float = 0.5
    noise_rate: float = 0.1


def generate_adversarial_graph(spec: AdversarialSpec) -> SyntheticGraph:
    if spec.family == "mixed_core_periphery":
        return mixed_core_periphery(spec)
    if spec.family == "hub_threshold_sweep":
        return hub_threshold_sweep(spec)
    if spec.family == "topology_noise_sweep":
        return topology_noise_sweep(spec)
    raise ValueError(f"unknown adversarial family: {spec.family}")


def mixed_core_periphery(spec: AdversarialSpec) -> SyntheticGraph:
    rng = random.Random(spec.seed)
    nodes = spec.nodes
    core_size = max(8, int(nodes * (0.12 + 0.18 * spec.hub_strength)))
    periphery_start = core_size
    values = [rng.uniform(-0.25, 0.25) for _ in range(nodes)]
    edges: list[Edge] = []

    edges.extend(preferential_edges(rng, start=0, end=core_size, links_per_node=3))
    edges.extend(
        ring_lattice_edges(rng, start=periphery_start, end=nodes, radius=2, rewire=0.06)
    )
    bridge_count = max(1, int(nodes * 0.02))
    for _ in range(bridge_count):
        src = rng.randrange(0, core_size)
        dst = rng.randrange(periphery_start, nodes)
        edges.append(support_edge(src, dst, rng))

    edges, contradiction_pairs = inject_placed_contradiction(
        rng, nodes, edges, values, spec.placement
    )
    return make_graph(spec, values, edges, contradiction_pairs)


def hub_threshold_sweep(spec: AdversarialSpec) -> SyntheticGraph:
    rng = random.Random(spec.seed)
    nodes = spec.nodes
    values = [rng.uniform(-0.25, 0.25) for _ in range(nodes)]
    edges: list[Edge] = []
    hub_count = max(2, int(nodes * (0.01 + 0.06 * spec.hub_strength)))
    target_edges = max(nodes * 3, nodes - 1)

    for node in range(hub_count, nodes):
        if rng.random() < spec.hub_strength:
            dst = rng.randrange(0, hub_count)
        else:
            dst = rng.randrange(0, node)
        if node != dst:
            edges.append(support_edge(node, dst, rng))
    while len(edges) < target_edges:
        src = rng.randrange(nodes)
        if rng.random() < spec.hub_strength:
            dst = rng.randrange(0, hub_count)
        else:
            dst = rng.randrange(nodes)
        if src != dst:
            edges.append(support_edge(src, dst, rng))

    edges = dedupe_edges(edges)
    edges, contradiction_pairs = inject_placed_contradiction(
        rng, nodes, edges, values, spec.placement
    )
    return make_graph(spec, values, edges, contradiction_pairs)


def topology_noise_sweep(spec: AdversarialSpec) -> SyntheticGraph:
    rng = random.Random(spec.seed)
    nodes = spec.nodes
    values = [rng.uniform(-0.25, 0.25) for _ in range(nodes)]
    if spec.hub_strength >= 0.5:
        edges = preferential_edges(rng, start=0, end=nodes, links_per_node=3)
    else:
        edges = ring_lattice_edges(rng, start=0, end=nodes, radius=3, rewire=0.08)

    replace_count = int(len(edges) * spec.noise_rate)
    for idx in rng.sample(range(len(edges)), k=min(replace_count, len(edges))):
        src = rng.randrange(nodes)
        dst = rng.randrange(nodes)
        if src != dst:
            edges[idx] = support_edge(src, dst, rng)

    edges = dedupe_edges(edges)
    edges, contradiction_pairs = inject_placed_contradiction(
        rng, nodes, edges, values, spec.placement
    )
    return make_graph(spec, values, edges, contradiction_pairs)


def preferential_edges(
    rng: random.Random, *, start: int, end: int, links_per_node: int
) -> list[Edge]:
    if end - start < 2:
        return []
    edges = [support_edge(start, start + 1, rng)]
    degree_bag = [start, start + 1]
    for node in range(start + 2, end):
        targets: set[int] = set()
        while len(targets) < min(links_per_node, node - start):
            targets.add(rng.choice(degree_bag))
        for target in targets:
            edges.append(support_edge(node, target, rng))
            degree_bag.extend([node, target])
    return edges


def ring_lattice_edges(
    rng: random.Random,
    *,
    start: int,
    end: int,
    radius: int,
    rewire: float,
) -> list[Edge]:
    edges: list[Edge] = []
    count = end - start
    if count < 2:
        return edges
    for offset_node in range(count):
        src = start + offset_node
        for offset in range(1, radius + 1):
            dst = start + ((offset_node + offset) % count)
            if rng.random() < rewire:
                dst = rng.randrange(start, end)
            if src != dst:
                edges.append(support_edge(src, dst, rng))
    return dedupe_edges(edges)


def inject_placed_contradiction(
    rng: random.Random,
    nodes: int,
    edges: list[Edge],
    values: list[float],
    placement: str,
) -> tuple[list[Edge], list[tuple[int, int]]]:
    degrees = degree_from_edges(nodes, edges)
    hubs = ranked_nodes(degrees, reverse=True)
    leaves = ranked_nodes(degrees, reverse=False)
    if placement == "hub_hub":
        src, dst = pick_pair(hubs[: max(2, len(hubs) // 10)], rng)
    elif placement == "hub_leaf":
        src = rng.choice(hubs[: max(1, len(hubs) // 10)])
        dst = rng.choice(leaves[: max(1, len(leaves) // 10)])
    elif placement == "leaf_leaf":
        src, dst = pick_pair(leaves[: max(2, len(leaves) // 10)], rng)
    elif placement == "random":
        src, dst = pick_pair(list(range(nodes)), rng)
    else:
        raise ValueError(f"unknown contradiction placement: {placement}")

    sign = 1.0 if rng.random() >= 0.5 else -1.0
    values[src] = sign * rng.uniform(0.65, 0.95)
    values[dst] = sign * rng.uniform(0.65, 0.95)
    updated = list(edges)
    updated.append(
        Edge(
            src=src,
            dst=dst,
            relation=CONTRADICTS,
            weight=rng.uniform(1.5, 2.5),
            provenance=f"synthetic_{placement}_contradiction",
        )
    )
    return updated, [(src, dst)]


def make_graph(
    spec: AdversarialSpec,
    values: list[float],
    edges: list[Edge],
    contradiction_pairs: list[tuple[int, int]],
) -> SyntheticGraph:
    edges = dedupe_edges(edges, keep_contradictions=True)
    graph_spec = GraphSpec(
        graph_type=spec.family,
        nodes=spec.nodes,
        edges=len(edges),
        seed=spec.seed,
        contradiction_pairs=contradiction_pairs,
    )
    return SyntheticGraph(
        spec=graph_spec,
        values=values,
        edges=edges,
        adjacency=build_adjacency(spec.nodes, edges),
    )


def support_edge(src: int, dst: int, rng: random.Random) -> Edge:
    return Edge(src=src, dst=dst, relation=SUPPORT, weight=rng.uniform(0.5, 1.0))


def dedupe_edges(
    edges: Iterable[Edge], keep_contradictions: bool = False
) -> list[Edge]:
    seen: set[tuple[int, int, str]] = set()
    result: list[Edge] = []
    for edge in edges:
        if edge.src == edge.dst:
            continue
        relation_key = edge.relation if keep_contradictions else SUPPORT
        key = (min(edge.src, edge.dst), max(edge.src, edge.dst), relation_key)
        if key in seen:
            continue
        seen.add(key)
        result.append(edge)
    return result


def degree_from_edges(nodes: int, edges: Iterable[Edge]) -> list[int]:
    degrees = [0 for _ in range(nodes)]
    for edge in edges:
        degrees[edge.src] += 1
        degrees[edge.dst] += 1
    return degrees


def ranked_nodes(degrees: list[int], *, reverse: bool) -> list[int]:
    return [
        idx
        for idx, _degree in sorted(
            enumerate(degrees), key=lambda row: row[1], reverse=reverse
        )
    ]


def pick_pair(candidates: list[int], rng: random.Random) -> tuple[int, int]:
    if len(candidates) < 2:
        raise ValueError("need at least two candidates")
    src = rng.choice(candidates)
    dst = rng.choice(candidates)
    while dst == src:
        dst = rng.choice(candidates)
    return src, dst
