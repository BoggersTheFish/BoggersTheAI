"""Typed tension kernel dataclasses.

These types are deliberately domain-neutral. TS-Reasoner, CIG, and project
control layers should attach their own meaning through node/edge data and
channel implementations instead of baking that meaning into the kernel.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class Node:
    node_id: str
    kind: str = "state"
    activation: float = 0.0
    stability: float = 1.0
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    relation: str = "constraint"
    weight: float = 1.0
    directed: bool = True
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class ActivationState:
    active_nodes: dict[str, float] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class ChannelResult:
    channel: str
    activated: bool
    initial_tension: float = 0.0
    final_tension: float = 0.0
    resolution: str = "not_activated"
    evidence: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class ResolverEvent:
    channel: str
    action: str
    status: str
    target: str | None = None
    tension_delta: float = 0.0
    evidence: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class RuntimeTrace:
    runtime: str = "ts_core.typed_tension"
    started_at: str = field(default_factory=utc_now)
    channel_results: list[ChannelResult] = field(default_factory=list)
    resolver_events: list[ResolverEvent] = field(default_factory=list)
    global_tension: float = 0.0
    settled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class Receipt:
    project: str
    version: str
    commit: str
    date: str
    claim: str
    scope: str
    inputs: list[Any] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    tests: dict[str, Any] = field(default_factory=dict)
    benchmarks: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    known_limitations: list[str] = field(default_factory=list)
    tensions_detected: list[str] = field(default_factory=list)
    tensions_resolved: list[str] = field(default_factory=list)
    unresolved_tensions: list[str] = field(default_factory=list)
    public_claim_level: str = "experimental"

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)
