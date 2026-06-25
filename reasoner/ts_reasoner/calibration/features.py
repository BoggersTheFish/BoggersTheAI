"""Feature extraction for typed-channel calibration.

The feature surface is intentionally small and auditable. It describes the
typed trace state and simple premise/query structure; it does not learn
reasoning behavior from raw text.
"""

from __future__ import annotations

import re
from typing import Any

from ts_reasoner.generator import extract_relations, infer_query_relation


CHANNELS = (
    "logic_transitivity",
    "identity_preservation",
    "directionality",
    "surface_structure",
    "confidence_abstention",
    "contradiction",
    "quantifier_scope",
)

FEATURE_NAMES = (
    "bias",
    "premise_count",
    "all_edge_count",
    "some_edge_count",
    "no_edge_count",
    "has_all_all_chain",
    "query_supported_directly",
    "query_supported_transitively",
    "query_reverse_of_chain",
    "query_is_identity",
    "has_some_all_upgrade",
    "has_direct_contradiction",
    "empty_premises",
    "answer_abstains",
    "channel_observed_initial_tension",
    "channel_observed_final_tension",
    "channel_logic_transitivity",
    "channel_identity_preservation",
    "channel_directionality",
    "channel_surface_structure",
    "channel_confidence_abstention",
    "channel_contradiction",
    "channel_quantifier_scope",
)

STRUCTURAL_NUMERIC_FEATURES = (
    "shortest_path_exists",
    "shortest_path_length",
    "num_paths_between_query_nodes",
    "has_direct_edge",
    "has_inferred_edge",
    "has_reverse_edge",
    "reverse_path_exists",
    "query_relevant_edge_count",
    "distractor_edge_count",
    "distractor_ratio",
    "path_contains_some",
    "path_contains_no",
    "path_all_subset_chain_valid",
    "contradiction_on_query_path",
    "contradiction_off_query_path",
    "contradiction_blocks_answer",
    "identity_evidence_exists",
    "identity_claim_without_evidence",
    "candidate_requires_transitive_closure",
    "candidate_requires_reverse_inference",
    "candidate_requires_identity_collapse",
    "candidate_requires_quantifier_upgrade",
)


def extract_case_features(case: dict[str, Any], output: Any, channel: str) -> dict[str, Any]:
    premises = [str(item) for item in case.get("premises", [])]
    relations = _extract_structural_relations(premises)
    query_subject, query_predicate, query_quantifier = _extract_structural_query(str(case.get("question", "")))
    all_edges = [relation for relation in relations if relation["relation"] in {"all", "subset_of"}]
    some_edges = [relation for relation in relations if relation["relation"] in {"some", "overlaps"}]
    no_edges = [relation for relation in relations if relation["relation"] in {"no", "contradicts"}]
    has_chain = _has_all_all_chain(all_edges)
    direct = _has_direct_relation(relations, query_subject, query_predicate, query_quantifier)
    transitive = _has_transitive_relation(all_edges, query_subject, query_predicate)
    reverse = _has_transitive_relation(all_edges, query_predicate, query_subject) and not direct
    some_all = _has_some_all_upgrade(some_edges, all_edges, query_subject, query_predicate, query_quantifier)
    contradiction = _has_direct_contradiction(relations)
    channel_trace = output.trace.get("tension_channels", {}).get(channel, {})
    structural = _structural_features(relations, query_subject, query_predicate, query_quantifier)

    features = {
        "bias": 1.0,
        "premise_count": float(len(premises)),
        "all_edge_count": float(len(all_edges)),
        "some_edge_count": float(len(some_edges)),
        "no_edge_count": float(len(no_edges)),
        "has_all_all_chain": float(has_chain),
        "query_supported_directly": float(direct),
        "query_supported_transitively": float(transitive),
        "query_reverse_of_chain": float(reverse),
        "query_is_identity": float(query_quantifier == "identity"),
        "has_some_all_upgrade": float(some_all),
        "has_direct_contradiction": float(contradiction),
        "empty_premises": float(len(premises) == 0),
        "answer_abstains": float("not enough" in output.final_answer.lower()),
        "channel_observed_initial_tension": float(channel_trace.get("initial_tension", 0.0)),
        "channel_observed_final_tension": float(channel_trace.get("final_tension", 0.0)),
        "query_subject": query_subject,
        "query_object": query_predicate,
        "query_relation": query_quantifier,
        "path_quantifier_signature": structural["path_quantifier_signature"],
    }
    features.update(structural)
    for name in CHANNELS:
        features[f"channel_{name}"] = float(channel == name)
    for name in FEATURE_NAMES:
        features[name] = float(features.get(name, 0.0))
    for name in STRUCTURAL_NUMERIC_FEATURES:
        features[name] = float(features.get(name, 0.0))
    return features


def _has_direct_relation(relations, subject: str, predicate: str, quantifier: str) -> bool:
    if not subject or not predicate:
        return False
    return any(
        relation["subject"].lower() == subject.lower()
        and relation["object"].lower() == predicate.lower()
        and _relation_matches_query(relation["relation"], quantifier)
        for relation in relations
    )


