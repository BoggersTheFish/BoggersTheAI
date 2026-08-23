"""Deterministic distributed proposal-ranking field."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from core.construction.types import (
    ConstructionSpec,
    FeatureExpr,
    FeatureOp,
)


FIELD_DIMENSION = 256


def _expression_tokens(
    expr: FeatureExpr,
    *,
    depth: int = 0,
) -> tuple[str, ...]:
    tokens = [
        "op:" + expr.op.value,
        "depth:" + str(depth),
    ]

    if expr.op == FeatureOp.LAG:
        assert expr.lag is not None

        tokens.extend(
            (
                "lag:" + str(expr.lag),
                "lag-band:"
                + str(
                    expr.lag.bit_length()
                ),
            )
        )

    elif expr.op == FeatureOp.REF:
        tokens.append(
            "ref"
        )

    else:
        assert expr.left is not None
        assert expr.right is not None

        tokens.extend(
            _expression_tokens(
                expr.left,
                depth=depth + 1,
            )
        )

        tokens.extend(
            _expression_tokens(
                expr.right,
                depth=depth + 1,
            )
        )

    return tuple(tokens)


def _feature(
    token: str,
) -> tuple[int, int]:
    digest = hashlib.sha256(
        token.encode(
            "utf-8"
        )
    ).digest()

    index = (
        int.from_bytes(
            digest[:4],
            "big",
        )
        % FIELD_DIMENSION
    )

    sign = (
        1
        if digest[4] & 1
        else -1
    )

    return (
        index,
        sign,
    )


def sparse_features(
    spec: ConstructionSpec,
    context_tokens: tuple[
        str,
        ...,
    ],
) -> dict[int, int]:
    result: dict[
        int,
        int,
    ] = {}

    tokens = list(
        _expression_tokens(
            spec.expression
        )
    )

    tokens.extend(
        "context:" + token
        for token
        in context_tokens
    )

    for token in tokens:
        index, sign = (
            _feature(
                token
            )
        )

        result[index] = (
            result.get(
                index,
                0,
            )
            + sign
        )

    return result


@dataclass(frozen=True)
class RankedCandidate:
    construction_id: str
    score: int


class DistributedProposalField:
    """Small deterministic online learned routing field.

    It changes ranking, never authority.
    """

    def __init__(self) -> None:
        self.weights = [
            0
            for _ in range(
                FIELD_DIMENSION
            )
        ]

        self.bias: dict[
            str,
            int,
        ] = {}

    def score(
        self,
        spec: ConstructionSpec,
        context_tokens: tuple[
            str,
            ...,
        ],
    ) -> int:
        features = (
            sparse_features(
                spec,
                context_tokens,
            )
        )

        total = self.bias.get(
            spec.construction_id,
            0,
        )

        for index, value in (
            features.items()
        ):
            total += (
                self.weights[
                    index
                ]
                * value
            )

        return total

    def update(
        self,
        spec: ConstructionSpec,
        context_tokens: tuple[
            str,
            ...,
        ],
        *,
        accepted: bool,
        gain_ppm: int,
    ) -> None:
        magnitude = max(
            1,
            min(
                100,
                abs(
                    gain_ppm
                )
                // 10_000
                + 1,
            ),
        )

        direction = (
            1
            if accepted
            else -1
        )

        step = (
            direction
            * magnitude
        )

        features = (
            sparse_features(
                spec,
                context_tokens,
            )
        )

        for index, value in (
            features.items()
        ):
            self.weights[
                index
            ] += (
                step
                * value
            )

        self.bias[
            spec.construction_id
        ] = (
            self.bias.get(
                spec.construction_id,
                0,
            )
            + step
        )

    def rank(
        self,
        specs: tuple[
            ConstructionSpec,
            ...,
        ],
        context_tokens: tuple[
            str,
            ...,
        ],
    ) -> tuple[
        RankedCandidate,
        ...,
    ]:
        rows = [
            RankedCandidate(
                construction_id=(
                    spec.construction_id
                ),
                score=self.score(
                    spec,
                    context_tokens,
                ),
            )
            for spec in specs
        ]

        rows.sort(
            key=lambda row: (
                -row.score,
                row.construction_id,
            )
        )

        return tuple(rows)
