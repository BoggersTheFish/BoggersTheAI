"""Cortex <-> PRIME bridge.

Neural cognition may propose and predict.
PRIME remains the sole epistemic authority.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from typing import Any

from core.language.tslc import TSLCCompiler
from core.verifier.verifier_os import VerifierOS


VERIFIER_LABELS = (
    "UNKNOWN",
    "ACCEPT",
    "REJECT",
    "REPAIR",
    "ABSTAIN",
)

VERIFIER_LABEL_TO_ID = {
    label: index
    for index, label in enumerate(VERIFIER_LABELS)
}


def canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def stable_hash(
    value: Any,
) -> str:
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def action_to_label(
    action: str | None,
) -> str:
    value = str(
        action or ""
    ).strip().lower()

    if value in {
        "accept",
        "accepted",
        "record",
        "commit",
        "committed",
    }:
        return "ACCEPT"

    if value in {
        "reject",
        "rejected",
    }:
        return "REJECT"

    if value in {
        "repair",
        "open_repair",
        "representation_repair",
        "supersede",
    }:
        return "REPAIR"

    if value in {
        "abstain",
        "abstained",
        "quarantine",
        "quarantined",
        "defer",
        "branch",
    }:
        return "ABSTAIN"

    return "UNKNOWN"


def compact_semantics(
    compiled: dict,
) -> dict:
    premises = list(
        compiled
        .get("graph_deltas", {})
        .get("premises", [])
    )[:4]

    obligations = list(
        compiled.get(
            "verifier_obligations",
            [],
        )
    )[:2]

    def clean(
        values,
    ):
        return [
            str(value)[:220]
            for value in values
        ]

    return {
        "provenance": "model_proposer",
        "status": "proposed",
        "premises": clean(
            premises
        ),
        "obligations": clean(
            obligations
        ),
    }


@dataclass
class VerifierExperience:
    source_sha256: str
    source_text: str

    proposal: dict
    proposal_sha256: str

    premises: list[str]
    obligation: str

    verifier_action: str
    verifier_label: str
    verifier_label_id: int

    verifier_result: dict
    verifier_result_sha256: str

    authority: str = "NONE"

    parent_hash: str = ""
    record_hash: str = ""

    def payload_without_hash(
        self,
    ):
        payload = asdict(
            self
        )

        payload.pop(
            "record_hash",
            None,
        )

        return payload


class PrimeCortexBridge:
    """Non-authoritative cortex interface to PRIME verification."""

    def __init__(
        self,
        *,
        compiler=None,
        verifier=None,
    ):
        self.compiler = (
            compiler
            if compiler is not None
            else TSLCCompiler()
        )

        self.verifier = (
            verifier
            if verifier is not None
            else VerifierOS()
        )

    def compile_source(
        self,
        text: str,
    ) -> dict:
        return self.compiler.compile(
            text
        )

    def semantic_proposal(
        self,
        text: str,
    ) -> dict:
        return compact_semantics(
            self.compile_source(
                text
            )
        )

    def verify_proposal(
        self,
        *,
        source_text: str,
        source_sha256: str,
        proposal: dict,
        parent_hash: str = "",
    ) -> list[VerifierExperience]:

        premises = [
            str(item)
            for item in proposal.get(
                "premises",
                [],
            )
        ]

        obligations = [
            str(item)
            for item in proposal.get(
                "obligations",
                [],
            )
        ]

        experiences = []

        for obligation in obligations:
            try:
                result = (
                    self.verifier.verify_claim(
                        premises,
                        obligation,
                    )
                )

                action = str(
                    result.get(
                        "action",
                        "unknown",
                    )
                )

            except Exception as error:
                action = "bridge_error"

                result = {
                    "action": action,
                    "error_type": (
                        type(error).__name__
                    ),
                    "error": str(error),
                }

            label = action_to_label(
                action
            )

            proposal_hash = stable_hash(
                proposal
            )

            verifier_hash = stable_hash(
                result
            )

            experience = VerifierExperience(
                source_sha256=(
                    source_sha256
                ),
                source_text=(
                    source_text
                ),
                proposal=proposal,
                proposal_sha256=(
                    proposal_hash
                ),
                premises=premises,
                obligation=obligation,
                verifier_action=action,
                verifier_label=label,
                verifier_label_id=(
                    VERIFIER_LABEL_TO_ID[
                        label
                    ]
                ),
                verifier_result=result,
                verifier_result_sha256=(
                    verifier_hash
                ),
                authority="NONE",
                parent_hash=parent_hash,
            )

            experience.record_hash = (
                stable_hash(
                    experience
                    .payload_without_hash()
                )
            )

            parent_hash = (
                experience.record_hash
            )

            experiences.append(
                experience
            )

        return experiences
