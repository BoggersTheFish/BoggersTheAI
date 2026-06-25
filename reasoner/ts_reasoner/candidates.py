"""Candidate-claim contracts for the TensionLM bridge.

The bridge treats model output as proposed graph claims. Candidate claims carry
provenance and confidence, but TS-Reasoner typed channels decide whether the
claim is accepted, rejected, or left unsupported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


CandidateStatus = Literal["accepted", "rejected", "abstained"]


@dataclass(frozen=True)
class CandidateClaim:
    candidate_id: str
    claim: str
    source: str = "candidate_bridge"
    confidence: float = 0.5
    raw_output: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "candidate_id": self.candidate_id,
            "claim": self.claim,
            "source": self.source,
            "confidence": self.confidence,
        }
        if self.raw_output is not None:
            payload["raw_output"] = self.raw_output
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass(frozen=True)
class CandidateVerification:
    candidate_id: str
    claim: str
    source: str
    confidence: float
    status: CandidateStatus
    reason: str
    channels: dict[str, str]
    channel_trace: dict[str, dict[str, Any]]
    typed_runtime: dict[str, Any]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "claim": self.claim,
            "source": self.source,
            "confidence": self.confidence,
            "status": self.status,
            "reason": self.reason,
            "channels": dict(self.channels),
            "channel_trace": self.channel_trace,
            "typed_runtime": self.typed_runtime,
            "provenance": self.provenance,
        }
