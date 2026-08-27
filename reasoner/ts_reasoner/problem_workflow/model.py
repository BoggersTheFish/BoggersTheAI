"""Immutable public contracts for the bounded TS problem workflow."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from prime_v19 import canonical_bytes

from .canonical import (
    canonical_tree_is_valid,
    canonicalize_source,
    restore_source_floats,
)


PROBLEM_SPEC_SCHEMA = "boggers-ts-problem-spec-v1"
_PROBLEM_ID = re.compile(r"[a-z0-9][a-z0-9_]{0,127}")
_MAX_TEXT_BYTES = 4 * 1024
_MAX_ITEMS = 32
_MAX_SPEC_BYTES = 32 * 1024


class ProblemSpecError(ValueError):
    """A problem specification is invalid or exceeds its bound."""


class WorkflowState(str, Enum):
    READY = "READY"
    BOUND = "BOUND"
    FIELD_READY = "FIELD_READY"
    FOCUSED = "FOCUSED"
    PROPOSED = "PROPOSED"
    ROUTED = "ROUTED"
    REQUEST_READY = "REQUEST_READY"
    SUBMITTED = "SUBMITTED"
    COMMITTED = "COMMITTED"
    REJECTED = "REJECTED"
    ABSTAINED = "ABSTAINED"
    FAIL_CLOSED = "FAIL_CLOSED"


def _bounded_text(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ProblemSpecError(f"{label} must be text")
    if value != unicodedata.normalize("NFC", value) or "\x00" in value:
        raise ProblemSpecError(f"{label} must be NUL-free NFC text")
    normalized = value.strip()
    if not normalized and not allow_empty:
        raise ProblemSpecError(f"{label} cannot be empty")
    if len(normalized.encode("utf-8")) > _MAX_TEXT_BYTES:
        raise ProblemSpecError(f"{label} exceeds {_MAX_TEXT_BYTES} UTF-8 bytes")
    return normalized


def _bounded_items(value: Any, label: str, *, required: bool) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ProblemSpecError(f"{label} must be a sequence of strings")
    if len(value) > _MAX_ITEMS or (required and not value):
        qualifier = "one through" if required else "zero through"
        raise ProblemSpecError(f"{label} must contain {qualifier} {_MAX_ITEMS} items")
    result = tuple(
        _bounded_text(item, f"{label}[{index}]") for index, item in enumerate(value)
    )
    if len(set(result)) != len(result):
        raise ProblemSpecError(f"{label} must not contain duplicates")
    return result


@dataclass(frozen=True, slots=True)
class ProblemSpec:
    """One bounded, structured problem statement.

    Mutable source mappings are serialized immediately.  Properties decode a
    fresh detached object, so later caller mutation cannot change a proposal.
    """

    problem_id: str
    question: str
    context: tuple[str, ...]
    constraints: tuple[str, ...]
    desired_outcomes: tuple[str, ...]
    failure_modes: tuple[str, ...]
    testable_predictions: tuple[str, ...]
    scope: str
    provenance_json: str
    schema: str = PROBLEM_SPEC_SCHEMA

    @classmethod
    def create(
        cls,
        *,
        problem_id: str,
        question: str,
        constraints: Sequence[str],
        desired_outcomes: Sequence[str],
        failure_modes: Sequence[str],
        testable_predictions: Sequence[str],
        scope: str,
        provenance: Mapping[str, Any],
        context: Sequence[str] = (),
    ) -> "ProblemSpec":
        problem_id = _bounded_text(problem_id, "problem_id")
        if _PROBLEM_ID.fullmatch(problem_id) is None:
            raise ProblemSpecError("problem_id is not a portable identifier")
        if not isinstance(provenance, Mapping):
            raise ProblemSpecError("provenance must be a mapping")
        try:
            detached_provenance = canonicalize_source(provenance)
            provenance_json = canonical_bytes(detached_provenance).decode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ProblemSpecError(f"invalid provenance: {exc}") from exc
        candidate = cls(
            problem_id=problem_id,
            question=_bounded_text(question, "question"),
            context=_bounded_items(context, "context", required=False),
            constraints=_bounded_items(constraints, "constraints", required=True),
            desired_outcomes=_bounded_items(
                desired_outcomes, "desired_outcomes", required=True
            ),
            failure_modes=_bounded_items(failure_modes, "failure_modes", required=True),
            testable_predictions=_bounded_items(
                testable_predictions, "testable_predictions", required=True
            ),
            scope=_bounded_text(scope, "scope"),
            provenance_json=provenance_json,
        )
        if len(canonical_bytes(candidate.to_dict())) > _MAX_SPEC_BYTES:
            raise ProblemSpecError(
                f"canonical problem specification exceeds {_MAX_SPEC_BYTES} bytes"
            )
        return candidate

    @classmethod
    def from_value(cls, value: "ProblemSpec | Mapping[str, Any]") -> "ProblemSpec":
        if isinstance(value, cls):
            if value.schema != PROBLEM_SPEC_SCHEMA:
                raise ProblemSpecError("unknown problem specification schema")
            return cls.create(
                problem_id=value.problem_id,
                question=value.question,
                context=value.context,
                constraints=value.constraints,
                desired_outcomes=value.desired_outcomes,
                failure_modes=value.failure_modes,
                testable_predictions=value.testable_predictions,
                scope=value.scope,
                provenance=restore_source_floats(value.provenance),
            )
        if not isinstance(value, Mapping):
            raise ProblemSpecError("problem specification must be a mapping")
        source_keys = {
            "problem_id",
            "question",
            "context",
            "constraints",
            "desired_outcomes",
            "failure_modes",
            "testable_predictions",
            "scope",
            "provenance",
        }
        keys = set(value)
        if keys == source_keys | {"schema"}:
            if value["schema"] != PROBLEM_SPEC_SCHEMA:
                raise ProblemSpecError("unknown problem specification schema")
            serialized = dict(value)
            if not canonical_tree_is_valid(serialized):
                raise ProblemSpecError(
                    "serialized problem specification is not canonical"
                )
            source = {key: value[key] for key in source_keys}
            source["provenance"] = restore_source_floats(source["provenance"])
        elif keys == source_keys:
            source = dict(value)
        else:
            raise ProblemSpecError("problem specification has unknown or missing keys")
        return cls.create(**source)

    @property
    def provenance(self) -> dict[str, Any]:
        value = json.loads(self.provenance_json)
        if not isinstance(value, dict):
            raise ProblemSpecError("stored provenance is not an object")
        return value

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "problem_id": self.problem_id,
            "question": self.question,
            "context": list(self.context),
            "constraints": list(self.constraints),
            "desired_outcomes": list(self.desired_outcomes),
            "failure_modes": list(self.failure_modes),
            "testable_predictions": list(self.testable_predictions),
            "scope": self.scope,
            "provenance": self.provenance,
        }


class AdviceProtocol(Protocol):
    """Tiny proposal-only surface implemented by a mounted sealed-v18 client."""

    def describe(self) -> Any: ...

    def propose_structural_features(self, text: str, *, top_k: int = 5) -> Any: ...


@dataclass(frozen=True, slots=True)
class WorkflowOutcome:
    state: WorkflowState
    trace: tuple[WorkflowState, ...]
    reason_codes: tuple[str, ...]
    request_created: bool
    problem_spec_hash: str
    node_id: str
    previous_root: str
    new_root: str
    receipt: Any | None
    receipt_verified: bool
    live_state_verified: bool

    @property
    def committed(self) -> bool:
        return self.state is WorkflowState.COMMITTED

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "boggers-ts-problem-workflow-outcome-v1",
            "state": self.state.value,
            "trace": [state.value for state in self.trace],
            "reason_codes": list(self.reason_codes),
            "request_created": self.request_created,
            "problem_spec_hash": self.problem_spec_hash,
            "node_id": self.node_id,
            "previous_root": self.previous_root,
            "new_root": self.new_root,
            "receipt": self.receipt.to_dict() if self.receipt is not None else None,
            "receipt_verified": self.receipt_verified,
            "live_state_verified": self.live_state_verified,
            "committed": self.committed,
        }
