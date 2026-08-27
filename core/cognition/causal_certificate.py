"""Logical intervention certificates and causal authority."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from itertools import combinations

from .causal_program import (
    CONFIGURATIONS,
    CausalProgram,
    program_lookup,
    program_universe,
)


ZERO_HASH = (
    "0"
    * 64
)


def _canonical(
    payload: dict,
) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


@lru_cache(maxsize=1)
def universe_hash() -> str:
    payload = [
        {
            "program_id": (
                program.program_id
            ),
            "label": (
                program.label
            ),
            "signature": list(
                program.signature
            ),
        }
        for program
        in program_universe()
    ]

    return hashlib.sha256(
        _canonical(
            {
                "programs": payload
            }
        )
    ).hexdigest()


def compatible_program_ids(
    observations: dict[
        tuple[int, ...],
        int,
    ],
) -> tuple[str, ...]:
    rows = []

    for program in (
        program_universe()
    ):
        if all(
            program.evaluate(
                configuration
            )
            == outcome
            for configuration, outcome
            in observations.items()
        ):
            rows.append(
                program.program_id
            )

    return tuple(
        rows
    )


@lru_cache(maxsize=None)
def minimal_certificate(
    program_id: str,
) -> tuple[
    tuple[int, ...],
    ...,
]:
    lookup = (
        program_lookup()
    )

    target = lookup[
        program_id
    ]

    others = tuple(
        program
        for program
        in program_universe()
        if (
            program.program_id
            != program_id
        )
    )

    for size in range(
        1,
        len(CONFIGURATIONS)
        + 1,
    ):
        for indices in combinations(
            range(
                len(
                    CONFIGURATIONS
                )
            ),
            size,
        ):
            if all(
                any(
                    target.evaluate(
                        CONFIGURATIONS[
                            index
                        ]
                    )
                    != other.evaluate(
                        CONFIGURATIONS[
                            index
                        ]
                    )
                    for index
                    in indices
                )
                for other
                in others
            ):
                return tuple(
                    CONFIGURATIONS[
                        index
                    ]
                    for index
                    in indices
                )

    raise RuntimeError(
        "no distinguishing certificate"
    )


@dataclass(frozen=True)
class CausalAuthorization:
    program_id: str
    verdict: bool
    observation_count: int
    compatible_program_ids: tuple[
        str,
        ...,
    ]
    universe_hash: str
    receipt_hash: str


class CausalAuthorityLedger:
    FORMAT = (
        "prime-m24-causal-authority-v1"
    )

    def __init__(self) -> None:
        self.records: list[
            dict
        ] = []

    @property
    def head_hash(self) -> str:
        if not self.records:
            return ZERO_HASH

        return self.records[
            -1
        ][
            "receipt_hash"
        ]

    def authorize(
        self,
        program_id: str,
        observations: dict[
            tuple[int, ...],
            int,
        ],
    ) -> CausalAuthorization:
        lookup = (
            program_lookup()
        )

        if program_id not in lookup:
            raise KeyError(
                "unknown causal program"
            )

        compatible = (
            compatible_program_ids(
                observations
            )
        )

        verdict = (
            compatible
            == (
                program_id,
            )
        )

        payload = {
            "format": self.FORMAT,
            "sequence": len(
                self.records
            ),
            "program_id": (
                program_id
            ),
            "observations": [
                {
                    "configuration": list(
                        configuration
                    ),
                    "outcome": (
                        outcome
                    ),
                }
                for (
                    configuration,
                    outcome,
                )
                in sorted(
                    observations.items()
                )
            ],
            "compatible_program_ids": list(
                compatible
            ),
            "universe_hash": (
                universe_hash()
            ),
            "verdict": verdict,
            "parent_hash": (
                self.head_hash
            ),
        }

        receipt_hash = (
            hashlib.sha256(
                _canonical(
                    payload
                )
            ).hexdigest()
        )

        record = {
            **payload,
            "receipt_hash": (
                receipt_hash
            ),
        }

        self.records.append(
            record
        )

        return CausalAuthorization(
            program_id=(
                program_id
            ),
            verdict=verdict,
            observation_count=len(
                observations
            ),
            compatible_program_ids=(
                compatible
            ),
            universe_hash=(
                payload[
                    "universe_hash"
                ]
            ),
            receipt_hash=(
                receipt_hash
            ),
        )

    def verify_chain(
        self,
    ) -> bool:
        parent = ZERO_HASH

        for sequence, record in (
            enumerate(
                self.records
            )
        ):
            if (
                record[
                    "sequence"
                ]
                != sequence
            ):
                return False

            if (
                record[
                    "parent_hash"
                ]
                != parent
            ):
                return False

            payload = {
                key: value
                for key, value
                in record.items()
                if key
                != "receipt_hash"
            }

            expected = (
                hashlib.sha256(
                    _canonical(
                        payload
                    )
                ).hexdigest()
            )

            if (
                expected
                != record[
                    "receipt_hash"
                ]
            ):
                return False

            parent = expected

        return True
