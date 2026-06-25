"""Small transitive proof-chain helpers.

This module intentionally stays narrow: v0.9 only recognizes positive
universal chains of the form all A are B, all B are C, ..., all Y are Z.
"""

from __future__ import annotations

from collections import deque
from typing import Iterable, Protocol


class UniversalRelation(Protocol):
    quantifier: str
    subject: str | None
    predicate: str | None
    text: str


def universal_bridge_path(
    relations: Iterable[UniversalRelation],
    subject: str,
    predicate: str,
) -> list[UniversalRelation]:
    """Return a shortest all/all transitive path from subject to predicate."""
    subject_key = subject.lower()
    predicate_key = predicate.lower()
    edges: dict[str, list[tuple[str, UniversalRelation]]] = {}
    for relation in relations:
        if relation.quantifier != "all" or not relation.subject or not relation.predicate:
            continue
        edges.setdefault(relation.subject.lower(), []).append((relation.predicate.lower(), relation))

    queue: deque[tuple[str, list[UniversalRelation]]] = deque([(subject_key, [])])
    seen = {subject_key}
    while queue:
        node, path = queue.popleft()
        for next_node, relation in edges.get(node, []):
            next_path = [*path, relation]
            if next_node == predicate_key:
                return next_path
            if next_node not in seen:
                seen.add(next_node)
                queue.append((next_node, next_path))
    return []


def has_universal_bridge(
    relations: Iterable[UniversalRelation],
    subject: str,
    predicate: str,
) -> bool:
    return bool(universal_bridge_path(relations, subject, predicate))
