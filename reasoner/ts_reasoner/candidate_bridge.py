"""TensionLM candidate-claim bridge.

TensionLM proposes candidate graph claims. TS-Reasoner verifies them by running
the premise graph through typed tension channels, then a small decision reducer
reads the settled graph and channel context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Protocol

from .cig_checker import CIGChecker
from .generator import ParsedRelation, extract_relations, infer_premises_from_question, infer_query_relation
from .proof_chain import has_universal_bridge
from .ts_core_adapter import channel_context, channel_results_to_trace, chain_to_graph
from .types import ReasoningChain, ReasoningStep
from .candidates import CandidateClaim, CandidateVerification
from .reasoning_channels import default_reasoning_channels

try:
    from ts_core import TypedTensionRuntime
except ModuleNotFoundError:  # pragma: no cover - ts_core_adapter inserts sibling path first in normal local use.
    from .ts_core_adapter import TypedTensionRuntime  # type: ignore


class CandidateProposer(Protocol):
    def propose(self, input_text: str, premises: Iterable[str] | None = None) -> list[CandidateClaim]:
        """Return candidate graph claims for TS-Reasoner verification."""


class MockTensionLMCandidateProposer:
    """Dependency-light deterministic stand-in for early bridge receipts."""

    source = "candidate_bridge"

    def propose(self, input_text: str, premises: Iterable[str] | None = None) -> list[CandidateClaim]:
        premise_list = _premise_list(input_text, premises)
        premise_relations = [relation for premise in premise_list for relation in extract_relations(premise)]
        query = infer_query_relation(input_text)
        if query is None:
            return [
                CandidateClaim(
                    candidate_id="mock_candidate_1",
                    claim="Not enough information.",
                    source=self.source,
                    confidence=0.35,
                    raw_output=input_text,
                    metadata={"proposal_rule": "no_query_relation"},
                )
            ]

        proposals = [
            CandidateClaim(
                candidate_id="mock_candidate_1",
                claim=_claim_text(query),
                source=self.source,
                confidence=0.82 if _relation_supported(query, premise_relations) else 0.58,
                raw_output=input_text,
                metadata={"proposal_rule": "query_relation"},
            )
        ]
        if query.subject.lower() != query.predicate.lower():
            reverse = ParsedRelation(query.quantifier, query.predicate, query.subject, "")
            proposals.append(
                CandidateClaim(
                    candidate_id="mock_candidate_2",
                    claim=_claim_text(reverse),
                    source=self.source,
                    confidence=0.41,
                    raw_output=input_text,
                    metadata={"proposal_rule": "reverse_relation_probe"},
                )
            )
        return proposals


class ExternalTensionLMCandidateProposer:
    """Optional hook for future TensionLM output without loading a model here."""

    def __init__(
        self,
        hook: Callable[[str, list[str]], Iterable[CandidateClaim | dict[str, Any] | str]] | None = None,
        source: str = "external_tensionlm",
    ) -> None:
        self.hook = hook
        self.source = source

    def propose(self, input_text: str, premises: Iterable[str] | None = None) -> list[CandidateClaim]:
        if self.hook is None:
            raise RuntimeError("External mode requires a hook that returns candidate claims.")
        premise_list = _premise_list(input_text, premises)
        candidates = []
        for index, item in enumerate(self.hook(input_text, premise_list), start=1):
            candidates.append(_coerce_candidate(item, index, self.source))
        return candidates


@dataclass
class TensionLMCandidateBridge:
    proposer: CandidateProposer

    def run(self, input_text: str, premises: Iterable[str] | None = None) -> dict[str, Any]:
        premise_list = _premise_list(input_text, premises)
        candidate_claims = self.proposer.propose(input_text, premise_list)
        verifications = [
            verify_candidate_claim(input_text, premise_list, candidate, index)
            for index, candidate in enumerate(candidate_claims, start=1)
        ]
        return build_bridge_payload(input_text, premise_list, candidate_claims, verifications)


def run_tensionlm_candidate_bridge(
    input_text: str,
    premises: Iterable[str] | None = None,
    mode: str = "mock",
    external_hook: Callable[[str, list[str]], Iterable[CandidateClaim | dict[str, Any] | str]] | None = None,
) -> dict[str, Any]:
    if mode == "mock":
        proposer: CandidateProposer = MockTensionLMCandidateProposer()
    elif mode == "external":
        proposer = ExternalTensionLMCandidateProposer(external_hook)
    else:
        raise ValueError(f"Unknown candidate bridge mode: {mode}")
    payload = TensionLMCandidateBridge(proposer).run(input_text, premises)
    payload["mode"] = mode
    return payload


def verify_candidate_claim(
    input_text: str,
    premises: list[str],
    candidate: CandidateClaim,
    index: int = 1,
) -> CandidateVerification:
    provenance = {
        "candidate_id": candidate.candidate_id,
        "source": candidate.source,
        "confidence": candidate.confidence,
        "raw_output": candidate.raw_output,
        "metadata": dict(candidate.metadata),
    }
    if not candidate.source:
        return CandidateVerification(
            candidate_id=candidate.candidate_id,
            claim=candidate.claim,
            source=candidate.source,
            confidence=candidate.confidence,
            status="rejected",
            reason="candidate provenance is missing",
            channels={"provenance": "rejected missing candidate source"},
            channel_trace={},
            typed_runtime={"available": False, "settled": False},
            provenance=provenance,
        )

    relations = extract_relations(candidate.claim)
    if not relations:
        identity_pair = _identity_pair(candidate.claim)
        if identity_pair is not None:
            return _verify_identity_candidate(premises, candidate, provenance, identity_pair, index)
        return CandidateVerification(
            candidate_id=candidate.candidate_id,
            claim=candidate.claim,
            source=candidate.source,
            confidence=candidate.confidence,
            status="rejected",
            reason="candidate claim could not be parsed as a graph relation",
            channels={"malformed_relation": "rejected unparsable graph claim"},
            channel_trace={},
            typed_runtime={"available": False, "settled": False},
            provenance=provenance,
        )

    relation = relations[-1]
    chain = _verification_chain(input_text, premises, relation, index)
    cig = CIGChecker().check(chain)
    graph = chain_to_graph(chain, cig)
    context = channel_context(chain, cig)
    typed_trace = TypedTensionRuntime(default_reasoning_channels()).run(graph, context)
    channel_trace = channel_results_to_trace(typed_trace.channel_results)
    channels, status, reason = _decide(relation, graph, context, channel_trace)
    if status != "rejected" and _candidate_contradicts_premises(relation, graph):
        channels = {"contradiction": "rejected candidate contradicts premise edge"}
        status = "rejected"
        reason = "candidate contradicts a premise-supported edge"
    typed_runtime = {
        "available": True,
        "settled": typed_trace.settled,
        "global_tension": typed_trace.global_tension,
        "resolver_events": [event.to_dict() for event in typed_trace.resolver_events],
        "context": {
            "blocked_edges": context.get("blocked_edges", []),
            "blocked_equalities": context.get("blocked_equalities", []),
            "surface_tags": context.get("surface_tags", {}),
            "abstention": context.get("abstention"),
            "contradiction_flagged": context.get("contradiction_flagged", False),
            "quantifier_scope_blocked": context.get("quantifier_scope_blocked", False),
        },
    }
    return CandidateVerification(
        candidate_id=candidate.candidate_id,
        claim=_claim_text(relation),
        source=candidate.source,
        confidence=candidate.confidence,
        status=status,
        reason=reason,
        channels=channels,
        channel_trace=channel_trace,
        typed_runtime=typed_runtime,
        provenance=provenance,
    )


def build_bridge_payload(
    input_text: str,
    premises: list[str],
    candidates: list[CandidateClaim],
    verifications: list[CandidateVerification],
) -> dict[str, Any]:
    accepted = [item.claim for item in verifications if item.status == "accepted"]
    rejected = [item.claim for item in verifications if item.status == "rejected"]
    abstained = [item.claim for item in verifications if item.status == "abstained"]
    channels: dict[str, str] = {}
    for item in verifications:
        for channel, reason in item.channels.items():
            channels.setdefault(channel, reason)
    return {
        "input_text": input_text,
        "premises": premises,
        "candidate_claims": [candidate.to_dict() for candidate in candidates],
        "verification": {
            "accepted": accepted,
            "rejected": rejected,
            "abstained": abstained,
            "channels": channels,
            "candidate_results": [item.to_dict() for item in verifications],
        },
        "trace_receipt": {
            "role": "TensionLM proposes. TS-Reasoner verifies. Typed channels decide. Receipts explain.",
            "candidate_count": len(candidates),
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "abstained_count": len(abstained),
            "provenance_preserved": all(bool(item.provenance.get("source")) for item in verifications),
        },
    }


def _decide(
    relation: ParsedRelation,
    graph: Any,
    context: dict[str, Any],
    channel_trace: dict[str, dict[str, Any]],
) -> tuple[dict[str, str], str, str]:
    candidate_edge = f"{relation.subject}->{relation.predicate}"
    channels: dict[str, str] = {}
    if candidate_edge in context.get("blocked_edges", []):
        channels["directionality"] = "blocked reverse inference"
        return channels, "rejected", "candidate reverses a directed support path"
    if context.get("quantifier_scope_blocked"):
        channels["quantifier_scope"] = "blocked some-to-all upgrade"
        return channels, "rejected", "candidate upgrades existential support into a universal claim"
    if context.get("contradiction_flagged"):
        channels["contradiction"] = "flagged contradiction"
        return channels, "rejected", "premise graph is contradictory for this candidate"

    support = _support_status(graph, relation)
    if support == "inferred":
        channels["logic_transitivity"] = "accepted inferred edge"
        return channels, "accepted", "candidate is supported by a typed transitive inference"
    if support == "premise":
        channels["surface_structure"] = "accepted premise edge"
        return channels, "accepted", "candidate is directly present in the premise graph"

    channels["typed_support"] = "abstained no accepted channel support"
    return channels, "abstained", "no typed channel produced support or a typed rejection"


def _support_status(graph: Any, relation: ParsedRelation) -> str | None:
    for edge in graph.edges:
        if edge.relation != relation.quantifier:
            continue
        if edge.source.lower() != relation.subject.lower() or edge.target.lower() != relation.predicate.lower():
            continue
        status = edge.data.get("status")
        if status in {"premise", "inferred"}:
            return status
    return None


def _candidate_contradicts_premises(relation: ParsedRelation, graph: Any) -> bool:
    if relation.quantifier not in {"all", "some", "no"}:
        return False
    for edge in graph.edges:
        if edge.source.lower() != relation.subject.lower() or edge.target.lower() != relation.predicate.lower():
            continue
        if edge.data.get("status") not in {"premise", "inferred"}:
            continue
        if relation.quantifier == "no" and edge.relation in {"all", "some"}:
            return True
        if edge.relation == "no" and relation.quantifier in {"all", "some"}:
            return True
    return False


def _verify_identity_candidate(
    premises: list[str],
    candidate: CandidateClaim,
    provenance: dict[str, Any],
    pair: tuple[str, str],
    index: int,
) -> CandidateVerification:
    subject, predicate = pair
    chain = _identity_verification_chain(premises, subject, predicate, index)
    cig = CIGChecker().check(chain)
    graph = chain_to_graph(chain, cig)
    context = channel_context(chain, cig)
    typed_trace = TypedTensionRuntime(default_reasoning_channels()).run(graph, context)
    channel_trace = channel_results_to_trace(typed_trace.channel_results)
    blocked_equalities = context.get("blocked_equalities", [])
    marker = f"{subject}!={predicate}"
    if marker in blocked_equalities:
        channels = {"identity_preservation": "blocked identity collapse"}
        status = "rejected"
        reason = "candidate collapses distinct graph nodes"
    else:
        channels = {"typed_support": "abstained no accepted channel support"}
        status = "abstained"
        reason = "identity candidate has no typed support"
    return CandidateVerification(
        candidate_id=candidate.candidate_id,
        claim=f"{subject} equals {predicate}",
        source=candidate.source,
        confidence=candidate.confidence,
        status=status,
        reason=reason,
        channels=channels,
        channel_trace=channel_trace,
        typed_runtime={
            "available": True,
            "settled": typed_trace.settled,
            "global_tension": typed_trace.global_tension,
            "resolver_events": [event.to_dict() for event in typed_trace.resolver_events],
            "context": {
                "blocked_edges": context.get("blocked_edges", []),
                "blocked_equalities": blocked_equalities,
                "surface_tags": context.get("surface_tags", {}),
                "abstention": context.get("abstention"),
                "contradiction_flagged": context.get("contradiction_flagged", False),
                "quantifier_scope_blocked": context.get("quantifier_scope_blocked", False),
            },
        },
        provenance=provenance,
    )


def _verification_chain(
    input_text: str,
    premises: list[str],
    relation: ParsedRelation,
    index: int,
) -> ReasoningChain:
    steps = [
        ReasoningStep(f"p{premise_index + 1}", premise, "premise", [], 0.9)
        for premise_index, premise in enumerate(premises)
    ]
    return ReasoningChain(
        chain_id=f"candidate_bridge_verify_{index}",
        question=_question_text(relation),
        premises=list(premises),
        steps=steps,
        final_answer=_claim_text(relation),
        generator="TensionLMCandidateBridge",
    )


def _identity_verification_chain(
    premises: list[str],
    subject: str,
    predicate: str,
    index: int,
) -> ReasoningChain:
    steps = [
        ReasoningStep(f"p{premise_index + 1}", premise, "premise", [], 0.9)
        for premise_index, premise in enumerate(premises)
    ]
    return ReasoningChain(
        chain_id=f"candidate_bridge_identity_verify_{index}",
        question=f"Is {subject} identical to {predicate}?",
        premises=list(premises),
        steps=steps,
        final_answer=f"{subject} equals {predicate}",
        generator="TensionLMCandidateBridge",
    )


def _premise_list(input_text: str, premises: Iterable[str] | None) -> list[str]:
    if premises is not None:
        return [premise.strip() for premise in premises if premise.strip()]
    return [premise.strip() for premise in infer_premises_from_question(input_text) if premise.strip()]


def _claim_text(relation: ParsedRelation) -> str:
    return f"{relation.quantifier.capitalize()} {relation.subject} are {relation.predicate}"


def _identity_pair(text: str) -> tuple[str, str] | None:
    match = re.search(
        r"\b(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+(?:equals|=|is\s+identical\s+to)\s+"
        r"(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)\b",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return match.group("subject"), match.group("predicate")


def _question_text(relation: ParsedRelation) -> str:
    return f"Are {relation.quantifier} {relation.subject} {relation.predicate}?"


def _relation_supported(relation: ParsedRelation, premise_relations: list[ParsedRelation]) -> bool:
    if any(
        item.quantifier == relation.quantifier
        and item.subject.lower() == relation.subject.lower()
        and item.predicate.lower() == relation.predicate.lower()
        for item in premise_relations
    ):
        return True
    if relation.quantifier == "all":
        return has_universal_bridge(premise_relations, relation.subject, relation.predicate)
    return False


def _coerce_candidate(item: CandidateClaim | dict[str, Any] | str, index: int, default_source: str) -> CandidateClaim:
    if isinstance(item, CandidateClaim):
        return item
    if isinstance(item, str):
        return CandidateClaim(
            candidate_id=f"external_candidate_{index}",
            claim=item,
            source=default_source,
            confidence=0.5,
            raw_output=item,
        )
    return CandidateClaim(
        candidate_id=str(item.get("candidate_id", f"external_candidate_{index}")),
        claim=str(item["claim"]),
        source=str(item.get("source", default_source)),
        confidence=float(item.get("confidence", 0.5)),
        raw_output=item.get("raw_output"),
        metadata=dict(item.get("metadata", {})),
    )
