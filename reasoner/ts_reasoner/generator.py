"""Candidate-chain generation.

The default generator is intentionally small and auditable. It makes candidate
constraint paths from the question and supplied premises. LearnedCandidateGenerator
is the narrow v0.3 experiment: it learns which proposal templates to activate,
then the existing CIG/ranker/repair pipeline still verifies the chains.
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from .proof_chain import has_universal_bridge, universal_bridge_path
from .types import ReasoningChain, ReasoningStep


RELATION_RE = re.compile(
    r"\b(?P<quantifier>all|some|no)\s+(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+"
    r"(?:are|is)\s+(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)\b",
    re.IGNORECASE,
)
QUERY_RE = re.compile(
    r"\b(?:are|is)\s+(?P<quantifier>all|some|no)?\s*"
    r"(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+"
    r"(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)\??",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedRelation:
    quantifier: str
    subject: str
    predicate: str
    text: str

    @property
    def normalized(self) -> str:
        return f"{self.quantifier.lower()} {self.subject.lower()} are {self.predicate.lower()}"


def extract_relations(text: str) -> List[ParsedRelation]:
    relations: List[ParsedRelation] = []
    for match in RELATION_RE.finditer(text):
        relations.append(
            ParsedRelation(
                quantifier=match.group("quantifier").lower(),
                subject=match.group("subject"),
                predicate=match.group("predicate"),
                text=match.group(0),
            )
        )
    return relations


def infer_premises_from_question(question: str) -> List[str]:
    """Pull simple natural-language premises out of an if/then-style question."""
    premise_region = re.split(r",\s*(?:are|is)\b", question, maxsplit=1, flags=re.IGNORECASE)[0]
    relations = extract_relations(premise_region)
    return [relation.text for relation in relations]


def infer_query_relation(question: str) -> Optional[ParsedRelation]:
    matches = list(QUERY_RE.finditer(question))
    if matches:
        match = matches[-1]
        quantifier = (match.group("quantifier") or "all").lower()
        return ParsedRelation(
            quantifier=quantifier,
            subject=match.group("subject"),
            predicate=match.group("predicate"),
            text=match.group(0).rstrip("?"),
        )
    relations = extract_relations(question)
    if relations:
        return relations[-1]
    return None


def _step(step_id: str, text: str, kind: str, deps: Sequence[str], confidence: float) -> ReasoningStep:
    return ReasoningStep(
        step_id=step_id,
        text=text,
        kind=kind,
        dependencies=list(deps),
        confidence=confidence,
    )


class DeterministicHeuristicGenerator:
    """Create a small candidate set from symbolic-looking text patterns."""

    name = "DeterministicHeuristicGenerator"

    def generate(self, question: str, premises: Optional[Iterable[str]] = None) -> List[ReasoningChain]:
        premise_list = [p.strip() for p in premises or infer_premises_from_question(question) if p.strip()]
        query = infer_query_relation(question)
        premise_relations = [rel for premise in premise_list for rel in extract_relations(premise)]
        candidates = [
            self._candidate_direct(question, premise_list, premise_relations, query),
            self._candidate_cautious(question, premise_list, premise_relations, query),
        ]
        bridge = self._candidate_bridge_explicit(question, premise_list, premise_relations, query)
        if bridge is not None:
            candidates.append(bridge)
        contradiction = self._candidate_contradiction(question, premise_list, premise_relations, query)
        if contradiction is not None:
            candidates.append(contradiction)
        return candidates

    def _premise_steps(self, premises: Sequence[str]) -> List[ReasoningStep]:
        return [
            _step(f"p{i + 1}", premise, "premise", [], 0.9)
            for i, premise in enumerate(premises)
        ]

    def _candidate_direct(
        self,
        question: str,
        premises: Sequence[str],
        relations: Sequence[ParsedRelation],
        query: Optional[ParsedRelation],
    ) -> ReasoningChain:
        steps = self._premise_steps(premises)
        deps = [step.step_id for step in steps]
        conclusion = self._direct_conclusion(relations, query)
        steps.append(_step("s1", conclusion, "conclusion", deps, 0.78))
        return ReasoningChain(
            chain_id="candidate_direct",
            question=question,
            premises=list(premises),
            steps=steps,
            final_answer=self._answer_from_conclusion(conclusion),
        )

    def _candidate_cautious(
        self,
        question: str,
        premises: Sequence[str],
        relations: Sequence[ParsedRelation],
        query: Optional[ParsedRelation],
    ) -> ReasoningChain:
        steps = self._premise_steps(premises)
        deps = [step.step_id for step in steps]
        if query is None:
            text = "The available premises are not enough to derive a definite answer."
        elif self._has_all_all_bridge(relations, query):
            bridge_path = universal_bridge_path(relations, query.subject, query.predicate)
            if len(bridge_path) > 2:
                bridge_text = " -> ".join(
                    [bridge_path[0].subject, *[relation.predicate for relation in bridge_path]]
                )
                text = f"The universal bridge {bridge_text} supports the requested relation. Therefore all {query.subject} are {query.predicate}."
            else:
                text = f"Therefore all {query.subject} are {query.predicate}."
        else:
            text = (
                f"The premises do not force the requested universal relation between {query.subject} and {query.predicate}; "
                "more information is needed."
            )
        steps.append(_step("s1", text, "conclusion", deps, 0.64))
        return ReasoningChain(
            chain_id="candidate_cautious",
            question=question,
            premises=list(premises),
            steps=steps,
            final_answer=self._answer_from_conclusion(text),
        )

    def _candidate_bridge_explicit(
        self,
        question: str,
        premises: Sequence[str],
        relations: Sequence[ParsedRelation],
        query: Optional[ParsedRelation],
    ) -> Optional[ReasoningChain]:
        if query is None:
            return None
        bridge_path = universal_bridge_path(relations, query.subject, query.predicate)
        if len(bridge_path) <= 2:
            return None
        steps = self._premise_steps(premises)
        deps = [step.step_id for step in steps]
        bridge_text = " -> ".join([bridge_path[0].subject, *[relation.predicate for relation in bridge_path]])
        steps.append(
            _step(
                "s1",
                f"Bridge the universal chain {bridge_text}.",
                "bridge",
                deps,
                0.72,
            )
        )
        steps.append(
            _step(
                "s2",
                f"Therefore all {query.subject} are {query.predicate}.",
                "conclusion",
                ["s1"],
                0.72,
            )
        )
        return ReasoningChain(
            chain_id="candidate_transitive_bridge",
            question=question,
            premises=list(premises),
            steps=steps,
            final_answer=f"all {query.subject} are {query.predicate}.",
        )

    def _candidate_contradiction(
        self,
        question: str,
        premises: Sequence[str],
        relations: Sequence[ParsedRelation],
        query: Optional[ParsedRelation],
    ) -> Optional[ReasoningChain]:
        if query is None:
            return None
        if not any(self._is_negative_pair(relation, query) for relation in relations):
            return None
        steps = self._premise_steps(premises)
        deps = [step.step_id for step in steps]
        text = (
            f"A contradiction touches {query.subject} and {query.predicate}, "
            "so the answer is unstable under the stated premises."
        )
        steps.append(_step("s1", text, "conclusion", deps, 0.45))
        return ReasoningChain(
            chain_id="candidate_a_contradiction_aware",
            question=question,
            premises=list(premises),
            steps=steps,
            final_answer="Contradiction detected; no stable answer follows.",
        )

    def _direct_conclusion(
        self, relations: Sequence[ParsedRelation], query: Optional[ParsedRelation]
    ) -> str:
        if query is None:
            return "Therefore the answer cannot be derived from the current premises."
        if self._has_all_all_bridge(relations, query):
            return f"Therefore all {query.subject} are {query.predicate}."
        if self._has_some_bridge(relations, query):
            return f"Therefore all {query.subject} are {query.predicate}."
        if any(self._same_relation(relation, query) for relation in relations):
            return f"Therefore {query.text}."
        return f"Therefore all {query.subject} are {query.predicate}."

    def _has_all_all_bridge(self, relations: Sequence[ParsedRelation], query: ParsedRelation) -> bool:
        return has_universal_bridge(relations, query.subject, query.predicate)

    def _has_some_bridge(self, relations: Sequence[ParsedRelation], query: ParsedRelation) -> bool:
        for left in relations:
            for right in relations:
                if (
                    left.quantifier == "some"
                    and right.quantifier == "all"
                    and left.subject.lower() == query.subject.lower()
                    and left.predicate.lower() == right.subject.lower()
                    and right.predicate.lower() == query.predicate.lower()
                ):
                    return True
        return False

    def _is_negative_pair(self, relation: ParsedRelation, query: ParsedRelation) -> bool:
        return (
            relation.quantifier == "no"
            and relation.subject.lower() == query.subject.lower()
            and relation.predicate.lower() == query.predicate.lower()
        )

    def _same_relation(self, relation: ParsedRelation, query: ParsedRelation) -> bool:
        return (
            relation.quantifier == query.quantifier
            and relation.subject.lower() == query.subject.lower()
            and relation.predicate.lower() == query.predicate.lower()
        )

    def _answer_from_conclusion(self, conclusion: str) -> str:
        lower = conclusion.lower()
        if "not force" in lower or "not enough" in lower or "cannot be derived" in lower:
            return "Not enough information."
        if "contradiction" in lower:
            return "Contradiction detected."
        if "therefore" in lower:
            return re.split(r"\btherefore\b", conclusion, flags=re.IGNORECASE)[-1].strip()
        return conclusion


class LearnedCandidateGenerator:
    """Template-selection candidate generator trained from synthetic rows.

    This is not a full language model. It learns proposal weights for a small
    set of candidate-chain templates, then delegates actual chain construction
    to the deterministic generator so the verifier can inspect every step.
    """

    name = "LearnedCandidateGenerator"

    def __init__(
        self,
        template_weights: dict[str, float],
        threshold: float = 0.3,
        min_candidates: int = 2,
        safety_fallback: bool = True,
    ) -> None:
        self.template_weights = dict(template_weights)
        self.threshold = threshold
        self.min_candidates = min_candidates
        self.safety_fallback = safety_fallback
        self.base_generator = DeterministicHeuristicGenerator()

    @classmethod
    def from_json(cls, path: str | Path) -> "LearnedCandidateGenerator":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            template_weights=payload["template_weights"],
            threshold=float(payload.get("threshold", 0.25)),
            min_candidates=int(payload.get("min_candidates", 2)),
            safety_fallback=bool(payload.get("safety_fallback", True)),
        )

    def to_json(self, path: str | Path, metadata: dict[str, object] | None = None) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generator": self.name,
            "model_type": "template_proposal_frequency_model",
            "template_weights": self.template_weights,
            "threshold": self.threshold,
            "min_candidates": self.min_candidates,
            "safety_fallback": self.safety_fallback,
            "metadata": metadata or {},
        }
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target

    def generate(self, question: str, premises: Optional[Iterable[str]] = None) -> List[ReasoningChain]:
        candidates = self.base_generator.generate(question, premises)
        by_id = {chain.chain_id: chain for chain in candidates}
        keep = {
            chain.chain_id
            for chain in candidates
            if self.template_weights.get(chain.chain_id, 0.0) >= self.threshold
        }
        if self.safety_fallback:
            keep = self._apply_safety_fallbacks(keep, candidates)
        selected = [chain for chain_id, chain in by_id.items() if chain_id in keep]
        return selected or candidates

    def _apply_safety_fallbacks(self, keep: set[str], candidates: List[ReasoningChain]) -> set[str]:
        by_id = {chain.chain_id: chain for chain in candidates}
        if len(keep) < self.min_candidates:
            for fallback in ("candidate_cautious", "candidate_direct"):
                if fallback in by_id:
                    keep.add(fallback)
                if len(keep) >= self.min_candidates:
                    break
        if any("contradiction" in chain.chain_id for chain in candidates):
            keep.update(chain.chain_id for chain in candidates if "contradiction" in chain.chain_id)
        return keep


class RandomCandidateProposer:
    """Deterministic pseudo-random candidate proposer for baseline comparisons."""

    name = "RandomCandidateProposer"

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold
        self.base_generator = DeterministicHeuristicGenerator()

    def generate(self, question: str, premises: Optional[Iterable[str]] = None) -> List[ReasoningChain]:
        candidates = self.base_generator.generate(question, premises)
        selected = [
            chain
            for chain in candidates
            if _stable_fraction(f"{question}::{chain.chain_id}") >= self.threshold
        ]
        return selected or candidates[:1]


def train_learned_candidate_generator(rows: Sequence[dict[str, object]]) -> LearnedCandidateGenerator:
    """Train a tiny template-frequency proposal model from candidate rows."""
    good_counts: dict[str, int] = {}
    total_counts: dict[str, int] = {}
    for row in rows:
        chain_id = str(row["chain_id"])
        total_counts[chain_id] = total_counts.get(chain_id, 0) + 1
        if int(row["label"]) == 0:
            good_counts[chain_id] = good_counts.get(chain_id, 0) + 1
    weights = {
        chain_id: round(good_counts.get(chain_id, 0) / max(1, total), 4)
        for chain_id, total in sorted(total_counts.items())
    }
    return LearnedCandidateGenerator(template_weights=weights)


def _stable_fraction(text: str) -> float:
    total = sum((index + 1) * ord(char) for index, char in enumerate(text))
    return (total % 10000) / 10000.0


class TensionLMGenerator:
    """Compatibility stub; use tensionlm_bridge for proposal integration."""

    name = "TensionLMGenerator"

    def generate(self, question: str, premises: Optional[Iterable[str]] = None) -> List[ReasoningChain]:
        raise NotImplementedError(
            "Use ts_reasoner.tensionlm_bridge to let TensionLM propose candidate text "
            "while TS-Reasoner verifies the resulting chain."
        )
