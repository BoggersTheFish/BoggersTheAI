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


_nli_pipeline = None


def _get_nli_pipeline():
    global _nli_pipeline
    if _nli_pipeline is None:
        try:
            import transformers

            # Lightweight zero-shot classifier model for NLI classification
            _nli_pipeline = transformers.pipeline(
                "zero-shot-classification",
                model="cross-encoder/nli-mini-roberta-sentence-transformers",
            )
        except Exception:
            pass
    return _nli_pipeline


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

                content_a = getattr(a, "content", "")
                content_b = getattr(b, "content", "")

                severity = 0.0
                reason = ""
                conflict_found = False

                # 1. Check zero-shot NLI pipeline if available
                nli_pipe = _get_nli_pipeline()
                if nli_pipe is not None:
                    try:
                        res = nli_pipe(
                            content_b,
                            candidate_labels=["contradicts", "agrees", "neutral"],
                            hypothesis=f"This statement {{}} the statement: '{content_a}'",
                        )
                        labels = res.get("labels", [])
                        scores = res.get("scores", [])
                        if labels and labels[0] == "contradicts":
                            severity = scores[0]
                            reason = f"NLI contradiction on shared topics {overlap} (score: {severity:.2f})"
                            conflict_found = True
                    except Exception as exc:
                        logger.debug("NLI contradiction check failed: %s", exc)

                # 2. Check Embedding negation/polarity alignment (if embeddings are populated)
                if (
                    not conflict_found
                    and getattr(a, "embedding", None)
                    and getattr(b, "embedding", None)
                ):
                    try:
                        from .embeddings import cosine_similarity

                        sim = cosine_similarity(a.embedding, b.embedding)
                        if sim > 0.85:
                            # High semantic similarity but opposite polarity/negations
                            negations = {
                                "not",
                                "never",
                                "no",
                                "cannot",
                                "n't",
                                "fail",
                                "unable",
                                "deny",
                                "refuse",
                            }
                            words_a = {
                                w.strip(".,?!;:") for w in content_a.lower().split()
                            }
                            words_b = {
                                w.strip(".,?!;:") for w in content_b.lower().split()
                            }
                            neg_a = bool(negations & words_a)
                            neg_b = bool(negations & words_b)
                            if neg_a != neg_b:
                                severity = sim * 0.9
                                reason = f"Semantic polarization contradiction on shared topics {overlap} (embedding similarity: {sim:.2f})"
                                conflict_found = True
                    except Exception as exc:
                        logger.debug("Embedding contradiction check failed: %s", exc)

                # 3. Fallback to lexical antonym matching
                if not conflict_found:
                    words_a = set(content_a.lower().split())
                    words_b = set(content_b.lower().split())
                    conflict_words: List[str] = []
                    for word in words_a:
                        antonyms = _KNOWN_ANTONYMS.get(word, set())
                        if antonyms & words_b:
                            conflict_words.append(word)

                    if conflict_words:
                        severity = min(
                            1.0,
                            (
                                getattr(a, "activation", 0.0)
                                + getattr(b, "activation", 0.0)
                            )
                            * 0.5
                            * len(conflict_words),
                        )
                        reason = f"antonym conflict on shared topics {overlap}: {conflict_words}"
                        conflict_found = True

                if conflict_found:
                    contradictions.append(
                        Contradiction(
                            node_a=aid,
                            node_b=bid,
                            reason=reason,
                            severity=severity,
                        )
                    )
                    logger.info(
                        "Contradiction: %s <-> %s severity=%.2f (%s)",
                        aid,
                        bid,
                        severity,
                        reason,
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
