from __future__ import annotations

import re
from collections import deque
from typing import Any

from ts_reasoner.generator import extract_relations, infer_premises_from_question
from ts_reasoner.proof_chain import universal_bridge_path


IDENTITY_RE = re.compile(
    r"\b(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+(?:equals|=|is\s+identical\s+to)\s+"
    r"(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)\b",
    re.IGNORECASE,
)


def extract_candidate_features(case: dict[str, Any], candidate: dict[str, Any]) -> dict[str, float]:
    input_text = str(case["input_text"])
    premises = [str(item) for item in case.get("premises") or infer_premises_from_question(input_text)]
    premise_relations = [relation for premise in premises for relation in extract_relations(premise)]
    claim = str(candidate["claim"])
    relations = extract_relations(claim)
    identity_pair = _identity_pair(claim)
    features = {
        "bias": 1.0,
        "premise_count": float(len(premise_relations)),
        "candidate_confidence": float(candidate.get("confidence", 0.5)),
        "parseable_relation": float(bool(relations)),
        "identity_candidate": float(identity_pair is not None),
        "malformed_candidate": float(not relations and identity_pair is None),
        "has_distractor": float("distractor" in case.get("tags", [])),
        "deeper_chain_case": float("deeper_chain" in case.get("tags", [])),
    }
    for key in ("all", "some", "no"):
        features[f"candidate_quantifier_{key}"] = 0.0
    if relations:
        relation = relations[-1]
        direct_support = _direct_support(premise_relations, relation)
        features[f"candidate_quantifier_{relation.quantifier}"] = 1.0
        features["candidate_subject_eq_predicate"] = float(
            relation.subject.lower() == relation.predicate.lower()
        )
        features["direct_support"] = float(direct_support)
        path = universal_bridge_path(premise_relations, relation.subject, relation.predicate)
        transitive_support = bool(path)
        reverse_path = _has_path(premise_relations, relation.predicate, relation.subject)
        contradiction_candidate = _contradicts(premise_relations, relation)
        some_to_all_risk = (
            relation.quantifier == "all"
            and any(
                item.quantifier == "some" and item.subject.lower() == relation.subject.lower()
                for item in premise_relations
            )
        )
        features["transitive_support"] = float(transitive_support)
        features["support_depth"] = float(len(path))
        features["reverse_path"] = float(reverse_path)
        features["contradiction_candidate"] = float(contradiction_candidate)
        features["no_against_transitive_support"] = float(
            relation.quantifier == "no" and transitive_support
        )
        features["some_to_all_risk"] = float(some_to_all_risk)
        features["accepted_relation_candidate"] = float(
            relation.quantifier == "all" and (direct_support or transitive_support)
        )
        features["unsupported_relation_candidate"] = float(
            relation.quantifier == "all"
            and not direct_support
            and not transitive_support
            and not reverse_path
            and not contradiction_candidate
            and not some_to_all_risk
        )
    else:
        features.update(
            {
                "candidate_subject_eq_predicate": 0.0,
                "direct_support": 0.0,
                "transitive_support": 0.0,
                "support_depth": 0.0,
                "reverse_path": 0.0,
                "contradiction_candidate": 0.0,
                "no_against_transitive_support": 0.0,
                "some_to_all_risk": 0.0,
                "accepted_relation_candidate": 0.0,
                "unsupported_relation_candidate": 0.0,
            }
        )
    if identity_pair is not None:
        subject, predicate = identity_pair
        features["identity_path_exists"] = float(_has_path(premise_relations, subject, predicate))
    else:
        features["identity_path_exists"] = 0.0
    return features


def _identity_pair(text: str) -> tuple[str, str] | None:
    match = IDENTITY_RE.search(text)
    if match is None:
        return None
    return match.group("subject"), match.group("predicate")


def _direct_support(relations, candidate_relation) -> bool:
    return any(
        relation.quantifier == candidate_relation.quantifier
        and relation.subject.lower() == candidate_relation.subject.lower()
        and relation.predicate.lower() == candidate_relation.predicate.lower()
        for relation in relations
    )


def _has_path(relations, subject: str, predicate: str) -> bool:
    subject_key = subject.lower()
    predicate_key = predicate.lower()
    edges: dict[str, list[str]] = {}
    for relation in relations:
        if relation.quantifier == "all":
            edges.setdefault(relation.subject.lower(), []).append(relation.predicate.lower())
    queue: deque[str] = deque([subject_key])
    seen = set()
    while queue:
        node = queue.popleft()
        if node == predicate_key:
            return True
        if node in seen:
            continue
        seen.add(node)
        queue.extend(edges.get(node, []))
    return False


def _contradicts(relations, candidate_relation) -> bool:
    if candidate_relation.quantifier not in {"all", "some", "no"}:
        return False
    for relation in relations:
        same_edge = (
            relation.subject.lower() == candidate_relation.subject.lower()
            and relation.predicate.lower() == candidate_relation.predicate.lower()
        )
        if not same_edge:
            continue
        if candidate_relation.quantifier == "no" and relation.quantifier in {"all", "some"}:
            return True
        if relation.quantifier == "no" and candidate_relation.quantifier in {"all", "some"}:
            return True
    return False