def _has_all_all_chain(all_edges) -> bool:
    return any(
        left["object"].lower() == right["subject"].lower()
        for left in all_edges
        for right in all_edges
        if left is not right
    )


def _has_transitive_relation(all_edges, subject: str, predicate: str) -> bool:
    if not subject or not predicate:
        return False
    return any(
        left["subject"].lower() == subject.lower()
        and left["object"].lower() == right["subject"].lower()
        and right["object"].lower() == predicate.lower()
        for left in all_edges
        for right in all_edges
        if left is not right
    )


def _has_some_all_upgrade(some_edges, all_edges, subject: str, predicate: str, quantifier: str) -> bool:
    if quantifier != "all":
        return False
    return any(
        left["subject"].lower() == subject.lower()
        and left["object"].lower() == right["subject"].lower()
        and right["object"].lower() == predicate.lower()
        for left in some_edges
        for right in all_edges
    )


def _has_direct_contradiction(relations) -> bool:
    for left in relations:
        for right in relations:
            if left is right:
                continue
            same_pair = (
                left["subject"].lower() == right["subject"].lower()
                and left["object"].lower() == right["object"].lower()
            )
            if same_pair and {left["relation"], right["relation"]} & {"no", "contradicts"} and {left["relation"], right["relation"]} & {"all", "some", "subset_of", "overlaps"}:
                return True
    return False


def _extract_structural_relations(premises: list[str]) -> list[dict[str, str]]:
    relations: list[dict[str, str]] = []
    for premise in premises:
        for relation in extract_relations(premise):
            relations.append(
                {
                    "subject": _norm_symbol(relation.subject),
                    "object": _norm_symbol(relation.predicate),
                    "relation": relation.quantifier,
                    "text": relation.text,
                }
            )
        text = premise.strip().rstrip(".?")
        patterns = [
            (r"^every\s+(?P<s>[A-Za-z][A-Za-z0-9_-]*)\s+is\s+(?:a|an)?\s*(?P<o>[A-Za-z][A-Za-z0-9_-]*)$", "all"),
            (r"^all\s+(?P<s>[A-Za-z][A-Za-z0-9_-]*)\s+are\s+(?P<o>[A-Za-z][A-Za-z0-9_-]*)$", "all"),
            (r"^(?P<s>[A-Za-z][A-Za-z0-9_-]*)\s+subset_of\s+(?P<o>[A-Za-z][A-Za-z0-9_-]*)$", "subset_of"),
            (r"^(?P<s>[A-Za-z][A-Za-z0-9_-]*)\s+equals\s+(?P<o>[A-Za-z][A-Za-z0-9_-]*)$", "equals"),
            (r"^(?P<s>[A-Za-z][A-Za-z0-9_-]*)\s+contradicts\s+(?P<o>[A-Za-z][A-Za-z0-9_-]*)$", "contradicts"),
            (r"^(?P<s>[A-Za-z][A-Za-z0-9_-]*)\s+overlaps\s+(?P<o>[A-Za-z][A-Za-z0-9_-]*)$", "overlaps"),
        ]
        for pattern, relation in patterns:
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if match:
                item = {
                    "subject": _norm_symbol(match.group("s")),
                    "object": _norm_symbol(match.group("o")),
                    "relation": relation,
                    "text": text,
                }
                if item not in relations:
                    relations.append(item)
    return relations


def _extract_structural_query(question: str) -> tuple[str, str, str]:
    identity_match = re.search(
        r"\bis\s+(?P<s>[A-Za-z][A-Za-z0-9_-]*)\s+identical\s+to\s+(?P<o>[A-Za-z][A-Za-z0-9_-]*)",
        question,
        flags=re.IGNORECASE,
    )
    if identity_match:
        return _norm_symbol(identity_match.group("s")), _norm_symbol(identity_match.group("o")), "identity"
    patterns = [
        (r"\bis\s+(?P<s>[A-Za-z][A-Za-z0-9_-]*)\s+subset_of\s+(?P<o>[A-Za-z][A-Za-z0-9_-]*)", "subset_of"),
        (r"\bdoes\s+(?P<s>[A-Za-z][A-Za-z0-9_-]*)\s+contradict\s+(?P<o>[A-Za-z][A-Za-z0-9_-]*)", "contradicts"),
        (r"\bare\s+some\s+(?P<s>[A-Za-z][A-Za-z0-9_-]*)\s+(?P<o>[A-Za-z][A-Za-z0-9_-]*)", "some"),
        (r"\bis\s+each\s+(?P<s>[A-Za-z][A-Za-z0-9_-]*)\s+(?:a|an)?\s*(?P<o>[A-Za-z][A-Za-z0-9_-]*)", "all"),
    ]
    for pattern, relation in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if match:
            return _norm_symbol(match.group("s")), _norm_symbol(match.group("o")), relation
    query = infer_query_relation(question)
    if query is not None:
        return _norm_symbol(query.subject), _norm_symbol(query.predicate), query.quantifier
    return "", "", ""


