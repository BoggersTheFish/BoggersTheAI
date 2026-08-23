"""Verifier-governed discrete transition world model."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json


def _hash_payload(
    payload: dict,
) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class TransitionCandidate:
    rule_id: str
    state: tuple[int, ...]
    action: str
    next_state: tuple[int, ...]
    support: int
    contradictions: int


@dataclass(frozen=True)
class TransitionAuthorization:
    rule_id: str
    verdict: bool
    evidence_hash: str
    reason: str


class VerifiedWorldModel:
    """Separate proposed and verified transition structure."""

    def __init__(self) -> None:
        self.counts: dict[
            tuple[
                tuple[int, ...],
                str,
            ],
            dict[
                tuple[int, ...],
                int,
            ],
        ] = {}

        self.proposed: dict[
            str,
            TransitionCandidate,
        ] = {}

        self.verified: dict[
            tuple[
                tuple[int, ...],
                str,
            ],
            TransitionCandidate,
        ] = {}

    @staticmethod
    def rule_id(
        state: tuple[int, ...],
        action: str,
        next_state: tuple[int, ...],
    ) -> str:
        return (
            "tr:"
            + _hash_payload(
                {
                    "state": list(
                        state
                    ),
                    "action": action,
                    "next_state": list(
                        next_state
                    ),
                }
            )
        )

    def observe(
        self,
        state: tuple[int, ...],
        action: str,
        next_state: tuple[int, ...],
    ) -> None:
        key = (
            state,
            action,
        )

        outcomes = (
            self.counts.setdefault(
                key,
                {},
            )
        )

        outcomes[
            next_state
        ] = (
            outcomes.get(
                next_state,
                0,
            )
            + 1
        )

    def propose_rule(
        self,
        state: tuple[int, ...],
        action: str,
    ) -> TransitionCandidate | None:
        outcomes = self.counts.get(
            (
                state,
                action,
            )
        )

        if not outcomes:
            return None

        ordered = sorted(
            outcomes.items(),
            key=lambda row: (
                -row[1],
                row[0],
            ),
        )

        next_state, support = (
            ordered[0]
        )

        total = sum(
            outcomes.values()
        )

        candidate = (
            TransitionCandidate(
                rule_id=self.rule_id(
                    state,
                    action,
                    next_state,
                ),
                state=state,
                action=action,
                next_state=(
                    next_state
                ),
                support=support,
                contradictions=(
                    total
                    - support
                ),
            )
        )

        self.proposed[
            candidate.rule_id
        ] = candidate

        return candidate

    def apply(
        self,
        authorization: (
            TransitionAuthorization
        ),
    ) -> None:
        candidate = (
            self.proposed.get(
                authorization.rule_id
            )
        )

        if candidate is None:
            raise KeyError(
                "unknown transition proposal"
            )

        if not authorization.verdict:
            raise PermissionError(
                "failed transition verdict "
                "cannot authorize world model"
            )

        self.verified[
            (
                candidate.state,
                candidate.action,
            )
        ] = candidate

    def step_verified(
        self,
        state: tuple[int, ...],
        action: str,
    ) -> tuple[int, ...] | None:
        candidate = (
            self.verified.get(
                (
                    state,
                    action,
                )
            )
        )

        if candidate is None:
            return None

        return candidate.next_state

    def verified_successors(
        self,
        state: tuple[int, ...],
    ) -> tuple[
        tuple[
            str,
            tuple[int, ...],
        ],
        ...,
    ]:
        rows = [
            (
                action,
                rule.next_state,
            )
            for (
                rule_state,
                action,
            ), rule
            in self.verified.items()
            if rule_state == state
        ]

        rows.sort()

        return tuple(rows)


class TransitionVerifier:
    """Initial conservative deterministic world-model gate.

    This is an architecture gate, not yet a scientific confidence claim.
    """

    MIN_SUPPORT = 16

    def authorize(
        self,
        candidate: TransitionCandidate,
    ) -> TransitionAuthorization:
        verdict = (
            candidate.support
            >= self.MIN_SUPPORT
            and candidate.contradictions
            == 0
        )

        payload = {
            "rule_id": (
                candidate.rule_id
            ),
            "support": (
                candidate.support
            ),
            "contradictions": (
                candidate.contradictions
            ),
            "minimum_support": (
                self.MIN_SUPPORT
            ),
            "verdict": verdict,
        }

        return (
            TransitionAuthorization(
                rule_id=(
                    candidate.rule_id
                ),
                verdict=verdict,
                evidence_hash=(
                    _hash_payload(
                        payload
                    )
                ),
                reason=(
                    "SUPPORTED_DETERMINISTIC_TRANSITION"
                    if verdict
                    else
                    "INSUFFICIENT_TRANSITION_EVIDENCE"
                ),
            )
        )
