from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from typing import Any, Iterable

from ts_reasoner.claim_normalizer import canonicalize_claim_surface
from ts_reasoner.runtime_kernel import normalize_claim
from ts_reasoner.typed_support import make_typed_support, validate_typed_support


ALL_RE = re.compile(r"^all (.+) are (.+)$")
NO_RE = re.compile(r"^no (.+) are (.+)$")


@dataclass(frozen=True)
class ParsedClaim:
    quantifier: str
    subject: str
    predicate: str


def parse_claim(text: str) -> ParsedClaim | None:
    claim = canonicalize_claim_surface(text)
    match = ALL_RE.match(claim)
    if match:
        return ParsedClaim("all", match.group(1), match.group(2))
    match = NO_RE.match(claim)
    if match:
        return ParsedClaim("no", match.group(1), match.group(2))
    return None


def _format_claim(parsed: ParsedClaim) -> str:
    return f"{parsed.quantifier} {parsed.subject} are {parsed.predicate}"


def _all_path(premises: list[ParsedClaim], source: str, target: str) -> list[ParsedClaim] | None:
    edges: dict[str, list[tuple[str, ParsedClaim]]] = {}
    for premise in premises:
        if premise.quantifier == "all":
            edges.setdefault(premise.subject, []).append((premise.predicate, premise))

    queue: deque[tuple[str, list[ParsedClaim]]] = deque([(source, [])])
    seen = {source}
    while queue:
        node, path = queue.popleft()
        for nxt, premise in edges.get(node, []):
            if premise.subject == premise.predicate:
                continue
            next_path = [*path, premise]
            if nxt == target:
                return next_path
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, next_path))
    return None


def derive_typed_support(premises: Iterable[str], claim: str) -> dict[str, Any]:
    normalized_premises = [canonicalize_claim_surface(item) for item in premises]
    parsed_premises = [parsed for item in normalized_premises if (parsed := parse_claim(item)) is not None]
    target = parse_claim(claim)
    normalized_claim = canonicalize_claim_surface(claim)

    if target is None:
        return {"status": "rejected", "reason": "unparseable_claim", "claim": normalized_claim}

    for premise_text in normalized_premises:
        if premise_text == normalized_claim:
            parsed = parse_claim(premise_text)
            if parsed and parsed.subject == parsed.predicate:
                return {"status": "rejected", "reason": "identity_block", "claim": normalized_claim}
            support = make_typed_support(
                channel="direct_support",
                premises=[premise_text],
                derived_claim=normalized_claim,
            )
            return {"status": "accepted", "claim": normalized_claim, "support": support}

    if target.quantifier == "all":
        if target.subject == target.predicate:
            return {"status": "rejected", "reason": "identity_block", "claim": normalized_claim}
        path = _all_path(parsed_premises, target.subject, target.predicate)
        if path and len(path) > 1:
            support = make_typed_support(
                channel="transitive_all",
                premises=[_format_claim(item) for item in path],
                derived_claim=normalized_claim,
            )
            return {"status": "accepted", "claim": normalized_claim, "support": support}
        reverse_path = _all_path(parsed_premises, target.predicate, target.subject)
        if reverse_path:
            return {"status": "rejected", "reason": "reverse_inference_block", "claim": normalized_claim}

    if target.quantifier == "no":
        for negative in parsed_premises:
            if negative.quantifier != "no":
                continue
            prefix = _all_path(parsed_premises, target.subject, negative.subject)
            if prefix and negative.predicate == target.predicate:
                support = make_typed_support(
                    channel="negative_exclusion",
                    premises=[*[_format_claim(item) for item in prefix], _format_claim(negative)],
                    derived_claim=normalized_claim,
                )
                return {"status": "accepted", "claim": normalized_claim, "support": support}

    return {"status": "abstained", "reason": "unsupported_claim", "claim": normalized_claim}


def verify_support_path(premises: Iterable[str], claim: str) -> dict[str, Any]:
    result = derive_typed_support(premises, claim)
    if result.get("status") == "accepted":
        support_check = validate_typed_support(result["claim"], result["support"])
        if not support_check["accepted"]:
            return {"status": "rejected", "reason": support_check["reason"], "claim": result["claim"]}
    return result


def evaluate_support_path_cases(cases: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    metrics = {
        "direct_support": [0, 0],
        "transitive_all": [0, 0],
        "negative_exclusion": [0, 0],
        "reverse_inference_block": [0, 0],
    }
    identity_collapse_count = 0
    accepted_without_typed = 0
    contamination = 0

    for case in cases:
        result = verify_support_path(case.get("premises", []), str(case.get("claim", "")))
        expected_status = str(case.get("expected_status"))
        expected_channel = str(case.get("expected_channel", ""))
        observed_channel = result.get("support", {}).get("channel") if result.get("support") else result.get("reason")
        passed = result["status"] == expected_status and (
            not expected_channel or observed_channel == expected_channel
        )
        if result["status"] == "accepted" and not result.get("support"):
            accepted_without_typed += 1
        if result.get("reason") == "identity_block" and result["status"] == "accepted":
            identity_collapse_count += 1
        if expected_channel in metrics:
            metrics[expected_channel][1] += 1
            if passed:
                metrics[expected_channel][0] += 1
        rows.append({
            "case_id": case.get("case_id"),
            "expected_status": expected_status,
            "observed_status": result["status"],
            "expected_channel": expected_channel,
            "observed_channel": observed_channel,
            "passed": passed,
        })

    case_count = len(rows)
    report = {
        "release": "v10.7.0",
        "case_count": case_count,
        "direct_support_accuracy": metrics["direct_support"][0] / metrics["direct_support"][1],
        "transitive_support_accuracy": metrics["transitive_all"][0] / metrics["transitive_all"][1],
        "negative_exclusion_accuracy": metrics["negative_exclusion"][0] / metrics["negative_exclusion"][1],
        "wrong_reverse_rejection_rate": metrics["reverse_inference_block"][0] / metrics["reverse_inference_block"][1],
        "identity_collapse_count": identity_collapse_count,
        "accepted_without_typed_support_count": accepted_without_typed,
        "candidate_graph_contamination_count": contamination,
        "results": rows,
    }
    report["all_gates_passed"] = (
        case_count > 0
        and all(row["passed"] for row in rows)
        and report["direct_support_accuracy"] == 1.0
        and report["transitive_support_accuracy"] == 1.0
        and report["negative_exclusion_accuracy"] == 1.0
        and report["wrong_reverse_rejection_rate"] == 1.0
        and identity_collapse_count == 0
        and accepted_without_typed == 0
        and contamination == 0
    )
    return report