def _structural_features(relations: list[dict[str, str]], subject: str, obj: str, query_relation: str) -> dict[str, Any]:
    path = _shortest_path(relations, subject, obj)
    reverse_path = _shortest_path(relations, obj, subject)
    path_edges = path or []
    path_signature = ">".join(edge["relation"] for edge in path_edges)
    query_nodes = _path_nodes(path_edges, subject)
    relevant_edges = [
        edge
        for edge in relations
        if edge["subject"] in query_nodes or edge["object"] in query_nodes
    ]
    distractors = [edge for edge in relations if edge not in relevant_edges]
    direct = any(edge["subject"] == subject and edge["object"] == obj for edge in relations)
    reverse_direct = any(edge["subject"] == obj and edge["object"] == subject for edge in relations)
    inferred = bool(path_edges) and len(path_edges) > 1
    path_relations = {edge["relation"] for edge in path_edges}
    contradiction_on_path = _contradiction_on_path(relations, query_nodes)
    contradiction_any = any(edge["relation"] in {"no", "contradicts"} for edge in relations)
    quantifier_upgrade = query_relation == "all" and any(edge["relation"] in {"some", "overlaps"} for edge in path_edges + relevant_edges)
    identity_evidence = any(
        edge["relation"] == "equals" and {edge["subject"], edge["object"]} == {subject, obj}
        for edge in relations
    )
    return {
        "shortest_path_exists": float(bool(path_edges)),
        "shortest_path_length": float(len(path_edges) if path_edges else 0),
        "num_paths_between_query_nodes": float(_path_count(relations, subject, obj)),
        "has_direct_edge": float(direct),
        "has_inferred_edge": float(inferred),
        "has_reverse_edge": float(reverse_direct),
        "reverse_path_exists": float(bool(reverse_path)),
        "query_relevant_edge_count": float(len(relevant_edges)),
        "distractor_edge_count": float(len(distractors)),
        "distractor_ratio": float(len(distractors) / max(1, len(relations))),
        "path_quantifier_signature": path_signature,
        "path_contains_some": float("some" in path_relations or "overlaps" in path_relations),
        "path_contains_no": float("no" in path_relations or "contradicts" in path_relations),
        "path_all_subset_chain_valid": float(bool(path_edges) and path_relations <= {"all", "subset_of", "equals"}),
        "contradiction_on_query_path": float(contradiction_on_path),
        "contradiction_off_query_path": float(contradiction_any and not contradiction_on_path),
        "contradiction_blocks_answer": float(contradiction_on_path and query_relation in {"all", "some", "subset_of"}),
        "identity_evidence_exists": float(identity_evidence),
        "identity_claim_without_evidence": float(query_relation == "identity" and not identity_evidence),
        "candidate_requires_transitive_closure": float(inferred and query_relation in {"all", "subset_of"}),
        "candidate_requires_reverse_inference": float(bool(reverse_path) and not bool(path_edges)),
        "candidate_requires_identity_collapse": float(query_relation == "identity" and bool(path_edges) and not identity_evidence),
        "candidate_requires_quantifier_upgrade": float(quantifier_upgrade),
    }


def _shortest_path(relations: list[dict[str, str]], source: str, target: str) -> list[dict[str, str]]:
    if not source or not target:
        return []
    frontier: list[tuple[str, list[dict[str, str]]]] = [(source, [])]
    seen = {source}
    while frontier:
        node, path = frontier.pop(0)
        for edge in relations:
            if edge["subject"] != node:
                continue
            next_node = edge["object"]
            next_path = path + [edge]
            if next_node == target:
                return next_path
            if next_node not in seen:
                seen.add(next_node)
                frontier.append((next_node, next_path))
    return []


def _path_count(relations: list[dict[str, str]], source: str, target: str, max_depth: int = 5) -> int:
    def walk(node: str, depth: int, seen: set[str]) -> int:
        if depth > max_depth:
            return 0
        total = 0
        for edge in relations:
            if edge["subject"] != node or edge["object"] in seen:
                continue
            if edge["object"] == target:
                total += 1
            else:
                total += walk(edge["object"], depth + 1, seen | {edge["object"]})
        return total

    if not source or not target:
        return 0
    return walk(source, 1, {source})


def _path_nodes(path_edges: list[dict[str, str]], subject: str) -> set[str]:
    nodes = {subject} if subject else set()
    for edge in path_edges:
        nodes.add(edge["subject"])
        nodes.add(edge["object"])
    return nodes


def _contradiction_on_path(relations: list[dict[str, str]], query_nodes: set[str]) -> bool:
    for edge in relations:
        if edge["relation"] not in {"no", "contradicts"}:
            continue
        if edge["subject"] in query_nodes or edge["object"] in query_nodes:
            return True
    return False


def _relation_matches_query(relation: str, query: str) -> bool:
    if relation == query:
        return True
    return relation == "subset_of" and query == "all"


def _norm_symbol(value: str) -> str:
    cleaned = value.strip().strip(".?,").lower()
    if len(cleaned) > 1 and cleaned.endswith("s"):
        cleaned = cleaned[:-1]
    return cleaned.upper() if len(cleaned) == 1 else cleaned
