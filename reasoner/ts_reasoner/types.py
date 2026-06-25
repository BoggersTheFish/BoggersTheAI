"""Shared dataclasses for TS-Reasoner-v0."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, List, Optional


def to_jsonable(value: Any) -> Any:
    """Recursively convert dataclasses into JSON-safe Python values."""
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class ReasoningStep:
    step_id: str
    text: str
    kind: str
    dependencies: List[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass(frozen=True)
class ReasoningChain:
    chain_id: str
    question: str
    premises: List[str]
    steps: List[ReasoningStep]
    final_answer: str
    generator: str = "DeterministicHeuristicGenerator"


@dataclass(frozen=True)
class TensionIssue:
    issue_id: str
    step_id: str
    kind: str
    severity: float
    message: str
    evidence: List[str] = field(default_factory=list)
    suggestion: str = ""


@dataclass(frozen=True)
class TensionScore:
    chain_id: str
    local_tension: Dict[str, float]
    global_tension: float
    issues: List[TensionIssue] = field(default_factory=list)
    stability: float = 0.0


@dataclass(frozen=True)
class TensionAgentSignal:
    channel: str
    tension: float
    suspect_edges: List[str] = field(default_factory=list)
    suggested_ops: List[str] = field(default_factory=list)
    confidence: float = 0.0
    shares_with: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    normalized: str
    source_step_id: str
    subject: Optional[str] = None
    predicate: Optional[str] = None
    quantifier: Optional[str] = None
    polarity: str = "positive"
    confidence: float = 0.5
    dependencies: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CIGCheck:
    chain_id: str
    claims: List[Claim]
    dependencies: Dict[str, List[str]]
    contradiction_pairs: List[List[str]] = field(default_factory=list)
    unsupported_claim_ids: List[str] = field(default_factory=list)
    circular_step_ids: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class RepairSuggestion:
    repair_id: str
    target_step_id: str
    issue_kind: str
    original_text: str
    proposed_text: str
    rationale: str
    expected_tension_delta: float
    status: str = "suggested"


@dataclass(frozen=True)
class ReasonerOutput:
    question: str
    premises: List[str]
    candidates: List[ReasoningChain]
    selected_chain: ReasoningChain
    tension_score: TensionScore
    cig_check: CIGCheck
    repairs: List[RepairSuggestion]
    final_answer: str
    trace: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return to_jsonable(self)
