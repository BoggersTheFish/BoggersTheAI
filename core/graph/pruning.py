from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

from ..types import Node

logger = logging.getLogger("boggers.graph.pruning")


@dataclass
class PruningPolicy:
    min_stability: float = 0.1
    max_age_waves: int = 500
    max_nodes: int = 10000
    archive_collapsed: bool = True


def apply_pruning_policy(
    nodes: Dict[str, Node],
    policy: PruningPolicy,
    current_wave: int = 0,
) -> list[str]:
    collapsed_ids: list[str] = []
    for node in nodes.values():
        if node.collapsed:
            continue
        if node.stability < policy.min_stability:
            node.collapsed = True
            node.activation = 0.0
            collapsed_ids.append(node.id)
            logger.debug(
                "Pruned node %s: stability %.3f < %.3f",
                node.id,
                node.stability,
                policy.min_stability,
            )
            continue
        if (
            policy.max_age_waves > 0
            and current_wave - node.last_wave > policy.max_age_waves
        ):
            node.collapsed = True
            node.activation = 0.0
            collapsed_ids.append(node.id)
            logger.debug(
                "Pruned node %s: age %d > %d waves",
                node.id,
                current_wave - node.last_wave,
                policy.max_age_waves,
            )

    active_count = sum(1 for n in nodes.values() if not n.collapsed)
    if active_count > policy.max_nodes:
        by_priority = sorted(
            [n for n in nodes.values() if not n.collapsed],
            key=lambda n: (n.activation * n.stability, n.base_strength),
        )
        excess = active_count - policy.max_nodes
        for node in by_priority[:excess]:
            node.collapsed = True
            node.activation = 0.0
            collapsed_ids.append(node.id)
        logger.info("Cap pruned %d nodes to stay under %d", excess, policy.max_nodes)

    return collapsed_ids
