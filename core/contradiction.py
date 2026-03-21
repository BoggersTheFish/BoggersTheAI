from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Set

logger = logging.getLogger("boggers.contradiction")


@dataclass(slots=True)
class Contradiction:
    node_a: str
    node_b: str
    reason: str
    severity: float = 0.0


_KNOWN_ANTONYMS: Dict[str, Set[str]] = {
    "true": {"false"},
    "false": {"true"},
    "good": {"bad"},
    "bad": {"good"},
    "increase": {"decrease"},
    "decrease": {"increase"},
    "positive": {"negative"},
    "negative": {"positive"},
    "yes": {"no"},
    "no": {"yes"},
}


def detect_contradictions(
    nodes: Dict[str, object],
    activation_threshold: float = 0.5,
    topic_overlap_min: int = 1,
) -> List[Contradiction]:
    contradictions: List[Contradiction] = []

    topic_to_ids: Dict[str, List[str]] = {}
    active_map: Dict[str, object] = {}
    for n in nodes.values():
        if getattr(n, "collapsed", False):
            continue
        if getattr(n, "activation", 0.0) < activation_threshold:
            continue
        nid = getattr(n, "id", "?")
        active_map[nid] = n
        for t in getattr(n, "topics", []):
            topic_to_ids.setdefault(t, []).append(nid)

    checked: Set[tuple[str, str]] = set()
    for ids in topic_to_ids.values():
        if len(ids) < 2:
            continue
        for i, aid in enumerate(ids):
            for bid in ids[i + 1 :]:
                pair = (min(aid, bid), max(aid, bid))
                if pair in checked:
                    continue
                checked.add(pair)

                a = active_map[aid]
                b = active_map[bid]
                topics_a = set(getattr(a, "topics", []))
                topics_b = set(getattr(b, "topics", []))
                overlap = topics_a & topics_b
                if len(overlap) < topic_overlap_min:
                    continue

                words_a = set(getattr(a, "content", "").lower().split())
                words_b = set(getattr(b, "content", "").lower().split())
                conflict_words: List[str] = []
                for word in words_a:
                    antonyms = _KNOWN_ANTONYMS.get(word, set())
                    if antonyms & words_b:
                        conflict_words.append(word)

                if conflict_words:
                    severity = min(
                        1.0,
                        (getattr(a, "activation", 0.0) + getattr(b, "activation", 0.0))
                        * 0.5
                        * len(conflict_words),
                    )
                    contradictions.append(
                        Contradiction(
                            node_a=aid,
                            node_b=bid,
                            reason=(
                                f"antonym conflict on shared topics {overlap}: "
                                f"{conflict_words}"
                            ),
                            severity=severity,
                        )
                    )
                    logger.info(
                        "Contradiction: %s <-> %s severity=%.2f (%s)",
                        aid,
                        bid,
                        severity,
                        conflict_words,
                    )

    return contradictions


def resolve_contradiction(
    nodes: Dict[str, object],
    contradiction: Contradiction,
    strategy: str = "weaken_lower",
) -> None:
    a = nodes.get(contradiction.node_a)
    b = nodes.get(contradiction.node_b)
    if a is None or b is None:
        return

    if strategy == "weaken_lower":
        if getattr(a, "stability", 1.0) <= getattr(b, "stability", 1.0):
            a.activation = max(0.0, getattr(a, "activation", 0.0) * 0.5)
        else:
            b.activation = max(0.0, getattr(b, "activation", 0.0) * 0.5)
    elif strategy == "collapse_lower":
        if getattr(a, "stability", 1.0) <= getattr(b, "stability", 1.0):
            a.collapsed = True
            a.activation = 0.0
        else:
            b.collapsed = True
            b.activation = 0.0
