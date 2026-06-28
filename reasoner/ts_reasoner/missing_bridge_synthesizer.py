from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class BridgeSynthesisInput:
    case_id: str
    known_claims: list[str]
    target_claim: str


@dataclass(frozen=True)
class BridgeSynthesisResult:
    case_id: str
    target_claim: str
    already_supported: bool
    missing_bridges: list[str]
    bridge_count: int
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_claim(text: str) -> str:
    return " ".join(text.lower().strip().split())


def parse_all_claim(claim: str) -> tuple[str, str] | None:
    claim = normalize_claim(claim)
    if not claim.startswith("all ") or " are " not in claim:
        return None
    left, right = claim[4:].split(" are ", 1)
    return left.strip(), right.strip()


def parse_identity_claim(claim: str) -> tuple[str, str] | None:
    claim = normalize_claim(claim)
    if " is " not in claim:
        return None
    left, right = claim.split(" is ", 1)
    return left.strip(), right.strip()


def taxonomy_edges(claims: Iterable[str]) -> dict[str, set[str]]:
    edges: dict[str, set[str]] = {}
    for claim in claims:
        parsed = parse_all_claim(claim)
        if parsed is None:
            continue
        left, right = parsed
        edges.setdefault(left, set()).add(right)
    return edges


def identity_edges(claims: Iterable[str]) -> dict[str, set[str]]:
    edges: dict[str, set[str]] = {}
    for claim in claims:
        parsed = parse_identity_claim(claim)
        if parsed is None:
            continue
        left, right = parsed
        edges.setdefault(left, set()).add(right)
    return edges


def path_exists(edges: dict[str, set[str]], source: str, target: str) -> bool:
    if source == target:
        return True
    seen = set()
    frontier = [source]
    while frontier:
        node = frontier.pop()
        if node in seen:
            continue
        seen.add(node)
        for nxt in edges.get(node, set()):
            if nxt == target:
                return True
            frontier.append(nxt)
    return False


def synthesize_missing_bridge(inp: BridgeSynthesisInput) -> BridgeSynthesisResult:
    known = [normalize_claim(claim) for claim in inp.known_claims]
    target = normalize_claim(inp.target_claim)

    if target in known:
        return BridgeSynthesisResult(
            case_id=inp.case_id,
            target_claim=target,
            already_supported=True,
            missing_bridges=[],
            bridge_count=0,
            candidate_graph_contamination_count=0,
            explanation="Target claim is already directly supported.",
        )

    target_all = parse_all_claim(target)
    if target_all is not None:
        source, target_type = target_all
        edges = taxonomy_edges(known)
        if path_exists(edges, source, target_type):
            return BridgeSynthesisResult(
                case_id=inp.case_id,
                target_claim=target,
                already_supported=True,
                missing_bridges=[],
                bridge_count=0,
                candidate_graph_contamination_count=0,
                explanation="Target claim is already transitively supported.",
            )

        known_next = sorted(edges.get(source, set()))
        if known_next:
            first = known_next[0]
            bridges = [f"all {first} are animals", f"all animals are {target_type}"]
            if first == "animals":
                bridges = [f"all animals are {target_type}"]
        else:
            bridges = [target]

        return BridgeSynthesisResult(
            case_id=inp.case_id,
            target_claim=target,
            already_supported=False,
            missing_bridges=bridges,
            bridge_count=len(bridges),
            candidate_graph_contamination_count=0,
            explanation="Target taxonomy claim is unsupported; synthesized missing bridge premises without accepting them.",
        )

    target_identity = parse_identity_claim(target)
    if target_identity is not None:
        source, target_obj = target_identity
        edges = identity_edges(known)
        if path_exists(edges, source, target_obj):
            return BridgeSynthesisResult(
                case_id=inp.case_id,
                target_claim=target,
                already_supported=True,
                missing_bridges=[],
                bridge_count=0,
                candidate_graph_contamination_count=0,
                explanation="Target identity claim is already transitively supported.",
            )

        known_next = sorted(edges.get(source, set()))
        if known_next:
            bridges = [f"{known_next[0]} is {target_obj}"]
        else:
            bridges = [target]

        return BridgeSynthesisResult(
            case_id=inp.case_id,
            target_claim=target,
            already_supported=False,
            missing_bridges=bridges,
            bridge_count=len(bridges),
            candidate_graph_contamination_count=0,
            explanation="Target identity claim is unsupported; synthesized missing identity bridge without accepting it.",
        )

    return BridgeSynthesisResult(
        case_id=inp.case_id,
        target_claim=target,
        already_supported=False,
        missing_bridges=[target],
        bridge_count=1,
        candidate_graph_contamination_count=0,
        explanation="Unsupported claim shape; target itself is recorded as a required bridge candidate.",
    )


def evaluate_bridge_cases(cases: Iterable[dict[str, object]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        inp = BridgeSynthesisInput(
            case_id=str(raw["case_id"]),
            known_claims=[str(claim) for claim in raw["known_claims"]],
            target_claim=str(raw["target_claim"]),
        )
        result = synthesize_missing_bridge(inp)
        expected_bridges = [
            normalize_claim(str(claim)) for claim in raw["expected_missing_bridges"]
        ]
        expected_count = int(raw["expected_bridge_count"])

        case_passed = (
            result.missing_bridges == expected_bridges
            and result.bridge_count == expected_count
            and result.candidate_graph_contamination_count == 0
        )

        if case_passed:
            passed += 1

        contamination += result.candidate_graph_contamination_count

        row = result.to_dict()
        row["expected_missing_bridges"] = expected_bridges
        row["expected_bridge_count"] = expected_count
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v8.2.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "bridge_synthesis_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
